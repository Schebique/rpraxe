#!/usr/bin/env python3
"""Noční agent rpraxe — třikrát týdně doplní a ověří nové úlohy a pošle vzkaz.

Běží uvnitř kontejneru `rpraxe-app` (cron). Co dělá:
  1. Spočítá, kolik je v bance ověřených úloh na aktuální lekci kurzu.
  2. Pokud jich je málo, požádá lokální model o nové a každou nechá
     automaticky ověřit spuštěním (řešení musí projít vlastní kontrolou,
     prázdné řešení musí spadnout).
  3. Projde dovednosti s nízkým odhadem a slabá opakování a zapíše ranní
     shrnutí do state/agent_posled.txt (zobrazuje se v aplikace i v Discordu).
Model je lokální (Ollama na Kozlikovi); data nikam neputují.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/srv")

from app import adaptive, ai, store, syllabus  # noqa: E402

STATE = Path("/data/state")


async def run(target: int = 3) -> str:
    store.init()
    with store.conn() as c:
        from app.main import load_banks, tasks_all  # noqa: PLC0415
        load_banks()
        tasks = tasks_all(c)
        skills = adaptive.skill_snapshot(c, "lenka")
        srs = adaptive.srs_snapshot(c, "lenka")
        lesson = syllabus.current_lesson()
        focus = syllabus.lesson_focus()
        due = [tid for tid, s in srs.items() if s.get("due", 0) <= time.time()]
        weak = sorted(((s["theta"], k) for k, s in skills.items() if s["n"] >= 2))[:3]

    in_lesson = [t for t in tasks if int(t.get("lesson") or 0) == lesson and t.get("status") == "approved"]
    created, failed = [], []
    allowed = sorted(p.name for p in Path("/data/datasets").glob("*") if p.is_file())
    for _ in range(max(0, target - len(in_lesson))):
        level = (sum(s["theta"] for s in skills.values()) / max(1, len(skills))) if skills else 1.4
        draft = await ai.generate_task(lesson, focus, allowed, level, [t["id"] for t in tasks])
        if not draft:
            failed.append("model nevrátil použitelný JSON")
            continue
        from app.main import validate_task  # noqa: PLC0415
        verdict = await validate_task(draft)
        draft["status"] = "approved" if verdict["ok"] else "draft"
        draft["note"] = "noční agent: " + verdict.get("msg", "")[:200]
        with store.conn() as c:
            store.upsert_task(c, draft)
        (created if verdict["ok"] else failed).append(f"{draft['id']} — {draft['title']}")
        tasks.append(draft)

    lines = [f"Agent {datetime.now():%d.%m. %H:%M}",
             f"Kurz: {lesson}. lekce — {syllabus.LESSONS[lesson]['title']}",
             f"Ověřených úloh na lekci: {len(in_lesson)} (cíl {target})",
             f"Nové ověřené: {', '.join(created) or 'žádné'}",
             f"Zamítnuto: {len(failed)}" + (f" ({'; '.join(failed[:2])})" if failed else ""),
             f"K zopakování (spí): {len(due)}"]
    if weak:
        lines.append("Nejslabší teraz: " + ", ".join(f"{k} ({t:.1f})" for t, k in weak))
    else:
        lines.append("Zatím nemá změřeno — první pokusy nastaví obtížnost.")
    msg = "\n".join(lines)
    (STATE / "agent_posled.txt").write_text(msg, encoding="utf-8")
    with store.conn() as c:
        c.execute("INSERT INTO feedback(ts,user,task,kind,text) VALUES(?,?,?,?,?)",
                  (time.time(), "agent", "", "nightly", msg))
    return msg


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(asyncio.run(run(n)))
