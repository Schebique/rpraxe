"""Nastavení účtů, role učitele a správa — FastAPI router.

Pomocí `register(app, ctx)` se napojí na hlavní aplikaci bez cyklického importu:
`ctx` je modul `app.main` (helpery `db`, `current_user`, `ensure_users`, …).

Role
  student  – procvičuje, vidí jen sebe
  teacher  – vidí progress studentů, píše úlohy, může je zapsat do dnešní dávky
  admin    – plus účty, model, zálohy, promazání historie
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import accounts, adaptive, ai, config as instance, store

LANGS = {"cs": "čeština", "en": "English", "sk": "slovenčina", "de": "Deutsch", "pl": "polština"}
THEMES = ("auto", "dark", "light")
BUDGETS = (10, 15, 20, 30, 45, 60)


class TridaBody(BaseModel):
    id: str | None = None
    name: str | None = None
    poznamka: str | None = None
    zaci: list[str] | None = None
    ucitel: str | None = None


class OveritBody(BaseModel):
    schvalit: bool = False


class StatusBody(BaseModel):
    status: str = "approved"


class AiBody(BaseModel):
    poskytovatel: str | None = None
    adresa: str | None = None
    klic: str | None = None
    model: str | None = None
    model_psani: str | None = None
    timeout: float | None = None
    overit: bool = True


class PrihlaseniBody(BaseModel):
    sso: bool | None = None
    hlavka_jmeno: str | None = None
    hlavka_role: str | None = None
    tajemstvi: str | None = None
    role_z_skupin: dict | None = None
    povolene_ucety: list[str] | None = None


class RestoreBody(BaseModel):
    jmeno: str
    potvrdit: str = ""


class PrefsBody(BaseModel):
    minutes: int | None = None
    focus: str | None = None
    theme: str | None = None
    model: str | None = None
    lang: str | None = None

class TaskBody(BaseModel):
    id: str | None = None
    kontrola_ai: bool = True      # model úlohu před uložením zkritizuje
    pres: bool = False            # uložit i přesto, že strojové ověření neprošlo
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


def _ai_pro_ui() -> dict:
    """Nasazený model pro kartu ve správě; klíč jen maskovaně."""
    nasazeni = instance.ai_cfg()
    return {"poskytovatel": nasazeni["poskytovatel"], "adresa": nasazeni["adresa"],
            "model": nasazeni["model"], "model_psani": nasazeni["model_psani"],
            "styl": nasazeni["styl"], "klic": instance.mask(nasazeni.get("klic", "")),
            "mimo_zdani": nasazeni["venku"]}


def _prihlaseni_pro_ui() -> dict:
    nasazeni = instance.sso_cfg()
    zapnuto = instance.sso_zapnuto()
    return {"zapnuto": zapnuto,
            "hlavka_jmeno": nasazeni.get("hlavka_jmeno") or "",
            "hlavka_role": nasazeni.get("hlavka_role") or "",
            "hlavka_tajemstvi": "x-rpraxe-sso",
            "popis": ("přihlašování přes bránu je zapnuté — účet se založí sám podle hlavičky"
                      if zapnuto else
                      "přihlašuje se jen heslem — SSO zapneš níže v kartě Přihlašování")}


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
            "models": models, "default_model": ai.modely_info()["model"],
            "ai": _ai_pro_ui(),
            "langs": LANGS, "themes": list(THEMES), "budgets": list(BUDGETS),
            "ai_online": bool(models),
            "sso": {"zapnuto": bool(os.environ.get("RPRAXE_SSO_SECRET")),
                    "hlavka": os.environ.get("RPRAXE_SSO_HEADER", "Remote-User"),
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
        # model si uživatel nevolí — nasazuje ho správce (Síť > Modely), ať everyone
        # dostane stejného kouče a nikdo si nenece rozpočet tím nejdražším
        with ctx.db() as c:
            p = store.set_prefs(c, user, val=body.minutes, focus=body.focus,
                                theme=body.theme, lang=body.lang)
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
                    "tridy": store.classes_of(c, name),
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
        """Uloží úlohu — ale nenesmysl nepustí.

        Nejdřív se úloha ověří spuštěním v sandboxu, do databáze se teprve pak
        dostane taková, která řešením projde a prázdným kódem ne. Model k tomu
        řekne svůj názor (volitelné); ten nic neschvaluje, jen varuje.
        """
        kdo, role_me = staff(request)
        t = body.model_dump()
        for key in ("title", "zadani", "check", "reseni"):
            if not (t[key] or "").strip():
                raise HTTPException(422, f"chybí {key}")
        t["source"] = f"ucitel:{kdo}"
        with ctx.db() as c:
            exist = ctx.get_task(c, t["id"]) if t["id"] else None
            t["id"] = t["id"] or ctx.new_task_id(c, "uc")
            if exist and (exist.get("source") or "bank") == "bank" and role_me != "admin":
                raise HTTPException(403, "texty z autorské banky může měnit jen správce")
            t["created"] = (exist or {}).get("created") or time.time()
        nacteno = await ctx.overeni_spustenim(t)
        nazor = {}
        if nacteno["ok"] and body.kontrola_ai:
            nazor = await ai.review_task(t)
        duvody = list(nacteno.get("duvody") or [])
        if not nazor.get("proslo") and nazor and not nazor.get("chyba"):
            duvody += ["model: " + z for z in (nazor.get("zavady") or [])[:4]]
        if not nacteno["ok"] and not body.pres:
            # nic se neprepíše — ať se učitel nestane autorem úlohy, která nejde splnit
            return {"ok": False, "ulozeno": False, "id": t["id"], "status": (exist or {}).get("status"),
                    "zprava": "; ".join(duvody) or "ověření neprošlo",
                    "detail": nacteno, "model": nazor}
        t["status"] = "approved" if (nacteno["ok"] and not duvody) else "draft"
        t["note"] = ("strojově ok" if nacteno["ok"] else "; ".join(duvody))[:400]
        with ctx.db() as c:
            store.upsert_task(c, {**t, "check": t["check"]})
        provozni_log("úloha %s uložena %s → %s (%s)" % (t["id"], kdo, t["status"], t["note"][:60]))
        return {"ok": t["status"] == "approved", "ulozeno": True, "id": t["id"],
                "status": t["status"], "zprava": "; ".join(duvody)[:300],
                "detail": nacteno, "model": nazor}

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
        provozni_log("ruční snímek %s udělal %s" % (name, is_admin(request)))
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
            "model_write": ai.modely_info()["model_psani"],
            "tasks": n_tasks, "drafts": n_draft, "users": n_users, "attempts": n_attempts,
            "db_bytes": size,
            "datasets": sorted(ctx.datasets()),
            "agent_note": (notes or [None])[0],
            "lesson_current": ctx.syllabus.current_lesson(),
            "backups": ctx.backup_status(),
            "version": ctx.VERSION,
            # aby bylo vidět, jest se přihlašuje přes bránu, nebo jen heslem
            "sso": _prihlaseni_pro_ui(),
            # co je zrovna nasazený model — uživatel sieho nevolí
            "ai": _ai_pro_ui(),
        }

    # -------------------------------------------------------------- třídy
    @router.get("/api/classes")
    def api_classes(request: Request):
        """Tridy, ktere vedi ten kdo; spratce vidí všechny."""
        kdo, role = staff(request)
        with ctx.db() as c:
            vsecny = store.classes(c)
            zaci_all = sorted(n for n, rec in ctx.ensure_users().items()
                              if rec.get("role", "student") == "student")
            if not vsecny:
                # aspoň jedna ukázka, ať je vidět, jak to má vypadat
                store.save_class(c, store.new_class_id(c), "Ukázková třída", kdo,
                                 "Ukázková skupina — přejmenuj ji nebo smaž.", zaci_all)
                vsecny = store.classes(c)
            if role == "admin":
                seznam = store.classes(c)
            else:
                seznam = [k for k in store.classes(c) if k["teacher"] == kdo]
            jmena = {k["id"] for k in seznam}
            for k in store.classes(c):        # cizí třídy ukážeme, jen je nejde měnit
                if k["id"] not in jmena:
                    k["cizí"] = True
                    seznam.append(k)
            zaci = sorted(n for n, rec in ctx.ensure_users().items()
                          if rec.get("role", "student") == "student")
        return {"tridy": seznam, "zaci": zaci, "ja": kdo}

    @router.post("/api/classes")
    def api_class_save(request: Request, body: TridaBody):
        """Založí nebo upravenou tridu uloží; učitel je její správce."""
        kdo, role = staff(request)
        name = (body.name or "").strip()
        if not name:
            raise HTTPException(422, "trída potřebuje jméno")
        if len(name) > 60:
            raise HTTPException(422, "jméno je moc dlouhé")
        zaci = [z.strip() for z in (body.zaci or []) if z.strip()]
        users = ctx.ensure_users()
        neplatni = [z for z in zaci if z not in users]
        if neplatni:
            raise HTTPException(422, "tyhle účty neznám: " + ", ".join(neplatni[:6]))
        with ctx.db() as c:
            identification = (body.id or "").strip()
            if identification:
                stajici = next((k for k in store.classes(c) if k["id"] == identification), None)
                if not stajici:
                    raise HTTPException(404, "taková trída není")
                if stajici["teacher"] != kdo and role != "admin":
                    raise HTTPException(403, "tuhle třídu nevedeš")
                teacher = stajici["teacher"] if role != "admin" else (body.ucitel or stajici["teacher"])
            else:
                teacher = kdo
                identification = store.new_class_id(c)
            trida = store.save_class(c, identification, name, teacher, (body.poznamka or "").strip(), zaci)
        provozni_log("trída %s (%s) uložena %s, žáků %d" % (identification, name, kdo, len(zaci)))
        return {"ok": True, "trida": trida}

    @router.delete("/api/classes/{identification}")
    def api_class_delete(request: Request, identification: str):
        kdo, role = staff(request)
        with ctx.db() as c:
            stajici = next((k for k in store.classes(c) if k["id"] == identification), None)
            if not stajici:
                raise HTTPException(404, "taková trída není")
            if stajici["teacher"] != kdo and role != "admin":
                raise HTTPException(403, "tuhle třídu nevedeš")
            store.drop_class(c, identification)
        provozni_log("trída %s smazána %s" % (identification, kdo))
        return {"ok": True}

    # --------------------------------------------- úloha pod drobnohledem (vyučující)
    @router.get("/api/tasks/{task_id}/review")
    async def api_task_review(request: Request, task_id: str):
        """Strukturovaný pohled i s řešením — pro lidskou kontrolu generované úlohy."""
        staff(request)
        with ctx.db() as c:
            ukol = ctx.get_task(c, task_id)
            if not ukol:
                raise HTTPException(404, "úloha není")
            pokusy = c.execute("SELECT COUNT(*) n, COALESCE(SUM(ok),0) p FROM attempts WHERE task=?",
                               (task_id,)).fetchone()
        ukol["check"] = ukol.pop("check_r", "") or ""
        ukol["pokusy"] = {"pokusy": pokusy["n"], "proselo": pokusy["p"]}
        nahled = await ctx.run_v_sandboxu(ukol, (ukol.get("nacti") or "").strip())
        return {"uloha": ukol,
                "nahled_dat": {k: nahled.get(k) for k in ("stdout", "error", "env") if k in nahled},
                "historie": history_overeni(ctx.db, task_id)}

    @router.post("/api/tasks/{task_id}/verify")
    async def api_task_verify(request: Request, task_id: str, body: OveritBody):
        """Ověř spuštěním: řešení musí projít, prázdný kód a kostka nesmí."""
        kdo, _ = staff(request)
        with ctx.db() as c:
            ukol = ctx.get_task(c, task_id)
            if not ukol:
                raise HTTPException(404, "úloha není")
        detail = await ctx.overeni_spustenim(ukol)
        short = "prošlo" if detail["ok"] else "; ".join(detail.get("duvody") or ["neprošlo"])
        with ctx.db() as c:
            c.execute("UPDATE tasks SET note=? WHERE id=?",
                      (("strojově %s: %s" % (ctx.today(), short))[:300], task_id))
            if detail["ok"] and body.schvalit:
                c.execute("UPDATE tasks SET status='approved' WHERE id=?", (task_id,))
        uloz_overeni(ctx.db, task_id, "stroj", {"kdo": kdo, "kdy": time.time(), **detail})
        with ctx.db() as c:
            stav = c.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()["status"]
        return {"ok": detail["ok"], "detail": detail, "status": stav}

    @router.post("/api/tasks/{task_id}/review-ai")
    async def api_task_review_ai(request: Request, task_id: str):
        """Nechat úlohu zkritizovat modelem; člověk vidí závady a případnou opravu checku."""
        kdo, _ = staff(request)
        with ctx.db() as c:
            ukol = ctx.get_task(c, task_id)
            if not ukol:
                raise HTTPException(404, "úloha není")
        nazor = await ai.review_task(ukol)
        uloz_overeni(ctx.db, task_id, "ai", {"kdo": kdo, "kdy": time.time(), **nazor})
        return nazor

    @router.post("/api/tasks/{task_id}/status")
    def api_task_status(request: Request, task_id: str, body: StatusBody):
        """Schválit / vrátit do konceptů / schovat — u banky jen správce."""
        kdo, role = staff(request)
        if body.status not in ("approved", "draft", "retired"):
            raise HTTPException(422, "neznámý status")
        with ctx.db() as c:
            ukol = ctx.get_task(c, task_id)
            if not ukol:
                raise HTTPException(404, "úloha není")
            vlastni = (ukol.get("source") or "").startswith("ucitel:%s" % kdo) or ukol.get("source") == "llm"
            if ukol.get("source") == "bank" and role != "admin":
                raise HTTPException(403, "úlohu z autorské banky mění jen správce")
            if not vlastni and role != "admin":
                raise HTTPException(403, "tuhle úlohu jsi nedělal ty")
            c.execute("UPDATE tasks SET status=? WHERE id=?", (body.status, task_id))
        provozni_log("status %s → %s (%s)" % (task_id, body.status, kdo))
        return {"ok": True, "status": body.status}

    # -------------------------------------------------------------- AI nastavení (admin)
    @router.get("/api/admin/ai")
    async def api_ai_config(request: Request):
        is_admin(request)
        nasazeni = instance.ai_cfg()
        online, hlaska = await ai.available()
        return {"poskytovatel": nasazeni["poskytovatel"], "adresa": nasazeni["adresa"],
                "model": nasazeni["model"], "model_psani": nasazeni["model_psani"],
                "klic": instance.mask(nasazeni.get("klic", "")), "timeout": nasazeni["timeout"],
                "mimo_zdani": nasazeni["venku"], "moznosti": instance.providers_pro_ui(),
                "online": online, "hlaska": hlaska[:300], "modely": await ai.list_models(),
                "info": ai.modely_info()}

    @router.post("/api/admin/ai")
    async def api_ai_save(request: Request, body: AiBody):
        kdo = is_admin(request)
        if body.poskytovatel and body.poskytovatel not in instance.PROVIDERS:
            raise HTTPException(422, "takového poskytovatele neznám")
        # externí poskytovatel bez klíče by jen mlčel — ať to ví hned
        zvoleny = body.poskytovatel or instance.ai_cfg()["poskytovatel"]
        venku = bool((instance.PROVIDERS.get(zvoleny) or {}).get("venku"))
        if venku and not (body.klic or instance.ai_cfg().get("klic")):
            jmeno = (instance.PROVIDERS.get(zvoleny) or {}).get("jmeno", zvoleny)
            raise HTTPException(422, "%s vyžaduje API klíč — bez něj by model neodpovídal" % jmeno)
        instance.set_cast("ai", poskytovatel=body.poskytovatel, adresa=body.adresa,
                          klic=body.klic, model=body.model, model_psani=body.model_psani,
                          timeout=body.timeout)
        nasazeni = instance.ai_cfg()
        online, hlaska = await ai.available() if body.overit else (True, "")
        provozni_log("AI nastavení změnil %s: %s %s %s" %
                     (kdo, nasazeni["poskytovatel"], nasazeni["adresa"], nasazeni["model"]))
        return {"ok": True, "poskytovatel": nasazeni["poskytovatel"], "model": nasazeni["model"],
                "klic": instance.mask(nasazeni.get("klic", "")), "online": online,
                "hlaska": hlaska[:300], "mimo_zdani": nasazeni["venku"]}

    # --------------------------------------------------- přihlašování přes bránu (admin)
    @router.get("/api/admin/login")
    def api_login_config(request: Request):
        is_admin(request)
        nasazeni = ctx.sso_cfg()
        return {"sso": bool(nasazeni.get("sso")), "hlavka_jmeno": nasazeni.get("hlavka_jmeno"),
                "hlavka_role": nasazeni.get("hlavka_role") or "",
                "tajemstvi": instance.mask(nasazeni.get("tajemstvi", "")),
                "role_z_skupin": nasazeni.get("role_z_skupin") or {},
                "povolene_ucety": nasazeni.get("povolene_ucety") or [],
                "sonda": ctx.sso_sonda(request), "ucity": sorted(ctx.ensure_users().keys()),
                "hlavka_tajemstvi": ctx.SSO_SECRET_HEADER}

    @router.post("/api/admin/login")
    def api_login_save(request: Request, body: PrihlaseniBody):
        kdo = is_admin(request)
        if body.sso and not (body.tajemstvi or ctx.sso_cfg().get("tajemstvi")):
            raise HTTPException(422, "bez tajemství brány SSO nezapnu")
        instance.set_cast("prihlasovani", sso=body.sso, hlavka_jmeno=body.hlavka_jmeno,
                          hlavka_role=body.hlavka_role, tajemstvi=body.tajemstvi,
                          role_z_skupin=body.role_z_skupin, povolene_ucety=body.povolene_ucety)
        provozni_log("přihlašování změnil %s: SSO=%s" % (kdo, "zap" if instance.sso_zapnuto() else "vyp"))
        return {"ok": True, "sso": instance.sso_zapnuto(), "tlacitko_na_strance": ctx.sso_zapnuto()}

    # ------------------------------------------------------------ zálohy a obnova (admin)
    @router.get("/api/admin/backups")
    def api_backups(request: Request):
        is_admin(request)
        return {"prehled": ctx.backup_status(), "snimky": snimky_k_obnove(ctx)}

    @router.post("/api/admin/restore")
    def api_restore(request: Request, body: RestoreBody):
        """Vrať databázi ke snímku. Bez slova OBNOVIT se nepřepíše nic."""
        kdo = is_admin(request)
        if (body.potvrdit or "").strip() != "OBNOVIT":
            raise HTTPException(422, "napiš OBNOVIT — jde o přepis dat")
        dostupne = {s["jmeno"]: s for s in snimky_k_obnove(ctx)}
        vybrany = dostupne.get(body.jmeno)
        if not vybrany:
            raise HTTPException(404, "takový snímek tu není")
        if not vybrany.get("pouzitelna"):
            raise HTTPException(422, "snímek nejde otevřít: " + vybrany.get("duvod", "?"))
        zdroj = ctx.BACKUP_DIR / body.jmeno
        jistota = ctx.BACKUP_DIR / ("pred-obnovou-%s.db" % time.strftime("%Y%m%d-%H%M%S"))
        with ctx.db() as zdroj_puvod, sqlite3.connect(jistota) as kopie:
            zdroj_puvod.backup(kopie)
        os.chmod(jistota, 0o600)
        with ctx.db() as c:
            c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        shutil.copyfile(zdroj, ctx.store.DB)
        for priloha in (str(ctx.store.DB) + "-wal", str(ctx.store.DB) + "-shm"):
            try:
                os.remove(priloha)
            except OSError:
                pass
        with ctx.db() as c:
            pokusu = c.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
            uloh = c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        provozni_log("DB obnovil %s ze %s (pokusy %d, úlohy %d, pojistka %s)" %
                     (kdo, body.jmeno, pokusu, uloh, jistota.name))
        return {"ok": True, "jmeno": body.jmeno, "pokusy": pokusu, "ulohy": uloh,
                "pojistka": jistota.name}

    app.include_router(router)


# --------------------------------------------------------------- pomoci pro spravu
def history_overeni(databaze, ukol: str) -> list[dict]:
    """Minulá ověření jedné úlohy (stroj i AI), nejnovější první."""
    with databaze() as c:
        rows = c.execute("SELECT val, ts FROM ai_cache WHERE key LIKE ? ORDER BY ts DESC LIMIT 12",
                         (f"overeni:{ukol}%",)).fetchall()
    out = []
    for r in rows:
        try:
            out.append(json.loads(r["val"]))
        except ValueError:
            continue
    return out


def uloz_overeni(databaze, ukol: str, druh: str, data: dict) -> None:
    """Jedno ověření do cache; klíč obsahuje čas, ať se záznamy nepřepisují."""
    klic = "overeni:%s:%s:%d" % (ukol, druh, int(time.time()))
    with databaze() as c:
        c.execute("INSERT INTO ai_cache(key,val,ts) VALUES(?,?,?) "
                  "ON CONFLICT(key) DO UPDATE SET val=excluded.val, ts=excluded.ts",
                  (klic, json.dumps(data, ensure_ascii=False)[:18000], time.time()))


def provozni_log(text: str) -> None:
    """Kdo kdy co přepnul — když se ztratí heslo nebo se objevil divný stav."""
    try:
        kam = Path(os.environ.get("RPRAXE_SPRAVA_LOG", "/data/state/sprava.log"))
        kam.parent.mkdir(parents=True, exist_ok=True)
        with open(kam, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + text + "\n")
    except OSError:
        pass


def snimky_k_obnove(ctx) -> list[dict]:
    """Snímky, ze kterých se dá vrátit; označí jen ty, které lze otevřít jako SQLite."""
    adresar = getattr(ctx, "BACKUP_DIR", None)
    if not adresar or not adresar.exists():
        return []
    out = []
    for cesta in sorted(adresar.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]:
        polozka = {"jmeno": cesta.name, "bytes": cesta.stat().st_size,
                   "cas": cesta.stat().st_mtime, "pouzitelna": False}
        try:
            with sqlite3.connect("file:%s?mode=ro" % cesta, uri=True) as probe:
                if probe.execute("PRAGMA integrity_check").fetchone()[0] == "ok":
                    polozka["pokusy"] = probe.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
                    polozka["ulohy"] = probe.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
                    polozka["pouzitelna"] = True
        except sqlite3.Error as exc:
            polozka["duvod"] = str(exc)[:120]
        out.append(polozka)
    return out
