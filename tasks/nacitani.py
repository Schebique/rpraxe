"""Lekce 4 — načítání dat, kontrola dat, chybějicí hodnoty, špinavé soubory."""

TASKS = [
    {
        "id": "nac-01",
        "title": "read.csv s desetinnou čárkou",
        "lesson": 4, "minutes": 4, "level": 2,
        "skills": ["nacitani", "cisteni", "read"],
        "dataset": "prodej_zbozi_sidla.txt",
        "zadani": ("Soubor `prodej_zbozi_sidla.txt` je oddělený `;` a má desetinnou čárku.\n"
                   "Načti ho do `zbozi` (pozor na `sep` a `dec`), zjisti počet řádků → `n_radku`\n"
                   "a vypiš `str(zbozi)`."),
        "starter": "zbozi <-\nn_radku <-\nstr(zbozi)\n",
        "hints": [
            "`read.table(\"prodej_zbozi_sidla.txt\", sep = \";\", dec = \",\", header = TRUE, stringsAsFactors = FALSE)`",
            "`read.csv(..., sep = \";\", dec = \",\")` funguje taky.",
        ],
        "check": ('sp <- read.table("prodej_zbozi_sidla.txt", sep = ";", dec = ",", header = TRUE, stringsAsFactors = FALSE)\n'
                  'if (!exists("zbozi")) return(.v_spam("Nenašel jsem data frame `zbozi`."))\n'
                  'a <- .v_num(get("n_radku"), nrow(sp))\nif (!a$pass) return(a)\n'
                  'if (is.character(get("zbozi")$cena))\n'
                  '  return(.v_spam("Pozor — cena se ti načetla jako text. Chybí argument dec s desetinnou čárkou."))\n'
                  'list(pass = TRUE, msg = "Ano. Když R neví, že desetinná oddělovačka je čárka, sloupec zůstane character.")'),
        "reseni": ('zbozi <- read.table("prodej_zbozi_sidla.txt", sep = ";", dec = ",", header = TRUE,\n'
                   '                 stringsAsFactors = FALSE)\nn_radku <- nrow(zbozi)\nstr(zbozi)\n'),
    },
    {
        "id": "nac-02",
        "title": "Textová čísla na čísla",
        "lesson": 4, "minutes": 4, "level": 3,
        "skills": ["cisteni", "as.numeric", "parse_number"],
        "dataset": "prodej_zbozi_sidla.txt",
        "zadani": ("Sloupec `pocet` vypadá jako „ 4 ks“ a `sleva` jako „10%“.\n"
                   "Uprav `zbozi` tak, aby `pocet` a `sleva_procento` byla čísla\n"
                   "(u slevy odstraň procento). Do `celkem_ks` ulož součet kusů."),
        "nacti": ('zbozi <- read.table("prodej_zbozi_sidla.txt", sep = ";", dec = ",", header = TRUE,\n'
                  '                 stringsAsFactors = FALSE)'),
        "starter": "library(dplyr)\nzbozi <- zbozi %>%\n\n celkem_ks <-\n",
        "hints": [
            "`readr::parse_number(pocet)` vytáhne číslo i z textu.",
            "`mutate(pocet = readr::parse_number(pocet), sleva_procento = readr::parse_number(sleva))`",
        ],
        "check": ('library(dplyr)\nsp <- read.table("prodej_zbozi_sidla.txt", sep = ";", dec = ",", header = TRUE, stringsAsFactors = FALSE)\n'
                  'sp_celkem <- sum(readr::parse_number(sp$pocet))\n'
                  'if (!exists("celkem_ks")) return(.v_spam("Chybí `celkem_ks`."))\n'
                  'if (!is.numeric(get("zbozi")$pocet)) return(.v_spam("`pocet` pořád není číslo."))\n'
                  '.v_num(get("celkem_ks"), sp_celkem, msg_ok = "Jo — `parse_number()` si poradí s mezerami, „ks“ i procenty.")'),
        "reseni": ('zbozi <- zbozi %>%\n'
                   '  mutate(pocet = readr::parse_number(pocet),\n'
                   '         sleva_procento = readr::parse_number(sleva))\n'
                   'celkem_ks <- sum(zbozi$pocet)\n'),
    },
    {
        "id": "nac-03",
        "title": "Chybějící hodnoty — kolik jich je",
        "lesson": 4, "minutes": 3, "level": 2,
        "skills": ["cisteni", "NA", "is.na"],
        "dataset": "kavarna.csv",
        "nacti": 'kavarna <- read.csv("kavarna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Zjisti, kolik řádků má chybějící `trzba` → `chybi_trzba`, a kolik řádků je\n"
                   "kompletních (bez NA ve `trzba` i `cena_ks`) → `kompletne`."),
        "starter": "chybi_trzba <-\nkompletne <-\n",
        "hints": [
            "`sum(is.na(kavarna$trzba))`",
            "`sum(complete.cases(kavarna[, c(\"trzba\", \"cena_ks\")]))`",
        ],
        "check": ('k <- read.csv("kavarna.csv", stringsAsFactors = FALSE)\n'
                  'a <- .v_num(get("chybi_trzba"), sum(is.na(k$trzba)))\nif (!a$pass) return(a)\n'
                  '.v_num(get("kompletne"), sum(complete.cases(k[, c("trzba", "cena_ks")])))'),
        "reseni": ('chybi_trzba <- sum(is.na(kavarna$trzba))\n'
                   'kompletne <- sum(complete.cases(kavarna[, c("trzba", "cena_ks")]))\n'),
    },
    {
        "id": "nac-04",
        "title": "Falší N/A na skutečné NA",
        "lesson": 4, "minutes": 5, "level": 3,
        "skills": ["cisteni", "NA", "mutate"],
        "libraries": ["dplyr"],
        "dataset": "lab_vzorky.csv",
        "nacti": 'vzorky <- read.csv("lab_vzorky.csv", stringsAsFactors = FALSE)',
        "zadani": ("Sloupec `namnozeni` obsahuje i text „N/A“. Převeď „N/A“ a prázdný text na `NA`,\n"
                   "„NE“ převeď na „ne“ a výsledek ulož jako faktor do `vzorky$namnozeni_cisto`.\n"
                   "Do `pocet_ne` pak dej, kolik je vlastně „ne“."),
        "starter": "library(dplyr)\nvzorky <- vzorky %>% mutate(\n  namnozeni_cisto = \n)\npocet_ne <-\n",
        "hints": [
            "`case_when(namnozeni %in% c(\"N/A\", \"\") ~ NA_character_, namnozeni == \"NE\" ~ \"ne\", TRUE ~ namnozeni)`",
            "Na faktor: `factor(..., c(\"ano\", \"ne\"))`; počet je `sum(vzorky$namnozeni_cisto == \"ne\", na.rm = TRUE)`.",
        ],
        "check": ('v <- read.csv("lab_vzorky.csv", stringsAsFactors = FALSE)\n'
                  'cz <- dplyr::case_when(v$namnozeni %in% c("N/A", "") ~ NA_character_,\n'
                  '                       v$namnozeni == "NE" ~ "ne", TRUE ~ v$namnozeni)\n'
                  'if (!exists("vzorky") || !("namnozeni_cisto" %in% names(get("vzorky"))))\n'
                  '  return(.v_spam("Chybí sloupec `namnozeni_cisto`."))\n'
                  'a <- .v_num(get("pocet_ne"), sum(cz == "ne", na.rm = TRUE))\nif (!a$pass) return(a)\n'
                  'if (!is.factor(get("vzorky")$namnozeni_cisto)) return(.v_spam("A je to faktor? Použij `factor(...)`. "))\n'
                  'list(pass = TRUE, msg = "Čistá práce. „N/A“ v datech není totéž jako NA — R je vidí jako text.")'),
        "reseni": ('vzorky <- vzorky %>%\n'
                   '  mutate(namnozeni_cisto = factor(\n'
                   '    dplyr::case_when(namnozeni %in% c("N/A", "") ~ NA_character_,\n'
                   '                     namnozeni == "NE" ~ "ne",\n'
                   '                     TRUE ~ namnozeni),\n'
                   '    levels = c("ano", "ne")))\n'
                   'pocet_ne <- sum(vzorky$namnozeni_cisto == "ne", na.rm = TRUE)\n'),
    },
    {
        "id": "nac-05",
        "title": "Datum z českého formátu",
        "lesson": 4, "minutes": 4, "level": 3,
        "skills": ["datum", "cisteni", "format"],
        "dataset": "prodej_zbozi_ciste.csv",
        "nacti": 'prodej <- read.csv("prodej_zbozi_ciste.csv", stringsAsFactors = FALSE)',
        "zadani": ("Sloupec `datum_prodeje` je text „den.mesic.rok“. Převeď ho na datum\n"
                   "(vlastní `format`), přidej sloupec `mesic` (číslo měsíce) a ulož do `prodej`.\n"
                   "Do `nejvice_prodeju` dej číslo měsíce, kdy bylo prodejů nejvíc."),
        "starter": "prodej$datum <- as.Date(prodej$datum_prodeje, format = )\nprodej$mesic <-\nnejvice_prodeju <-\n",
        "hints": [
            "`format = \"%d.%m.%Y\"`",
            "`prodej$mesic <- as.integer(format(prodej$datum, \"%m\"))`, pak `which.max(table(prodej$mesic))`",
        ],
        "check": ('p <- read.csv("prodej_zbozi_ciste.csv", stringsAsFactors = FALSE)\n'
                  'd <- as.Date(p$datum_prodeje, format = "%d.%m.%Y")\n'
                  'sp <- as.integer(names(sort(-table(format(d, "%m"))))[1])\n'
                  'if (!inherits(get("prodej")$datum, "Date"))\n'
                  '  return(.v_spam("datum pořád není Datum — převeď ji přes as.Date s format = %d.%m.%Y"))\n'
                  '.v_num(get("nejvice_prodeju"), sp)'),
        "reseni": ('prodej$datum <- as.Date(prodej$datum_prodeje, format = "%d.%m.%Y")\n'
                   'prodej$mesic <- as.integer(format(prodej$datum, "%m"))\n'
                   'nejvice_prodeju <- which.max(table(prodej$mesic))\n'),
    },
    {
        "id": "nac-06",
        "title": "Duplicity a jak je najít",
        "lesson": 4, "minutes": 4, "level": 3,
        "skills": ["cisteni", "duplicity", "unique"],
        "dataset": "prodej_zbozi_ciste.csv",
        "nacti": 'prodej <- read.csv("prodej_zbozi_ciste.csv", stringsAsFactors = FALSE)',
        "zadani": ("Kód zboží se opakuje. Zjisti, kolik je různých kódů → `ruzne_kody`, a kolik\n"
                   "řádků zbytečně duplicuje ten nejčastější kód → `max_duplicita`."),
        "starter": "ruzne_kody <-\nmax_duplicita <-\n",
        "hints": [
            "`length(unique(prodej$kod))` nebo `n_distinct()`",
            "`max(table(prodej$kod))`",
        ],
        "check": ('p <- read.csv("prodej_zbozi_ciste.csv", stringsAsFactors = FALSE)\n'
                  'a <- .v_num(get("ruzne_kody"), length(unique(p$kod)))\nif (!a$pass) return(a)\n'
                  '.v_num(get("max_duplicita"), max(table(p$kod)))'),
        "reseni": ('ruzne_kody <- length(unique(prodej$kod))\nmax_duplicita <- max(table(prodej$kod))\n'),
    },
    {
        "id": "nac-07",
        "title": "Dva soubory, jeden pohled",
        "lesson": 4, "minutes": 5, "level": 4,
        "skills": ["nacitani", "rbind", "bind_rows"],
        "libraries": ["dplyr"],
        "dataset": "kavarna.csv",
        "nacti": 'kavarna <- read.csv("kavarna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Rozděl data na dva pohledy: `velka` (velkost `large`) a `mala` (velkost\n"
                   "'small'), pak je spoj zase k sobě (`bind_rows`) do `spojene` a ověř, že\n"
                   "`spojene` má součet řádků obou částí. Do `pocet_spojene` dej počet řádků `spojene`."),
        "starter": "library(dplyr)\nvelka <- kavarna %>% filter( )\nmala <- kavarna %>% filter( )\nspojene <- bind_rows( )\npocet_spojene <- nrow(spojene)\n",
        "hints": [
            "`filter(velkost == \"large\")`, pak `bind_rows(velka, mala)`",
            "`nrow(velka) + nrow(mala)` by se mělo rovnat `pocet_spojene`.",
        ],
        "check": ('k <- read.csv("kavarna.csv", stringsAsFactors = FALSE)\n'
                  'sp <- sum(k$velkost == "large") + sum(k$velkost == "small")\n'
                  '.v_num(get("pocet_spojene"), sp, msg_ok = "Jo. `bind_rows()` umí i odlišné sloupce — doplní NA.")'),
        "reseni": ('velka <- kavarna %>% filter(velkost == "large")\nmala <- kavarna %>% filter(velkost == "small")\n'
                   'spojene <- bind_rows(velka, mala)\npocet_spojene <- nrow(spojene)\n'),
    },
    {
        "id": "nac-08",
        "title": "Shrnutí na jeden řádek",
        "lesson": 4, "minutes": 3, "level": 2,
        "skills": ["kontrola", "summary", "sctr"],
        "dataset": "energie_byty.csv",
        "nacti": 'energie <- read.csv("energie_byty.csv", stringsAsFactors = FALSE)',
        "zadani": ("Pomocí `summary()` na `energie$kwh` zjisti medián → `median_kwh`\n"
                   "a rozdíl mezi maximem a minimem → `rozpeti_kwh`."),
        "starter": "s <- summary(energie$kwh)\nmedian_kwh <-\nrozpeti_kwh <-\n",
        "hints": [
            "`s[\"Median\"]` nebo `median(energie$kwh)`",
            "`max(energie$kwh, na.rm = TRUE) - min(energie$kwh, na.rm = TRUE)`",
        ],
        "check": ('e <- read.csv("energie_byty.csv", stringsAsFactors = FALSE)\n'
                  'a <- .v_num(get("median_kwh"), median(e$kwh))\nif (!a$pass) return(a)\n'
                  '.v_num(get("rozpeti_kwh"), max(e$kwh) - min(e$kwh))'),
        "reseni": ('s <- summary(energie$kwh)\nmedian_kwh <- as.numeric(s["Median"])\n'
                   'rozpeti_kwh <- max(energie$kwh) - min(energie$kwh)\n'),
    },
]
