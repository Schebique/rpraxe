# ---------------------------------------------------------------------------
# rpraxe — generátor syntetických datasetů
# Deterministické (fixní seed), české reálie, záměrně "špinavé" tak,
# aby šlo procvičovat to, co kurz potřebuje: faktory, NA, dec = ",",
# textová čísla, duplicity, data, ISO datum, dlouhé/široké tabulky.
# ---------------------------------------------------------------------------
set.seed(20261102)
out <- Sys.getenv("RPRAXE_OUT", Sys.getenv("RPRAXE_DATASETS", "/data/datasets"))
dir.create(out, recursive = TRUE, showWarnings = FALSE)
setwd(out)

cs <- function(...) paste0(..., collapse = "")

# ---------------------------------------------------------------------------
# 1) KAVÁRNA — objednávky: dplyr, pipes, group_by, summarize, faktory, ggplot
# ---------------------------------------------------------------------------
n <- 420
pobocky <- c("Kralupy", "Kladno", "Praha-Holešovice", "Kladno", "Kralupy")
napoje  <- c("espresso", "cappuccino", "flat white", "caj", "horka", "limonada")
dny <- seq(as.Date("2026-03-02"), as.Date("2026-06-30"), by = "day")
kavarna <- data.frame(
  id_objednavky = sprintf("K%04d", seq_len(n)),
  datum   = sample(dny, n, replace = TRUE),
  hodina  = sprintf("%02d:%02d", sample(7:19, n, TRUE), sample(c(0L,15L,30L,45L), n, TRUE)),
  pobocka = factor(sample(pobocky, n, TRUE)),
  napoj   = factor(sample(napoje, n, TRUE, prob = c(.22,.26,.16,.13,.12,.11))),
  velkost = factor(sample(c("small","medium","large"), n, TRUE, prob = c(.35,.45,.20)),
                   levels = c("small","medium","large")),
  pocet_kus = sample(1:4, n, TRUE, prob = c(.62,.24,.10,.04)),
  cena_ks = round(runif(n, 39, 129), 1),
  sleva_procento = ifelse(runif(n) < .22, sample(c(5,10,15), n, TRUE), 0),
  zakaznik_new = sample(c(TRUE, FALSE), n, TRUE, prob = c(.3,.7)),
  barista = factor(sample(c("Lenka","Petr","Kamila","Ondra","Nena"), n, TRUE)),
  hodnoceni = sample(1:5, n, TRUE, prob = c(.05,.08,.17,.37,.33))
)
kavarna$trzba <- round(kavarna$pocet_kus * kavarna$cena_ks * (1 - kavarna$sleva_procento/100), 1)
kavarna$trzba[sample(n, 14)] <- NA          # chybějící tržba -> NA cvičení
kavarna$cena_ks[sample(n, 6)] <- NA
write.csv(kavarna, "kavarna.csv", row.names = FALSE)

# ---------------------------------------------------------------------------
# 2) ŠKOLNÍ ZAHRADA — pokus s hnojením: faktory, t-test, ANOVA, boxplot
# ---------------------------------------------------------------------------
g <- 90
osetreni <- factor(rep(c("bez hnojeni", "kompost", "hnedUHNOJ", "substrat"),
                       length.out = g), levels = c("bez hnojeni","kompost","hnedUHNOJ","substrat"))
blok <- factor(rep(c("A","B","C"), length.out = g))
zaklad <- c(`bez hnojeni` = 12.4, kompost = 17.8, hnedUHNOJ = 21.3, substrat = 15.1)[as.character(osetreni)]
zahrada <- data.frame(
  rostlina_id = sprintf("R%03d", seq_len(g)),
  blok = blok,
  osetreni = osetreni,
  vyska_cm = round(zaklad + rnorm(g, 0, 2.6) + as.numeric(blok) * .7, 1),
  listu = pmax(2, round(rnorm(g, 14, 4) + as.numeric(osetreni) * 1.4)),
  kvety = rpois(g, lambda = pmax(.2, zaklad/7)),
  puda_ph = round(rnorm(g, 6.6, .4), 2),
  slunecni_hodiny = round(runif(g, 2.5, 9.5), 1),
  poznamka = sample(c("", "", "", "polito navic", "presazena", "usla po mraziku"), g, TRUE)
)
zahrada$vyska_cm[sample(g, 5)] <- NA
write.csv(zahrada, "skolni_zahrada.csv", row.names = FALSE)

# ---------------------------------------------------------------------------
# 3) DOJÍŽĎKA — napodobuje vzor "dojizdeniSkola" z kurzu (dlouhý formát, kódy)
# ---------------------------------------------------------------------------
obce <- c("Kralupy nad Vltavou","Kladno","Slany","Velvary","Neratovice","Melnik",
          "Roudnice nad Labem","Litomerice","Mounotov","Veltrusy")
typy <- c("zakladni skola","stredni skola","ucilisni obor")
doprava <- factor(sample(c("autem","MHD","vlak","kolo","pesky"), 260, TRUE,
                         prob = c(.41,.21,.14,.12,.12)),
                  levels = c("pesky","kolo","MHD","autem","vlak"))
dojizdka <- data.frame(
  id_linka     = sprintf("D%05d", seq_len(260)),
  obec         = factor(sample(obce, 260, TRUE)),
  skola_typ    = factor(sample(typy, 260, TRUE)),
  pocet_zaku   = as.integer(round(runif(260, 12, 480))),
  vzdalenost_km = round(runif(260, .4, 28), 1),
  cas_min      = round(runif(260, 3, 78)),
  doprava       = doprava,
  den          = factor(sample(c("pondeli","streda","patek"), 260, TRUE),
                        levels = c("pondeli","streda","patek")),
  sldb_rok     = 2021,
  platna_do    = sample(seq(as.Date("2026-06-30"), as.Date("2027-12-31"), by = "month"), 260, TRUE)
)
dojizdka$vzdalenost_km[dojizdka$cas_min > 60 & dojizdka$doprava == "pesky"] <- NA
write.csv(dojizdka, "dojizdka.csv", row.names = FALSE)
writeLines(c(
  "popis datasetu dojizdka.csv (synteticka data,inspirovana datasetem z kurzu)",
  "id_linka      - identifikator linky (text)",
  "obec          - name obce, ze ktere se dojiždí (faktor)",
  "skola_typ     - typ skoly (zakladni skola / stredni skola / ucilisni obor)",
  "pocet_zaku    - pocet dojíždějících žáků (celé číslo)",
  "vzdalenost_km - vzdálenost ve km (desetinné číslo, DEC = TEČKA)",
  "cas_min       - doba dojížďky v minutách",
  "doprava       - prostředek (ordinaální faktor: pesky < kolo < MHD < autem < vlak)",
  "den           - den v týdnu (ordinaální faktor)",
  "sldb_rok      - rok zjištění",
  "platna_do     - datum platnosti údaje (ISO)"
), "dojizdka_popis.txt")

# ---------------------------------------------------------------------------
# 4) SPOTŘEBA BYTU — den × byt: široká tabulka, NA, nutnost pivot delšího
# ---------------------------------------------------------------------------
n <- 240
energie <- data.frame(
  id  = seq_len(n),
  mesic = factor(month.abb[rep(1:8, length.out = n)], levels = month.abb[1:8]),
  byt = factor(rep(paste0("byt_", sprintf("%02d", 1:6)), length.out = n)),
  topna_sezona = rep(c(TRUE, TRUE, TRUE, TRUE, FALSE, FALSE, FALSE, FALSE), length.out = n),
  kwh = round(abs(rnorm(n, 42, 22)) + ifelse(rep(rep(c(TRUE,TRUE,TRUE,TRUE,FALSE,FALSE,FALSE,FALSE), length.out = n), 1), 35, 0), 2),
  cena_kwh = round(runif(n, 4.8, 6.9), 2),
  obyvatel = sample(1:5, n, TRUE),
  podlazí = sample(c("-1","1","2","3","4","5+"), n, TRUE),  # textové číslo záměrně
  pozn = sample(c("", "", "", "vypadek mereni", "vynechana factura"), n, TRUE)
)
write.csv(energie, "energie_byty.csv", row.names = FALSE)

# ---------------------------------------------------------------------------
# 5) MĚŘENÍ VZORKŮ v laboratoři (styl 2. lekce): faktory, NA, "N/A" text
# ---------------------------------------------------------------------------
n <- 120
barviva <- c("NucSpot 488", "Thiazole Green", "RedDot Far-Red", "NucSpot 750")
vzorky <- data.frame(
  vzorek   = sprintf("V%03d", seq_len(n)),
  barvivo  = factor(sample(barviva, n, TRUE)),
  koncentrace = round(runif(n, .05, 4.5), 3),
  signl    = round(runif(n, 120, 9800)),
  namnozeni = c("ano","ne","NE","ano","ne","N/A")[sample(1:6, n, TRUE)],  # neuklizeno
  den_odberu = sample(seq(as.Date("2026-09-01"), as.Date("2026-10-15"), by = "day"), n, TRUE),
  teplota_st = round(rnorm(n, 21.5, 1.8), 1),
  operator = factor(sample(c("LD","SS","AM","JH"), n, TRUE)),
  diluace  = sample(c("1:10","1:100","1:50","ne"), n, TRUE)
)
vzorky$signl[sample(n, 9)] <- NA
vzorky$koncentrace[sample(n, 5)] <- NA
write.csv(vzorky, "lab_vzorky.csv", row.names = FALSE)

# ---------------------------------------------------------------------------
# 6) TEPLITA PRAHA — časová řada (denní), pro lubridate, klouzavý průměr, geoms
# ---------------------------------------------------------------------------
dny <- seq(as.Date("2025-01-01"), as.Date("2026-10-31"), by = "day")
t <- seq_along(dny)
season <- 9.5 + 10.5 * sin((2 * pi * (as.integer(format(dny, "%j")) - 105)) / 365)
teplota <- data.frame(
  datum = dny,
  teplot_prum = round(season + rnorm(length(dny), 0, 2.3), 1),
  sraz_mm = round(pmax(0, rnorm(length(dny), 1.6, 3.2)), 1),
  slun_hod = round(pmax(0, rnorm(length(dny), 3.6, 2.1)), 1),
  stanice = factor(rep(c("Praha-Libus","Praha-Ruzyne"), length.out = length(dny)))
)
teplota$sraz_mm[teplota$sraz_mm < .1] <- 0
write.csv(teplota, "teplota_praha.csv", row.names = FALSE)

# ---------------------------------------------------------------------------
# 7) PRODEJ ZBOŽÍ — messy soubor: dec ",", textová čísla, duplicity, ";"
# ---------------------------------------------------------------------------
n <- 150
zbozi <- data.frame(
  kod = sprintf("Z%03d", sample(1:40, n, TRUE)),       # duplicity záměrně
  zbozi = factor(sample(c("hrnek","miska","nádoba","prkénko","loupačka","hrnec"), n, TRUE)),
  pocet = sample(1:25, n, TRUE),
  cena = sprintf("%.2f", runif(n, 49, 890)),           # text s tečkou
  sleva = sprintf("%d%%", sample(c(0,0,5,10,20), n, TRUE)),
  sklad = sample(c("ANO","ano","Ne","NE","ano"), n, TRUE),
  datum_prodeje = format(sample(seq(as.Date("2026-01-05"), as.Date("2026-09-30"), by = "day"), n, TRUE), "%d.%m.%Y")
)
write.csv(zbozi, "prodej_zbozi_ciste.csv", row.names = FALSE)
zbozi$pocet <- sample(1:25, n, TRUE)
zbozi$cena <- sprintf("%.2f", runif(n, 49, 890))
messy <- zbozi
messy$cena <- sub(".", ",", messy$cena, fixed = TRUE)                 # dec = ","
messy$pocet <- paste0(" ", messy$pocet, " ks")                        # textové číslo
write.table(messy, "prodej_zbozi_sidla.txt", sep = ";", dec = ",",
            row.names = FALSE, quote = FALSE)

# ---------------------------------------------------------------------------
# 8) MZDY A VZDĚLÁNÍ — korelace, regrese, ordinální vzdělání
# ---------------------------------------------------------------------------
n <- 200
vzdelani <- factor(sample(c("SŠ","VS-bak","VS-mgr","VS-Ph.D."), n, TRUE, prob = c(.34,.28,.28,.10)),
                   levels = c("SŠ","VS-bak","VS-mgr","VS-Ph.D."))
praxe <- round(runif(n, 0, 32))
mzdy <- data.frame(
  id = sprintf("M%03d", seq_len(n)),
  vek = sample(22:63, n, TRUE),
  praxe_roky = praxe,
  vzdelani = vzdelani,
  obor = factor(sample(c("IT","strojirenstvi","skolstvi","zdravotnictvi","administrativa"), n, TRUE)),
  misto_prace = factor(sample(c("Praha","Kladno","remote","Brno"), n, TRUE, prob = c(.42,.18,.22,.18))),
  hodin_tyden = round(runif(n, 20, 52)),
  spokojenost = sample(1:10, n, TRUE),
  plat_kc = round((32000 + 900 * as.integer(vzdelani) + 620 * praxe +
                     rnorm(n, 0, 4800)) / 100) * 100
)
mzdy$plat_kc[mzdy$praxe_roky > 28 & mzdy$vzdelani == "SŠ"] <- NA
write.csv(mzdy, "mzdy.csv", row.names = FALSE)

# ---------------------------------------------------------------------------
# 9) KNIHOVNA — výpůjčky, datum, textové řetězce, chybějící data
# ---------------------------------------------------------------------------
n <- 200
knihovna <- data.frame(
  vypujcka_id = sprintf("V%05d", seq_len(n)),
  titul = factor(sample(c("Vek kova","Hovori hadi","Prvni R skript","Data a rozhodovani",
                          "Zahrada pro zacetniky","Statistika pro biology","tidywalk"), n, TRUE)),
  zanr = factor(sample(c("beletrie","odborna","ucobnice","pohadky"), n, TRUE)),
  vypujcka = sample(seq(as.Date("2026-01-01"), as.Date("2026-10-20"), by = "day"), n, TRUE),
  vraceni = as.Date(NA),
  dny_pujcky = NA_integer_,
  stav = factor(sample(c("vraceno","v pujcovne","pozde","ztraceno"), n, TRUE, prob = c(.7,.18,.10,.02)),
                levels = c("v pujcovne","vraceno","pozde","ztraceno")),
  ctenar_vek = sample(7:88, n, TRUE),
  popisky = sample(c("", "", "dobry tip", "doporucuje klub", "poskozena vazba"), n, TRUE)
)
ret <- knihovna$vypujcka + sample(1:60, n, TRUE)
knihovna$vraceni <- as.Date(ifelse(knihovna$stav %in% c("vraceno","pozde"), as.character(ret), NA_character_))
knihovna$dny_pujcky <- as.integer(knihovna$vraceni - knihovna$vypujcka)
write.csv(knihovna, "knihovna.csv", row.names = FALSE)

# ---------------------------------------------------------------------------
# 10) MALÝ CVIČNÝ DATASET — úplně základní (1. lekce, indexace, vektory)
# ---------------------------------------------------------------------------
male <- data.frame(
  jmeno = c("Jana","Petr","Marie","Tomas","Eva","Filip","Nina","Samuel","Irena","Lena"),
  vek   = c(41, 38, 55, 29, 47, 12, 33, 9, 61, 44),
  vyska_cm = c(168, 182, 165, 179, 171, 149, 174, 137, 163, 170),
  oblibena_cisla = c(7, 3, 9, 2, 5, 11, 4, 6, 8, 1),
  mesto = factor(c("Kralupy","Kladno","Praha","Kladno","Slany","Kralupy","Praha","Kralupy","London","Kladno")),
  radek_sestavi = seq_len(10)
)
write.csv(male, "skupina_deset.csv", row.names = FALSE)

# ---------------------------------------------------------------------------
# 11) ZVIRATA — zaběhnutá tabulka (srovnatelná s animals), bez náhody
# ---------------------------------------------------------------------------
zw <- data.frame(
  name = c("golias", "slon", "kun", "tygr", "potkan", "kocka", "pes", "pras", "ovce", "krava",
           "lizet", "opice", "gorila", "clovek", "myš", "kralik", "velryba", "delfin", "kůň", "los"),
  order = c("Carnivora", "Proboscidea", "Perissodactyla", "Carnivora", "Rodentia", "Carnivora",
            "Carnivora", "Artiodactyla", "Artiodactyla", "Artiodactyla", "Carnivora", "Primates",
            "Primates", "Primates", "Rodentia", "Lagomorpha", "Cetacea", "Cetacea",
            "Perissodactyla", "Artiodactyla"),
  life_exp = c(20.0, 69.0, 30.4, 24.0, 3.8, 15.0, 12.0, 19.8, 12.0, 30.0, 14.0, 30.0,
               31.0, 74.0, 3.5, 9.6, 100.0, 57.0, 46.0, 30.4),
  sleep_exp = c(10.0, 3.3, 2.9, 8.7, 7.6, 12.1, 10.1, 8.3, 3.0, 4.0, 12.5, 9.4,
                11.9, 8.0, 7.6, 8.6, NA, NA, 2.9, 3.1),
  bodywt = c(1600, 6654, 203, 162, 1.0, 3.3, 11.4, 192, 55.5, 603, 14.2, 25.0,
             203, 61.9, 0.02, 2.5, 20000, 1740, 521, 250),
  stringsAsFactors = FALSE
)
write.csv(zw, "zvirata.csv", row.names = FALSE)

cat("generováno do", out, "\n")
print(list.files(out))
