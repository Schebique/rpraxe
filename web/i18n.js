/* Překlady rozhraní. Zdrojový text je český (kurz je česky), slovník překládá
 * přesně shodné řeči. Přidat jazyk = přidat řádek sem; nic dalšího se nemění.
 *
 * Obsahuje jen rozhraní. Zadání úloh zůstává v jazyce banky — ta se překládá
 * jako obsah (sloupec `lang` v bance), ne slovníkem. */
const I18N = {
  cs: {},
  en: {
    "Dnes": "Today", "Knihovna": "Library", "Progres": "Progress", "Tahák": "Cheat sheet",
    "Třída": "Class", "Změnit heslo": "Change password", "Nastavení": "Settings",
    "Správa": "Administration", "odhlásit": "sign out", "dnes": "today",
    "nová dávka": "new set", "Řešení": "Solution", "zkontrolovat ✓": "check ✓", "spustit ▸": "run ▸",
    "napověda": "hint", "zapsat poznámku": "add note",
    "dávka": "set", "min": "min", "lekce": "lesson", "kurz": "course",
    "hotovo": "done", "Dnešní úlohy": "Today's tasks", "tvůj R kód": "your R code",
    "výstup se objeví tady…": "output appears here…", "výstup": "output",
    "zadání": "task", "data": "data", "vyber úlohu": "pick a task",
    "Počkej…": "Working…", "počkej…": "working…",
    "Úspěšnost na první dobrou": "First-try success", "bez nápovědy a bez opakování": "no hints, no repeats",
    "Vyplněné úlohy": "Tasks completed", "Řada": "Streak", "dní za sebou": "days in a row",
    "Odklikáno": "Time spent", "celkem v systému": "total in the app",
    "dní procvičování": "days of practice", "Posledních 30 dní": "Last 30 days",
    "Dovednosti (odhad úrovně)": "Skills (estimated level)", "Kde se to zadrhává": "Where you get stuck",
    "Tvoje poznámky": "Your notes", "Posledních 25 pokusů": "Last 25 attempts",
    "Pokud narazíš na chybu": "If you hit an error",
    "kdy": "when", "úloha": "task", "výsledek": "result", "nápovědy": "hints",
    "stáhnout CSV (celá historie)": "download CSV (full history)",
    "Nastavení účtu": "Account settings", "motiv": "theme", "jazyk": "language",
    "délka dávky": "daily set", "model kouče": "coach model",
    "Systémový (tmavý)": "System (dark)", "Světlý": "Light", "Tmavý": "Dark",
    "Výchozí": "Default", "uložit": "save", "zrušit": "cancel", "smazat": "delete",
    "Poznámka k úloze": "Note for this task", "Tvoje poznámka k téhle úloze": "Your note for this task",
    "zapsáno": "written", "Žáci": "Students", "Naposledy": "Last seen", "Úspěšnost": "Success rate",
    "Odklikáno celkem": "Total time", "Řada dní": "Day streak", "Dnes splněno": "Done today",
    "nic": "none", "Zobrazit": "Show", "zapisuje…": "writing…", "ověřeno spuštěním": "verified by running",
    "ověřit": "to verify", "do dneška": "add to today", "Uložit jako koncept": "Save as draft",
    "Uložit a ověřit": "Save and verify", "Nová úloha": "New task", "titulek": "title",
    "znaků": "characters", "Áčko": "A grade", "B": "B grade", "C": "C grade",
    "Přihlášen jako": "Signed in as", "Role": "Role",
  },
  sk: {
    "Dnes": "Dnes", "Knihovna": "Knižnica", "Progres": "Progres", "Tahák": "Tahák",
    "Třída": "Trieda", "Změnit heslo": "Zmeniť heslo", "Nastavení": "Nastavenia",
    "odhlásit": "odhlásiť", "nová dávka": "nová dávka", "Řešení": "Riešenie",
    "zkontrolovat ✓": "skontrolovať ✓", "spustit ▸": "spustiť ▸", "napověda": "napoveda",
    "zapsat poznámku": "zapísať poznámku", "dnes": "dnes", "min": "min", "lekce": "lekcia",
    "kurz": "kurz", "hotovo": "hotovo", "Dnešní úlohy": "Dnešné úlohy",
    "výstup se objeví tady…": "výstup sa objaví tu…", "zadání": "zadanie", "data": "dáta",
    "vyber úlohu": "vyber úlohu", "dávka": "dávka",
    "Úspěšnost na první dobrou": "Úspešnosť na prvýkrát", "Vyplněné úlohy": "Splnené úlohy",
    "Řada": "Séria", "dní za sebou": "dní po sebe", "Odklikáno": "Nadané",
    "celkem v systému": "spolu v apke", "Posledních 30 dní": "Posledných 30 dní",
    "Dovednosti (odhad úrovně)": "Zručnosti (odhad úrovne)", "Kde se to zadrhává": "Kde sa to zasekáva",
    "Tvoje poznámky": "Tvoje poznámky", "Posledních 25 pokusů": "Posledných 25 pokusov",
    "kdy": "kedy", "úloha": "úloha", "výsledek": "výsledok", "nápovědy": "napovedy",
    "motiv": "motív", "jazyk": "jazyk", "délka dávky": "dĺžka dávky", "model kouče": "model kouča",
    "Světlý": "Svetlý", "Tmavý": "Tmavý", "Výchozí": "Predvolený", "uložit": "uložiť",
    "zrušit": "zrušiť", "smazat": "zmazať", "Žáci": "Žiaci", "Naposledy": "Naposledy",
    "Úspěšnost": "Úspešnosť", "Řada dní": "Séria dní", "Dnes splněno": "Dnes splnené",
    "nic": "nič", "Zobrazit": "Zobraziť", "znaků": "znakov",
  },
  de: {
    "Dnes": "Heute", "Knihovna": "Bibliothek", "Progres": "Fortschritt", "Tahák": "Spickzettel",
    "Třída": "Klasse", "Změnit heslo": "Passwort ändern", "Nastavení": "Einstellungen",
    "odhlásit": "abmelden", "nová dávka": "neue Aufgabe", "Řešení": "Lösung",
    "zkontrolovat ✓": "prüfen ✓", "spustit ▸": "ausführen ▸", "napověda": "Hinweis",
    "zapsat poznámku": "Notiz anlegen", "dnes": "heute", "min": "Min", "lekce": "Lektion",
    "kurz": "Kurs", "hotovo": "erledigt", "Dnešní úlohy": "Heutige Aufgaben",
    "výstup se objeví tady…": "Ausgabe erscheint hier…", "zadání": "Aufgabe", "data": "Daten",
    "vyber úlohu": "Aufgabe wählen", "dávka": "Pensum",
    "Úspěšnost na první dobrou": "Erfolg im ersten Versuch", "Vyplněné úlohy": "Gelöste Aufgaben",
    "Řada": "Serie", "dní za sebou": "Tage in Folge", "Odklikáno": "Zeit",
    "celkem v systému": "gesamt in der App", "Posledních 30 dní": "Letzte 30 Tage",
    "Dovednosti (odhad úrovně)": "Fähigkeiten (geschätzt)", "Kde se to zadrhává": "Wo es hakt",
    "Tvoje poznámky": "Deine Notizen", "Posledních 25 pokusů": "Letzte 25 Versuche",
    "kdy": "wann", "úloha": "Aufgabe", "výsledek": "Ergebnis", "nápovědy": "Hinweise",
    "motiv": "Design", "jazyk": "Sprache", "délka dávky": "Pensum", "model kouče": "Coach-Modell",
    "Světlý": "Hell", "Tmavý": "Dunkel", "Výchozí": "Standard", "uložit": "speichern",
    "zrušit": "abbrechen", "smazat": "löschen", "Žáci": "Schülerinnen", "Naposledy": "Zuletzt",
    "Úspěšnost": "Erfolgsquote", "Řada dní": "Tagesserie", "Dnes splněno": "Heute erledigt",
    "nic": "keine", "Zobrazit": "Anzeigen", "znaků": "Zeichen",
  },
};

/* slovník pro placeholdery (překlad atributu, ne textového uzlu) */
const I18N_ATTR = {
  en: {
    "hledat v názvu/zadání…": "search title or task…",
    "co mě tu mrzelo, na co si dát příště pozor…": "what tripped me up, what to remember next time…",
    "např. group_by, na.rm": "e.g. group_by, na.rm",
  },
  sk: {
    "hledat v názvu/zadání…": "hľadať v názve/zadaní…",
    "co mě tu mrzelo, na co si dát příště pozor…": "čo ma tu napálilo, na čo si dať pozor…",
  },
  de: {
    "hledat v názvu/zadání…": "Titel oder Aufgabe suchen…",
    "co mě tu mrzelo, na co si dát příště pozor…": "worüber ich gestolpert bin…",
  },
};

let LANG = "cs";

function t(text) {
  const s = String(text ?? "");
  return (I18N[LANG] && I18N[LANG][s]) || s;
}

/**
 * Přeloží statický text v DOM: textové uzly i placeholder. Zdroj je vždy
 * česky, takže si ke každému uzlu pamatujeme originál (`__cs`) — díky tomu
 * přepnutí zpátky do češtiny text vrátí, ne nechá viset v cizím jazyce.
 */
function translateDom(root) {
  if (!root) return;
  const dict = I18N[LANG] || {}, attrs = I18N_ATTR[LANG] || {};
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
  const nodes = [];
  let node;
  while ((node = walker.nextNode())) nodes.push(node);
  for (const n of nodes) {
    if (n.parentElement && ["SCRIPT", "STYLE", "CODE", "PRE"].includes(n.parentElement.tagName)) continue;
    if (typeof n.__cs !== "string") n.__cs = n.nodeValue;
    const key = (n.__cs || "").trim();
    if (!key || key.length > 70) continue;
    const preklad = dict[key];
    const nova = preklad ? n.__cs.replace(key, preklad) : n.__cs;
    // přiřazujeme jen při změně — jinak by observer videl změnu donekonečna
    if (n.nodeValue !== nova) n.nodeValue = nova;
  }
  if (root.querySelectorAll) {
    root.querySelectorAll("[placeholder]").forEach(el => {
      if (typeof el.dataset.csPlaceholder !== "string") el.dataset.csPlaceholder = el.placeholder || "";
      el.placeholder = attrs[el.dataset.csPlaceholder] || el.dataset.csPlaceholder || "";
    });
  }
}
