"""Lekce 6-7 — vizualizace (zakladni plot i ggplot2)."""

TASKS = [
    {
        "id": "viz-01",
        "title": "Bodovy graf zakladnimi prikazy",
        "lesson": 6, "minutes": 3, "level": 2,
        "skills": ["vizualizace", "plot"],
        "dataset": "mzdy.csv",
        "nacti": 'mzdy <- read.csv("mzdy.csv", stringsAsFactors = FALSE)',
        "zadani": ("Nakresli bodovy graf vztahu `praxe_roky` (osa x) a `plat_kc` (osa y)\n"
                   "pomoci `plot()`. Popisky os dopln přes `xlab` a `ylab`."),
        "starter": "# zatím prázdné\n",
        "hints": [
            "`plot(mzdy$praxe_roky, mzdy$plat_kc, xlab = \"praxe (roky)\", ylab = \"plat (Kc)\")`",
            "Nemusíš nic vracet — stačí, aby graf proběhl bez chyby.",
        ],
        "check": '.v_plot(msg_ok = "Graf je na světě. Všimni si, jaká je to mračina bodů — na to existuje ggplot.")\n',
        "reseni": 'plot(mzdy$praxe_roky, mzdy$plat_kc, xlab = "praxe (roky)", ylab = "plat (Kc)", pch = 16, col = rgb(0, 0, 0, .4))\n',
        "needs_plot": True,
    },
    {
        "id": "viz-02",
        "title": "Prvni ggplot",
        "lesson": 6, "minutes": 4, "level": 2,
        "skills": ["vizualizace", "ggplot2", "geom_point"],
        "libraries": ["ggplot2"],
        "dataset": "mzdy.csv",
        "nacti": 'mzdy <- read.csv("mzdy.csv", stringsAsFactors = FALSE)',
        "zadani": ("Postav ggplot: `graf <- ggplot(mzdy, aes(x = praxe_roky, y = plat_kc)) + geom_point()`.\n"
                   "Výsledek pojmenuj `graf` (kontrola se ptá na něj)."),
        "starter": "library(ggplot2)\ngraf <- ggplot( ) +\n\n",
        "hints": [
            "`ggplot(mzdy, aes(x = praxe_roky, y = plat_kc)) + geom_point()`",
            "Všimni si rozdílu: `aes()` mapuje proměnné, `geom_*()` kreslí.",
        ],
        "check": 'if (!exists("graf")) .v_spam("Nenašel jsem objekt `graf`.")\n.v_plot(get("graf"))',
        "reseni": 'graf <- ggplot(mzdy, aes(x = praxe_roky, y = plat_kc)) + geom_point()\n',
        "needs_plot": True,
    },
    {
        "id": "viz-03",
        "title": "Barvovy graf podle skupiny",
        "lesson": 6, "minutes": 4, "level": 2,
        "skills": ["vizualizace", "ggplot2", "geom_col"],
        "libraries": ["ggplot2", "dplyr"],
        "dataset": "kavarna.csv",
        "nacti": 'kavarna <- read.csv("kavarna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Spočti tržbu podle nápoje a vykresli sloupcový graf. Ulož ho do `graf` a jako\n"
                   "ose x použij nápoj seřazený podle tržby (pomocí `fct_reorder`)."),
        "starter": "library(ggplot2)\nlibrary(dplyr)\ntrzba <- kavarna %>% group_by(napoj) %>% summarise(trzba = sum(trzba, na.rm = TRUE))\n\n",
        "hints": [
            "`mutate(napoj = forcats::fct_reorder(napoj, trzba))`",
            "`ggplot(trzba, aes(x = napoj, y = trzba)) + geom_col()`",
        ],
        "check": 'if (!exists("graf")) .v_spam("Chybi `graf`.")\n.v_plot(get("graf"), msg_ok = "Jo — a všimni si, že seřazené sloupce se čtou mnohem líp.")',
        "reseni": ('trzba <- kavarna %>%\n'
                   '  group_by(napoj) %>%\n'
                   '  summarise(trzba = sum(trzba, na.rm = TRUE), .groups = "drop") %>%\n'
                   '  mutate(napoj = forcats::fct_reorder(napoj, trzba))\n'
                   'graf <- ggplot(trzba, aes(x = napoj, y = trzba)) + geom_col() + labs(x = NULL, y = "tržba (Kč)")\n'),
        "needs_plot": True,
    },
    {
        "id": "viz-04",
        "title": "Boxplot podskupin",
        "lesson": 7, "minutes": 5, "level": 3,
        "skills": ["vizualizace", "ggplot2", "geom_boxplot"],
        "libraries": ["ggplot2"],
        "dataset": "skolni_zahrada.csv",
        "nacti": 'zahrada <- read.csv("skolni_zahrada.csv", stringsAsFactors = TRUE)',
        "zadani": ("Udělej boxplot výšek (`vyska_cm`) podle `osetreni`, s barvou podle ošetření\n"
                   "a popiskem os. Ulož do `graf`."),
        "starter": "library(ggplot2)\ngraf <- ggplot(zahrada, aes(x = , y = )) +\n\n",
        "hints": [
            "`aes(x = osetreni, y = vyska_cm, fill = osetreni)`",
            "`+ geom_boxplot() + labs(x = \"ošetření\", y = \"výška (cm)\")`",
        ],
        "check": 'if (!exists("graf")) .v_spam("Chybi `graf`.")\n.v_plot(get("graf"))',
        "reseni": ('graf <- ggplot(zahrada, aes(x = osetreni, y = vyska_cm, fill = osetreni)) +\n'
                   '  geom_boxplot() + labs(x = "ošetření", y = "výška (cm)") + theme(legend.position = "none")\n'),
        "needs_plot": True,
    },
    {
        "id": "viz-05",
        "title": "Casova rada s klouzavym prumerem",
        "lesson": 7, "minutes": 6, "level": 4,
        "skills": ["vizualizace", "casove_radky", "geom_line"],
        "libraries": ["ggplot2", "dplyr"],
        "dataset": "teplota_praha.csv",
        "nacti": 'teplota <- read.csv("teplota_praha.csv", stringsAsFactors = FALSE)',
        "zadani": ("Vykresli denní `teplot_prum` jako čáru a přidž klouzavý průměr po 30 dnech\n"
                   "(sloupec `kl30`). Ulož do `graf`."),
        "starter": 'library(ggplot2)\nlibrary(dplyr)\nteplota$datum <- as.Date(teplota$datum)\n\n',
        "hints": [
            "`teplota$kl30 <- zoo::rollmeanr(teplota$teplot_prum, 30, fill = NA)` — nebo ručně `filter()` + `mean()` ve `mutate()`.",
            "`geom_line(aes(x = datum, y = teplot_prum), alpha = .3) + geom_line(aes(y = kl30), linewidth = 1)`",
        ],
        "check": 'if (!exists("graf")) .v_spam("Chybi `graf`.")\n.v_plot(get("graf"), msg_ok = "Paráda. Přesně tohle se v kurzu dělá u časových řad.")',
        "reseni": ('teplota$kl30 <- filter(teplota, !is.na(teplot_prum)) %>%\n'
                   '  mutate(kl30 = mean(teplot_prum)) %>% pull(kl30)\n'
                   'klouzavy <- numeric(nrow(teplota))\n'
                   'for (i in seq_along(klouzavy)) {\n'
                   '  okno <- max(1, i - 29):i\n  klouzavy[i] <- mean(teplota$teplot_prum[okno], na.rm = TRUE)\n}\n'
                   'teplota$kl30 <- klouzavy\n'
                   'graf <- ggplot(teplota, aes(x = datum, y = teplot_prum)) +\n'
                   '  geom_line(alpha = .25) + geom_line(aes(y = kl30), color = "firebrick", linewidth = 1) +\n'
                   '  labs(x = NULL, y = "teplota (°C)", title = "Denní teplota a 30denní průměr")\n'),
        "needs_plot": True,
    },
    {
        "id": "viz-06",
        "title": "Histogram a hustota",
        "lesson": 7, "minutes": 4, "level": 3,
        "skills": ["vizualizace", "geom_histogram", "deskriptiva"],
        "libraries": ["ggplot2"],
        "dataset": "mzdy.csv",
        "nacti": 'mzdy <- read.csv("mzdy.csv", stringsAsFactors = FALSE)',
        "zadani": ("Vykresli histogram `plat_kc` (30 binů) a přidej křivku hustoty\n"
                   "(`geom_density(aes(y = after_stat(density)))`). Ulož do `graf`."),
        "starter": "library(ggplot2)\ngraf <- ggplot(mzdy, aes(x = plat_kc)) +\n\n",
        "hints": [
            "`geom_histogram(bins = 30)`",
            "`+ geom_density(aes(y = after_stat(density)), color = \"darkorange\")`",
        ],
        "check": 'if (!exists("graf")) .v_spam("Chybi `graf`.")\n.v_plot(get("graf"))',
        "reseni": ('graf <- ggplot(mzdy, aes(x = plat_kc)) +\n'
                   '  geom_histogram(bins = 30, fill = "grey70") +\n'
                   '  geom_density(aes(y = after_stat(density)), color = "darkorange", linewidth = 1)\n'),
        "needs_plot": True,
    },
    {
        "id": "viz-07",
        "title": "Vice grafu najednou: facet_wrap",
        "lesson": 7, "minutes": 6, "level": 4,
        "skills": ["vizualizace", "facet_wrap", "ggplot2"],
        "libraries": ["ggplot2"],
        "dataset": "kavarna.csv",
        "nacti": 'kavarna <- read.csv("kavarna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Udělej boxplot ceny za kus podle velikosti, rozdělený do panelů podle pobočky\n"
                   "(`facet_wrap(~ pobocka)`). Ulož do `graf`."),
        "starter": "library(ggplot2)\ngraf <- ggplot(kavarna, aes(x = velkost, y = cena_ks)) +\n\n",
        "hints": [
            "`+ geom_boxplot() + facet_wrap(~ pobocka)`",
            "Pomůže `theme_minimal()` a `labs(x = NULL, y = \"cena za kus (Kč)\")`.",
        ],
        "check": 'if (!exists("graf")) .v_spam("Chybi `graf`.")\n.v_plot(get("graf"))',
        "reseni": ('graf <- ggplot(kavarna, aes(x = velkost, y = cena_ks, fill = velkost)) +\n'
                   '  geom_boxplot() + facet_wrap(~ pobocka) + theme_minimal() +\n'
                   '  labs(x = NULL, y = "cena za kus (Kč)") + theme(legend.position = "none")\n'),
        "needs_plot": True,
    },
    {
        "id": "viz-08",
        "title": "Scatter s barvou a velikosti",
        "lesson": 6, "minutes": 5, "level": 3,
        "skills": ["vizualizace", "aes", "ggplot2"],
        "libraries": ["ggplot2"],
        "dataset": "dojizdka.csv",
        "nacti": 'dojizdka <- read.csv("dojizdka.csv", stringsAsFactors = FALSE)',
        "zadani": ("Bodový graf: x = `vzdalenost_km`, y = `cas_min`, barva = `doprava`,\n"
                   "velikost bodu = `pocet_zaku`. Výsledek do `graf`."),
        "starter": "library(ggplot2)\ngraf <- ggplot(dojizdka, aes( )) +\n\n",
        "hints": [
            "`aes(x = vzdalenost_km, y = cas_min, color = doprava, size = pocet_zaku)`",
            "`+ geom_point(alpha = .7)`",
        ],
        "check": 'if (!exists("graf")) .v_spam("Chybi `graf`.")\n.v_plot(get("graf"), msg_ok = "Tohle je graf, který má smysl: vidíš, že cyklisté mají krátké vzdálenosti.")',
        "reseni": ('graf <- ggplot(dojizdka, aes(x = vzdalenost_km, y = cas_min, color = doprava, size = pocet_zaku)) +\n'
                   '  geom_point(alpha = .7) + theme_minimal() + labs(x = "vzdálenost (km)", y = "čas (min)")\n'),
        "needs_plot": True,
    },
    {
        "id": "viz-09",
        "title": "Violin a hustota spolu",
        "lesson": 7, "minutes": 5, "level": 4,
        "skills": ["vizualizace", "geom_violin", "geom_density"],
        "libraries": ["ggplot2"],
        "dataset": "skolni_zahrada.csv",
        "nacti": 'zahrada <- read.csv("skolni_zahrada.csv", stringsAsFactors = TRUE)',
        "zadani": ("Porovnej rozložení `vyska_cm` mezi ošetřeními pomocí `geom_violin()`\n"
                   "a přidej mediánové čáry (`geom_boxplot(width = .1)`). Do `graf`."),
        "starter": "library(ggplot2)\ngraf <- ggplot(zahrada, aes(x = osetreni, y = vyska_cm, fill = osetreni)) +\n\n",
        "hints": [
            "`+ geom_violin(alpha = .6) + geom_boxplot(width = .12)`",
            "`theme_minimal()` a `labs()` dokončí obrázek.",
        ],
        "check": 'if (!exists("graf")) .v_spam("Chybi `graf`.")\n.v_plot(get("graf"))',
        "reseni": ('graf <- ggplot(zahrada, aes(x = osetreni, y = vyska_cm, fill = osetreni)) +\n'
                   '  geom_violin(alpha = .6) + geom_boxplot(width = .12, outlier.shape = NA) +\n'
                   '  theme_minimal() + labs(x = "ošetření", y = "výška (cm)") + theme(legend.position = "none")\n'),
        "needs_plot": True,
    },
    {
        "id": "viz-10",
        "title": "Graf ulozit na disk",
        "lesson": 6, "minutes": 3, "level": 2,
        "skills": ["vizualizace", "ggsave"],
        "libraries": ["ggplot2"],
        "dataset": "knihovna.csv",
        "nacti": 'knihovna <- read.csv("knihovna.csv", stringsAsFactors = FALSE)',
        "zadani": ("Vytvoř sloupcový graf počtu výpůjček podle žánru a ulož ho\n"
                   "`ggsave(\"vystup.png\", width = 7, height = 4)`. Graf musí existet jako `graf`."),
        "starter": "library(ggplot2)\nlibrary(dplyr)\n\n",
        "hints": [
            "`count(knihovna, zanr) %>% ggplot(aes(zanr, n)) + geom_col()`",
            "`ggsave(\"vystup.png\", graf, width = 7, height = 4)`",
        ],
        "check": 'if (!exists("graf")) .v_spam("Chybi objekt `graf`.")\n.v_plot(get("graf"), msg_ok = "A soubor `vystup.png` je na disku. Přesně takhle se grafy odevzdávají.")',
        "reseni": ('graf <- count(knihovna, zanr) %>% ggplot(aes(x = zanr, y = n)) + geom_col(fill = "steelblue") +\n'
                   '  labs(x = NULL, y = "výpůjčky")\nggsave("vystup.png", graf, width = 7, height = 4)\n'),
        "needs_plot": True,
    },
]
