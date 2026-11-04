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

ROLES = ("student", "teacher", "admin")
ROLE_ALIASES = {"nahled": "teacher", "lektor": "teacher", "ucitel": "teacher",
                "student": "student", "zak": "student", "admin": "admin", "root": "admin"}

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


def seed_from_env(users: dict) -> list[str]:
    """Účty ze `RPRAXE_USERS="lenka:student,ondra:admin"`; heslo z `RPRAXE_PASS_<JMÉNO>`.

    Vrací seznam účtů, které dostaly vygenerované heslo (při prvním startu bez
    nastavení), aby je aplikace mohla jednorázově vypsat do logu.
    """
    spec = os.environ.get("RPRAXE_USERS", "").strip()
    generated: list[str] = []
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
        if name in users:
            if users[name].get("role") != role:
                users[name]["role"] = role
            continue
        env = "RPRAXE_PASS_" + name.upper().replace("-", "_")
        pw = os.environ.get(env)
        if not pw:
            pw = secrets.token_urlsafe(9)
            generated.append(name)
        rec = {"hash": hash_pw(pw), "role": role,
               "created": time.time(), "generated": not os.environ.get(env)}
        if not os.environ.get(env):
            rec["first_pw"] = pw            # ať ho provozatel může přečíst v users.json (mód 600)
        users[name] = rec
    return generated


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
