#!/usr/bin/env python3
"""Doplní chybějící překlady přes lokální model a zapíše je do preklady_data.py.

Jednorázová údržba: `python3 scripts/preklady_doplnt.py` … přeloží to, co hlásí
`scripts/preklady.py`, a vyhodnotí výsledek jako tabulku. Překlady z modelu se
do `web/i18n.js` dostaną až po `scripts/preklady.py --doplň` — mezi tím je vidět
do diffu, takže je lze zkontrolovat.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preklady                                              # noqa: E402

ADRESA = "http://172.20.0.1:11434/api/generate"
MODEL = "qwen3.6:35b-a3b"


def model(vyzva: str, cas: int = 600) -> str:
    data = json.dumps({"model": MODEL, "prompt": vyzva, "stream": False,
                       "think": False, "options": {"temperature": 0.1, "num_ctx": 16384}}).encode()
    zadaní = urllib.request.Request(ADRESA, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(zadaní, timeout=cas) as odpoved:
        return json.loads(odpoved.read().decode()).get("response", "").strip()


def preklad(retezce: list[str], cil: str, navedeni: str) -> dict:
    """Přeloží dávku řetězců; vrací {česky: cizky}."""
    vysled = {}
    for i in range(0, len(retezce), 30):
        davka = retezce[i:i + 30]
        vyzva = (
            f"Jsi překladatel rozhraní web aplikace pro výuku R. Přelož každou českou "
            f"textovou část do {cil}. \n{navedeni}\n"
            "Vrať POUZE platný JSON objekt, kde klíč je přesně ten český text "
            "(včetně teček, pomlček a tečky na konci) a hodnota překlad. "
            "Bez vysvětlení, bez markdown, bez ```.\n\nČeské texty:\n"
            + json.dumps(davka, ensure_ascii=False, indent=1))
        odpoved = model(vyzva)
        zacetek, konec = odpoved.find("{"), odpoved.rfind("}")
        if zacetek < 0 or konec < 0:
            print(f"      dávka {i}: model se nevyjádřil ke JSON", file=sys.stderr)
            continue
        try:
            data = json.loads(odpoved[zacetek:konec + 1])
        except Exception as chyba:                         # noqa: BLE001
            print(f"      dávka {i}: špatný JSON ({chyba})", file=sys.stderr)
            continue
        for retez in davka:
            hodnota = data.get(retez)
            if isinstance(hodnota, str) and hodnota.strip():
                vysled[retez] = hodnota.strip().replace('"', "'")
        print(f"      dávka {i}: {len([r for r in davka if r in vysled])}/{len(davka)}")
    return vysled


def main() -> int:
    prelozeno = preklady.slovniky()
    if not prelozeno:
        return 2
    retezce = preklady.pouzite_retezce()
    data_soubor = Path(__file__).with_name("preklady_data.py")
    existujici = {}
    if data_soubor.exists():
        prostori = {}
        exec(compile(data_soubor.read_text(encoding="utf-8"), str(data_soubor), "exec"), prostori)
        existujici = dict(prostori.get("PREKLADY", {}))

    jazyky = {"en": ("angličtiny", "Tykáš studentům (you), styl stručný a přátelský, "
                               "odborné výrazy obvyklé v R komunitě (task, hint, sandbox)."),
              "sk": ("slovenčiny", "Používej slovenské ekvivalenty, ne češtinu; "
                                    "tykej (ty), technické výrazy ponech (sandbox, model, dataset).")}
    for jazyk, (nazev, navedeni) in jazyky.items():
        chybi = [r for r in retezce if r not in prelozeno.get(jazyk, {}) and r not in existujici]
        if not chybi:
            print(f"{jazyk}: nic chybějícího")
            continue
        print(f"{jazyk}: překládám {len(chybi)} řetězců")
        hotovo = preklad(chybi, nazev, navedeni)
        for retez, hodnota in hotovo.items():
            en, sk = existujici.get(retez, ("", ""))
            if jazyk == "en":
                existujici[retez] = (hodnota, sk)
            else:
                existujici[retez] = (en, hodnota)

    radky = ["# Doplněk překladů: český zdroj → (angličtina, slovenčina).",
             "# Přes `scripts/preklady.py --doplň` se dostane do web/i18n.js.",
             "PREKLADY = {"]
    for retez in sorted(existujici):
        en, sk = existujici[retez]
        radky.append("    %r: (%r, %r)," % (retez, en, sk))
    radky.append("}")
    data_soubor.write_text("\n".join(radky) + "\n", encoding="utf-8")
    print(f"zapsáno {len(existujici)} položek → {data_soubor.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
