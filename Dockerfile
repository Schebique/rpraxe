# rpraxe — jeden obraz, dva režimy spuštění
#
# Proč ne `rocker/tidyverse`: 2,9 GB se špatně pushuje do registry (Docker Hub
# i GHCR mají praktické meze na velikost vrstvy) a tahá knihovny, které tu
# nikdo nepoužívá. `rocker/r2u` je ten samý R na Ubuntu LTS, jen střízlivý, a
# R balíčky se instalují jako hotové apt balíčky (žádné překládání).
#
# Stejný obraz umí:
#   * `RPRAXE_RUNNER_PROMIT=1` (výchozí) — aplikace i sandbox R v jednom
#     kontejneru. Hodí se pro Kubernetes (CESNET/e-INFRA) a pro „nainstaluj
#     si to doma“.
#   * `RPRAXE_RUNNER_PROMIT=0` — aplikace jen volá runner jiný; ten bývá
#     v samostatném kontejneru bez východu na síť (viz docker-compose.yml).
#
# Vlastní R balíček si postavte overlay obrazem (viz docs/hosting.md).

FROM rocker/r2u:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Prague

# R balíčky, na které se spoléhají úlohy (dplyr, ggplot2) i generátor dat.
# Seznam ověřuje scripts/check_rpkgs.R — kdyby tu něco chybělo, build spadne.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
         r-cran-dplyr r-cran-tidyr r-cran-readr r-cran-tibble r-cran-stringr \
         r-cran-forcats r-cran-lubridate r-cran-purrr r-cran-ggplot2 \
         r-cran-jsonlite r-cran-base64enc \
         python3-venv python3-pip file procps \
         fontconfig fonts-dejavu-core tzdata ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python běžec — aplikace i runner sdílejí jednu virtualenv
RUN python3 -m venv --system-site-packages /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir \
         "fastapi==0.115.6" "uvicorn[standard]==0.34.0" "httpx==0.28.1" \
         "pyyaml==6.0.2" "python-multipart==0.0.20"

# Uživatel, pod kterým běží web i R. Skupina 0 (root) je záměr: Kubernetesu
# stačí `fsGroup: 0` a zapsatelné svazky fungují bez měnění vlastníka.
# UID/GID souhlasí s hodnotami RPRAXE_SANDBOX_UID/GID v runner/server.py.
RUN groupadd -g 4242 sandbox 2>/dev/null || true; \
    useradd -m -u 4242 -g 4242 -o sandbox 2>/dev/null || true; \
    usermod -aG 0 sandbox; \
    mkdir -p /srv /work /data/datasets /data/state; \
    chown -R sandbox:0 /work /data; \
    chmod -R 0775 /work /data; \
    chmod 1777 /tmp

ENV PATH="/opt/venv/bin:${PATH}" \
    RPRAXE_DATASETS=/data/datasets \
    RPRAXE_STATE_DIR=/data/state \
    RPRAXE_WORK=/work

WORKDIR /srv
COPY runner/ /srv/runner/
COPY app/ /srv/app/
COPY web/ /srv/web/
COPY tasks/ /srv/tasks/
COPY r/ /srv/r/
COPY agent/ /srv/agent/
COPY scripts/ /srv/scripts/
COPY docker/ /srv/docker/

# brána kvality: obraz bez nezbytných knihoven ani nevstane
RUN Rscript /srv/scripts/check_rpkgs.R \
    && /opt/venv/bin/python /srv/scripts/check_static.py

USER 4242:4242
EXPOSE 8080
ENTRYPOINT ["/srv/docker/entrypoint.sh"]
# Startuje docker/entrypoint.sh (ENTRYPOINT), CMD je tu jen jako dokumentace —
# entrypoint ho nečte. Adresa i port se přepisují proměnnými RPRAXE_BIND a
# RPRAXE_PORT_INTERNAL, viz docs/hosting.md.
CMD ["/opt/venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", \
     "--port", "8080", "--app-dir", "/srv", "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
