# Nápověda / Help

Stručná verze tychle textů je přímo v aplikaci (menu **Nápověda**,
`web/app.js`, objekt `HELP`). Tenhle soubor je rozšířená verze pro čtení
v repozitáři. Když se změní chování aplikace, aktualizuje se obojí.

## Česká verze

### Denní rutina
1. Záložka **Dnes** namíchá krátkou dávku úloh z látky, kterou zrovna probíráte.
   Je záměrně krátká — 15 až 30 minut. Pravidelnost je důležitější než objem.
2. U úlohy je zadání, náhled dat a okno pro R kód. **spustit ▸** kód nechá
   spočítat, **zkontrolovat ✓** změří, jestli splňuje zadání.
3. **napověda** odkrývá nápovědu po kouskách. Tlačítko **kouč** vysvětlí
   konkrétní chybu, kterou vypsalo R.
4. **Řešení** se ukáže až na požádání a jeho otevření se zapíše do historie.
   Počítá se jako nápověda, takže ho pak radši přepiš bez pohledu.

### Kde co najdeš
- **Knihovna** — všechny úlohy; filtr na lekci a status, hledání v textu.
  Tlačítkem *do dneška* si úlohu přidáš do vlastní dávky.
- **Progres** — úspěšnost na první dobrou, řada dní, odhady dovedností
  (každý účet zvlášť), témata kde se to zadrhává, historie a CSV export.
- **Tahák** — rychlý opis základů R, zůstává na stránce. Žádná popup okna.
- **Poznámky** — vlastní poznámka k úloze ve větším okně, uložená na serveru,
  takže ji uvidíš i z jiného počítače.

### K čemu jsou poznámky
Poznámka u úlohy není hodnocení ani vzkaz učiteli — je to vlastní záznam vedle
konkrétní úlohy: co napálilo, na co si příště dát pozor. Hodnotu má proto, že
za měsíc si nikdo neneše, v čem tehdy chyboval; u úlohy, která trvala půl
hodiny, je řádek „pozor, `group_by` počítá i řádky s `NA`“ to nejcennější, co
systém uchová. Učitel a správce je vidí v přehledu třídy, takže poznají, kde
skupina zápasí, i když počet pokusů vypadá dobře. Kouč je nedostává — zůstávají
tvůj text.

### Nastavení účtu
Motiv (tmavý / světlý / systémový), jazyk rozhraní a délka denní dávky.
Ukládá se do databáze, takže platí i na jiném zařízení.
**Model si uživatel nevolí** — nastavuje ho správce ve správě instance.

### Třídy
Tříd může být několik — klidne se stejnými žáky v různých skupinách (ranní a
odpolední kurz) a se stejnými nebo různými učiteli. Učitel si založí vlastní a
vybere do ní účty; jeden účet může patřit do několika tříd. V záložce Třída je
karta **Třídy**: název, poznámka, výběr žáků (Ctrl/Cmd vybere víc), uložení.
Vybranou třídu lze upravit nebo smazat — účty zůstanou, zmizí jen sdružení.
Přehled žáků ukazuje, v jakých třídách kdo je. Nová instance dostane jednu
**Ukázkovou třídu**, aby bylo vidět, jak to vypadá; klidne ji přejmenuj nebo smaž.

### Práce ve třídě (role učitel)
- **Třída** — komu se daří a kde se žáci opakovaně potýkají se stejnou látkou.
- **Nová úloha** — vygenerovat modelem, nebo napsat vlastní.
- U každé úlohy je tlačítko **prozkoumat**: zadání, startovací kostka, řešení
  a kontrolní kód jsou každý zvlášť, aby se na to dalo lidsky podívat.
- V tom okně je **ověřit spuštěním** (řešení musí projít, prázdný kód
  a startovací kostka nesmí) a **nechat zkontrolovat modelem** (kritika
  a návrh opravy). Schvaluje vždy člověk.
- Koncept (`draft`) se studentům neukáže, dokud není schválený.

### Správa instance (role správce)
- **Účty** — přidat člověka, role `student` / `teacher` / `admin`, vygenerovat heslo.
- **Modely** — provider (vlastní Ollama, OpenAI-kompatibilní API, Anthropic,
  Google Gemini), adresa, klíč, model pro povídání a pro tvorbu úloh.
  Uloží se do `state/config.json` (mód 600); do prohlížeče se klíč nevrací,
  jen maskovaná ukázka.
- **Přihlašování** — přihlášení heslem, nebo jednotné přihlášení z brány před celou
  doménou; hlavičky, tajemství a mapování skupin na role. Vzor pro
  Caddy/Authelia je v `docs/sso.md`.
- **Zálohy a obnova** — ruční snímek databáze, seznam snímků a tlačítko
  **načíst**, které databázi vrátí ke zvolenému snímku. Před obnovou se vždy
  udělá pojistka `pred-obnovou-*.db` a pro jistotu se opsuje slovo `OBNOVIT`.

### Klávesy
| klávesa | akce |
|---|---|
| `Ctrl+Enter` | spustit kód |
| `Ctrl+Shift+Enter` | zkontrolovat |
| `Esc` | zavřít dialog |

## English version

### Daily routine
**Today** mixes a short set (15–30 min) from the part of the course you are in.
`run ▸` executes your R code, `check ✓` grades it. `hint` uncovers one hint at
a time and the coach explains the exact R error. The solution appears only on
request and is recorded as a hint.

### Where things are
**Library** (filters, search, *add to today*), **Progress** (first-try success,
day streak, per-account skill estimates, weak topics, CSV export), **Cheat
sheet** (stays on the page, no pop-ups), **Notes** (per task, stored on the
server).

### What the notes are for
A note is not a grade and not a message to the teacher — it is your own line next
to a specific task: what caught you out, what to watch for next time. It matters
because nobody remembers in a month what the mistake was; for a task that took
half an hour, "careful, `group_by` counts the NA rows too" is the most valuable
thing the system keeps. Teachers and admins see notes in the class overview, so a
struggle is visible even when the attempt counts look fine. The coach never
receives them.

### Account settings
Theme, interface language and the length of the daily set, stored server-side.
**Users do not pick the model** — the administrator does.

### Classes
There can be several classes, with the same or different students and teachers.
A teacher creates their own and picks the accounts; one account can belong to
several classes. In the Class tab, the **Classes** card holds the name, a note
and the student picker (Ctrl/Cmd selects more). A selected class can be edited or
deleted — accounts stay, only the grouping goes. A fresh instance ships with one
**sample class** so the shape is obvious; rename or delete it freely.

### Teaching (teacher role)
**Class** shows per-student progress. New tasks are generated or written by
hand. **inspect** shows the assignment, starter, solution and checking code
separately; *verify by running* executes the solution, the empty code and the
starter; *ask the model to criticise* returns problems and a proposed fix.
A human always approves. Students never see a draft.

### Administration
Accounts and roles; model provider and keys (saved to `state/config.json`,
mode 600, never returned to the browser); sign-in (password or an SSO gateway,
see `docs/sso.md`); backups with **restore** — a `pred-obnovou-*.db` safety
copy is made first and you must type `OBNOVIT`.
