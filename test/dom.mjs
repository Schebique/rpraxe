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

/* 4) nastavení: motiv, jazyk, model */
d.querySelector("#btn-settings").click();
await sleep(400);
check("dialog nastavení se otevřel", !d.querySelector("#setmodal").hidden);
check("motiv má tři možnosti", d.querySelectorAll("#set-theme option").length === 3);
check("jazyků je aspoň pět", d.querySelectorAll("#set-lang option").length >= 5,
      String(d.querySelectorAll("#set-lang option").length));
const modelu = d.querySelectorAll("#set-model option").length;
check("model AI se dá vybrat", modelu >= 1, `${modelu} na výběr`);
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
