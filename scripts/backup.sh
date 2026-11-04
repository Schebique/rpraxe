#!/usr/bin/env bash
# Záloha stavu „R v ruce“: SQLite snímek + účty + banka úloh, s rotací.
#   použití: backup.sh <cíl> [počet_kopií] [jméno_kontejneru]
#   cron:    40 3 * * * /usr/local/bin/backup.sh /mnt/nas/zalohy/rpraxe 7
# Ticho = úspěch. Výstup jen při chybě nebo s RPRAXE_ZALOHA_TLDR=1.
set -u

DEST="${1:?použij: backup.sh <cilovy-adresar> [pocet-kopii] [jmeno-kontejneru]}"
KEEP="${2:-7}"
CONTAINER="${3:-rpraxe-app-1}"
APP_DIR="${RPRAXE_APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# docker může vyžadovat sudo (záleží na skupině uživatele, který spustí cron)
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

NAME="rpraxe-$(date +%F-%H%M%S).db"
timeout 300 cp "$APP_DIR/state/.zaloha.db" "$DEST/$NAME" || fail "kopie do $DEST"
rm -f "$APP_DIR/state/.zaloha.db"
chmod 600 "$DEST/$NAME" 2>/dev/null || true

# banka úloh a nasazení — bez toho je obnovená aplikace prázdná
tar czf "$DEST/rpraxe-tasks-latest.tgz" -C "$APP_DIR" tasks README.md docker-compose.yml Dockerfile 2>/dev/null

# přihlašovací stav: bez účtů a podpisového klíče by se po obnově DB nikdo
# nepřihlásil změněným heslem (soubor patří uživateli, jen zřídka owns ho root)
tar czf "$DEST/rpraxe-ucty-latest.tgz" --mode=600 -C "$APP_DIR" state/users.json state/secret.key 2>/dev/null \
  || sudo -n tar czf "$DEST/rpraxe-ucty-latest.tgz" --mode=600 -C "$APP_DIR" state/users.json state/secret.key 2>/dev/null \
  || echo "$(ts) VAROVÁNÍ: záloha účtů selhala (DB záloha proběhla)"
chmod 600 "$DEST/rpraxe-ucty-latest.tgz" 2>/dev/null || true

# rotace
ls -1t "$DEST"/rpraxe-*.db 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r f; do rm -f "$f"; done

[ "${RPRAXE_ZALOHA_TLDR:-0}" = "1" ] && \
  echo "$(ts) OK: $NAME $(du -h "$DEST/$NAME" | cut -f1), volné $(df -h "$DEST" | awk 'NR==2{print $4}')"
exit 0
