#!/usr/bin/env python3
"""Uklidí ve slovnících `web/i18n.js`.

Klíč je živý, když se jeho české znění vyskytuje slovo od slova v `web/app.js`
nebo `web/index.html` — odtud totiž bere text rozhraní (`t("…")`) a translateDom
(textové uzly v HTML). Klíč, který se nikde nevyskytuje, je pozůstatek po
přepsané hlášce: zabírá místo v poměru pokrytí a nikdo ho nepřekládá.

Použití:
  python3 scripts/preklady_uklid.py            … jen report
  python3 scripts/preklady_uklid.py --uctej    … smaž mrtvé klíče
"""
from __future__ import annotations

import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
RADKY_PREKLADU = __import__("re").compile(r'^\s{2}"((?:[^"\\]|\\.)+)":')


def nacti() -> tuple[list[str], str]:
    radky = (WEB / "i18n.js").read_text(encoding="utf-8").splitlines()
    zdroj = "\n".join((WEB / jmeno).read_text(encoding="utf-8")
                      for jmeno in ("app.js", "index.html"))
    return radky, zdroj.replace('\\"', '"')


def main() -> int:
    radky, zdroj = nacti()
    mrtvi, zivi = [], set()
    for cislo, radek in enumerate(radky, start=1):
        shoda = RADKY_PREKLADU.match(radek)
        if not shoda:
            continue
        klic = shoda.group(1).replace('\\"', '"')
        if klic in zdroj or klic.strip() in zdroj:
            zivi.add(klic)
        elif klic not in zivi:
            mrtvi.append((cislo, klic))
    print("živých klíčů: %d, mrtvých výskytů: %d" % (len(zivi), len(mrtvi)))
    for cislo, klic in mrtvi[:25]:
        print("  ř. %4d  %s" % (cislo, klic))
    if len(mrtvi) > 25:
        print("  … a %d dalších" % (len(mrtvi) - 25))
    if "--uctej" not in sys.argv:
        print("\nbez změny — pust s --uctej")
        return 0
    smazat = {cislo for cislo, _ in mrtvi}
    nove = [radek for i, radek in enumerate(radky, start=1) if i not in smazat]
    (WEB / "i18n.js").write_text("\n".join(nove) + "\n", encoding="utf-8")
    print("\nsmazáno %d řádků s mrtvými klíči" % len(smazat))
    return 0


if __name__ == "__main__":
    sys.exit(main())
