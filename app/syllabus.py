"""Kalendář a sylabus kurzu R (Mgr. Lucie Hošková, ZS 2026/27).

Zdroj: https://luc-hoskova.github.io/introR_CUNI/sylabus.html
Termíny se používají na to, aby plánovač věděl, co zrovna probírali.
"""
from __future__ import annotations

from datetime import date, datetime

LESSONS = {
    1: {"date": "2026-09-15", "title": "Úvodní hodina",
        "topics": ["orientace v IDE RStudio", "projekty a organizace skriptu", "napoveda",
                   "operatory", "ukladani do promennych", "datove typy v R"],
        "skills": ["zaklady", "operatory", "promenne", "typy"]},
    2: {"date": "2026-09-29", "title": "Datove struktury",
        "topics": ["uvod do funkci", "datove struktury v R", "faktory", "prace s balicky"],
        "skills": ["vektory", "matice", "data.frame", "list", "faktory", "balicky"]},
    3: {"date": "2026-10-13", "title": "Indexace",
        "topics": ["indexace pomoci base R", "indexace pomoci dplyr", "hodnoty vs struktury"],
        "skills": ["indexace", "logika", "data.frame"]},
    4: {"date": "2026-10-27", "title": "Nacitani a transformace dat",
        "topics": ["nacitani dat do R", "kontrola dat", "pipes", "balicek dplyr"],
        "skills": ["nacitani", "cisteni", "pipes", "dplyr"]},
    5: {"date": "2026-11-10", "title": "Funkce",
        "topics": ["syntax funkce", "tvorba vlastni funkce", "cykly", "funkce apply() a rodina apply",
                   "vektorizace vs. iterativni pristup", "cas a datum"],
        "skills": ["funkce", "cykly", "apply", "vektorizace", "datum"]},
    6: {"date": "2026-11-24", "title": "Zaklady vizualizace",
        "topics": ["premysleni nad ucelem grafu", "bodove, carove a sloupcove grafy",
                   "zakladni vizualizace v R", "uvod do ggplot2"],
        "skills": ["vizualizace", "ggplot2", "barvy"]},
    7: {"date": "2026-12-08", "title": "Pokrocila vizualizace",
        "topics": ["boxploty", "denseplotty", "heat mapy", "violin grafy", "casove rady"],
        "skills": ["vizualizace", "ggplot2", "casove_radky"]},
    8: {"date": "2027-01-05", "title": "Mapy, 3D a interaktivni grafy",
        "topics": ["prostorova data v R", "bodove mapy", "chloropleth mapy", "3D grafy", "interaktivni grafy"],
        "skills": ["mapy", "interaktivni", "ggplot2"]},
    9: {"date": "2027-01-19", "title": "Typy dat a deskriptivni statistika",
        "topics": ["kvalitativni vs kvantitativni", "nominalni, ordinalni, intervalova, pomerova",
                   "prumer, median, modus", "miry variability"],
        "skills": ["statistika", "deskriptiva", "typy_dat"]},
    10: {"date": "2027-02-02", "title": "Uvod do inferencni statistiky",
         "topics": ["populace, vyber", "urcovani normality dat", "parametricke testy", "t-testy"],
         "skills": ["statistika", "testy", "normalita"]},
    11: {"date": "2027-02-16", "title": "Analyza kategoriálních dat, korelace a regrese",
         "topics": ["kontingencni tabulka", "neparametricke testy", "chi-kvadrat",
                    "Pearson/Spearman korelace", "regrese"],
         "skills": ["statistika", "chikvadrat", "korelace", "regrese"]},
}

CHEATSHEET = {
    "Zaklady a promenne": [
        ("x <- 5", "ulozeni hodnoty"),
        ("ls(); rm(x)", "vypis / smazani promennych"),
        ("class(x); str(x); mode(x)", "typ / struktura / mod"),
        ("?mean; ??ggplot", "napoveda"),
        ("getwd(); setwd('cesta')", "pracovni slozka"),
    ],
    "Datove struktury": [
        ("c(1, 2, 3); 1:10; seq(1, 10, by = 2)", "vektor, sekvence"),
        ("rep(1:3, each = 2); rep(1:3, 2)", "opakovani"),
        ("matrix(1:6, nrow = 2, byrow = TRUE)", "matice"),
        ("data.frame(a = 1:3, b = c('x','y','z'))", "data frame"),
        ("factor(v, levels = c('m','z'), labels = c('muz','zeena'))", "faktor s poradim"),
        ("list(a = 1, b = 'text'); l$a; l[['b']]", "list a vyber"),
        ("cbind(); rbind(); nrow(); ncol(); dim()", "skládání a rozměry"),
    ],
    "Indexace": [
        ("v[3]; v[c(1, 4)]; v[-2]; v[2:5]", "podle pozice"),
        ("v[v > 10]", "podle logical vektoru"),
        ("which(v > 10)", "pozice vyhovujicich"),
        ("df[, 'vek']; df$vek; df[['vek']]", "sloupec jako vektor"),
        ("df[1:5, ]; df[df$vek > 30, ]", "radky"),
        ("df[3, 2, drop = FALSE]", "prvek jako tabulka"),
        ("names(df)[1]; rownames(df)", "nazvy"),
    ],
    "Nacitani a kontrola dat": [
        ("read.csv('subor.csv', stringsAsFactors = FALSE)", "CSV s teckou"),
        ("read.csv('subor.csv', dec = ',', sep = ';')", "CSV s carkou / oddelovac")
        ,
        ("read.table('subor.txt', header = TRUE, dec = ',')", "obecne textova data"),
        ("readxl::read_xlsx('subor.xlsx', sheet = 1)", "Excel"),
        ("head(df, 10); str(df); summary(df); anyNA(df)", "kontrola"),
        ("df[df == '' | df == 'N/A'] <- NA", "rueni falšivých NA"),
        ("as.numeric(); readr::parse_number()", "text na cislo"),
        ("na.omit(df); dplyr::filter(!is.na(x))", "odstraneni radku s NA"),
    ],
    "Pipes a dplyr": [
        ("df %>% filter(vek > 30) %>% select(jmeno, vek)", "vyber radku a sloupcu"),
        ("df %>% mutate(bmi = hmot / (vys/100)^2)", "novy sloupec"),
        ("df %>% arrange(desc(trzba))", "razeni"),
        ("df %>% rename(vek = vek_txt)", "prejmenovani"),
        ("df %>% group_by(kraj) %>% summarise(prumer = mean(vek, na.rm = TRUE), n = n())", "agregace"),
        ("df %>% pull(vek)", "sloupec jako vektor"),
        ("ifelse(vek < 18, 'deti', 'dospeli')", "rozhodovani po radcich"),
        ("case_when(x < 10 ~ 'malo', TRUE ~ 'hodne')", "vice vetvi"),
        ("left_join(a, b, by = 'id')", "spojeni tabulek"),
    ],
    "Funkce, smycky, apply": [
        ("prumer <- function(v, na.rm = TRUE) mean(v, na.rm = na.rm)", "vlastni funkce"),
        ("for (i in seq_along(v)) { ... }", "smycka"),
        ("while (pocet < 10) { pocet <- pocet + 1 }", "while"),
        ("sapply(split(df$v, df$skupina), mean)", "split + apply"),
        ("tapply(df$v, df$skupina, mean)", "prumer po skupinach"),
        ("lapply(list_of_dfs, nrow)", "vrat list"),
        ("vapply(v, is.numeric, logical(1))", "s kontrolou typu"),
        ("rowSums(df); colMeans(df)", "vektorizovane misto smycky"),
    ],
    "Datum a cas": [
        ("as.Date('2026-11-03')", "datum ISO"),
        ("as.Date('03.11.2026', format = '%d.%m.%Y')", "ceske datum"),
        ("format(datum, '%Y-%m')", "textovy mesic"),
        ("seq(min(d), max(d), by = 'month')", "mesicni sekvence"),
        ("weekdays(d); months(d); quarters(d)", "den v tydnu / mesic / ctvrtleti"),
        ("as.numeric(d2 - d1)", "rozdil ve dnech"),
        ("lubridate::ymd(); lubridate::floor_date(d, 'week')", "lubridate"),
    ],
    "ggplot2": [
        ("ggplot(df, aes(x = vek, y = trzba)) + geom_point()", "bodovy graf"),
        ("+ geom_line() / geom_col() / geom_boxplot()", "cara / sloupce / krabice"),
        ("ggplot(df, aes(x = faktor, y = hodnota, fill = faktor)) + geom_boxplot()", "porovnani skupin"),
        ("+ geom_density(alpha = .3)", "hustota"),
        ("+ facet_wrap(~ pobocka)", "rozdeleni do panelu"),
        ("+ labs(x = 'vek', y = 'Kc', title = 'Trzba') + theme_minimal()", "popisky a styl"),
        ("+ scale_y_continuous(labels = scales::comma)", "formatovani osy"),
        ("ggsave('graf.png', graf, width = 8, height = 5)", "ulozeni grafu"),
    ],
    "Statistika (pozdejsi lekce)": [
        ("mean(x); median(x); sd(x); IQR(x); table(x)", "poloha a variabilita"),
        ("shapiro.test(x)", "normalita (n do 5000)"),
        ("t.test(hodnota ~ skupina, data = df)", "dvouvyberovy t-test"),
        ("wilcox.test(hodnota ~ skupina, data = df)", "neparametricka obdoba"),
        ("chisq.test(table(skupina, kategorie))", "chi-kvadrat"),
        ("cor(x, y, method = 'pearson'); cor.test(x, y)", "korelace"),
        ("model <- lm(tezky ~ vek, data = df); summary(model)", "linearni regrese"),
        ("anova(lm(...))", "rozdily mezi vice skupinami"),
    ],
}


def parse(d: str) -> date:
    return datetime.strptime(d, "%Y-%m-%d").date()


def current_lesson(today: date | None = None) -> int:
    """Která lekce kurzu právě probíhá (naposledy konaná)."""
    today = today or date.today()
    done = [n for n, l in LESSONS.items() if parse(l["date"]) <= today]
    return max(done) if done else 1


def lesson_focus(today: date | None = None) -> list[str]:
    """Dovednosti, které jsou teď aktuální: probíraná lekce + jedna předchozí."""
    n = current_lesson(today)
    focus = list(LESSONS.get(n, {}).get("skills", []))
    focus += list(LESSONS.get(max(1, n - 1), {}).get("skills", []))
    return list(dict.fromkeys(focus))
