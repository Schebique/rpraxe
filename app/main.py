"""rpraxe — hlavní aplikace (FastAPI).

Cizí závislosti: fastapi, uvicorn, httpx. Data: SQLite v /data/state.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import accounts, config as instance, adaptive, ai, store, syllabus

WEB = Path(os.environ.get("RPRAXE_WEB", "/srv/web"))
USERS_FILE = Path(os.environ.get("RPRAXE_USERS", "/data/state/users.json"))
SECRET_FILE = Path(os.environ.get("RPRAXE_SECRET", "/data/state/secret.key"))
RUNNER = os.environ.get("RPRAXE_RUNNER", "http://rpraxe-runner:8081")
USER = os.environ.get("RPRAXE_USER", "lenka")
SSO_SECRET_HEADER = "x-rpraxe-sso"

app = FastAPI(title="rpraxe", docs_url=None, redoc_url=None)
VERSION = os.environ.get("RPRAXE_VERSION", "0.2.0")

# ------------------------------------------------------------------ auth ---


def secret() -> bytes:
    if not SECRET_FILE.exists():
        SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
        SECRET_FILE.write_bytes(secrets.token_bytes(32))
        SECRET_FILE.chmod(0o600)
    return SECRET_FILE.read_bytes()


def hash_pw(pw: str) -> str:
    return accounts.hash_pw(pw)


def check_pw(pw: str, stored: str) -> bool:
    return accounts.check_pw(pw, stored)


def ensure_users() -> dict:
    users = accounts.load(USERS_FILE)
    changed = False
    generated = accounts.seed_from_env(users)
    for name in generated:
        print(f"[rpraxe] účet {name}: heslo vygenerováno do {USERS_FILE} (klíč first_pw), "
              f"nebo nastav {('RPRAXE_PASS_' + name.upper())}", flush=True)
    if changed or not USERS_FILE.exists():
        accounts.save(USERS_FILE, users)
    return users


def make_token(user: str) -> str:
    exp = int(time.time()) + 30 * 86400
    payload = f"{user}.{exp}"
    sig = hmac.new(secret(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}.{sig}"


def read_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        user, exp, sig = token.split(".")
    except ValueError:
        return None
    payload = f"{user}.{exp}"
    good = hmac.new(secret(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, good) or int(exp) < time.time():
        return None
    return user


def current_user(request: Request) -> str | None:
    return read_token(request.cookies.get("rpraxe"))


LOGIN_PAGE = """<!doctype html><html lang="cs"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>přihlášení — R v ruce</title><link rel="stylesheet" href="/static/style.css"></head>
<body class="login"><form method="post" action="/login" class="card">
<h1>R v ruce</h1><p class="muted">Denních 15–30 minut R, přesně na míru.</p>
<label>jméno<input name="user" autocomplete="username" value="{user}"></label>
<label>heslo<input name="pass" type="password" autocomplete="current-password"></label>
{err}<button class="primary">přihlásit</button>{sso}
<p class="tiny muted">běží doma na serveru, přístupné jen z domácí sítě a přes Tailscale</p>
</form></body></html>"""


@app.get("/login")
def login_page(request: Request):
    """Po odhlášení sem přiletí 303 z /logout — bez toho by prohlížeč ukázal 405."""
    if current_user(request):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(LOGIN_PAGE.format(user="", err="", sso=sso_button()))


@app.post("/login")
def login(response: Response, user: str = Form(...), pas: str = Form("", alias="pass")):
    users = ensure_users()
    rec = users.get(user.lower().strip())
    if not rec or not check_pw(pas, rec["hash"]):
        return HTMLResponse(LOGIN_PAGE.format(user=user, err='<p class="err">nesedí heslo</p>',
                                              sso=sso_button()), status_code=401)
    name = user.lower().strip()
    if accounts.pw_is_legacy(rec["hash"]):        # nový algoritmus, až uživatel zadá heslo
        users[name] = {**rec, "hash": hash_pw(pas)}
        _users_save(users)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("rpraxe", make_token(name), httponly=True, samesite="lax",
                    max_age=30 * 86400, secure=request_is_https())
    return resp


_REQ_IS_HTTPS = {"v": False}

def sso_zapnuto() -> bool:
    """SSO platí, jen když je zapnuté a má tajemství — jinak by stačil cizí header."""
    return instance.sso_zapnuto() or bool(
        os.environ.get("RPRAXE_SSO_SECRET") and os.environ.get("RPRAXE_SSO_HEADER"))


def sso_cfg() -> dict:
    cfg = instance.sso_cfg()
    if not cfg.get("tajemstvi"):
        cfg["tajemstvi"] = os.environ.get("RPRAXE_SSO_SECRET", "")
    if not (cfg.get("hlavka_jmeno") or "").strip():
        cfg["hlavka_jmeno"] = os.environ.get("RPRAXE_SSO_HEADER", "Remote-User")
    if not (cfg.get("hlavka_role") or "").strip():
        cfg["hlavka_role"] = os.environ.get("RPRAXE_SSO_ROLE_HEADER", "")
    return cfg


def sso_button() -> str:
    if not sso_zapnuto():
        return ""
    return ('<p class="tiny muted">nebo</p><button class="ghost" formaction="/login/sso">'
            'přihlásit účtem instituce</button>')


def role_z_skupin(skupiny: str, mapa: dict | None = None) -> str:
    """Skupiny z brány -> role. Vlastní mapování má přednost před výčtem zvyklostí."""
    d = (skupiny or "").lower()
    for skupina, role in (mapa or {}).items():
        role = str(role or "").strip().lower()
        if role in ("admin", "teacher", "student") and str(skupina).lower() in d:
            return role
    if "admin" in d:
        return "admin"
    if any(g in d for g in ("teacher", "lektor", "ucitel", "skola", "vyucujici")):
        return "teacher"
    return "student"


def sso_login(request: Request) -> str | None:
    """Přihlášení přes bránu: jméno z headeru + sdílené tajemství.

    Bez tajemství header ignorujeme — klient by si jméno vymyslel sám. Brána posílá
    `header_up Remote-User <přihlášený>` a `header_up X-Rpraxe-SSO <tajemství>`.
    """
    cfg = sso_cfg()
    tajemstvi = str(cfg.get("tajemstvi") or "").strip()
    hlavka = str(cfg.get("hlavka_jmeno") or "").strip()
    if not tajemstvi or not hlavka or not sso_zapnuto():
        return None
    if not hmac.compare_digest(request.headers.get(SSO_SECRET_HEADER, ""), tajemstvi):
        return None
    uzivatel = (request.headers.get(hlavka) or "").strip().lower()
    if not uzivatel:
        return None
    povoleni = [str(x).lower() for x in (cfg.get("povolene_ucety") or [])]
    if povoleni and uzivatel not in povoleni:
        print(f"[rpraxe] SSO: {uzivatel} není na seznamu povolených účtů", flush=True)
        return None
    role = role_z_skupin(request.headers.get(cfg.get("hlavka_role") or "", ""),
                         cfg.get("role_z_skupin") or {})
    uzivatele = ensure_users()
    if uzivatel not in uzivatele:
        uzivatele[uzivatel] = {"hash": hash_pw(secrets.token_urlsafe(12)), "role": role,
                               "created": time.time(), "sso": True}
        accounts.save(USERS_FILE, uzivatele)
        print(f"[rpraxe] SSO: založen účet {uzivatel} ({role})", flush=True)
    elif uzivatele[uzivatel].get("role") != role and role != "student":
        uzivatele[uzivatel]["role"] = role
        accounts.save(USERS_FILE, uzivatele)
    return uzivatel


def sso_sonda(request: Request) -> dict:
    """Co od brány přišlo — pro klávesnici správy, když se nikdo nepřihlásí."""
    cfg = sso_cfg()
    jmena = {k.lower(): (k, v[:40]) for k, v in request.headers.items()}
    tajan = request.headers.get(SSO_SECRET_HEADER, "")
    return {
        "hlavka_jmeno": cfg.get("hlavka_jmeno"),
        "jmeno_prichazi": bool(jmena.get((cfg.get("hlavka_jmeno") or "").lower())),
        "hlavka_role": cfg.get("hlavka_role"),
        "role_prichazi": bool((cfg.get("hlavka_role") or "") and jmena.get(cfg["hlavka_role"].lower())),
        "tajemstvi_prichazi": bool(tajan),
        "tajemstvi_sedi": bool(tajan and hmac.compare_digest(tajan, str(cfg.get("tajemstvi") or ""))),
        # hlavičky, které by mohl poslat sám klient a mohly by matet — běžný
        # User-Agent mezi to nepatří, ať to v kartě nevystraší
        "podezrele_havicky": sorted(k for k, _ in jmena.values()
                                    if k != "user-agent"
                                    and any(s in k for s in ("user", "mail", "group", "role", "auth"))),
    }


@app.get("/login/sso")
@app.post("/login/sso")
def login_sso(request: Request):
    user = sso_login(request)
    if not user:
        return HTMLResponse(LOGIN_PAGE.format(user="", err='<p class="err">přihlášení přes bránu '
                            "se nepovedlo — chybí tajemstvo?</p>", sso=""), status_code=401)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("rpraxe", make_token(user), httponly=True, samesite="lax",
                    max_age=30 * 86400, secure=request_is_https())
    return resp





def request_is_https() -> bool:
    return _REQ_IS_HTTPS["v"]


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    _REQ_IS_HTTPS["v"] = request.headers.get("x-forwarded-proto", "http") == "https"
    path = request.url.path
    if path.startswith("/static") or path == "/login" or path == "/healthz":
        return await call_next(request)
    if not current_user(request):
        if path.startswith("/api/"):
            return JSONResponse({"error": "nepřihlášen"}, status_code=401)
        return HTMLResponse(LOGIN_PAGE.format(user="", err="", sso=sso_button()))
    return await call_next(request)


# -------------------------------------------------------------- helpers ----

def db() -> sqlite3.Connection:
    return store.conn()


def today() -> str:
    return date.today().isoformat()


def load_banks() -> int:
    """Načte banky úloh z Python modulů v /srv/tasks do databáze."""
    import importlib
    import sys

    sys.path.insert(0, os.environ.get("RPRAXE_TASKS", "/srv/tasks"))
    n = 0
    with db() as c:
        for f in sorted(Path(os.environ.get("RPRAXE_TASKS", "/srv/tasks")).glob("*.py")):
            if f.name.startswith("_"):
                continue
            mod = importlib.import_module(f.stem)
            for t in getattr(mod, "TASKS", []):
                t.setdefault("source", "bank")
                for k in ("check", "reseni", "zadani", "starter", "nacti", "title"):
                    if isinstance(t.get(k), tuple):      # chybička v bance: 'a' 'b', 'c' → tuple
                        t[k] = "\n".join(str(x) for x in t[k])
                        print(f"[rpraxe] pozor {t.get('id')}: pole {k} je tuple, slepeno", flush=True)
                store.upsert_task(c, t)
                n += 1
                for s in t.get("skills") or []:
                    c.execute("INSERT OR IGNORE INTO skill_labels(key,label,lesson) VALUES(?,?,?)",
                              (s, s, int(t.get("lesson") or 0)))
    return n


def tasks_all(c: sqlite3.Connection) -> list[dict]:
    rows = c.execute("SELECT * FROM tasks WHERE status != 'retired'").fetchall()
    return [store.row_to_task(r) for r in rows]


def get_task(c: sqlite3.Connection, tid: str) -> dict | None:
    r = c.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
    return store.row_to_task(r) if r else None


BACKUP_DIR = Path(os.environ.get("RPRAXE_BACKUP_DIR", "/data/state/backups"))
INFO_FILE = Path(os.environ.get("RPRAXE_BACKUP_INFO", "/data/state/zaloha.json"))


def backup_status() -> dict:
    """Co je vidět z kontejneru: lokální snímky DB + hláška z noční zálohy na NAS."""
    snaps = []
    if BACKUP_DIR.exists():
        for f in sorted(BACKUP_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
            snaps.append({"name": f.name, "bytes": f.stat().st_size,
                          "mtime": f.stat().st_mtime})
    info = {}
    if INFO_FILE.exists():
        try:
            info = json.loads(INFO_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            info = {}
    return {"local": snaps, "last": info}


def new_task_id(c: sqlite3.Connection, prefix: str = "uc") -> str:
    n = c.execute("SELECT COUNT(*) FROM tasks WHERE id LIKE ?", (f"{prefix}-%",)).fetchone()[0]
    while True:
        n += 1
        cand = f"{prefix}-{n:02d}"
        if not c.execute("SELECT 1 FROM tasks WHERE id=?", (cand,)).fetchone():
            return cand


def is_admin(user: str) -> bool:
    return ensure_users().get(user, {}).get("role") == "admin"


def datasets() -> list[str]:
    d = Path(os.environ.get("RPRAXE_DATASETS", "/data/datasets"))
    return sorted(p.name for p in d.glob("*") if p.is_file())


def task_lessons() -> dict:
    return syllabus.LESSONS


@app.on_event("startup")
def startup():
    store.init()
    ensure_users()
    n = load_banks()
    print(f"[rpraxe] načteno {n} úloh", flush=True)


# ------------------------------------------------------------------ web ----


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")


from app import manage as manage_api   # až na konci — potřebuje hotové helpery


manage_api.register(app, sys.modules[__name__])


@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": time.time()}


# ------------------------------------------------------------------ API ----

class RunBody(BaseModel):
    task_id: str | None = None
    code: str
    check: bool = False
    elapsed_ms: int | None = None


@app.get("/api/bootstrap")
def bootstrap(request: Request):
    user = current_user(request) or USER
    with db() as c:
        plan = ensure_plan(c, user)
        stats = adaptive.daily_stats(c, user, today())
        streak = adaptive.streak(c, user)
        lessons = task_lessons()
        focus = syllabus.lesson_focus()
        cur = syllabus.current_lesson()
        pref = store.prefs(c, user)
    role = ensure_users().get(user, {}).get("role", "student")
    note = ""
    p = Path(os.environ.get("RPRAXE_AGENT_NOTE", "/data/state/agent_posled.txt"))
    if p.exists():
        note = p.read_text(encoding="utf-8").strip()
    return {
        "user": user, "day": today(), "streak": streak, "today": stats, "agent_note": note,
        "lesson_current": cur, "lesson_title": lessons[cur]["title"],
        "focus": focus, "items": plan,
        "budget": int(pref["val"]), "role": role,
        "theme": pref["theme"], "lang": pref["lang"], "model": pref["model"],
    }


def minutes_budget(c: sqlite3.Connection, user: str) -> int:
    return int(store.prefs(c, user)["val"])


@app.get("/api/plan")
def api_plan(request: Request, minutes: int | None = None, refresh: int = 0):
    user = current_user(request) or USER
    with db() as c:
        if minutes:
            store.set_prefs(c, user, val=int(minutes))
        if refresh:
            c.execute("DELETE FROM plan WHERE day = ? AND user = ?", (today(), user))
        items = ensure_plan(c, user)
    return {"items": items, "budget": minutes_budget(c, user)}


def ensure_plan(c: sqlite3.Connection, user: str) -> list[dict]:
    row = c.execute("SELECT task_ids, minutes FROM plan WHERE day = ? AND user = ?", (today(), user)).fetchone()
    # do dávky patří jen schválené úlohy, které si člověk osobně nezahodil
    odlozeno = store.dropped_for(c, user)
    tasks = [t for t in tasks_all(c) if t.get("status") == "approved" and t["id"] not in odlozeno]
    budget = minutes_budget(c, user)
    if row:
        ids = json.loads(row["task_ids"])
        done = {r["task"] for r in c.execute(
            "SELECT task FROM attempts WHERE user=? AND ok=1 AND date(ts,'unixepoch','localtime')=?",
            (user, today()))}
        items = []
        for tid in ids:
            if tid in odlozeno:
                continue
            t = get_task(c, tid)
            if not t or t.get("status") != "approved":
                continue
            t["solved"] = tid in done
            t.pop("check_r", None); t.pop("reseni", None)
            items.append(t)
        if len(items) >= 2:
            return items
    skills = adaptive.skill_snapshot(c, user)
    srs = adaptive.srs_snapshot(c, user)
    tried = {r["task"] for r in c.execute(
        "SELECT DISTINCT task FROM attempts WHERE user = ? AND ts > ?", (user, time.time() - 30 * 86400))}
    picks = adaptive.plan_session(tasks, skills, srs, minutes=budget,
                                  done_ids=sorted(tried), focus_skills=syllabus.lesson_focus())
    ids = [p.task["id"] for p in picks]
    why = {p.task["id"]: p.why for p in picks}
    c.execute("INSERT INTO plan(day,user,task_ids,minutes,created) VALUES(?,?,?,?,?) "
              "ON CONFLICT(day,user) DO UPDATE SET task_ids=excluded.task_ids, minutes=excluded.minutes",
              (today(), user, json.dumps(ids), budget, time.time()))
    out = []
    for p in picks:
        t = dict(p.task)
        t["why"] = p.why
        t["solved"] = False
        t.pop("check_r", None); t.pop("reseni", None)
        out.append(t)
    return out


class PickBody(BaseModel):
    task_id: str


@app.post("/api/pick")
def api_pick(request: Request, body: PickBody):
    """Přidat libovolnou úlohu do dnešní dávky."""
    user = current_user(request) or USER
    with db() as c:
        t = get_task(c, body.task_id)
        if not t:
            raise HTTPException(404, "neznámá úloha")
        row = c.execute("SELECT task_ids FROM plan WHERE day=? AND user=?", (today(), user)).fetchone()
        ids = json.loads(row["task_ids"]) if row else []
        if t["id"] not in ids:
            ids.append(t["id"])
            c.execute("INSERT INTO plan(day,user,task_ids,minutes,created) VALUES(?,?,?,?,?) "
                      "ON CONFLICT(day,user) DO UPDATE SET task_ids=excluded.task_ids",
                      (today(), user, json.dumps(ids), minutes_budget(c, user), time.time()))
        t.pop("check_r", None); t.pop("reseni", None)
        return t


class DropBody(BaseModel):
    task_id: str
    obnovit: bool = False


@app.post("/api/drop")
def api_drop(request: Request, body: DropBody):
    """Žák si úlohu osobně zahodí — nebo zas obnoví. Banky se to nedotkne."""
    user = current_user(request) or USER
    with db() as c:
        if not c.execute("SELECT 1 FROM tasks WHERE id = ?", (body.task_id,)).fetchone():
            raise HTTPException(404, "neznámá úloha")
        store.set_dropped(c, user, body.task_id, not body.obnovit)
        # ze dnešní dávky zmizí hned, jinak by ji člověk viděl dál
        radka = c.execute("SELECT task_ids FROM plan WHERE day=? AND user=?", (today(), user)).fetchone()
        if radka and not body.obnovit:
            ids = [i for i in json.loads(radka["task_ids"]) if i != body.task_id]
            c.execute("UPDATE plan SET task_ids=? WHERE day=? AND user=?",
                      (json.dumps(ids), today(), user))
    return {"ok": True, "zahozeno": not body.obnovit}


class OwnBody(BaseModel):
    """To, co žák u své úlohy smí měnit. Hodnoty dál neprojdou bez ověření."""
    id: str | None = None
    title: str = ""
    zadani: str
    reseni: str = ""
    check: str = ""
    starter: str = ""
    nacti: str = ""
    dataset: str | None = None
    hints: list[str] = []
    minutes: int = 4
    lesson: int = 0
    level: float = 2.0
    skills: list[str] = []


@app.post("/api/own")
async def api_own(request: Request, body: OwnBody):
    """Žák sepíše nebo upraví vlastní úlohu. Než se ukáže světu, musí projít spuštěním."""
    user = current_user(request) or USER
    if not body.zadani.strip():
        raise HTTPException(422, "bez zadání z toho úloha nevznikne")
    if not body.reseni.strip():
        raise HTTPException(422, "přilož i řešení — bez něj to nemůžeme ověřit")
    with db() as c:
        exist = get_task(c, body.id) if body.id else None
    # žáh nezasáhne do cizích věcí — měnit smí jen to, co samo vytvořilo
    if body.id and not exist:
        raise HTTPException(403, "takovou úlohu nemůžeš přepisovat")
    if exist and (exist.get("owner") or "") != user:
        raise HTTPException(403, "tohle není tvoje úloha — upravit ji může jen ten, kdo ji napsal")
    if body.dataset and body.dataset not in datasets():
        raise HTTPException(422, "soubor %s v bance dat není — nejdřív ho nahraj" % body.dataset)
    klice = re.sub(r"[^a-z0-9]+", "-", user.lower()).strip("-")[:10]
    uloha = {
        "id": body.id or ("zak-%s-%x" % (klice or "zak", int(time.time()) & 0xffff)),
        "title": (body.title or body.zadani)[:60].strip(),
        "lesson": int(body.lesson or 0), "minutes": max(1, min(int(body.minutes or 4), 30)),
        "level": max(1.0, min(float(body.level or 2.0), 4.5)),
        "skills": [str(s)[:24] for s in (body.skills or [])][:6],
        "dataset": body.dataset, "nacti": body.nacti or "", "starter": body.starter or "",
        "zadani": body.zadani, "check": body.check or "FALSE", "reseni": body.reseni,
        "hints": [str(h)[:400] for h in (body.hints or [])][:5],
        "status": "draft", "source": "vlastni", "owner": user, "note": "",
    }
    if not uloha["dataset"]:
        uloha["nacti"] = ""
    prezkous = await validate_task(uloha)
    uloha["status"] = "approved" if prezkous["ok"] else "draft"
    uloha["note"] = ("vlastní úloha — ověřeno spuštěním" if prezkous["ok"]
                     else "vlastní úloha ke kontrole: " + str(prezkous.get("msg", ""))[:300])
    with db() as c:
        store.upsert_task(c, uloha)
    return {"ok": prezkous["ok"], "ulozeno": True, "id": uloha["id"], "status": uloha["status"],
            "zprava": uloha["note"]}


# Knihovny se počítají na minutu: zavření dplyr+ggplot2+… stojí ~2,5 s navíc
# na každý běh, proto se tažej jen ty, které úloha nebo kód skutečně volá.
VSECHNY_KNIHOVNY = {"dplyr", "tidyr", "ggplot2", "readr", "forcats", "lubridate"}
POZNANI_KNIHOVEN = [
    ("dplyr", r"%>|\b(group_by|ungroup|summarise|summarize|mutate|transmute|filter|select|rename|"
               r"arrange|distinct|slice|left_join|inner_join|right_join|full_join|bind_rows|bind_cols|"
               r"pull|recode|case_when|if_else|n\(\)|everything\(\)|across|near)\b"),
    ("ggplot2", r"\bggplot\s*\(|\baes\s*\(|\bgeom_[a-z_]+\s*\(|\bfacet_|\btheme_|\bscale_[a-z_]+\s*\(|\blabs\s*\("),
    ("readr", r"\bread_(csv|delim|table2|log|lines)\s*\(|\bwrite_(csv|lines|delim)\s*\("),
    ("lubridate", r"\b(ymd|mdy|dmy|ymd_hms|as_datetime|floor_date|ceiling_date|int_year|int_month|"
                  r"wday|quarter|days\s*\(|hours\s*\(|months\s*\(|years\s*\()\s*\("),
    ("tidyr", r"\b(pivot_longer|pivot_wider|separate|separate_rows|unite|nest|unnest|fill|drop_na|replace_na)\s*\("),
    ("forcats", r"\b(fct_relevel|fct_reorder|fct_infreq|fct_rev|fct_lump|fct_collapse|fct_explicit_na)\s*\("),
]


def odhad_knihovny(text: str) -> list[str]:
    found = [nazev for nazev, vzor in POZNANI_KNIHOVEN if re.search(vzor, text or "")]
    return found


def libraries_for(task: dict | None, code: str) -> list[str]:
    """Co spustit před kódem: declared > odhad z kódu + kontroly + načtení dat."""
    if task and task.get("libraries"):
        return [l for l in task["libraries"] if l in VSECHNY_KNIHOVNY] or ["dplyr"]
    text = "\n".join([code or "", (task or {}).get("check_r") or "", (task or {}).get("nacti") or ""])
    return odhad_knihovny(text)


def chybi_knihovna(out: dict) -> bool:
    hlaska = " ".join(str(out.get(k) or "") for k in ("error", "stderr"))
    return bool(re.search(r"could not find function|no applicable method|there is no package called|"
                          r"Objects of class .* cannot be subset|function .* not found", hlaska))


@app.post("/api/run")
async def api_run(request: Request, body: RunBody):
    """Spustí kód v runneru. Při check=True vyhodnotí i kontrolu a zapíše pokus."""
    user = current_user(request) or USER
    payload = {"code": body.code, "plots": True}  # knižovny doplníme níž
    task = None
    with db() as c:
        if body.task_id:
            task = get_task(c, body.task_id)
    if task:
        if task.get("dataset"):
            payload["datasets"] = [task["dataset"]]
        if task.get("nacti"):
            payload["code"] = task["nacti"] + "\n" + body.code
        if body.check and task.get("check_r"):
            payload["check"] = task["check_r"]
    else:
        payload["code"] = body.code
        payload["datasets"] = datasets()

    payload["libraries"] = libraries_for(task, body.code)

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(f"{RUNNER}/run", json=payload)
        r.raise_for_status()
        out = r.json()
        # nejistota v odhadu knihoven nesmí skončit jako „nefunguje to“:
        # jestli R hlásí neznámou funkci, zkusíme jednou vše a teprve pak hlásíme chybu
        if chybi_knihovna(out) and set(payload["libraries"]) != VSECHNY_KNIHOVNY:
            payload["libraries"] = sorted(VSECHNY_KNIHOVNY)
            r = await client.post(f"{RUNNER}/run", json=payload)
            r.raise_for_status()
            out = r.json()

    ok = None
    if body.check and isinstance(out.get("check"), dict):
        ok = bool(out["check"].get("pass"))
    if body.check and task:
        with db() as c:
            grade_and_record(c, user, task, ok, out, body.code, body.elapsed_ms)
            out["progress"] = adaptive.daily_stats(c, user, today())
            out["streak"] = adaptive.streak(c, user)
            out["next"] = suggest_next(c, user)
    return out


def grade_and_record(c: sqlite3.Connection, user: str, task: dict, ok: bool | None, out: dict, code: str,
                   elapsed_ms: int | None = None) -> None:
    key = f"hints:{user}:{task['id']}:{today()}"
    row = c.execute("SELECT val FROM ai_cache WHERE key=?", (key,)).fetchone()
    hints_used = int(row["val"]) if row else 0
    first = c.execute("SELECT COUNT(*) n FROM attempts WHERE user=? AND task=?", (user, task["id"])).fetchone()["n"] == 0
    q = adaptive.quality(bool(ok), hints_used, first)
    # Elo: student per skill, task level
    for s in task.get("skills") or []:
        row = c.execute("SELECT theta, n FROM skills WHERE key=? AND user=?", (s, user)).fetchone()
        theta = row["theta"] if row else 1.6
        n = row["n"] if row else 0
        new_theta, new_n = adaptive.update_theta(theta, float(task["level"]), q, n)
        c.execute("INSERT INTO skills(key,user,theta,n) VALUES(?,?,?,?) "
                  "ON CONFLICT(key,user) DO UPDATE SET theta=excluded.theta, n=excluded.n",
                  (s, user, new_theta, new_n))
        c.execute("INSERT OR IGNORE INTO skill_labels(key,label,lesson) VALUES(?,?,?)",
                  (s, s, int(task.get("lesson") or 0)))
    new_level = adaptive.update_level(float(task["level"]), q)
    c.execute("UPDATE tasks SET level = ? WHERE id = ?", (new_level, task["id"]))
    sr = c.execute("SELECT ease, reps, lapses FROM srs WHERE task=? AND user=?", (task["id"], user)).fetchone()
    interval, ease, reps, lapses = adaptive.srs_next(sr["ease"] if sr else 2.3,
                                                     sr["reps"] if sr else 0,
                                                     sr["lapses"] if sr else 0, q)
    c.execute("INSERT INTO srs(task,user,due,ease,reps,lapses,last) VALUES(?,?,?,?,?,?,?) "
              "ON CONFLICT(task,user) DO UPDATE SET due=excluded.due, ease=excluded.ease, "
              "reps=excluded.reps, lapses=excluded.lapses, last=excluded.last",
              (task["id"], user, time.time() + interval, ease, reps, lapses, time.time()))
    # cas merime prohlizecem (od otevreni ukoly); 0 az 30 minut je rozumny rozsah
    spent_ms = max(5_000, min(int(elapsed_ms or 0), 1_800_000)) if elapsed_ms else int(out.get("ms") or 0)
    store.record_attempt(c, user=user, task=task["id"], ok=bool(ok), hints=hints_used,
                         ms=spent_ms, first_try=int(bool(ok) and hints_used == 0 and first),
                         code=code, err=(out.get("error") or "")[:900])
    c.execute("UPDATE plan SET minutes_done = COALESCE(minutes_done,0) + ? WHERE day=? AND user=?",
              (round(spent_ms / 60000, 2) if ok else 0.5, today(), user))


def suggest_next(c: sqlite3.Connection, user: str) -> dict | None:
    row = c.execute("SELECT task_ids FROM plan WHERE day=? AND user=?", (today(), user)).fetchone()
    if not row:
        return None
    ids = json.loads(row["task_ids"])
    done = {r["task"] for r in c.execute(
        "SELECT task FROM attempts WHERE user=? AND ok=1 AND date(ts,'unixepoch','localtime')=?",
        (user, today()))}
    for tid in ids:
        if tid not in done:
            t = get_task(c, tid)
            if t:
                return {"id": t["id"], "title": t["title"], "why": t.get("why") or "další z dnešní dávky"}
    return None


class HintBody(BaseModel):
    task_id: str
    step: int = 1
    code: str = ""
    error: str | None = None


@app.post("/api/hint")
async def api_hint(request: Request, body: HintBody):
    user = current_user(request) or USER
    with db() as c:
        task = get_task(c, body.task_id)
        if not task:
            raise HTTPException(404, "neznámá úloha")
        hints = task.get("hints") or []
        key = f"hints:{user}:{task['id']}:{today()}"
        cur = c.execute("SELECT val FROM ai_cache WHERE key=?", (key,)).fetchone()
        n = int(cur["val"]) if cur else 0
        n += 1
        c.execute("INSERT INTO ai_cache(key,val,ts) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET val=excluded.val, ts=excluded.ts",
                  (key, str(n), time.time()))
    if body.step <= len(hints):
        return {"source": "banka", "text": hints[body.step - 1]}
    txt = await ai.coach_hint(task, body.code, body.error, None, "hint")
    with db() as c:
        store_feedback(c, user, task["id"], "hint_ai", txt)
    return {"source": "ai", "text": txt}


class CoachBody(BaseModel):
    task_id: str | None = None
    code: str = ""
    error: str | None = None
    check_msg: str | None = None
    mode: str = "error"


@app.post("/api/coach")
async def api_coach(request: Request, body: CoachBody):
    user = current_user(request) or USER
    task = {}
    if body.task_id:
        with db() as c:
            task = get_task(c, body.task_id) or {}
    txt = await ai.coach_hint(task or {"title": "volná práce", "zadani": ""}, body.code,
                              body.error, body.check_msg, body.mode)
    return {"text": txt}


class SolutionBody(BaseModel):
    task_id: str


@app.post("/api/solution")
async def api_solution(request: Request, body: SolutionBody):
    user = current_user(request) or USER
    with db() as c:
        task = get_task(c, body.task_id)
        if not task:
            raise HTTPException(404, "neznámá úloha")
        store_feedback(c, user, task["id"], "solution_opened", "")
        return {"reseni": task.get("reseni") or "(řešení zatím není)",
                "note": "Otevření řešení se počítá jako nápověda — aspoň to pak přepiš sám/sama bez koukání."}


@app.get("/api/tasks")
def api_tasks(request: Request, lesson: int | None = None, skill: str | None = None,
              status: str | None = None):
    # koncepty vidí jen učitel a správce — student ať nedostane nic neprověřeného,
    # výjimkou je koncept, který on sám nechal napsat nebo napsal
    kdo = current_user(request) or ""
    role = ensure_users().get(kdo, {}).get("role", "student")
    vidim_koncepty = role in ("teacher", "admin")
    with db() as c:
        q = "SELECT * FROM tasks WHERE status != 'retired'"
        args: list = []
        if lesson:
            q += " AND lesson = ?"
            args.append(lesson)
        if skill:
            q += " AND skills LIKE ?"
            args.append(f'%"{skill}"%')
        if status:
            q += " AND status = ?"
            args.append(status)
        if not vidim_koncepty:
            q += " AND (status = 'approved' OR owner = ?)"
            args.append(kdo)
        q += " ORDER BY lesson, level, id"
        odlozeno = store.dropped_for(c, kdo or USER)
        out = []
        for r in c.execute(q, args):
            t = store.row_to_task(r)
            t["moje"] = bool(t.get("owner")) and t.get("owner") == kdo
            t["zahozena"] = t["id"] in odlozeno
            a = c.execute("SELECT COUNT(*) n, COALESCE(SUM(ok),0) p FROM attempts WHERE user=? AND task=?",
                          (current_user(request) or USER, t["id"])).fetchone()
            t.update(attempts=a["n"], passed=a["p"])
            for k in ("check_r", "reseni", "nacti"):
                t.pop(k, None)
            out.append(t)
        return {"tasks": out, "lessons": task_lessons()}


@app.get("/api/progress")
def api_progress(request: Request, days: int = 60):
    user = current_user(request) or USER
    with db() as c:
        st = store.user_stats(c, user, days)
        by_lesson = [dict(r) for r in c.execute(
            """SELECT t.lesson, COUNT(*) n, SUM(a.ok) p, AVG(t.level) lvl
               FROM attempts a JOIN tasks t ON t.id = a.task
               WHERE a.user = ? GROUP BY t.lesson ORDER BY t.lesson""", (user,))]
        weak = [dict(r) for r in c.execute(
            """SELECT s.key, s.label, s.theta, s.n FROM skills s
               WHERE s.n > 0 ORDER BY s.theta ASC LIMIT 6""")]
        recent = [dict(r) for r in c.execute(
            """SELECT a.ts, a.task, a.ok, a.hints, t.title, t.level FROM attempts a
               JOIN tasks t ON t.id = a.task WHERE a.user=? ORDER BY a.ts DESC LIMIT 25""", (user,))]
        hard = [dict(r) for r in c.execute(
            "SELECT task, reps, lapses, due FROM srs WHERE user=? AND lapses>0 ORDER BY lapses DESC LIMIT 8", (user,))]
        gen = [dict(r) for r in c.execute(
            "SELECT id, title, lesson, level, status, source FROM tasks WHERE source='llm' ORDER BY created DESC LIMIT 20")]
    return {**st, "by_lesson": by_lesson, "weak": weak, "recent": recent, "hard": hard,
            "generated": gen, "streak": adaptive.streak(c, user), "lesson_current": syllabus.current_lesson(),
            "cheatsheet": syllabus.CHEATSHEET, "syllabus": task_lessons()}


@app.get("/api/cheatsheet")
def api_cheatsheet(request: Request):
    """Tahák po lekcích — zvlášť, aby záložka nečekala na celý progres."""
    return {"cheatsheet": syllabus.CHEATSHEET, "lesson_current": syllabus.current_lesson(),
            "syllabus": task_lessons()}


@app.get("/api/notes")
def api_notes(request: Request, limit: int = 40):
    """Poznámky, které si user sám zapsal k úlohám. Leží v tabulce feedback."""
    user = current_user(request) or USER
    with db() as c:
        rows = [dict(r) for r in c.execute(
            """SELECT f.ts, f.task, f.text, COALESCE(t.title, f.task) AS title
                 FROM feedback f LEFT JOIN tasks t ON t.id = f.task
                WHERE f.user = ? AND f.kind = 'note'
                ORDER BY f.ts DESC LIMIT ?""", (user, max(1, min(int(limit), 200))))]
    return {"notes": rows}


@app.get("/api/datasets")
def api_datasets():
    return {"datasets": datasets()}


@app.get("/api/dataset/{name}")
def api_dataset(name: str, lines: int = 25):
    """Náhled datového souboru. CSV vrací i strukturu (cols/data), aby se z ní
    dal v prohlížeči složit skutečný stolek; txt zůstává jako text."""
    p = (Path(os.environ.get("RPRAXE_DATASETS", "/data/datasets")) / Path(name).name).resolve()
    root = Path(os.environ.get("RPRAXE_DATASETS", "/data/datasets")).resolve()
    if root not in p.parents or not p.is_file():
        raise HTTPException(404, "není")
    vse = p.read_text(encoding="utf-8", errors="replace").splitlines()
    vzorek = vse[:lines]
    cols: list[str] = []
    data: list[list[str]] = []
    if p.suffix.lower() == ".csv":
        import csv
        import io
        nactene = [r for r in csv.reader(io.StringIO("\n".join(vzorek))) if r]
        if nactene:
            cols, data = nactene[0], nactene[1:]
    return {"name": p.name, "cols": cols, "data": data, "shown": len(data),
            "rows_total": max(0, len(vse) - 1) if p.suffix.lower() == ".csv" else 0,
            "preview": "\n".join(vzorek), "size": p.stat().st_size}


class FeedbackBody(BaseModel):
    task_id: str | None = None
    kind: str = "note"
    text: str = ""


def store_feedback(c, user, task, kind, text):
    c.execute("INSERT INTO feedback(ts,user,task,kind,text) VALUES(?,?,?,?,?)",
              (time.time(), user, task, kind, text[:4000]))


@app.post("/api/feedback")
def api_feedback(request: Request, body: FeedbackBody):
    user = current_user(request) or USER
    with db() as c:
        store_feedback(c, user, body.task_id or "", body.kind, body.text)
    return {"ok": True}


@app.post("/api/generate")
async def api_generate(request: Request, count: int = 2):
    """Vygeneruje a automaticky ověří nové úlohy (používá noční úloha i tlačítko)."""
    user = current_user(request) or "system"
    allowed = datasets()
    made = []
    with db() as c:
        tasks = tasks_all(c)
        skills = adaptive.skill_snapshot(c, user if user in ("lenka", "ondra") else "lenka")
    for _ in range(max(1, min(count, 5))):
        focus = syllabus.lesson_focus()
        level = max(1.0, min(4.0, (sum(s["theta"] for s in skills.values()) / max(1, len(skills))) + 0.2))
        draft = await ai.generate_task(syllabus.current_lesson(), focus, allowed, level,
                                       [t["id"] for t in tasks])
        if not draft:
            continue
        verdict = await validate_task(draft)
        draft["status"] = "approved" if verdict["ok"] else "draft"
        draft["note"] = verdict.get("msg", "")[:400]
        # ať víme, komu koncept patří, když ho chce ještě upravit
        draft["owner"] = "" if user == "system" else user
        with db() as c:
            store.upsert_task(c, draft)
        made.append({"id": draft["id"], "title": draft["title"], "validated": verdict["ok"],
                     "msg": verdict.get("msg", "")[:200]})
    return {"created": made}


async def validate_task(draft: dict) -> dict:
    """Spustí řešení úlohy v runneru; solution musí projít vlastní kontrolou."""
    payload = {"code": draft.get("reseni") or "", "check": draft.get("check") or "FALSE",
               "plots": False, "libraries": ["dplyr", "tidyr", "ggplot2", "readr", "forcats", "lubridate"]}
    if draft.get("dataset"):
        payload["datasets"] = [draft["dataset"]]
    if draft.get("nacti"):
        payload["code"] = draft["nacti"] + "\n" + payload["code"]
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(f"{RUNNER}/run", json=payload)
            out = r.json()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "msg": f"runner nedostupný: {exc}"}
    if out.get("error"):
        return {"ok": False, "msg": "řezení hází chybu: " + str(out["error"])[:200]}
    chk = out.get("check") or {}
    if not chk.get("pass"):
        return {"ok": False, "msg": "řešení neprošlo kontrolou: " + str(chk.get("msg", ""))[:200]}
    # pojistka: prázdný kód musí spadnout, jinak je kontrola moc štědrá
    empty = {"code": "# nic", "check": draft.get("check") or "FALSE", "plots": False,
             "libraries": ["dplyr"]}
    if draft.get("dataset"):
        empty["datasets"] = [draft["dataset"]]
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            out2 = (await client.post(f"{RUNNER}/run", json=empty)).json()
        if (out2.get("check") or {}).get("pass"):
            return {"ok": False, "msg": "kontrola projde i bez řešení — odmítnuto"}
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "msg": "ověřeno spuštěním"}


async def run_v_sandboxu(task: dict, code: str) -> dict:
    """Jeden běh v sandboxu s kontrolou téhle úlohy — pro ověřování i náhled."""
    kontrola = task.get("check") or task.get("check_r") or "FALSE"
    payload = {"code": code, "check": kontrola, "plots": True,
               "libraries": ["dplyr", "tidyr", "ggplot2", "readr", "forcats", "lubridate"]}
    if task.get("dataset"):
        payload["datasets"] = [task["dataset"]]
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            return (await client.post(f"{RUNNER}/run", json=payload)).json()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"runner nedostupný: {exc}"}


async def overeni_spustenim(task: dict) -> dict:
    """Ověří jednu úlohu ze tří stran: řešení, prázdný kód, startovací kostka.

    Vrací i to, co běhy vypisovaly — učitel pak neposuzuje jen green check,
    ale vidí výstup a stav prostředí.
    """
    nacti = (task.get("nacti") or "").strip()
    reseni = (task.get("reseni") or "").strip()
    beh_reseni = await run_v_sandboxu(task, (nacti + "\n" + reseni).strip())
    bez_reseni = await run_v_sandboxu(task, "# zatím prázdné")

    vysledek = {
        "reseni_proslo": bool((beh_reseni.get("check") or {}).get("pass")) and not beh_reseni.get("error"),
        "zprava_kontrolky": str((beh_reseni.get("check") or {}).get("msg") or "")[:300],
        "vystup_reseni": str(beh_reseni.get("stdout") or beh_reseni.get("error") or "")[:2500],
        "prostredi": (beh_reseni.get("env") or [])[:14],
        "graf": bool(beh_reseni.get("plot")),
        "prazdny_kod_prosel": bool((bez_reseni.get("check") or {}).get("pass")),
    }
    if (task.get("starter") or "").strip():
        kostka = await run_v_sandboxu(task, (nacti + "\n" + task["starter"]).strip())
        vysledek["kostka_prosel"] = bool((kostka.get("check") or {}).get("pass"))
    else:
        vysledek["kostka_prosel"] = False

    duvody = []
    if not vysledek["reseni_proslo"]:
        duvody.append("řešení neprošlo kontrolou")
    if vysledek["prazdny_kod_prosel"]:
        duvody.append("kontrola propustí i prázdný kód")
    if vysledek.get("kostka_prosel"):
        duvody.append("kontrola propustí i startovací kostku")
    vysledek["duvody"] = duvody
    vysledek["ok"] = not duvody
    return vysledek


@app.get("/api/backups")
def api_backups(request: Request):
    """Stav zálohování — pro dashboard i pro krizovou obnovu."""
    admin(request)
    return backup_status()


@app.get("/api/export")
def api_export(request: Request):
    user = current_user(request) or USER
    with db() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT a.ts, a.task, a.ok, a.hints, a.code, t.title, t.lesson FROM attempts a "
            "LEFT JOIN tasks t ON t.id=a.task WHERE a.user=? ORDER BY a.ts", (user,))]
    def esc(v):
        s = str(v if v is not None else "")
        return '"' + s.replace('"', '""').replace("\n", " ") + '"'
    csv_lines = ["cas;uloha;titulek;lekce;uspech;nnapovedy;kod"]
    for r in rows:
        csv_lines.append(";".join([esc(datetime.fromtimestamp(r["ts"]).isoformat(timespec="seconds")),
                                   esc(r["task"]), esc(r.get("title")), esc(r.get("lesson")),
                                   esc("ano" if r["ok"] else "ne"), esc(r["hints"]), esc(r["code"])]))
    return Response("\n".join(csv_lines), media_type="text/csv; charset=utf-8",
                    headers={"content-disposition": f'attachment; filename="procvicovani-{today()}.csv"'})


@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("rpraxe")
    return resp


@app.get("/api/whoami")
def whoami(request: Request):
    u = current_user(request)
    rec = ensure_users().get(u or "", {})
    with db() as c:
        pref = store.prefs(c, u) if u else dict(store.PREF_DEFAULTS)
    return {"user": u, "role": rec.get("role", "?"), "theme": pref["theme"],
            "lang": pref["lang"], "model": pref["model"], "minutes": int(pref["val"])}


PW_MIN = 8                 # nejkratší nové heslo
PW_FAIL_MAX = 5            # pokusů se špatným současným heslem
PW_LOCK_S = 600            # pak pauza na 10 minut


def _fail_row(c: sqlite3.Connection, key: str) -> tuple[int, float]:
    row = c.execute("SELECT val FROM ai_cache WHERE key=?", (key,)).fetchone()
    if not row:
        return 0, 0.0
    try:
        fails, until = json.loads(row["val"])
        return int(fails), float(until)
    except (ValueError, TypeError):
        return 0, 0.0


def _users_save(users: dict) -> None:
    accounts.save(USERS_FILE, users)


class PasswordBody(BaseModel):
    current: str
    new: str
    repeat: str


@app.post("/api/password")
def api_password(request: Request, body: PasswordBody):
    """Změní heslo přihlášeného účtu. Chce současné heslo, hlídá délku a hrubou sílu."""
    user = current_user(request)
    if not user:
        raise HTTPException(401, "nepřihlášen")
    key = f"pwfail:{user}"
    now = time.time()
    with db() as c:
        fails, until = _fail_row(c, key)
    if until > now:
        raise HTTPException(429, f"Příliš mnoho pokusů — zkus to znovu za {int((until - now) / 60) + 1} min.")

    users = ensure_users()
    rec = users.get(user)
    if not rec:
        raise HTTPException(404, "účet nenalezen")

    if not check_pw(body.current, rec["hash"]):
        with db() as c:
            fails += 1
            locked = fails >= PW_FAIL_MAX
            until = now + PW_LOCK_S if locked else 0.0
            c.execute("INSERT INTO ai_cache(key,val,ts) VALUES(?,?,?) "
                      "ON CONFLICT(key) DO UPDATE SET val=excluded.val, ts=excluded.ts",
                      (key, json.dumps([0 if locked else fails, until]), now))
        raise HTTPException(401, "Nesedí současné heslo.")

    if body.new != body.repeat:
        raise HTTPException(422, "Nová hesla se neshodují.")
    if len(body.new) < PW_MIN:
        raise HTTPException(422, f"Nové heslo musí mít aspoň {PW_MIN} znaků.")
    if body.new == body.current:
        raise HTTPException(422, "Nové heslo musí být jiné než to současné.")
    if len(set(body.new)) < 4:
        raise HTTPException(422, "Nové heslo je příliš jednoduché — použij aspoň čtyři různé znaky.")

    users[user] = {**rec, "hash": hash_pw(body.new), "generated": False,
                   "changed": datetime.now().isoformat(timespec="seconds")}
    _users_save(users)
    with db() as c:
        c.execute("DELETE FROM ai_cache WHERE key=?", (key,))
    print(f"[rpraxe] {datetime.now():%Y-%m-%d %H:%M} ucet {user}: heslo zmeneno (profil)", flush=True)

    resp = JSONResponse({"ok": True, "msg": "heslo změněno"})
    resp.set_cookie("rpraxe", make_token(user), httponly=True, samesite="lax",
                    max_age=30 * 86400, secure=request_is_https())
    return resp
