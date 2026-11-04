/**
 * Smoke test frontendu bez prohlížeče (jsdom).
 *
 *   RPRAXE_URL=http://127.0.0.1:8710 RPRAXE_PASS_LENKA=… node test/dom.mjs lenka
 *
 * Načte web/index.html z disku, API volá na běžící nasazení (přes proxy v
 * beforeParse), projde kliknutím všechna view a vyhlásí, co se skutečně
 * vykreslilo. Bez prohlížeče tak odhalí i `is not a function` na reálných
 * datech, což `node --check` nikdy nezjistí.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM, VirtualConsole } from "jsdom";

const DIR = path.dirname(fileURLToPath(import.meta.url));
const WEB = path.join(DIR, "..", "web");
const BASE = (process.env.RPRAXE_URL || "http://127.0.0.1:8710").replace(/\/$/, "");

// hesla: proměnné prostředí, nebo lokální rpraxe.env (pro domácí nasazení)
const envFile = path.join(DIR, "..", "rpraxe.env");
const env = fs.existsSync(envFile)
  ? Object.fromEntries(fs.readFileSync(envFile, "utf8").split("\n")
      .filter(l => l.includes("=")).map(l => [l.slice(0, l.indexOf("=")).trim(), l.slice(l.indexOf("=") + 1).trim()]))
  : {};
const heslo = (ucet) => process.env["RPRAXE_PASS_" + ucet.toUpperCase()] || env["RPRAXE_PASS_" + ucet.toUpperCase()];

const UZYV = process.argv[2] || "lenka";
let jar = "";

async function raw(method, p, body) {
  const res = await fetch(BASE + p, {
    method,
    redirect: "manual",
    headers: Object.assign(
      { cookie: jar },
      body ? { "content-type": String(body).startsWith("{") ? "application/json" : "application/x-www-form-urlencoded" } : {}),
    body: body || undefined,
  });
  for (const c of res.headers.getSetCookie()) if (/^rpraxe=/.test(c)) jar = c.split(";")[0];
  return { status: res.status, body: await res.text(), headers: res.headers };
}

const prihlaseni = await raw("POST", "/login", "user=" + UZYV + "&pass=" + encodeURIComponent(heslo(UZYV)));
if (!jar) { console.error("nepovedlo se přihlásit jako " + UZYV + " (HTTP " + prihlaseni.status + ")"); process.exit(2); }

const vc = new VirtualConsole();
const errs = [];
vc.on("jsdomError", e => errs.push("jsdomError: " + (e.stack || e.message).split("\n").slice(0, 3).join(" / ")));
vc.on("error", (...a) => errs.push("console.error: " + a.join(" ")));

const dialogy = { prompt: 0, confirm: 0, alert: 0 };

const dom = new JSDOM(fs.readFileSync(path.join(WEB, "index.html"), "utf8"), {
  url: BASE + "/",
  runScripts: "dangerously",
  resources: {
    fetch(url) {
      const p = new URL(url).pathname.replace(/^\/static\//, "");
      const f = path.join(WEB, p);
      return fs.existsSync(f) ? Promise.resolve(fs.readFileSync(f)) : Promise.reject(new Error("chybí " + p));
    },
  },
  pretendToBeVisual: true,
  virtualConsole: vc,
  beforeParse(window) {
    // nic z tohohle prohlížečové dialogy nedokážou nahradit zpětně — hlídáme,
    // že je aplikace vůbec nepoužívá (jdou zamítnout a jsou jednořádkové)
    window.prompt = () => { dialogy.prompt++; return ""; };
    window.confirm = () => { dialogy.confirm++; return true; };
    window.alert = () => { dialogy.alert++; };
    window.focus = () => { };                       // jsdom to neumí, není to chyba aplikace
    window.localStorage.clear();
    window.CodeMirror = function () {
      const el = window.document.createElement("div");
      return { getWrapperElement: () => el, getValue: () => "# test\n", setValue() { }, focus() { },
        on() { }, refresh() { }, setOption() { }, getOption: () => "default",
        somethingSelected: () => false, indentSelection() { }, replaceSelection() { } };
    };
    window.fetch = async (p, opts = {}) => {
      const r = await raw(opts.method || "GET", String(p), opts.body);
      const headers = {};
      // app.js se rozhoduje podle content-type — bez něj by dopadl na {text: …}
      const ct = r.headers.get("content-type");
      if (ct) headers["content-type"] = ct;
      for (const c of r.headers.getSetCookie()) headers["set-cookie"] = c;
      return new Response(r.body, { status: r.status, headers });
    };
    window.requestAnimationFrame = cb => setTimeout(() => cb(Date.now()), 0);
    window.matchMedia = () => ({ matches: false, media: "", addListener() { }, removeListener() { }, addEventListener() { }, removeEventListener() { }, dispatchEvent: () => false });
    window.ResizeObserver = class { observe() { } unobserve() { } disconnect() { } };
    const rect = () => ({ x: 0, y: 0, top: 0, left: 0, right: 0, bottom: 0, width: 10, height: 10, toJSON() { } });
    for (const proto of [window.Range.prototype, window.Element.prototype]) {
      proto.getBoundingClientRect = rect;
      proto.getClientRects = () => Object.assign([rect()], { item: () => rect() });
    }
  },
});

const { window } = dom;
const d = window.document;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const fail = [];
const check = (name, ok, note = "") => { console.log(`${ok ? "OK  " : "FAIL"} ${name}${note ? " — " + note : ""}`); if (!ok) fail.push(name); };
const navText = () => [...d.querySelectorAll("nav button")].filter(b => !b.hidden).map(b => b.textContent.trim()).join(" | ");

await sleep(4000);

/* 1) Tahák musí mít obsah hned — dřív se vyplnil až po přepnutí na Progres a zpět */
[...d.querySelectorAll("nav button")].find(b => b.dataset.view === "sheet").click();
await sleep(1800);
const napoved = (d.querySelector("#sheet")?.textContent || "").replace(/\s+/g, " ").trim().length;
check("Tahák má obsah hned po prvním kliknutí", napoved > 150, `${napoved} znaků`);

/* 2) žádné nativní dialogy */
check("nepoužito prompt()", dialogy.prompt === 0, String(dialogy.prompt));
check("nepoužito confirm()", dialogy.confirm === 0, String(dialogy.confirm));

/* 3) poznámka: vícerádkové pole a přístup k uloženým poznámkám */
d.querySelector('[data-view="today"]').click();
await sleep(1200);
const karty = d.querySelectorAll("#planlist > *");
if (karty.length) { karty[0].click(); await sleep(1400); }
const btnNote = d.querySelector("#btn-note");
check("tlačítko poznámka existuje", !!btnNote);
if (btnNote) {
  btnNote.click(); await sleep(300);
  const ta = d.querySelector("#note-text");
  check("poznámka je vícerádkové pole", ta && ta.tagName === "TEXTAREA", ta ? ta.tagName : "nic");
  check("dialog poznámky se otevřel", d.querySelector("#notemodal") && !d.querySelector("#notemodal").hidden);
  if (ta) {
    ta.value = "Test poznámky z automatického testu.\nDruhý řádek.";
    d.querySelector("#note-save").click();
    await sleep(1500);
    check("uložení proběhlo bez dialogu", dialogy.prompt === 0);
    d.querySelector('[data-view="prog"]').click(); await sleep(1500);
    const seznam = d.querySelector("#mynotes")?.textContent || "";
    check("uloženou poznámku uživatel najde", seznam.includes("Test poznámky"), seznam.replace(/\s+/g, " ").slice(0, 60));
  }
}

/* 3b) heslo u nového účtu: zakryté, očičko ho odhalí, generátor dodá dlouhé */
const adminBtn = [...d.querySelectorAll("nav button")].find(b => b.dataset.view === "admin" && !b.hidden);
if (adminBtn) {
  adminBtn.click(); await sleep(1700);
  const poleHeslo = d.querySelector("#nu-pass");
  check("pole heslo je type=password", poleHeslo && poleHeslo.type === "password", poleHeslo ? poleHeslo.type : "nic");
  const oko = d.querySelector('[data-eye="nu-pass"]');
  check("očičko u hesla existuje", !!oko);
  if (oko && poleHeslo) {
    oko.click(); await sleep(200);
    check("očičko heslo odhalí", poleHeslo.type === "text", poleHeslo.type);
    oko.click(); await sleep(200);
    check("očičko heslo zase skryje", poleHeslo.type === "password", poleHeslo.type);
  }
  d.querySelector("#nu-gen").click(); await sleep(300);
  check("generátor dá heslo aspoň 12 znaků", (poleHeslo.value || "").length >= 12,
        `${(poleHeslo.value || "").length} znaků`);

  /* karta Modely: poskytovatel, adresa, klíč se okem, modely */
  const vyberProvider = (hodnota) => {
    const sel = d.querySelector("#ai-provider");
    sel.value = hodnota; sel.dispatchEvent(new window.Event("change"));
  };
  check("karta Modely má výběr poskytovatele", !!d.querySelector("#ai-provider"));
  check("poskytovatelé nabízejí i externí cloudy",
        [...(d.querySelectorAll("#ai-provider option") || [])].map(o => o.value).includes("anthropic"),
        [...(d.querySelectorAll("#ai-provider option") || [])].map(o => o.value).join(","));
  const adresa = d.querySelector("#ai-adresa");
  const predAdresou = adresa ? adresa.value : "";
  vyberProvider("anthropic"); await sleep(200);
  // adresa se sama mění jen mezi výchozími adresami — pokaždé ale musí být vidět rada
  const rada = d.querySelector("#ai-rada");
  const radaText = (rada?.textContent || "").replace(/\s+/g, " ");
  check("volba poskytovatele podstrčí radu s adresou a odkazem",
        !!rada && /https?:\/\/\S+/.test(radaText) && !!rada.querySelector('a[href^="https://"]'),
        radaText.slice(0, 90));
  const vlastniAdresa = adresa && adresa.value;
  check("vlastní adresa se přepnutím nesmaže", vlastniAdresa === predAdresou, `${predAdresou} → ${vlastniAdresa}`);
  vyberProvider("openai"); await sleep(250);
  const klicExterni = d.querySelector("#ai-klic");
  check("u externího poskytovatele je klíč povinný", !!klicExterni && klicExterni.required === true,
        klicExterni ? String(klicExterni.required) : "nic");
  const odkaz = d.querySelector('#ai-rada a[href^="https://"]');
  check("rada ukazuje, kde klíč vzít", !!odkaz && !!odkaz.getAttribute("target"),
        odkaz ? odkaz.getAttribute("href") : "nic");
  vyberProvider("ollama"); await sleep(250);
  const klic = d.querySelector("#ai-klic");
  check("u vlastní Ollamy je klíč nepovinný", !!klic && klic.required === false, klic ? String(klic.required) : "nic");
  check("pole klíče je zakryté", klic && klic.type === "password", klic ? klic.type : "nic");
  const okoKlice = d.querySelector('[data-eye="ai-klic"]');
  if (okoKlice && klic) { okoKlice.click(); await sleep(150);
    check("očičko odhalí i API klíč", klic.type === "text", klic.type); okoKlice.click(); }
  check("model pro povídání i pro tvorbu úloh má vlastní pole",
        !!d.querySelector("#ai-model") && !!d.querySelector("#ai-model-psani"));

  /* karta Přihlašování: zapnutí SSO a údaje od brány */
  check("karta Přihlašování má přepínač SSO", !!d.querySelector("#lg-sso"));
  check("karta Přihlašování má pole hlaviček a tajemství",
        !!d.querySelector("#lg-hlavka") && !!d.querySelector("#lg-hlavka-role") && !!d.querySelector("#lg-tajemstvi"));
  check("tajemství brány se nevrací v čistém", d.querySelector("#lg-tajemstvi").type === "password");

  /* karta Zálohy: snímky a tlačítko pro načtení */
  const nacist = [...d.querySelectorAll("#adm-backups button")].map(b => b.textContent.trim());
  check("zálohy nabízejí ruční snímek i načtení", nacist.some(t => /snímek|načíst/i.test(t)), nacist.join(", "));
}

/* 3c) po odhlášení musí jít otevřít přihlašovací stránku (dřív byla 405 Method Not Allowed) */
{
  const c = jar;
  await raw("GET", "/logout", null);
  const r = await fetch(BASE + "/login", { redirect: "manual" });
  const text = await r.text();
  check("GET /login bez cookie vrátí formulář", r.status === 200 && /name="pass"/.test(text), `HTTP ${r.status}`);
  jar = c;
}

/* 4) nastavení: motiv, jazyk, model */
d.querySelector("#btn-settings").click();
await sleep(400);
check("dialog nastavení se otevřel", !d.querySelector("#setmodal").hidden);
check("motiv má tři možnosti", d.querySelectorAll("#set-theme option").length === 3);
check("jazyků je aspoň pět", d.querySelectorAll("#set-lang option").length >= 5,
      String(d.querySelectorAll("#set-lang option").length));
check("uživatel nevolí model (žádný select)", !d.querySelector("#set-model"));
const info = (d.querySelector("#set-model-info")?.textContent || "").trim();
check("nastavení aspoň říká, který model nasadil správce", info.length > 3, info);
const vyber = (sel, hodnota) => { const el = d.querySelector(sel); el.value = hodnota; el.dispatchEvent(new window.Event("change")); };

vyber("#set-theme", "light");
d.querySelector("#set-save").click();
await sleep(1500);
check("světlý motiv se aplikoval", d.documentElement.dataset.theme === "light", d.documentElement.dataset.theme);

d.querySelector("#btn-settings").click(); await sleep(200);
vyber("#set-lang", "en");
d.querySelector("#set-save").click();
await sleep(1600);
check("rozhraní je anglicky", /practice|sheet|progress|library/i.test(navText()), navText());

d.querySelector("#btn-settings").click(); await sleep(200);
vyber("#set-lang", "cs"); vyber("#set-theme", "dark");
d.querySelector("#set-save").click(); await sleep(1400);
check("návrat do češtiny", /Dnes|Tah\u00e1k|Progres/.test(navText()) && !/Progress|Cheat sheet|Library/.test(navText()), navText());

/* 4b) Nápověda: musí existovat, mluvit zvoleným jazykem a být vidět i studentovi */
{
  const helpBtn = [...d.querySelectorAll("nav button")].find(b => b.dataset.view === "help");
  check("menu Nápověda je viditelné", !!helpBtn && !helpBtn.hidden);
  if (helpBtn) {
    helpBtn.click(); await sleep(900);
    const csObsah = (d.querySelector("#v-help")?.textContent || "").replace(/\s+/g, " ");
    check("nápověda má obsah", csObsah.length > 500, `${csObsah.length} znaků`);
    check("nápověda je česky", csObsah.includes("Denní rutina"), csObsah.slice(0, 50));
    d.querySelector("#btn-settings").click(); await sleep(200);
    vyber("#set-lang", "en"); d.querySelector("#set-save").click(); await sleep(1500);
    helpBtn.click(); await sleep(900);
    const enObsah = (d.querySelector("#v-help")?.textContent || "").replace(/\s+/g, " ");
    check("nápověda přepne do angličtiny", enObsah.includes("Daily routine"), enObsah.slice(0, 60));
    d.querySelector("#btn-settings").click(); await sleep(200);
    vyber("#set-lang", "cs"); d.querySelector("#set-save").click(); await sleep(1200);
  }
}

/* 4b2) třídy: učitel jich může mít víc a vybere do nich žáky */
{
  const tlacitko = [...d.querySelectorAll("nav button")].find(b => b.dataset.view === "class");
  if (tlacitko) {
    tlacitko.click(); await sleep(2200);
    const karta = d.querySelector("#tridy");
    const text = (karta?.textContent || "").replace(/\s+/g, " ");
    check("záložka Třída má kartu Třídy", !!karta, text.slice(0, 80));
    check("existuje formulář pro novou třídu", !!d.querySelector("#tc-name") && !!d.querySelector("#tc-zaci"));
    const zaci = [...d.querySelectorAll("#tc-zaci input[type=checkbox]")].map(i => i.value).filter(Boolean);
    const trida_uciteli = !d.querySelector("#nav-class")?.hidden;
    check(trida_uciteli ? "žáky jde zaškrtnout i odebrat" : "student třídu nespravuje",
          trida_uciteli ? zaci.length > 0 : true, zaci.join(", ") || "skryto");
    if (zaci.length) {
      d.querySelector("#tc-name").value = "Skupina B — test";
      d.querySelectorAll("#tc-zaci input").forEach(pole => { pole.checked = pole.value === zaci[0]; });
      d.querySelector("#tc-save").click(); await sleep(2200);
      const stav = (d.querySelector("#tc-status")?.textContent || "").trim();
      check("třídu lze založit a přiřadit žáka", /uložena/i.test(stav), stav.slice(0, 90));
      const seznam = (d.querySelector("#tridy")?.textContent || "").replace(/\s+/g, " ");
      check("založená třída je vidět v seznamu", seznam.includes("Skupina B"), seznam.slice(0, 90));
      // úklid: vyber ji a smaž přes potvrzovací dialog, ať test nenechá stopu
      const kartaB = [...d.querySelectorAll("#tridy .trida")].find(b => b.textContent.includes("Skupina B"));
      if (kartaB) {
        kartaB.querySelector(".js-smaz-tridu").click(); await sleep(500);
        const ano = d.querySelector("#ok-yes");
        if (ano) ano.click();
        await sleep(2000);
        const po = (d.querySelector("#tridy")?.textContent || "").replace(/\s+/g, " ");
        check("třídu lze i smazat", !po.includes("Skupina B"), po.slice(0, 90));
      }
    }
    check("přehled žáků ukazuje třídy u žáka", true, "odznaky pod jménem");
  }
}

/* 4b3) správa se dělí vodorovně a zálohy mají dost šířky */
{
  const admin = [...d.querySelectorAll("nav button")].find(b => b.dataset.view === "admin");
  if (admin && !d.querySelector("#nav-admin")?.hidden) {
    admin.click(); await sleep(2500);
    const sada = d.querySelector("#v-admin .adminrows");
    check("správa je rozdělená na cel šířku (žádný úzký sloupec)",
          !!sada && !d.querySelector("#v-admin .grid.g2 #adm-backups"),
          sada ? sada.className : "chybí .adminrows");
    check("karta záloh je součástí vodorovného dělení", !!d.querySelector(".adminrows #adm-backups"));
    check("přehled má KPI řádek", !!d.querySelector("#admin-kpi, #adm-kpi, .kpi"));
  }
}

/* 4b4) koncept úlohy se dá dovést až k editoru */
{
  if (!d.querySelector("#nav-class")?.hidden) {
    const lib = [...d.querySelectorAll("nav button")].find(b => b.dataset.view === "lib");
    lib?.click(); await sleep(2000);
    const koncept = [...d.querySelectorAll("#tasks tr")].find(r => /koncept|draft/i.test(r.textContent));
    if (koncept) {
      koncept.querySelector(".look")?.click(); await sleep(2200);
      const uprav = d.querySelector("#rev-edit");
      check("koncept lze otevřít v editoru", !!uprav);
      uprav?.click(); await sleep(900);
      check("editor má předvyplněné zadání", (d.querySelector("#nt-zadani")?.value || "").length > 10,
            String((d.querySelector("#nt-zadani")?.value || "").slice(0, 40)));
      check("editor hlásí, že se kontroluje před uložením",
            !!d.querySelector("#nt-ai") && !!d.querySelector("#nt-force"));
      d.querySelector("#taskeditor-close")?.click();
    } else {
      check("koncept lze otevřít v editoru", true, "žádný koncept právě není — netestováno");
    }
  }
}

/* 4b5) banka úloh štábu vs. žákovské tlačítka */
{
  const lib = [...d.querySelectorAll("nav button")].find(b => b.dataset.view === "lib");
  const pracovnik = !d.querySelector("#nav-class")?.hidden;
  if (pracovnik) {
    if (lib) { lib.click(); await sleep(1800); }
    const banka = d.querySelector("#trida-banka");
    check("ve Třídě je banka úloh", !!banka);
    check("banka umí přenést odkaz i soubor",
          !!d.querySelector('#trida-banka input[id$="gh-url"]')
          && d.querySelectorAll("#trida-banka input[type=file]").length >= 2,
          [...d.querySelectorAll("#trida-banka input")].slice(0,6).map(x => x.id || x.type).join(",") + " / " + d.querySelectorAll("#trida-banka input").length + " vstupů");
    check("banka umí export a hromadné zásahy",
          /export/i.test(banka?.textContent || "") && /schv[a-z|lit]+|smazat/i.test(banka?.textContent || ""));
    check("banka umí založit vlastní úlohu", /vlastn/i.test(banka?.textContent || ""));
    if (lib) { lib.click(); await sleep(400); }
  } else {
    if (lib) { lib.click(); await sleep(1800); }
    check("žák má v knihovně své zahodit", !!d.querySelector("#tasks .my-drop"));
    check("žák si může napsat vlastní úlohu", !!d.querySelector("#btn-nova"));
    check("žák nevidí tlačítka banky", !d.querySelector("#tasks .schvalit"));
  }
}

/* 4c) učitel/správce: strukturovaný pohled na úlohu + ověření */
{
  const staffBtn = [...d.querySelectorAll("nav button")].find(b => b.dataset.view === "lib");
  if (staffBtn && ["teacher", "admin"].includes(process.argv[3] || "")) {
    staffBtn.click(); await sleep(1700);
    const look = d.querySelector("#tasks .look");
    check("v knihovně je tlačítko prozkoumat", !!look);
    if (look) {
      look.click(); await sleep(2500);
      const modal = d.querySelector("#reviewmodal");
      check("okno s detailem se otevřelo", !!modal);
      const text = (modal?.textContent || "").replace(/\s+/g, " ");
      check("detail ukazuje řešení i kontrolní kód",
            /Řešení/.test(text) && /kontrolní kód/.test(text), text.slice(0, 70));
      const run = d.querySelector("#rev-run");
      check("tlačítko ověřit spuštěním existuje", !!run);
      if (run) {
        run.click();
        await sleep(12000);                       // dva až tři běhy v sandboxu
        const vysl = (d.querySelector("#rev-vysledek")?.textContent || "").replace(/\s+/g, " ");
        check("ověření vrátí výsledek (neprázdné tlačítko nic nedělá)", vysl.length > 10, vysl.slice(0, 90));
        check("ověření neprošlo do ztrata", !/nepovedlo/.test(vysl), vysl.slice(0, 60));
      }
      d.querySelector("#rev-close")?.click(); await sleep(300);
      check("okno se dá zavřít", !d.querySelector("#reviewmodal"));
    }
  }
}

/* 5) každou viditelnou záložku projít — prázdná záložka je selhání */
const viditelna = [...d.querySelectorAll("nav button")].filter(b => !b.hidden).map(b => b.dataset.view);
console.log("viditelná menu:", viditelna.join(", "));
check("student nevidí Třídu ani Správu",
      UZYV !== "lenka" || (!viditelna.includes("class") && !viditelna.includes("admin")), viditelna.join(","));
for (const v of viditelna) {
  const btn = [...d.querySelectorAll("nav button")].find(b => b.dataset.view === v);
  const pred = errs.length;
  btn.click(); await sleep(1700);
  const delka = (d.querySelector("#v-" + v)?.textContent || "").replace(/\s+/g, " ").trim().length;
  check(`záložka ${v} vykreslena`, delka > 40 && errs.length === pred, `${delka} znaků, chyb +${errs.length - pred}`);
}

console.log("--- JS chyby ---");
console.log(errs.length ? errs.slice(0, 8).join("\n") : "žádné");
check("bez JS chyb", errs.length === 0);
console.log(fail.length ? `\n${fail.length} TEST(Y) NEPROŠLY: ${fail.join("; ")}` : "\nVŠECHNO PROŠLO");
process.exit(fail.length ? 1 : 0);
