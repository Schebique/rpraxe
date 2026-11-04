"""Nastavení účtů, role učitele a správa — FastAPI router.

Pomocí `register(app, ctx)` se napojí na hlavní aplikaci bez cyklického importu:
`ctx` je modul `app.main` (helpery `db`, `current_user`, `ensure_users`, …).

Role
  student  – procvičuje, vidí jen sebe
  teacher  – vidí progress studentů, píše úlohy, může je zapsat do dnešní dávky
  admin    – plus účty, model, zálohy, promazání historie
"""
from __future__ import annotations

import os
import time
from datetime import date

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import accounts, adaptive, ai, store

LANGS = {"cs": "čeština", "en": "English", "sk": "slovenčina", "de": "Deutsch", "pl": "polština"}
THEMES = ("auto", "dark", "light")
BUDGETS = (10, 15, 20, 30, 45, 60)


class PrefsBody(BaseModel):
    minutes: int | None = None
    focus: str | None = None
    theme: str | None = None
    model: str | None = None
    lang: str | None = None

class TaskBody(BaseModel):
    id: str | None = None
    title: str = ""
    lesson: int = 0
    minutes: int = 4
    level: float = 1.0
    skills: list[str] = []
    dataset: str | None = None
    nacti: str = ""
    starter: str = ""
    zadani: str = ""
    check: str = ""
    reseni: str = ""
    hints: list[str] = []

class UserBody(BaseModel):
    user: str
    password: str = ""
    role: str = "student"


def register(app: APIRouter, ctx) -> None:
    """`ctx` je modul app.main — všechna sdílená helpery jsou na něm."""
    router = APIRouter()

    SSO_SECRET_ENV = "RPRAXE_SSO_SECRET"

    def me(request: Request) -> tuple[str, str]:
        user = ctx.current_user(request)
        if not user:
            raise HTTPException(401, "nepřihlášen")
        role = ctx.ensure_users().get(user, {}).get("role", "student")
        return user, role

    def staff(request: Request) -> tuple[str, str]:
        user, role = me(request)
        if role not in ("teacher", "admin"):
            raise HTTPException(403, "jen pro učitele nebo správce")
        return user, role

    def is_admin(request: Request) -> str:
        user, role = me(request)
        if role != "admin":
            raise HTTPException(403, "jen pro správce")
        return user

    # ------------------------------------------------------------ nastavení
    @router.get("/api/settings")
    async def api_settings(request: Request):
        user, role = me(request)
        with ctx.db() as c:
            p = store.prefs(c, user)
        models = await ai.list_models()
        return {
            "user": user, "role": role,
            "minutes": p["val"], "focus": p["focus"], "theme": p["theme"],
            "model": p["model"], "lang": p["lang"],
            "models": models, "default_model": ai.MODEL_CHAT,
            "langs": LANGS, "themes": list(THEMES), "budgets": list(BUDGETS),
            "ai_online": bool(models),
            "sso": {"possible": bool(os.environ.get("RPRAXE_SSO_HEADER")),
                    "gateway": bool(os.environ.get(SSO_SECRET_ENV))},
        }


    @router.post("/api/settings")
    async def api_settings_save(request: Request, body: PrefsBody):
        user, _ = me(request)
        if body.theme and body.theme not in THEMES:
            raise HTTPException(422, "takový motiv neznám")
        if body.lang and body.lang not in LANGS:
            raise HTTPException(422, "takový jazyk neznám")
        if body.minutes is not None and int(body.minutes) not in BUDGETS:
            raise HTTPException(422, "délka dávky musí být z nabídky")
        if body.model:
            if body.model not in await ai.list_models():
                raise HTTPException(422, "model není na serveru nahraný")
        with ctx.db() as c:
            p = store.set_prefs(c, user, val=body.minutes, focus=body.focus,
                                theme=body.theme, model=body.model or "", lang=body.lang)
        return {"ok": True, "minutes": p["val"], "theme": p["theme"], "model": p["model"],
                "lang": p["lang"], "focus": p["focus"]}

    # -------------------------------------------------- přehled žáků (učitel)
    @router.get("/api/class")
    def api_class(request: Request):
        staff(request)
        users = ctx.ensure_users()
        out = []
        with ctx.db() as c:
            for name, rec in sorted(users.items()):
                if rec.get("role", "student") != "student":
                    continue
                st = store.user_stats(c, name, days=120)
                last = c.execute("SELECT MAX(ts) FROM attempts WHERE user=?", (name,)).fetchone()[0]
                out.append({
                    "user": name,
                    "last": last or 0,
                    "days_active": st.get("days_active", 0),
                    "total": st.get("total", 0),
                    "passed": st.get("passed", 0),
                    "first_try_rate": st.get("first_try_rate"),
                    "minutes_total": round(st.get("minutes_total") or 0),
                    "streak": adaptive.streak(c, name),
                    "lesson": (c.execute("SELECT lesson FROM tasks WHERE status='approved' "
                                        "ORDER BY lesson DESC LIMIT 1").fetchone() or [None])[0],
                    "weak": [s["label"] for s in (st.get("skills") or [])
                             if s.get("n", 0) >= 2 and s.get("theta", 1) < 0.55][:3],
                })
        out.sort(key=lambda r: -r["last"])
        return {"students": out, "generated": time.time()}

    @router.get("/api/class/{student}")
    def api_class_one(request: Request, student: str, days: int = 90):
        staff(request)
        users = ctx.ensure_users()
        if student not in users:
            raise HTTPException(404, "takový účet není")
        with ctx.db() as c:
            st = store.user_stats(c, student, days=min(days, 365))
            st["plan_today"] = c.execute(
                "SELECT task_ids, minutes FROM plan WHERE day=? AND user=?",
                (ctx.today(), student)).fetchone()
            st["recent"] = [dict(r) for r in c.execute(
                "SELECT a.ts, a.task, t.title, a.ok, a.hints FROM attempts a "
                "LEFT JOIN tasks t ON t.id=a.task WHERE a.user=? ORDER BY a.ts DESC LIMIT 12",
                (student,))]
        return st

    # ------------------------------------------------------ úlohy (učitel)

    @router.post("/api/tasks")
    async def api_task_save(request: Request, body: TaskBody):
        who, role_of_me = staff(request)
        t = body.model_dump()
        for key in ("title", "zadani", "check", "reseni"):
            if not (t[key] or "").strip():
                raise HTTPException(422, f"chybí {key}")
        t["source"] = f"ucitel:{who}"
        t["status"] = "draft"
        with ctx.db() as c:
            exists = ctx.get_task(c, t["id"]) if t["id"] else None
            t["id"] = t["id"] or ctx.new_task_id(c, "uc")
            if exists and (exists.get("source") or "bank") == "bank" and role_of_me != "admin":
                raise HTTPException(403, "texty z autorské banky může měnit jen správce")
            t["created"] = (exists or {}).get("created") or time.time()
            store.upsert_task(c, {**t, "check": t["check"]})
        verdict = await ctx.validate_task({**t, "check_r": t["check"]})
        t["status"] = "approved" if verdict["ok"] else "draft"
        t["note"] = verdict.get("msg", "")[:400]
        with ctx.db() as c:
            store.upsert_task(c, t)
        return {"ok": verdict["ok"], "id": t["id"], "status": t["status"],
                "msg": verdict.get("msg", ""), "validated": verdict["ok"]}

    @router.delete("/api/tasks/{task_id}")
    def api_task_delete(request: Request, task_id: str):
        who, role = staff(request)
        with ctx.db() as c:
            t = ctx.get_task(c, task_id)
            if not t:
                raise HTTPException(404, "úloha není")
            owned = (t.get("source") or "").startswith(f"ucitel:{who}")
            if t.get("source") == "bank" and role != "admin":
                raise HTTPException(403, "úlohu z autorské banky může smazat jen správce")
            if not owned and role != "admin":
                raise HTTPException(403, "tuhle úlohu jsi nedělal ty")
            c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            c.execute("DELETE FROM srs WHERE task=?", (task_id,))
            c.execute("UPDATE plan SET task_ids = "
                      "REPLACE(task_ids, '\"' || ? || '\"', '') WHERE task_ids LIKE ?",
                      (task_id, f"%{task_id}%"))
        return {"ok": True, "id": task_id}

    @router.post("/api/tasks/{task_id}/assign")
    def api_task_assign(request: Request, task_id: str, student: str):
        who, _ = staff(request)
        users = ctx.ensure_users()
        if student not in users:
            raise HTTPException(404, "takový účet není")
        with ctx.db() as c:
            t = ctx.get_task(c, task_id)
            if not t:
                raise HTTPException(404, "úloha není")
            row = c.execute("SELECT task_ids FROM plan WHERE day=? AND user=?",
                            (ctx.today(), student)).fetchone()
            import json as _json
            ids = _json.loads(row["task_ids"]) if row else []
            if task_id not in ids:
                ids.append(task_id)
            c.execute("INSERT INTO plan(day,user,task_ids,minutes,created) VALUES(?,?,?,?,?) "
                      "ON CONFLICT(day,user) DO UPDATE SET task_ids=excluded.task_ids",
                      (ctx.today(), student, _json.dumps(ids), 0, time.time()))
        return {"ok": True, "student": student, "task": task_id}

    # ----------------------------------------------------------- účty (admin)
    @router.get("/api/users")
    def api_users(request: Request):
        is_admin(request)
        users = ctx.ensure_users()
        return {"users": [{"user": k, "role": v.get("role", "student"),
                           "changed": v.get("changed"), "generated_pw": bool(v.get("first_pw"))}
                          for k, v in sorted(users.items())],
                "roles": list(accounts.ROLES)}


    @router.post("/api/users")
    def api_user_create(request: Request, body: UserBody):
        is_admin(request)
        users = ctx.ensure_users()
        try:
            rec = accounts.create_user(users, body.user, body.password, body.role)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        ctx._users_save(users)
        return {"ok": True, "user": body.user.lower(), "role": rec["role"]}

    @router.post("/api/users/{name}/password")
    def api_user_password(request: Request, name: str, body: UserBody):
        is_admin(request)
        users = ctx.ensure_users()
        if name not in users:
            raise HTTPException(404, "účet nenalezen")
        if len(body.password or "") < 8:
            raise HTTPException(422, "heslo musí mít aspoň 8 znaků")
        users[name] = {**users[name], "hash": accounts.hash_pw(body.password),
                       "changed": time.strftime("%Y-%m-%d %H:%M"), "first_pw": None}
        ctx._users_save(users)
        return {"ok": True, "user": name}

    @router.post("/api/users/{name}/role")
    def api_user_role(request: Request, name: str, body: UserBody):
        admin = is_admin(request)
        users = ctx.ensure_users()
        if name not in users:
            raise HTTPException(404, "účet nenalezen")
        if name == admin and body.role != "admin":
            raise HTTPException(422, "sám sobě nemůžeš vzít roli správce")
        users[name] = {**users[name], "role": accounts.normalize_role(body.role)}
        ctx._users_save(users)
        return {"ok": True, "user": name, "role": users[name]["role"]}

    # ------------------------------------------------------ provoz (admin)
    @router.post("/api/admin/backup")
    def api_backup_now(request: Request):
        """Konzistentní snímek běžící DB do state/backups (kopii na NAS dělá noční skript)."""
        import sqlite3

        is_admin(request)
        ctx.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        name = time.strftime("rpraxe-%Y%m%d-%H%M%S.db")
        dst_path = ctx.BACKUP_DIR / name
        try:
            with ctx.db() as src, sqlite3.connect(dst_path) as dst:
                src.backup(dst)
        except sqlite3.Error as exc:
            raise HTTPException(500, f"snímek se nepovedl: {exc}") from exc
        os.chmod(dst_path, 0o600)
        return {"ok": True, "name": name, "bytes": dst_path.stat().st_size}

    @router.get("/api/system")
    async def api_system(request: Request):
        is_admin(request)
        ok, msg = await ai.available()
        with ctx.db() as c:
            n_tasks = c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            n_draft = c.execute("SELECT COUNT(*) FROM tasks WHERE status='draft'").fetchone()[0]
            n_users = len(ctx.ensure_users())
            n_attempts = c.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
            size = store.DB.stat().st_size if store.DB.exists() else 0
            notes = c.execute("SELECT val FROM ai_cache WHERE key='agent_note'").fetchone()
        return {
            "ai_online": ok, "ai_msg": msg[:200],
            "models": await ai.list_models(),
            "model_write": ai.MODEL_WRITE,
            "tasks": n_tasks, "drafts": n_draft, "users": n_users, "attempts": n_attempts,
            "db_bytes": size,
            "datasets": sorted(ctx.datasets()),
            "agent_note": (notes or [None])[0],
            "lesson_current": ctx.syllabus.current_lesson(),
            "backups": ctx.backup_status(),
            "version": ctx.VERSION,
        }

    app.include_router(router)
