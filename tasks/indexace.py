"""Lekce 3 — indexace (base R i dplyr), hodnoty versus struktury."""

TASKS = [
    {
        "id": "idx-01",
        "title": "Prvních pět, poslední tři",
        "lesson": 3, "minutes": 2, "level": 1,
        "skills": ["indexace", "vektory"],
        "zadani": ("Máš vektor `x <- c(15, 87, 23, 91, 42, 68, 54, 78, 54, 45, 10, 98, 54, 98)`.\n"
                   "Do `prvnich5` ulož prvních pět hodnot, do `posl3` poslední tři hodnoty.\n"
                   "Druhý dotaz zkus tak, aby to fungovalo i kdyby se délka vektoru změnila."),
        "starter": "x <- c(15, 87, 23, 91, 42, 68, 54, 78, 54, 45, 10, 98, 54, 98)\nprvnich5 <-\nposl3 <-\n",
        "hints": ["`x[1:5]`", "`x[(length(x) - 2):length(x)]` — nebo `tail(x, 3)`"],
        "check": ('if (!exists("prvnich5") || !exists("posl3")) .v_spam("Chybí `prvnich5` nebo `posl3`.")\n'
                  'x <- c(15, 87, 23, 91, 42, 68, 54, 78, 54, 45, 10, 98, 54, 98)\n'
                  'a <- .v_num(get("prvnich5"), x[1:5])\nif (!a$pass) return(a)\n'
                  '.v_num(get("posl3"), tail(x, 3), msg_ok = "Správně. `length(x)` dělá kód odolný vůči změně dat.")'),
        "reseni": "x <- c(15, 87, 23, 91, 42, 68, 54, 78, 54, 45, 10, 98, 54, 98)\nprvnich5 <- x[1:5]\nposl3 <- x[(length(x) - 2):length(x)]\n",
    },
    {
        "id": "idx-02",
        "title": "Jmenovaný vektor bez jedné položky",
        "lesson": 3, "minutes": 3, "level": 2,
        "skills": ["indexace", "jmenovane_vektory"],
        "zadani": ('Měj jmenovaný vektor\n'
                   '`v <- c(zemepis = "CZ", region = "Ostravsko", mesto = "Havirov", pocet = 12)`.\n'
                   "1) Vrať celý vektor kromě položky `region` → výsledek nechat vypsat.\n"
                   "2) Proč nejde `v[-\"region\"]`? Napiš krátkou odpověď, klíčové slovo je `indexace`."),
        "starter": 'v <- c(zemepis = "CZ", region = "Ostravsko", mesto = "Havirov", pocet = 12)\n'
                   'bez_regionu <-\nproc <-\n',
        "hints": [
            "`v[names(v) != \"region\"]`",
            "Záporná indexace pracuje s pozicemi (čísly), jméno pozici není.",
        ],
        "check": ('v <- c(zemepis = "CZ", region = "Ostravsko", mesto = "Havirov", pocet = 12)\n'
                  'a <- .v_txt(paste(names(get("bez_regionu")), collapse = ","),\n'
                  '              paste(names(v[names(v) != "region"]), collapse = ","))\n'
                  'if (!a$pass) return(a)\n'
                  'p <- tolower(paste(as.character(unlist(get("proc"))), collapse = " "))\n'
                  'if (!grepl("indexac", p)) return(.v_spam("V vysvetleni hledam slovo `indexace` — záporná indexace bere pozice, ne jména."))\n'
                  'list(pass = TRUE, msg = "Jo — `-` bere pozice. Přes jméno filtruješ přes `names(v) != ...`.")'),
        "reseni": ('v <- c(zemepis = "CZ", region = "Ostravsko", mesto = "Havirov", pocet = 12)\n'
                   'bez_regionu <- v[names(v) != "region"]\n'
                   'proc <- "zaporna indexace funguje jen pro ciselne pozice, ne pro jmena"\n'),
    },
    {
        "id": "idx-03",
        "title": "data frame versus vektor — trojí indexace",
        "lesson": 3, "minutes": 3, "level": 2,
        "skills": ["indexace", "data.frame"],
        "dataset": "skupina_deset.csv",
        "nacti": 'skupina <- read.csv("skupina_deset.csv", stringsAsFactors = FALSE)',
        "zadani": ("Odpověz jedním číslem na tři otázky:\n"
                   "1) `n1` = kolik prvků má `skupina[, 1]`\n"
                   "2) `n2` = kolik prvků má `skupina[[1]]`\n"
                   "3) `n3` = kolik řádků má `skupina[1]`"),
        "starter": "n1 <-\nn2 <-\nn3 <-\n",
        "hints": [
            "`df[, 1]` i `df[[1]]` zjednoduší na vektor → `length()`.",
            "`df[1]` zůstává data frame → `nrow()`.",
        ],
        "check": ('sk <- read.csv("skupina_deset.csv", stringsAsFactors = FALSE)\n'
                  'a <- .v_num(get("n1"), length(sk[, 1]))\nif (!a$pass) return(a)\n'
                  'b <- .v_num(get("n2"), length(sk[[1]]))\nif (!b$pass) return(b)\n'
                  'c <- .v_num(get("n3"), nrow(sk[1]))\nif (!c$pass) return(c)\n'
                  'list(pass = TRUE, msg = "Přesně. `[,1]` a `[[1]]` zjednoduší na vektor, `[1]` tabulku zachová.")'),
        "reseni": "n1 <- length(skupina[, 1])\nn2 <- length(skupina[[1]])\nn3 <- nrow(skupina[1])\n",
    },
    {
        "id": "idx-04",
        "title": "První a poslední řádek současně",
        "lesson": 3, "minutes": 3, "level": 2,
        "skills": ["indexace", "data.frame"],
        "dataset": "kavarna.csv",
        "nacti": 'kavarna <- read.csv("kavarna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Vrať první a poslední řádek tabulky `kavarna` jako dvourojkový data frame `okraje`\n"
                   "a do `sloupce` ulož, kolik sloupců má."),
        "starter": "okraje <-\nsloupce <-\n",
        "hints": ["`kavarna[c(1, nrow(kavarna)), ]` — nezapomeň na čárku za závorkou.", "Počet sloupců je `ncol(okraje)`."]
        ,
        "check": ('k <- read.csv("kavarna.csv", stringsAsFactors = FALSE)\n'
                  'a <- .v_num(get("sloupce"), ncol(k))\nif (!a$pass) return(a)\n'
                  'if (!isTRUE(nrow(get("okraje")) == 2)) return(.v_spam("`okraje` by mel mit 2 radky."))\n'
                  'list(pass = TRUE, msg = "Ano. Čárka za `c(1, nrow(...))` je důležitá — bez ní bys vybíral sloupce.")'),
        "reseni": "okraje <- kavarna[c(1, nrow(kavarna)), ]\nsloupce <- ncol(okraje)\n",
    },
    {
        "id": "idx-05",
        "title": "Průměr vzdálenosti na kole",
        "lesson": 3, "minutes": 4, "level": 2,
        "skills": ["indexace", "logika", "agregace"],
        "dataset": "dojizdka.csv",
        "nacti": 'dojizdka <- read.csv("dojizdka.csv", stringsAsFactors = FALSE)',
        "zadani": ("Zjisti průměrnou vzdálenost (`vzdalenost_km`) dojížděk, kde je `doprava == \"kolo\"`.\n"
                   "Výsledek zaokrouhlený na 2 desetinná místa ulož do `prumer_kolo`.\n"
                   "Base R styl: `$` a hranaté závorky."),
        "starter": "prumer_kolo <-\n",
        "hints": [
            "`dojizdka$vzdalenost_km[dojizdka$doprava == \"kolo\"]` vybere jen cyklisty.",
            "`round(mean(..., na.rm = TRUE), 2)`",
        ],
        "check": ('k <- read.csv("dojizdka.csv", stringsAsFactors = FALSE)\n'
                  'sp <- round(mean(k$vzdalenost_km[k$doprava == "kolo"], na.rm = TRUE), 2)\n'
                  '.v_num(get("prumer_kolo"), sp, msg_ok = "Přesně — a bez `na.rm = TRUE` by vyšlo NA.")'),
        "reseni": 'prumer_kolo <- round(mean(dojizdka$vzdalenost_km[dojizdka$doprava == "kolo"], na.rm = TRUE), 2)\n',
    },
    {
        "id": "idx-06",
        "title": "which() versus logicky vektor",
        "lesson": 3, "minutes": 4, "level": 3,
        "skills": ["indexace", "which", "logika"],
        "dataset": "skolni_zahrada.csv",
        "nacti": 'zahrada <- read.csv("skolni_zahrada.csv", stringsAsFactors = FALSE)',
        "zadani": ("Najdi pozice (čísla řádků) rostlin, které mají `osetreni == \"kompost\"`\n"
                   "A SOUČASNĚ `slunecni_hodiny > 6`. Pozice ulož do `pozice`, jejich počet do `pocet`."),
        "starter": "pozice <-\npocet <-\n",
        "hints": [
            "`which(zahrada$osetreni == \"kompost\" & zahrada$slunecni_hodiny > 6)`",
            "Počet je `length(pozice)`.",
        ],
        "check": ('z <- read.csv("skolni_zahrada.csv", stringsAsFactors = FALSE)\n'
                  'sp <- which(z$osetreni == "kompost" & z$slunecni_hodiny > 6)\n'
                  'a <- .v_num(get("pocet"), length(sp))\nif (!a$pass) return(a)\n'
                  'if (!isTRUE(all.equal(as.integer(get("pozice")), as.integer(sp))))\n'
                  '  return(.v_spam("Cisla radku nesedi — pouzivas `&`, ne `&&`?"))\n'
                  'list(pass = TRUE, msg = "Správně. `which()` vrací pozice, logický vektor TRUE/FALSE se hodí zas jinam.")'),
        "reseni": 'pozice <- which(zahrada$osetreni == "kompost" & zahrada$slunecni_hodiny > 6)\npocet <- length(pozice)\n',
    },
    {
        "id": "idx-07",
        "title": "Stejná úloha po dplyr",
        "lesson": 3, "minutes": 4, "level": 2,
        "skills": ["dplyr", "filter", "mutate"],
        "libraries": ["dplyr"],
        "dataset": "mzdy.csv",
        "nacti": 'mzdy <- read.csv("mzdy.csv", stringsAsFactors = FALSE)',
        "zadani": ("Přepiš to do `dplyr`: vyber lidi s `obor == \"skolstvi\"`, nech sloupce\n"
                   "`id`, `vzdelani`, `plat_kc` a přidej logický sloupec `vysoka_plat`\n"
                   "(TRUE když je `plat_kc` vyšší než 45000). Výsledek ulož do `vyber`."),
        "starter": "library(dplyr)\nvyber <- mzdy %>%\n\n",
        "hints": [
            "`filter(obor == \"skolstvi\") %>% select(id, vzdelani, plat_kc) %>% mutate(vysoka_plat = plat_kc > 45000)`",
            "`mutate()` musí být až po `select()`, pokud v něm počítáš s `plat_kc`.",
        ],
        "check": ('library(dplyr)\nm <- read.csv("mzdy.csv", stringsAsFactors = FALSE)\n'
                  'sp <- m %>% filter(obor == "skolstvi") %>% select(id, vzdelani, plat_kc) %>%\n'
                  '  mutate(vysoka_plat = plat_kc > 45000)\n'
                  '.v_df(get("vyber"), sp, msg_ok = "Pěkný řetězec. `mutate()` přidává sloupec, `select()` vybírá.")'),
        "reseni": ('vyber <- mzdy %>%\n  filter(obor == "skolstvi") %>%\n  select(id, vzdelani, plat_kc) %>%\n'
                   '  mutate(vysoka_plat = plat_kc > 45000)\n'),
    },
    {
        "id": "idx-08",
        "title": "NEBO a negace",
        "lesson": 3, "minutes": 4, "level": 3,
        "skills": ["indexace", "logika", "negace"],
        "dataset": "knihovna.csv",
        "nacti": 'knihovna <- read.csv("knihovna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Kolik výpůjček je ve stavu `pozde` NEBO mají `dny_pujcky` více než 45?\n"
                   "→ `pozde_nebo_dlouhe`. A kolik výpůjček NENÍ ve stavu `vraceno` → `nevracene`."),
        "starter": "pozde_nebo_dlouhe <-\nnevracene <-\n",
        "hints": [
            "`sum(knihovna$stav == \"pozde\" | knihovna$dny_pujcky > 45, na.rm = TRUE)`",
            "Druhá otázka: `sum(knihovna$stav != \"vraceno\")`.",
        ],
        "check": ('k <- read.csv("knihovna.csv", stringsAsFactors = FALSE)\n'
                  'a <- .v_num(get("pozde_nebo_dlouhe"), sum(k$stav == "pozde" | k$dny_pujcky > 45, na.rm = TRUE))\n'
                  'if (!a$pass) return(a)\n'
                  '.v_num(get("nevracene"), sum(k$stav != "vraceno", na.rm = TRUE))'),
        "reseni": ('pozde_nebo_dlouhe <- sum(knihovna$stav == "pozde" | knihovna$dny_pujcky > 45, na.rm = TRUE)\n'
                   'nevracene <- sum(knihovna$stav != "vraceno", na.rm = TRUE)\n'),
    },
    {
        "id": "idx-09",
        "title": "Podmnožina podle jména sloupce",
        "lesson": 3, "minutes": 3, "level": 3,
        "skills": ["indexace", "data.frame"],
        "dataset": "energie_byty.csv",
        "nacti": 'energie <- read.csv("energie_byty.csv", stringsAsFactors = FALSE)',
        "zadani": ("Vrať jen byty `byt_03` a `byt_05` a jen sloupce `mesic`, `kwh`, `cena_kwh`.\n"
                   "Ulož do `cast` a do `soucet_kwh` dej součet `kwh` v této množině."),
        "starter": "cast <-\nsoucet_kwh <-\n",
        "hints": [
            "`energie[energie$byt %in% c(\"byt_03\", \"byt_05\"), c(\"mesic\", \"kwh\", \"cena_kwh\")]`",
            "Součet: `sum(cast$kwh)`",
        ],
        "check": ('e <- read.csv("energie_byty.csv", stringsAsFactors = FALSE)\n'
                  'sp <- e[e$byt %in% c("byt_03", "byt_05"), c("mesic", "kwh", "cena_kwh")]\n'
                  'a <- .v_num(get("soucet_kwh"), sum(sp$kwh))\nif (!a$pass) return(a)\n'
                  '.v_df(get("cast"), sp)'),
        "reseni": ('cast <- energie[energie$byt %in% c("byt_03", "byt_05"), c("mesic", "kwh", "cena_kwh")]\n'
                   'soucet_kwh <- sum(cast$kwh)\n'),
    },
]
