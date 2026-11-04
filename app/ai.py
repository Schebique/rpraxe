"""AI vrstva — lokální model na Kozlikovi (ollama-gate), žádný externí cloud.

Dvě role:
  1) kouč – vysvětlí chybu / napoví, ale nevezme studentovi práci (Sokratovský styl)
  2) autor – vygeneruje novou úlohu se syntetickými daty; tu musí schválit
     automat: řešení musí projít vlastní kontrolou v runneru.
"""
from __future__ import annotations

import json
import os
import re

import httpx

OLLAMA = os.environ.get("RPRAXE_OLLAMA", "http://192.168.0.162:11434")
MODEL_CHAT = os.environ.get("RPRAXE_MODEL", "qwen3.5:9b")
MODEL_WRITE = os.environ.get("RPRAXE_MODEL_WRITE", "qwen3.6:35b-a3b")
TIMEOUT = float(os.environ.get("RPRAXE_AI_TIMEOUT", "90"))

COACH_SYSTEM = """Jsi zkušená lektorka R, která doprovází začátečnici (Lenka) při denním \
procvičování. Kurz: Zpracovávání výzkumných dat v R (RStudio, tidyverse, dplyr, ggplot2).
Pravidla:
- Odpovídej česky, stručně (max 5 vět), tykaj.
- NIKDY nevpisuj hotové řešení úlohy. Polož otázku nebo napiš napovědu, která vede k vlastnímu nápadu.
- Když studentka chybuje v syntaxi, vysvětli princip (co R čeká), ne konkrétní znaky pro tuto úlohu.
- Nepoužívej emoji. Nebasni. Když nevíš, řekni to.
"""

TASK_SYSTEM = """Píšeš úlohy do cvičného systému R pro úplnou začátečnici. Vrať POUZE platný JSON \
bez markdown ohraničení. Formát:
{
 "title": "krátky nadpis",
 "lesson": <1-11>,
 "minutes": <3-6>,
 "level": <1.0-5.0>,
 "skills": ["dplyr", "pipes"],
 "dataset": "<name.csv or null>",
 "nacti": "<R one-liner which loads data, e.g. x <- read.csv(\\"name.csv\\") or empty>",
 "zadani": "<zadani cesky, max 3 vety, muzes pouzit backticks>",
 "starter": "<R skeleton, 1-4 radky>",
 "hints": ["<napoveda 1>", "<napoveda 2>"],
 "check": "<R kod, ktery vrati TRUE/FALSE nebo list(pass=, msg=); pouzivej helpery .v_num(got, want), .v_txt(got, want), .v_df(got, want), .v_spam(msg), .v_plot(got); pocitej ocekavanou hodnotu primo z dat, nenazaduj cisla napevno>",
 "reseni": "<R reseni, ktere kontrolu splni>"
}
Pravidla: dostupne balicky dplyr, tidyr, ggplot2, readr, forcats, lubridate, jsonlite. \
Datove soubory: jen ty, ktere jsou uvedeny jako povolene. Pomucka: kontrola bezi ve stejnem \
prostredi jako reseni, muze volat read.csv("...") znovu.
"""


async def chat(messages: list[dict], model: str = "", temperature: float = 0.4,
               json_mode: bool = False) -> str:
    model = model or MODEL_CHAT
    payload = {"model": model, "messages": messages, "stream": False,
               "options": {"temperature": temperature, "num_ctx": 6144}}
    if json_mode:
        payload["format"] = "json"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{OLLAMA}/api/chat", json=payload)
        r.raise_for_status()
        return (r.json().get("message") or {}).get("content", "").strip()


async def list_models() -> list[str]:
    """Modely dostupné na lokální Ollamě — pro výběr v nastavení uživatele."""
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(f"{OLLAMA}/api/tags")
        return sorted(m["name"] for m in r.json().get("models", []))
    except Exception:  # noqa: BLE001
        return []


async def list_models() -> list[str]:
    """Modely na lokální Ollamě — výběr v nastavení uživatele."""
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(f"{OLLAMA}/api/tags")
        return sorted(m["name"] for m in r.json().get("models", []))
    except Exception:  # noqa: BLE001
        return []


async def available() -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(f"{OLLAMA}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
        return True, ", ".join(models[:8])
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


async def coach_hint(task: dict, code: str, error: str | None, check_msg: str | None,
                     kind: str = "hint", model: str = "", jazyk: str = "cs") -> str:
    ctx = [
        f"Úloha: {task.get('title')}",
        f"Zadání: {task.get('zadani')}",
        f"Dovednosti: {', '.join(task.get('skills') or [])}",
        f"Kód studentky:\n```r\n{(code or '')[:1800]}\n```",
    ]
    if error:
        ctx.append(f"Chyba z R:\n{error[:800]}")
    if check_msg:
        ctx.append(f"Vzkaz kontrolky: {check_msg[:400]}")
    if jazyk != "cs":
        ctx.append(f"Odpověz jazykem {jazyk} (studentka si tak nastavila rozhraní).")
    if kind == "error":
        ask = ("Vysvětli POZORU, co ta chyba znamená v principu a na co se má zeptat sama sebe. "
               "Neprozradíš konkrétní opravný kód.")
    elif kind == "solution_review":
        ask = "Ohodnoť její řešení 1 větou a napiš jednu věcnou poznámku pro příště (co je zvykem udělat hezčí)."
    else:
        ask = "Dej jedna krátkou napovědu, která ji nasměruje, ale neřeší úlohu za ni."
    try:
        return await chat([{"role": "system", "content": COACH_SYSTEM},
                           {"role": "user", "content": "\n\n".join(ctx) + "\n\n" + ask}],
                          model=model, temperature=0.5)
    except Exception as exc:  # noqa: BLE001
        return f"(AI kouč není zrovna dostupný: {exc.__class__.__name__}) Zkus to samá – přečti si zadání nahlas a rozdej si ho na menší kroky."


async def generate_task(lesson: int, focus_skills: list[str], datasets: list[str],
                        level: float, avoid: list[str]) -> dict | None:
    prompt = (
        f"Vytvoř JEDNU novou úlohu.\n"
        f"- Lekce kurzu: {lesson}\n"
        f"- Dovednosti k procviceni: {', '.join(focus_skills) or 'volne'}\n"
        f"- Obtiznost 1-5: {level:.1f} (1 = uplne zacatek, 5 = slozitejsi aggregace)\n"
        f"- Povolene datove soubory (bez techto nepocitej): {', '.join(datasets)}\n"
        f"- Nepakuj po vzkazich: {', '.join(avoid[:12])}\n"
        f"- Musi jit zkontrolovat automaticky; ocekavanou hodnotu vypoctej v check z dat."
    )
    for attempt in range(2):
        try:
            raw = await chat([{"role": "system", "content": TASK_SYSTEM},
                              {"role": "user", "content": prompt}],
                             model=MODEL_WRITE, temperature=0.75 + attempt * 0.15, json_mode=True)
        except Exception:  # noqa: BLE001
            continue
        data = _parse_json(raw)
        if not data:
            continue
        data["source"] = "llm"
        data["lesson"] = _as_int(data.get("lesson"), lesson)
        data["minutes"] = min(max(_as_int(data.get("minutes"), 4), 2), 8)
        data["level"] = min(max(_as_float(data.get("level"), level), 0.5), 5.0)
        if data.get("dataset") and data["dataset"] not in datasets:
            data["dataset"] = None
            data["nacti"] = ""
        for key in ("title", "zadani", "check", "reseni"):
            if not str(data.get(key) or "").strip():
                data = None
                break
        if data:
            if not data.get("hints"):
                data["hints"] = ["Rozděl si to na kroky a každý vypiď zvlášť.", "Koukni na tahák k lekci."]
            data["id"] = "llm-" + re.sub(r"[^a-z0-9]+", "-", data["title"].lower())[:34].strip("-")
            return data
    return None


def _parse_json(raw: str) -> dict | None:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < 0:
        return None
    try:
        obj = json.loads(raw[start:end + 1])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _as_int(v, default):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _as_float(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default
