# Provoz „R v ruce“ (rpraxe)

## Kde co je
- aplikace: `rpraxe-app-1` na `umaxque-server`, naslouchá `127.0.0.1:8710`
- pískoviště s R: `rpraxe-runner-1` — bez přístupu do sítě, datům jen čte
- stav: `state/` vedle `docker-compose.yml` → v kontejneru `/data/state`
  (`rpraxe.db`, `users.json`, `config.json`, `secret.key`, `backups/`)
- datové soubory úloh: `datasets/` → `/data/datasets` (appka zapisuje, runner čte)
- banky úloh: `tasks/*.json`, fronta: `web/`
- HTTPS: `https://r-praxe.schebique.eu` → Caddy → `127.0.0.1:8710`

## Účty a role
- `RPRAXE_USERS="lenka:student,ondra:admin"` je **výčet** účtů, ne cesta
- `RPRAXE_USERS_FILE` je cesta k souboru účtů — výchozí `/data/state/users.json`
  (dřív si o jednu proměnnou kořistily dvě věci a účty se psaly do souboru
  pojmenovaného podle celého výčtu doprostřed obrazu; aplikace to sama přenese)
- heslo účtu `x` nastaví `RPRAXE_PASS_X`; bez toho se vygeneruje a jednou se
  vypíše do logu (pod klíčem `first_pw`)
- role `student` · `teacher` · `admin` se mění ve Správě; projeví se po
  novém načtení stránky
- role z `RPRAXE_USERS` se při startu dosazují na účty, které výčet jmenuje —
  účet založený v rozhraní si roli drží
- relace drží 30 dní; menu vpravo nahoře má „odhlásit ostatní zařízení“,
  což zneplatní všechna předchozí přihlášení daného účtu najednou
- přihlašování brzdí: 6 špatných pokusů na účet nebo IP ⇒ 10 minut zámek.
  Správce vidí zadržené účty v kartě Provoz

## Zálohy
- skript: `scripts/backup.sh <cil> [pocet_kopii] [kontejner]`
  - Konzistentní snímek DB za chodu (`sqlite3 .backup` uvnitř kontejneru),
    `state/users.json` + `state/secret.key`, banky úloh a nasazení,
    `state/config.json`, rotace
  - na konci napíše `backup.json` se **jmeny souborů**, které realmente
    existí — API je pak neukazuje jako chybějící
- nasazení do cronu na hostiteli:
  ```sh
  cp -f ~/dev/rpraxe/scripts/backup.sh /usr/local/bin/rpraxe-zaloha.sh
  chmod +x /usr/local/bin/rpraxe-zaloha.sh
  ( crontab -l | grep -v rpraxe-zaloha; \
    echo '30 3 * * * /usr/local/bin/rpraxe-zaloha.sh /srv/zalohy/rpraxe 14 rpraxe-app-1 >> /home/hermes/.hermes/logs/zaloha.log 2>&1' ) | crontab -
  ```
  (hostitel `hermes` má `sudo -n docker`, jinak by se ke kontejneru nedostal)
- cíl je `/srv/zalohy/rpraxe`; adresář se zálohuje s celým `/srv/zalohy`
- kontrola: karta Zálohy ve Správě, nebo `GET /api/admin/backups` —
  `backup.json` obsahuje čas, velikost a `ucet_souboru`/`config`

## Obnova (cvičit, ne jen mít)
1. `GET /api/admin/backups` → vybrat snímek
2. `POST /api/admin/restore` s `{"jmeno": "…", "potvrdit": "OBNOVIT"}`
   – aktuální DB se před přepisem kopíruje do `state/backups/pred-obnovou-*.db`
3. účty: `tar xzf rpraxe-ucty-<cas>.tgz -C ~/dev/rpraxe` a restart appky
4. datové soubory: `tar xzf rpraxe-data-<cas>.tgz -C ~/dev/rpraxe`

Záloha se osvěží i tlačítkem ve Správě (`POST /api/admin/backup`) — pak je
vidět čerstvý čas bez čekání na noc.

## Zdravotní stav a logy
- `GET /healthz` — barva, počet úloh, odpověď runnera; používá ho
  `HEALTHCHECK` v compose i externí hlídání
- logy kontejnerů rotují (10 MB × 3 soubory), takže disk nezaplní
  kecy z R
- limity pískoviště (CPU, zeď, RAM) nastavuje `docker-compose.yml`;
  karta Provoz je čte z `GET /limits` runnera, ať je správce nemusí hledat
  v souborech

## Co hlídat
| věc | kde | co znamená |
|---|---|---|
| záloha stará > 30 h | Správa → Zálohy | cron neběží nebo je cíl nedostupný |
| chybějící dataset | Správa → Provoz | úloha odkazuje na soubor, který nikdo nenahrál |
| zadržené účty | Správa → Provoz | někdo zkouší hádat hesla (nebo si to uživatel zasloužil) |
| runner nedostupný | `/healthz`, Provoz | pískoviště vstalo nebo nemá data |
