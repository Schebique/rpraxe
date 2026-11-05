#!/usr/bin/env python3
"""Projde barvy v obou motivech — tokeny, vlastní CSS i téma editoru.

Dělá tři věci:
1. Změří kontrasy mezi tokeny (text vs. podklad) ve tmavém i světlém motivu.
2. Projde `web/style.css` a u každého pravidla, které sahá na barvu textu nebo
   na podklad, spočítá kontrast proti podkladu, na kterém ta barva sedí. Průsvitné
   podklady (rgba) počítá jako kompozici nad podkladem, na kterém leží.
3. Podívá se i do vlajkového tématu editoru — světlý motiv jinak dědí pastelové
   barvy stavěné na tmavé pozadí a ty jsou na bílé špatně čitelné.

Spusť `python3 scripts/kontrast.py`; návratová hodnota 1 znamená, že něco
nedosahuje WCAG AA (4,5:1 běžný text, 3,0:1 velký text a grafika).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ADRESAR = Path(__file__).resolve().parent.parent
WEB = ADRESAR / "web"
CSS = WEB / "style.css"
EDITOR_THEME = WEB / "vendor" / "material-darker.css"
HTML = WEB / "index.html"
JS = WEB / "app.js"

MEZ = 4.5
MEZ_VELKY = 3.0

# (popisek, token textu, token podkladu, velký text?)
PARY = [
    ("běžný text", "--fg", "--bg", False),
    ("text na kartě", "--fg", "--bg2", False),
    ("text na výplni", "--fg", "--bg3", False),
    ("text v bloku kódu", "--fg", "--code", False),
    ("výstup v konzoli", "--fg", "--console", False),
    ("rámeček kouče", "--fg", "--coach", False),
    ("vybraná úloha", "--fg", "--taskon", False),
    ("pruhovaná tabulka", "--fg", "--zebra", False),
    ("text pod ztmavením", "--fg", "--scrim", False),
    ("popisek", "--muted", "--bg", False),
    ("popisek na kartě", "--muted", "--bg2", False),
    ("tichá poznámka", "--dim", "--bg2", False),
    ("tichá poznámka na pozadí", "--dim", "--bg", False),
    ("odkaz", "--accent", "--bg", False),
    ("odkaz na kartě", "--accent", "--bg2", False),
    ("důvod proč", "--accent2", "--bg", False),
    ("důvod proč na kartě", "--accent2", "--bg2", False),
    ("pozitivní hláška", "--ok", "--bg2", False),
    ("pozitivní na pozadí", "--ok", "--bg", False),
    ("chybová hláška", "--bad", "--bg2", False),
    ("varování", "--warn", "--bg2", False),
    ("text na hlavním tlačítku", "--on-accent", "--accent", True),
    ("štítek na akcentní barvě", "--on-accent", "--accent", False),
]

# Podklady, na kterých text v appce bývá.
POZADI = ("--bg", "--bg2", "--bg3")
# Dekorace bez textu — ty posuzujeme jen jako grafiku (3:1) nebo vůbec ne
DEKORACE = (">i", ".spark", "img", "svg", "scrollbar", "::selection",
            ".CodeMirror-cursor", ".sep", ".modal", "hr", ".plotrow")
# Velký text / nadpisy: stačí 3:1
VELKY = ("h1", "h2", "h3", ".big", "legend", ".brand")


def barva(retez: str):
    """Vrátí ((r,g,b), alfa) nebo None. Umí #hex i rgb/rgba."""
    retez = (retez or "").strip()
    if retez.startswith("#"):
        ozn = retez[1:]
        if len(ozn) == 3:
            ozn = "".join(z * 2 for z in ozn)
        if len(ozn) not in (6, 8):
            return None
        slozky = tuple(int(ozn[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        alfa = int(ozn[6:8], 16) / 255.0 if len(ozn) == 8 else 1.0
        return slozky, alfa
    if retez.startswith("rgb"):
        cisla = re.findall(r"[\d.]+%?", retez)
        if len(cisla) < 3:
            return None
        slozky = tuple(float(c.rstrip("%")) / (100.0 if c.endswith("%") else 255.0)
                       for c in cisla[:3])
        alfa = float(cisla[3]) if len(cisla) > 3 else 1.0
        return slozky, alfa
    return None


def jas(slovky) -> float:
    def dil(h):
        return h / 12.92 if h <= 0.03928 else ((h + 0.055) / 1.055) ** 2.4
    return sum(dil(v) * k for v, k in zip(slovky, (0.2126, 0.7152, 0.0722)))


def pomer(a, b) -> float:
    svetly, tmavy = sorted([jas(a), jas(b)], reverse=True)
    return (svetly + 0.05) / (tmavy + 0.05)


def kompozice(poprva, podklad):
    """Průsvitná barva nad podkladem — počítá s tím, co je pod ní."""
    slozky, alfa = poprva
    if alfa >= 0.999:
        return slozky
    spodni = podklad if podklad else (0.0, 0.0, 0.0)
    return tuple(alfa * v + (1 - alfa) * d for v, d in zip(slozky, spodni))


def tokeny(text: str, motiv: str) -> dict:
    """Sloučí `:root` a bloky `html[data-theme="<motiv>"]`; motiv přebíjí základ."""
    vysledek = {}
    for hlavicka, telo in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
        hlavicka = hlavicka.strip()
        if "--" not in telo:
            continue
        if hlavicka != ":root" and (motiv not in hlavicka or "data-theme" not in hlavicka):
            continue
        for klic, hodnota in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", telo):
            vysledek[klic] = hodnota.strip()
    return vysledek


def slovky(hodnota: str, hodnoty: dict, podklad=None, hloubka: int = 0):
    """Rozbalí `var(--x)` a vrátí RGB skutečného podkladu (kompozice + gradient)."""
    if hloubka > 8 or not hodnota:
        return None
    hodnota = hodnota.strip()
    if "gradient" in hodnota:
        for kus in re.findall(r"#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|var\(--[\w-]+\)", hodnota):
            vysledek = slovky(kus, hodnoty, podklad, hloubka + 1)
            if vysledek:
                return vysledek
        return None
    if hodnota.startswith("color-mix") or hodnota.startswith("calc"):
        return None
    odkaz = re.fullmatch(r"var\((--[\w-]+)(?:\s*,\s*([^)]+))?\)", hodnota)
    if odkaz:
        nahrazeno = hodnoty.get(odkaz.group(1)) or (odkaz.group(2) or "")
        if not nahrazeno:
            return None
        return slovky(nahrazeno.strip(), hodnoty, podklad, hloubka + 1)
    usek = hodnota if hodnota.startswith("rgb") else hodnota.split()[0]
    nalez = barva(usek)
    if not nalez:
        return None
    return kompozice(nalez, podklad)


def pravidla(text: str) -> dict:
    """Sloučí deklara­ce pro každý selektor — v CSS se přidávají i přepisují."""
    vysledek: dict[str, dict] = {}
    for selektor, telo in re.findall(r"([^{}@]+)\{([^{}]*)\}", text):
        selektor = selektor.strip().splitlines()[-1].strip()
        if not selektor or selektor.startswith(":root"):
            continue
        spojene = dict(vysledek.get(selektor, {}))
        spojene.update(dict(re.findall(r"([-\w]+)\s*:\s*([^;]+);?", telo)))
        vysledek[selektor] = spojene
    return vysledek


def plati_pro(selektor: str, motiv: str) -> bool:
    """Pravidlo vázané na `data-theme="..."` se hodnotí jen pro svůj motiv."""
    vazano = re.findall(r'data-theme\s*=\s*"([\w-]+)"', selektor)
    return motiv in vazano if vazano else True


def ma_pozadi(text: str) -> set:
    """Třídy, které si někde v CSS nesou vlastní podklad — barvu textu k nim
    nelze posuzovat proti běžné výplni, vždycky sedí na svém."""
    prvky = set()
    for selektor, deklarace in pravidla(text).items():
        if not (deklarace.get("background") or deklarace.get("background-color")):
            continue
        for kus in selektor.split(","):
            prvky.update(popisek_posledniho(kus))
    return prvky


def popisek_posledniho(selektor: str) -> set:
    """Výrazy, kterými selektor končí — barví se právě ten poslední výraz."""
    vysledek = set()
    for kus in selektor.split(","):
        kus = kus.strip()
        if not kus:
            continue
        posledni = kus.split()[-1]
        vysledek.update(re.findall(r"[.#]?[-\w]+", posledni))
        vysledek.update(t for t in re.findall(r"[-\w]+", posledni))
    return vysledek


def prohled(text: str, hodnoty: dict, motiv: str, jmeno: str = "style.css") -> list:
    """Najde pravidla, kde je text čitelně hůř čitelný, než má být."""
    najde = []
    s_pozadim = ma_pozadi(text)
    zaklad = {klic: slovky(hodnoty.get(klic, ""), hodnoty) for klic in POZADI}
    zaklad = {klic: hodnota for klic, hodnota in zaklad.items() if hodnota}
    vychozi_text = slovky(hodnoty.get("--fg", ""), hodnoty)
    for selektor, deklarace in pravidla(text).items():
        if not plati_pro(selektor, motiv):
            continue
        dekorace = any(st in selektor for st in DEKORACE)
        velky = dekorace or any(st in selektor for st in VELKY)
        mez = MEZ_VELKY if velky else MEZ
        podklad_karty = zaklad.get("--bg2")
        pozadi = deklarace.get("background-color") or deklarace.get("background") or ""
        barva_textu = slovky(deklarace.get("color", ""), hodnoty, podklad_karty)
        barva_pozadi = slovky(pozadi, hodnoty, zaklad.get("--bg")) if pozadi else None

        if barva_textu and barva_pozadi:
            hodnota = pomer(barva_textu, barva_pozadi)
            if hodnota < mez:
                najde.append((jmeno, selektor, "text na svém podkladu", hodnota, mez))
        elif barva_pozadi and not dekorace and vychozi_text:
            # text se dědí od rodiče, ve výchozím stavu je to --fg
            hodnota = pomer(barva_pozadi, vychozi_text)
            if hodnota < mez:
                najde.append((jmeno, selektor, "podklad bez barvy textu", hodnota, mez))
        elif barva_textu and zaklad and not dekorace:
            if popisek_posledniho(selektor) & s_pozadim:
                continue                     # barva textu patří k vlastnímu podkladu
            kontrasty = {klic: pomer(barva_textu, podklad) for klic, podklad in zaklad.items()}
            nejlepsi = max(kontrasty.values())
            if nejlepsi < mez:                 # špatné na všech běžných podkladech
                klic = max(kontrasty, key=kontrasty.get)
                najde.append((jmeno, selektor, f"text na {klic}", kontrasty[klic], mez))
    return najde


def editor(hodnoty: dict, motiv: str) -> list:
    """Barvy syntaxe z vlajkového tématu — na světlém pozadí se musí přepsat."""
    if not EDITOR_THEME.exists():
        return []
    text = EDITOR_THEME.read_text(encoding="utf-8")
    prepsane = set()
    for selektor in pravidla(CSS.read_text(encoding="utf-8")):
        if "data-theme" in selektor and motiv in selektor:
            prepsane.update(re.findall(r"\.cm-[\w-]+|\.CodeMirror-[\w-]+", selektor))
    pozadi_editoru = slovky(hodnoty.get("--code", ""), hodnoty)
    if not pozadi_editoru:
        return []
    najde = []
    videne = set()
    for selektor, deklarace in pravidla(text).items():
        if "color" not in deklarace:
            continue
        trida = next((s for s in re.findall(r"\.cm-[\w-]+|\.CodeMirror-[\w-]+", selektor)), None)
        if not trida or trida in prepsane or trida in videne:
            continue
        videne.add(trida)
        slozky_textu = slovky(deklarace["color"], hodnoty, pozadi_editoru)
        if not slozky_textu:
            continue
        hodnota = pomer(slozky_textu, pozadi_editoru)
        if hodnota < MEZ:
            najde.append(("material-darker.css", trida, "barva syntaxe", hodnota, MEZ))
    return najde


def chybějící_prepsani(text: str) -> list:
    """Tokeny ze `:root`, které světlý motiv nepřepisuje.

    Tady se schovává ta nepříjemná třída chyb: základ je tmavý, světlá varianta
    na něj nedosáhne a výsledek je tmavý podklad ve světlém motivu (nebo tmavý
    text na něm). Token, který se v CSS vůbec nepoužívá, nevadí.
    """
    zaklad = tokeny(text, "dark")
    light = tokeny(text, "light")
    absence = []
    for klic, hodnota in zaklad.items():
        if klic in light or "gradient" in hodnota:
            continue
        if klic not in text.replace(klic + ":", "", 1):
            continue
        nalez = barva(hodnota)
        if not nalez:
            continue
        if jas(kompozice(nalez, (1.0, 1.0, 1.0))) < 0.25:
            absence.append((klic, hodnota))
    return absence


def main() -> int:
    if not CSS.exists():
        print(f"soubor {CSS} není")
        return 2
    text = CSS.read_text(encoding="utf-8")
    chyby = []

    for motiv in ("dark", "light"):
        hodnoty = tokeny(text, motiv)
        karta = slovky(hodnoty.get("--bg2", ""), hodnoty)
        print(f"\n== {motiv} — tokeny ==")
        for popisek, klic_textu, klic_pozadi, velky in PARY:
            slozky_textu = slovky(hodnoty.get(klic_textu, ""), hodnoty, karta)
            pozadi_token = slovky(hodnoty.get(klic_pozadi, ""), hodnoty, karta)
            if not slozky_textu or not pozadi_token:
                chyby.append((motiv, popisek, 0.0))
                print(f"  ?      {popisek:<28} chybí token {klic_textu} / {klic_pozadi}")
                continue
            hodnota = pomer(slozky_textu, pozadi_token)
            mez = MEZ_VELKY if velky else MEZ
            if hodnota < mez:
                chyby.append((motiv, popisek, hodnota))
            print(f"  {'OK' if hodnota >= mez else 'SPAD'}    {popisek:<28} {hodnota:5.1f}:1   "
                  f"{hodnoty.get(klic_textu)} na {hodnoty.get(klic_pozadi)}  (min {mez})")

        nalez = prohled(text, hodnoty, motiv) + editor(hodnoty, motiv)
        print(f"\n== {motiv} — pravidla ==")
        if not nalez:
            print("  všechna pravidla s barvou dosahují AA")
        for soubor, selektor, druh, hodnota, mez in sorted(nalez, key=lambda r: r[3]):
            chyby.append((motiv, f"{selektor} ({druh})", hodnota))
            print(f"  SPAD  {selektor:<52} {hodnota:5.1f}:1  {druh} (min {mez})  {soubor}")

    absence = chybějící_prepsani(text)
    if absence:
        print("\ntmavé tokeny, které světlý motiv nepřepisuje:")
        for klic, hodnota in absence:
            print(f"   {klic:<14} {hodnota}")
        chyby.extend(("light", f"token {klic} bez světlé varianty", 0.0)
                     for klic, _ in absence)
    else:
        print("\nsvětlý motiv přepisuje všechny tmavé tokeny")

    pevne = []
    for soubor in (HTML, JS):
        if not soubor.exists():
            continue
        for shoda in re.finditer(r"(?:style=\"[^\"]*|color\s*[:=]\s*['\"]?\s*)(#[0-9a-fA-F]{3,8})",
                                 soubor.read_text(encoding="utf-8")):
            pevne.append(f"{soubor.name}: {shoda.group(1)}")
    if pevne:
        print(f"\npevné barvy mimo tokeny ({len(pevne)}):")
        for radek in pevne[:12]:
            print("  ", radek)
        print("  → raději token, ať to sedí v obou motivech")
    else:
        print("\nHTML ani JS nesahají po pevné barvě — vše jde přes tokeny")

    if chyby:
        print(f"\n{len(chyby)} párů pod WCAG AA")
        return 1
    print("\n všechny barvy procházejí WCAG AA v obou motivech")
    return 0


if __name__ == "__main__":
    sys.exit(main())
