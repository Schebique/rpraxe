"""Nastavení účtů, role učitele a správa — FastAPI router.

Pomocí `register(app, ctx)` se napojí na hlavní aplikaci bez cyklického importu:
`ctx` je modul `app.main` (helpery `db`, `current_user`, `ensure_users`, …).

Role
  student  – procvičuje, vidí jen sebe
  teacher  – vidí progress studentů, píše úlohy, může je zapsat do dnešní dávky
  admin    – plus účty, model, zálohy, promazání historie
"""
from __future__ import annotations

import csv
import httpx
import io
import json
import os
import re
import shutil
import sqlite3
import time
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import accounts, adaptive, ai, config as instance, store

_SANDBOX_CACHE = (0.0, {})

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


class DatasetBody(BaseModel):
    """CSV, které učitel nahraje z počítače a úloha se na něj pak odkáže."""
    jmeno: str
    data: str
    prepsat: bool = False


class ImportBody(BaseModel):
    """Text souboru s úlohami — klient načte JSON z disku a pošle ho jako řetězec."""
    data: str
    jmeno: str = "soubor.json"


class GithubBody(BaseModel):
    odkaz: str
    ref: str = "main"


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


# ------------------------------------------------------ datové soubory (vlastní)
_ADRESAR_DAT = os.environ.get("RPRAXE_DATASETS", "/data/datasets")
_POVOLENE_PRIPONY = (".csv", ".tsv", ".txt")
_MEZNIK_DAT = 4_000_000


def _jmeno_souboru(jmeno: str) -> str:
    """Důsledné jméno souboru — žádná cesta, žádná tečka za jménem adresáře."""
    ciste = Path((jmeno or "").strip()).name
    if not ciste or ciste.startswith("."):
        raise HTTPException(422, "soubor potřebuje jméno, třeba zkousky.csv")
    if not ciste.lower().endswith(_POVOLENE_PRIPONY):
        raise HTTPException(422, "dovedu jen .csv, .tsv a .txt — a úloha pak čte "
                                 "stejné jméno, jaké tu napíšeš")
    if len(ciste) > 64:
        raise HTTPException(422, "jméno je moc dlouhé (max 64 znaků)")
    return ciste


def _cesta_k_datum(jmeno: str) -> Path:
    root = Path(_ADRESAR_DAT).resolve()
    cesta = (root / jmeno).resolve()
    if root not in cesta.parents:
        raise HTTPException(422, "tohle není soubor v adresáři dat")
    return cesta


def _prepis_csv(text: str, cesta_k: Path) -> tuple[int, list[str]]:
    """Zkontroluje, že je to čitelná tabulka, a zapíše ji; vrátí řádky a sloupce."""
    oddelovac = "\t" if cesta_k.suffix.lower() == ".tsv" else ","
    nacteno = list(csv.reader(io.StringIO(text), delimiter=oddelovac))
    nacteno = [r for r in nacteno if any(str(b).strip() for b in r)]
    if len(nacteno) < 2:
        raise HTTPException(422, "v souboru není ani hlavička a jeden řádek dat")
    sirka = len(nacteno[0])
    if sirka < 1:
        raise HTTPException(422, "první řádek musí obsahovat názvy sloupců")
    if any(len(r) != sirka for r in nacteno[1:]):
        chybny = next(i for i, r in enumerate(nacteno[1:], start=2) if len(r) != sirka)
        raise HTTPException(422, "na řádku %d je jiný počet sloupců než v hlavičce (%d)"
                                    % (chybny, sirka))
    cesta_k.write_text(text.replace("\r\n", "\n").lstrip("\ufeff"), encoding="utf-8")
    return len(nacteno) - 1, [str(b).strip() for b in nacteno[0]]


def _uloz_data(jmeno: str, polozka: dict) -> str | None:
    """Součástí importu může být i rovnou obsah dat — pole řádků, nebo CSV text."""
    if not jmeno:
        return None
    cesta_k = _cesta_k_datum(jmeno)
    if cesta_k.is_file():
        return None
    csv_text = polozka.get("csv") or polozka.get("data_csv") or ""
    radky = polozka.get("data")
    if not csv_text and isinstance(radky, list) and radky and isinstance(radky[0], dict):
        sloupce = list(radky[0].keys())
        buffer = io.StringIO()
        zapis = csv.DictWriter(buffer, fieldnames=sloupce)
        zapis.writeheader()
        for radek in radky:
            zapis.writerow({k: radek.get(k, "") for k in sloupce})
        csv_text = buffer.getvalue()
    if not str(csv_text).strip():
        return None
    if len(csv_text) > _MEZNIK_DAT:
        raise HTTPException(422, "vložená data jsou moc velké (max 4 MB na soubor)")
    _prepis_csv(str(csv_text), cesta_k)
    return cesta_k.name


# --------------------------------------------------------- pomoci s GitHubem
_GITHUB_RE = re.compile(
    r"github[.]com[/:](?P<vlastnik>[\w.-]+)/(?P<repo>[\w.-]+?)(?:[.]git)?"
    r"(?:/(?:tree|blob)/(?P<ref>[^/]+)/(?P<cesta>.+?))?/?$", re.I)
_RAW_RE = re.compile(
    r"(?:raw|gist)[.]githubusercontent[.]com/(?P<vlastnik>[\w.-]+)/(?P<repo>[\w.-]+?)/"
    r"(?P<ref>[^/]+)/(?P<cesta>.+?)$", re.I)
_KRATKY_RE = re.compile(r"^(?P<vlastnik>[\w.-]+)/(?P<repo>[\w.-]+?)(?:/(?P<cesta>.+))?$")


def _rozloz_github(odkaz: str) -> tuple[str, str, str, str] | None:
    """Z odkazu vybere vlastníka, repozitář, větev a cestu k souboru."""
    odkaz = (odkaz or "").strip().rstrip("/")
    if not odkaz:
        return None
    nalez = _RAW_RE.search(odkaz)
    if nalez:
        return (nalez.group("vlastnik"), nalez.group("repo"), nalez.group("ref"),
                nalez.group("cesta"))
    nalez = _GITHUB_RE.search(odkaz)
    if not nalez:
        nalez = _KRATKY_RE.match(odkaz)
        if not nalez:
            return None
        return (nalez.group("vlastnik"), nalez.group("repo"), "", nalez.group("cesta") or "")
    return (nalez.group("vlastnik"), nalez.group("repo"), nalez.group("ref") or "",
            nalez.group("cesta") or "")


async def _stahni_github(vlastnik: str, rep: str, ref: str, cesta: str,
                         prima_adresa: str = "") -> object:
    """Stáhne JSON z raw.githubusercontent.com; zkusí i main/master a index souborů."""
    kandidati = [(ref, cesta)]
    if ref == "main":
        kandidati.append(("master", cesta))
    if not cesta:
        kandidati = [(r, c) for r, c in kandidati for c in ("ukoly.json", "tasks.json", "ulohy.json")]
    if prima_adresa:
        kandidati.insert(0, ("", ""))
    naposledy = None
    for poradi, (vetev, cesta_v) in enumerate(kandidati):
        adresa = prima_adresa if (poradi == 0 and prima_adresa) else \
            f"https://raw.githubusercontent.com/{vlastnik}/{rep}/{vetev}/{cesta_v}"
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
            odpoved = await client.get(adresa)
        if odpoved.status_code == 200:
            try:
                return odpoved.json()
            except ValueError:
                raise HTTPException(422, "na %s není platný JSON" % adresa)
        naposledy = "%s → HTTP %s" % (adresa, odpoved.status_code)
    raise HTTPException(422, "soubor s úlohami jsem nenašel (%s)" % naposledy)


_PREKLAD = {"title": "title", "nadpis": "title", "nazev": "title", "název": "title",
            "zadani": "zadani", "zadání": "zadani", "task": "zadani",
            "reseni": "reseni", "řešení": "reseni", "solution": "reseni",
            "check": "check", "kontrola": "check",
            "starter": "starter", "kostka": "starter", "kostra": "starter",
            "nacti": "nacti", "načti": "nacti",
            "dataset": "dataset", "id": "id", "note": "note",
            "lesson": "lesson", "lekce": "lesson", "lekce": "lesson",
            "minutes": "minutes", "minuty": "minutes", "minuty": "minutes",
            "level": "level", "obtiznost": "level", "obtížnost": "level"}


def _normalizuj_ulohu(polozka: dict, poradi: int, zdroj: str, kdo: str) -> dict | None:
    """Jedna položka ze souboru → záznam úlohy; tolerantní k českým i anglickým klíčům."""
    uloha = {}
    for klic, hodnota in polozka.items():
        cil = _PREKLAD.get(str(klic).strip().lower())
        if cil and hodnota not in (None, "", []):
            uloha[cil] = hodnota
    if not uloha.get("zadani") or not uloha.get("reseni"):
        return None
    if isinstance(uloha.get("zadani"), (list, tuple)):
        uloha["zadani"] = "\n".join(str(r) for r in uloha["zadani"])
    dovednosti = polozka.get("skills") or polozka.get("dovednosti") or []
    if isinstance(dovednosti, str):
        dovednosti = [d.strip() for d in dovednosti.split(",") if d.strip()]
    napovedy = polozka.get("hints") or polozka.get("napovedy") or polozka.get("nápovědy") or []
    if isinstance(napovedy, str):
        napovedy = [napovedy]
    cislo = lambda k, v: float(uloha.get(k) if str(uloha.get(k, "")).replace(".", "", 1).isdigit() else v)
    # id se odvozuje od posledního slova zdroje (název repa, nebo souboru) — ať je
    # krátké a stejné, když tenž soubor přenesu příště
    zaklad = re.sub(r"[^a-z0-9]+", "-", zdroj.lower().split(":")[-1].split("/")[-1])
    zaklad = re.sub(r"-+", "-", zaklad).strip("-")
    for privlastek in ("-json", "-csv"):
        zaklad = zaklad.removesuffix(privlastek)
    zaklad = zaklad[:18] or "uloha"
    return {
        "id": str(uloha.get("id") or ("%s-%02d" % (zaklad, poradi + 1)))[:40],
        "title": str(uloha.get("title") or uloha["zadani"][:60])[:120],
        "lesson": int(cislo("lesson", 0)), "minutes": int(cislo("minutes", 4)),
        "level": cislo("level", 2.0), "skills": list(dovednosti)[:6],
        "dataset": uloha.get("dataset"), "nacti": str(uloha.get("nacti") or ""),
        "zadani": str(uloha["zadani"]), "reseni": str(uloha["reseni"]),
        "check": str(uloha.get("check") or ""), "starter": str(uloha.get("starter") or ""),
        "hints": [str(h) for h in napovedy][:5], "status": "draft", "source": zdroj,
        "note": str(uloha.get("note") or "")[:400], "created": time.time(),
    }


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
        """Pohled na jednoho žáka: progres, dnešní dávka, poslední pokusy, jeho poznámky."""
        kdo, role = staff(request)
        users = ctx.ensure_users()
        if student not in users:
            raise HTTPException(404, "takový účet není")
        with ctx.db() as c:
            if role != "admin" and student not in _zaci_ucitele(c, kdo):
                raise HTTPException(403, "tenhle žák není ve tvé třídě")
            st = store.user_stats(c, student, days=min(days, 365))
            plan = c.execute("SELECT task_ids, minutes FROM plan WHERE day=? AND user=?",
                             (ctx.today(), student)).fetchone()
            st["plan_today"] = plan
            st["recent"] = [dict(r) for r in c.execute(
                "SELECT a.ts, a.task, t.title, a.ok, a.hints FROM attempts a "
                "LEFT JOIN tasks t ON t.id=a.task WHERE a.user=? ORDER BY a.ts DESC LIMIT 12",
                (student,))]
            # poznámky jsou soukromá poznámka žáka k úloze — učitel je vidí,
            # ale nemůže do nich sahat; pomáhá to najit špatné zadání
            st["poznamky"] = [dict(r) for r in c.execute(
                """SELECT f.ts, f.task, COALESCE(t.title, f.task) AS titulek, f.text
                     FROM feedback f LEFT JOIN tasks t ON t.id = f.task
                    WHERE f.user = ? AND f.kind = 'note'
                    ORDER BY f.ts DESC LIMIT 40""", (student,))]
            st["skoly"] = _skolni_prehled(c, student)
        return st

    def _zaci_ucitele(c, ucitel: str) -> list[str]:
        """Žáci, které učitel vede aspoň v jedné třídě."""
        return [r["student"] for r in c.execute(
            "SELECT DISTINCT cs.student FROM class_students cs JOIN classes cl ON cl.id=cs.class "
            "WHERE cl.teacher = ?", (ucitel,))]

    def _skolni_prehled(c, student: str) -> dict:
        """Co žák dluží: dnešní dávka versus co už stihl."""
        plan = c.execute("SELECT task_ids, minutes FROM plan WHERE day=? AND user=?",
                         (ctx.today(), student)).fetchone()
        hotovo = c.execute("SELECT COUNT(*) FROM attempts WHERE user=? AND ok=1 "
                           "AND date(ts,'unixepoch','localtime')=?",
                           (student, ctx.today())).fetchone()[0]
        try:
            ids = json.loads(plan["task_ids"]) if plan and plan["task_ids"] else []
        except (json.JSONDecodeError, TypeError):
            ids = []
        return {"nacteno": len(ids), "hotovo": hotovo,
                "plan_min": int(plan["minutes"]) if plan else 0}

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
        with ctx.db() as c:
            naposledy = {r["user"]: r["ts"] for r in c.execute(
                "SELECT user, MAX(ts) ts FROM attempts GROUP BY user")}
        return {"users": [{"user": k, "role": v.get("role", "student"),
                           "changed": v.get("changed"), "generated_pw": bool(v.get("first_pw")),
                           "prihlasen": v.get("last_login") or naposledy.get(k) or 0,
                           "uloh_vlastnich": 0}
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
        users[name] = {**users[name], "role": accounts.normalize_role(body.role),
                       "role_ruce": time.strftime("%Y-%m-%d %H:%M")}   # env už roli nesahne
        ctx._users_save(users)
        return {"ok": True, "user": name, "role": users[name]["role"]}

    @router.post("/api/users/{name}/logout")
    def api_user_logout(request: Request, name: str):
        """Odhlásí účet ze všech zařízení — hodí se po ztraceném notebooku."""
        is_admin(request)
        users = ctx.ensure_users()
        if name not in users:
            raise HTTPException(404, "účet nenalezen")
        ctx.posun_epochu(users, name)
        ctx._users_save(users)
        provozni_log("účet %s odhlášen ze všech zařízení" % name)
        return {"ok": True}

    @router.delete("/api/users/{name}")
    def api_user_delete(request: Request, name: str, potvrdit: str = ""):
        """Smaže účet i s jeho daty; chce jméno účtu jako potvrzení."""
        kdo = is_admin(request)
        if name == kdo:
            raise HTTPException(422, "sám sobě se nedáš smazat")
        users = ctx.ensure_users()
        if name not in users:
            raise HTTPException(404, "účet nenalezen")
        if (potvrdit or "").strip().lower() != name.lower():
            raise HTTPException(422, "pro smazání napiš jméno účtu %s" % name)
        del users[name]
        ctx._users_save(users)
        with ctx.db() as c:
            for tabulka, sloupec in (("attempts", "user"), ("skills", "user"), ("srs", "user"),
                                     ("plan", "user"), ("settings", "user"), ("feedback", "user"),
                                     ("dropped", "user"), ("class_students", "student")):
                c.execute(f"DELETE FROM {tabulka} WHERE {sloupec} = ?", (name,))
            c.execute("DELETE FROM classes WHERE teacher = ?", (name,))
        provozni_log("účet %s smazán %s" % (name, kdo))
        return {"ok": True, "user": name}

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
            # aby bylo vidět, zda se chodí přes bránu, nebo jen s heslem
            "sso": _prihlaseni_pro_ui(),
            # co je zrovna nasazený model — uživatel si ho nevolí
            "ai": _ai_pro_ui(),
            # limity pískoviště, aby bylo vidět, co kód smí
            "sandbox": await _limity_piskoviste(),
            # chybějící nebo osiřelé datové soubory
            "data": _kontrola_dat(c),
            # brzdění přihlašování po špatných pokusech
            "prihlasovani_zaraza": ctx.prihlaseni_stav(),
        }

    # -------------------------------------------------------------- třídy
    @router.get("/api/classes")
    def api_classes(request: Request):
        """Třídy, které vidí přihlášený; správce vidí všechny."""
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
            raise HTTPException(422, "třída potřebuje název")
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
                    raise HTTPException(404, "taková třída není")
                if stajici["teacher"] != kdo and role != "admin":
                    raise HTTPException(403, "tuhle třídu nevedeš")
                teacher = stajici["teacher"] if role != "admin" else (body.ucitel or stajici["teacher"])
            else:
                teacher = kdo
                identification = store.new_class_id(c)
            trida = store.save_class(c, identification, name, teacher, (body.poznamka or "").strip(), zaci)
        provozni_log("třída %s (%s) uložena %s, žáků %d" % (identification, name, kdo, len(zaci)))
        return {"ok": True, "trida": trida}

    @router.get("/api/classes/{identification}/export")
    def api_class_export(request: Request, identification: str, days: int = 90):
        """Výsledky třídy do CSV — každý žák a jeho hotové úlohy za období."""
        kdo, role = staff(request)
        with ctx.db() as c:
            trida = next((k for k in store.classes(c) if k["id"] == identification), None)
            if not trida:
                raise HTTPException(404, "taková třída není")
            if role != "admin" and trida["teacher"] != kdo:
                raise HTTPException(403, "tuhle třídu nevedeš")
            od = time.time() - max(1, min(int(days), 365)) * 86400
            radky = [dict(r) for r in c.execute(
                """SELECT cs.student,
                          COUNT(a.id)                                                   jako_pokusu,
                          COALESCE(SUM(a.ok), 0)                                        jako_uspechu,
                          COUNT(DISTINCT CASE WHEN a.ok = 1 THEN a.task END)            jako_uloh,
                          COALESCE(SUM(a.ms), 0) / 60000.0                              jako_minut,
                          MAX(a.ts)                                                     jako_posledni
                     FROM class_students cs
                     LEFT JOIN attempts a ON a.user = cs.student AND a.ts > ?
                    WHERE cs.class = ?
                    GROUP BY cs.student ORDER BY cs.student""", (od, identification))]
            hotove = {r["id"]: r for r in c.execute(
                "SELECT id, title, lesson FROM tasks WHERE status = 'approved'")}
        detail = []
        with ctx.db() as c:
            for r in radky:
                detail.append(c.execute(
                    "SELECT task FROM attempts WHERE user=? AND ok=1 AND ts>?",
                    (r["student"], od)).fetchall())

        def esc(h):
            text = str(h if h is not None else "")
            return '"' + text.replace('"', '""').replace("\n", " ") + '"'

        hlavicky = ["zak", "pokusy", "uspechy", "uloh_spolu", "minuty", "naposledy", "ulohy"]
        csv = [";".join(hlavicky)]
        for r, detaily in zip(radky, detail):
            posledni = r["jako_posledni"]
            csv.append(";".join([
                esc(r["student"]), esc(r["jako_pokusu"]), esc(r["jako_uspechu"]),
                esc(r["jako_uloh"]), esc(round(r["jako_minut"] or 0)),
                esc(time.strftime("%Y-%m-%d", time.localtime(posledni)) if posledni else ""),
                esc(" ".join(sorted(d["task"] for d in detaily)))]))
        from fastapi.responses import Response      # import zde, aby se nebral ze správcovské routy
        nazev = "".join(ch if ch.isalnum() else "-" for ch in trida["name"])[:40]
        return Response("\n".join(csv), media_type="text/csv; charset=utf-8",
                        headers={"content-disposition":
                                 f'attachment; filename="trida-{nazev}-{ctx.today()}.csv"'})

    @router.delete("/api/classes/{identification}")
    def api_class_delete(request: Request, identification: str):
        kdo, role = staff(request)
        with ctx.db() as c:
            stajici = next((k for k in store.classes(c) if k["id"] == identification), None)
            if not stajici:
                raise HTTPException(404, "taková třída není")
            if stajici["teacher"] != kdo and role != "admin":
                raise HTTPException(403, "tuhle třídu nevedeš")
            store.drop_class(c, identification)
        provozni_log("třída %s smazána %s" % (identification, kdo))
        return {"ok": True}

    async def _limity_piskoviste() -> dict:
        """Runner ke svym omezim pripojí — aplikace si je jen precte."""
        global _SANDBOX_CACHE
        if time.time() - _SANDBOX_CACHE[0] < 300:
            return _SANDBOX_CACHE[1]
        info = {"dostupne": False}
        try:
            async with httpx.AsyncClient(timeout=3.0) as klient:
                r = await klient.get(ctx.RUNNER.rstrip("/") + "/limits")
                if r.status_code == 200:
                    info = {**r.json(), "dostupne": True}
        except Exception as vyjimka:                      # noqa: BLE001
            info = {"dostupne": False, "duvod": vyjimka.__class__.__name__}
        _SANDBOX_CACHE = (time.time(), info)
        return info

    def _kontrola_dat(c) -> dict:
        """Úloha odkazuje na soubor, nebo soubor nikdo nepoužívá? Obojí je chyba."""
        from pathlib import Path as _P
        adresar = _P(_ADRESAR_DAT)
        soubory = {p.name for p in adresar.glob("*") if p.is_file()}
        pouzivane: dict[str, list[str]] = {}
        for r in c.execute("SELECT id, dataset FROM tasks WHERE dataset IS NOT NULL AND dataset != ''"):
            pouzivane.setdefault(r["dataset"], []).append(r["id"])
        chybi = [{"soubor": s, "ulohy": sorted(idy)[:6]} for s, idy in sorted(pouzivane.items())
                 if s not in soubory]
        osirele = sorted(soubory - set(pouzivane))
        return {"chybi": chybi, "osirele": osirele[:20], "souboru": len(soubory)}

    @router.get("/api/admin/datasets")
    def api_datasets_seznam(request: Request):
        """Co je v adresáři dat — i s velikostí, ať je vidět, co se nahraje."""
        staff(request)
        root = Path(_ADRESAR_DAT)
        soubory = [{"jmeno": p.name, "bytes": p.stat().st_size,
                    "upraveno": p.stat().st_mtime,
                    "pouziva": 0} for p in sorted(root.glob("*")) if p.is_file()]
        with ctx.db() as c:
            for t in c.execute("SELECT dataset, COUNT(*) n FROM tasks GROUP BY dataset").fetchall():
                for soubor in soubory:
                    if soubor["jmeno"] == t["dataset"]:
                        soubor["pouziva"] = t["n"]
        return {"ok": True, "soubory": soubory, "dovolene": list(_POVOLENE_PRIPONY)}

    @router.post("/api/datasets")
    def api_dataset_upload(request: Request, body: DatasetBody):
        """Nahraje CSV/TSV do banky dat; učitel ho pak napíše do pole dataset."""
        kdo, _ = staff(request)
        jmeno = _jmeno_souboru(body.jmeno)
        cesta_k = _cesta_k_datum(jmeno)
        if cesta_k.exists() and not body.prepsat:
            raise HTTPException(409, "%s už existuje — zaškrtni přepsat, nebo ho pojmenuj jinak" % jmeno)
        if len(body.data or "") > _MEZNIK_DAT:
            raise HTTPException(422, "soubor je moc velký — nejvíc je 4 MB")
        radky, sloupce = _prepis_csv(body.data, cesta_k)
        provozni_log("data %s nahrána %s (%d řádků)" % (jmeno, kdo, radky))
        return {"ok": True, "jmeno": jmeno, "radku": radky, "sloupce": sloupce}

    @router.delete("/api/datasets/{jmeno}")
    def api_dataset_delete(request: Request, jmeno: str):
        """Smaže soubor jen tehdy, když na něj žádná úloha neodkazuje."""
        kdo, _ = staff(request)
        jmeno = _jmeno_souboru(jmeno)
        cesta_k = _cesta_k_datum(jmeno)
        if not cesta_k.is_file():
            raise HTTPException(404, "takový soubor není")
        with ctx.db() as c:
            kde = [r["id"] for r in c.execute(
                "SELECT id FROM tasks WHERE dataset = ? LIMIT 5", (jmeno,)).fetchall()]
        if kde:
            raise HTTPException(409, "na %s se ještě odkazuje %s — nejdřív je přeřaď"
                                     % (jmeno, ", ".join(kde)))
        cesta_k.unlink()
        provozni_log("data %s smazána %s" % (jmeno, kdo))
        return {"ok": True}

    # --------------------------------------------------- přenos úloh dovnitř/ven
    async def _prenes_polozky(kdo, polozky, zdroj, odkud):
        """Přezkouší a uloží přenesené úlohy; co projde, je schváleno hned."""
        if not isinstance(polozky, list) or not polozky:
            raise HTTPException(422, "v souboru není seznam úloh — očekává se pole nebo "
                                     "{\"ukoly\": […]}")
        vysledky, schvaleno = [], 0
        for poradi, polozka in enumerate(polozky[:200]):
            if not isinstance(polozka, dict):
                continue
            uloha = _normalizuj_ulohu(polozka, poradi, zdroj, kdo)
            if not uloha:
                continue
            # kdyby JSON obsahoval i rovnou data, založí je do banky dat,
            # aby je ověření i žák našli pod stejným jménem jako v úloze
            _uloz_data(uloha.get("dataset"), polozka)
            if len(vysledky) < 8:                   # ať to u velké banky netrvá věčnost
                nacteno = await ctx.overeni_spustenim(uloha)
            else:
                nacteno = {"ok": False, "duvody": ["neověřeno — moc úloh najednou"]}
            uloha["status"] = "approved" if nacteno.get("ok") else "draft"
            uloha["note"] = ("přeneseno: %s, strojem ověřeno" % odkud if nacteno.get("ok")
                             else "přeneseno: %s — ke kontrole: %s"
                                  % (odkud, "; ".join(nacteno.get("duvody") or ["neověřeno"])))[:400]
            with ctx.db() as c:
                store.upsert_task(c, {**uloha, "check": uloha["check"]})
            if uloha["status"] == "approved":
                schvaleno += 1
            vysledky.append({"id": uloha["id"], "title": uloha["title"],
                             "status": uloha["status"]})
        provozni_log("%s %s: %s úloh (%s schváleno)" % (odkud, kdo, len(vysledky), schvaleno))
        return {"ok": True, "zdroj": zdroj, "pocet": len(vysledky),
                "schvaleno": schvaleno, "seznam": vysledky}

    @router.post("/api/tasks/import")
    async def api_tasks_import(request: Request, body: ImportBody):
        """Nahraje banku úloh ze souboru, který člověk vybere v prohlížeči."""
        kdo, _ = staff(request)
        text = (body.data or "").strip()
        if not text:
            raise HTTPException(422, "soubor je prázdný")
        if len(text) > 900_000:
            raise HTTPException(422, "soubor je moc velký — nejvíc je 900 kB")
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise HTTPException(422, "v %s není platný JSON: %s" % (body.jmeno, exc))
        polozky = data if isinstance(data, list) else (data.get("ukoly") or data.get("tasks") or [])
        return await _prenes_polozky(kdo, polozky, "soubor:%s" % body.jmeno, "ze souboru")

    @router.get("/api/tasks/export")
    def api_tasks_export(request: Request, status: str = "", lesson: int = -1,
                         q: str = "", zdroj: str = "", ids: str = "", daty: bool = False):
        """Banka ven do stejného formátu, jakým se umí vrátit zpátky.

        Filtrovat lze statusem, lekcí, výskytem řetězce, zdrojem nebo výčtem id —
        aby šlo exportovat všechno, jen co zrovna vidím, nebo vybrané úlohy.
        """
        staff(request)
        vybrane = {x.strip() for x in ids.split(",") if x.strip()}
        with ctx.db() as c:
            rows = ctx.tasks_all(c) if hasattr(ctx, "tasks_all") else [
                store.row_to_task(r) for r in
                c.execute("SELECT * FROM tasks ORDER BY lesson, id").fetchall()]
        vybrano = []
        for t in rows:
            if status and t.get("status") != status:
                continue
            if lesson >= 0 and int(t.get("lesson") or 0) != lesson:
                continue
            if zdroj and not (t.get("source") or "").startswith(zdroj):
                continue
            if q:
                hledane = ("%s %s" % (t.get("title", ""), t.get("zadani", ""))).lower()
                if q.lower() not in hledane:
                    continue
            if vybrane and t["id"] not in vybrane:
                continue
            vybrano.append({
                "id": t["id"], "title": t.get("title", ""), "lesson": t.get("lesson", 0),
                "minutes": t.get("minutes", 4), "level": t.get("level", 1),
                "skills": t.get("skills") or [], "dataset": t.get("dataset"),
                "nacti": t.get("nacti") or "", "starter": t.get("starter") or "",
                "zadani": t.get("zadani", ""), "reseni": t.get("reseni") or "",
                "check": t.get("check") or t.get("check_r") or "",
                "hints": t.get("hints") or [], "status": t.get("status", "approved"),
            })
            if daty and vybrano[-1]["dataset"]:
                soubor = Path(_ADRESAR_DAT) / str(vybrano[-1]["dataset"])
                if soubor.is_file() and soubor.stat().st_size <= 400_000:
                    try:
                        radky = list(csv.DictReader(io.StringIO(
                            soubor.read_text(encoding="utf-8", errors="replace"))))
                        vybrano[-1]["data"] = radky[:1000]
                    except OSError:
                        pass
        return {"ok": True, "pocet": len(vybrano), "ukoly": vybrano}

    # --------------------------------------------- úloha pod drobnohledem (vyučující)
    @router.get("/api/tasks/{task_id}")
    def api_task_detail(request: Request, task_id: str):
        """Jedna úloha i s řešením a kontrolou — aby šla otevřít v editoru."""
        staff(request)
        with ctx.db() as c:
            ukol = ctx.get_task(c, task_id)
        if not ukol:
            raise HTTPException(404, "úloha není")
        return ukol

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

    @router.post("/api/tasks/{task_id}/autofix")
    async def api_task_autofix(request: Request, task_id: str):
        """Nech model úlohu přepsat, až projde strojovým ověřením."""
        kdo, _ = staff(request)
        with ctx.db() as c:
            r = c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            t = store.row_to_task(r) if r else None
        if not t:
            raise HTTPException(404, "úloha neexistuje")
        nacteno = await ctx.overeni_spustenim(t)
        if nacteno["ok"]:
            return {"ok": True, "status": t.get("status"), "opraveno": False,
                    "zprava": "úloha už ověřením prochází", "detail": nacteno}
        navrhy = await ai.fix_task(t, nacteno)
        if navrhy.get("chyba"):
            return {"ok": False, "opraveno": False, "zprava": navrhy["chyba"], "detail": nacteno}
        opravena = {**t}
        for údaj in ("reseni", "check", "zadani", "starter", "nacti"):
            if navrhy.get(údaj):
                opravena[údaj] = navrhy[údaj]
        overeno = await ctx.overeni_spustenim(opravena)
        opravena["status"] = "approved" if overeno["ok"] else "draft"
        opravena["note"] = (("opraveno modelem: " if overeno["ok"] else "model ještě neprošlo: ")
                            + (navrhy.get("duvod") or ""))[:400]
        with ctx.db() as c:
            store.upsert_task(c, {**opravena, "check": opravena["check"]})
        provozni_log("úloha %s opravována modelem (podnět %s) → %s" % (task_id, kdo, opravena["status"]))
        return {"ok": overeno["ok"], "opraveno": True, "status": opravena["status"],
                "zprava": navrhy.get("duvod") or "", "detail": overeno, "uloha": opravena}

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

    # ------------------------------------------------------ banka úloh z GitHubu
    @router.post("/api/github/import")
    async def api_github_import(request: Request, body: GithubBody):
        """Načte soubor s úlohami z repozitáře učitele a založí je jako koncepty.

        Přebírá se `ukoly.json` (nebo to, na co ukáže odkaz); položky smí být
        česky i anglicky popsané. Každá se přezkouší spuštěním — co projde, je
        hned schváleno, zbytek zůstává přečtení člověkem.
        """
        kdo, _ = staff(request)
        uvnitř = _rozloz_github(body.odkaz)
        if not uvnitř:
            raise HTTPException(422, "tomu odkazu rozumím jako https://github.com/vlastnik/repo "
                                     "nebo vlastnik/repo/soubor.json")
        vlastnik, rep, ref, cesta = uvnitř
        prima = body.odkaz.strip() if "githubusercontent.com/" in body.odkaz.lower() else ""
        data = await _stahni_github(vlastnik, rep, ref or body.ref or "main", cesta, prima)
        polozky = data if isinstance(data, list) else (data.get("ukoly") or data.get("tasks") or [])
        return await _prenes_polozky(kdo, polozky, f"github:{vlastnik}/{rep}",
                                     "z GitHubu %s" % (cesta or "výchozí soubor"))

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
