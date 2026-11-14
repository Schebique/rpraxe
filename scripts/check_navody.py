#!/usr/bin/env python3
"""Navody musi jit z kopirovani.

Kodove bloky v *.md se maji dat zkopirovat a spustit, takze tady hlidame, ze:

  1. `docker compose exec <sluzka>` jmenuje sluzku, ktera v compose souboru je,
  2. soubory, na ktere prikaz v repozitari ukazuje, v repozitari skutecne jsou,
  3. zadny prikaz neceka image s tagem, ktery `docker build` ani GHCR nedava
     (presne tohle zpusobilo, ze rychly start neskoncil bezicim kontejnerem),
  4. kazda `RPRAXE_*` ze seznamu promennych ma skutecny vyznam v kodu,
  5. markdown odkazy na soubory v repozitari vedou.

Spousti se bez Dockeru, klidne i pred buildem:
    python3 scripts/check_navody.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHYBY = []

# ktere tagy obrazu ve skutecnosti existuji: GHCR publishuje `latest`, `master`
# a numericke `X.Y.Z`; local `docker build` bez -t nevznikne vubec
POVOLENE_TAGY = re.compile(r"^(latest|master|main|ci|\d+\.\d+(\.\d+)?)$")


def nacti(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def markdown_soubory():
    preskocit = {".git", "node_modules", "__pycache__", "state", "datasets", "venv"}
    for root, dirs, soubory in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in preskocit)
        for s in sorted(soubory):
            if s.endswith(".md"):
                yield os.path.relpath(os.path.join(root, s), ROOT)


def kodove_bloky(text):
    """[(jazyk, radek, kod)] pro kazdy ``` blok v souboru."""
    najdene = []
    blok = None
    for cislo, radek in enumerate(text.splitlines(), 1):
        zahaj = re.match(r"^\s*```(\w*)\s*$", radek)
        if zahaj and blok is None:
            blok = [zahaj.group(1), cislo, []]
        elif blok is not None and radek.strip() == "```":
            jazyk, start, linky = blok
            najdene.append((jazyk, start, "\n".join(linky)))
            blok = None
        elif blok is not None:
            blok[2].append(radek)
    if blok is not None:
        CHYBY.append("blokovani ``` neni uzavrene (radek %d)" % blok[1])
    return najdene


def sluzky_a_tagy():
    """({nazvy sluzeb}, {vychozi tagy}) z docker-compose*.yml v koreni."""
    sluzby, tagy = set(), set()
    for rel in sorted(os.listdir(ROOT)):
        if not re.match(r"docker-compose.*\.ya?ml$", rel):
            continue
        text = nacti(rel)
        try:
            import yaml

            data = yaml.safe_load(text) or {}
            for nazev, sluzba in (data.get("services") or {}).items():
                sluzby.add(nazev)
                image = str((sluzba or {}).get("image", ""))
                tagy.update(t for _v, t in re.findall(r"\$\{(\w+):-([^}]*)\}", image))
        except Exception:
            # bez PyYAML: aspon klice pod `services:`, ne i jinde v souboru
            services = text.split("services:", 1)
            if len(services) > 1:
                for radek in services[1].splitlines():
                    m = re.match(r"^  ([a-z][-\w]*):\s*$", radek)
                    if m:
                        sluzby.add(m.group(1))
                tagy.update(re.findall(r"image:\s*rpraxe:\$\{\w+:-([^}]*)\}", services[1]))
    return sluzby, tagy


def kontroluj_prikazy(rel, start, kod):
    for offset, radek in enumerate(kod.splitlines(), 1):
        r = radek.strip()
        kam = "%s:%d" % (rel, start + offset)
        if not r or r.startswith("#"):
            continue
        if r.endswith("\\"):
            # prikaz pokracuje na dalsim radku - tag zatim nemuzeme posoudit
            r = r[:-1]
            m_check_build = False
        else:
            m_check_build = True
        # 1) sluzka v `compose exec`
        m = re.search(r"compose\b.*?\bexec\b((?:\s+-\w+)*)\s+(\S+)", r)
        if m and m.group(2) not in SLUZBY:
            CHYBY.append(
                "%s: `compose exec %s` -- takova sluzka neni (%s)"
                % (kam, m.group(2), ", ".join(sorted(SLUZBY)))
            )
        # 2) soubor, ktery navod otevira
        for misto in re.findall(
            r"(?:cat|cp|head|-f|-o|\./)\s+((?:app|runner|agent|scripts|docs|deploy|r|test|tasks)/[\w./-]+)",
            r,
        ):
            misto = misto.rstrip(".,;)>")
            if not os.path.exists(os.path.join(ROOT, misto)):
                CHYBY.append("%s: %s v repozitari neni" % (kam, misto))
        # 3) tag obrazu, ktery bude hledat `docker compose up`
        if m_check_build:
            for jmeno in re.findall(r"docker build\b[^|;&]*?-t\s+[\"']?([\w./-]+(?::[\w.$}{\-]+)?)", r):
                if "/" in jmeno:
                    # obraz miri do cizi registry (hub.cerit.io/...), compose ho nehleda
                    continue
                tag = jmeno.rsplit(":", 1)[1] if ":" in jmeno else None
                if tag is None:
                    CHYBY.append("%s: `docker build -t %s` bez tagu, compose takovy image nehleda" % (kam, jmeno))
                elif "$" not in tag and not POVOLENE_TAGY.match(tag):
                    CHYBY.append("%s: tag `%s` nevznikne buildem ani z GHCR" % (kam, tag))
        for tag in re.findall(r"docker tag \S+\s+rpraxe:([\w.\-]+)", r):
            if not POVOLENE_TAGY.match(tag):
                CHYBY.append("%s: tag `%s` nevznikne buildem ani z GHCR" % (kam, tag))


def kontroluj_compose():
    """sluzba, ktera se da postavit z repozitare, musi to v compose i rikat.

    Bez `build:` si `docker compose up` (i s --build) jde image stahnout. Pokud
    ho žádná veřejná registry nezná, návod v README padne na „pull access
    denied" — tohle se stalo naopravdu, jen co byl compose bez `build:`.
    """
    for rel in sorted(os.listdir(ROOT)):
        if not re.match(r"docker-compose.*\.ya?ml$", rel):
            continue
        try:
            import yaml

            data = yaml.safe_load(nacti(rel)) or {}
        except Exception:
            continue  # rozepsanost hlídá `compose config`, tady nechal bych jen šum
        for nazev, sluzba in (data.get("services") or {}).items():
            sluzba = sluzba or {}
            if not sluzba.get("build"):
                CHYBY.append("%s: služba `%s` nemá `build:` — `up --build` je bez něj jen pull" % (rel, nazev))
            if sluzba.get("pull_policy") != "build":
                CHYBY.append(
                    "%s: služba `%s` nemá `pull_policy: build` — compose by si jel pro image do registry"
                    % (rel, nazev)
                )


def kontroluj_odkazy(rel, text):
    for cilo in re.findall(r"\]\((?!https?://|mailto:|#)([^)\s]+)", text):
        cesta = cilo.split("#")[0]
        if cesta and not os.path.exists(os.path.join(ROOT, os.path.dirname(rel), cesta)):
            CHYBY.append("%s: odkaz `%s` nevede" % (rel, cilo))


def kontroluj_promenne():
    """kazda `RPRAXE_*` ze seznamu promennych musi neco delat nekde v repozitari."""
    kod = ""
    for slozka in ("app", "runner", "scripts", "docker", "r", "agent"):
        adresar = os.path.join(ROOT, slozka)
        if not os.path.isdir(adresar):
            continue
        for root, dirs, soubory in os.walk(adresar):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for s in soubory:
                if s.endswith((".py", ".R", ".sh")):
                    kod += nacti(os.path.relpath(os.path.join(root, s), ROOT))
    kod += nacti("Dockerfile")
    # compose a CI jsou taky "kod": RPRAXE_IMAGE_TAG ci RPRAXE_PORT se cte az tam
    for rel in sorted(os.listdir(ROOT)):
        if re.match(r"docker-compose.*\.ya?ml$", rel):
            kod += nacti(rel)
    workflowy = os.path.join(ROOT, ".github", "workflows")
    if os.path.isdir(workflowy):
        for s in sorted(os.listdir(workflowy)):
            kod += nacti(os.path.join(".github", "workflows", s))
    # hesla se jmenuji RPRAXE_PASS_<JMENO_UCTU> - v kodu zije jen prefix
    DYNAMICKE_PREFIXY = ("RPRAXE_PASS_", "RPRAXE_HESLO_")
    for rel in ("README.md", "docs/hosting.md", ".env.example", "rpraxe.env.example"):
        if not os.path.exists(os.path.join(ROOT, rel)):
            continue
        for jmeno in sorted(set(re.findall(r"\bRPRAXE_[A-Z0-9_]+\b", nacti(rel)))):
            if jmeno not in kod and not jmeno.startswith(DYNAMICKE_PREFIXY):
                CHYBY.append("%s: %s se v kodu nikde necete" % (rel, jmeno))


def main():
    global SLUZBY
    SLUZBY, _tagy = sluzky_a_tagy()
    for rel in markdown_soubory():
        text = nacti(rel)
        for jazyk, start, kod in kodove_bloky(text):
            if jazyk in ("sh", "bash", "shell", "console", "shell-session", "console-session", ""):
                kontroluj_prikazy(rel, start, kod)
        kontroluj_odkazy(rel, text)
    kontroluj_promenne()
    kontroluj_compose()
    if CHYBY:
        for chyba in sorted(set(CHYBY)):
            print(chyba)
        print("\n%d problemu v navodech" % len(set(CHYBY)))
        return 1
    print("navody sedí: %d souboru, sluzky %s" % (len(list(markdown_soubory())), ", ".join(sorted(SLUZBY))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
