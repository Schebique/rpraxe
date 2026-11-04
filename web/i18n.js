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
    "Nápověda": "Help", "prozkoumat": "inspect", "koncept": "draft", "schváleno": "approved",
    "schováno": "retired", "Model": "Model", "Poskytovatel": "Provider", "Adresa serveru": "Server URL",
    "API klíč": "API key", "Model pro povídání (kouč, nápovědy)": "Chat model (coach, hints)",
    "Model pro tvorbu úloh": "Task-writing model", "uložit a vyzkoušet": "save & test",
    "modelů k dispozici": "models available", "model odpovídá": "model replies",
    "model neodpovídá": "model does not reply", "uloženo, model odpovídá": "saved, model replies",
    "uloženo, ale model neodpovídá": "saved, but the model does not reply",
    "Nastavení modelu uloženo.": "Model settings saved.", "zkouším…": "testing…", "ukázat": "show",
    "nepovinný": "optional", "uloženo: ": "stored: ",
    "jednotné přihlášení je zapnuté": "single sign-on is on", "přihlašování heslem": "password sign-in",
    "přihlašovat přes bránu (SSO)": "sign in through a gateway (SSO)",
    "Hlavička s jménem uživatele": "Header with the user name",
    "Hlavička se skupinami (pro role)": "Header with groups (for roles)",
    "Tajemství brány": "Gateway secret", "uložit přihlašování": "save sign-in settings",
    "Přihlašování uloženo.": "Sign-in settings saved.", "Skupina → role (jedna na řádek, např. redakce=admin)":
      "Group → role (one per line, e.g. editors=admin)",
    "soubor": "file", "pokusy": "attempts", "naš": "tasks", "načíst": "load",
    "udělat snímek teď": "snapshot now", "Snímek uložen": "Snapshot saved", "Poslední noční záloha": "Last nightly backup",
    "zatím žádná": "none yet", "nepoužitelný": "unusable", "Obnoveno": "Restored", "pojistka": "safety copy",
    "Načíst ze zálohy": "Load from backup", "Přepisuju databázi snímkem": "Overwriting the database with snapshot",
    "ověřit spuštěním": "verify by running", "nechat zkontrolovat modelem": "ask the model to criticise",
    "Úloha detailně": "Task in detail", "kontrolní kód": "checking code", "startovací kostka": "starter code",
    "schválit a pustit do nabídky": "approve and offer it", "nechat v konceptech": "keep as draft",
    "spouštím v sandboxu…": "running in the sandbox…", "model přemýšlí…": "the model is thinking…",
    "spočítáno a zkontrolováno": "ran and checked", "Úloha neprošla": "The task failed",
    "řešení prošlo": "solution passed", "prázdný kód": "empty code", "propustil kontrolu": "passed the check",
    "propustila kontrolu": "passed the check", "vykreslil graf": "drew a plot",
    "model neshledal závadu": "the model found nothing wrong", "model našel závady": "the model found problems",
    "návrh opravené kontroly": "proposed fixed check", "návrh opraveného řešení": "proposed fixed solution",
    "model není dostupný": "the model is unavailable", "ověření se nepovedlo": "verification failed",
    "Úloha je teď: ": "Task is now: ", "pokusů": "attempts", "prošlo": "passed",
    "Model volí správce — všichni v instanci mají stejného kouče.":
      "The administrator picks the model — everyone in this instance gets the same coach.",
    "Model zatím nemá nastavený správce.": "The administrator has not set a model yet.",
    "data jdou mimo dům": "data leaves home", "data zůstávají doma": "data stays home",
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
    "Nápoveda": "Nápoveda", "prozkúmať": "preskúmať", "koncept": "návrh", "schváleno": "schválené",
    "Poskytovateľ": "Poskytovateľ", "Adresa servera": "Adresa servera", "API kľúč": "API kľúč",
    "Model": "Model", "načítať": "načítať", "súbor": "súbor", "skúšky": "pokusy",
    "uložiť a vyskúšať": "uložiť a vyskúšať", "overiť spustením": "overiť spustením",
    "nechať skontrolovať modelom": "nechať skontrolovať modelom", "riadiace heslo brány": "heslo brány",
    "jednotné prihlasovanie je zapnuté": "jednotné prihlasovanie je zapnuté",
    "Model volí správca — všetci inštancii majú rovnakého kouča.":
      "Model volí správca — všetci v inštalácii majú rovnakého kouča.",
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
    "Nápověda": "Hilfe", "prozkoumat": "prüfen", "Model": "Modell", "Poskytovatel": "Anbieter",
    "Adresa serveru": "Server-URL", "API klíč": "API-Schlüssel", "načíst": "laden", "soubor": "Datei",
    "ověřit spuštěním": "per Ausführung prüfen", "koncept": "Entwurf", "schváleno": "freigegeben",
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

/* --- Nové oddíly správy, tříd a editoru — doplněné překlady -------------
 * Zdrojový text je český; tady se pojmenovávají nové nadpisy a hlášky. */
Object.assign(I18N.en, {
  "Nápověda": "Help", "Správa": "Administration",
  "Co je tohle zač": "What this is", "Jak postupovat": "How to work through it",
  "Pro učitele a správce": "For teachers and admins", "Co jsem si zapsal": "My own notes",
  "Kde co najdu": "Where to find what", "Model, hesla a zálohy": "Model, passwords and backups",
  "Adresa serveru (endpoint)": "Server address (endpoint)",
  "Model pro povídání (kouč, nápovědy)": "Chat model (coach, hints)",
  "Model pro tvorbu úloh": "Model for writing tasks",
  "uložit a vyzkoušet": "save and test", "model odpovídá": "model answers",
  "model neodpovídá": "model does not answer", "modelů stažených na adrese výše": "models listed at the address above",
  "vyplň, pokud ho poskytovatel vyžaduje": "fill in if your provider requires one",
  "povinný": "required", "nepovinný": "optional",
  "bez klíče to nefunguje": "it will not work without a key", "nechat prázdné": "leave it empty",
  "Adresa se píše takto": "The address looks like this",
  "uloženo, model odpovídá": "saved, the model answers",
  "uloženo, ale model neodpovídá": "saved, but the model does not answer",
  "Tenhle poskytovatel klíč vyžaduje — bez něj to nebude mluvit.":
    "This provider requires an API key — nothing will work without it.",
  "Nastavení modelu uloženo.": "Model settings saved.",
  "Přihlašovat přes bránu (SSO)": "Sign in through a gateway (SSO)",
  "zapnuto — účet se založí sám podle hlavičky": "on — accounts are created from the header",
  "vypnuto — přihlašuje se heslem": "off — passwords are used",
  "Hlavička s jménem uživatele": "Header with the user name",
  "Hlavička se skupinami (pro role)": "Header with groups (for roles)",
  "Heslo brány (shared secret)": "Gateway shared secret",
  "uloženo: ": "stored: ", "vygeneruj a vlož i do brány": "generate one and put the same value in the gateway",
  "vygenerovat heslo brány": "generate a gateway secret", "hlavička s heslem": "secret header",
  "Skupina → role (jeden na řádek, např. pedagogove=teacher)":
    "Group → role (one per line, e.g. teachers=teacher)",
  "účty": "accounts", "Co přišlo v tomto požadavku": "What arrived in this request",
  "Jak to nastavit v bráně (Authelia, Caddy…)": "How to set this up in the gateway (Authelia, Caddy…)",
  "uložit přihlašování": "save sign-in settings", "Přihlašování uloženo.": "Sign-in settings saved.",
  "Stejné heslo vlož i do nastavení brány.": "Put the same secret into the gateway configuration too.",
  "Přihlášení bránou": "Gateway sign-in", "přihlásit se přes bránu": "sign in through the gateway",
  "Zálohy a obnova": "Backups and restore", "Okamžik, kopíruji databázi…": "Hold on, copying the database…",
  "Okamžik, obnovuji…": "Hold on, restoring…", "Záloha hotova.": "Backup done.",
  "Tohle je pojistka před obnovou — nemaž ji.": "This is the pre-restore copy — do not delete it.",
  "obnovit": "restore", "obnovit zálohu": "restore a backup", "Záloha": "Backup",
  "Pojistka před obnovou": "Pre-restore copy", "Pozor, obnova přepíše současnou databázi.":
    "Careful — restoring overwrites the current database.",
  "Aplikace se pak sama restartuje.": "The app restarts itself afterwards.",
  "Aplikace se pak sama restartuje": "The app restarts itself afterwards",
  "Žáci": "Students", "Celkem": "Total", "Průměrná úspěšnost": "Average success",
  "celkem": "total", "průměrná úspěšnost": "average success", "bez dat": "no data",
  "Žáci nejsou žádní.": "No students yet.",
  "Třídy": "Classes", "načítám…": "loading…", "zatím žádný studentský účet": "no student accounts yet",
  "cizí": "other teacher", "učitel": "teacher", "žáků": "students", "zatím bez žáků": "no students yet",
  "Zatím žádná třída — založ první níže.": "No classes yet — create the first one below.",
  "začít novou třídu": "start a new class", "uložit třídu": "save class", "smazat vybranou": "delete selected",
  "Třída uložena": "Class saved", "Třída smazána": "Class deleted", "Smazat třídu": "Delete class",
  "Vyber třídu, kterou chceš smazat.": "Pick the class you want to delete.",
  "název třídy": "class name", "poznámka (nepovinná)": "note (optional)", "žáci ve třídě": "students in the class",
  "spouštím v sandboxu a nechám to číst modelem…": "running it in the sandbox and letting the model read it…",
  "ověřuji spuštěním…": "verifying by running it…", "server nedostupný": "server unreachable",
  "úloha": "task", "uložena a schválena": "saved and approved",
  "uloženo jako koncept — studenti ji nevidí": "saved as a draft — students cannot see it",
  "uložení se nezdařilo": "saving failed", "výstup řešení": "solution output", "model:": "model:",
  "obtížnost": "difficulty", "upravit v editoru": "edit in the editor",
  "nechat v konceptech": "keep as a draft", "schválit a pustit do nabídky": "approve and publish",
  "nechat úlohu před uložením zkontrolovat i modelem (trvá déle)":
    "let the model review the task before saving (takes longer)",
});

Object.assign(I18N.sk, {
  "Nápoveda": "Nápoveda", "Nápověda": "Nápoveda", "Správa": "Správa",
  "Třídy": "Triedy", "Žáci": "Žiaci", "Zálohy a obnova": "Zálohy a obnova",
  "obnovit": "obnoviť", "obnovit zálohu": "obnoviť zálohu", "Záloha": "Záloha",
  "Pozor, obnova přepíše současnou databázi.": "Pozor, obnova prepíše súčasnú databázu.",
  "Poskytovatel": "Poskytovateľ", "Adresa serveru (endpoint)": "Adresa servera (endpoint)",
  "Model pro povídání (kouč, nápovědy)": "Model na rozhovor (kouč, nápovedy)",
  "Model pro tvorbu úloh": "Model na tvorbu úloh", "uložit a vyzkoušet": "uložiť a vyskúšať",
  "povinný": "povinný", "nepovinný": "nepovinný",
  "Přihlašovat přes bránu (SSO)": "Prihlasovať cez bránu (SSO)",
  "Heslo brány (shared secret)": "Heslo brány (shared secret)",
  "vygenerovat heslo brány": "vygenerovať heslo brány",
  "uložit přihlašování": "uložiť prihlasovanie", "Přihlašování uloženo.": "Prihlasovanie uložené.",
  "začít novou třídu": "začať novou triedu", "uložit třídu": "uložiť triedu",
  "smazat vybranou": "vymazať vybranú", "Třída uložena": "Trieda uložená",
  "spouštím v sandboxu a nechám to číst modelem…": "spúšťam v sandboxu a nechám to čítať modelom…",
  "ověřuji spuštěním…": "overujem spustením…", "obtížnost": "ťažkosť",
  "upravit v editoru": "upraviť v editore", "nechat v konceptech": "nechať v konceptoch",
});

Object.assign(I18N_ATTR, {
  en: Object.assign({}, I18N_ATTR.en, {
    "uloženo — studenti ji nevidí": "saved — invisible to students",
    "např. Skupina A — úterý": "e.g. Group A — Tuesdays",
    "vyplň, pokud ho poskytovatel vyžaduje": "fill in if your provider requires one",
    "vygeneruj a vlož i do brány": "generate one and put it in the gateway too",
    "jméno modelu, např. qwen3.5:9b": "model name, e.g. qwen3.5:9b",
  }),
  sk: Object.assign({}, I18N_ATTR.sk, {
    "uloženo — studenti ji nevidí": "uložené — žiaci to nevidia",
    "např. Skupina A — úterý": "napr. Skupina A — utorok",
  }),
});

Object.assign(I18N.en, {
  "žáci ve třídě — klikni, kdo do ní patří": "students in the class — click who belongs",
  "smazat třídu": "delete class", "Opravdu smazat třídu": "Really delete the class",
  "Napiš aspoň název třídy.": "At least write a class name.",
  "Vytvořit vlastní úlohu": "Write your own task", "Vlastní úloha": "Own task",
  "Nová úloha": "New task", "Úprava úlohy": "Editing task", "žáků": "students",
  "Učitel může mít tříd víc a stejného žáka zařadit do dvou. Třídu smažeš tlačítkem u ní.":
    "A teacher can run several classes and put the same student in two of them. Delete a class with its button.",
});
Object.assign(I18N.sk, {
  "smazat třídu": "zmazať triedu", "Opravdu smazat třídu": "Naozaj zmazať triedu",
  "Vytvořit vlastní úlohu": "Vytvoriť vlastnú úlohu", "Vlastní úloha": "Vlastná úloha",
  "Nová úloha": "Nová úloha", "Úprava úlohy": "Úprava úlohy",
});

Object.assign(I18N.en, {
  "Vlastní úlohy": "Your own tasks",
  "Úlohu napsat nebo upravit jde z dialogu — ať jsi kdekoli. Uložit se dá jen taková, která projde vlastním řešením.":
    "The editor is a dialog, so it opens from anywhere. Only a task that passes its own solution can be saved.",
  "Vlastní banka na GitHubu": "Your own task bank on GitHub",
  "načíst z GitHubu": "load from GitHub",
  "stahuji a přezkouším…": "downloading and re-checking…",
  "přeneseno": "imported", "schváleno": "approved", "koncept": "draft", "schováno": "retired",
  "Vlož odkaz na repozitář nebo na soubor ukoly.json.": "Paste a repository link or a link to ukoly.json.",
  "nechat opravit modelem": "let the model fix it",
  "model přepisuje úlohu, ať projde…": "the model is rewriting the task so that it passes…",
  "přepsáno a ověřeno": "rewritten and verified",
  "po přepsání to pořád neprochází": "it still does not pass after the rewrite",
  "Napiš aspoň název třídy.": "Write at least a class name.",
  "Opravdu smazat třídu": "Really delete the class",
  "smazat": "delete",
});

Object.assign(I18N.sk, {
  "Vlastní úlohy": "Vlastné úlohy", "Vlastní banka na GitHubu": "Vlastná banka úloh na GitHube",
  "načíst z GitHubu": "načítať z GitHubu", "nechat opravit modelem": "nechať opraviť modelom",
  "přeneseno": "preneseno", "koncept": "koncept", "smazat": "zmazať",
});

Object.assign(I18N.en, {
  "zahodit": "discard", "obnovit": "restore", "zahozeno": "discarded",
  "tvůj koncept": "your draft", "+ vlastní úlohu": "+ write your own",
  "nahrát data": "upload data", "nahávám data…": "uploading data…",
  "data nahrána": "data uploaded", "do dneška": "add to today",
  "úloha je zpátky": "the task is back", "_banka_dat": "Data bank",
});

Object.assign(I18N.sk, {
  "zahodit": "zahodiť", "obnovit": "obnoviť", "zahozeno": "zahodené",
  "tvůj koncept": "tvoj koncept", "+ vlastní úlohu": "+ vlastná úloha",
  "nahrát data": "nahrať dáta", "do dneška": "do dneška",
  "úloha je zpátky": "úloha je späť",
});
