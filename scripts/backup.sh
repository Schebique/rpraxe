#!/usr/bin/env bash
# Záloha „R v ruce“: SQLite snímek + účty + data + banky, vše pod jedním časem.
#   použití: backup.sh <cíl> [počet_kopí] [jméno_kontejneru]
#   cron:    30 3 * * * /usr/local/bin/rpraxe-zaloha.sh /srv/zalohy/rpraxe 14 rpraxe-app-1
# Ticho = úspěch. Vypisuje se jen při chybě, nebo s RPRAXE_ZALOHA_TLDR=1.
#
# Všechny soubory jedné noci sdílejí známku <čas>. Obnova pak patří k sobě a
# aplikace ji pozná podle jména (volá rpraxe-data-<stejný-čas>.tgz).
set -u

DEST="${1:?použij: backup.sh <cilovy-adresar> [pocet-kopii] [jmeno-kontejneru]}"
KEEP="${2:-14}"
CONTAINER="${3:-rpraxe-app-1}"
APP_DIR="${RPRAXE_APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LOGSOUBOR="${RPRAXE_ZALOHA_STAV:-$DEST/backup.json}"

docker_cmd() { docker "$@" 2>/dev/null || sudo -n docker "$@"; }
ts() { date +%F' '%H:%M:%S; }
fail() { echo "$(ts) FAIL: $*"; exit 1; }

mkdir -p "$DEST" || fail "nejde vytvořit $DEST"
timeout 15 ls "$DEST" >/dev/null 2>&1 || fail "$DEST nedostupný"

# konzistentní snímek za chodu: zálohu dělá sqlite uvnitř kontejneru;
# state/ je bind mount, takže soubor vidíme i na hostiteli
docker_cmd exec "$CONTAINER" /opt/venv/bin/python -c "
import sqlite3
src = sqlite3.connect('/data/state/rpraxe.db')
dst = sqlite3.connect('/data/state/.zaloha.db')
src.backup(dst); dst.close(); src.close()
" || fail "snapshot DB selhal"
[ -r "$APP_DIR/state/.zaloha.db" ] || fail "snapshot nikde (state/ není bind mount?)"

CAS="$(date +%F-%H%M%S)"
DO="$DEST/rpraxe-$CAS.db"
timeout 300 cp "$APP_DIR/state/.zaloha.db" "$DO" || fail "kopie DB do $DEST"
rm -f "$APP_DIR/state/.zaloha.db"
chmod 600 "$DO" 2>/dev/null || true

# co se balí: banka úloh a nasazení, účty a podpisový klíč, datasety, nastavení
tar czf "$DEST/rpraxe-tasks-$CAS.tgz" -C "$APP_DIR" tasks README.md docker-compose.yml Dockerfile 2>/dev/null \
  || echo "$(ts) VAROVÁNÍ: banka úloh se nezálohovala"
tar czf "$DEST/rpraxe-ucty-$CAS.tgz" --mode=600 -C "$APP_DIR" state/users.json state/secret.key 2>/dev/null \
  || sudo -n tar czf "$DEST/rpraxe-ucty-$CAS.tgz" --mode=600 -C "$APP_DIR" state/users.json state/secret.key 2>/dev/null \
  || echo "$(ts) VAROVÁNÍ: záloha účtů selhala (DB proběhla)"
chmod 600 "$DEST/rpraxe-ucty-$CAS.tgz" 2>/dev/null || true
tar czf "$DEST/rpraxe-data-$CAS.tgz" -C "$APP_DIR" datasets 2>/dev/null \
  || echo "$(ts) VAROVÁNÍ: adresář datasets se nebalil"
tar czf "$DEST/rpraxe-nastaveni-$CAS.tgz" -C "$APP_DIR" state/config.json 2>/dev/null || true

# stav pro rozhraní: napíše se do záložního adresáře i do state/, aby to
# aplikace viděla z kontejneru i bezdalšího mountu
python3 - "$DEST" "$CAS" "$APP_DIR/state/zaloha.json" <<'PY'
import json
import os
import sys
import time
cil, cas, cesta_stavu = sys.argv[1], sys.argv[2], sys.argv[3]
soubory = sorted(f for f in os.listdir(cil) if cas in f)
stav = {"at": int(time.time()), "cas": cas, "dest": cil, "soubory": soubory,
        "db_bytes": os.path.getsize(os.path.join(cil, "rpraxe-%s.db" % cas))
        if os.path.exists(os.path.join(cil, "rpraxe-%s.db" % cas)) else 0,
        "ucty": "rpraxe-ucty-%s.tgz" % cas if os.path.exists(os.path.join(cil, "rpraxe-ucty-%s.tgz" % cas)) else None,
        "data": "rpraxe-data-%s.tgz" % cas if os.path.exists(os.path.join(cil, "rpraxe-data-%s.tgz" % cas)) else None,
        "banka": "rpraxe-tasks-%s.tgz" % cas if os.path.exists(os.path.join(cil, "rpraxe-tasks-%s.tgz" % cas)) else None,
        "volno_bytes": os.statvfs(cil).f_bavail * os.statvfs(cil).f_frsize}
for cesta in (os.path.join(cil, "backup.json"), cesta_stavu):
    try:
        with open(cesta, "w", encoding="utf-8") as soubor:
            json.dump(stav, soubor, ensure_ascii=False, indent=1)
    except OSError:
        pass
PY

# rotace — drží se pohromadě, aby obnova nemíchala různé noci
for vzor in 'rpraxe-*.db' 'rpraxe-tasks-*.tgz' 'rpraxe-ucty-*.tgz' 'rpraxe-data-*.tgz' 'rpraxe-nastaveni-*.tgz'; do
  ls -1t "$DEST"/$vzor 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r f; do rm -f "$f"; done
done

if [ "${RPRAXE_ZALOHA_TLDR:-0}" = "1" ]; then
  echo "$(ts) OK: $CAS, DB $(du -h "$DO" | cut -f1), $(ls -1 "$DEST" | wc -l) souborů v $DEST, volné $(df -h "$DEST" | awk 'NR==2{print $4}')"
fi
exit 0
