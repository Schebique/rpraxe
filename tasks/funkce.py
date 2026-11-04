"""Lekce 5 — vlastni funkce, cykly, rodina apply, vektorizace, datum a cas."""

TASKS = [
    {
        "id": "fce-01",
        "title": "Prvni vlastni funkce",
        "lesson": 5, "minutes": 4, "level": 2,
        "skills": ["funkce", "zaklady"],
        "zadani": ("Napiš funkci `bmi`, která dostane výšku v cm a hmotnost v kg a vrátí BMI\n"
                   "(kg / m², tedy výšku převeď na metry). Ověř ji: `moje_bmi <- bmi(170, 68)`."),
        "starter": "bmi <- function(vyska_cm, hmotnost_kg) {\n\n}\nmoje_bmi <- bmi(170, 68)\n",
        "hints": [
            "`vyska_m <- vyska_cm / 100`, pak `hmotnost_kg / vyska_m^2`",
            "Funkce vrací poslední vyčíslený výraz, `return()` být nemusí.",
        ],
        "check": ('if (!exists("bmi") || !is.function(get("bmi"))) .v_spam("Nenašel jsem funkci `bmi`.")\n'
                  'f <- get("bmi")\n'
                  'sp_ok <- isTRUE(all.equal(round(f(170, 68), 2), round(68 / 1.7^2, 2), tolerance = 1e-2))\n'
                  'if (!sp_ok) return(.v_spam("Funkce vrací jinou hodnotu. Zkus `68 / (170/100)^2` porovnat s výsledkem."))\n'
                  '.v_num(get("moje_bmi"), 68 / 1.7^2, tol = 1e-2)'),
        "reseni": ("bmi <- function(vyska_cm, hmotnost_kg) {\n"
                   "  vyska_m <- vyska_cm / 100\n"
                   "  hmotnost_kg / vyska_m^2\n}\nmoje_bmi <- bmi(170, 68)\n"),
    },
    {
        "id": "fce-02",
        "title": "Funkce s vychozim parametrem",
        "lesson": 5, "minutes": 4, "level": 3,
        "skills": ["funkce", "argumenty"],
        "zadani": ("Napiš funkci `prumer(x, na.rm = TRUE)`, která spočítá průměr a umí ho počítat\n"
                   "i s NA. Ověř: `s_na <- prumer(c(4, 8, NA, 10))` a `bez_na <- prumer(c(4, 8, NA, 10), na.rm = FALSE)`."),
        "starter": "prumer <- function(x, na.rm = TRUE) {\n\n}\n",
        "hints": [
            "`mean(x, na.rm = na.rm)`",
            "S `na.rm = FALSE` má vyjít NA — to je správně.",
        ],
        "check": ('if (!exists("prumer") || !is.function(get("prumer")))\n'
                  '  return(.v_spam("Chybi funkce `prumer` — napiš ji celou."))\n'
                  'a <- .v_num(get("s_na"), mean(c(4, 8, NA, 10), na.rm = TRUE), tol = 1e-6)\nif (!a$pass) return(a)\n'
                  'if (!isTRUE(is.na(get("bez_na")))) return(.v_spam("`bez_na` ma byt NA — ten parametr se nesmi zahodit."))\n'
                  'list(pass = TRUE, msg = "Správně. Vychozí hodnota argumentu je to, čeho si v kurzu všímají.")'),
        "reseni": ('prumer <- function(x, na.rm = TRUE) mean(x, na.rm = na.rm)\n'
                   's_na <- prumer(c(4, 8, NA, 10))\nbez_na <- prumer(c(4, 8, NA, 10), na.rm = FALSE)\n'),
    },
    {
        "id": "fce-03",
        "title": "for smycka bez vektorizace",
        "lesson": 5, "minutes": 5, "level": 3,
        "skills": ["cykly", "for", "vektorizace"],
        "zadani": ("Bez `for` smyčky to nejde: měj vektor `teploty <- c(18.2, 21.9, 17.4, 25.1, 19.8)`.\n"
                   "Projdí ho smyčkou a ulož si do `flagy` logický vektor, kde TRUE znamená\n"
                   "teplotu nad 20 °C. (Účel: uvědomit si, co dělá smyčka, než to vezmeš vektorově.)"),
        "starter": "teploty <- c(18.2, 21.9, 17.4, 25.1, 19.8)\nflagy <- logical(length(teploty))\nfor (i in seq_along(teploty)) {\n\n}\nflagy\n",
        "hints": [
            "`flagy[i] <- teploty[i] > 20`",
            "`seq_along()` je v R preferito `1:length()`, když může být vektor prázdný.",
        ],
        "check": ('sp <- c(18.2, 21.9, 17.4, 25.1, 19.8) > 20\n'
                  'g <- get("flagy")\nif (is.null(g)) .v_spam("Chybi vektor `flagy`.")\n'
                  'if (!identical(as.logical(g), sp)) return(.v_spam("Nektera polozka je jina — porovnej krok po kroku."))\n'
                  'list(pass = TRUE, msg = "Tak přesně tohle dělá `teploty > 20` najednou. Až na to příště zapomeneš, vzpomeň si na tuhle smyčku.")'),
        "reseni": ('teploty <- c(18.2, 21.9, 17.4, 25.1, 19.8)\n'
                   'flagy <- logical(length(teploty))\n'
                   'for (i in seq_along(teploty)) flagy[i] <- teploty[i] > 20\n'),
    },
    {
        "id": "fce-04",
        "title": "sapply pres sloupce",
        "lesson": 5, "minutes": 5, "level": 3,
        "skills": ["apply", "sapply", "data.frame"],
        "dataset": "mzdy.csv",
        "nacti": 'mzdy <- read.csv("mzdy.csv", stringsAsFactors = FALSE)',
        "zadani": ("Pomocí `sapply` spočítej průměr každého číselného sloupce tabulky `mzdy`.\n"
                   "Výsledný pojmenovaný vektor ulož do `prumery` (použij `na.rm = TRUE`)."),
        "starter": "ciselné <- mzdy[, sapply(mzdy, is.numeric)]\nprumery <- sapply( )\n",
        "hints": [
            "`sapply(ciselne, mean, na.rm = TRUE)`",
            "Extra: `mzdy[, vapply(mzdy, is.numeric, logical(1))]` je bezpečnější.",
        ],
        "check": ('m <- read.csv("mzdy.csv", stringsAsFactors = FALSE)\n'
                  'sp <- sapply(m[, vapply(m, is.numeric, logical(1))], mean, na.rm = TRUE)\n'
                  'g <- get("prumery")\nif (is.null(g)) return(.v_spam("Chybi `prumery`."))\n'
                  'sp <- sp[names(sp) %in% names(g)]\n'
                  '.v_num(as.numeric(g[names(sp)]), as.numeric(sp), tol = 1e-3,\n'
                  '       msg_ok = "Jo, a všimni si pojmenovaných výsledků — to `sapply()` dává zadarmo.")'),
        "reseni": ('ciselne <- mzdy[, vapply(mzdy, is.numeric, logical(1))]\n'
                   'prumery <- sapply(ciselne, mean, na.rm = TRUE)\n'),
    },
    {
        "id": "fce-05",
        "title": "tapply — dplyr bez dplyr",
        "lesson": 5, "minutes": 5, "level": 4,
        "skills": ["apply", "tapply", "agregace"],
        "dataset": "skolni_zahrada.csv",
        "nacti": 'zahrada <- read.csv("skolni_zahrada.csv", stringsAsFactors = TRUE)',
        "zadani": ("Pomocí `tapply` spočítej průměrnou `vyska_cm` podle `osetreni`.\n"
                   "Výsledek do `prumery_osetreni` a do `nejlepsi_osetreni` napiš ošetření s nejvyšším průměrem."),
        "starter": "prumery_osetreni <- tapply( )\nnejlepsi_osetreni <-\n",
        "hints": [
            "`tapply(zahrada$vyska_cm, zahrada$osetreni, mean, na.rm = TRUE)`",
            "`names(which.max(prumery_osetreni))`",
        ],
        "check": ('z <- read.csv("skolni_zahrada.csv", stringsAsFactors = TRUE)\n'
                  'sp <- tapply(z$vyska_cm, z$osetreni, mean, na.rm = TRUE)\n'
                  'a <- .v_txt(get("nejlepsi_osetreni"), names(which.max(sp)))\nif (!a$pass) return(a)\n'
                  '.v_num(as.numeric(get("prumery_osetreni")), as.numeric(sp), tol = 1e-3)'),
        "reseni": ('prumery_osetreni <- tapply(zahrada$vyska_cm, zahrada$osetreni, mean, na.rm = TRUE)\n'
                   'nejlepsi_osetreni <- names(which.max(prumery_osetreni))\n'),
    },
    {
        "id": "fce-06",
        "title": "ifelse a nova promenna",
        "lesson": 5, "minutes": 4, "level": 2,
        "skills": ["ifelse", "logika", "faktory"],
        "dataset": "skupina_deset.csv",
        "nacti": 'skupina <- read.csv("skupina_deset.csv", stringsAsFactors = FALSE)',
        "zadani": ("Přidej do `skupina` sloupec `skupina_vekova` s hodnotami „deti“ (vek < 15),\n"
                   "„dospeli“ (15–64) a „seniori“ (65+). Pomocí `ifelse()`. Ulož počet dětí do `pocet_deti`."),
        "starter": 'skupina$skupina_vekova <- ifelse(skupina$vek < 15, "deti",\n                        ifelse(, , ))\npocet_deti <-\n',
        "hints": [
            "`ifelse(vek < 15, \"deti\", ifelse(vek <= 64, \"dospeli\", \"seniori\"))`",
            "`sum(skupina$skupina_vekova == \"deti\")`",
        ],
        "check": ('s <- read.csv("skupina_deset.csv", stringsAsFactors = FALSE)\n'
                  'sp <- ifelse(s$vek < 15, "deti", ifelse(s$vek <= 64, "dospeli", "seniori"))\n'
                  'g <- get("skupina")\nif (is.null(g) || !("skupina_vekova" %in% names(g))) return(.v_spam("Chybi sloupec `skupina_vekova`."))\n'
                  'if (!identical(as.character(g$skupina_vekova), sp)) return(.v_spam("Rozdeleni neni uplne spravne — kam spadla hraniční hodnota 64 a 65?"))\n'
                  '.v_num(get("pocet_deti"), sum(sp == "deti"))'),
        "reseni": ('skupina$skupina_vekova <- ifelse(skupina$vek < 15, "deti",\n'
                   '                             ifelse(skupina$vek <= 64, "dospeli", "seniori"))\n'
                   'pocet_deti <- sum(skupina$skupina_vekova == "deti")\n'),
    },
    {
        "id": "fce-07",
        "title": "Datum: kolik je dni",
        "lesson": 5, "minutes": 4, "level": 3,
        "skills": ["datum", "as.Date", "format"],
        "dataset": "knihovna.csv",
        "nacti": 'knihovna <- read.csv("knihovna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Převeď `vypujcka` a `vraceni` na Datum, spočítej `dny` = rozdíl a porovnej ho\n"
                   "s existujícím `dny_pujcky`. Do `opravene_miry` dej součet správných délek a do\n"
                   "`nejdelsi_vypujcka` maximální délku."),
        "starter": "knihovna$vypujcka <- as.Date(knihovna$vypujcka)\nknihovna$vraceni <- as.Date(knihovna$vraceni)\nknihovna$dny <-\nopravene_miry <-\nnejdelsi_vypujcka <-\n",
        "hints": [
            "`as.integer(knihovna$vraceni - knihovna$vypujcka)`",
            "`sum(knihovna$dny, na.rm = TRUE)`",
        ],
        "check": ('k <- read.csv("knihovna.csv", stringsAsFactors = FALSE)\n'
                  'd <- as.integer(as.Date(k$vraceni) - as.Date(k$vypujcka))\n'
                  'a <- .v_num(get("opravene_miry"), sum(d, na.rm = TRUE))\nif (!a$pass) return(a)\n'
                  '.v_num(get("nejdelsi_vypujcka"), max(d, na.rm = TRUE))'),
        "reseni": ('knihovna$vypujcka <- as.Date(knihovna$vypujcka)\nknihovna$vraceni <- as.Date(knihovna$vraceni)\n'
                   'knihovna$dny <- as.integer(knihovna$vraceni - knihovna$vypujcka)\n'
                   'opravene_miry <- sum(knihovna$dny, na.rm = TRUE)\n'
                   'nejdelsi_vypujcka <- max(knihovna$dny, na.rm = TRUE)\n'),
    },
    {
        "id": "fce-08",
        "title": "Vektorizace versus smycka — srovnani",
        "lesson": 5, "minutes": 6, "level": 4,
        "skills": ["vektorizace", "cykly", "performance"],
        "dataset": "teplota_praha.csv",
        "nacti": 'teplota <- read.csv("teplota_praha.csv", stringsAsFactors = FALSE)',
        "zadani": ("Ulož do `teploty_over_20` počet dní s `teplot_prum > 20` **pomocí smyčky**\n"
                   "a do `vektorove_over_20` stejný výsledek **vektorově**. Obojí se musí rovnat."),
        "starter": 'teplota$teplot_prum <- as.numeric(teplota$teplot_prum)\nsmycka <- 0\nfor (t in teplota$teplot_prum) {\n\n}\nteploty_over_20 <-\nvektorove_over_20 <-\n',
        "hints": [
            "`if (t > 20) Smycka <- smycka + 1`",
            "Vektorově: `sum(teplota$teplot_prum > 20, na.rm = TRUE)`",
        ],
        "check": ('t <- read.csv("teplota_praha.csv", stringsAsFactors = FALSE)$teplot_prum\n'
                  'sp <- sum(t > 20, na.rm = TRUE)\n'
                  'a <- .v_num(get("teploty_over_20"), sp)\nif (!a$pass) return(a)\n'
                  'b <- .v_num(get("vektorove_over_20"), sp)\nif (!b$pass) return(b)\n'
                  'list(pass = TRUE, msg = "Stejné číslo, dva způsoby. Vektorové je kratší, rychlejší a meno chyb.")'),
        "reseni": ('smycka <- 0\nfor (t in teplota$teplot_prum) if (t > 20) smycka <- smycka + 1\n'
                   'teploty_over_20 <- smycka\n'
                   'vektorove_over_20 <- sum(teplota$teplot_prum > 20, na.rm = TRUE)\n'),
    },
    {
        "id": "fce-09",
        "title": "while a smycka s ukoncenim",
        "lesson": 5, "minutes": 4, "level": 3,
        "skills": ["cykly", "while", "break"],
        "zadani": ("Do investice 50 000 Kč každý měsíc připočti 8 % ročně (tedy `urok <- 0.08/12`) a ptej se,\n"
                   "za kolik měsíců částka přesáhne 70 000 Kč. Výsledej do `pocet_mesicu`."),
        "starter": "castka <- 50000\nmesic <- 0\nwhile ( ) {\n\n}\npocet_mesicu <- mesic\n",
        "hints": [
            "`while (castka <= 70000) { castka <- castka * (1 + 0.08/12); mesic <- mesic + 1 }`",
            "Ošetři si, že se smyčka zastaví — jinak tě runner umrtví po 30 sekundách.",
        ],
        "check": ('c <- 50000; m <- 0\nwhile (c <= 70000) { c <- c * (1 + 0.08 / 12); m <- m + 1 }\n'
                  '.v_num(get("pocet_mesicu"), m, msg_ok = "Ano, takhle to roste. Vyplatí se zkusit si to nakreslit `plot()`.")'),
        "reseni": ('castka <- 50000\nmesic <- 0\nwhile (castka <= 70000) {\n'
                   '  castka <- castka * (1 + 0.08 / 12)\n  mesic <- mesic + 1\n}\npocet_mesicu <- mesic\n'),
    },
    {
        "id": "fce-10",
        "title": " Rodina apply: rowMeans a company",
        "lesson": 5, "minutes": 5, "level": 4,
        "skills": ["apply", "rowMeans", "matice"],
        "dataset": "lab_vzorky.csv",
        "nacti": 'vzorky <- read.csv("lab_vzorky.csv", stringsAsFactors = FALSE)',
        "zadani": ("Vytvoř matici `mat` ze sloupců `koncentrace` a `signl` a přidej do `vzorky`\n"
                   "sloupec `prumer_2` = průměr z těch dvou sloupců (pomocí `rowMeans()`).\n"
                   "Pozor, `signl` je v jiných řádech — proto je průměr jen cvičení, ne medicína."),
        "starter": "mat <- as.matrix(vzorky[, c(\"koncentrace\", \"signl\")])\nvzorky$prumer_2 <-\ndim(mat)\n",
        "hints": [
            "`rowMeans(mat, na.rm = TRUE)`",
            "`apply(mat, 1, mean, na.rm = TRUE)` je to samé, jen pomalejší.",
        ],
        "check": ('v <- read.csv("lab_vzorky.csv", stringsAsFactors = FALSE)\n'
                  'sp <- rowMeans(as.matrix(v[, c("koncentrace", "signl")]), na.rm = TRUE)\n'
                  'g <- get("vzorky")\nif (is.null(g) || !("prumer_2" %in% names(g))) return(.v_spam("Chybi sloupec `prumer_2`."))\n'
                  '.v_num(head(as.numeric(g$prumer_2)), head(sp), tol = 1e-2)'),
        "reseni": ('mat <- as.matrix(vzorky[, c("koncentrace", "signl")])\n'
                   'vzorky$prumer_2 <- rowMeans(mat, na.rm = TRUE)\ndim(mat)\n'),
    },
]
