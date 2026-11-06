#!/usr/bin/env python3
"""Kontrola provázanosti: routy vs. volání z prohlížeče, tlačítka vs. handlery.

Spusť z adresáře projektu:  python3 test/provaznost.py
Vypíše routy, které nic v webu nevolá, a ovládací prvky, na které nic nenavazuje.
"""
from __future__ import annotations

import re
from pathlib import Path

ADRESAR = Path(__file__).resolve().parent.parent
PY = [ADRESAR / "app" / "main.py", ADRESAR / "app" / "manage.py"]
JS = [ADRESAR / "web" / "app.js", ADRESAR / "web" / "i18n.js"]
HTML = ADRESAR / "web" / "index.html"

cesty_py: set[str] = set()
for soubor in PY:
    if soubor.exists():
        text = soubor.read_text(encoding="utf-8", errors="replace")
        cesty_py |= set(re.findall(r'@(?:app|router)\.(?:get|post|put|delete)\(\s*"([^"]+)"', text))

js = "\n".join(s.read_text(encoding="utf-8", errors="replace") for s in JS if s.exists())
volani = set(re.findall(r"/api/[A-Za-z0-9_/{}$.:\-]+", js))
volani |= set(re.findall(r"`(/api/[^`$]*)", js))
# odkazy v HTML volají API taky — bez nich kontrolor hlásí falesné sirotky
html_text = HTML.read_text(encoding="utf-8", errors="replace") if HTML.exists() else ""
volani |= set(re.findall(r"""['"](/api/[^'"?#]*)""", html_text))


def normalizuj(cesta: str) -> str:
    cesta = re.sub(r"\{[^}]*\}", "*", cesta)
    cesta = re.sub(r"\$\{[^}]*\}", "*", cesta)
    return cesta.rstrip("/")


pouzite = {normalizuj(v) for v in volani}


def pouzito(cesta: str) -> bool:
    n = normalizuj(cesta)
    for p in pouzite:
        if p == n or p.startswith(n + "/") or n.startswith(p + "/") or p.rstrip("*").rstrip("/") == n.rstrip("*").rstrip("/"):
            if len(p.split("/")) >= 3:
                return True
    return False


osiero = sorted(c for c in cesty_py if c.startswith("/api") and not pouzito(c))
print(f"rout celkem {len(cesty_py)}, volání z webu {len(volani)}")
print("\nROUTY, KTERÉ WEB NEVOLÁ:")
for c in osiero:
    print("  ", c)

# tlačítka a odkazy v HTML, která nikdo neošetřuje
html = HTML.read_text(encoding="utf-8", errors="replace")
idcka = set(re.findall(r'<(?:button|a|input|select|div|span|form)[^>]*\bid="([^"]+)"', html))
data_akce = set(re.findall(r'data-(?:view|action|akce)="([^"]+)"', html))
reaguje = set(re.findall(r'getElementById\(\s*[\'"]([^\'"]+)[\'"]\s*\)', js))
reaguje |= set(re.findall(r'\$\(\s*[\'"]#?([A-Za-z0-9_\-]+)[\'"]\s*\)', js))
reaguje |= set(re.findall(r'data-view=.{0,40}', js))
nic_nereaguje = sorted(i for i in idcka if i not in reaguje and i.lower() not in js.lower())
print(f"\nID v HTML bez vazby v JS ({len(nic_nereaguje)}):")
for i in nic_nereaguje[:40]:
    print("  ", i)
print(f"\ndata-view v HTML: {sorted(data_akce)[:30]}")
zadane = {d for d in data_akce if d.startswith("view") is False}
print("akce bez handleru:", sorted(a for a in zadane if a.lower() not in js.lower())[:20])

# chybějící překlady
ople = ADRESAR / "web" / "preklady.js"
if ople.exists():
    pre = ople.read_text(encoding="utf-8", errors="replace")
    pouzite_klice = set(re.findall(r"""(?:t|preklad|tlacitko)\(\s*['"]([a-z0-9_.]{3,40})['"]""", js))
    kazdy = {}
    for jazyk in ("cs", "en", "de", "es"):
        nalez = re.search(rf'\b{jazyk}\s*:\s*\{{', pre)
        kazdy[jazyk] = len(set(re.findall(r'"([a-z0-9_.]{3,40})"\s*:', pre[nalez.start():]))) if nalez else 0
    chybi = sorted(k for k in list(pouzite_klice)[:4000] if f'"{k}"' not in pre)
    print(f"\nklíče použité v JS: {len(pouzite_klice)}; chybějící v předloze: {len(chybi)}")
    for k in chybi[:15]:
        print("   chybí:", k)
