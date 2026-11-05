#!/usr/bin/env python3
"""Test účtů a rolí bez serveru — stačí `python3 test/ucty.py`.

Obsahuje vrásky, které se v produkci opakovaly: role „teacher" se musí vrátit
jako teacher (kvůli tomu se učitelské účty vracívaly na studenta) a soubor účtů
nesmí nikdy vypadnout z datového adresáře.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import accounts                                        # noqa: E402

splneno: list[str] = []
selnano: list[str] = []


def check(ok: bool, text: str, detail: str = "") -> bool:
    if ok:
        splneno.append(text)
    else:
        selnano.append(text)
    print(f"  {'OK  ' if ok else 'CHY'} {text}" + (f" — {detail}" if detail else ""))
    return bool(ok)


def main() -> int:
    ok_env = {k: v for k, v in os.environ.items()}
    print("\nrole")
    for role in accounts.ROLES:
        check(accounts.normalize_role(role) == role,
              f"role '{role}' se vrátí jako '{role}'", accounts.normalize_role(role))
    for alias, cile in [("ucitel", "teacher"), ("lektor", "teacher"), ("nahled", "teacher"),
                        ("skolitel", "teacher"), ("zak", "student"), ("spravce", "admin"),
                        ("ROOT", "admin"), ("", "student"), ("blbost", "student")]:
        check(accounts.normalize_role(alias) == cile,
              f"alias '{alias}' -> {cile}", accounts.normalize_role(alias))

    print("\nsoubor účtů")
    try:
        os.environ.pop("RPRAXE_USERS_FILE", None)
        os.environ["RPRAXE_USERS"] = "lenka:student,ondra:admin"
        check(str(accounts.soubor_uctu()) == accounts.VYCHOZNI_SOUBOR,
              "výčet účtů se nesmí tvářit jako cesta", str(accounts.soubor_uctu()))
        os.environ["RPRAXE_USERS_FILE"] = str(Path(tempfile.gettempdir()) / "ucty.json")
        check(str(accounts.soubor_uctu()).endswith("ucty.json"),
              "vlastní cesta se respektuje", str(accounts.soubor_uctu()))
        os.environ["RPRAXE_USERS_FILE"] = "relativni/ucty.json"
        check(accounts.soubor_uctu().is_absolute(),
              "relativní cesta se strčí pod datový adresář", str(accounts.soubor_uctu()))
    finally:
        os.environ.clear()
        os.environ.update(ok_env)

    print("\núčty")
    with tempfile.TemporaryDirectory() as doctest:
        cesta = Path(doctest) / "users.json"
        uzivatele = accounts.load(cesta)
        os.environ.update({"RPRAXE_USERS": "lenka:student,ondra:admin,ucitel:teacher",
                           "RPRAXE_PASS_LENKA": "heslo-lenky-1",
                           "RPRAXE_PASS_ONDRA": "heslo-ondry-1",
                           "RPRAXE_PASS_UCITEL": "heslo-ucitele-1"})
        try:
            vygenerovane, doplnene = accounts.seed_from_env(uzivatele)
            check(set(uzivatele) == {"lenka", "ondra", "ucitel"}, "všechny účty vznikly",
                  ", ".join(uzivatele))
            check(uzivatele["ucitel"]["role"] == "teacher", "učitel je učitel",
                  uzivatele["ucitel"]["role"])
            check(not vygenerovane and not doplnene, "nic se nemusí domýšlet",
                  f"{vygenerovane} {doplnene}")
            check(accounts.check_pw("heslo-lenky-1", uzivatele["lenka"]["hash"]),
                  "heslo z nastavení sedí")

            uzivatele["lenka"]["role"] = "teacher"
            uzivatele["lenka"]["role_ruce"] = "dnes"
            uzivatele["lenka"]["changed"] = "dnes"
            accounts.save(cesta, uzivatele)
            druhe = accounts.load(cesta)
            os.environ["RPRAXE_PASS_LENKA"] = "jine-heslo-2"
            accounts.seed_from_env(druhe)
            check(druhe["lenka"]["role"] == "teacher",
                  "ručně změněná role přežije další start", druhe["lenka"]["role"])
            check(accounts.check_pw("heslo-lenky-1", druhe["lenka"]["hash"]),
                  "vlastní heslo si účet podrží")
            check(accounts.vynut_hesla_z_env(druhe) == ["lenka"],
                  "reset hesla podle nastavení zabere", str(druhe["lenka"].get("changed")))
            check(accounts.check_pw("jine-heslo-2", druhe["lenka"]["hash"]),
                  "po resetu platí heslo z nastavení")

            treti = accounts.load(cesta)
            jmena = accounts.jmena_ze_specu(os.environ["RPRAXE_USERS"])
            check(jmena == ["lenka", "ondra", "ucitel"], "výčet účtů se dá přečíst",
                  ", ".join(jmena))
            check(set(treti) == set(jmena), "nastavení a stav sedí", str(set(treti)))
        finally:
            for klice in ("RPRAXE_USERS", "RPRAXE_PASS_LENKA", "RPRAXE_PASS_ONDRA",
                          "RPRAXE_PASS_UCITEL"):
                os.environ.pop(klice, None)

    print(f"\n{len(splneno)} testů prošlo, {len(selnano)} selhalo")
    for text in selnano:
        print("  -", text)
    return 1 if selnano else 0


if __name__ == "__main__":
    sys.exit(main())
