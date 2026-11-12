# Testy bez prohlížeče

## Brány, které běhají samy

* `scripts/check_static.py` — v Dockerfile i při startu kontejneru. Odkazy
  v `index.html` musí existovat a každé `<button id="…">` i každá `data-*`
  skupina musí mít v `app.js` obsluhu. Negativní test (chybějící soubor)
  udělej v kopii adresáře `web/`, ať stráž nespadne dřív na cestách.
* `scripts/validate.py` — solutions v sandboxu, viz `task-banks.md`.
* `test/behriste.py` — adresa běžce R. Běží bez Dockeru, ale kontroluje i to,
  co se ukáže až uvnitř kontejneru: `docker compose exec` nedostane proměnné z
  entrypointu, takže skript musí poznat vestavěný sandbox sám.

## Frontend přes jsdom

`node --check` odhalí jen syntax, ne `is not a function` na reálných datech.
Na stroji bez Chromium se vyplatí jsdom (~150 kB npm místo 500 MB prohlížeče):

```sh
cd test && npm install jsdom
RPRAXE_PASS_LENKA=… RPRAXE_PASS_ONDRA=… node test/dom.mjs lenka
```

Harness (`test/dom.mjs`) načte `web/index.html` z disku, `beforeParse` mu
nasadí stuby (`CodeMirror`, `requestAnimationFrame`, `matchMedia`,
`ResizeObserver`, míry elementů) a `window.fetch` posílá na běžící nasazení
s reálným cookie účtu. Pak projde `click()`-em všechna view a vyhlásí:

* délku vykresleného textu každé záložky (prázdná záložka = selhání),
* jestli se někde použilo `prompt()`/`confirm()` (nesmí — prohlížeč je umí
  zamítnout a jednořádkový `prompt()` se nedá číst),
* jestli se motiv a jazyk skutečně přeply (`documentElement.dataset.theme`,
  text navigace),
* součet JS chyb z `virtualConsole`.

`window.focus()` jsdom neumí — v harnessi je proto stub; není to chyba aplikace.

## Co otestovat rukou po změně, která sahá do přihlášení

1. přihlášení špatným heslem → hláška, počet pokusů, pauza po pěti
2. změna hesla → nové platí, staré ne, **po restartu kontejneru** taky
   (to je důkaz, že rozhoduje `state/users.json`, ne `env_file`)
3. druhý účet má po všech krocích pořád stejný otisk hesla
4. role: `student` na `/api/class` a `/api/users` musí dostat 403
