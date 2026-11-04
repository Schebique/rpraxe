FROM rocker/tidyverse:4.4

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3-pip python3-venv file \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv --system-site-packages /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir \
      "fastapi==0.115.6" "uvicorn[standard]==0.34.0" "httpx==0.28.1" "pyyaml==6.0.2" "python-multipart==0.0.20"

# sandbox user for R execution (never run student code as root)
RUN useradd -m -u 4242 sandbox && mkdir -p /work && chown -R sandbox:sandbox /work

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv
COPY runner/ /srv/runner/
COPY app/ /srv/app/
COPY web/ /srv/web/
COPY tasks/ /srv/tasks/
COPY r/ /srv/r/
COPY agent/ /srv/agent/
COPY scripts/ /srv/scripts/

RUN mkdir -p /data/datasets /data/state && chmod 777 /tmp

# brána kvality: stránka se vykresluje až z app.js, špatná cesta = černá obrazovka
RUN /opt/venv/bin/python /srv/scripts/check_static.py

EXPOSE 8080 8081
CMD ["sh", "-c", "/opt/venv/bin/python /srv/scripts/check_static.py; exec /opt/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --app-dir /srv"]
