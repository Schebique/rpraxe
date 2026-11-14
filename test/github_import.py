"""Dovoz banky úloh z GitHubu — rozbor odkazů, stahování, normalizace, ověření.

Spouští se uvnitř nádoby, kde je vidět sandbox:
    docker compose exec rpraxe /opt/venv/bin/python -m pytest test/github_import.py -q
Síťové testy se samy vynechají, když nádoba nemá východ ven.
"""
import asyncio
import os
import traceback

try:
    import pytest
except ModuleNotFoundError:      # obraz neobsahuje pytest — test musí jít spustit i bez něj
    class _NahrazeniPytest:
        class mark:                       # pytest.mark.skipif jako dekorátor
            @staticmethod
            def skipif(podminka, reason=""):
                def ozdobni(funkce):
                    return funkce
                return ozdobni

        @staticmethod
        def skipif(podminka, reason=""):
            def ozdobni(funkce):
                return funkce
            return ozdobni

        @staticmethod
        def raises(typ):
            class Ochoz:
                value = None

                def __enter__(self):
                    return self

                def __exit__(self, druh, vyjimka, stopa):
                    if druh is None or not issubclass(druh, typ):
                        raise AssertionError("očekávaná výjimka %s přišla %s" % (typ, druh))
                    self.value = vyjimka
                    return True
            return Ochoz()

    pytest = _NahrazeniPytest()

from app import main, manage

DOSKY = os.environ.get("RPRAXE_TEST_NET", "1") == "1"


def test_odkazy():
    rozloz = manage._rozloz_github
    assert rozloz("https://github.com/jan-novak/ulohy-r") == ("jan-novak", "ulohy-r", "", "")
    v, r, ref, cesta = rozloz("https://github.com/jan-novak/ulohy-r/blob/main/ukoly.json")
    assert (v, r, ref, cesta) == ("jan-novak", "ulohy-r", "main", "ukoly.json")
    assert rozloz("jan-novak/ulohy-r/podklad/ukoly.json")[3] == "podklad/ukoly.json"
    assert rozloz("git@github.com:jan-novak/ulohy-r.git")[0] == "jan-novak"
    assert rozloz("https://raw.githubusercontent.com/jan/ulohy/main/ukoly.json") == \
        ("jan", "ulohy", "main", "ukoly.json")
    assert rozloz("https://example.com/ulohy.json") is None
    assert rozloz("") is None


def test_normalizace():
    uloha = manage._normalizuj_ulohu(
        {"název": "Průměr", "zadání": "Spočítej průměr", "řešení": "mean(x)",
         "kontrola": "TRUE", "dovednosti": "mean, sum", "minuty": "3",
         "obtížnost": "2.5", "napovědy": "pomocí mean()"}, 0, "github:x/y", "ondra")
    assert uloha["title"] == "Průměr" and uloha["zadani"] == "Spočítej průměr"
    assert uloha["reseni"] == "mean(x)" and uloha["check"] == "TRUE"
    assert uloha["skills"] == ["mean", "sum"]
    assert uloha["minutes"] == 3 and abs(uloha["level"] - 2.5) < 1e-9
    assert uloha["status"] == "draft" and uloha["source"] == "github:x/y"
    assert uloha["id"].startswith("y-"), uloha["id"]
    # anglické klíče a řetězcové zadání
    druha = manage._normalizuj_ulohu({"title": "T", "task": ["a", "b"], "solution": "s",
                                      "check": "TRUE", "id": "moje-1"}, 1, "soubor:banka.json", "ondra")
    assert druha["zadani"] == "a\nb" and druha["id"] == "moje-1"
    assert manage._normalizuj_ulohu({"title": "bez řešení"}, 2, "github:x/y", "ondra") is None


@pytest.mark.skipif(not DOSKY, reason="nádoba nemá východ na GitHub")
def test_stazeni_realneho_souboru():
    """Veřejný soubor, který JSON není → jasná chyba, ne tichý průšvih."""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as nadehle:
        asyncio.run(manage._stahni_github("tidyverse", "dplyr", "main", "DESCRIPTION"))
    assert "není platný JSON" in str(nadehle.value.detail)


@pytest.mark.skipif(not DOSKY, reason="nádoba nemá východ na GitHub")
def test_cizi_repozitar():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as nadehle:
        asyncio.run(manage._stahni_github("neexistuje-tenhle", "repo", "main", "ukoly.json"))
    assert "404" in str(nadehle.value.detail)


def test_prezkouseni_importovane_ulohy():
    """Importuje se to, co projde; špatná kontrola zůstane konceptem."""
    spravna = manage._normalizuj_ulohu(
        {"id": "t-test-1", "title": "Dva", "zadani": "x <- 1 + 1", "reseni": "x <- 1 + 1",
         "check": "x == 2", "starter": "x <- NA"}, 0, "github:test/banka", "ondra")
    spatna = manage._normalizuj_ulohu(
        {"id": "t-test-2", "title": "Špatně", "zadani": "x <- 1 + 1", "reseni": "x <- 1 + 1",
         "check": "x == 3"}, 1, "github:test/banka", "ondra")

    async def spust():
        return await main.overeni_spustenim(spravna), await main.overeni_spustenim(spatna)

    (dobra, spatne) = asyncio.run(spust())
    assert dobra["ok"] is True, dobra
    assert spatne["ok"] is False and spatne["duvody"], spatne


if __name__ == "__main__":
    # bez pytestu: projdi vše, co začíná na test_, a vyhlas výsledek
    selhani = 0
    for jmeno, funkce in sorted(globals().items()):
        if not jmeno.startswith("test_") or not callable(funkce):
            continue
        try:
            funkce()
            print("  OK   " + jmeno)
        except Exception as vyjimka:                      # noqa: BLE001
            selhani += 1
            posledni = traceback.TracebackException.from_exception(vyjimka)
            print("  CHYBA " + jmeno + " — " + "".join(list(posledni.format())[-3:])[:400])
    print("pytest bez pytestu: %d selhání" % selhani)
    raise SystemExit(1 if selhani else 0)
