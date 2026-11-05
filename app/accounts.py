"""Účty, role a přihlašování mimo heslo.

Role:
  student  – procvičuje, vidí jen sebe
  teacher  – vidí progress studentů, píše a spravuje úlohy, zapisuje úkoly
  admin    – plus správa účtů, nastavení modelu, záloh

Účty žijí v `users.json` (mimo DB), aby obnovění databáze nezměnila hesla,
která si lidé sami změnili. Soubor je sha2-mode 600 a mění se výměnou.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import stat
import time
from pathlib import Path

VYCHOZNI_SOUBOR = "/data/state/users.json"

ROLES = ("student", "teacher", "admin")
# vlastní názvy rolí jsou také platná hodnota. Bez toho „teacher" nikdo nezná a
# normalize_role z něj je výchozí „student" — přesně tak se učitelské účty
# vracívaly na studenta: správce v tabulce vybral učitele, uložil se student.
ROLE_ALIASES = {role: role for role in ROLES}
ROLE_ALIASES.update({"nahled": "teacher", "lektor": "teacher", "ucitel": "teacher",
                     "zak": "student", "skolitel": "teacher", "vyucujici": "teacher",
                     "root": "admin", "spravce": "admin"})

PBKDF2_ROUNDS = 240_000


def hash_pw(pw: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def legacy_scrypt_ok(pw: str, stored: str) -> bool:
    """Staré hesloULOŽENÉ skryptem; přežije, než si uživatel nastaví nové."""
    try:
        salt, dk = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(got.hex(), dk)
    except ValueError:
        return False


def check_pw(pw: str, stored: str) -> bool:
    if stored.count("$") == 3:
        _, rounds, salt, dk = stored.split("$")
        got = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(got.hex(), dk)
    return legacy_scrypt_ok(pw, stored)


def pw_is_legacy(stored: str) -> bool:
    return stored.count("$") != 3


def normalize_role(role: str) -> str:
    return ROLE_ALIASES.get((role or "").strip().lower(), "student")


def jmena_ze_specu(spec: str) -> list[str]:
    """Jména účtů z `RPRAXE_USERS` — aby šlo zkontrolovat, že nastavení sedí se stavem."""
    vysledek = []
    for chunk in (spec or "").replace(";", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            vysledek.append(chunk.partition(":")[0].strip().lower())
    return vysledek


def soubor_uctu() -> Path:
    """Kde účty žijí. Vždy pod datovým adresářem, nikdy ne v kořeni obrazu.

    `RPRAXE_USERS` je výčet účtů (`lenka:student,ondra:admin`), ne cesta — na
    cestu je vlastní `RPRAXE_USERS_FILE`. Dřív o tu jednu proměnnou soupeřily
    dvě věci a aplikace zapsala účty do souboru pojmenovaného podle celého
    výčtu, tedy doprostřed obrazu, kde záloha nic nenajde.
    """
    hrube = (os.environ.get("RPRAXE_USERS_FILE") or "").strip()
    if not hrube:
        stara = (os.environ.get("RPRAXE_USERS") or "").strip()
        hrube = stara if ("/" in stara or stara.endswith(".json")) else ""
    cesta = Path(hrube or VYCHOZNI_SOUBOR)
    if not cesta.is_absolute():                     # relativní cesta patří do stavu
        cesta = Path(VYCHOZNI_SOUBOR).parent / cesta
    return cesta


def presun_zbytky(cil: Path) -> list[str]:
    """Sloučí účty ze souboru z éry, kdy `RPRAXE_USERS` byla i cesta.

    Přednost má novější záznam; původní soubor se přejmenuje na `.predit`, aby
    se migrace neopakovala a šla ručně vrátit. Vrací jména přenesených účtů.
    """
    presunute: list[str] = []
    for stary in _stara_jmena_souboru():
        if not stary.exists():
            continue
        try:
            if stary.resolve() == cil.resolve():
                continue
            starsi = json.loads(stary.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            continue
        nyni = load(cil)
        for jmeno, zaznam in starsi.items():
            if not isinstance(zaznam, dict):
                continue
            soucasny = nyni.get(jmeno)
            if soucasny is None or float(zaznam.get("created") or 0) > float(soucasny.get("created") or 0):
                nyni[jmeno] = zaznam
                presunute.append(jmeno)
        if not presunute and not starsi:
            continue
        save(cil, nyni)
        try:
            stary.replace(stary.with_name(stary.name + ".predit"))
        except OSError:
            pass
    return presunute


def _stara_jmena_souboru() -> list[Path]:
    """Kam se účty psaly dřív: výčet účtů vyložený jako jméno souboru."""
    spec = (os.environ.get("RPRAXE_USERS") or "").strip()
    if not spec or "/" in spec:
        return []
    return [Path.cwd() / spec, Path(spec)]


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save(path: Path, users: dict) -> None:
    """Výměna souboru, která zachová vlastníka i režim z předchůdce.

    Kontejner běží jako root, kdežto `state/` na hostiteli vlastní běžný uživatel;
    bez přenosu uid/gid by hostitelské skripty (záloha) na soubor nedosáhly.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(users, indent=1, ensure_ascii=False), encoding="utf-8")
    if path.exists():
        st = path.stat()
        os.chmod(tmp, stat.S_IMODE(st.st_mode))
        try:
            os.chown(tmp, st.st_uid, st.st_gid)
        except PermissionError:
            pass
    else:
        tmp.chmod(0o600)
    tmp.replace(path)


def seed_from_env(users: dict) -> tuple[list[str], list[str]]:
    """Účty ze `RPRAXE_USERS="lenka:student,ondra:admin"`; heslo z `RPRAXE_PASS_<JMÉNO>`.

    Vrací dvojici: účty, které dostaly vygenerované heslo (první start bez
    nastavení, aby je aplikace jednorázově vypsal do logu), a účty, kterým se
    doplnilo heslo z env.

    Heslo z `RPRAXE_PASS_<JMÉNO>` platí, dokud si ho účet sám nepřepíše. Pak je
    závazek na druhé straně: `changed` v users.json a env se už neptá. Role se z
    env přepíší taky, ale jen dokud je správce ručně nezměnil (`role_ruce`).
    """
    spec = os.environ.get("RPRAXE_USERS", "").strip()
    generated: list[str] = []
    doplnene: list[str] = []
    pairs = []
    if spec:
        for chunk in spec.replace(";", ",").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            name, _, role = chunk.partition(":")
            pairs.append((name.strip().lower(), normalize_role(role)))
    else:                                                   # zpětná kompatibilita
        pairs = [("lenka", "student"), ("ondra", "teacher")]
    for name, role in pairs:
        env = "RPRAXE_PASS_" + name.upper().replace("-", "_")
        pw = os.environ.get(env)
        if name in users:
            zaznam = users[name]
            if zaznam.get("role") != role and not zaznam.get("role_ruce"):
                zaznam["role"] = role
            if pw and not zaznam.get("changed") and not check_pw(pw, zaznam.get("hash") or ""):
                zaznam["hash"] = hash_pw(pw)                # env je stále platný zdroj
                doplnene.append(name)
            continue
        if not pw:
            pw = secrets.token_urlsafe(9)
            generated.append(name)
        rec = {"hash": hash_pw(pw), "role": role,
               "created": time.time(), "generated": not os.environ.get(env)}
        if not os.environ.get(env):
            rec["first_pw"] = pw            # ať ho provozatel může přečíst v users.json (mód 600)
        users[name] = rec
    return generated, doplnene


def vynut_hesla_z_env(users: dict, jmena: set[str] | None = None) -> list[str]:
    """Jednorázová záchrana: nastaví hesla podle env i u účtů, které už je mají.

    `RPRAXE_RESET_HESLA=1` (nebo seznam jmen) — použije se, když se sejde starý
    soubor účtů s novým nastavením a nikdo se nedostane dovnitř. Vrací jména,
    kterým se heslo změnilo; pak je třeba proměnnou zase vypnout.
    """
    obnove: list[str] = []
    for chunk in os.environ.get("RPRAXE_USERS", "").replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        name = chunk.partition(":")[0].strip().lower()
        if jmena and name not in jmena:
            continue
        pw = os.environ.get("RPRAXE_PASS_" + name.upper().replace("-", "_"))
        if pw and name in users and not check_pw(pw, users[name].get("hash") or ""):
            users[name] = {**users[name], "hash": hash_pw(pw), "changed": False}
            users[name].pop("first_pw", None)
            obnove.append(name)
    return obnove


def create_user(users: dict, name: str, pw: str, role: str) -> dict:
    name = (name or "").strip().lower()
    if not name or not all(c.isalnum() or c in "-._" for c in name):
        raise ValueError("jméno musí být bez mezer a diakritiky (písmena, číslice, - . _)")
    if name in users:
        raise ValueError("takový účet už existuje")
    if len(pw) < 8:
        raise ValueError("heslo musí mít aspoň 8 znaků")
    users[name] = {"hash": hash_pw(pw), "role": normalize_role(role),
                   "created": time.time(), "generated": False}
    return users[name]


def sso_user_from_headers(headers, trusted: bool) -> tuple[str, str] | None:
    """Přihlášení přes důvěryhodnou bránu (Authelia / forward_auth).

    `RPRAXE_SSO_HEADER` (výchozí `Remote-User`) a volitelně `RPRAXE_SSO_ROLE_HEADER`
    (`Remote-Groups`). Header se bere jen z prověřené adresy brány — inak by si
    jakýkoli klient vymyslel jméno.
    """
    name_hdr = os.environ.get("RPRAXE_SSO_HEADER", "").strip()
    if not name_hdr or not trusted:
        return None
    name = (headers.get(name_hdr) or "").strip().lower()
    if not name:
        return None
    role = "student"
    role_hdr = os.environ.get("RPRAXE_SSO_ROLE_HEADER", "").strip()
    if role_hdr:
        groups = (headers.get(role_hdr) or "").lower()
        if "admin" in groups:
            role = "admin"
        elif any(g in groups for g in ("teacher", "lektor", "ucitel", "skola")):
            role = "teacher"
    return name, role
