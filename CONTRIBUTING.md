# Přispět do R v ruce

Díky. Než pošleš pull request, nastřel si prostředí a projdi podmínky níže.
Není to byrokracie — v téhle aplikaci se špatná úloha nebo špatný odkaz ukážou
až v rukou člověka, který se právě učí R.

## Co musí projít

```sh
python -m compileall app runner agent scripts tasks
python3 test/behriste.py                              # adresa běžce R pro obě varianty
docker compose exec rpraxe /opt/venv/bin/python /srv/scripts/check_static.py   # service se jmenuje `rpraxe` (dřív `app`)
docker compose exec rpraxe /opt/venv/bin/python /srv/scripts/validate.py
```

* `check_static.py` — každý odkaz v `index.html` existuje a každé tlačítko má
  obsluhu. Bez toho je černá stránka nebo klik bez reakce a v logu ticho.
* `validate.py` — řešení každé úlohy projde vlastní kontrolkou a prázdný kód
  musí spadnout. Poslední řádek budiž `… 0 s problémem z …`.
* Přidej-li text rozhraní, přidej ho i do `web/i18n.js` pro `en`, `sk`, `de`,
  `pl`. Bez překladu se text vrátí do češtiny, což je vidět.

## Styl, který tu držíme

* Krátké věty, konkrétní jména. Komentář vysvětluje *proč*, ne *co*.
* Čeština bez cizích písem. Vygenerované texty umí vrátit Čínské znaky nebo
  cyriliku; hlídej to takhle:

  ```sh
  grep -rnP '[\x{4E00}-\x{9FFF}\x{3040}-\x{30FF}\x{0400}-\x{04FF}]' \
    --include='*.py' --include='*.js' --include='*.html' --include='*.md' .
  ```

* Řetězce s R uvnitř Pythonu: každý newline je `\\n`. Po patchi vždy vygeneruj
  skutečný R skript a testej `"\nif (" in generated`, ne `in source`.
* Schéma SQLite se vyvíjí migrací v `store.init()` podle `PRAGMA table_info` —
  `CREATE TABLE IF NOT EXISTS` sloupec do existující tabulky nepřidá.
* `PRIMARY KEY` se musí shodovat s `ON CONFLICT(…)`.
* Nová tabulka nebo sloupec znamená i migraci a test na existující databázi.
* Nikdo nepřidá CDN ani externí skript. Aplikace běží v LAN bez venkovní sítě;
  knihovny se vendorují do `web/vendor/`.
* Limity a bezpečnost sandboxu neměň bez důvodu: `runner` je na síti
  `internal` a studentský kód se pouští pod `setpriv` s limity.

## Zpráva ke commitu

```
správa účtů: učitel vidí jen souhrny, ne poznámky

Učitel potřebuje vidět, komu se nedaří, ne co si kdo píše. Soukromí studenta
drží i to, že /api/class vrací agregáty a poznámky zůstávají pod vlastnickou
kontrolou.
```

## Co s pull requestem neuděláme

* Nezařadíme úlohu, která neprošla `validate.py`.
* Nepřeskočíme `check_static.py` kvůli rychlé opravě v UI.
* Neměníme schéma bez migrační větve — lidé mají vlastní data.
