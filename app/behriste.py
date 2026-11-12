"""Jak se dostaneš ke službě, která pouští R.

Jedno místo, protože adres je víc a mýtí se snadno:

* **jeden kontejner** (výchozí) — běžec R běží vedle aplikace ve stejném
  kontejneru, adresa je `http://127.0.0.1:8081`. Pozor na to: entrypoint si ji
  nastaví pro svůj proces, ale `docker compose exec` pouští nový proces bez
  toho, takže skripty musí poznat vestavěný sandbox samy.
* **dva kontejnery** — `RPRAXE_RUNNER_PROMIT=0` a `RPRAXE_RUNNER` ukazuje na
  službu (název service v compose, nebo `http://runner:8081`).
* **Kubernetes** — `http://<název-service>:8081`; vestavěný sandbox se tam
  nechává zapnutý, takže se adresa vůbec nezadává.
"""
from __future__ import annotations

import os

DOSLVNI = "http://rpraxe-runner:8081"


def vestaveny() -> str:
    return "http://127.0.0.1:" + os.environ.get("RPRAXE_RUNNER_INTERNAL_PORT", "8081")


def adresa() -> str:
    """Plná adresa běžce R bez lomítka na konci."""
    if os.environ.get("RPRAXE_RUNNER_PROMIT", "1") == "1":
        return vestaveny()
    return (os.environ.get("RPRAXE_RUNNER") or DOSLVNI).rstrip("/")
