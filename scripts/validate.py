#!/usr/bin/env python3
"""Ověří banku úloh: řešení musí projít kontrolou, prázdný kód musí spadnout.

Spouští se uvnitř kontejneru:  python3 /srv/scripts/validate.py [filtr]
Vrací seznam úloh, které je potřeba opravit — žádné „snad to funguje“.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

# Adresu řeší app/behriste.py — uvnitř kontejneru, i když je sandbox vestavěný
# a `docker compose exec` nedostal proměnné z entrypointu.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from app.behriste import adresa as _adresa_behrziste
    RUNNER = _adresa_behrziste()
except Exception:                                   # skript mimo balíček app/
    RUNNER = (os.environ.get("RPRAXE_RUNNER") or "http://rpraxe-runner:8081").rstrip("/")

TASKS_DIR = os.environ.get("RPRAXE_TASKS", "/srv/tasks")
LIBS = ["dplyr", "tidyr", "ggplot2", "readr", "forcats", "lubridate"]


def post(payload: dict) -> dict:
    req = urllib.request.Request(f"{RUNNER}/run", data=json.dumps(payload).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def load_tasks():
    import importlib
    from pathlib import Path
    sys.path.insert(0, TASKS_DIR)
    out = []
    for f in sorted(Path(TASKS_DIR).glob("*.py")):
        if f.name.startswith("_"):
            continue
        mod = importlib.import_module(f.stem)
        for t in getattr(mod, "TASKS", []):
            out.append(t)
    return out


def check_task(t: dict) -> list[str]:
    problems = []
    for k, v in t.items():
        if isinstance(v, tuple):
            problems.append(f"pole {k} je tuple (v bance chybí uvozovky/oddělovač)")
    ds = [t["dataset"]] if t.get("dataset") else []
    nacti = t.get("nacti") or ""
    base = {"check": t.get("check") or "FALSE", "datasets": ds, "libraries": LIBS, "plots": True}

    sol = post({**base, "code": nacti + "\n" + (t.get("reseni") or "")})
    if sol.get("error"):
        problems.append("řešení hází chybu: " + str(sol["error"])[:160])
    chk = sol.get("check") or {}
    if not chk.get("pass"):
        problems.append("řešení neprošlo kontrolou: " + str(chk.get("msg", ""))[:160])

    empty = post({**base, "code": "# zatím prázdné"})
    if (empty.get("check") or {}).get("pass"):
        problems.append("kontrola propustí i prázdné řešení")

    if t.get("starter"):
        st = post({**base, "code": nacti + "\n" + t["starter"]})
        if (st.get("check") or {}).get("pass"):
            problems.append("kontrola propustí i startovací kostru")

    for h in (t.get("hints") or []):
        if "chybějící" in h.lower() and not t.get("dataset"):
            problems.append("nápověda zmiňuje data, ale úloha žádná nemá")
    return problems


def main() -> int:
    flt = sys.argv[1] if len(sys.argv) > 1 else ""
    tasks = [t for t in load_tasks() if flt in t["id"] or flt in t.get("title", "")]
    bad, ok = [], 0
    for t in tasks:
        p = check_task(t)
        if p:
            bad.append((t["id"], t.get("title"), p))
            print(f"✗ {t['id']:12s} {t.get('title')}")
            for line in p:
                print(f"    · {line}")
        else:
            ok += 1
            print(f"✓ {t['id']:12s} {t.get('title')}", flush=True)
    print(f"\n{ok} v pořádku, {len(bad)} s problémem z {len(tasks)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
