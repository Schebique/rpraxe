# Banka úloh: jak psát a jak ověřit

Úlohy jsou Python moduly v `tasks/`, každý se seznamem `TASKS`. Není to
databáze textů — každá úloha se **spouští**, takže špatný záznam se projeví
ihned. Jeden zlý záznam by přitom strhl celý start aplikace, proto se moduly
načítají s tolerancí: rozbitná úloha se přeskočí a zapíše se do logu.

## Pole úlohy

```python
{
  "id": "pipe-03",              # unikátní, drží se v historii i v SRS
  "title": "mutate: novy sloupec",
  "lesson": 4,                  # lekce sylabu 1..11
  "minutes": 5,                 # odhad, sčítá se do denní dávky
  "level": 2.0,                 # start obtížnost; systém ji přepočítá z pokusů
  "skills": ["mutate", "pipes"],# klíče pro adaptivní model (společné napříč bankami)
  "dataset": "zbozi.csv",       # soubor v datasets/, nebo None
  "nacti": 'zbozi <- read.csv("zbozi.csv", dec = ",")',  # úvod do světa úlohy
  "starter": 'library(dplyr)\nzbozi %>% …',              # co vidí uživatel
  "zadani": "Přidej sloupec …", # zadání česky, v přítomném čase, jedná věc navíc max.
  "hints": ["…", "…"],          # ručně psané, od náznaku ke konkrétnímu tvaru
  "check": '…',                 # R kód; zavolá .v_ok / .v_spam, viz níže
  "reseni": '…',                # kompletní řešení — musí samo projít kontrolou
  "libraries": ["dplyr"],
}
```

`reseni` se zobrazuje po kliknutí na „ukázat řešení“ a používá ho i validátor:
musí tedy být **samostatně spustitelné** (včetně načtení dat a dílčích
proměnných), ne jen poslední řádek.

## Helpery kontrolky (definice v `runner/server.py`)

| helper | význam |
|---|---|
| `.v_num(got, want, tol = 1e-4, msg_ok)` | číselná hodnota sedí (v tolerance) |
| `.v_txt(got, want, msg_ok)` | text sedí (po srovnání mezer a velikosti písmen) |
| `.v_df(got, want, msg_ok)` | data.frame má stejný tvar i hodnoty jako `want` |
| `.v_plot(got = NULL, msg_ok)` | uživatel vykreslil graf — base `plot()` i `ggplot2` |
| `.v_contains(got, pattern, msg_ok)` | řetězec obsahuje hledaný vzor |
| `.v_spam(msg)` | stop — `msg` musí říct **druh** chyby, ne výsledek |
| `.v_ok(msg)` | hotovo, splněno |

Kontrolka nečte očekávanou hodnotu ze zadání — počítá ji z dat.
`check` tedy bývá: spočítej `chceno` z `datasetu`, porovnej s tím, co uživatel
uložil do proměnné, a když nesedí, popiš, co chybí.

## Druhy chyby, ne výsledek

`"agreguj přes na.rm = TRUE"` ✓ — `"správně je 12,4"` ✗. Student má zůstat
v úloze, ne ji opisovat.

## Ověření celé banky

```sh
docker compose exec rpraxe /opt/venv/bin/python /srv/scripts/validate.py         # všechno
docker compose exec rpraxe /opt/venv/bin/python /srv/scripts/validate.py pipe-03 # jedna
```

Validátor pro každou úlohu: (1) pustí `reseni` v sandboxu a zavolá `check` —
musí projít; (2) pustí prázdný kód — `check` musí spadnout; (3) hlásí
podezřelé texty (cizí písma v češtině, `TODO`, neukončené přiřazení ve `starter`).
Poslední řádek je shrnutí: `N v pořádku, M s problémem z K`. V CI je povinné
`M == 0`.

Dlouhou validaci pouštěj detachovaně, ať nesekneš terminál:

```sh
docker compose exec -d app /opt/venv/bin/python /srv/scripts/validate.py \
  > state/validace.log 2>&1
tail -f state/validace.log
```

## Přenos banky: odkaz, soubor, export

Knihovna (Učitel → Knihovna, Správa → Banka úloh) umí úlohy **přenést dovnitř i ven**:

| cesta | jak | co se stane |
|---|---|---|
| odkaz | vložíš URL na `ukoly.json` (GitHub, raw, gist, `user/repo`) | stáhne se, přepíše cizí klíče, přepočítá `id` |
| soubor | vybereš `*.json` z počítače | stejná cesta, jen bez stahování |
| export | celá banka / právě vyfiltrovaná / jen vybrané | JSON, který se tímž tlačítkem vrátí zpátky |

Přenesené úlohy se **samozřetězně ověří**: `reseni` se pustí v sandboxu a musí
projít vlastní `check`. Co projde, je hned `approved`; co ne, zůstává `draft`
s poznámkou, proč to neprošlo. Učitel pak v bance vidí obojí a koncept buď
doplní, nebo zahodí. Limit je 200 úloh na přenos a 900 kB souboru.

Opakovaný přenos téhož souboru úlohy **upgraduje podle `id`**, nedělá dvojčata.

## Data k úlohám (dataset)

Dataset **není součástí JSONu** — úloha v sobě má jen jméno souboru
(`"dataset": "zkousky.csv"`) a `nacti` kód, který ho čte ze stejného jména.
Data jsou větší, může jich užít víc úloh a žák je dostává sandboxem.

Nahrávají se vedle úlohy, v editoru i v bance:

* tlačítko *nahrat data* pošle `.csv`, `.tsv` nebo `.txt` do `datasets/`,
* při přenosu JSONu lze přiložit rovnou i řádky (`"data": [{...}, ...]`) —
  server z nich ten soubor sepíše a pojmenuje ho podle pole `dataset`,
* export volbou *včetně dat* přibalí obsah souboru k každé úloze, takže se
  banka i s daty přenese na jinou instalaci,
* soubor, na který ještě něco ukazuje, mazání odmítne (ať se úloha neraZboří).

Formát: první řádek hlavička se jmény sloupců, dál stejný počet sloupců.
Jiný počet sloupců se oznámí i s číslem řádku, aby bylo kam sahat.

## Noční autor (nepovinné)

`agent/nightly.py` nechá lokální model napsat nové úlohy a **než je pustí do
hry, ověří je stejnou cestou jako validátor**. Co neprojde, zůstává v tabulce
`draft` a uživatel to nevidí. Spouští se uvnitř kontejneru aplikace, kde má
stejnou cestu k sandboxu i databázi:

```sh
docker compose exec rpraxe /opt/venv/bin/python /srv/agent/nightly.py 8
```
