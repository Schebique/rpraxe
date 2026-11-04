"""Lekce 4 — pipes a dplyr. Právě tohle kurz zrovna probírá a chce to dril."""

TASKS = [
    {
        "id": "pipe-01",
        "title": "První pipe: filtr a sloupec",
        "lesson": 4, "minutes": 3, "level": 1,
        "skills": ["pipes", "dplyr", "filter", "pull"],
        "libraries": ["dplyr"],
        "dataset": "kavarna.csv",
        "nacti": 'kavarna <- read.csv("kavarna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Přes pipe (`%>%`) vyber objednávky z pobočky `Kladno` a nech si jen sloupec\n"
                   "`trzba` jako vektor → `trzba_kladno`. Pak spočítej její součet → `celkem_kladno`."),
        "starter": "library(dplyr)\ntrzba_kladno <- kavarna %>%\n\n",
        "hints": [
            "`kavarna %>% filter(pobocka == \"Kladno\") %>% pull(trzba)`",
            "`sum(trzba_kladno, na.rm = TRUE)`",
        ],
        "check": ('k <- read.csv("kavarna.csv", stringsAsFactors = FALSE)\n'
                  'sp <- sum(k$trzba[k$pobocka == "Kladno"], na.rm = TRUE)\n'
                  'if (!is.numeric(get("trzba_kladno"))) return(.v_spam("`trzba_kladno` ma byt ciselny vektor — pouzij `pull(trzba)`."))\n'
                  '.v_num(get("celkem_kladno"), sp, msg_ok = "Presně. `pull()` je pipe verze operátoru `$`.")'),
        "reseni": ('trzba_kladno <- kavarna %>% filter(pobocka == "Kladno") %>% pull(trzba)\n'
                   'celkem_kladno <- sum(trzba_kladno, na.rm = TRUE)\n'),
    },
    {
        "id": "pipe-02",
        "title": "Dve podminky v filtru",
        "lesson": 4, "minutes": 3, "level": 2,
        "skills": ["pipes", "filter", "summarise"],
        "libraries": ["dplyr"],
        "dataset": "kavarna.csv",
        "nacti": 'kavarna <- read.csv("kavarna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Kolik je objednávek nápoje `cappuccino` s cenou za kus vyšší než 90 Kč? → `pocet`.\n"
                   "A jaké je u nich průměrné hodnocení? → `prumer_hodnoceni`."),
        "starter": "library(dplyr)\nv <- kavarna %>%\n\npocet <- v$pocet\nprumer_hodnoceni <- v$prumer_hodnoceni\n",
        "hints": [
            "`filter(napoj == \"cappuccino\", cena_ks > 90)` — čárka znamená „a zároveň“.",
            "`summarise(pocet = n(), prumer_hodnoceni = mean(hodnoceni, na.rm = TRUE))`",
        ],
        "check": ('k <- read.csv("kavarna.csv", stringsAsFactors = FALSE)\n'
                  'p <- k$napoj == "cappuccino" & k$cena_ks > 90\n'
                  'a <- .v_num(get("pocet"), sum(p, na.rm = TRUE))\nif (!a$pass) return(a)\n'
                  '.v_num(get("prumer_hodnoceni"), mean(k$hodnoceni[p], na.rm = TRUE), tol = 1e-3)'),
        "reseni": ('v <- kavarna %>%\n'
                   '  filter(napoj == "cappuccino", cena_ks > 90) %>%\n'
                   '  summarise(pocet = n(), prumer_hodnoceni = mean(hodnoceni, na.rm = TRUE))\n'
                   'v <- as.data.frame(v)\npocet <- v$pocet\nprumer_hodnoceni <- v$prumer_hodnoceni\n'),
    },
    {
        "id": "pipe-03",
        "title": "mutate: novy sloupec",
        "lesson": 4, "minutes": 4, "level": 2,
        "skills": ["pipes", "mutate"],
        "libraries": ["dplyr"],
        "dataset": "dojizdka.csv",
        "nacti": 'dojizdka <- read.csv("dojizdka.csv", stringsAsFactors = FALSE)',
        "zadani": ("Přidej sloupec `rychlost_km_h` = `vzdalenost_km / (cas_min / 60)` a logický\n"
                   "sloupec `delsi_dojizdka` (TRUE když je doba delší než 30 minut).\n"
                   "Tabulku ulož do `upravene` a průměrnou rychlost do `prumer_rychlosti`."),
        "starter": "library(dplyr)\nupravene <- dojizdka %>%\n\nprumer_rychlosti <-\n",
        "hints": [
            "`mutate(rychlost_km_h = vzdalenost_km / (cas_min / 60), delsi_dojizdka = cas_min > 30)`",
            "`mean(upravene$rychlost_km_h, na.rm = TRUE)`",
        ],
        "check": ('d <- read.csv("dojizdka.csv", stringsAsFactors = FALSE)\n'
                  'sp <- mean(d$vzdalenost_km / (d$cas_min / 60), na.rm = TRUE)\n'
                  'if (!("rychlost_km_h" %in% names(get("upravene")))) return(.v_spam("Chybí sloupec `rychlost_km_h`."))\n'
                  '.v_num(get("prumer_rychlosti"), sp, tol = 1e-3)'),
        "reseni": ('upravene <- dojizdka %>%\n'
                   '  mutate(rychlost_km_h = vzdalenost_km / (cas_min / 60),\n'
                   '         delsi_dojizdka = cas_min > 30)\n'
                   'prumer_rychlosti <- mean(upravene$rychlost_km_h, na.rm = TRUE)\n'),
    },
    {
        "id": "pipe-04",
        "title": "group_by a summarise",
        "lesson": 4, "minutes": 5, "level": 3,
        "skills": ["pipes", "group_by", "summarise", "arrange"],
        "libraries": ["dplyr"],
        "dataset": "kavarna.csv",
        "nacti": 'kavarna <- read.csv("kavarna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Spočítej podle poboček celkovou tržbu (bez NA) a průměrné hodnocení.\n"
                   "Výsledek nech v `po_pobockach` se sloupci `pobocka`, `trzba_celkem`, `hodnoceni_prumer`\n"
                   "a seřaď ho od nejvyšší tržby."),
        "starter": "library(dplyr)\npo_pobockach <- kavarna %>%\n\n",
        "hints": [
            "`group_by(pobocka) %>% summarise(trzba_celkem = sum(trzba, na.rm = TRUE), hodnoceni_prumer = mean(hodnoceni, na.rm = TRUE))`",
            "Na konci `arrange(desc(trzba_celkem))`.",
        ],
        "check": ('library(dplyr)\nk <- read.csv("kavarna.csv", stringsAsFactors = FALSE)\n'
                  'sp <- k %>% group_by(pobocka) %>%\n'
                  '  summarise(trzba_celkem = sum(trzba, na.rm = TRUE),\n'
                  '            hodnoceni_prumer = mean(hodnoceni, na.rm = TRUE), .groups = "drop") %>%\n'
                  '  arrange(desc(trzba_celkem))\n'
                  '.v_df(get("po_pobockach"), sp,\n'
                  '       msg_ok = "Perfektní — tohle je klasická kurzová trojice group_by, summarise, arrange.")'),
        "reseni": ('po_pobockach <- kavarna %>%\n'
                   '  group_by(pobocka) %>%\n'
                   '  summarise(trzba_celkem = sum(trzba, na.rm = TRUE),\n'
                   '            hodnoceni_prumer = mean(hodnoceni, na.rm = TRUE), .groups = "drop") %>%\n'
                   '  arrange(desc(trzba_celkem))\n'),
    },
    {
        "id": "pipe-05",
        "title": "Nejlepsi barista",
        "lesson": 4, "minutes": 5, "level": 3,
        "skills": ["pipes", "group_by", "filter"],
        "libraries": ["dplyr"],
        "dataset": "kavarna.csv",
        "nacti": 'kavarna <- read.csv("kavarna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Který barista má nejvyšší průměrné hodnocení a přitom obsloužil aspoň 10 objednávek?\n"
                   "Jméno do `nejlepsi`, průměr do `prumer_nejlepsi` (na 3 desetinná místa)."),
        "starter": "library(dplyr)\n\n",
        "hints": [
            "`group_by(barista) %>% summarise(prumer = mean(hodnoceni, na.rm = TRUE), n = n(), .groups = \"drop\")`",
            "`filter(n >= 10) %>% arrange(desc(prumer))` a pak první řádek.",
        ],
        "check": ('library(dplyr)\nk <- read.csv("kavarna.csv", stringsAsFactors = FALSE)\n'
                  'sp <- k %>% group_by(barista) %>%\n'
                  '  summarise(prumer = mean(hodnoceni, na.rm = TRUE), n = n(), .groups = "drop") %>%\n'
                  '  filter(n >= 10) %>% arrange(desc(prumer)) %>% slice(1)\n'
                  'a <- .v_txt(get("nejlepsi"), sp$barista[1])\nif (!a$pass) return(a)\n'
                  '.v_num(get("prumer_nejlepsi"), round(sp$prumer[1], 3), tol = 1e-3)'),
        "reseni": ('v <- kavarna %>%\n'
                   '  group_by(barista) %>%\n'
                   '  summarise(prumer = mean(hodnoceni, na.rm = TRUE), n = n(), .groups = "drop") %>%\n'
                   '  filter(n >= 10) %>% arrange(desc(prumer))\n'
                   'nejlepsi <- v$barista[1]\nprumer_nejlepsi <- round(v$prumer[1], 3)\n'),
    },
    {
        "id": "pipe-06",
        "title": "case_when misto zahnizdeeneho ifelse",
        "lesson": 4, "minutes": 5, "level": 3,
        "skills": ["pipes", "case_when", "faktory"],
        "libraries": ["dplyr"],
        "dataset": "mzdy.csv",
        "nacti": 'mzdy <- read.csv("mzdy.csv", stringsAsFactors = FALSE)',
        "zadani": ("Vytvoř kategoriální sloupec `pasek` podle platu: do 35 000 „nizky“, do 45 000\n"
                   "„stredni“, výš „vyssi“. Ulož do `mzdy` a přidej tabulku četností → `tabulka_pasek`."),
        "starter": "library(dplyr)\nmzdy <- mzdy %>% mutate(pasek = case_when(\n\n))\ntabulka_pasek <-\n",
        "hints": [
            "`case_when(plat_kc <= 35000 ~ \"nizky\", plat_kc <= 45000 ~ \"stredni\", TRUE ~ \"vyssi\")`",
            "`table(mzdy$pasek)` nebo `count(mzdy, pasek)`",
        ],
        "check": ('m <- read.csv("mzdy.csv", stringsAsFactors = FALSE)\n'
                  'p <- dplyr::case_when(m$plat_kc <= 35000 ~ "nizky", m$plat_kc <= 45000 ~ "stredni",\n'
                  '                      TRUE ~ "vyssi")\n'
                  'if (!("pasek" %in% names(get("mzdy")))) return(.v_spam("Chybi `pasek`."))\n'
                  'got <- sort(as.numeric(table(get("mzdy")$pasek)))\n'
                  'sp <- sort(as.numeric(table(p)))\n'
                  'if (!isTRUE(all.equal(got, sp)))\n'
                  '  return(.v_spam("Rozdelieni do pasmu nesedi — `case_when()` vyhodnocuje podminky zleva, prvni shoda vyhrava."))\n'
                  'list(pass = TRUE, msg = "Správně. Kdyby „stredni“ byla první podmínka, spolkne i nízké platy.")'),
        "reseni": ('mzdy <- mzdy %>%\n'
                   '  mutate(pasek = case_when(plat_kc <= 35000 ~ "nizky",\n'
                   '                           plat_kc <= 45000 ~ "stredni",\n'
                   '                           TRUE ~ "vyssi"))\n'
                   'tabulka_pasek <- table(mzdy$pasek)\n'),
    },
    {
        "id": "pipe-07",
        "title": "left_join dvou tabulek",
        "lesson": 4, "minutes": 6, "level": 4,
        "skills": ["pipes", "left_join", "spojovani"],
        "libraries": ["dplyr"],
        "dataset": "dojizdka.csv",
        "nacti": ('dojizdka <- read.csv("dojizdka.csv", stringsAsFactors = FALSE)\n'
                  'popis_obci <- data.frame(obec = unique(dojizdka$obec),\n'
                  '                          kraj = "Stredocesky", stringsAsFactors = FALSE)'),
        "zadani": ("Připoj k `dojizdka` sloupec `kraj` z tabulky `popis_obci` (klíč `obec`).\n"
                   "Pak spočítej počet dojížděk podle typu dopravy → `po_doprave`\n"
                   "se sloupci `doprava` a `n`."),
        "starter": "library(dplyr)\nspojene <- left_join( )\npo_doprave <-\n",
        "hints": [
            "`left_join(dojizdka, popis_obci, by = \"obec\")`",
            "`count(spojene, doprava, name = \"n\")`",
        ],
        "check": ('library(dplyr)\nd <- read.csv("dojizdka.csv", stringsAsFactors = FALSE)\n'
                  'sp <- d %>% count(doprava, name = "n")\n'
                  '.v_df(get("po_doprave"), sp,\n'
                  '       msg_ok = "Ano — `left_join()` nechává všechny řádky z levé tabulky a doplní, co najde.")'),
        "reseni": ('spojene <- left_join(dojizdka, popis_obci, by = "obec")\n'
                   'po_doprave <- count(spojene, doprava, name = "n")\n'),
    },
    {
        "id": "pipe-08",
        "title": "Mesicni vitez",
        "lesson": 4, "minutes": 6, "level": 4,
        "skills": ["pipes", "group_by", "slice_max", "datum"],
        "libraries": ["dplyr"],
        "dataset": "kavarna.csv",
        "nacti": 'kavarna <- read.csv("kavarna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Pro každý měsíc (podle `datum`) najdi nápoj s nejvyšší tržbou.\n"
                   "Výsledek ulož do `mesicni_vitezove` se sloupci `mesic` (text „YYYY-MM“),\n"
                   "`napoj`, `trzba`."),
        "starter": 'library(dplyr)\nkavarna$mesic <- format(as.Date(kavarna$datum), "%Y-%m")\nmesicni_vitezove <- kavarna %>%\n\n',
        "hints": [
            "`group_by(mesic, napoj) %>% summarise(trzba = sum(trzba, na.rm = TRUE), .groups = \"drop\")`",
            "`slice_max(trzba, n = 1)` — groupa je měsíc, ne nápoj.",
        ],
        "check": ('library(dplyr)\nk <- read.csv("kavarna.csv", stringsAsFactors = FALSE)\n'
                  'k$mesic <- format(as.Date(k$datum), "%Y-%m")\n'
                  'sp <- k %>% group_by(mesic, napoj) %>%\n'
                  '  summarise(trzba = sum(trzba, na.rm = TRUE), .groups = "drop") %>%\n'
                  '  slice_max(trzba, n = 1)\n'
                  'g <- get("mesicni_vitezove")\n'
                  'if (is.null(g)) return(.v_spam("Chybi `mesicni_vitezove`."))\n'
                  'if (nrow(as.data.frame(g)) != nrow(sp))\n'
                  '  return(.v_spam(paste0("Radku je ", nrow(as.data.frame(g)), ", mit jich byt ", nrow(sp),\n'
                  '                        ". Maximum se počítá uvnitř měsíce, ne v roce celém.")))\n'
                  '.v_num(sum(as.data.frame(g)$trzba, na.rm = TRUE), sum(sp$trzba, na.rm = TRUE), tol = 1e-3)'),
        "reseni": ('kavarna$mesic <- format(as.Date(kavarna$datum), "%Y-%m")\n'
                   'mesicni_vitezove <- kavarna %>%\n'
                   '  group_by(mesic, napoj) %>%\n'
                   '  summarise(trzba = sum(trzba, na.rm = TRUE), .groups = "drop") %>%\n'
                   '  slice_max(trzba, n = 1)\n'),
    },
    {
        "id": "pipe-09",
        "title": "count a podil",
        "lesson": 4, "minutes": 3, "level": 2,
        "skills": ["pipes", "count"],
        "libraries": ["dplyr"],
        "dataset": "knihovna.csv",
        "nacti": 'knihovna <- read.csv("knihovna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Který žánr má nejvíc výpůjček? Název do `nej zanr` (bez mezer: `nejzanne`),\n"
                   "jeho podíl z všech výpůjček na 3 desetinná místa do `podil`."),
        "starter": "library(dplyr)\n\n",
        "hints": [
            "`count(knihovna, zanr) %>% arrange(desc(n))`",
            "Podíl je `n[1] / sum(n)`.",
        ],
        "check": ('k <- read.csv("knihovna.csv", stringsAsFactors = FALSE)\n'
                  't <- sort(table(k$zanr), decreasing = TRUE)\n'
                  'a <- .v_txt(get("nejzanne"), names(t)[1])\nif (!a$pass) return(a)\n'
                  '.v_num(get("podil"), round(as.numeric(t[1] / sum(t)), 3), tol = 1e-3)'),
        "reseni": ('p <- count(knihovna, zanr) %>% arrange(desc(n))\n'
                   'nejzanne <- p$zanr[1]\npodil <- round(p$n[1] / sum(p$n), 3)\n'),
    },
    {
        "id": "pipe-10",
        "title": "select, rename, arrange — uklid tabulku",
        "lesson": 4, "minutes": 4, "level": 3,
        "skills": ["pipes", "rename", "select", "arrange"],
        "libraries": ["dplyr"],
        "dataset": "dojizdka.csv",
        "nacti": 'dojizdka <- read.csv("dojizdka.csv", stringsAsFactors = FALSE)',
        "zadani": ("Udělej přehlednou tabulku `prehled`: sloupce `cas_min`, `vzdalenost_km`,\n"
                   "`doprava`, `skola_typ`, `obec` (v tomto pořadí), přejmenuj `skola_typ` na\n"
                   "`typ_skoly` a seřaď podle času sestupně. Název prvního sloupce do `prvni_sloupec`."),
        "starter": "library(dplyr)\nprehled <- dojizdka %>%\n\nprvni_sloupec <- names(prehled)[1]\n",
        "hints": [
            "`select(cas_min, vzdalenost_km, doprava, skola_typ, obec) %>% rename(typ_skoly = skola_typ)`",
            "`arrange(desc(cas_min))` na konec.",
        ],
        "check": ('library(dplyr)\nd <- read.csv("dojizdka.csv", stringsAsFactors = FALSE)\n'
                  'sp <- d %>% select(cas_min, vzdalenost_km, doprava, skola_typ, obec) %>%\n'
                  '  rename(typ_skoly = skola_typ) %>% arrange(desc(cas_min))\n'
                  'a <- .v_txt(get("prvni_sloupec"), "cas_min")\nif (!a$pass) return(a)\n'
                  '.v_df(get("prehled"), sp)'),
        "reseni": ('prehled <- dojizdka %>%\n'
                   '  select(cas_min, vzdalenost_km, doprava, skola_typ, obec) %>%\n'
                   '  rename(typ_skoly = skola_typ) %>% arrange(desc(cas_min))\n'
                   'prvni_sloupec <- names(prehled)[1]\n'),
    },
    {
        "id": "pipe-11",
        "title": "Sumarizace přes vic sloupcu",
        "lesson": 4, "minutes": 6, "level": 4,
        "skills": ["pipes", "group_by", "n"],
        "libraries": ["dplyr"],
        "dataset": "kavarna.csv",
        "nacti": 'kavarna <- read.csv("kavarna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Kombinace pobočka × velkost: spočítej počet objednávek a průměrnou cenu za kus.\n"
                   "Výsledek do `kriz` se sloupci `pobocka`, `velkost`, `n`, `cena_prumer`."),
        "starter": "library(dplyr)\nkriz <- kavarna %>%\n\n",
        "hints": [
            "`group_by(pobocka, velkost)`",
            "`summarise(n = n(), cena_prumer = mean(cena_ks, na.rm = TRUE), .groups = \"drop\")`",
        ],
        "check": ('library(dplyr)\nk <- read.csv("kavarna.csv", stringsAsFactors = FALSE)\n'
                  'sp <- k %>% group_by(pobocka, velkost) %>%\n'
                  '  summarise(n = n(), cena_prumer = mean(cena_ks, na.rm = TRUE), .groups = "drop")\n'
                  '.v_df(get("kriz"), sp, msg_ok = "Good. Dva GROUP sloupce = kombinace, přesně jako kontingenční tabulka.")'),
        "reseni": ('kriz <- kavarna %>%\n'
                   '  group_by(pobocka, velkost) %>%\n'
                   '  summarise(n = n(), cena_prumer = mean(cena_ks, na.rm = TRUE), .groups = "drop")\n'),
    },
    {
        "id": "pipe-12",
        "title": "Under a over: porovnani skupin",
        "lesson": 4, "minutes": 5, "level": 3,
        "skills": ["pipes", "filter", "pull"],
        "libraries": ["dplyr"],
        "dataset": "zvirata.csv",
        "nacti": 'zvirata <- read.csv("zvirata.csv", stringsAsFactors = FALSE)',
        "zadani": ("Porovnej průměrnou délku života (life_exp) u zvířat `order == \"Primates\"`\n"
                   "a `order == \"Carnivora\"`. Do `rozdil` dej o kolik let se liší (kladně)."),
        "starter": "library(dplyr)\n\n",
        "hints": [
            "`zvirata %>% filter(order %in% c(\"Primates\", \"Carnivora\")) %>% group_by(order) %>% summarise(prumer = mean(life_exp, na.rm = TRUE))`",
            "`abs(diff(v$prumer))`",
        ],
        "check": ('library(dplyr)\nz <- read.csv("zvirata.csv", stringsAsFactors = FALSE)\n'
                  'p <- z %>% filter(order %in% c("Primates", "Carnivora")) %>%\n'
                  '  group_by(order) %>% summarise(prumer = mean(life_exp, na.rm = TRUE), .groups = "drop")\n'
                  '.v_num(get("rozdil"), abs(diff(p$prumer)), tol = 1e-2)'),
        "reseni": ('p <- zvirata %>%\n'
                   '  filter(order %in% c("Primates", "Carnivora")) %>%\n'
                   '  group_by(order) %>%\n'
                   '  summarise(prumer = mean(life_exp, na.rm = TRUE), .groups = "drop")\n'
                   'rozdil <- abs(diff(p$prumer))\n'),
    },
]
