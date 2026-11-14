# R v ruce (rpraxe)

**CZ:** Adaptivní cvičnice R postavená na sylabu kurzu *Mgr. Lucie Hoškové*
„Zpracovávání výzkumných dat v R“ (`luc-hoskova.github.io/introR_CUNI`).
Krátké denní úlohy na 15–30 minut, syntetická data, automatická kontrola
českou větou, lokální AI kouč. Kód ani data neopouštějí tvůj stroj.

**EN:** An adaptive daily-practice app for learning R, built on a real
university syllabus. Short tasks (15–30 min/day), synthetic datasets, an
automatic grader that names the *kind* of mistake, spaced repetition and an
Elo-like skill model. The AI coach runs on a **local** Ollama server — student
code and answers never leave the machine. Self-hosted with one Docker Compose
file; roles for students, teachers and admins; UI in 5 languages.

Features at a glance:

* **Today's set** — 2–5 tasks chosen by an adaptive module (per-skill Elo-ish
  estimate, SM-2-style spaced repetition, current syllabus lesson, last
  sticking points).
* **Machine grading** — every task ships an R checker that recomputes the
  expected value from the data; feedback describes the error, never the answer.
* **AI coach on the provider you choose** — your own Ollama, any
  OpenAI-compatible endpoint (incl. GitHub Models), Anthropic or Google Gemini.
  The **administrator** sets it once in the UI; users never pick a model.
  Hand-written hints stay hand-written and the model never sees the solutions.
* **Nightly author agent** (optional) — drafts new tasks and only publishes the
  ones that pass automated validation: the solution must pass its own checker
  and empty code must fail.
* **Roles** — `student` (own practice), `teacher` (student progress, task review),
  `admin` (accounts, model provider, SSO, backups, restore).
* **Human review of generated tasks** — *inspect* shows the assignment, starter,
  solution and checker separately; *verify by running* proves the solution
  passes while empty code and the starter fail; the model can also be asked to
  criticise its own task. A human approves before students see it.
* **In-app help** — the Help tab explains the workflow in the language you chose.
* **Notes, cheat sheet, progress** — multi-line notes per task, per-lesson cheat
  sheet, first-try success rate, streak, skill profile, CSV export.
* **UI languages** — čeština (source), English, slovenčina, Deutsch, polština;
  task texts stay in the language of the bank you use.
* **SSO-ready** — trust an authenticator proxy (Authelia, Authentik, oauth2-proxy)
  via signed headers; password login stays available as a fallback.

---

## Rychlý start / Quickstart

Potřebuješ Docker s Compose **2.17 a novějším** (`docker compose version`) —
starší Compose neumí říct, že se image má postavit z `Dockerfile`, a jde si ho
nejdřív stáhnout do registry, kde ještě žádný není.

```sh
git clone https://github.com/Schebique/rpraxe && cd rpraxe
cp rpraxe.env.example rpraxe.env && chmod 600 rpraxe.env      # vyplň hesla účtů
cp .env.example .env                                          # bind/port/tag image
mkdir -p state datasets && sudo chown -R 4242:4242 state datasets
docker compose up -d --build                                  # nebo nejdřív:
#   docker pull ghcr.io/Schebique/rpraxe:latest && docker compose up -d
docker compose exec rpraxe Rscript /srv/r/gen_datasets.R      # syntetická data
docker compose exec rpraxe /opt/venv/bin/python /srv/scripts/validate.py
curl -s 'http://127.0.0.1:8710/healthz?detail=1'              # aplikace + běžiště R
```

`docker compose up -d` beze `--build` použije hotový image: buď ten, co jsi
právě sestavil, nebo `docker pull ghcr.io/Schebique/rpraxe:latest` — to je
rychlejší a chce to jen stáhnout hotový image. `docker build -t rpraxe:latest .`
před `up` je taky cesta; compose čeká tag `latest`, předepsat se dá v `.env`
přes `RPRAXE_IMAGE_TAG`. V `docker-compose.yml` je `pull_policy: build`, takže
když image lokálně není, postavit se dá přímo z repozitáře a stačí to jedno
`up`.

`docker-compose.yml` je varianta **jeden kontejner** (aplikace i R uvnitř) —
stejný chod jako v Kubernetes. Variantu, kde R běží v kontejneru **bez přístupu
ven**, spustíš jako `docker compose -f docker-compose.dva-slouzby.yml up -d`;
kdy a jak kterou je rozepsané v [`docs/hosting.md`](docs/hosting.md).

Složky `state/` a `datasets/` musí patřit UID 4242, pod kterým kontejner běží —
bez toho aplikace nezaloží účty a generátor dat nenapíše ani soubor.
`chown` chce roota; v Kubernetes to zařídí `fsGroup` samo.

Pak `http://127.0.0.1:8710`. Přihlášení funguje s hesly z `rpraxe.env`, dokud
se účet nezaloží; pak si je každý změní v profilu a od té doby platí jen to,
co je v `state/users.json`.

Without Docker (during development):

```sh
python -m venv .venv && .venv/bin/pip install fastapi "uvicorn[standard]" httpx pyyaml python-multipart
RPRAXE_SERVE=runner .venv/bin/python -m uvicorn runner.server:app --port 8081 &
RPRAXE_DB=./state/dev.db RPRAXE_RUNNER=http://127.0.0.1:8081 \
  .venv/bin/uvicorn app.main:app --app-dir . --port 8710
```

## Konfigurace

Všechno se nastavuje proměnnými prostředí — kompletní komentovaný seznam je v
[`rpraxe.env.example`](rpraxe.env.example). Nejdůležitější:

| proměnná | význam | výchozí |
|---|---|---|
| `RPRAXE_USERS` | `jméno:role,…` — role `student` / `teacher` / `admin` | `lenka:student` |
| `RPRAXE_PASS_<ÚČET>` | výchozí heslo účtu (použije se jen při prvním založení) | — |
| `RPRAXE_SECRET` | **cesta** k souboru s podpisovým klíčem cookie, ne klíč sám | `state/secret.key`, vygeneruje se |
| `RPRAXE_PROVIDER` | `ollama` / `openai` / `anthropic` / `gemini` / `einfra` (předvolba na `llm.ai.e-infra.cz`, viz `docs/hosting.md`) | `ollama` |
| `RPRAXE_AI_ADRESA` | adresa modelu (Ollama, OpenAI-kompatibilní brána, e-INFRA LLM API…); `RPRAXE_OLLAMA` je starší název | `http://127.0.0.1:11434` |
| `RPRAXE_AI_KEY` | API klíč poskytovatele (nepovinný u vlastní Ollamy) — nebo ho vyplň ve správě | prázdné |
| `RPRAXE_MODEL` / `RPRAXE_MODEL_WRITE` | model kouče / generování úloh | `qwen3.5:9b` / `qwen3.6:35b-a3b` |
| `RPRAXE_DB`, `RPRAXE_DATASETS`, `RPRAXE_WEB`, `RPRAXE_TASKS` | cesty uvnitř kontejneru | výchozí sedí |
| `RPRAXE_CPU_LIMIT`, `RPRAXE_WALL_LIMIT`, `RPRAXE_MEM_MB` | limity sandboxu | `20`, `30`, `1500` |
| `RPRAXE_RUNNER_PROMIT` / `RPRAXE_SERVE` / `RPRAXE_RUNNER` | jak je postavený sandbox: vestavěný, nebo běžec v jiném kontejneru | `1` / `app` / `http://rpraxe-runner:8081` |
| `RPRAXE_SSO_*` | přihlášení přes bránu, viz [docs/sso.md](docs/sso.md) | vypnuto |
| `RPRAXE_BIND`, `RPRAXE_PORT`, `RPRAXE_IMAGE_TAG` (v souboru `.env`) | na čem poslouchá container a jaký tag image compose čeká | `127.0.0.1:8710`, `latest` |

AI vrstva je nepovinná: bez modelu funguje zadávání, kontrola, adaptivní plán i
progres; kouč jen odpoví z ručně psaných nápověd.

Kde to spustit (jeden kontejner, dva kontejnery bez sítě, Kubernetes, CESNET),
jak přibalit R knihovny, jak zálohovat a přenést data na jiný stroj a co dělat,
když appka naskočí, ale úlohy ne: [`docs/hosting.md`](docs/hosting.md).

**Proměnné prostředí jsou jen výchozí hodnoty.** Provider, adresu, klíče, modely
i přihlášení přes bránu přepneš bez restartu v menu **Správa** — ukládají se do
`state/config.json` (mód 600). Tajemství se do prohlížeče nikdy nevrací, jen
maskovaná ukázka. Díky tomu jde instance nasadit jinde a nastavit ji z
prohlížeče, aniž bys sahal do spouštěcího skriptu.

## Role

| role | co smí |
|---|---|
| `student` | dnešní dávka, knihovna úloh, vlastní poznámky, vlastní progres, nastavení, změna hesla |
| `teacher` | navíc přehled všech studentů (aktivita, úspěšnost na první dobrou, slabá místa), přidávat a měnit úlohy |
| `admin` | navíc účty (vznik, role, nastavení hesla), volba modelu, stav systému, přehled záloh a ruční snímek DB |

Role se nastavuje v `RPRAXE_USERS` anebo v menu **Správa** (admin). Učitel
nevidí cizí poznámky ani změnu hesla jiného uživatele — jen souhrny.

## Třídy / Classes

Účet může patřit do několika tříd a tříd může mít učitel kolik chce — klidně se
stejnými žáky v ranní i odpolední skupině. Tabulky `classes` a
`class_students` jsou v téže databázi; sdružení je jen pohled, ne vlastnictví.

Učitel i správce založí třídu v záložce **Třída** (karta *Třídy*): název,
nepovinná poznámka a výběr žáků. Uložené třídy se dají upravit i smazat —
účty zůstanou, zmizí jen sdružení. Přehled žáků ukazuje, v jakých třídách kdo
je. Nová instance dostane jednu **Ukázkovou třídu**, aby bylo zřejmé, jak to
má vypadat; klidně ji přejmenuj nebo smaž.

## Nastavení a jazyky

Menu uživatele → **Nastavení**: motiv (systémový / světlý / tmavý), jazyk
rozhraní (cs / en / sk / de / pl) a délka denní dávky. Preference se drží
v databázi, takže po přihlášení na jiném zařízení sedí stejně; motiv se aplikuje
ještě před vykreslením, aby stránka neblikala.

**Model si uživatel nevolí** — v nastavení jen vidí, kterého kouče nasadil
správce. Hodí se to v produkci i ve třídě: všichni mají stejné chování a
náklady na model rozhodují na jednom místě.

## Modely (volí správce)

Menu **Správa → Modely** nastaví, odkud se AI bere: vlastní Ollama,
OpenAI-kompatibilní brána (včetně GitHub Models, Groq či vLLM — jen přepíšeš
adresu), Anthropic nebo Google Gemini, zvlášť model na povídání a na tvorbu
úloh. Uloženo v `state/config.json` (mód 600), klíč se do prohlížeče nevrací.
Tlačítko *uložit a vyzkoušet* rovnou napíše, jestli model odpovídá. Pro
akademické nasazení je tam i předvolba **e-INFRA LLM API** (`RPRAXE_PROVIDER=einfra`,
`https://llm.ai.e-infra.cz/v1`, styl OpenAI) — klíč si vygeneruje každý v Chat WebUI
a název modelu zkopíruje ze seznamu, protože se mění.
Karta u každého poskytovatele řekne, jestli data opouštějí dům, kde se bere
adresa (Ollama `http://stroj:11434`, OpenAI `https://api.openai.com/v1`, GitHub
Models `https://models.inference.ai.azure.com`, Groq, vLLM …) a odkazy, kde
vytvořit klíč. U poskytovatelů, kteří klíč vyžadují, je pole povinné — bez něj
se nastavení neuloží. Jsou-li na adrese dostupné modely, nabídnou se
v roletce; jinak se jméno napíše.

## Kontrola vygenerovaných úloh

Učitel i správce má v knihovně tlačítko **prozkoumat**:

1. strukturovaný pohled — zadání, startovací kostka, **řešení** a kontrolní kód
   každé zvlášť, k tomu dataset a jeho hlavička,
2. **ověřit spuštěním** — řešení musí projít, prázdný kód a startovací kostka
   nesmí; vidíš výstup i to, jaké knihovny sandbox nabízel,
3. **nechat zkontrolovat modelem** — model úlohu kritizuje a může navrhnout
   opravenou kontrolu,
4. teprve pak **schválit a pustit do nabídky**. Koncept (`draft`) se studentům
   nikdy neukáže.

Koncept se dá i **upravit**: tlačítkem *upravit v editoru* se úloha nahraje do
editoru. Před uložením ji aplikace sama prověře — řešení musí projít a prázdný
kód ani startovací kostka nesmí — a volitelně ji čte i model a vyjmenuje
nejasnosti. Když prověrka nevyjde, uložení se **odmítne** a stará verze zůstane;
*uložit i přesto* uloží rozdělaný nápad jako koncept, který studenti nevidí.

## Zálohy

Denní zálohu dělá skript [`scripts/backup.sh`](scripts/backup.sh): konzistentní
snímek běžící SQLite (`sqlite3 .backup`) plus `state/users.json` a
`state/secret.key` — bez těch dvou by obnovená aplikace sice běžela, ale nikdo
by se nepřihlásil. Archiv putuje na jedno místo, které určíš, a rotuje se
(default 7 kopií). Menu **Správa** ukazuje stáří poslední zálohy a umí
okamžitý snímek DB; nabídku nastavení záloh najdeš tamtéž.

```sh
cp scripts/backup.sh /usr/local/bin/ && crontab -e
# 40 3 * * * /usr/local/bin/backup.sh /mnt/nas/zalohy/rpraxe 7
```

**Obnova ze zálohy** je i v prohlížeči: menu **Správa → Zálohy a obnova** ukáže
snímky (včetně počtu pokusů a úloh v každém), a tlačítko *načíst* databázi
vrátí ke zvolenému snímku. Před obnovou se vždy udělá pojistka
`pred-obnovou-*.db` a po opsání slova `OBNOVIT` se teprve přepíše. Účty a
hesla zůstávají v `state/users.json`, takže je obnova DB nepokazí.

Ručně zvenčí: `docker compose down`, nahradit `state/rpraxe.db` a rozbalit
`rpraxe-ucty-*.tgz` do `state/`, `docker compose up -d`.

## K čemu jsou poznámky

Poznámka visí na dvojici (účet, úloha) a je to **cizí slovo pro to, co si žák
zapíše sám**: proč mu úloha nedala spát, na co si dát pozor. Není to hodnocení
ani vzkaz — systém z ní nic neposuzuje a kouč ji nedostává. Má cenu proto, že
za měsíc si nikdo neneše, v čem tehdy chyboval; a učitel podle nich pozná, kde
skupina zápasí, i když počet pokusů vypadá dobře. Prázdné pole se mažou, aby
se v nich nehromadilo nic.

## Banka úloh

`tasks/*.py` — moduly se seznamem `TASKS`; načítají se při startu do SQLite
(při načtení se **nepřepisuje** `level`, který si systém odpozoroval z pokusů).
Lekce 1–11: základy → datové struktury → indexace → načítání + pipes/dplyr →
funkce, smyčky, apply, datum a čas → grafy a ggplot2 → statistika.

Pole: `id, title, lesson, minutes, level, skills, dataset, nacti, starter,
zadani, hints[], check (R), reseni (R), libraries[]`. Helpery v kontrolce:
`.v_num(got, want, tol)`, `.v_txt`, `.v_df`, `.v_plot`, `.v_contains`,
`.v_spam(msg)`, `.v_ok(msg)` — definice v `runner/server.py`.

Jak psát úlohy a jak je ověřit spuštěním:
[`docs/task-banks.md`](docs/task-banks.md).

## Architektura a sandbox

```
prohlížeč ──HTTPS──> reverse proxy ──> app (FastAPI, :8080)
                                         ├──> runner (:8081, interní síť, bez východu)
                                         │      └─ Rscript jako uživatel sandbox, limity
                                         └──> Ollama (kouč + generování úloh)
data: ./datasets (syntetická, do runneru jen čtenářsky)
stav: ./state/rpraxe.db + state/users.json
```

* `runner` sedí na síti `internal: true` — studentský R kód se k internetu nemá
  jak dostat.
* Kód pouští `setpriv` na neprivilegované uid, s `RLIMIT_CPU/AS/NPROC/FSIZE`,
  nástěnným timeoutem, `tmpfs /work` a výstupem zkráceným na 40 kB. V pracovním
  adresáři leží jen data dané úlohy a po běhu se mažou.
* Žádné CDN — editor (CodeMirror) je vendorený v `web/vendor/`, aplikace
  funguje offline v LAN.
* Cookie `HttpOnly` + `SameSite=Lax`, PBKDF2-SHA256 (240k iterací) na hesla,
  relace 30 dní, po pěti špatných heslech desetiminutová pauza.
* Každý text, který vygeneruje model a uvidí ho uživatel, nejdřív projde
  strojovým ověřením (spustit, porovnat, zahodit).

## Brány při buildu

`scripts/check_static.py` běží v Dockerfile i při startu kontejneru a hlídá dvě
věci, které se navenek tváří jako „aplikace nic nedělá“: odkaz v `index.html`
na neexistující soubor (černá stránka) a tlačítko či skupinu ovládání, na nichž
v `app.js` nic není (klik bez reakce, v logu ticho). `scripts/validate.py`
spustí řešení každé úlohy v sandboxu a ověří, že kontrolka odpoví stejně;
na konci napíše `N v pořádku, M s problémem z K`.

## Co vidí uživatel po spuštění kódu

* `stdout` — co kód vypsal, `poslední výraz` — co vrátil poslední řádek.
* Když kód nic nevypsal (typicky `v <- ...`), aplikace vysvětlí, že R u
  přiřazení záměrně mlčí, a vypíše **co zůstalo v prostředí** — jméno proměnné
  a krátký `str()` popis hodnoty.
* Záložka **data** u úlohy vykreslí CSV jako skutečnou tabulku (s počtem
  řádků); textové `.txt` podklady zůstanou textem.

## Hesla a jejich reset

* Výchozí hesla jsou v `rpraxe.env`; při prvním startu se z nich stanou PBKDF2
  hashe v `state/users.json`. Ten je pak rozhodující — `env_file` se už
  nedočítá, takže změna hesla přežije restart i rebuild.
* Uživatel: menu vpravo nahoře → **Změnit heslo** (vyžaduje současné, min. 8
  znaků, nesmí být jednostranné).
* Zapomenuté heslo: admin v **Správa** → *nové heslo*, nebo smazat klíč účtu ze
  `state/users.json` a restartovat — účet se osadí znovu z `rpraxe.env`.
* `state/users.json` je součástí zálohy, takže se dá vrátit i dříve používané
  heslo.

## Naše nasazení (domácí)

Na jednom miniPC: `docker compose` (varianta dva kontejnery, takže R nemá
přístup ven) s image `rpraxe:latest`, aplikace na
`172.20.0.1:8710`, před ní Caddy brána s wildcard certifikátem, DNS přes
Pi-hole — `https://r-praxe.schebique.eu`, dostupné z LAN a tailnetu, nikdy
veřejně. Kouč i generátor běží na Ollamě na sousedním stroji
(`qwen3.5:9b`, `qwen3.6:35b-a3b`). Noční agent (`agent/nightly.py`) běhá 3×
týdně a záloha jednou denně na NAS s rotací 7 dnů.

## Vývoj a testy

```sh
python -m compileall app runner agent scripts tasks        # syntax
python3 scripts/check_navody.py                            # návody sedí ke složení
python3 scripts/validate.py                                # banka úloh i bez kontejneru
docker compose exec rpraxe /opt/venv/bin/python /srv/scripts/check_static.py
docker compose exec rpraxe /opt/venv/bin/python /srv/scripts/validate.py
```

`scripts/check_navody.py` kontroluje to, co se jinak odhalí až při instalaci
cizím člověkem: že `docker compose exec` jmenuje skutečnou službu, že soubory,
na které příkazy ukazují, v repozitáři jsou, že žádný návod nečeká tag obrazu,
který `docker build` ani GHCR nedává, a že každá `RPRAXE_*` ze seznamu
proměnných v kódu něco dělá. Běží bez Dockeru a je i v CI.

Frontend se dá ověřit i bez prohlížeče přes jsdom
([`docs/testing.md`](docs/testing.md)) — po každé změně `web/` se to vyplatí
spustit na běžící instanci, projde to totiž skutečným klikáním:

```sh
RPRAXE_URL=http://127.0.0.1:8710 node test/dom.mjs ondra   # správce
RPRAXE_URL=http://127.0.0.1:8710 node test/dom.mjs lenka   # student
```

Provoz hotové instance (zálohy, obnova, denní kontrola) má vlastní
[`docs/provoz.md`](docs/provoz.md), nasazení a migrace
[`docs/hosting.md`](docs/hosting.md). Podmínky pull requestu:
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

[MIT](LICENSE). Syllabus kurzu je dílem Mgr. Lucie Hoškové (Katedra
psychologických a behaviorálních studií FSS MU); texty úloh v `tasks/` jsou
vlastní a uvolněné pod MIT.
