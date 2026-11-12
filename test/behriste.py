#!/usr/bin/env python3
"""Adresa běžce R se chová podle toho, v jaké variantě to běží.

Testuje se ve vlastním procesu, protože `app.behriste` čte prostředí a to si
nedá měnit tam, kde už test někam sahal.

    python3 test/behriste.py
"""
from __future__ import annotations

import os
import subprocess
import sys

ADRESAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUS = "from app.behriste import adresa; print(adresa())"
PRAVIDLA = [
    ({}, "http://127.0.0.1:8081",
     "vestaveny bezec"),
    ({"RPRAXE_RUNNER_PROMIT": "1"}, "http://127.0.0.1:8081",
     "vestaveny vyslovne"),
    ({"RPRAXE_RUNNER_INTERNAL_PORT": "9099"}, "http://127.0.0.1:9099",
     "vestaveny na jinem portu"),
    ({"RPRAXE_RUNNER_PROMIT": "0"}, "http://rpraxe-runner:8081",
     "sluzba, adresa se nezaplnila"),
    ({"RPRAXE_RUNNER_PROMIT": "0", "RPRAXE_RUNNER": "http://runner:8081/"},
     "http://runner:8081", "sluzba, lomátko na konci se ořízne"),
    # tohle je ten případ, co jsme chytili až uvnitř kontejneru: entrypoint si
    # adresu nastaví pro svůj proces, ale `docker compose exec` ji nemá
    ({"RPRAXE_RUNNER_PROMIT": "1", "RPRAXE_RUNNER": "http://runner:8081"},
     "http://127.0.0.1:8081", "vestaveny má přednost i před RPRAXE_RUNNER"),
]


def main() -> int:
    selhani = 0
    for extra, cekano, popis in PRAVIDLA:
        env = {k: v for k, v in os.environ.items() if not k.startswith("RPRAXE_")}
        env.update(extra)
        try:
            vysledek = subprocess.run([sys.executable, "-c", KUS], cwd=ADRESAR, env=env,
                                      capture_output=True, text=True, timeout=60)
            dostalo = vysledek.stdout.strip() or vysledek.stderr.strip()[-120:]
        except Exception as e:                       # noqa: BLE001
            dostalo = f"vyjimka {e}"
        ok = dostalo == cekano
        selhani += 0 if ok else 1
        print(("✓ " if ok else "✗ ") + popis + ("" if ok else f" — čekan {cekano}, je {dostalo}"))
    print(f"\n{len(PRAVIDLA) - selhani} v pořádku, {selhani} s problémem z {len(PRAVIDLA)}")
    return 1 if selhani else 0


if __name__ == "__main__":
    sys.exit(main())
