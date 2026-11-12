# Vlastní banka úloh na GitHubu

Učitel i správce může mít vlastní sbor zadání v repozitáři a do instance je
přenést. Nic se nesynchronizuje na pozadí — stiskne se *načíst z GitHubu*,
soubor se stáhne a každá úloha se přezkouší spuštěním v sandboxu. Co projde,
dostane status **schváleno**; ostatní zůstanou jako **koncept**, který studenti
nevidí, a učitel je dočítá v editoru.

## Co vložit do rozhraní

Stačí odkaz na repozitář, nebo rovnou na soubor:

```
https://github.com/jan-novak/ulohy-r
https://github.com/jan-novak/ulohy-r/blob/main/ukoly.json
jan-novak/ulohy-r
```

Bez upřesnění cesty zkusí `ukoly.json`, `tasks.json` a `ulohy.json` na větvích
`main` a `master`. Opakovaný dovoz stejného souboru úlohy **upgraduje** (stejné
`id`), nekopíruje je.

## Formát souboru

JSON — buď rovnou pole úloh, nebo objekt `{"ukoly": [...]}`. Klíče můžou být
česky i anglicky:

```json
[
  {
    "id": "skupiny-01",
    "title": "Průměr skupin",
    "lesson": 5,
    "minutes": 5,
    "level": 2.2,
    "skills": ["group_by", "summarise"],
    "dataset": "zkousky.csv",
    "nacti": "data <- read.csv('zkousky.csv')",
    "zadani": "Spočítej průměr bodů pro každý `skupina` a výsledek ulož do `prumer`.",
    "starter": "library(dplyr)\n# data <- ...",
    "reseni": "library(dplyr)\nprumer <- data %>% group_by(skupina) %>% summarise(body = mean(body, na.rm = TRUE))",
    "check": "exists('prumer') && nrow(prumer) == length(unique(data$skupina))",
    "hints": ["group_by(), pak summarise()", "na.rm = TRUE"]
  }
]
```

| klíč (cs) | klíč (en) | povinné | význam |
|---|---|---|---|
| `zadani` | `task` | ano | zadání, co žák vidí |
| `reseni` | `solution` | ano | řešení, které musí projít kontrolou |
| `kontrola` | `check` | ano | R kód vracející `TRUE`, `FALSE` nebo `list(pass=, msg=)`; funguje i `stopifnot()` |
| `název` | `title` | ne | nadpis, jinak prvních 60 znaků zadání |
| `lekce` | `lesson` | ne | číslo lekce 0–11 |
| `minuty` | `minutes` | ne | délka v minutách |
| `obtížnost` | `level` | ne | 0–5 |
| `dovednosti` | `skills` | ne | pole nebo řetězec oddělený čárkami |
| `dataset` | `dataset` | ne | soubor z `data/datasets/` |
| `načti` | `nacti` | ne | R kód, který data načte před řešením |
| `kostra` | `starter` | ne | startovací kostka; musí kontrolou **neprojit** |
| `napovědy` | `hints` | ne | řádky nápovědy |
| `id` | `id` | ne | stabilní identifikátor; bez něj se odvodí ze jména repozitáře |

## Pravidla, která kontrola musí splnit

1. `reseni` + `kontrola` v sandboxu **projde**.
2. Prázdný kód a `kostra` kontrolou **neprojdou** — jinak by úloha šla
   splnit bez práce.
3. Kontrola počítá očekávanou hodnotu z dat, netvrdí nic napevno.

To druhé je důvod, proč se některé importované úlohy zachovají jako koncept:
stroj je zkusil a neprošly. V přehledu konceptů pak slouží tlačítko *nechat
opravit modelem* — model je přepíše podle výstupu z R a znovu je přezkouší;
rozhodnutí o schválení ale pořád patří člověku.

## Bezpečnost a soukromí

Stahuje se přes `raw.githubusercontent.com`, tedy veřejně dostupný obsah.
Repositoráře v soukromí musí být dostupné odkud instance běží (tohle vydání
posílá na GitHub requesty bez autentizace). R kód se z repozitáře dostane do
stejné izolované nádoby jako kód studenta — bez sítě, s limitem času i CPU.
