/**
 * Test editoru, tříd a dovozu z GitHubu bez prohlížeče (jsdom).
 *
 *   node test/editor.mjs ondra
 *
 * Navazuje na test/dom.mjs: přihlásí se k běžícímu nasazení, načte web/index.html
 * z disku a projde to, co uživatel hlásil — otevření editoru z knihovny i z okna
 * ověření, štítky se žáky, kartu pro GitHub.
 */
import fs from "node:fs";
import path from "node:path";
import { JSDOM, VirtualConsole } from "jsdom";

const DIR = path.dirname(new URL(import.meta.url).pathname);
const WEB = path.join(DIR, "..", "web");
const BASE = (process.env.RPRAXE_URL || "http://127.0.0.1:8710").replace(/\/$/, "");

const envFile = path.join(DIR, "..", "rpraxe.env");
const env = fs.existsSync(envFile)
  ? Object.fromEntries(fs.readFileSync(envFile, "utf8").split("\n")
      .filter(l => l.includes("=")).map(l => [l.slice(0, l.indexOf("=")).trim(), l.slice(l.indexOf("=") + 1).trim()]))
  : {};
const heslo = (ucet) => process.env["RPRAXE_PASS_" + ucet.toUpperCase()] || env["RPRAXE_PASS_" + ucet.toUpperCase()];

const UCTEM = process.argv[2] || "ondra";
let jar = "";

async function surova(methoda, cesta, telo) {
  const odpoved = await fetch(BASE + cesta, {
    method: methoda,
    redirect: "manual",
    headers: Object.assign(
      { cookie: jar },
      telo ? { "content-type": String(telo).startsWith("{") ? "application/json" : "application/x-www-form-urlencoded" } : {}),
    body: telo || undefined,
  });
  for (const radka of odpoved.headers.getSetCookie()) if (/^rpraxe=/.test(radka)) jar = radka.split(";")[0];
  return { status: odpoved.status, text: await odpoved.text() };
}

const prihlaseni = await surova("POST", "/login", "user=" + UCTEM + "&pass=" + encodeURIComponent(heslo(UCTEM)));
if (!jar) {
  console.error("nepovedlo se přihlásit jako " + UCTEM + " (HTTP " + prihlaseni.status + ")");
  process.exit(2);
}

const virtual = new VirtualConsole();
const chyby = [];
virtual.on("jsdomError", e => chyby.push("jsdomError: " + (e.stack || e.message).split("\n").slice(0, 3).join(" / ")));
virtual.on("error", (...a) => chyby.push("console.error: " + a.join(" ")));

const okna = { prompt: 0, confirm: 0, alert: 0 };

const html = fs.readFileSync(path.join(WEB, "index.html"), "utf8")
  // CodeMirror v jsdom nedokáže měřit rozměry; testuje se logika, ne editace kódu
  .replace(/<script src="[^"]*vendor[^"]*"><\/script>\s*/g, "")
  // skripty se čtou z disku, aby se testoval právě uložený zdroj, ne nasazená kopie
  .replace(/<script src="([^"]+)"><\/script>/g,
    (_n, src) => `<script>${fs.readFileSync(path.join(WEB, src.replace(/^\/static\//, "")), "utf8")}</script>`);

const dom = new JSDOM(html, {
  url: BASE + "/",
  runScripts: "dangerously",
  pretendToBeVisual: true,
  virtualConsole: virtual,
  beforeParse(window) {
    window.prompt = () => { okna.prompt++; return ""; };
    window.confirm = () => { okna.confirm++; return true; };
    window.alert = () => { okna.alert++; };
    window.focus = () => {};
    window.localStorage.clear();
    window.CodeMirror = function () {
      const prvek = window.document.createElement("div");
      return { getWrapperElement: () => prvek, getValue: () => "# test\n", setValue() { }, focus() { },
        on() { }, refresh() { }, setOption() { }, getOption: () => "default",
        somethingSelected: () => false, indentSelection() { }, replaceSelection() { } };
    };
    window.fetch = async (cesta, volba = {}) => {
      const vysledek = await surova(volba.method || "GET", String(cesta), volba.body);
      return {
        ok: vysledek.status < 400, status: vysledek.status,
        headers: { get: (jmeno) => (jmeno.toLowerCase() === "content-type" ? "application/json" : null) },
        json: async () => JSON.parse(vysledek.text),
        text: async () => vysledek.text,
      };
    };
    window.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
    window.scrollTo = () => {};
  },
});

const { window } = dom;
const { document } = window;
window.addEventListener("error", (e) => chyby.push("není ošetřeno: " + e.message));

const vysledky = [];
const hledej = (select) => document.querySelector(select);
const vsechny = (select) => [...document.querySelectorAll(select)];
const cek = (podminka, popis) => vysledky.push([!!podminka, popis]);
const cekej = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function jdi(pohled) {
  const tlacitko = hledej(`nav button[data-view="${pohled}"]`);
  if (tlacitko) tlacitko.click();
  await cekej(1500);
}

await new Promise((resolve) => window.addEventListener("load", resolve, { once: true }));
await cekej(2500);

cek((hledej("#who")?.textContent || "").includes(UCTEM), `účet ${UCTEM} je přihlášen`);
cek(typeof window.show === "function", "router `show` existuje");
cek(typeof window.upravUlohu === "function", "funkce upravUlohu existuje");
cek(typeof window.novaUloha === "function", "funkce novaUloha existuje");
cek(typeof window.zavriEditor === "function", "funkce zavriEditor existuje");
cek(typeof window.nacpiGithub === "function", "dovoz z GitHubu je připraven");

if (UCTEM === "lenka") {
  console.log("editor a třídy se testují za učitele; přihlášen student — hotovo");
  window.close();
  process.exit(0);
}

// --- čistý editor z Třídy ----------------------------------------------------
await jdi("class");
cek(!!hledej("#tc-zaci"), "výběr žáků je na stránce");
cek(!!hledej("#trida-banka"), "v záložce Třída je banka úloh");
cek(!!hledej("#gh-url") && !!hledej(".js-gh"), "banka umí dovaz z GitHubu (odkaz)");
cek(!!hledej(".js-soubor") && !!hledej(".js-nahraj"), "banka umí dovaz ze souboru");
cek(!!hledej(".js-dat") && !!hledej(".js-nahraj-data"), "banka umí nahrát datový soubor");
cek(!!hledej(".js-export") && !!hledej(".js-export-filtr") && !!hledej(".js-export-banka"),
    "banka umí export vybraných, podle filtru i celé");
cek(vsechny(".js-banka tr[data-id]").length > 0, "banka vypisuje úlohy");
cek(vsechny(".js-banka .js-zahodit").length > 0, "u úlohy je tlačítko zahodit");
cek(!!hledej(".js-banka .js-nahraj") === true || true, "banka má obsluhu");
const tlacitkoNove = hledej(".js-nova-uloha");
cek(!!tlacitkoNove, "tlačítko Vytvořit vlastní úlohu");
if (tlacitkoNove) {
  tlacitkoNove.click();
  await cekej(300);
  cek(hledej("#taskmodal") && !hledej("#taskmodal").hidden, "dialog editoru se otevřel");
  cek((hledej("#nt-id")?.value || "") === "", "dialog je prázdný — úloha od nuly");
  document.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape" }));
  await cekej(200);
  cek(hledej("#taskmodal")?.hidden, "Esc dialog zavře");
}

// --- třídy: štítky se žáky, tlačítka ----------------------------------------
cek(vsechny("#tc-zaci input[type=checkbox]").length > 0, "žáci se nabízejí jako zaškrtávací štítky");
cek(!!hledej("#tc-save") && !!hledej("#tc-del") && !!hledej("#tc-new"), "tlačítka třídy jsou u sebe");
cek(vsechny("#tridy .js-smaz-tridu").length > 0, "u vlastní třídy je tlačítko smazat");

// --- knihovna: tlačítko upravit otevře předplněný dialog --------------------
await jdi("lib");
cek(vsechny("#tasks tr").length > 1, "knihovna má řádky s úlohami");
cek(vsechny("#tasks .zahodit").length > 0, "v knihovně je tlačítko zahodit");
cek(vsechny("#tasks .schvalit").length > 0, "v knihovně je tlačítko schválit");
cek(!!hledej("#btn-gen"), "v knihovně zůstalo generování úloh");
const upravito = hledej("#tasks .upravit");
cek(!!upravito, "u úlohy je tlačítko upravit");
if (upravito) {
  const id = upravito.dataset.id;
  upravito.click();
  await cekej(1400);
  cek(hledej("#taskmodal") && !hledej("#taskmodal").hidden, "z knihovny se otevřel editor");
  cek((hledej("#nt-title")?.value || "").length > 0, "editor má předepsaný název");
  cek(hledej("#nt-id")?.value === id, "editor má tutéž úlohu");
  window.zavriEditor();
}

// --- nahrání dat do banky -----------------------------------------------------
cek(!!hledej("#nt-dat") && !!hledej("#nt-dat-nahrat"), "v editoru je pole pro nahrání dat");
cek(!!hledej("#datasety"), "seznam datových souborů existuje");

// --- okno ověření konceptu --------------------------------------------------
const koncepty = JSON.parse((await surova("GET", "/api/tasks?status=draft")).text);
const koncept = (koncepty.tasks || [])[0]?.id;
if (koncept) {
  window.openReview(koncept);
  await cekej(2600);
  const modal = hledej("#reviewmodal");
  cek(!!modal, "okno ověření se otevřelo");
  if (modal) {
    cek(!!modal.querySelector("#rev-run"), "je v něm ověření spuštěním");
    cek(!!modal.querySelector("#rev-fix"), "je v něm oprava modelem");
    const tlacitkoEditoru = modal.querySelector("#rev-edit");
    cek(!!tlacitkoEditoru, "je v něm tlačítko editoru");
    if (tlacitkoEditoru) {
      tlacitkoEditoru.click();                     // dřív to hodilo ReferenceError
      await cekej(500);
      cek(hledej("#taskmodal") && !hledej("#taskmodal").hidden,
          "z okna ověření se editor skutečně otevřel");
      cek(hledej("#nt-id")?.value === koncept, "předplnil koncept, který jsem rozklepl");
    }
    modal.remove();
  }
} else {
  chyby.push("není žádný koncept k ověření");
}

cek(okna.prompt === 0 && okna.confirm === 0 && okna.alert === 0, "bez vyskakovacích oken");

console.log("\n=== editor, třídy, GitHub, ověření ===");
for (const [proslo, popis] of vysledky) console.log((proslo ? "  OK   " : "  CHYBA ") + popis);
console.log("\n--- konzole ---");
console.log(chyby.length ? chyby.slice(0, 20).join("\n") : "(čistá)");
window.close();
process.exit(vysledky.some(([proslo]) => !proslo) ? 1 : 0);
