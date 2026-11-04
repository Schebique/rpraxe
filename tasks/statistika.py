"""Lekce 9-11 — typy dat, deskriptiva, testy, korelace, regrese (dopredu)."""

TASKS = [
    {
        "id": "stat-01",
        "title": "Poloha a variabilita",
        "lesson": 9, "minutes": 4, "level": 3,
        "skills": ["statistika", "deskriptiva", "sd"],
        "dataset": "mzdy.csv",
        "nacti": 'mzdy <- read.csv("mzdy.csv", stringsAsFactors = FALSE)',
        "zadani": ("U platů (`plat_kc`) spočti průměr, medián, směrodatnou odchylku a IQR\n"
                   "(vše `na.rm = TRUE`). Do `zpaty_prumerny` dej o kolik je průměr větší než medián."),
        "starter": "prumer <-\nmedian <-\nsd <-\niqr <-\nzpaty_prumerny <-\n",
        "hints": [
            "`mean(mzdy$plat_kc, na.rm = TRUE)`, `median(...)`, `sd(...)`, `IQR(...)`",
            "`zpaty_prumerny <- prumer - median`",
        ],
        "check": ('m <- na.omit(read.csv("mzdy.csv", stringsAsFactors = FALSE)$plat_kc)\n'
                  'a <- .v_num(get("prumer"), mean(m))\nif (!a$pass) return(a)\n'
                  'b <- .v_num(get("median"), median(m))\nif (!b$pass) return(b)\n'
                  'c <- .v_num(get("zpaty_prumerny"), mean(m) - median(m), tol = 1e-2)\nif (!c$pass) return(c)\n'
                  '.v_num(get("sd"), sd(m), tol = 1e-2)'),
        "reseni": ('prumer <- mean(mzdy$plat_kc, na.rm = TRUE)\nmedian <- median(mzdy$plat_kc, na.rm = TRUE)\n'
                   'sd <- sd(mzdy$plat_kc, na.rm = TRUE)\niqr <- IQR(mzdy$plat_kc, na.rm = TRUE)\n'
                   'zpaty_prumerny <- prumer - median\n'),
    },
    {
        "id": "stat-02",
        "title": "Jaky to je typ dat",
        "lesson": 9, "minutes": 4, "level": 3,
        "skills": ["typy_dat", "skala"],
        "dataset": "skolni_zahrada.csv",
        "nacti": 'zahrada <- read.csv("skolni_zahrada.csv", stringsAsFactors = TRUE)',
        "zadani": ("Prirad k promennym spravnou skalu. Odpovez jako text ve tvaru\n"
                   "`osetreni=<nominalni|ordinalni>,blok=<...>,puda_ph=<nominalni|ordinalni|intervalova|pomerova>,vyska_cm=<...>`."),
        "starter": 'odpoved <- "osetreni=,blok=,puda_ph=,vyska_cm="\n',
        "hints": [
            "ošetření = kategorie bez pořadí; blok = kategorie (také bez pořadí, ale ordinální se dá obhájit — bereme nominalní)",
            "pH je intervalová, výška v cm je poměrová (má smysluplnou nulu).",
        ],
        "check": ('g <- tolower(gsub(" ", "", paste(as.character(unlist(get("odpoved"))), collapse = "")))\n'
                  'if (is.null(g) || g == "") return(.v_spam("Chybi `odpoved`."))\n'
                  'sp <- c(osetreni = "nominalni", blok = "nominalni", puda_ph = "intervalova", vyska_cm = "pomerova")\n'
                  'for (k in names(sp)) {\n'
                  '  got <- sub(paste0(".*", k, "=([^,]*).*"), "\\\\1", g)\n'
                  '  if (!identical(got, sp[[k]]))\n'
                  '    return(.v_spam(paste0("U ", k, " to není „", got, "“. Zkus to znovu — jde o to, jestli má proměnná pořadí a smysluplnou nulu.")))\n'
                  '}\n'
                  'list(pass = TRUE, msg = "Správně. Od škály se odvíjí, jaký graf a jaký test má smysl použít.")'),
        "reseni": 'odpoved <- "osetreni=nominalni,blok=nominalni,puda_ph=intervalova,vyska_cm=pomerova"\n',
    },
    {
        "id": "stat-03",
        "title": "Normalita — shapiro test",
        "lesson": 10, "minutes": 5, "level": 4,
        "skills": ["statistika", "normalita", "shapiro"],
        "dataset": "skolni_zahrada.csv",
        "nacti": 'zahrada <- read.csv("skolni_zahrada.csv", stringsAsFactors = FALSE)',
        "zadani": ("Otestuj normalitu výšek (`vyska_cm`) u ošetření `kompost` (Shapiro-Wilk).\n"
                   "Do `p_hodnota` dej p-hodnotu (na 4 mesta), do `je_normalni` TRUE/FALSE\n"
                   "(hladinová významnost 0.05)."),
        "starter": "v <- zahrada$vyska_cm[zahrada$osetreni == \"kompost\"]\nv <- v[!is.na(v)]\nst <- shapiro.test(v)\np_hodnota <-\nje_normalni <-\n",
        "hints": [
            "`st$p.value`",
            "`st$p.value > 0.05` — nulová hypotéza je „data jsou normální“.",
        ],
        "check": ('z <- read.csv("skolni_zahrada.csv", stringsAsFactors = FALSE)\n'
                  'v <- z$vyska_cm[z$osetreni == "kompost"]; v <- v[!is.na(v)]\n'
                  'sp <- shapiro.test(v)$p.value\n'
                  'a <- .v_num(get("p_hodnota"), round(sp, 4), tol = 1e-3)\nif (!a$pass) return(a)\n'
                  'if (!is.logical(get("je_normalni"))) return(.v_spam("`je_normalni` ma byt TRUE nebo FALSE."))\n'
                  'if (get("je_normalni") != (sp > 0.05)) return(.v_spam("Rozhodnutí nesedí k p-hodnotě — připomeň si, že vysoké p neznamená „není normální“, ale „nemáme důkaz opaku“."))\n'
                  'list(pass = TRUE, msg = "Správně. A pamatuj: test normality je o důkazech, ne o pravdě.")'),
        "reseni": ('v <- zahrada$vyska_cm[zahrada$osetreni == "kompost"]\nv <- v[!is.na(v)]\n'
                   'st <- shapiro.test(v)\n'
                   'p_hodnota <- round(st$p.value, 4)\nje_normalni <- st$p.value > 0.05\n'),
    },
    {
        "id": "stat-04",
        "title": "t-test mezi osetrenimi",
        "lesson": 10, "minutes": 6, "level": 4,
        "skills": ["statistika", "t_test", "porovnani"],
        "dataset": "skolni_zahrada.csv",
        "nacti": 'zahrada <- read.csv("skolni_zahrada.csv", stringsAsFactors = FALSE)',
        "zadani": ("Porovnej výšky rostlin `kompost` versus `bez hnojeni` Welchovým t-testem.\n"
                   "Do `t_hodnota` dej testovou statistiku (2 mesta), do `p_hodnota` p-hodnotu (4 mesta),\n"
                   "do `rodil_cm` rozdíl průměrů (2 mesta)."),
        "starter": 'a <- zahrada$vyska_cm[zahrada$osetreni == "kompost"]\nb <- zahrada$vyska_cm[zahrada$osetreni == "bez hnojeni"]\n tt <- t.test(a, b)\n',
        "hints": [
            "`tt$statistic` a `tt$p.value`",
            "`mean(a, na.rm = TRUE) - mean(b, na.rm = TRUE)`",
        ],
        "check": ('z <- read.csv("skolni_zahrada.csv", stringsAsFactors = FALSE)\n'
                  'a <- z$vyska_cm[z$osetreni == "kompost"]; b <- z$vyska_cm[z$osetreni == "bez hnojeni"]\n'
                  'tt <- t.test(a, b)\n'
                  'a1 <- .v_num(get("t_hodnota"), round(as.numeric(tt$statistic), 2), tol = 5e-2)\nif (!a1$pass) return(a1)\n'
                  'b1 <- .v_num(get("p_hodnota"), round(tt$p.value, 4), tol = 1e-3)\nif (!b1$pass) return(b1)\n'
                  '.v_num(get("rodil_cm"), round(mean(a, na.rm = TRUE) - mean(b, na.rm = TRUE), 2), tol = 5e-2)'),
        "reseni": ('a <- zahrada$vyska_cm[zahrada$osetreni == "kompost"]\n'
                   'b <- zahrada$vyska_cm[zahrada$osetreni == "bez hnojeni"]\n'
                   'tt <- t.test(a, b)\n'
                   't_hodnota <- round(as.numeric(tt$statistic), 2)\np_hodnota <- round(tt$p.value, 4)\n'
                   'rodil_cm <- round(mean(a, na.rm = TRUE) - mean(b, na.rm = TRUE), 2)\n'),
    },
    {
        "id": "stat-05",
        "title": "Kontingencni tabulka a chi-kvadrat",
        "lesson": 11, "minutes": 6, "level": 4,
        "skills": ["statistika", "chikvadrat", "table"],
        "dataset": "knihovna.csv",
        "nacti": 'knihovna <- read.csv("knihovna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Je závislost mezi žánrem a stavem výpůjčky? Udělej kontingenční tabulku\n"
                   "`table(zanr, stav)`, otestuj chi-kvadrátem a do `p_hodnota` dej p-hodnotu (4 mesta)."),
        "starter": 'tt <- table(knihovna$zanr, knihovna$stav)\nchisq.test(tt)\np_hodnota <-\n',
        "hints": [
            "`chisq.test(tt)$p.value`",
            "Pozor na varování o malých četnostech — to je součást odpovědi.",
        ],
        "check": ('k <- read.csv("knihovna.csv", stringsAsFactors = FALSE)\n'
                  'sp <- suppressWarnings(chisq.test(table(k$zanr, k$stav))$p.value)\n'
                  '.v_num(get("p_hodnota"), round(sp, 4), tol = 2e-3,\n'
                  '       msg_ok = "Jo. A až budeš psát závěr, přidej, že některé buňky jsou řídké.")'),
        "reseni": ('tt <- table(knihovna$zanr, knihovna$stav)\n'
                   'p_hodnota <- round(chisq.test(tt)$p.value, 4)\n'),
    },
    {
        "id": "stat-06",
        "title": "Korelace plat a praxe",
        "lesson": 11, "minutes": 5, "level": 3,
        "skills": ["statistika", "korelace", "cor"],
        "dataset": "mzdy.csv",
        "nacti": 'mzdy <- read.csv("mzdy.csv", stringsAsFactors = FALSE)',
        "zadani": ("Spočti Pearsonovu korelaci mezi `praxe_roky` a `plat_kc` (complete cases)\n"
                   "a Stejně tak Spearmanovu. Do `r_pearson`, `rho_spearman` (oba na 3 mesta)\n"
                   "a do `silnejsi` napiš který je silnější („pearson“ / „spearman“)."),
        "starter": 'm <- mzdy[complete.cases(mzdy[, c("praxe_roky", "plat_kc")]), ]\nr_pearson <-\nrho_spearman <-\nsilnejsi <-\n',
        "hints": [
            "`cor(m$praxe_roky, m$plat_kc)` a `cor(..., method = \"spearman\")`",
            "`if (abs(r) > abs(rho)) \"pearson\" else \"spearman\"`",
        ],
        "check": ('m <- read.csv("mzdy.csv", stringsAsFactors = FALSE)\n'
                  'm <- m[complete.cases(m[, c("praxe_roky", "plat_kc")]), ]\n'
                  'rp <- cor(m$praxe_roky, m$plat_kc); rs <- cor(m$praxe_roky, m$plat_kc, method = "spearman")\n'
                  'a <- .v_num(get("r_pearson"), round(rp, 3), tol = 1e-3)\nif (!a$pass) return(a)\n'
                  'b <- .v_num(get("rho_spearman"), round(rs, 3), tol = 1e-3)\nif (!b$pass) return(b)\n'
                  '.v_txt(get("silnejsi"), if (abs(rp) >= abs(rs)) "pearson" else "spearman")'),
        "reseni": ('m <- mzdy[complete.cases(mzdy[, c("praxe_roky", "plat_kc")]), ]\n'
                   'r_pearson <- round(cor(m$praxe_roky, m$plat_kc), 3)\n'
                   'rho_spearman <- round(cor(m$praxe_roky, m$plat_kc, method = "spearman"), 3)\n'
                   'silnejsi <- if (abs(r_pearson) >= abs(rho_spearman)) "pearson" else "spearman"\n'),
    },
    {
        "id": "stat-07",
        "title": "Jednoducha regrese",
        "lesson": 11, "minutes": 6, "level": 4,
        "skills": ["statistika", "regrese", "lm"],
        "dataset": "mzdy.csv",
        "nacti": 'mzdy <- read.csv("mzdy.csv", stringsAsFactors = FALSE)',
        "zadani": ("Nasaď lineární model `plat_kc ~ praxe_roky` (jen platné řádky). Do `sklonac` dej\n"
                   "odhad koeficientu u praxe (Kč za rok, 1 místo), do `prusecik` úsek (na celá čísla)\n"
                   "a do `pred_15_let` předpověď platu po 15 letech praxe."),
        "starter": 'm <- mzdy[complete.cases(mzdy[, c("praxe_roky", "plat_kc")]), ]\nmodel <- lm(plat_kc ~ praxe_roky, data = m)\n',
        "hints": [
            "`coef(model)[\"praxe_roky\"]` a `coef(model)[1]`",
            "`predict(model, newdata = data.frame(praxe_roky = 15))`",
        ],
        "check": ('m <- read.csv("mzdy.csv", stringsAsFactors = FALSE)\n'
                  'm <- m[complete.cases(m[, c("praxe_roky", "plat_kc")]), ]\n'
                  'mo <- lm(plat_kc ~ praxe_roky, data = m)\n'
                  'a <- .v_num(get("sklonac"), round(coef(mo)["praxe_roky"], 1), tol = 5e-1)\nif (!a$pass) return(a)\n'
                  'b <- .v_num(get("prusecik"), round(coef(mo)[1], 0), tol = 5e1)\nif (!b$pass) return(b)\n'
                  '.v_num(get("pred_15_let"), round(as.numeric(predict(mo, newdata = data.frame(praxe_roky = 15))), 0), tol = 1e2)'),
        "reseni": ('m <- mzdy[complete.cases(mzdy[, c("praxe_roky", "plat_kc")]), ]\n'
                   'model <- lm(plat_kc ~ praxe_roky, data = m)\n'
                   'sklonac <- round(coef(model)["praxe_roky"], 1)\nprusecik <- round(coef(model)[1], 0)\n'
                   'pred_15_let <- round(as.numeric(predict(model, newdata = data.frame(praxe_roky = 15))), 0)\n'),
    },
]
