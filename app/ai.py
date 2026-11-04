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

from app import config as instance

# Konfigurace (poskytovatel, adresa, klíč, modely) se čte za chodu z app.config —
# správa ji mění v prohlížeči. Proměnné prostředí jsou jen výchozí hodnota, takže
# nasazení, která je nikdy nenastavila, se chovají jako dřív.

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


def modely_info() -> dict:
    """Co je právě nastavené — pro zobrazení ve správě."""
    cfg = instance.ai_cfg()
    return {"poskytovatel": cfg["poskytovatel"], "jmeno": instance.PROVIDERS[cfg["poskytovatel"]]["jmeno"],
            "adresa": cfg["adresa"], "model": cfg["model"], "model_psani": cfg["model_psani"],
            "venku": cfg["venku"], "klic": instance.mask(cfg.get("klic", ""))}


def _vystup_ollama(data: dict) -> str:
    return (data.get("message") or {}).get("content", "") or ""


def _vystup_openai(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    casti = msg.get("content")
    if isinstance(casti, list):          # některé brány vracejí pole částí
        casti = "".join(c.get("text", "") for c in casti if isinstance(c, dict))
    return casti or ""


def _vystup_anthropic(data: dict) -> str:
    return "".join(c.get("text", "") for c in (data.get("content") or []) if isinstance(c, dict))


def _vystup_gemini(data: dict) -> str:
    kandidati = data.get("candidates") or []
    if not kandidati:
        return ""
    casti = (kandidati[0].get("content") or {}).get("parts") or []
    return "".join(c.get("text", "") for c in casti if isinstance(c, dict))


def _rozeber(styl: str, messages: list[dict]) -> tuple[str, list[dict]]:
    """System prompt má každé API jinak — sjednotíme ho do (system, zprávy)."""
    system = "\n\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
    dalsi = [m for m in messages if m.get("role") != "system"]
    return system, dalsi


async def chat(messages: list[dict], model: str = "", temperature: float | None = None,
               json_mode: bool = False, ucel: str = "chat") -> str:
    """Pošli konverzaci do nastaveného modelu a vrať text odpovědi.

    `ucel="psani"` sahá po modelu pro tvorbu úloh, jinak po tom konverzačním.
    """
    cfg = instance.ai_cfg()
    model = model or (cfg["model_psani"] if ucel == "psani" else cfg["model"])
    ladka = float(temperature if temperature is not None else os.environ.get("RPRAXE_AI_LADKA", "0.4"))
    system, dalsi = _rozeber(cfg["styl"], messages)
    klice = {"Content-Type": "application/json"}
    if cfg.get("klic"):
        klice["Authorization"] = "Bearer " + cfg["klic"]
        klice["x-api-key"] = cfg["klic"]

    if cfg["styl"] == "ollama":
        adresu = cfg["adresa"] + "/api/chat"
        tele = {"model": model, "messages": messages, "stream": False,
                "options": {"temperature": ladka, "num_ctx": 6144}}
        if json_mode:
            tele["format"] = "json"
        cteni = _vystup_ollama
    elif cfg["styl"] == "anthropic":
        adresu = cfg["adresa"] + "/v1/messages"
        klice["anthropic-version"] = "2023-06-01"
        tele = {"model": model, "max_tokens": 2400, "temperature": ladka, "messages": dalsi}
        if system:
            tele["system"] = system
        cteni = _vystup_anthropic
    elif cfg["styl"] == "gemini":
        adresu = f'{cfg["adresa"]}/v1beta/models/{model}:generateContent'
        if cfg.get("klic"):
            adresu += "?key=" + cfg["klic"]
        tele = {"contents": [{"role": "user" if m["role"] == "user" else "model",
                              "parts": [{"text": m.get("content", "")}]} for m in dalsi],
                "generationConfig": {"temperature": ladka}}
        if system:
            tele["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            tele["generationConfig"]["responseMimeType"] = "application/json"
        cteni = _vystup_gemini
    else:                                            # openai a každá kompatibilní brána
        adresu = cfg["adresa"].rstrip("/") + "/chat/completions"
        tele = {"model": model, "messages": messages, "temperature": ladka}
        if json_mode:
            tele["response_format"] = {"type": "json_object"}
        cteni = _vystup_openai

    async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
        r = await client.post(adresu, json=tele, headers=klice)
        if r.status_code >= 400:
            raise RuntimeError(f"{cfg['poskytovatel']} vrátil {r.status_code}: {r.text[:200]}")
    return str(cteni(r.json())).strip()


async def list_models() -> list[str]:
    """Modely, které poskytovatel skutečně nabízí — pro výběr ve správě."""
    cfg = instance.ai_cfg()
    klice = {}
    if cfg.get("klic"):
        klice = {"Authorization": "Bearer " + cfg["klic"], "x-api-key": cfg["klic"]}
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            if cfg["styl"] == "ollama":
                r = await client.get(cfg["adresa"] + "/api/tags")
                return sorted(m["name"] for m in r.json().get("models", []))
            if cfg["styl"] == "gemini":
                r = await client.get(cfg["adresa"] + "/v1beta/models",
                                     params={"key": cfg.get("klic", "")})
                return sorted((m.get("name") or "").replace("models/", "")
                              for m in r.json().get("models", []))
            r = await client.get(cfg["adresa"].rstrip("/") + "/models", headers=klice)
            data = r.json().get("data") or r.json().get("models") or []
            return sorted(str(m.get("id") or m.get("name")) for m in data)
    except Exception:  # noqa: BLE001
        return []


async def available() -> tuple[bool, str]:
    cfg = instance.ai_cfg()
    modely = await list_models()
    if modely:
        return True, ", ".join(modely[:8])
    # někteří poskytovatelé seznam modelů nedají — zkusíme krátké volání
    try:
        odpoved = await chat([{"role": "user", "content": "Řekni jen ANO."}], temperature=0.0)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:200]
    return (True, odpoved[:120]) if odpoved else (False, "model odpověděl prázdně")


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
                             temperature=0.75 + attempt * 0.15, json_mode=True, ucel="psani")
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


REVIEW_SYSTEM = """Prohlížíš úlohu do cvičné soustavy R pro začátečníka. Hledáš jen závady; pochvaly nepíšeš. Vrať POUZE platný JSON bez ohraničení, s těmito poli:
{"zadani_sedí": true/false, "kontrola_měří_zadání": true/false, "obtížnost": <1-5>,
 "zavady": ["krátká věta", "..."], "opravený_check": "<R kód, jen když umíš opravit kontrolu, inak prázdný text>"}
Závažné závady: kontrola měří něco jiného než zadání; řešení kontrolou neprojde; úloha volá data, která k dispozici nejsou; zadání je dvousmyslné; obtížnost neodpovídá lekci.
"""


async def review_task(task: dict) -> dict:
    """Názor modelu k hotové úloze — pro lidské oko; rozhoduje pořád člověk.

    Texty se zkrátí, aby se vešly do kontextu: model má posoudit zadání proti
    kontrole, ne se probírat načítáním dat.
    """
    limity = {"title": 120, "zadani": 1600, "reseni": 2200, "check": 1600,
              "starter": 700, "nacti": 500, "hints": 400}
    kus = {"lesson": task.get("lesson"), "level": task.get("level"),
           "dataset": task.get("dataset"), "skills": task.get("skills")}
    for k, maxv in limity.items():
        h = task.get(k)
        if isinstance(h, list):
            h = "; ".join(str(x) for x in h)
        if h:
            kus[k] = str(h)[:maxv]
    pokusy = [{"role": "system", "content": REVIEW_SYSTEM},
              {"role": "user", "content": json.dumps(kus, ensure_ascii=False)}]
    surove = ""
    for zprávy in (pokusy, _zkracene(pokusy)):
        try:
            surove = await chat(zprávy, temperature=0.2, json_mode=True, ucel="psani")
        except Exception as exc:  # noqa: BLE001
            return {"proslo": False, "chyba": str(exc)[:200], "zavady": ["model není dostupný"]}
        data = _parse_json(surove)
        if data:
            break
    if not data:
        return {"proslo": False, "chyba": "model neodpověděl JSONem",
                "ukázka": str(surove)[:400], "zavady": []}
    zavady = [str(z) for z in (data.get("zavady") or []) if str(z).strip()][:8]
    meri = bool(data.get("kontrola_měří_zadání", data.get("kontrola meri zadani")))
    sedí = bool(data.get("zadani_sedí", True))
    if not meri:
        zavady.append("kontrola podle modelu neměří to, co žádá zadání")
    if not sedí:
        zavady.append("zadání je nejasné nebo dvousmyslné")
    return {"proslo": meri and sedí and not zavady,
            "obtížnost": _as_float(data.get("obtížnost"), 0.0),
            "opravený_check": str(data.get("opravený_check") or "")[:4000],
            "zavady": zavady}


FIX_SYSTEM = (
    "Jsi opravář úloh pro kurz R. Dostaneš úlohu, která neprošla strojovým "
    "ověřením, spolu s výstupem z R. Oprav ji tak, aby (a) vlastní řešení "
    "kontrolou prošlo, (b) prázdný kód kontrolou neprošel a (c) startovací "
    "kostka také neprošla. Kontrolu piš jako R kód, který vrací TRUE nebo "
    "list(pass=, msg=); očekávanou hodnotu počítej ze dat, ne ji piš napevno. "
    "Zadání měň jen tehdy, je-li skutečně nejasné. Vrať JEDEN JSON bez "
    "komentáře: {\"reseni\": \"...\", \"check\": \"...\", \"zadani\": \"...\", "
    "\"starter\": \"...\", \"nacti\": \"...\", \"duvod\": \"co a proč jsem změnil\"}"
)


async def fix_task(task: dict, detail: dict | None = None) -> dict:
    """Nech model úlohu přepsat tak, aby prošla. Výsledek je návrh — soudí člověk."""
    kus = {k: str(task.get(k) or "")[:2200] for k in ("zadani", "reseni", "check", "starter", "nacti")}
    kus["dataset"] = task.get("dataset")
    selhani = {k: (detail or {}).get(k) for k in ("reseni_proslo", "prazdny_kod_prosel",
                                                  "kostka_prosel", "duvody", "zprava_kontrolky")}
    zprávy = [{"role": "system", "content": FIX_SYSTEM},
              {"role": "user", "content": json.dumps(
                  {"uloha": kus, "selhani": selhani,
                   "vystup_z_R": str((detail or {}).get("vystup_reseni") or "")[:1500]},
                  ensure_ascii=False)}]
    surove = ""
    for pokus in (zprávy, _zkracene(zprávy)):
        try:
            surove = await chat(pokus, temperature=0.2, json_mode=True, ucel="psani")
        except Exception as exc:  # noqa: BLE001
            return {"chyba": str(exc)[:200]}
        data = _parse_json(surove)
        if data:
            break
    if not data:
        return {"chyba": "model neodpověděl JSONem", "ukázka": str(surove)[:300]}
    return {
        "reseni": str(data.get("reseni") or "")[:6000],
        "check": str(data.get("check") or data.get("kontrola") or "")[:6000],
        "zadani": str(data.get("zadani") or "")[:6000],
        "starter": str(data.get("starter") or "")[:3000],
        "nacti": str(data.get("nacti") or "")[:1500],
        "duvod": str(data.get("duvod") or "")[:800],
    }


def _zkracene(zprávy: list[dict]) -> list[dict]:
    """Druhý pokus bez detailů — kdyby první odpověď byla moc dlouhá na kontext."""
    zp = [dict(zprávy[0])]
    try:
        data = json.loads(zprávy[1]["content"])
        tenká = {k: data[k] for k in ("zadani", "check", "reseni") if k in data}
        zp.append({"role": "user", "content": json.dumps(tenká, ensure_ascii=False)})
    except (ValueError, KeyError):
        zp.append(dict(zprávy[1]))
    return zp


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
