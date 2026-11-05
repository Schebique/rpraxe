#!/usr/bin/env python3
"""Pokrytí překladů a doplnění slovníku.

`python3 scripts/preklady.py` … spočítá, kolik řetězců rozhraní má překlad, a
vypíše ty, které chybí. Návratová hodnota 1 = angličtina nebo slovenčina jsou
pod 95 % — ty se v nastavení nabízejí, takže hotové být musejí.

`python3 scripts/preklady.py --doplň` … zapíše překlady ze
`scripts/preklady_data.py` do `web/i18n.js` mezi značky (opakovatelné).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preklady_data                                        # noqa: E402

ADRESAR = Path(__file__).resolve().parent.parent
WEB = ADRESAR / "web"
I18N = WEB / "i18n.js"
MEZ = 0.95
ZNACKA = "/* --- doplněk překladů (scripts/preklady.py --doplň) --- */"
KONEC = "/* --- konec doplňku --- */"


def nabizene_jazyky() -> tuple[str, ...]:
    """Jazyky, které rozhraní nabízí — čte se ze stejného seznamu v i18n.js."""
    text = I18N.read_text(encoding="utf-8")
    shoda = re.search(r"const PREKLADY_HOTOVE\s*=\s*\[([^\]]*)\]", text)
    if not shoda:
        return ("en", "sk")
    kod = tuple(re.findall(r'"([a-z]{2})"', shoda.group(1)))
    return tuple(j for j in kod if j != "cs")     # čeština je zdroj, ta překládán není


NABIZENE = nabizene_jazyky()


def pouzite_retezce() -> list[str]:
    """Vše, co rozhraní žádá přeložit: t("…") a data-i18n v HTML."""
    nalez = set()
    text = (WEB / "app.js").read_text(encoding="utf-8")
    for shoda in re.finditer(r"\bt\(\s*[\"`]([^\"`]{1,160})[\"`]", text):
        nalez.add(shoda.group(1))
    for shoda in re.finditer(r'data-i18n="([^"]+)"', (WEB / "index.html").read_text(encoding="utf-8")):
        nalez.add(shoda.group(1))
    return sorted(nalez)


def slovniky() -> dict:
    """Vyhodnotí `web/i18n.js` v node a vrátí hotové slovníky."""
    if not I18N.exists():
        return {}
    kod = ("const fs=require('fs'),vm=require('vm');"
           "const ctx={};vm.createContext(ctx);"
           "vm.runInContext(fs.readFileSync(process.argv[1],'utf8')"
           "+'\\n;globalThis.__I=I18N;',ctx);"
           "console.log(JSON.stringify(ctx.__I));")
    pokus = subprocess.run(["node", "-e", kod, str(I18N)], capture_output=True, text=True, timeout=60)
    if pokus.returncode != 0:
        print(pokus.stderr.strip()[:500])
        return {}
    return json.loads(pokus.stdout)


def pokryti(slovnik: dict, retezce: list[str]) -> tuple[float, list[str]]:
    merene = [retez for retez in retezce if retez.strip()]
    chybi = [retez for retez in merene if retez not in slovnik]
    if not merene:
        return 1.0, []
    return 1.0 - len(chybi) / len(merene), chybi


def blok(text: str, hodnoty: dict) -> str:
    """Vytvoří (nebo obnoví) blok s překlady mezi značkami — lze pouštět znovu."""
    casti = []
    for index, jazyk in enumerate(NABIZENE):
        polozky = []
        for cesky, preklady in hodnoty.items():
            hodnota = preklady[index]
            if not hodnota:
                continue                       # prázdné pole překlad nedefinuje
            polozky.append('  "%s": "%s"' % (cesky.replace('"', '\\"'),
                                             hodnota.replace('"', '\\"')))
        if polozky:
            casti.append("Object.assign(I18N.%s, {\n%s\n});" % (jazyk, ",\n".join(polozky)))
    return ZNACKA + "\n" + "\n".join(casti) + "\n" + KONEC + "\n"


def main() -> int:
    if not I18N.exists():
        print(f"soubor {I18N} není")
        return 2
    if "--doplň" in sys.argv or "--doplN" in sys.argv:
        text = I18N.read_text(encoding="utf-8")
        novy = blok(text, preklady_data.PREKLADY)
        if ZNACKA in text:
            start = text.index(ZNACKA)
            konec = text.index(KONEC, start) + len(KONEC) + 1
            text = text[:start] + novy + text[konec:]
        else:
            text = text.rstrip() + "\n\n" + novy
        I18N.write_text(text, encoding="utf-8")
        print("doplněno %d řetězců do %s" % (len(preklady_data.PREKLADY), I18N.name))
        return 0

    prelozeno = slovniky()
    if not prelozeno:
        return 2
    nabizene = nabizene_jazyky()
    retezce = pouzite_retezce()
    print("nabízené jazyky: %s" % ", ".join(("cs",) + nabizene))
    print("řetězců v rozhraní: %d\n" % len(retezce))
    padlo = 0
    for jazyk in ("en", "sk", "de", "pl"):
        if jazyk not in prelozeno:
            print("%s: slovník chybí" % jazyk)
            if jazyk in nabizene:
                padlo += 1
            continue
        podil, chybi = pokryti(prelozeno[jazyk], retezce)
        znameni = "OK  " if podil >= MEZ else "MÁLO"
        povinnost = "" if jazyk in NABIZENE else "  (ve volbě jazyka se kvůli tomu neukáže)"
        print("%s %s: %5.1f %%  (chybí %d)%s" % (znameni, jazyk, podil * 100, len(chybi), povinnost))
        if podil < MEZ and jazyk in nabizene:
            padlo += 1
            for retez in chybi[:15]:
                print("      - %s" % retez)
            if len(chybi) > 15:
                print("      … a dalších %d" % (len(chybi) - 15))
    if padlo:
        print("\nnabízené jazyky nejsou hotové — buď je dodělat, nebo nechat filtrovat")
        return 1
    print("\nnabízené jazyky mají překlad")
    return 0


if __name__ == "__main__":
    sys.exit(main())
