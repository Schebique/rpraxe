# Kde a jak rpraxi spustit

Aplikace je jeden Docker image, který umí běžet sám o sobě i v Kubernetes.
Tenhle dokument popisuje způsoby nasazení, volbu sandboxu, proměnné, data,
migraci, CESNET/e-INFRA a nejčastější chyby při startu.
Pro vývoj v repozitáři viz [testing.md](testing.md), pro chod instance
v provozu [provoz.md](provoz.md).

## Co je uvnitř image

| vrstva | co | kde |
|---|---|---|
| R | `rocker/r2u:24.04` (Ubuntu 24.04 + R), balíčky jako hotové `r-cran-*` | `Rscript` v `PATH` |
| Python | virtualenv `/opt/venv` s FastAPI + uvicorn | aplikace i runner sdílejí jeden venv |
| aplikace | `app/` + statické `web/` | `/srv`, poslouchá na 8080 |
| sandbox | `runner/` — pouští R, hlídá limity | `/srv`, poslouchá na 8081 |
| data | databáze, účty, nahraná CSV | `/data/state`, `/data/datasets` |
| běžiště | adresář, kde studentův kód proběhne | `/work` (tmpfs, mizí s kontejnerem) |

Image je jeden a tentýž pro aplikaci i sandbox; o tom, co v kontejneru
naběhne, rozhodují dvě proměnné:

| proměnná | hodnoty | význam |
|---|---|---|
| `RPRAXE_SERVE` | `app` (výchozí) / `runner` | kontejner je aplikace, nebo jen běžec R |
| `RPRAXE_RUNNER_PROMIT` | `1` (výchozí) / `0` | v aplikaci se roztočí i sandbox na localhostu |
| `RPRAXE_BIND` | `0.0.0.0` | adresa uvnitř kontejneru; `127.0.0.1` smysluplné jen s proxy před aplikací |

## Tři způsoby, jak to postavit

1. **Jeden kontejner** (`docker-compose.yml`) — aplikace i R uvnitř. Nejjednodušší
   na instalaci i na Kubernetes. R má k dispozici síť kontejneru, takže by
   teoreticky mohl něco stáhnout; studentova kód je jinak omezený limity a nemá
   kam zapsat trvale.
2. **Dvě služby** (`docker-compose.dva-slouzby.yml`) — `runner` sedí na `internal`
   síti bez brány a bez DNS, tedy žádný ven. Aplikace ven smí, protože potřebuje
   model. Doporučeno všude, kde kód píší cizí lidé.
3. **Kubernetes** (`deploy/einfra/k8s.yaml`) — jeden kontejner na pod, svazek na
   data, Ingress s TLS. Volitelně `NetworkPolicy` pro zúžení sítě.

Bez Dockeru to jde také (`python -m venv` + `Rscript`), ale pak si limity a
běžce spravuješ sám; návod je v [README](../README.md) v sekci *Without Docker*.

## Rychlý start s Docker Compose

```sh
git clone https://github.com/<vlastník>/rpraxe && cd rpraxe
cp rpraxe.env.example rpraxe.env && chmod 600 rpraxe.env
$EDITOR rpraxe.env            # RPRAXE_USERS a hesla
docker pull ghcr.io/<vlastník>/rpraxe:latest
docker tag ghcr.io/<vlastník>/rpraxe:latest rpraxe:2
mkdir -p state datasets
sudo chown -R 4242:0 state datasets        # kontejner běží pod UID 4242
docker compose up -d
```

`docker compose up` bez parametru sáhne po `docker-compose.yml`, tedy po
jednokontejnerové variantě. Image si klidně pojmenuj jinak — compose čte tag z
`RPRAXE_IMAGE_TAG` (výchozí `2`), takže stačí `RPRAXE_IMAGE_TAG=0.3.0 docker
compose up -d`.

Pak `http://127.0.0.1:8710`. Přihlášení funguje s hesly z `rpraxe.env`, dokud
se účet nezaloží; pak žije hash v `state/users.json`.

### Ověř, že to skutečně běží

```sh
curl -s http://127.0.0.1:8710/healthz              # aplikace žije → {"ok":true,...}
curl -s 'http://127.0.0.1:8710/healthz?detail=1'   # + stav běžiště R
curl -s http://127.0.0.1:8711/ping                # runner sám (při dvouslužbové variantě)
docker compose logs --tail 30                      # má tam být „startuji aplikaci“
```

`/healthz` je schválně levný a o běžišti nic neříká — aby se v něm dal nechat
healthcheck i loadbalancer bez zbytečné zátěže. Se `?detail=1` připojí sondu na
běžiště a vrátí třeba

```json
{"ok": true, "version": "0.3.0", "sandbox_url": "http://127.0.0.1:8081",
 "sandbox": {"ok": true, "sandbox": "direct", "uid": 4242}, "sready": true}
```

To `sready: false` je přesně ten stav, kdy aplikace jede, ale student u úlohy
dostane hlášku, že běžiště nedostihne vysvětlit kód. Běžiště má vlastní
`/ping` (bez podprocesu R) a `/health`, které navíc vrátí verzi R a seznam
datasetů — `curl http://127.0.0.1:8711/health` je nejrychlejší způsob, jak
ověřit, jaká R a jaké knihovny se v kontejneru skutečně vidí.

## Varianty sandboxu

`runner/server.py` si režim vybere sám podle efektivního UID kontejneru:

| režim | kdy | co to dělá |
|---|---|---|
| `direct` | kontejner neběží jako root — to je náš image (`USER 4242:4242`) i Kubernetes | R běží pod týmž UID jako runner |
| `drop` | kontejner startuje jako root a účet `sandbox` existuje (obraz s `--user root`) | R spadne pod UID 4242 přes `setpriv` |

Vynutit můžeš `RPRAXE_SANDBOX_MODE=auto|drop|direct`. Režim `drop` je jediná
chvíle, kdy je studentský kód pod jiným UID než samo běžiště; protože obraz má
`USER 4242:4242`, běžně běží `direct` a izolaci drží limity, `no-new-privileges`,
seccomp a `NetworkPolicy`. Kvůli tomu jsou `state/` a `datasets/` mountnuté
jako skupina 0 a v Kubernetes stačí `securityContext.fsGroup: 0`.

Limity platí v každém režimu: `RPRAXE_CPU_LIMIT` (procesorový čas, SIGXCPU),
`RPRAXE_WALL_LIMIT` (stěnový čas přes `timeout`), `RPRAXE_MEM_MB` (RLIMIT_AS),
20 MB na výstupní soubor, 2000 řádků `stdout`. Když kód limit přesáhne, student
dostane větu, co přesáhlo a co s tím — ne výpis shellu.

## Kubernetes (obecně)

`deploy/einfra/k8s.yaml` je kompletní manifest: `Namespace`, `PersistentVolumeClaim`,
`Deployment`, `Service`, `Ingress` a volitelná `NetworkPolicy`. Nejdřív si projdi
tyhle místa:

* `image:` — `ghcr.io/VASE-UCET/rpraxe:latest`. GHCR vyžaduje malé písmeno v
  názvu, ale ať je zřejmé, že je to placeholder; při nasazení pinuj konkrétní
  version (`:0.3.0`) a `imagePullPolicy: IfNotPresent`.
* `RPRAXE_USERS` a `RPRAXE_PASS_UCITEL` — první účet. Aplikuje se jen tehdy,
  když `state/users.json` ještě neexistuje, tedy na prázdném svazku.
* secret `rpraxe-secrets` s klíčem `ucitel-heslo` a volitelný `rpraxe-ai`
  s `key` (klíč od modelu). Bez AI klíče appka běží, jen bez kouče.

```sh
kubectl -n rpraxe create secret generic rpraxe-secrets \
  --from-literal=ucitel-heslo="$(openssl rand -base64 12)"
kubectl apply -f deploy/einfra/k8s.yaml
kubectl -n rpraxe rollout status deploy/rpraxe
kubectl -n rpraxe logs deploy/rpraxe --tail 40
```

`storageClassName: standard` přepiš podle clusteru (`kubectl storageclass get`).
Ingress čeká na `ingressClassName: nginx` a anotaci pro cert-manager; jestli
cluster dává TLS jinou cestou, anotace smaž.

Public image, ze které se táhne bez přihlášení, udělá workflow
`.github/workflows/obraz.yml`: push na `main` dá `latest` a `main`, tag `v0.3.0`
dá `0.3.0`. Repo bývá public, takže stačí `GITHUB_TOKEN` a povolení
`packages: write`, což je v workflow už zapsané. Jiná registry (Harbor, Docker
Hub) znamená doplnit vlastní secret a přepsat `images:`.

## CESNET / e-INFRA CZ (MetaCentrum)

Platforma je zdarma pro akademickou sféru, běžná služba tam může jet trvale
(na rozdíl od davových front s 24h limitem). Co potřebuješ:

1. **Účet** přes eduID.cz, schvaluje se ručně (dny). Účet se nesmí sdílet —
   pokud má autorka úloh vlastní (zaměstnanka VŠ), je ideální nasadit to v
   *jejím* namespace a ty jen dodáš image a manifest.
2. **Projekt/namespace** a kvóty. Náš needs je 2 CPU a ~2,6 GB RAM, tedy zlomek
   toho, co osobní namespace bývá.
3. **Registry.** Buď nech pod táhnout `ghcr.io/...` (nejméně práce, image je
   veřejný), nebo si image nahraj do `hub.cerit.io/<projekt>/rpraxe`:

   ```sh
   docker build -t hub.cerit.io/<projekt>/rpraxe:0.3.0 .
   docker login hub.cerit.io            # heslo = clone token z GitHubu
   docker push hub.cerit.io/<projekt>/rpraxe:0.3.0
   ```

   Pro soukromý image pak v namespace vytvoř pull secret a přidej ho do
   `imagePullSecrets` v Deploymentu:

   ```sh
   kubectl -n <namespace> create secret docker-registry hub-cerit \
     --docker-server=hub.cerit.io --docker-username='<uživatel>' \
     --docker-password='<clone token>'
   ```
4. **`kubectl apply`** s upraveným manifestem. `storageClassName` i
   `ingressClassName` nech na tom, co cluster nabízí; Ingress pak dostane
   `*.app.e-infra.cz` s certifikátem automaticky.
5. **Model.** Buď **e-INFRA LLM API** (`RPRAXE_PROVIDER=einfra`, adresa
   `https://llm.ai.e-infra.cz/v1`, styl OpenAI) — klíč si každý vygeneruje sám
   v Chat WebUI (Accounts → API Keys) a název modelu zkopíruje ze seznamu,
   protože se mění. Nebo **Ollama uvnitř clusteru/tailnetu** — pak
   `RPRAXE_AI_ADRESA` ukazuje na ni a `RPRAXE_PROVIDER=ollama`. Obojí se dá
   přepnout bez restartu v menu *Správa → Modely*.

Pozor na to, že `NetworkPolicy` v manifestu pouští ven jen 443 a DNS. Pokud
model není dostupný přes HTTPS z clusteru, buď politiku uprav, nebo ji na začátek
nespouštěj (je to samostatný dokument v souboru, klidně ho `kubectl delete -f`
souhlasnou částí).

### Obraz do cizí registry (např. `hub.cerit.io`)

GitHub Container Registry bývá pro cizí cluster první překážka — vlastníku clusteru
se image nejlíp dostane do registry, kterou cluster zná:

```sh
docker tag ghcr.io/<vlastnik>/rpraxe:0.3.0 hub.cerit.io/<projekt>/rpraxe:0.3.0
docker login hub.cerit.io -u <uzivatelske-jmeno>   # heslo = CLI secret, ne heslo k účtu
docker push hub.cerit.io/<projekt>/rpraxe:0.3.0
```

- **Přihlašovací heslo do Harboru není heslo k účtu.** Je to *CLI secret* v
  uživatelském profilu na portálu (stejné i pro `docker login cerit.io`).
  Nemá časový limit, ale s vypršením účtu přestává platit i on.
- Každý má vlastní projekt s kvótou 100 GB, další projekty si zakládá v Rancheru;
  plná adresa je `hub.cerit.io/<projekt>/<image>:<tag>`.
- **Image uvnitř clusteru je čitelný odkudkoli** — kdo zná přesné jméno, může si
  ho stáhnout. V obrazu proto nikdy nenechávej token ani klíč.
- Bez docker enginu: `docker save rpraxe:0.3.0 | gzip > rpraxe.tar.gz` a
  `docker load` u nich, nebo `skopeo copy` registry → registry.

### Postup nasazení v e-INFRA (kuba-cluster)

Manifiesty jsou v `deploy/einfra/k8s.yaml`; namespace si vytvoř v Rancheru,
nebo:

```sh
kubectl -n <jmeno> apply -f deploy/einfra/k8s.yaml
kubectl -n <jmeno> create secret generic rpraxe-secrets \
  --from-literal=RPRAXE_SECRET_KEY="$(openssl rand -hex 32)"
kubectl -n <jmeno> rollout restart deployment/rpraxe
```

Co je v manifestu a proč:

- **Adresa.** Ingress musí končit na `.dyn.cloud.e-infra.cz` a jméno musí mít
  jedinou label před příponou (`rpraxe.dyn.cloud.e-infra.cz`) — cluster pak
  přidá DNS i TLS z wildcard certifikátu. Vícemístné jméno chce vlastní
  `Gateway`, kotvu `external-dns` a issuer `letsencrypt-gateway`. Třída ingressu
  je `nginx-traefik`; novější cesta jsou dva `HTTPRoute` na sdílený
  `traefik-gateway` (webová adresa z něj vrací 308 na https).
- **Issuer.** Dokumentace uvádí `letsencrypt-prod` i `letsencrypt-gateway`,
  povolené jsou jen cluster isscery. Když se certifikát nevygeneruje, zkus v
  anotaci ten druhý.
- **Jedna identita.** `runAsNonRoot` + `runAsUser: 4242` + `fsGroup: 4242`, aby
  šlo zapisovat na svazek. Bez `fsGroup` skončí entrypoint hláškou o zápisu.
- **Síť.** `NetworkPolicy` pouští dovnitř jen bránu z `kube-system` — bez toho
  by se do appky dostal kontejner z cizího projektu přímo po ClusterIP, tedy
  mimo přihlašování. Ven pouští DNS a HTTPS mimo privátní rozsahy.
- **Model.** `RPRAXE_PROVIDER=einfra`, nebo vlastní Ollama v clusteru (manifest
  s ní počítá jako samostatná deployment, oslovíš ji přes Service).
- **Přihlašování.** Brána e-INFRA (oauth2-proxy) posílá identitu obecnými
  hlavičkami bez našeho tajemství, takže `RPRAXE_SSO_*` z ní rovnou nepoužiješ —
  buď ponech účty aplikace (hesla vygeneruje správce), nebo si před to postav
  vlastní oauth2-proxy s `--pass-user-headers` a vlastním tajemstvím.

Je jedna věc, kterou izolace uvnitř jednoho podu nedá: sandbox R sdílí se sítí
i adresu aplikace, takže studentův kód může oslovit `localhost:8080`. Oddělí ho
až druhý kontejner (`RPRAXE_RUNNER_PROMIT=0`), který navíc dostane vlastní
`NetworkPolicy` bez přístupu ke službě.

## Vlastní R balíčky

Základní obraz má jen knihovny, které banka úloh skutečně potřebuje.
`rocker/r2u` umí instalovat `r-cran-*` jako apt balíčky, tedy rychle a bez
kompilátoru. Vlastní knihovny přidej overlay obrazem:

```dockerfile
FROM ghcr.io/<vlastník>/rpraxe:0.3.0
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends r-cran-lme4 r-cran-psych \
    && rm -rf /var/lib/apt/lists/*
USER 4242:4242
```

Balíčky, které nejsou v apt, nainstaluj jako root do sdílené knihovny, jinak
je UID 4242 neuvidí:

```dockerfile
USER root
RUN Rscript -e 'install.packages("jméno", repos = "https://cloud.r-project.org")'
USER 4242:4242
```

Seznam knihoven, na které se spoléhá banka úloh, ověřuje
`scripts/check_rpkgs.R` — běží při buildu, takže na chybějící balíček build
samotný upozorní. Přidej si ho i do vlastního CI.

## Data, zálohy, migrace

Všechno stavové je ve dvou adresářích:

* `state/` — `rpraxe.db` (SQLite), `users.json`, `config.json`, `secret.key`,
  zálohy v `state/backups/`. Řádově MB.
* `datasets/` — CSV, se kterými úlohy pracují; učitel sem může nahrát nová.

Záloha je tedy obyčejný `tar` při běžící aplikaci (SQLite se zálohuje přes
`.backup`, ať nesmažeš poloviční zapisování — `scripts/` na to má skript a
denní snímek popisuje [provoz.md](provoz.md)):

Konzistentní snímek databáze za chodu dělá `scripts/backup.sh` (volá
`sqlite3 .backup` uvnitř kontejneru, rotuje snímky, píše `backup.json`) —
popis a cron nasazení má [provoz.md](provoz.md). Ruční snímek všeho je
jednoduchý:

```sh
tar czf rpraxe-zaloha-$(date +%F).tar.gz state datasets
```

Obnova na jiném stroji:

```sh
tar xzf rpraxe-zaloha-2026-11-12.tar.gz
sudo chown -R 4242:0 state datasets
docker compose up -d
```

To je celá migrace mezi instalacemi — stav je přenositelný, protože cesty
uvnitř kontejneru jsou vždycky `/data/...`. Když migrateješ do Kubernetes,
obsah adresářů nahraj do svazku (typicky `kubectl cp` do podu nebo inicializační kontejner);
po `rollout` zkontroluj, že se účty nezačaly zakládat znovu, což by znamenalo,
že appka na svazek nevidí.

## Nejčastější problémy při startu

| co vidíš | příčina | co s tím |
|---|---|---|
| `EACCES` při zakládání účtů, appka jede na prázdné databázi | `state/` nepatří UID 4242 | `chown -R 4242:0 state datasets`, v K8s `fsGroup: 0` |
| `Read-only file system` na `/data` | `:ro` mount nebo `readOnlyRootFilesystem` bez svazku | přepni mount na rw, `/data` musí být zapsatelné |
| „do adresare '/data/datasets' se nedá zapisovat“ jen u dvouslužbové varianty | datasets jsou tam záměrně `:ro` a entrypoint to zkoušel jako běžný adresář | nastav `RPRAXE_DATASETS_RO=1` (v compose services runner to je) |
| „do adresare ... se nedá zapisovat pod UID 4242“ kdekoli jinde | bind mount patří tvému účtu | `chown -R 4242:4242 state datasets work`; v K8s `fsGroup` |
| appka startuje donekonečna a v logu je „cekam na runnera“ | vestavěný sandbox neskočil (přepnutý `RPRAXE_RUNNER`, chybějící `/work`, málo paměti) | `docker compose logs`, `df -h /work`, zvyšte `mem_limit` |
| studentovská hláška o nedostupném běžišti u každé úlohy | `RPRAXE_RUNNER_PROMIT=0` bez `RPRAXE_RUNNER`, nebo runner neběží | zkontroluj `docker compose ps`, u dvouslužbové varianty `runner` |
| `HTTP 401` od AI | chybějící/špatný klíč, nebo jsi nepsal přes `RPRAXE_AI_ADRESA` | menu *Správa → Modely*, tlačítko *uložit a vyzkoušet* |
| Ingress vrací 502 | containerPort/Service si neodpovídají (appka mluví 8080) | `kubectl describe svc rpraxe` |

## Bezpečnost — co sandbox drží a co ne

* **Drží:** čas (CPU i stěnový), pamět (`RLIMIT_AS`), velikost souboru, počet
  řádků výstupu, `pids_limit` a `mem_limit` nad kontejnerem, `no-new-privileges`,
  seccomp `RuntimeDefault`, capabilities drop. V dvouslužbové variantě navíc
  úplná absence venkovní sítě.
* **Co to neznamená:** v režimu `direct` běží studentský kód pod týmž UID jako
  aplikace, takže uvnitř kontejneru si sahá do procesů a souborů tohoto UID.
  Proto se data do běžiště kopírují a nemountují; proto `state/` v
  jednokontejnerové variantě sice tentýž UID čte, ale bez privilegovaného účtu
  z něj nic nedostane ven; a proto, když sandbox pouštíš cizím lidem, ber
  dvouslužbovou variantu nebo `NetworkPolicy`.
* Student kód nikdy nevidí shell — aplikace posílá text do `/run` a dostává
  strukturovanou odpověď.
* Veškerý text od modelu, který uvidí uživatel, projde strojovým ověřením
  (spustit, porovnat, zahodit) — model nemůže do úlohy napsat cokoli.
