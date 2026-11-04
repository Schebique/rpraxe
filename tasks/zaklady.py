"""Banka úloh — lekce 1-2 (základy, typy, vektory, matice, listy, faktory).

Formát záznamu:
  id, title, lesson, minutes, level (1-5), skills[], dataset, nacti,
  zadani, starter, hints[], check (R), reseni (R)
Pravidla pro `check`:
  - běží ve stejném prostředí jako studentský kód (má k dispozici jeho proměnné)
  - vrací TRUE / FALSE nebo list(pass = , msg = )
  - helpery: .v_num(got, want, tol, msg_ok), .v_txt(got, want, msg_ok),
             .v_spam(msg), .v_df(got, want, msg_ok)
"""

TASKS = [
    {
        "id": "zakl-01",
        "title": "Operátory a ukládání do proměnné",
        "lesson": 1, "minutes": 2, "level": 1,
        "skills": ["zaklady", "operatory", "promenne"],
        "zadani": ("Ulož do proměnné `pocet` číslo 27 a do proměnné `cena` číslo 129.5.\n"
                   "Pak spočítej celkovou částku `castka` = počet × cena a nech ji vypsat."),
        "starter": "pocet <-\ncena <-\n# spocitej castka a nech ji vypsat\n",
        "hints": [
            "K uložení se v R používá šipka `<-` bez mezer, tedy `pocet <- 27`.",
            "Násobení je `*`. Poslední řádek skriptu se vytiskne sám, jinak použij `print(castka)`.",
        ],
        "check": 'if (!exists("castka")) .v_spam("Nenašel jsem proměnnou `castka`.")\n.v_num(get("castka"), 27 * 129.5)',
        "reseni": "pocet <- 27\ncena <- 129.5\ncastka <- pocet * cena\ncastka\n",
    },
    {
        "id": "zakl-02",
        "title": "Jak to R vidí — class()",
        "lesson": 1, "minutes": 2, "level": 1,
        "skills": ["typy", "class"],
        "zadani": ("Zjisti, jak se R chová k výsledku `12L + 0.5` a k textu `\"R\"`.\n"
                   "Výsledky ulož jako text do `typ_vysledku` a `typ_textu`."),
        "starter": "typ_vysledku <-\ntyp_textu <-\n",
        "hints": [
            "`12L` je celé číslo (integer), `0.5` je double. Sečti je a zeptej se `class()`.",
            "Výsledek se porovnává jako text, stačí `class(12L + 0.5)`.",
        ],
        "check": ('if (!exists("typ_vysledku")) .v_spam("Chybí `typ_vysledku`.")\n'
                  'if (!exists("typ_textu")) .v_spam("Chybí `typ_textu`.")\n'
                  'a <- .v_txt(get("typ_vysledku"), "numeric")\nif (!a$pass) a else\n.v_txt(get("typ_textu"), "character")'),
        "reseni": 'typ_vysledku <- class(12L + 0.5)\ntyp_textu <- class("R")\n',
    },
    {
        "id": "zakl-03",
        "title": "Vektor lichých čísel",
        "lesson": 2, "minutes": 3, "level": 1,
        "skills": ["vektory", "seq", "length"],
        "zadani": ("Vytvoř vektor `lichych` se všemi lichými čísly od 1 do 49, ulož jeho\n"
                   "délku do `delka` a součet do `soucet`."),
        "starter": "lichych <-\ndelka <-\nsoucet <-\n",
        "hints": ["`seq(1, 49, by = 2)` dělá lichá čísla.", "Délka je `length()`, součet `sum()`."],
        "check": ('if (!exists("delka") || !exists("soucet")) .v_spam("Chybí `delka` nebo `soucet`.")\n'
                  'a <- .v_num(get("delka"), 25)\nif (!a$pass) a else\n.v_num(get("soucet"), sum(seq(1, 49, by = 2)))'),
        "reseni": "lichych <- seq(1, 49, by = 2)\ndelka <- length(lichych)\nsoucet <- sum(lichych)\n",
    },
    {
        "id": "zakl-04",
        "title": "rep() a c() kombinované",
        "lesson": 2, "minutes": 3, "level": 2,
        "skills": ["vektory", "rep", "c"],
        "zadani": ("Sestav vektor `rozvrh`, který má tři trojky, tři čtyřky, tři pětky\n"
                   "(každá hodina třikrát za sebou) a pak navíc hodnoty 9, 7, 5.\n"
                   "Průměr vektoru ulož do `prumer`."),
        "starter": "rozvrh <-\nprumer <-\n",
        "hints": [
            "Zkus `rep(3:5, each = 3)` — opakuje každou hodnotu zvlášť.",
            "`c()` kusy spojí dohromady; průměr je `mean()`.",
        ],
        "check": ('if (!exists("rozvrh")) .v_spam("Chybí vektor `rozvrh`.")\n'
                  'if (!isTRUE(all.equal(as.numeric(get("rozvrh")), as.numeric(c(rep(3:5, each = 3), 9, 7, 5)))))\n'
                  '  .v_spam("Ten vektor má jiný tvar. Pozor na `each` versus `times` a na pořadí hodnot.")\n'
                  '.v_num(get("prumer"), mean(c(rep(3:5, each = 3), 9, 7, 5)),\n'
                  '       msg_ok = "Přesně. `each` opakuje každou hodnotu zvlášť, `times` by opakovala celý vektor dokola.")'),
        "reseni": "rozvrh <- c(rep(3:5, each = 3), 9, 7, 5)\nprumer <- mean(rozvrh)\n",
    },
    {
        "id": "zakl-05",
        "title": "Matice ze dvou řádků",
        "lesson": 2, "minutes": 4, "level": 2,
        "skills": ["matice", "matrix", "dim"],
        "zadani": ("Vytvoř matici `m` ze dvou řádků: první čísla 15 až 20, druhý 37 až 42.\n"
                   "Použij `matrix()`, `ncol` a `byrow = TRUE`.\n"
                   "Rozměry ulož do `rozmery` jako text ve tvaru `2 x 6`."),
        "starter": "m <- matrix(, ncol = , byrow = TRUE)\nrozmery <-\n",
        "hints": [
            "`matrix(c(15:20, 37:42), ncol = 6, byrow = TRUE)`",
            "`dim(m)` vrací c(2, 6); na text se hodí `paste(dim(m)[1], \"x\", dim(m)[2])`.",
        ],
        "check": 'if (!exists("rozmery")) .v_spam("Chybí `rozmery`.")\n.v_txt(get("rozmery"), "2 x 6")',
        "reseni": 'm <- matrix(c(15:20, 37:42), ncol = 6, byrow = TRUE)\nrozmery <- paste(dim(m)[1], "x", dim(m)[2])\n',
    },
    {
        "id": "zakl-06",
        "title": "Data frame ručně z vektorů",
        "lesson": 2, "minutes": 4, "level": 2,
        "skills": ["data.frame", "cbind", "indexace"],
        "dataset": "skupina_deset.csv",
        "nacti": 'skupina <- read.csv("skupina_deset.csv", stringsAsFactors = FALSE)',
        "zadani": ("V tabulce `skupina` máš 10 lidí. Vytvoř data frame `dorost` jen se sloupci\n"
                   "`jmeno` a `vek` pro lidi mladší 15 let a do `pocet_dorostu` ulož, kolik jich je."),
        "starter": "dorost <-\npocet_dorostu <-\n",
        "hints": [
            "Filtr hranatou závorkou: `skupina$jmeno[skupina$vek < 15]`.",
            "Nový data frame složíš `data.frame(jmeno = ..., vek = ...)`, počet je `nrow(dorost)`.",
        ],
        "check": ('if (!exists("pocet_dorostu")) .v_spam("Chybí `pocet_dorostu`.")\n'
                  '.v_num(get("pocet_dorostu"), sum(read.csv("skupina_deset.csv")$vek < 15),\n'
                  '       msg_ok = "Ano. Porovnání `vek < 15` vrací logický vektor a ten funguje jako index.")'),
        "reseni": ("dorost <- data.frame(jmeno = skupina$jmeno[skupina$vek < 15],\n"
                   "                     vek = skupina$vek[skupina$vek < 15])\n"
                   "pocet_dorostu <- nrow(dorost)\n"),
    },
    {
        "id": "zakl-07",
        "title": "Faktory a jejich hladiny",
        "lesson": 2, "minutes": 3, "level": 2,
        "skills": ["faktory", "levels", "nlevels"],
        "dataset": "lab_vzorky.csv",
        "nacti": 'vzorky <- read.csv("lab_vzorky.csv", stringsAsFactors = TRUE)',
        "zadani": ("Sloupec `namnozeni` je malé peklo (\"ano\", \"ne\", \"NE\", \"N/A\").\n"
                   "Ulož počet hladin do `pocet_hladin` a hladiny do `hladiny` jako jeden text\n"
                   "oddělený čárkou a mezerou, tedy ve tvaru `A, B, C`."),
        "starter": "pocet_hladin <-\nhladiny <-\n",
        "hints": ["`nlevels()` a `levels()`.", "Spojení do jednoho textu: `paste(levels(...), collapse = \", \")`."],
        "check": ('if (!exists("hladiny")) .v_spam("Chybí `hladiny`.")\n'
                  'spravne <- levels(read.csv("lab_vzorky.csv", stringsAsFactors = TRUE)$namnozeni)\n'
                  'a <- .v_num(get("pocet_hladin"), length(spravne))\nif (!a$pass) a else\n'
                  '.v_txt(get("hladiny"), paste(spravne, collapse = ", "),\n'
                  '       msg_ok = "Přesně. „NE“ a „ne“ jsou pro R dvě různé hladiny — čistí se přes `factor(levels = )` nebo `dplyr::recode()`.")'),
        "reseni": ('pocet_hladin <- nlevels(vzorky$namnozeni)\nhladiny <- paste(levels(vzorky$namnozeni), collapse = ", ")\n'),
    },
    {
        "id": "zakl-08",
        "title": "List jako přihrádka na vše",
        "lesson": 2, "minutes": 4, "level": 3,
        "skills": ["list", "extrakce"],
        "zadani": ("Vytvoř list `pokus` se třemi položkami: `nakaz` (text \"octomilky\"),\n"
                   "`vysledky` (logický vektor TRUE TRUE FALSE TRUE) a `pocty` (12, 9, 15).\n"
                   "Do `pocet_uspechu` ulož, kolik pokusů vyšlo, do `prumer_poctu` průměr počtů."),
        "starter": "pokus <- list(nakaz = , vysledky = , pocty = )\npocet_uspechu <-\nprumer_poctu <-\n",
        "hints": [
            "`list(nakaz = \"octomilky\", vysledky = c(TRUE, TRUE, FALSE, TRUE), pocty = c(12, 9, 15))`",
            "`sum()` umí sečíst logický vektor (TRUE je 1); průměr je `mean()`.",
        ],
        "check": ('if (!exists("pocet_uspechu") || !exists("prumer_poctu")) .v_spam("Chybí jedna z výsledných proměnných.")\n'
                  'a <- .v_num(get("pocet_uspechu"), 3)\nif (!a$pass) a else\n'
                  '.v_num(get("prumer_poctu"), mean(c(12, 9, 15)))'),
        "reseni": ('pokus <- list(nakaz = "octomilky",\n'
                   '              vysledky = c(TRUE, TRUE, FALSE, TRUE),\n'
                   '              pocty = c(12, 9, 15))\n'
                   'pocet_uspechu <- sum(pokus$vysledky)\nprumer_poctu <- mean(pokus$pocty)\n'),
    },
    {
        "id": "zakl-09",
        "title": "Dvojrozměrná matice a indexy",
        "lesson": 2, "minutes": 3, "level": 3,
        "skills": ["matice", "indexace"],
        "zadani": ("Vytvoř matici `tab` ze sloupců `a = 1:4` a `b = 5:8` pomocím `cbind()`.\n"
                   "Do `druhy_sloupec` ulož celý druhý sloupec jako vektor\n"
                   "a do `soucin_diagonaly` součin prvků na diagonále (1 a 6)."),
        "starter": "a <- 1:4\nb <- 5:8\ntab <-\ndruhy_sloupec <-\nsoucin_diagonaly <-\n",
        "hints": [
            "`cbind(a, b)` skládá sloupce vedle sebe.",
            "Druhý sloupec je `tab[, 2]`, diagonála `diag(tab)`.",
        ],
        "check": ('if (!exists("soucin_diagonaly")) return(.v_spam("Chybí `soucin_diagonaly`."))\n'
                  'a1 <- .v_num(get("soucin_diagonaly"), prod(diag(cbind(1:4, 5:8))))\nif (!a1$pass) a1 else\n'
                  'if (!isTRUE(all.equal(as.numeric(get("druhy_sloupec")), 5:8))) .v_spam("`druhy_sloupec` není ten správný sloupec.")\n'
                  'list(pass = TRUE, msg = "Ber. Index matice je `[radek, sloupec]` — prázdné místo znamená „všechny“.")'),
        "reseni": ('a <- 1:4\nb <- 5:8\ntab <- cbind(a, b)\ndruhy_sloupec <- tab[, 2]\n'
                   'soucin_diagonaly <- prod(diag(tab))\n'),
    },
    {
        "id": "zakl-10",
        "title": "Vektorizace versus for smyčka",
        "lesson": 2, "minutes": 4, "level": 3,
        "skills": ["vektory", "vektorizace"],
        "dataset": "skupina_deset.csv",
        "nacti": 'skupina <- read.csv("skupina_deset.csv", stringsAsFactors = FALSE)',
        "zadani": ("Převeď výšky z `skupina$vyska_cm` na metry do nového sloupce\n"
                   "`skupina$vyska_m` — bez smyčky, jednou operací. Pak do\n"
                   "`nejVyssi_jmeno` ulož jméno nejvyššího člověka jako text."),
        "starter": 'skupina$vyska_cm <- as.numeric(skupina$vyska_cm)\nskupina$vyska_m <-\nnejVyssi_jmeno <-\n',
        "hints": [
            "Vektor vydělíš číslemwhole najednou: `skupina$vyska_cm / 100`.",
            "`which.max(skupina$vyska_cm)` vrátí pozici; tu vlož do `skupina$jmeno[...]`.",
        ],
        "check": ('sk <- read.csv("skupina_deset.csv", stringsAsFactors = FALSE)\n'
                  'if (!exists("skupina")) .v_spam("Chybí data frame `skupina`.")\n'
                  'a <- .v_num(max(as.numeric(get("skupina")$vyska_m)), max(as.numeric(sk$vyska_cm)) / 100)\n'
                  'if (!a$pass) a else\n'
                  '.v_txt(get("nejVyssi_jmeno"), sk$jmeno[which.max(sk$vyska_cm)])'),
        "reseni": ("skupina$vyska_m <- skupina$vyska_cm / 100\n"
                   "nejVyssi_jmeno <- skupina$jmeno[which.max(skupina$vyska_cm)]\n"),
    },
]
