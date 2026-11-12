"""Nastavení instance: poskytovatel modelů a přihlášení přes bránu.

Leží v `state/config.json` (mód 600), ne v proměnných prostředí — správa to
ovládá z prohlížeče a jinde nasazená instance se liší. Proměnné prostředí jsou
jen výchozí hodnota, takže stávající nasazení se chovají stejně.

Tajemství se do prohlížeče nevrací: API klíč ani SSO tajemství vidí client jen
maskovaně ({"nastaveno": true, "ukazka": "sk-…abc"}).
"""
from __future__ import annotations

import json
import os
import stat
import threading
from pathlib import Path

_STATE = Path(os.environ.get("RPRAXE_DB", "/data/state/rpraxe.db")).parent
CONFIG_FILE = Path(os.environ.get("RPRAXE_CONFIG", str(_STATE / "config.json")))
_LOCK = threading.Lock()

# Zkratka -> jak vypadá dotaz, jaká adresa a modely se nabídnou jako výchozí.
PROVIDERS: dict[str, dict] = {
    "ollama": {
        "jmeno": "Ollama (vlastní server)",
        "styl": "ollama",
        "adresa": "http://127.0.0.1:11434",
        "model": "qwen3.5:9b",
        "model_psani": "qwen3.6:35b-a3b",
        "venku": False,
        "popis": "Běží u tebe; kód i data neopouštějí síť.",
    },
    "openai": {
        "jmeno": "OpenAI nebo OpenAI-kompatibilní API",
        "styl": "openai",
        "adresa": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "model_psani": "gpt-4o-mini",
        "venku": True,
        "popis": "Sedí i na Groq, Together, GitHub Models nebo vLLM — stačí přepsat adresu.",
    },
    "einfra": {
        "jmeno": "e-INFRA CZ / MetaCentrum (OpenAI API)",
        "styl": "openai",
        "adresa": "https://llm.ai.e-infra.cz/v1",
        "model": "qwen3.5-397b-a17b",
        "model_psani": "qwen3.5-397b-a17b",
        "venku": True,
        "popis": "Modely CERIT-SC pro akademickou sféru. Klíč si dělá každý sám "
                 "v Chat WebUI (Accounts → API Keys); přesný název modelu zkopíruj "
                 "odtud ze seznamu.",
    },
    "anthropic": {
        "jmeno": "Anthropic (Claude)",
        "styl": "anthropic",
        "adresa": "https://api.anthropic.com",
        "model": "claude-sonnet-4-5",
        "model_psani": "claude-sonnet-4-5",
        "venku": True,
        "popis": "Klíč v hlavičce x-api-key; max_tokens doplníme sami.",
    },
    "gemini": {
        "jmeno": "Google Gemini",
        "styl": "gemini",
        "adresa": "https://generativelanguage.googleapis.com",
        "model": "gemini-2.5-flash",
        "model_psani": "gemini-2.5-pro",
        "venku": True,
        "popis": "Klíč z AI Studia; posílá se v adrese volání.",
    },
}
DEFAULT_PROVIDER = "ollama"


def _vychozi() -> dict:
    return {
        "ai": {
            "poskytovatel": os.environ.get("RPRAXE_PROVIDER", DEFAULT_PROVIDER),
            # viz docs/hosting.md: volba poskytovatele prostředím (pro nasazení bez UI)
            # RPRAXE_AI_ADRESA platí pro jakéhokoli poskytovatele; RPRAXE_OLLAMA
            # zůstává jako domecká alternativa (adresa Ollamy se tak zadávala dřív)
            "adresa": (os.environ.get("RPRAXE_AI_ADRESA") or os.environ.get("RPRAXE_OLLAMA")
                       or PROVIDERS[DEFAULT_PROVIDER]["adresa"]),
            "klic": os.environ.get("RPRAXE_AI_KEY", ""),
            "model": os.environ.get("RPRAXE_MODEL", ""),
            "model_psani": os.environ.get("RPRAXE_MODEL_WRITE", ""),
            "timeout": float(os.environ.get("RPRAXE_AI_TIMEOUT", "90")),
        },
        "prihlasovani": {
            "sso": False,
            "hlavka_jmeno": os.environ.get("RPRAXE_SSO_HEADER", "Remote-User"),
            "hlavka_role": os.environ.get("RPRAXE_SSO_ROLE_HEADER", ""),
            "tajemstvi": os.environ.get("RPRAXE_SSO_SECRET", ""),
            "role_z_skupin": {},
            "povolene_ucety": [],
        },
        "zaloha": {"cil": "", "ponechat": 7},
    }


def _slus(novy: dict) -> dict:
    """Doplň chybějící klíče ze výchozího nastavení (schéma se vyvíjí)."""
    zaklad = _vychozi()
    for sekce, hodnoty in zaklad.items():
        dostane = novy.get(sekce)
        if not isinstance(dostane, dict):
            novy[sekce] = hodnoty
            continue
        for k, v in hodnoty.items():
            dostane.setdefault(k, v)
    return novy


def load() -> dict:
    if not CONFIG_FILE.exists():
        return _vychozi()
    try:
        return _slus(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return _vychozi()


def save(data: dict) -> dict:
    with _LOCK:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        doc = CONFIG_FILE.with_suffix(".json.tmp")
        doc.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        # atomická výměna si nesmí nést práva z dočasného souboru — root 600 by
        # hostitelským skriptům (záloha) zablokoval čtení
        if CONFIG_FILE.exists():
            puv = CONFIG_FILE.stat()
            os.chmod(doc, stat.S_IMODE(puv.st_mode))
            os.chown(doc, puv.st_uid, puv.st_gid)
        else:
            os.chmod(doc, 0o600)
        doc.replace(CONFIG_FILE)
    return data


def set_cast(sekce: str, ** zmeny) -> dict:
    """Aktualizuj vybranou sekci; `None` hodnoty nech ostitut (ne nulovat)."""
    data = load()
    cil = data.setdefault(sekce, {})
    for k, v in zmeny.items():
        if v is not None:
            cil[k] = v
    return save(data)


def mask(value: str, videt: int = 3) -> dict:
    s = str(value or "")
    if not s:
        return {"nastaveno": False, "ukazka": ""}
    if len(s) <= 10:
        return {"nastaveno": True, "ukazka": "…" + s[-2:]}
    return {"nastaveno": True, "ukazka": s[:4] + "…" + s[-videt:]}


def ai_cfg() -> dict:
    data = dict(load()["ai"])
    zkratka = data.get("poskytovatel") or DEFAULT_PROVIDER
    zaklad = PROVIDERS.get(zkratka) or PROVIDERS[DEFAULT_PROVIDER]
    data["poskytovatel"] = zkratka
    data["styl"] = zaklad["styl"]
    data["venku"] = bool(zaklad.get("venku"))
    data["adresa"] = (data.get("adresa") or zaklad["adresa"]).rstrip("/")
    data["model"] = data.get("model") or zaklad["model"]
    data["model_psani"] = data.get("model_psani") or data["model"]
    data["timeout"] = float(data.get("timeout") or 90)
    return data


def sso_cfg() -> dict:
    return load()["prihlasovani"]


def sso_zapnuto() -> bool:
    cfg = sso_cfg()
    return bool(cfg.get("sso") and cfg.get("tajemstvi") and (cfg.get("hlavka_jmeno") or "").strip())


def providers_pro_ui() -> list[dict]:
    return [dict(zkratka=z, **cfg) for z, cfg in PROVIDERS.items()]
