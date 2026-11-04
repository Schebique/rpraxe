"""SQLite vrstva pro rpraxe — úlohy, dovednosti, pokusy, adaptivní model."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

DB = Path(os.environ.get("RPRAXE_DB", "/data/state/rpraxe.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id TEXT PRIMARY KEY, name TEXT, pass_hash TEXT, role TEXT DEFAULT 'student', created REAL);
CREATE TABLE IF NOT EXISTS tasks(
  id TEXT PRIMARY KEY,
  title TEXT, lesson INTEGER, minutes INTEGER, level REAL,
  skills TEXT, dataset TEXT, nacti TEXT, starter TEXT, zadani TEXT,
  check_r TEXT, reseni TEXT, hints TEXT,
  status TEXT DEFAULT 'approved',         -- approved | draft | retired
  source TEXT DEFAULT 'bank',             -- bank | template | llm
  theta REAL DEFAULT 0,                   -- odhad obtížnosti (Elo-like)
  n_att INTEGER DEFAULT 0, n_pass INTEGER DEFAULT 0,
  created REAL, note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS attempts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL, user TEXT, task TEXT, ok INTEGER, hints INTEGER,
  ms INTEGER, first_try INTEGER DEFAULT 0, code TEXT, err TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS skill_labels(
  key TEXT PRIMARY KEY, label TEXT, lesson INTEGER
);
CREATE TABLE IF NOT EXISTS skills(
  key TEXT, user TEXT, theta REAL DEFAULT 1.0, n INTEGER DEFAULT 0,
  PRIMARY KEY(key, user)
);
CREATE TABLE IF NOT EXISTS srs(
  task TEXT, user TEXT, due REAL, ease REAL DEFAULT 2.3, reps INTEGER DEFAULT 0,
  lapses INTEGER DEFAULT 0, last REAL, PRIMARY KEY(task, user)
);
CREATE TABLE IF NOT EXISTS plan(
  day TEXT, user TEXT, task_ids TEXT, minutes INTEGER, minutes_done INTEGER DEFAULT 0,
  created REAL, done_at REAL, PRIMARY KEY(day, user)
);
CREATE TABLE IF NOT EXISTS settings(
  user TEXT PRIMARY KEY, val INTEGER DEFAULT 20, focus TEXT DEFAULT '', updated REAL,
  theme TEXT DEFAULT 'auto', model TEXT DEFAULT '', lang TEXT DEFAULT 'cs'
);
CREATE TABLE IF NOT EXISTS feedback(
  ts REAL, user TEXT, task TEXT, kind TEXT, text TEXT
);
CREATE TABLE IF NOT EXISTS ai_cache(key TEXT PRIMARY KEY, val TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS classes(
  id TEXT PRIMARY KEY, name TEXT, teacher TEXT, note TEXT DEFAULT '', created REAL);
CREATE TABLE IF NOT EXISTS class_students(
  class TEXT, student TEXT, joined REAL, PRIMARY KEY(class, student));
"""


def conn() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=30, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=8000")
    return c


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)
        cols = {r["name"] for r in c.execute("PRAGMA table_info(attempts)")}
        if "first_try" not in cols:      # stará DB měla jen odhadovaný čas
            c.execute("ALTER TABLE attempts ADD COLUMN first_try INTEGER DEFAULT 0")
        # předvolby: stará DB znala jen délku dávky a zaměření
        pref = {r["name"] for r in c.execute("PRAGMA table_info(settings)")}
        for col, dflt in (("theme", "'auto'"), ("model", "''"), ("lang", "'cs'")):
            if col not in pref:
                c.execute(f"ALTER TABLE settings ADD COLUMN {col} TEXT DEFAULT {dflt}")
        # odhady dovedností bývaly společné pro všechny účty — od teď zvlášť pro každý
        if "skills_old" not in {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
            cols = {r["name"] for r in c.execute("PRAGMA table_info(skills)")}
            if "user" not in cols:
                c.execute("ALTER TABLE skills RENAME TO skills_old")
                c.executescript("""CREATE TABLE skills(
                    key TEXT, user TEXT, theta REAL DEFAULT 1.0, n INTEGER DEFAULT 0,
                    PRIMARY KEY(key, user));
                  INSERT INTO skills(key, user, theta, n)
                    SELECT key, COALESCE((SELECT MIN(user) FROM attempts), 'lenka'), theta, n
                    FROM skills_old;
                  CREATE TABLE IF NOT EXISTS skill_labels(
                    key TEXT PRIMARY KEY, label TEXT, lesson INTEGER);
                  INSERT OR IGNORE INTO skill_labels(key, label, lesson)
                    SELECT key, label, lesson FROM skills_old;""")
                print("[rpraxe] schema: odhady dovedností rozděleny podle účtů", flush=True)
        migrace(c)


def migrace(c: sqlite3.Connection) -> None:
    """Doplní, co přibylo s novými funkcemi — stará databáze zůstane čitelná."""
    sloupce = {r["name"] for r in c.execute("PRAGMA table_info(tasks)")}
    if "owner" not in sloupce:
        c.execute("ALTER TABLE tasks ADD COLUMN owner TEXT DEFAULT ''")
    # vlastní „zahodit“ je věc každého žáka — úloha se nikam nesmí smazat globally
    c.execute("CREATE TABLE IF NOT EXISTS dropped("
              "user TEXT, task TEXT, ts REAL, PRIMARY KEY(user, task))")


PREF_DEFAULTS = {"val": 20, "focus": "", "theme": "auto", "model": "", "lang": "cs"}


def prefs(c: sqlite3.Connection, user: str) -> dict:
    row = c.execute("SELECT * FROM settings WHERE user = ?", (user,)).fetchone()
    out = dict(PREF_DEFAULTS)
    if row:
        out.update({k: row[k] for k in row.keys() if k in out})
    out["val"] = int(out["val"] or 20)
    return out


def set_prefs(c: sqlite3.Connection, user: str, **changes) -> dict:
    allowed = set(PREF_DEFAULTS)
    data = prefs(c, user)
    data.update({k: v for k, v in changes.items() if k in allowed and v is not None})
    c.execute(
        "INSERT INTO settings(user,val,focus,theme,model,lang,updated) VALUES(?,?,?,?,?,?,?)\n"
        "  ON CONFLICT(user) DO UPDATE SET val=excluded.val, focus=excluded.focus,"
        " theme=excluded.theme, model=excluded.model, lang=excluded.lang, updated=excluded.updated",
        (user, int(data["val"]), data["focus"], data["theme"], data["model"], data["lang"], time.time()))
    return prefs(c, user)


def row_to_task(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in ("skills", "hints"):
        if d.get(k):
            try:
                d[k] = json.loads(d[k])
            except json.JSONDecodeError:
                d[k] = []
        else:
            d[k] = []
    d["level"] = float(d.get("level") or 1)
    return d


def upsert_task(c: sqlite3.Connection, t: dict) -> None:
    c.execute(
        """INSERT INTO tasks(id,title,lesson,minutes,level,skills,dataset,nacti,starter,zadani,
                             check_r,reseni,hints,status,source,created,note,owner)
           VALUES(:id,:title,:lesson,:minutes,:level,:skills,:dataset,:nacti,:starter,:zadani,
                 :check_r,:reseni,:hints,:status,:source,:created,:note,:owner)
           ON CONFLICT(id) DO UPDATE SET
             title=excluded.title, lesson=excluded.lesson, minutes=excluded.minutes,
             level = CASE WHEN excluded.level = 1 THEN tasks.level ELSE excluded.level END,
             skills=excluded.skills, dataset=excluded.dataset,
             nacti=excluded.nacti, starter=excluded.starter, zadani=excluded.zadani,
             check_r=excluded.check_r, reseni=excluded.reseni, hints=excluded.hints,
             status=excluded.status, source=excluded.source, note=excluded.note,
             owner=CASE WHEN excluded.owner = '' THEN tasks.owner ELSE excluded.owner END""",
        {
            "id": t["id"], "title": t.get("title", t["id"]), "lesson": int(t.get("lesson") or 0),
            "minutes": int(t.get("minutes") or 4), "level": float(t.get("level") or 1),
            "skills": json.dumps(t.get("skills") or []), "dataset": t.get("dataset"),
            "nacti": t.get("nacti") or "", "starter": t.get("starter") or "",
            "zadani": t.get("zadani", ""), "check_r": t.get("check") or t.get("check_r") or "",
            "reseni": t.get("reseni") or "", "hints": json.dumps(t.get("hints") or [], ensure_ascii=False),
            "status": t.get("status", "approved"), "source": t.get("source", "bank"),
            # "owner" má jen to, co si člověk vytvořil sám (žákova úloha, AI pro něj)
            "owner": t.get("owner") or "",
            "created": t.get("created") or time.time(), "note": t.get("note", ""),
        },
    )


def dropped_for(c: sqlite3.Connection, user: str) -> set[str]:
    """Úlohy, které si člověk osobně zahodil — nikoho jiného se to netýká."""
    return {r["task"] for r in c.execute("SELECT task FROM dropped WHERE user = ?", (user,))}


def set_dropped(c: sqlite3.Connection, user: str, uloha: str, zahodit: bool) -> None:
    if zahodit:
        c.execute("INSERT OR REPLACE INTO dropped(user,task,ts) VALUES(?,?,?)",
                  (user, uloha, time.time()))
    else:
        c.execute("DELETE FROM dropped WHERE user = ? AND task = ?", (user, uloha))


def record_attempt(c: sqlite3.Connection, **kw) -> None:
    c.execute(
        """INSERT INTO attempts(ts,user,task,ok,hints,ms,first_try,code,err,note)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (kw.get("ts") or time.time(), kw.get("user"), kw.get("task"), int(bool(kw.get("ok"))),
         int(kw.get("hints") or 0), int(kw.get("ms") or 0), int(bool(kw.get("first_try"))),
         kw.get("code") or "", kw.get("err") or "", kw.get("note") or ""),
    )
    c.execute("UPDATE tasks SET n_att = n_att + 1, n_pass = n_pass + ? WHERE id = ?",
              (int(bool(kw.get("ok"))), kw.get("task")))


def user_stats(c: sqlite3.Connection, user: str, days: int = 60) -> dict:
    since = time.time() - days * 86400
    tot = c.execute("SELECT COUNT(*) n, SUM(ok) p FROM attempts WHERE user=? AND ts>?", (user, since)).fetchone()
    by_day = [dict(r) for r in c.execute(
        """SELECT date(ts,'unixepoch','localtime') d, COUNT(*) n, SUM(ok) p, SUM(ms)/60000.0 min
           FROM attempts WHERE user=? AND ts>? GROUP BY d ORDER BY d""", (user, since))]
    by_skill = [dict(r) for r in c.execute(
        """SELECT s.key, l.label, s.theta, s.n FROM skills s
           LEFT JOIN skill_labels l ON l.key = s.key
           WHERE s.user = ? ORDER BY COALESCE(l.lesson, 99), s.key""", (user,))]
    ft = c.execute(
        """SELECT COUNT(*) n, COALESCE(SUM(first_try),0) p
           FROM attempts WHERE user=? AND ts>? AND ok=1""", (user, since)).fetchone()
    dayinfo = c.execute(
        """SELECT COUNT(DISTINCT date(ts,'unixepoch','localtime')) d,
                  COALESCE(SUM(ms),0)/60000.0 min
           FROM attempts WHERE user=? AND ts>?""", (user, since)).fetchone()
    return {"total": tot["n"] or 0, "passed": tot["p"] or 0, "by_day": by_day, "skills": by_skill,
            "first_try_rate": round(100.0 * ft["p"] / ft["n"]) if ft["n"] else 0,
            "days_active": dayinfo["d"] or 0, "minutes_total": round(dayinfo["min"] or 0)}

# ----------------------------------------------------------------- tridy
def new_class_id(c: sqlite3.Connection) -> str:
    n = c.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
    while True:
        n += 1
        kand = "tr-%02d" % n
        if not c.execute("SELECT 1 FROM classes WHERE id=?", (kand,)).fetchone():
            return kand


def classes(c: sqlite3.Connection, teacher: str | None = None) -> list[dict]:
    """Tridy i se zaky; `teacher` omezi jen na ty, ktere ten kdo vede."""
    if teacher:
        rows = c.execute("SELECT * FROM classes WHERE teacher=? ORDER BY name", (teacher,)).fetchall()
    else:
        rows = c.execute("SELECT * FROM classes ORDER BY name").fetchall()
    out = []
    for r in rows:
        zaci = [x["student"] for x in c.execute(
            "SELECT student FROM class_students WHERE class=? ORDER BY student", (r["id"],))]
        out.append({"id": r["id"], "name": r["name"], "teacher": r["teacher"],
                    "note": r["note"] or "", "created": r["created"], "students": zaci})
    return out


def save_class(c, identification: str, name: str, teacher: str,
               note: str = "", students: list[str] | None = None) -> dict:
    c.execute("INSERT INTO classes(id,name,teacher,note,created) VALUES(?,?,?,?,?) "
              "ON CONFLICT(id) DO UPDATE SET name=excluded.name, teacher=excluded.teacher, "
              "note=excluded.note", (identification, name, teacher, note, time.time()))
    if students is not None:
        c.execute("DELETE FROM class_students WHERE class=?", (identification,))
        for z in dict.fromkeys(students):
            c.execute("INSERT OR IGNORE INTO class_students(class,student,joined) VALUES(?,?,?)",
                      (identification, z, time.time()))
    return next((k for k in classes(c) if k["id"] == identification), {"id": identification})


def drop_class(c, identification: str) -> None:
    c.execute("DELETE FROM classes WHERE id=?", (identification,))
    c.execute("DELETE FROM class_students WHERE class=?", (identification,))


def classes_of(c, student: str) -> list[str]:
    return [r["name"] for r in c.execute(
        "SELECT cl.name FROM classes cl JOIN class_students cs ON cs.class=cl.id "
        "WHERE cs.student=? ORDER BY cl.name", (student,))]
