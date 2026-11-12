#!/bin/sh
# Start aplikace rpraxe. Stará se o to, aby šlo spustit obraz kdekoli —
# doma v docker compose, v Kubernetes (CESNET/e-INFRA), u kolegy na notebooku.
#
# Důležité: adresáře musí být zapsatelné pod UID, pod kterým běží kontejner.
# V Kubernetes to zařídí `fsGroup` v securityContext, u bind mountu ve složení
# to musí udělat správce hostitele (`chown -R 4242:4242 state datasets`).
set -eu

proc() { printf '%s %s\n' "$(date -u +%H:%M:%SZ)" "$*" >&2; }

kontrola_zapisu() {
    dirs=""
    [ -n "${RPRAXE_STATE_DIR:-}" ] && dirs="$dirs $RPRAXE_STATE_DIR"
    # datasets bývá záměrně jen pro čtení (runner je nikdy nepíše) — pak
    # kontrolu přeskoč, ať z bezpečnostního opatření není chyba při startu
    if [ "${RPRAXE_DATASETS_RO:-0}" != "1" ] && [ -n "${RPRAXE_DATASETS:-}" ]; then
        dirs="$dirs $RPRAXE_DATASETS"
    fi
    [ -n "${RPRAXE_WORK:-}" ] && dirs="$dirs $RPRAXE_WORK"
    for d in $dirs; do
        mkdir -p "$d" 2>/dev/null || true
        # zkus zapsat — `test -w` klame, když adresář patří někomu jinému a
        # soubory v něm jen čteme (staré nasazení s kořenem v kontejneru)
        if (touch "$d/.zapis-rpraxe" && rm -f "$d/.zapis-rpraxe") 2>/dev/null; then
            continue
        fi
        proc "SMULA: do adresare '$d' se nedá zapisovat pod UID $(id -u)."
        proc "  u bind mountu:  chown -R $(id -u):$(id -g) $d"
        proc "  v Kubernetes:   do deploymentu přidej securityContext.fsGroup: $(id -g)"
        exit 1
    done
}

cekani_na_runner() {
    i=0
    while [ "$i" -lt 90 ]; do
        if /opt/venv/bin/python -c \
             "import urllib.request,sys
try:
    sys.exit(0 if urllib.request.urlopen('$1/ping', timeout=2).status == 200 else 1)
except Exception:
    sys.exit(1)" 2>/dev/null; then
            proc "runner pripraven ($1)"
            return 0
        fi
        i=$((i + 1))
        sleep 1
    done
    return 1
}

kontrola_zapisu

# samostatný runner: kontejner, ve kterém běží jen sandbox R (dvousložkové
# složení — viz docker-compose.dva-slouzby.yml)
if [ "${RPRAXE_SERVE:-app}" = "runner" ]; then
    proc "startuji jen runner (sandbox R), UID $(id -u)"
    exec /opt/venv/bin/uvicorn runner.server:app --host 0.0.0.0 \
        --port "${RPRAXE_RUNNER_PORT_INTERNAL:-8081}" --app-dir /srv --workers 1
fi

# sandbox pro R — ve výchozím zapnutí běží v témže kontejneru, aplikace ho
# volá přes localhost. Vypne se RPRAXE_RUNNER_PROMIT=0, pak musí běžet runner
# někde jinde a musí mířit RPRAXE_RUNNER.
if [ "${RPRAXE_RUNNER_PROMIT:-1}" = "1" ]; then
    : "${RPRAXE_WORK:=/work}"
    : "${RPRAXE_STATE:=/data/state/runner}"
    export RPRAXE_WORK RPRAXE_STATE
    : "${RPRAXE_RUNNER_INTERNAL_PORT:=8081}"
    # sandbox běží tady, takže adresa musí být localhost — i kdyby rpraxe.env
    # ukazoval na jinou službu (z dvouslužbového složení)
    if [ "${RPRAXE_RUNNER:-}" != "http://127.0.0.1:$RPRAXE_RUNNER_INTERNAL_PORT" ]; then
        [ -n "${RPRAXE_RUNNER:-}" ] &&
            proc "pozor: predepsany RPRAXE_RUNNER ($RPRAXE_RUNNER) pri vestavenem sandboxu davam localhost"
        RPRAXE_RUNNER="http://127.0.0.1:$RPRAXE_RUNNER_INTERNAL_PORT"
    fi
    export RPRAXE_RUNNER
    /opt/venv/bin/uvicorn runner.server:app --host 127.0.0.1 \
        --port "$RPRAXE_RUNNER_INTERNAL_PORT" --app-dir /srv --workers 1 &
    RUNNER_PID=$!
    proc "cekam na runnera (PID $RUNNER_PID, $RPRAXE_RUNNER)"
    cekani_na_runner "$RPRAXE_RUNNER" ||
        proc "POZOR: runner neslapi do 90 s — úlohy půjdou na hlášku, ne ke spuštění"
else
    : "${RPRAXE_RUNNER:=http://rpraxe-runner:8081}"
    export RPRAXE_RUNNER
    proc "runner spousti nekdo jiny: $RPRAXE_RUNNER"
fi

# brána kvality: špatná cesta ve web/ = černá obrazovka, ať to praskne hned
/opt/venv/bin/python /srv/scripts/check_static.py || proc "POZOR: check_static nasel problemy, startuju dal"

# Adresa: default 0.0.0.0, aby to fungovalo i v Kubernetesu, kde health probe
# míří na IP podu. RPRAXE_BIND=127.0.0.1 dává smysl jen s proxy před aplikací
# (vlastní Ingress sidecar) — jinak pak kontejner není dosažitelný zvenčí.
proc "startuji aplikaci na ${RPRAXE_BIND:-0.0.0.0}:${RPRAXE_PORT_INTERNAL:-8080}, UID $(id -u)"
exec /opt/venv/bin/uvicorn app.main:app \
    --host "${RPRAXE_BIND:-0.0.0.0}" --port "${RPRAXE_PORT_INTERNAL:-8080}" \
    --app-dir /srv --proxy-headers --forwarded-allow-ips '*'
