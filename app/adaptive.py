"""Adaptivní jádro — Elo pro dovednosti, intervalové opakování, plánovač sezení.

Model:
  theta_s  …obtížnost, kterou už žák zvládá (Elo-like, škála ~0.5–3.5)
  level_t  …úroveň úlohy (1–5, bankou odhadnuto, zpřesňuje se z průchodnosti)
  P(pass)  …logistická funkce rozdílu (theta - level)
  K        …přizpůsobivost; po nápovědě se aktualizace tlumí
"""
from __future__ import annotations

import math
import random
import sqlite3
import time
from dataclasses import dataclass

K_STUDENT = 0.28
K_TASK = 0.18
SCALE = 0.9          # měřítko logistiky (v úrovních)
TARGET_P = 0.78      # cílová šance na úspěch u nové úlohy


def p_pass(theta: float, level: float) -> float:
    return 1 / (1 + math.exp(-(theta - level) / SCALE))


def quality(ok: bool, hints: int, first_try: bool) -> float:
    """Spolehlivost výkonu 0–1, trest za nápovědy a opakování."""
    if not ok:
        return 0.0
    q = 1.0 - 0.22 * min(hints, 3)
    if not first_try:
        q -= 0.15
    return max(0.25, q)


def update_theta(theta: float, level: float, q: float, n: int) -> tuple[float, int]:
    exp_p = p_pass(theta, level)
    k = K_STUDENT * (1.35 if n < 4 else 1.0)
    return theta + k * (q - exp_p), n + 1


def update_level(level: float, q: float) -> float:
    return max(0.6, min(5.0, level + K_TASK * (1 - q) - K_TASK * 0.15))


# ---------------------------------------------------------------- SRS ------
DAY = 86400.0


def srs_next(ease: float, reps: int, lapses: int, q: float) -> tuple[float, float, int, int]:
    """Zjednodušené SM-2: interval ve dnech."""
    if q < 0.5:
        return 0.5 * DAY, max(1.3, ease - 0.2), 0, lapses + 1
    interval = {0: 1.0, 1: 3.0}.get(reps, ease * (2.2 ** min(reps - 1, 3)))
    interval = min(interval, 45.0)
    ease = max(1.3, min(2.8, ease + (0.08 + (reps >= 2) * 0.02) * (3 * q - 2)))
    return interval * DAY, ease, reps + 1, lapses


# --------------------------------------------------------- výběh úloh ------
@dataclass
class Candidate:
    task: dict
    score: float
    why: str


def plan_session(tasks: list[dict], skills: dict[str, dict], srs: dict[str, dict],
                 minutes: int = 20, done_ids: list[str] | None = None,
                 focus_skills: list[str] | None = None,
                 rng: random.Random | None = None,
                 max_lessons_ahead: int = 1) -> list[Candidate]:
    """Vyber úlohy tak, aby se vešly do časového budgetu a sedly na aktuální úroveň."""
    rng = rng or random.Random()
    done = set(done_ids or [])
    focus = set(focus_skills or [])
    budget = max(5, int(minutes))
    out: list[Candidate] = []
    used_datasets: dict[str, int] = {}
    used_prefix: set[str] = set()

    def theta_of(task: dict) -> float:
        sk = task.get("skills") or []
        vals = [skills.get(s, {}).get("theta", 1.6) for s in sk]
        return sum(vals) / len(vals) if vals else 1.6

    def level_of(task: dict) -> float:
        return float(task.get("level") or 1)

    def score(task: dict) -> tuple[float, str]:
        th, lv = theta_of(task), level_of(task)
        p = p_pass(th, lv)
        s = -abs(p - TARGET_P) * 3.0
        why = f"trefena obtížnost (přibližná šance {int(p * 100)} %)"
        sk = set(task.get("skills") or [])
        if focus & sk:
            s += 1.4
            why = "procvičuje to, co zrovna probíráte v kurzu"
        key = (task.get("id") or "").split("-")[0]
        sr = srs.get(task["id"])
        if sr and sr.get("due", 0) <= time.time():
            s += 1.9
            why = "je čas to zopakovat (zapomínání)"
        if sr and sr.get("lapses", 0) >= 2:
            s += 1.2
            why = "tuhle látku jsi zatím dvakrát nezvládla na první pokus"
        if key in used_prefix:
            s -= 1.6
        ds = task.get("dataset") or ""
        if ds and used_datasets.get(ds, 0) >= 1:
            s -= 1.1
        if task.get("source") == "llm":
            s += 0.15
        s += rng.uniform(0, 0.35)
        return s, why

    pool = [t for t in tasks if t["id"] not in done and t.get("status", "approved") == "approved"]
    scored = sorted(((score(t), t) for t in pool), key=lambda x: -x[0][0])

    current_lesson = max([int(t.get("lesson") or 0) for t in tasks] or [0])
    for (s, why), t in scored:
        if budget <= 0:
            break
        mins = int(t.get("minutes") or 4)
        if mins > budget + 2:
            continue
        lesson = int(t.get("lesson") or 0)
        if lesson > current_lesson:            # daleko před kurzem neposílám
            pass
        out.append(Candidate(t, s, why))
        budget -= mins
        used_datasets[t.get("dataset") or ""] = used_datasets.get(t.get("dataset") or "", 0) + 1
        used_prefix.add((t.get("id") or "").split("-")[0])
    return out


def skill_snapshot(conn: sqlite3.Connection, user: str) -> dict[str, dict]:
    """Odhad dovedností jednoho účtu — nikdy ne přes všechny studenty dohromady."""
    rows = conn.execute(
        "SELECT s.key, COALESCE(l.label, s.key) AS label, s.theta, s.n, COALESCE(l.lesson, 0) AS lesson "
        "FROM skills s LEFT JOIN skill_labels l ON l.key = s.key WHERE s.user = ?", (user,)).fetchall()
    return {r["key"]: {"theta": r["theta"], "n": r["n"], "label": r["label"], "lesson": r["lesson"]}
            for r in rows}


def srs_snapshot(conn: sqlite3.Connection, user: str) -> dict[str, dict]:
    rows = conn.execute("SELECT task, due, ease, reps, lapses FROM srs WHERE user = ?", (user,)).fetchall()
    return {r["task"]: {"due": r["due"], "ease": r["ease"], "reps": r["reps"], "lapses": r["lapses"]}
            for r in rows}


def daily_stats(conn: sqlite3.Connection, user: str, day: str) -> dict:
    row = conn.execute(
        "SELECT COUNT(*) n, COALESCE(SUM(ok),0) p, COALESCE(SUM(ms),0)/60000.0 min "
        "FROM attempts WHERE user = ? AND date(ts,'unixepoch','localtime') = ?",
        (user, day)).fetchone()
    return {"n": row["n"], "passed": row["p"], "minutes": round(row["min"] or 0, 1)}


def streak(conn: sqlite3.Connection, user: str) -> int:
    rows = conn.execute(
        "SELECT DISTINCT date(ts,'unixepoch','localtime') d FROM attempts WHERE user = ? AND ok = 1",
        (user,)).fetchall()
    days = {r["d"] for r in rows}
    if not days:
        return 0
    import datetime as _dt
    d = _dt.date.today()
    if d.isoformat() not in days:
        d -= _dt.timedelta(days=1)
    n = 0
    while d.isoformat() in days:
        n += 1
        d -= _dt.timedelta(days=1)
    return n
