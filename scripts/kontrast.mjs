import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

// Audit kontrastu: projde skutečné zobrazení stránky v obou motivatedch
// a vypíše páry text/pozadí pod prahem WCAG.
//   node scripts/kontrast.mjs [základ_url] [uživatelské_jmeno] [heslo]
// Vypíše řádky „poměr | cesta k prvku | text | barva na pozadí“ a skončí 1,
// pokud našel něco pod 4,5 (velký text 3,0).
//
// Potřebuje `puppeteer-core` a lokální chromium. Jestliže nejsou nainstalované
// v projektu, ukáž na adresář, kde jsou:
//   PUPPETEER_CESTA=/cesta/k/puppeteer-core node scripts/kontrast.mjs ...
let puppeteer;
try {
  puppeteer = (await import(process.env.PUPPETEER_CESTA || "puppeteer-core")).default;
} catch (chyba) {
  console.log("Chybí puppeteer-core. Nainstaluj `npm i puppeteer-core`, nebo nastav");
  console.log("PUPPETEER_CESTA na adresář s ním. Původní chyba: " + String(chyba).slice(0, 120));
  process.exit(2);
}

const ZAKLAD = process.argv[2] || 'http://172.20.0.1:8710';
const JMENO = process.argv[3] || '';
const HESLO = process.argv[4] || '';
// název obrazovky a tlačítko, které se pro ni stiskne (podle lišty v index.html)
const OBRAZOVKY = [
  ["Dnes", '[data-view="today"]'],
  ["Knihovna", '[data-view="lib"]'],
  ["Progres", '[data-view="prog"]'],
  ["Tahák", '[data-view="sheet"]'],
  ["Třída", '[data-view="class"]'],
  ["Správa", '[data-view="admin"]'],
  ["Nápověda", '[data-view="help"]'],
  ["Nastavení", '#btn-settings'],
];
const PRAH = 4.5, PRAHVelky = 3.0;

function rozlozBarvu(p) {
  const shoda = String(p).match(/rgba?\(([^)]+)\)/);
  if (!shoda) return null;
  const [r, g, b, a] = shoda[1].split(',').map((x) => parseFloat(x));
  return { r, g, b, a: a === undefined ? 1 : a };
}
function presvetleni(popr, pozadi) {
  if (popr.a >= 1) return popr;
  return { r: popr.r * popr.a + pozadi.r * (1 - popr.a), g: popr.g * popr.a + pozadi.g * (1 - popr.a), b: popr.b * popr.a + pozadi.b * (1 - popr.a), a: 1 };
}
function svetlost(b) {
  const f = (c) => { const s = c / 255; return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(b.r) + 0.7152 * f(b.g) + 0.0722 * f(b.b);
}
function pomer(a, b) {
  const [x, y] = [svetlost(a), svetlost(b)].sort((m, n) => n - m);
  return (x + 0.05) / (y + 0.05);
}
function hex(b) { return '#' + [b.r, b.g, b.b].map((c) => Math.round(c).toString(16).padStart(2, '0')).join(''); }

// chromium najdeme buď z proměnné, nebo z obvyklých míst (balíček i stažený build)
function najdiChrom() {
  const { existsSync } = require('node:fs');
  const kandidati = [process.env.CHROME_CESTA, '/usr/bin/chromium', '/usr/bin/chromium-browser',
                     '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable'];
  const domaci = require('node:fs').readdirSync(require('node:os').homedir() + '/.hermes/tools', { withFileTypes: true })
    .filter((v) => v.isDirectory() && v.name.startsWith('chromium')).map((v) => require('node:path').join(
      require('node:os').homedir(), '.hermes/tools', v.name, 'chrome-linux64', 'chrome'));
  return kandidati.concat(domaci).find((c) => c && existsSync(c));
}
const browser = await puppeteer.launch({ executablePath: najdiChrom(), args: ['--no-sandbox', '--disable-dev-shm-usage'] });
const stranka = await browser.newPage();
await stranka.setViewport({ width: 1440, height: 900 });

if (JMENO) {
  // přihlásíme se z Node, ať vidíme hlavičku se sušenkou — prohlížeč ji JavaScriptu neukáže
  const odpoved = await fetch(ZAKLAD + '/api/prihlaseni', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jmeno: JMENO, heslo: HESLO, prihlaska: JMENO }),
    redirect: 'manual',
  });
  const suenka = (odpoved.headers.get('set-cookie') || '').split(';')[0];
  if (!suenka.includes('=')) { console.log('Přihlášení selhalo', odpoved.status); process.exit(2); }
  const [nazev, ...hodnota] = suenka.split('=');
  await stranka.setCookie({ name: nazev.trim(), value: hodnota.join('='), url: ZAKLAD, path: '/' });
}

let nalezy = 0;
for (const motiv of ['light', 'dark']) {
  for (const [nazev, volba] of OBRAZOVKY) {
    await stranka.goto(ZAKLAD + '/?', { waitUntil: 'domcontentloaded' });
    await stranka.evaluate((m, selektor) => {
      document.documentElement.dataset.theme = m;
      try { localStorage.setItem('rpraxe.tema', m); } catch (e) {}
      const tlacitko = document.querySelector(selektor);
      if (tlacitko) { tlacitko.hidden = false; tlacitko.click(); }
    }, motiv, volba);
    await new Promise((r) => setTimeout(r, 1100));
    const vysledek = await stranka.evaluate((prah, prahVelky) => {
      const najite = [];
      const zaklad = { r: 255, g: 255, b: 255, a: 1 };
      function rozloz(p) { const s = String(p).match(/rgba?\(([^)]+)\)/); if (!s) return null; const [r, g, b, a] = s[1].split(',').map(parseFloat); return { r, g, b, a: a === undefined ? 1 : a }; }
      function pozadiPro(el) {
        let prvek = el;
        while (prvek && prvek.nodeType === 1) {
          const rozlozena = rozloz(getComputedStyle(prvek).backgroundColor);
          if (rozlozena && rozlozena.a > 0.05) return mix(rozlozena, zaklad);
          prvek = prvek.parentElement;
        }
        return zaklad;
      }
      function mix(b, p) { if (b.a >= 1) return b; return { r: b.r * b.a + p.r * (1 - b.a), g: b.g * b.a + p.g * (1 - b.a), b: b.b * b.a + p.b * (1 - b.a), a: 1 }; }
      function svetlostS(b) { const f = (c) => { const s = c / 255; return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); }; return 0.2126 * f(b.r) + 0.7152 * f(b.g) + 0.0722 * f(b.b); }
      function pomer(a, b) { const [x, y] = [svetlostS(a), svetlostS(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); }
      function hex(b) { return '#' + [b.r, b.g, b.b].map((c) => Math.round(c).toString(16).padStart(2, '0')).join(''); }
      function cesta(el) { const casti = []; let prvek = el; for (let i = 0; i < 4 && prvek && prvek.tagName; i++) { casti.unshift(prvek.tagName.toLowerCase() + (prvek.id ? '#' + prvek.id : '') + (prvek.className && typeof prvek.className === 'string' ? '.' + prvek.className.trim().split(/\s+/).slice(0, 2).join('.') : '')); prvek = prvek.parentElement; } return casti.join(' '); }
      for (const el of document.querySelectorAll('body *')) {
        if (!(el.offsetWidth || el.offsetHeight)) continue;
        if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG'].includes(el.tagName)) continue;
        const text = Array.from(el.childNodes).filter((n) => n.nodeType === 3).map((n) => n.textContent.trim()).join(' ').trim();
        if (!text) continue;
        const styl = getComputedStyle(el);
        if (styl.visibility === 'hidden' || Number(styl.opacity) < 0.35) continue;
        const font = parseFloat(styl.fontSize) || 16;
        const tuC = (parseFloat(styl.fontWeight) || 400) >= 700;
        const prahPouzity = (font >= 24 || (font >= 18.66 && tuC)) ? prahVelky : prah;
        const pozadiBarva = pozadiPro(el);
        const textBarva = rozloz(styl.color);
        if (!pozadiBarva || !textBarva) continue;
        const pom = pomer(mix(textBarva, pozadiBarva), pozadiBarva);
        if (pom < prahPouzity) {
          najite.push({ pom: Math.round(pom * 100) / 100, cesta: cesta(el), text: text.slice(0, 44), barva: hex(mix(textBarva, pozadiBarva)), pozadi: hex(pozadiBarva), font: Math.round(font), prah: prahPouzity });
        }
      }
      return najite;
    }, PRAH, PRAHVelky).catch((e) => ({ chyba: String(e).slice(0, 160) }));
    if (vysledek.chyba) { console.log(`  ${motiv}/${obrazovka}: ${vysledek.chyba}`); continue; }
    if (!vysledek.length) continue;
    nalezy += vysledek.length;
    console.log(`\n== ${motiv} / ${obrazovka} ==`);
    for (const r of vysledek.slice(0, 12)) {
      console.log(`  ${String(r.pom).padStart(5)} (prah ${r.prah}, ${r.font}px)  ${r.barva} na ${r.pozadi}  ${r.cesta}\n         „${r.text}“`);
    }
    if (vysledek.length > 12) console.log(`  … a ${vysledek.length - 12} dalších`);
  }
}
console.log(`\ncelkem pod prahem: ${nalezy}`);
await browser.close();
process.exit(nalezy ? 1 : 0);
