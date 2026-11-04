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
* **Local AI coach** — a Socratic nudge from your own Ollama model; hand-written
  hints stay hand-written and the model never sees the solutions.
* **Nightly author agent** (optional) — drafts new tasks and only publishes the
  ones that pass automated validation: the solution must pass its own checker
  and empty code must fail.
* **Roles** — `student` (own practice), `teacher` (student progress, own tasks),
  `admin` (accounts, models, backups).
* **Notes, cheat sheet, progress** — multi-line notes per task, per-lesson cheat
  sheet, first-try success rate, streak, skill profile, CSV export.
* **UI languages** — čeština (source), English, slovenčina, Deutsch, polština;
  task texts stay in the language of the bank you use.
* **SSO-ready** — trust an authenticator proxy (Authelia, Authentik, oauth2-proxy)
  via signed headers; password login stays available as a fallback.

---

## Rychlý start / Quickstart

```sh
git clone <repo> && cd rpraxe
cp rpraxe.env.example rpraxe.env && chmod 600 rpraxe.env      # vyplň hesla účtů
docker build -t rpraxe:1 .
docker compose up -d
docker compose exec app Rscript /srv/r/gen_datasets.R         # syntetická data
docker compose exec app /opt/venv/bin/python /srv/scripts/validate.py
```

Pak `http://127.0.0.1:8710` (nebo `http://localhost:${RPRAXE_PORT}`). První
přihlášení funguje s hesly z `rpraxe.env`; pak si je každý změní v profilu a
od té doby platí jen to, co je v `state/users.json`.

Without Docker (during development):

```sh
docker compose up -d runner
python -m venv .venv && .venv/bin/pip install fastapi "uvicorn[standard]" httpx pyyaml python-multipart
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
| `RPRAXE_SECRET` | podpis session cookie (`openssl rand -hex 32`) | vygeneruje se do `state/secret.key` |
| `RPRAXE_OLLAMA` | adresa Ollamy; prázdné = AI vypnutá | prázdné |
| `RPRAXE_MODEL` / `RPRAXE_MODEL_WRITE` | model kouče / generování úloh | `qwen3.5:9b` / `qwen3.6:35b-a3b` |
| `RPRAXE_DB`, `RPRAXE_DATASETS`, `RPRAXE_WEB`, `RPRAXE_TASKS` | cesty uvnitř kontejneru | výchozí sedí |
| `RPRAXE_CPU_LIMIT`, `RPRAXE_WALL_LIMIT`, `RPRAXE_MEM_MB` | limity sandboxu | `20`, `30`, `1500` |
| `RPRAXE_SSO_*` | přihlášení přes bránu, viz [docs/sso.md](docs/sso.md) | vypnuto |
| `RPRAXE_BIND`, `RPRAXE_PORT` (v souboru `.env`) | na čem poslouchá container | `127.0.0.1:8710` |

AI vrstva je nepovinná: bez Ollamy funguje zadávání, kontrola, adaptivní plán i
progres; kouč jen odpoví z ručně psaných nápověd.

## Role

| role | co smí |
|---|---|
| `student` | dnešní dávka, knihovna úloh, vlastní poznámky, vlastní progres, nastavení, změna hesla |
| `teacher` | navíc přehled všech studentů (aktivita, úspěšnost na první dobrou, slabá místa), přidávat a měnit úlohy |
| `admin` | navíc účty (vznik, role, nastavení hesla), volba modelu, stav systému, přehled záloh a ruční snímek DB |

Role se nastavuje v `RPRAXE_USERS` anebo v menu **Správa** (admin). Učitel
nevidí cizí poznámky ani změnu hesla jiného uživatele — jen souhrny.

## Nastavení a jazyky

Menu uživatele → **Nastavení**: motiv (systémový / světlý / tmavý), jazyk
rozhraní, délka denní dávky a model AI kouče (vybírá se z modelů, které má
Ollama skutečně nahrané). Preference se drží v databázi, takže po přihlášení na
jiném zařízení sedí stejně; motiv se aplikuje ještě před vykreslením, aby
stránka neblikala.

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

Obnova: `docker compose down`, nahradit `state/rpraxe.db` a rozbalit
`rpraxe-ucty-*.tgz` do `state/`, `docker compose up -d`.

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

Na jednom miniPC: `docker compose` s image `rpraxe:1`, aplikace na
`172.20.0.1:8710`, před ní Caddy brána s wildcard certifikátem, DNS přes
Pi-hole — `https://r-praxe.schebique.eu`, dostupné z LAN a tailnetu, nikdy
veřejně. Kouč i generátor běží na Ollamě na sousedním stroji
(`qwen3.5:9b`, `qwen3.6:35b-a3b`). Noční agent (`agent/nightly.py`) běhá 3×
týdně a záloha jednou denně na NAS s rotací 7 dnů.

## Vývoj a testy

```sh
python -m compileall app runner agent scripts tasks        # syntax
docker compose exec app /opt/venv/bin/python /srv/scripts/check_static.py
docker compose exec app /opt/venv/bin/python /srv/scripts/validate.py
```

Frontend se dá ověřit i bez prohlížeče přes jsdom
([`docs/testing.md`](docs/testing.md)). Podmínky pull requestu:
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

[MIT](LICENSE). Syllabus kurzu je dílem Mgr. Lucie Hoškové (Katedra
psychologických a behaviorálních studií FSS MU); texty úloh v `tasks/` jsou
vlastní a uvolněné pod MIT.
