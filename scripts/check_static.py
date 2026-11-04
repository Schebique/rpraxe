#!/usr/bin/env python3
"""Ověří, že si index.html volá jen ty soubory, které v image opravdu jsou.

Strojová kontrola, ne dohled: stránka se vykreslí až z app.js, takže špatná
cesta udělá černou obrazovku bez jediné chyby v logu aplikace.
Spouští se při buildu image a při každém startu kontejneru.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

WEB = Path(os.environ.get("RPRAXE_WEB", "/srv/web"))


def mrtve_ovladaci(html: str, js: str) -> list[str]:
    """Tlačítka, na kterých nic není.

    Klik na tlačítko bez obsluhy se navenek tváří jako „nic se nestalo“ a v
    serverovém logu není vidět vůbec nic — přesně jako u záložky data.
    """
    mrtva = []
    for bid in re.findall(r'<button[^>]*\bid="([^"]+)"', html):
        if f'"#{bid}"' not in js and f"'#{bid}'" not in js:
            mrtva.append(f"tlačítko #{bid} nemá v app.js obsluhu")
    for skup in sorted({m for m in re.findall(r'(data-[a-z-]+)=', html)}):
        # v JS se čte buď atribut, nebo camelCase vlastnota datasetu (data-view → dataset.view)
        kusy = skup.removeprefix("data-").split("-")
        camel = kusy[0] + "".join(k.capitalize() for k in kusy[1:])
        if skup not in js and f"dataset.{camel}" not in js:
            mrtva.append(f"skupina ovládacích prvků [{skup}] nemá v app.js obsluhu")
    return mrtva


def chybejici_prvky(html: str, js: str) -> list[str]:
    """Prvky, které si app.js volá a nikde nevznikly.

    `$("#něco").onclick = …` na prvku, který v HTML není a ani se nedostaví,
    hodí `Cannot set properties of null` už při startu a aplikace je pak černá
    — proto to počítá až build, ne až první návštěvník.
    """
    exists = set(re.findall(r'id="([^"]+)"', html)) | set(re.findall(r'id="([^"]+)"', js))
    exists |= set(re.findall(r'''\.id\s*=\s*["']([\w-]+)''', js))       # prvky, které JS vytvoří sám
    # id sestavené v šabloně: id="${i("gh-url")}" — název je uvnitř výrazu
    exists |= set(re.findall(r'''id="\$\{[^{}]*["']([\w-]+)["']''', js))
    nacteno = set(re.findall(r"""(?:querySelector|querySelectorAll)\(\s*[\"']#([A-Za-z][\w-]*)""", js))
    nacteno |= set(re.findall(r"""\$\(\s*[\"']#([A-Za-z][\w-]*)""", js))
    return [f"#{i} si app.js volá, ale nikde takový prvek není" for i in sorted(nacteno - exists)]


def main() -> int:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    refs = [m for m in re.findall(r'(?:src|href)="(/static/[^"]+)"', html)
            if not m.startswith("//")]
    chybí = [r for r in refs if not (WEB / r.removeprefix("/static/")).is_file()]
    if chybí:
        print("CHYBI STATICKE SOUBORY (stranka by byla prazdna / bez editoru):")
        for c in chybí:
            print("  -", c)
        return 1
    if "app.js" not in html:
        print("index.html nivolal zadny app.js — stranka by byla prazdna")
        return 1
    js = (WEB / "app.js").read_text(encoding="utf-8")
    mrtve = mrtve_ovladaci(html, js) + chybejici_prvky(html, js)
    if mrtve:
        print(" MRTVE OVLADACI (klik na ne nic nedela):")
        for m in mrtve:
            print("  -", m)
        return 1
    print(f"staticka v poradku: {len(refs)} souboru odkazu, vsechny existuji; "
          f"vsechna tlačítka mají obsluhu; všechny volané prvky existují")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
