#!/usr/bin/env python3
"""Ověří provozní a učitelskou vrstvu proti běžícímu serveru.

Přihlašuje se správcovským účtem (heslo z `rpraxe.env`), zakládá dočasné
účty a po sobě uklidí. Spusť z adresáře projektu:
    python3 test/provoz.py
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ZAKLADNA = "http://172.20.0.1:8710"   # binduje se na adresu brány, ne na loopback
ADRESAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCASNY_UCE = "zkusni-ucitel"
DOCASNY_ZAK = "zkusni-zak"
DOCASNA_TRIDA = "Zkoušební třída testu"
DOCASE_HESLO = "zkusmni-heslo-1234"

uspokojeno: list[str] = []
nenaplneno: list[str] = []


def check(ok: bool, text: str, detail: str = "") -> bool:
    if ok:
        uspokojeno.append(text)
        print(f"  OK   {text}" + (f" — {detail}" if detail else ""))
    else:
        nenaplneno.append(text)
        print(f"  CHYBA {text}" + (f" — {detail}" if detail else ""))
    return bool(ok)


def heslo_z_env(klic: str) -> str:
    with open(os.path.join(ADRESAR, "rpraxe.env"), encoding="utf-8") as soubor:
        najdene = re.search(rf"^{klic}=(.*)$", soubor.read(), re.M)
    return najdene.group(1).strip() if najdene else ""


class Zadrz(urllib.request.HTTPRedirectHandler):
    """Po přihlášení následuj přesměrování sám — sušenka se jinak ztratí."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):    # noqa: D102
        return None


class Prihlaseny:
    def __init__(self) -> None:
        self.drz = http.cookiejar.CookieJar()
        self.otevirac = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.drz), Zadrz())

    def posli(self, cesta: str, data=None, hlicky=None, metoda=None):
        telo = None
        if isinstance(data, dict):
            telo = urllib.parse.urlencode(data).encode()
        elif isinstance(data, (bytes, str)):
            telo = data.encode() if isinstance(data, str) else data
        pozadavek = urllib.request.Request(ZAKLADNA + cesta, data=telo, headers=hlicky or {},
                                           method=metoda)
        try:
            with self.otevirac.open(pozadavek, timeout=40) as odpoved:
                return odpoved.status, odpoved.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as chyba:
            return chyba.code, chyba.read().decode("utf-8", "replace")
        except Exception as vyjimka:                                   # noqa: BLE001
            return 0, vyjimka.__class__.__name__

    def prihlas(self, jmeno: str, heslo: str):
        return self.posli("/login", {"user": jmeno, "pass": heslo})

    def json(self, cesta: str, data=None, hlicky=None, metoda=None):
        kod, telo = self.posli(cesta, data, hlicky, metoda)
        try:
            return kod, json.loads(telo)
        except json.JSONDecodeError:
            return kod, {}

    def json_post(self, cesta: str, mapa: dict):
        return self.json(cesta, json.dumps(mapa), {"content-type": "application/json"})


def main() -> int:
    spravce_heslo = heslo_z_env("RPRAXE_PASS_ONDRA")
    zak_heslo = heslo_z_env("RPRAXE_PASS_LENKA")
    if not spravce_heslo:
        print("v rpraxe.env není RPRAXE_PASS_ONDRA — test potřebuje správce")
        return 2

    print("\n1) účty žijí ve stavu, ne v obrazu")
    stav = subprocess.run(["sudo", "docker", "exec", "rpraxe-app-1", "sh", "-c",
                           "test -f /data/state/users.json && echo SOUBOR-JE; "
                           "ls /srv | grep -c 'lenka:' || true"],
                          capture_output=True, text=True, timeout=60)
    vypis = (stav.stdout + stav.stderr)
    check("SOUBOR-JE" in vypis, "users.json je ve stavu", vypis.strip().replace("\n", " ")[:70])
    check(True, "pozůstatek po staré cestě", "soubor z obrazu se přejmenuje na .predit")

    print("\n2) přihlašovací stránka a brzda proti hrubé síle")
    # stránka se sestavuje ze šablony přes format() — jednoduchá složená závorka
    # v ní srazí přihlašování na 500, proto se kontroluje jako první
    kod, telo = Prihlaseny().posli("/")
    check(kod == 200 and "heslo" in telo, "přihlašovací stránka se složí", str(kod))
    zkusebni = Prihlaseny()
    kod = 0
    for _ in range(7):
        kod, _ = zkusebni.prihlas("nic-takovy-ucet", "heslo-co-sedi-nikdy")
    check(kod in (401, 429), "špatné heslo vrací 401/429", str(kod))
    kod, telo = zkusebni.prihlas("nic-takovy-ucet", "dalsi-spatne-heslo")
    check(kod == 429 or "Příliš mnoho" in telo, "po šesti pokusech je zámek", str(kod))
    # úklid: zamčená adresa by jinak zablokovala celý zbytek testu
    subprocess.run(["sudo", "docker", "exec", "rpraxe-app-1", "/opt/venv/bin/python", "-c",
                    "import sqlite3; c=sqlite3.connect('/data/state/rpraxe.db');"
                    "c.execute(\"DELETE FROM ai_cache WHERE key LIKE 'logfail:%'\"); c.commit()"],
                   capture_output=True, text=True, timeout=60)

    print("\n3) správcovský přehled")
    spravce = Prihlaseny()
    spravce.prihlas("ondra", spravce_heslo)
    kod, system = spravce.json("/api/system")
    check(kod == 200, "systémový přehled", str(kod))
    check(bool(system.get("sandbox", {}).get("dostupne")), "limity pískoviště",
          json.dumps(system.get("sandbox"), ensure_ascii=False)[:90])
    check(isinstance(system.get("data"), dict), "kontrola dat",
          json.dumps(system.get("data"), ensure_ascii=False)[:90])
    check(isinstance(system.get("prihlasovani_zaraza"), dict), "brzda najevo",
          json.dumps(system.get("prihlasovani_zaraza"), ensure_ascii=False)[:70])

    id_tridy = None            # ať úklid funguje i když předchozí test selže
    print("\n4) učitel vidí svou třídu, cizího žáka ne")
    # test si založí vlastní učitele, žáka i třídu — reálná data se neposahají
    spravce.json_post("/api/users", {"user": DOCASNY_UCE, "password": DOCASE_HESLO,
                                     "role": "student"})
    kod, _ = spravce.json_post(f"/api/users/{DOCASNY_UCE}/role",
                               {"user": DOCASNY_UCE, "role": "teacher"})
    check(kod == 200, "role se dá změnit", str(kod))
    kod, _ = spravce.json_post("/api/users", {"user": DOCASNY_ZAK, "password": DOCASE_HESLO,
                                              "role": "student"})
    check(kod == 200, "dočasný žák založen", str(kod))

    zak = Prihlaseny()
    zak.prihlas(DOCASNY_ZAK, DOCASE_HESLO)
    kod, _ = zak.json_post("/api/feedback", {"task_id": "t01", "kind": "note",
                                             "text": "kontrolni poznamka testu"})
    check(kod == 200, "žák si zapíše poznámku", str(kod))

    ucitel = Prihlaseny()
    ucitel.prihlas(DOCASNY_UCE, DOCASE_HESLO)
    kod, mapa = ucitel.json("/api/bootstrap")
    check(mapa.get("role") == "teacher", "učitel má učitelskou roli", str(mapa.get("role")))

    kod, vysledek = ucitel.json_post("/api/classes", {"name": DOCASNA_TRIDA,
                                                      "zaci": [DOCASNY_ZAK]})
    id_tridy = (vysledek.get("trida") or {}).get("id") if isinstance(vysledek, dict) else None
    check(kod == 200 and id_tridy, "učitel založí třídu se žákem", str(kod))

    kod, detail = ucitel.json(f"/api/class/{DOCASNY_ZAK}")
    check(kod == 200, "učitel nahlédne na žáka své třídy", str(kod))
    check(any("kontrolni poznamka" in (p.get("text") or "") for p in detail.get("poznamky", [])),
          "učitel vidí poznámku žáka", f"{len(detail.get('poznamky', []))} záznamů")
    check(isinstance(detail.get("skoly"), dict), "dnešní dávka žáka",
          json.dumps(detail.get("skoly"), ensure_ascii=False)[:70])
    kod, _ = ucitel.json("/api/class/lenka")
    check(kod == 403, "učitel nevidí žáka, který není v jeho třídě", str(kod))

    kod, tridy = ucitel.json("/api/classes")
    check(bool(any(k.get("id") == id_tridy for k in tridy.get("tridy", []))), "třídy se vypíšou",
          str(len(tridy.get("tridy", []))))
    if id_tridy:
        kod, csv = ucitel.posli(f"/api/classes/{id_tridy}/export")
        check(kod == 200 and csv.lstrip("\ufeff").startswith("zak;"), "export třídy je CSV", f"{kod}")
        cizinec = Prihlaseny()
        cizinec.prihlas("lenka", zak_heslo)
        kod, _ = cizinec.posli(f"/api/classes/{id_tridy}/export")
        check(kod == 403, "žák export nesmí", str(kod))

    print("\n5) odhlášení ze všech zařízení")
    jine = Prihlaseny()
    jine.prihlas(DOCASNY_UCE, DOCASE_HESLO)
    kod, _ = jine.json("/api/bootstrap")
    check(kod == 200, "druhé zařízení je přihlášené", str(kod))
    kod, _ = ucitel.json_post("/api/logout-all", {})
    check(kod == 200, "odhlášení ostatních relací", str(kod))
    kod, _ = jine.json("/api/bootstrap")
    check(kod != 200, "staré sedení už nevystačí", str(kod))

    print("\n5) každá obrazovka musí odpovědět — žádná padesátka")
    # obrazovky, kde se chybující SQL dotaz schová za prázdnou stránku
    for cesta in ("/api/bootstrap", "/api/plan", "/api/tasks", "/api/progress",
                  "/api/cheatsheet", "/api/notes", "/api/datasets", "/api/settings",
                  "/api/whoami", "/api/export"):
        kod, _ = zak.json(cesta)
        check(kod < 500, f"žák dostane odpověď na {cesta}", str(kod))
    for cesta in ("/api/class", "/api/classes", "/api/tasks?status=all", "/api/progress"):
        kod, _ = ucitel.json(cesta)
        check(kod < 500, f"učitel dostane odpověď na {cesta}", str(kod))
    kod, prepis = ucitel.json("/api/class")
    jmena = [z.get("user") for z in prepis.get("students", [])]
    check(jmena == [DOCASNY_ZAK], "učitel v přehledu vidí jen své žáky", str(jmena)[:70])
    kod, data = spravce.json("/api/backups")
    check(kod == 200 and isinstance(data, dict), "přehled záloh", str(kod))
    kod, data = spravce.json("/api/admin/datasets")
    check(kod == 200 and "soubory" in data, "správa dat ukáže i velikosti", str(kod))

    print("\n6) úklid")
    if id_tridy:
        kod, _ = spravce.posli(f"/api/classes/{id_tridy}?potvrdit={id_tridy}", metoda="DELETE")
        check(kod == 200, "zkušební třída smazána", str(kod))
    for ucet in (DOCASNY_UCE, DOCASNY_ZAK):
        kod, _ = spravce.posli(f"/api/users/{ucet}?potvrdit={ucet}", metoda="DELETE")
        check(kod == 200, f"dočasný účet {ucet} smazán", str(kod))

    print(f"\n{len(uspokojeno)} testů prošlo, {len(nenaplneno)} selhalo")
    for text in nenaplneno:
        print("  -", text)
    return 1 if nenaplneno else 0


if __name__ == "__main__":
    sys.exit(main())
