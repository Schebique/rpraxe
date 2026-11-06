const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let cm, current = null, boot = null, hintStep = 0, openedAt = 0;
let ROLE = "student", SETTINGS = null;

/* ----------------------------- motiv a jazyk (bez vyskakovacích oken) ---- */
function applyTheme(theme) {
  const dark = theme === "dark" ||
    (theme === "auto" && !(window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches));
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  try { localStorage.setItem("rpraxe.theme", theme || "auto"); } catch (e) {}
  if (cm) cm.setOption("theme", dark ? "material-darker" : "default");
}

function applyLang(lang) {
  LANG = lang && I18N[lang] ? lang : "cs";
  document.documentElement.lang = LANG;
  try { localStorage.setItem("rpraxe.lang", LANG); } catch (e) {}
  translateDom(document.body);   // i modaly, které se appendují za #app
}

/* překlad běží i pro nodes, které vzniknou až po načtení */
function watchTranslations() {
  const box = document.body;
  if (!box || typeof MutationObserver === "undefined") return;
  let timer = null;
  new MutationObserver(() => {
    if (LANG === "cs") return;
    clearTimeout(timer);
    timer = setTimeout(() => translateDom(box), 120);
  }).observe(box, { childList: true, subtree: true, characterData: true });
}

async function api(path, opts = {}) {
  const { redirect401 = true, ...send } = opts;
  const r = await fetch(path, Object.assign({ headers: { "content-type": "application/json" } }, send));
  if (r.status === 401 && redirect401) { location = "/"; throw new Error("nepřihlášen"); }
  const ct = r.headers.get("content-type") || "";
  return ct.includes("json") ? r.json() : { text: await r.text() };
}

function busy(on, where = $("#busy")) { where.innerHTML = on ? '<span class="spin"></span> počkej…' : ""; }

/* ---------------------------------------------------------------- editor */
function initEditor() {
  cm = CodeMirror($("#editor"), {
    value: "# tvůj R kód\n", mode: "r", theme: "material-darker",
    lineNumbers: true, matchBrackets: true, autoCloseBrackets: true,
    styleActiveLine: true, indentUnit: 2, tabSize: 2, viewportMargin: Infinity,
    extraKeys: {
      "Ctrl-Enter": () => runCode(false), "Cmd-Enter": () => runCode(false),
      "Ctrl-B": () => runCode(true), "Cmd-B": () => runCode(true),
      Tab: c => { if (c.somethingSelected()) c.indentSelection("add"); else c.replaceSelection("  "); },
    },
  });
  cm.getWrapperElement().style.flex = "1";
}

/* ----------------------------------------------------------------- dnes */
async function loadBoot() {
  boot = await api("/api/bootstrap");
  ROLE = boot.role || "student";
  applyTheme(boot.theme || "auto");
  applyLang(boot.lang || "cs");
  $("#nav-help").hidden = false;   // nápověda patří i pro studenty
  $("#nav-class").hidden = !["teacher", "admin"].includes(ROLE);
  $("#nav-admin").hidden = ROLE !== "admin";
  $("#who").textContent = boot.user;
  $("#streak").textContent = boot.streak ? `řada ${boot.streak} dní` : "";
  $("#day-title").textContent = new Date().toLocaleDateString("cs-CZ", { weekday: "long", day: "numeric", month: "long" });
  $("#budget").value = String(boot.budget);
  $("#budget-lbl").textContent = `dávka ${boot.budget} min · kurz: ${boot.lesson_current}. lekce — ${boot.lesson_title}`;
  renderPlan(boot.items);
  renderMinutes();
  const an = $("#agent-note");
  if (an) { an.style.display = boot.agent_note ? "" : "none"; an.textContent = boot.agent_note || ""; }
  // na mobilu je seznam až moc dlouhý na to, aby byl vždy rozbalený
  if (window.matchMedia && window.matchMedia("(max-width:1020px)").matches) {
    const box = $("#planbox"); if (box) box.open = false;
  }
  if (!current && boot.items.length) openTask(boot.items[0].id);
}

function renderMinutes() {
  const m = boot.today?.minutes || 0, b = boot.budget || 20;
  $("#min-bar").style.width = Math.min(100, (m / b) * 100) + "%";
  $("#min-lbl").textContent = `${m.toFixed(0)} / ${b} min · ${boot.today?.passed || 0} hotovo z ${boot.items.length}`;
}

function renderPlan(items) {
  const sum = $("#planbox-title");
  if (sum) {
    const hotovo = items.filter(t => t.solved).length;
    sum.textContent = items.length ? `Dnešní úlohy — ${hotovo} z ${items.length} hotovo` : "Dnešní úlohy";
  }
  $("#planlist").innerHTML = items.map(t => `
    <button class="taskitem ${t.solved ? "done" : ""} ${current && current.id === t.id ? "on" : ""}" data-id="${esc(t.id)}">
      <span class="t">${esc(t.title)}</span>
      <span class="m">${t.minutes} min · lekce ${t.lesson} · ${esc((t.skills || []).slice(0, 3).join(", "))}</span>
      ${t.why && !t.solved ? `<span class="why">${esc(t.why)}</span>` : ""}
    </button>`).join("") || `<p class="muted">Dnešní dávka je hotová. Můžeš si přidat něco z knihovny.</p>`;
  $$("#planlist .taskitem").forEach(b => b.onclick = () => openTask(b.dataset.id));
  $$("[data-pane]").forEach(b => { b.onclick = () => showPane(b.dataset.pane); });
}

async function openTask(id) {
  const t = (await api("/api/tasks")).tasks.find(x => x.id === id) || boot.items.find(x => x.id === id);
  if (!t) return;
  current = t; hintStep = 0; openedAt = Date.now(); $("#hintbox").innerHTML = "";
  $("#t-title").textContent = t.title;
  $("#t-meta").textContent = `lekce ${t.lesson} · ${t.minutes} min · obtížnost ${Number(t.level).toFixed(1)} · ${t.id}`;
  $("#zadani").innerHTML = esc(t.zadani).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\n/g, "<br>");
  if (t.dataset) {
    $("#datainfo").textContent = "soubor: " + t.dataset;
  } else {
    $("#datainfo").textContent = "tahle úloha se obejde bez souboru — stačí psát rovnou kód";
    $("#datatable").innerHTML = "";
    $("#dataprev").style.display = "none";
  }
  const saved = JSON.parse(localStorage.getItem("rpraxe.code") || "{}");
  cm.setValue(saved[id] || t.starter || "# začni psát\n");
  $$("[data-pane]").forEach(b => b.classList.toggle("on", b.dataset.pane === "zadani"));
  showPane("zadani");
  vykresliPoznamku();
  if (t.dataset) showDataset(t.dataset);
  $("#out").textContent = "výstup se objeví tady…"; $("#verdict").style.display = "none";
  $("#plots").style.display = "none"; $("#plots").innerHTML = "";
  renderPlan(boot.items);
  cm.focus();
}

async function showDataset(name) {
  const d = await api("/api/dataset/" + encodeURIComponent(name));
  if (d.detail) {
    $("#datainfo").textContent = "náhled se nepodařilo načíst";
    $("#datatable").innerHTML = ""; $("#dataprev").style.display = ""; $("#dataprev").textContent = "";
    return;
  }
  if (d.cols && d.cols.length) {
    const hlavicka = "<tr>" + d.cols.map(c => `<th>${esc(c)}</th>`).join("") + "</tr>";
    const radky = d.data.map(r => "<tr>" + r.map(x => `<td>${esc(x)}</td>`).join("") + "</tr>").join("");
    $("#datatable").innerHTML = `<table class="dtable"><thead>${hlavicka}</thead><tbody>${radky}</tbody></table>`;
    $("#dataprev").style.display = "none";
    $("#datainfo").textContent = `${d.name} · ${d.cols.length} sloupců · zobrazeno ${d.shown} z ${d.rows_total} řádků (seřazeno jako v souboru)`;
  } else {
    $("#datatable").innerHTML = "";
    $("#dataprev").style.display = "";
    $("#dataprev").textContent = d.preview || "(soubor se nepodařilo přečíst)";
    $("#datainfo").textContent = `${d.name} · textový soubor`;
  }
}

/* přepínání záložek zadání / data — bez toho tlačítko „data“ nedělalo nic */
function showPane(which) {
  $$("[data-pane]").forEach(b => b.classList.toggle("on", b.dataset.pane === which));
  $("#pane-zadani").style.display = which === "zadani" ? "" : "none";
  $("#pane-data").style.display = which === "data" ? "" : "none";
}

/* ------------------------------------------------------- vlastní poznámky */
let poznamky = [];   // naposledy načtené, nejnovější první

async function nactiPoznamky() {
  try { poznamky = (await api("/api/notes")).notes || []; } catch (e) { poznamky = []; }
}

const poznamkaPro = (id) => {
  const n = poznamky.find(x => x.task === id);
  return n && (n.text || "").trim() ? n : null;
};

function vykresliPoznamku() {
  const box = $("#mynote");
  if (!box) return;
  const n = current ? poznamkaPro(current.id) : null;
  if (!n) { box.style.display = "none"; box.innerHTML = ""; return; }
  box.style.display = "";
  box.innerHTML = `<strong class="tiny">Tvoje poznámka k téhle úloze</strong><br>`
    + esc(n.text).replace(/\n/g, "<br>")
    + `<div class="tiny muted" style="margin-top:4px">zapsáno `
    + new Date(n.ts * 1000).toLocaleString("cs-CZ") + `</div>`;
}

function vykresliSeznamPoznamek() {
  const box = $("#mynotes");
  if (!box) return;
  const plnene = poznamky.filter(n => (n.text || "").trim());
  box.innerHTML = plnene.length
    ? "<ul>" + plnene.slice(0, 12).map(n => `<li><a href='#' data-id='${esc(n.task)}'>${esc(n.title)}</a>`
      + ` <span class="tiny muted">${new Date(n.ts * 1000).toLocaleDateString("cs-CZ")}</span>`
      + `<div class="tiny muted">${esc(n.text.slice(0, 120))}${n.text.length > 120 ? "…" : ""}</div></li>`).join("") + "</ul>"
    : "<p class='muted tiny'>zatím žádné — u úlohy klikni na „zapsat poznámku“</p>";
  $$("#mynotes a").forEach(a => a.onclick = e => { e.preventDefault(); openTask(a.dataset.id); show("today"); });
}

function poznámka(id) { return poznamkaPro(id); }

function openNote() {
  if (!current) { toast("Nejdřív vyber úlohu."); return; }
  const n = poznamkaPro(current.id);
  $("#note-err").textContent = "";
  $("#note-text").value = n ? n.text : "";
  $("#notemodal").hidden = false;
  $("#note-save").disabled = false;
  $("#note-text").focus();
}

async function ulozPoznamku(text) {
  if (!current) return;
  $("#note-save").disabled = true;
  try {
    await api("/api/feedback", { method: "POST",
      body: JSON.stringify({ task_id: current.id, kind: "note", text }) });
    await nactiPoznamky();
    vykresliPoznamku(); vykresliSeznamPoznamek();
    $("#notemodal").hidden = true;
    toast(text.trim() ? "Poznámka uložená — najdeš ji pod zadáním a v Progresu."
                      : "Poznámka smazaná.");
  } catch (e) {
    $("#note-err").textContent = "Nepovedlo se uložit — zkus to znovu.";
    $("#note-save").disabled = false;
  }
}

/* --------------------------------------------------------------- běh */
function saveCode() {
  if (!current) return;
  const all = JSON.parse(localStorage.getItem("rpraxe.code") || "{}");
  all[current.id] = cm.getValue();
  localStorage.setItem("rpraxe.code", JSON.stringify(all));
}

async function runCode(check) {
  if (!current && !check) { $("#out").textContent = "Vyber si úlohu vlevo, nebo si hraj v knihovně."; return; }
  saveCode(); busy(true);
  let res;
  try {
    const elapsed = openedAt ? Date.now() - openedAt : 0;
    res = await api("/api/run", { method: "POST", body: JSON.stringify({ task_id: current?.id || null, code: cm.getValue(), check: !!check, elapsed_ms: elapsed }) });
    if (check) openedAt = Date.now();
  }
  finally { busy(false); }
  paint(res);
  if (check && res.progress) {
    boot.today = res.progress; boot.streak = res.streak;
    $("#streak").textContent = res.streak ? `řada ${res.streak} dní` : "";
    const b = await api("/api/bootstrap"); boot.items = b.items; boot.today = b.today; renderPlan(boot.items); renderMinutes();
    if (res.next && (res.check || {}).pass) {
      toast(`Správně. Doporučuju pak: ${res.next.title}`);
    }
  }
}

function paint(res) {
  const out = $("#out");
  const bits = [];
  if (res.stdout) bits.push(esc(res.stdout));
  if (res.last && !res.stdout) bits.push(esc(res.last));
  if (res.stderr) bits.push(`<span class="w">${esc(res.stderr)}</span>`);
  if (res.error) bits.push(`<span class="e">Chyba: ${esc(res.error)}</span>`);
  const prostredi = (res.env || []).map(r => `<div class="envrow">${esc(r)}</div>`).join("");
  if (bits.length) {
    out.innerHTML = bits.join("\n");
  } else if (prostredi) {
    out.innerHTML = `<span class="muted">R nic nevypsal — u přiřazení typu <code>x &lt;- ...</code> je to normální,`
      + ` R vypíše jen to, co nezadáš do proměnné. Napiš na další řádek název (třeba <code>head(mzdy)</code>),`
      + ` pokud to chceš vidět.<div class="envtitle">co máš teď v prostředí:</div>${prostredi}</span>`;
  } else {
    out.innerHTML = `<span class="muted">R nic nevypsal — zkus výsledek vypsat, třeba <code>head(mzdy)</code>.</span>`;
  }
  const v = $("#verdict");
  const c = res.check;
  if (c && c.pass !== null && c.pass !== undefined) {
    v.style.display = "";
    v.className = "verdict " + (c.pass ? "p" : "f");
    v.textContent = c.pass ? ("✓ " + (c.msg || "Správně — uloženo do tvé rady.")) : ("… " + (c.msg || "Ještě to nesedí. Zkus to znovu."));
    if (c.pass && current) { current.solved = true; const it = boot.items.find(x => x.id === current.id); if (it) it.solved = true; renderPlan(boot.items); }
    if (!c.pass && cm.getValue().length > 30) coach("check", c.msg);
  } else if (res.error) {
    v.style.display = ""; v.className = "verdict f";
    v.textContent = "R to vrátilo chybu — dole je výpis. Koukám na to s tebou.";
    coach("error", res.error);
  } else { v.style.display = "none"; }
  const pl = $("#plots");
  if (res.plots && res.plots.length) {
    pl.style.display = ""; pl.innerHTML = res.plots.map(p => `<img src="data:image/png;base64,${p}" alt="graf">`).join("");
  } else { pl.style.display = "none"; pl.innerHTML = ""; }
}

async function coach(mode, msg) {
  const box = $("#hintbox");
  box.innerHTML = '<div class="coach"><span class="spin"></span> kouč se na to dívá…</div>';
  const r = await api("/api/coach", { method: "POST", body: JSON.stringify({
    task_id: current?.id || null, code: cm.getValue(), error: mode === "error" ? msg : null,
    check_msg: mode === "check" ? msg : null, mode }) });
  box.innerHTML = `<div class="coach"><strong>Kouč:</strong> ${esc(r.text)}</div>`;
}

/* --------------------------------------------------------------- panely */
async function loadLib() {
  const d = await api("/api/tasks");
  const sel = $("#f-lesson");
  if (sel.options.length <= 1)
    sel.innerHTML = '<option value="">všechny lekce</option>' + Object.entries(d.lessons)
      .map(([n, l]) => `<option value="${n}">${n}. ${esc(l.title)}</option>`).join("");
  const render = () => {
    const lv = sel.value, st = $("#f-status").value, q = $("#f-q").value.toLowerCase();
    const rows = d.tasks.filter(t => (!lv || t.lesson == lv) && (!st || t.status === st) &&
      (!q || (t.title + " " + t.zadani).toLowerCase().includes(q)));
    $("#tasks").innerHTML = "<tr><th>úloha</th><th>lekce</th><th>obdrž</th><th>pokusa</th><th></th></tr>" +
      rows.map(t => `<tr>
        <td><strong>${esc(t.title)}</strong><div class="tiny muted">${esc((t.skills || []).join(", "))} · ${esc(t.id)}</div></td>
        <td>${t.lesson}</td><td>${Number(t.level).toFixed(1)}</td>
        <td>${t.passed}/${t.attempts}</td>
        <td>${t.status === "draft" ? `<span class="pill">${t.moje ? "tvůj koncept" : "koncept"}</span>` : ""}
            ${t.zahozena ? '<span class="pill">zahozeno</span>' : ""}
            <button data-id="${esc(t.id)}" class="ghost pick">do dneška</button>
            <button data-id="${esc(t.id)}" class="ghost look" title="úkoly, řešení a kontrola zvlášť">prozkoumat</button>
            ${["teacher", "admin"].includes(ROLE)
              ? `<button data-id="${esc(t.id)}" class="ghost upravit" title="upravit v editoru">upravit</button>
                <button data-id="${esc(t.id)}" class="ghost schvalit" title="ukázat studentům">schválit</button>
                <button data-id="${esc(t.id)}" class="ghost zahodit" title="schovat před studenty">zahodit</button>`
              : `${t.moje && t.status === "draft"
                  ? `<button data-id="${esc(t.id)}" class="ghost my-edit" title="dopsat a nechat ověřit">upravit</button>` : ""}
                 <button data-id="${esc(t.id)}" class="ghost my-drop" data-zahozeno="${t.zahozena ? 1 : 0}">${t.zahozena ? "obnovit" : "zahodit"}</button>`}</td></tr>`).join("");
    if (!["teacher", "admin"].includes(ROLE)) $$("#tasks .look").forEach(b => b.remove());
    $$("#tasks .my-edit").forEach(b => b.onclick = async () => {
      const u = await api(`/api/tasks/${b.dataset.id}`);
      if (!u || !u.id) { toast("úlohu jsem nenašel"); return; }
      u.check = u.check ?? u.check_r; nactiDatasety(); otorEditor(u);
    });
    $$("#tasks .my-drop").forEach(b => b.onclick = () => {
      const zahozene = b.dataset.zahozeno === "1";
      const deal = async () => {
        await api("/api/drop", { method: "POST",
          body: JSON.stringify({ task_id: b.dataset.id, obnovit: zahozene }) });
        toast(zahozene ? "úloha je zpátky" : "zahazeno — nikdo ti ji už nenabídne");
        loadLib();
      };
      zahozene ? deal() : potvrd(`Opravdu zahodit ${b.dataset.id}? Jen u sebe; banka zůstane celá.`,
                                deal, "zahodit");
    });
    $$("#tasks .look").forEach(b => b.onclick = () => openReview(b.dataset.id));
    $$("#tasks .schvalit").forEach(b => b.onclick = () => zmenStav(b.dataset.id, "approved"));
    $$("#tasks .zahodit").forEach(b => b.onclick = () => potvrd(
      `Opravdu zahodit ${b.dataset.id}? Studenti ji neuvidí; smazat se dá úplně později.`,
      () => zmenStav(b.dataset.id, "retired"), "zahodit"));
    $$("#tasks .upravit").forEach(b => b.onclick = async () => {
      const u = await api(`/api/tasks/${b.dataset.id}`);
      if (u && u.id) upravUlohu(u); else toast("úlohu jsem nenašel");
    });
    $$("#tasks .pick").forEach(b => b.onclick = async () => {
      await api("/api/pick", { method: "POST", body: JSON.stringify({ task_id: b.dataset.id }) });
      toast("Přidáno do dnešní dávky."); await loadBoot(); show("today");
    });
  };
  [sel, $("#f-status")].forEach(e => e.onchange = render);
  $("#f-q").oninput = render; render();
}

let tahakHtml = "";
async function loadTahak() {
  if (!tahakHtml) {
    const c = await api("/api/cheatsheet");
    const radek = (r) => String(Array.isArray(r) ? r.join("  ") : r ?? "");
    tahakHtml = Object.entries(c.cheatsheet || {}).map(([k, v]) =>
      `<h3>${esc(k)}</h3><pre>${esc((Array.isArray(v) ? v : [v]).map(radek).join("\n"))}</pre>`).join("")
      || "<p class='muted'>Tahák zatím není připravený.</p>";
  }
  $("#sheet").innerHTML = tahakHtml;
}

let chybyHtml = "";
async function fillGlossary() {
  // karta „Pokud narazíš na chybu“ — bez toho zůstane prázdná a mate žáka
  const box = $("#glossary");
  if (!box) return;
  if (!chybyHtml) {
    try {
      const c = await api("/api/cheatsheet");
      chybyHtml = (c.error_help || []).map(([chyba, rada]) =>
        `<p class="tiny"><code>${esc(chyba)}</code><br><span class="muted">${esc(rada)}</span></p>`
      ).join("") || "<p class='tiny muted'>tipy zatím nejsou.</p>";
    } catch { chybyHtml = "<p class='tiny muted'>tipy se nepodařilo načíst.</p>"; }
  }
  box.innerHTML = chybyHtml;
}

async function loadProg() {
  const p = await api("/api/progress");
  fillGlossary();
  const rate = p.total ? Math.round(100 * p.passed / p.total) : 0;
  $("#kpis").innerHTML = [
    ["Úspěšnost na první dobrou", `${p.first_try_rate ?? "—"} %`, "bez nápovědy a bez opakování"],
    ["Vyplněné úlohy", p.total ?? 0, `${p.days_active ?? 0} dní procvičování`],
    ["Řada", p.streak, "dní za sebou"],
    ["Odklikáno", `${Math.round(p.minutes_total || 0)} min`, "celkem v systému"],
  ].map(([l, v, s]) => `<div class="card"><div class="muted tiny">${l}</div><div class="kpi">${v}</div>
      <div class="tiny muted">${s}</div></div>`).join("");
  const days = p.by_day || [];
  const max = Math.max(1, ...days.map(d => d.n || 0));
  $("#spark").innerHTML = Array.from({ length: 30 }, (_, i) => {
    const d = days.find(x => x.d === new Date(Date.now() - (29 - i) * 864e5).toISOString().slice(0, 10));
    return `<i style="height:${d ? Math.max(8, (d.n / max) * 100) : 3}%;opacity:${d ? (d.p ? .95 : .35) : .12}"
      title="${d ? d.d + ": " + d.p + "/" + d.n : ""}"></i>`;
  }).join("");
  $("#spark-lbl").textContent = "plné = úlohy, světlé = zkoušely se ale neprošly";
  // odhad úrovně: krátký proužek jen tam, kde už něco změřeno je; jinak mate prázdný
  const zmerene = (p.skills || []).filter(s => (s.n || 0) > 0);
  $("#skillbars").innerHTML = (p.skills || []).map(s => {
    const n = s.n || 0;
    const prouzek = n > 0
      ? `<span class="minibar" title="odhad úrovně ${s.theta.toFixed(2)} (škála ~0,5 až 3,5)">`
        + `<i style="width:${Math.min(100, s.theta / 3.5 * 100)}%"></i></span>`
      : `<span class="minibar empty" title="zatím neměřeno"></span>`;
    return `<div class="skillrow"><span class="sl" title="${esc(s.key)}">${esc(s.label)}</span>${prouzek}`
      + `<span class="tiny muted num">${n}×</span></div>`;
  }).join("") || "<p class='muted tiny'>zatím nic — po prvních pokusech se tady objeví tvůj profil.</p>";
  const lbl = $("#skill-lbl");
  if (lbl) lbl.textContent = zmerene.length
    ? `Proužek = odhad úrovně (0,5 = základy, 3,5 = pokročilé), číslo u toho = kolik pokusů k tomu už máme. `
      + `Tmavý proužek = zatím nic změřeného.`
    : "Zatím nic změřeného — po prvních úlohách se tady objeví tvůj profil.";
  $("#hard").innerHTML = (p.hard || []).length
    ? "<ul>" + p.hard.map(h => `<li><a href='#' data-id='${esc(h.task)}'>${esc(h.task)}</a> — ${h.lapses}× zabrzda</li>`).join("") + "</ul>"
    : "<p class='muted tiny'>zatím nic, co by se vracelo</p>";
  $("#recent").innerHTML = "<tr><th>kdy</th><th>úloha</th><th>výsledek</th><th>nápovědy</th></tr>" +
    (p.recent || []).map(a => `<tr><td class="tiny muted">${new Date(a.ts * 1000).toLocaleString("cs-CZ")}</td>
      <td>${esc(a.title)}</td><td>${a.ok ? '<span class="ok">✓</span>' : '<span class="err">✗</span>'}</td>
      <td>${a.hints || 0}</td></tr>`).join("");
  vykresliTyden(p.tyden);
  vykresliOpakovani(p.opakovani);
  loadTahak();
  nactiPoznamky().then(vykresliSeznamPoznamek);
  $$("#hard a").forEach(a => a.onclick = e => { e.preventDefault(); openTask(a.dataset.id); show("today"); });
}

/** Týdenní souhrn — aby student poznal, jestli ten týden vůbec něco byl. */
function vykresliTyden(tyden) {
  const box = $("#tyden");
  if (!box) return;
  const d = tyden || {};
  if (!d.pokusy) {
    box.innerHTML = `<p class="muted tiny">Tenhle týden zatím žádné pokusy.
      Stačí jedna úloha a denní řada se rozjíždí.</p>`;
    return;
  }
  const slabsi = (d.slabsi || []).map(s => esc(s.label)).join(", ");
  box.innerHTML = `<div class="row" style="gap:14px;flex-wrap:wrap">
      <div><div class="kpi">${d.pokusy}</div><div class="tiny muted">pokusů</div></div>
      <div><div class="kpi">${d.uspesnost} %</div><div class="tiny muted">úspěšných</div></div>
      <div><div class="kpi">${d.minuty}</div><div class="tiny muted">minut</div></div>
      <div><div class="kpi">${d.aktivni_dny}/7</div><div class="tiny muted">dnů s cvičením</div></div>
    </div>
    <p class="tiny muted" style="margin-top:8px">${d.uloh} různých úloh ·
      ${d.poznamek ? d.poznamek + " poznámek" : "bez poznámek"}</p>
    ${slabsi ? `<p class="tiny">Slabší místa: ${slabsi}</p>` : ""}`;
}

/** Rozvrh opakování: co je dnes a co se chystá. */
function vykresliOpakovani(opakovani) {
  const box = $("#opakovani");
  if (!box) return;
  const d = opakovani || {};
  const radek = (x, retezec) => `<li><a href="#" data-id="${esc(x.task)}">${esc(x.title || x.task)}</a>
    <span class="tiny muted">${retezec}</span>${x.lapses ? ` <span class="pill">${x.lapses}× těžké</span>` : ""}</li>`;
  const dnes = (d.dnes || []).map(x => radek(x, "dnes")).join("");
  const blizko = (d.blizko || []).slice(0, 6)
    .map(x => radek(x, x.za_dny <= 1 ? "zítra" : `za ${Math.round(x.za_dny)} dní`)).join("");
  box.innerHTML = `${dnes ? `<strong class="tiny">Dnes</strong><ul class="tiny">${dnes}</ul>` : ""}
    ${blizko ? `<strong class="tiny">Brzy</strong><ul class="tiny">${blizko}</ul>`
             : '<p class="tiny muted">Nic dalšího nenasbíraného — opakování se naplní z procvičovaných úloh.</p>'}`;
  $$("#opakovani a").forEach(a => a.onclick = e => {
    e.preventDefault(); openTask(a.dataset.id); show("today");
  });
}

/* ------------------------------------------------------- Nápověda (Help) */
/* Obsah je přepsaný v každém jazyce zvlášť — rozhraní překládá slovník,
 * ale výklad se špatně skládá z frází, proto je tady celý text. */
const HELP = {
  cs: {
    titulek: "Návod, jak se systémem pracuje",
    sekce: [
      ["Denní rutina", [
        "Záložka Dnes ti namíchá krátkou dávku úloh z látky, kterou zrovna probíráte. Cíleně je krátká — 15 až 30 minut.",
        "U úlohy vidíš zadání, data a okno pro tvůj R kód. Kód spustí tlačítko spustit, správnost ověří tlačítko zkontrolovat.",
        "Když nevíš dál, tak napověda odkrývá nápovědu po kouscích. Tlačítko kouč vysvětlí konkrétní chybu, kterou vypsalo R.",
        "Řešení se ukazuje až na požádání a systém si ho poznamená — lepší je nejdřív to zkusit sám.",
      ]],
      ["Kde co najdeš", [
        "Knihovna — všechny úlohy, dá se filtrovat podle lekce, obtížnosti a hledat ve slovech. Tlačítkem do dneška si úlohu přidáš do své dávky.",
        "Progres — úspěšnost na první dobrou, řada dní, odhady dovedností a seznam témat, kde se to nejvíc zadrhává. Dole je historie a CSV export.",
        "Tahák — rychlý opis základů R, který zůstává na stránce, žádná vyskakovací okna.",
        "Poznámky — u každé úlohy si můžeš nechat vlastní poznámku ve větším okně; uloží se na server a uvidíš ji i z jiného počítače.",
      ]],
      ["K čemu jsou poznámky", [
        "Poznámka není hodnocení ani zpráva učiteli. Je to tvůj vlastní záznam u konkrétní úlohy: co tě na ní napálilo, na co si příště dát pozor.",
        "Proč to má smysl: za měsíc si neneš, v čem jsi tehdy chyboval. U úlohy, která tě stála půl hodiny, je věta „pozor, group_by počítá i řádky s NA“ to nejcennější, co systém umí uchovat.",
        "Učitel a správce je vidí v přehledu třídy — díky nim poz ná, kde skupina zápasí, i když počet pokusů vyzná dobře.",
        "Kouč k nim nic neposílá; poznámky zůstávají tvůj text. Klidně do nich zapiš i poznámku ke svému skriptu.",
      ]],
      ["Nastavení účtu", [
        "V menu uživatele je Nastavení: motiv (tmavý, světlý nebo podle systému), jazyk rozhraní a délka denní dávky.",
        "Nastavení se ukládá na server, ne jen do prohlížeče — tak tě pozná i na jiném zařízení.",
        "Model, který systém používá, si uživatel nevolí. Nastavuje ho správce, aby měli všichni stejného kouče.",
      ]],
      ["Když pracuješ ve třídě (učitel)", [
        "Tříd může být víc — klidně se stejnými žáky v různých skupinách (ránní a odpolední kurz). Učitel si založí vlastní a vybere do ní účty; jeden účet můž být ve třídách několika.",
        "Nová třýd: v záložce Třída je karta Třídy — napiš název, vyber žáky ze seznamu (Ctrl/Cmd přidá víc) a ulož. Vybranou třýdu lze upravit i smazat; žáci zůstanou, zmizí jen sdružení.",
        "Přehled žáků ukazuje, v jakých třýdách kdo je.",
        "Záložka Třída ukazuje, komu se co daří a kde se žáci opakovaně potýkají se stejnou látkou.",
        "Nové úlohy se přidávají ve správě; vygeneruješ je tlačítkem, nebo napíšeš vlastní.",
        "U každé úlohy je tlačítko prozkoumat: ukáže zadání, kostru, řešení a kontrolní kód zvlášť, aby se na to dalo lidsky podívat.",
        "V tom okně je i strojové ověření (spustí řešení, pak prázdný kód) a názor modelu. Rozhoduje pořád člověk — schvaluje se tlačítkem.",
        "Koncept (draft) se žákům neukáže, dokud není schválený.",
      ]],
      ["Správa systému", [
        "Účty — přidání člověka, role (student, učitel, správce), vygenerování hesla.",
        "Modely — provider, adresa serveru, model pro povídání i pro tvorbu úloh, API klíč. Uloží se do souboru v adresáři state, ne do obrazu.",
        "Přihlašování — heslem, nebo přes jednotné přihlášení (SSO) z brány před celým domenovým jménem. Vypínač a údaj o hlavičkách jsou tady.",
        "Zálohy — ruční snímek databáze a seznam snímků. Načtení ze zálohy přepíše současná data, proto se ptá na opsání slova OBNOVIT; před obnovou se vždy udělá pojistka.",
      ]],
      ["Bezpečnost a data", [
        "Tvoje R kód se spouští v oddělené nádobě bez přístupu do sítě — kód se k tvým datům dostane, ven se nedostane nic.",
        "Zálohy a databáze jsou na tvém serveru; pokud správce nenastaví externí model, data neopouštějí dům.",
      ]],
    ],
    klavesy: [
      ["Ctrl + Enter", "spustit kód"], ["Ctrl + Shift + Enter", "zkontrolovat řešení"],
      ["Esc", "zavřít okno"],
    ],
  },
  en: {
    titulek: "How the system works",
    sekce: [
      ["Daily routine", [
        "The Today tab mixes a short set of tasks from the part of the course you are in. It is deliberately short: 15 to 30 minutes.",
        "Each task shows the assignment, the data and an editor for your R code. Run runs the code, check verifies the result.",
        "Stuck? hint uncovers one hint at a time; the coach button explains the exact R error on screen.",
        "The solution appears only when you ask, and the system notes that you asked — try it yourself first.",
      ]],
      ["Where things are", [
        "Library — every task, filterable by lesson and difficulty, with text search. Add to today puts a task into your own set.",
        "Progress — first-try success, day streak, estimated skills and the topics where you keep getting stuck, plus history and CSV export.",
        "Cheat sheet — a quick R summary that stays on the page; no pop-up windows.",
        "Notes — every task can carry your own note written in a proper text area, stored on the server and visible from any device.",
      ]],
      ["What the notes are for", [
        "A note is not a grade and not a report to the teacher. It is your own line next to a specific task: what caught you out, what to watch for next time.",
        "Why bother: in a month you will not remember what tripped you up. For a task that took half an hour, “careful, group_by counts NA rows too” is the most valuable thing the system can keep.",
        "Teachers and admins see them in the class overview, so they can spot a struggle even when the attempt count looks fine.",
        "The coach never receives them; notes stay your own text.",
      ]],
      ["Account settings", [
        "In the user menu: theme (dark, light or system), interface language and the length of the daily set.",
        "Settings live on the server, not only in the browser, so another device sees the same thing.",
        "Users do not pick the model. The administrator sets it so everyone gets the same coach.",
      ]],
      ["Teaching a class", [
        "The Class tab shows who is doing well and where students keep hitting the same topic.",
        "There can be several classes, even with the same students in different groups. A teacher creates their own and picks accounts for it; one account can belong to several classes.",
        "To add one: in the Class tab use the Classes card — type a name, pick students from the list (Ctrl/Cmd adds more) and save. A selected class can be edited or deleted; students stay, only the grouping disappears.",
        "The student list shows which classes each person belongs to.",
        "New tasks are added in Administration, generated by the model or written by hand.",
        "Every task has an inspect button: assignment, starter, solution and the checking code shown separately for a human read.",
        "That window also runs a machine check (solution, then empty code) and asks the model for criticism. A human still approves it.",
        "Students never see a draft until it is approved.",
      ]],
      ["Administration", [
        "Accounts — add a person, set a role (student, teacher, admin), generate a password.",
        "Models — provider, server address, chat and writing model, API key. Saved into the state directory, not into the image.",
        "Sign-in — password, or single sign-on from a gateway in front of the whole domain. The switch and header names are here.",
        "Backups — a manual snapshot plus the list of stored ones. Restoring overwrites current data, so it asks you to type RESTORE; a safety copy is always made first.",
      ]],
      ["Safety and data", [
        "Your R code runs in a separate container without network access — it can read its own data, nothing leaves.",
        "Backups and the database stay on your server; unless the admin enables an external model, data stays home.",
      ]],
    ],
    klavesy: [["Ctrl + Enter", "run code"], ["Ctrl + Shift + Enter", "check solution"], ["Esc", "close dialog"]],
  },
  sk: {
    titulek: "Návod, ako so systémom pracovať",
    sekce: [
      ["Denná rutina", [
        "Záložka Dnes ti namieša krátku dávku úloh z látky, ktorú práve preberáte. Zámerne je krátka — 15 až 30 minút.",
        "Kód spustí tlačidlo spustiť, správnosť overí tlačidlo skontrolovať.",
        "Keď nevieš ďalej, nápoveda odkrýva rady po kúskoch a tlačidlo kouč vysvetlí konkrétnu chybu R.",
        "Riešenie sa ukáže až na požiadanie a systém si poznamená, že si sa naň pozrel.",
      ]],
      ["Kde čo nájdeš", [
        "Knižnica — všetky úlohy, filter podľa lekcie a obtiažnosti, vyhľadávanie; tlačidlo do dneška pridá úlohu do tvojej dávky.",
        "Progres — úspešnosť na prvýkrát, séria dní, odhady zručností a témy, kde sa to zachytáva.",
        "Tahák — rýchly opis základov R, žiadne vyskakovacie okná.",
        "Poznámky — pri úlohe si môžeš nechať vlastnú poznámku; uloží sa na server a uvidíš ju aj z iného počítača.",
      ]],
      ["Na čo sú poznámky", [
        "Poznámka nie je známka ani odkaz pre učiteľa. Je to tvoj vlastný záznam pri konkrétnej úlohe: čo ťa napálilo a na čo si dať pozor.",
        "O mesiac si nepamätáš, v čom si chyboval. Pri úlohe, ktorá trvala pol hodiny, je veta „pozor, group_by počíta aj riadky s NA“ to najcennejšie, čo systém uchová.",
        "Učiteľ a správca ich vidia v prehľade triedy, takže všimnú, kde skupina zápasí, aj keď počet pokusov vyzerá dobre.",
        "Kouč ich nedostáva — poznámky ostávajú tvoj text.",
      ]],
      ["Nastavenie účtu", [
        "V používateľskom menu: motív (tmavý, svetlý alebo systémový), jazyk rozhrania a dĺžka dennej dávky.",
        "Nastavenia sú na serveri, nie len v prehliadači, takže ťa pozná aj iné zariadenie.",
        "Model si používateľ nevolí — nastavuje ho správca, aby mali všetci rovnakého kouča.",
      ]],
      ["Triedy", [
        "Tried môže byť viac, aj s tými istými žiakmi v rôznych skupinách. Učiteľ si založí vlastnú a vyberie do nej účty; jeden účet môže byť v niekoľkých triedach.",
        "Novú triedu vytvoríš v karte Triedy: napíš názov, vyber žiakov zo zoznamu (Ctrl/Cmd pridá viac) a ulož. Vybranú triedu môžeš upraviť alebo zmazať — žiaci ostanú, zmizne len združenie.",
        "Prehľad žiakov ukazuje, v ktorých triedach kto je.",
      ]],
      ["Keď vyučuješ (učiteľ)", [
        "Nové úlohy sa pridávajú v správe — vygeneruješ ich, alebo napíšeš vlastné.",
        "Tlačidlo preskúmať ukáže zadanie, kostru, riešenie a kontrolný kód osobitne, aby sa na ne dalo pozrieť človekom.",
        "V tom okne je aj strojové overenie (spustí riešenie, potom prázdny kód) a názor modelu. Rozhoduje človek — schvaľuje sa tlačidlom.",
        "Pred uložením sa úloha sama overí: musí prejsť vlastným riešením a nesmie prejsť prázdny kód. Keď to nevyjde, uloženie sa odmietne a pôvodný text ostane.",
        "Koncept sa žiakom neukáže, kým nie je schválený; upraviť ho ide cez upraviť v editore.",
      ]],
      ["Správa", [
        "účty — pridať človeka, nastaviť rolu, vygenerovať heslo.",
        "Modely — poskytovateľ, adresa, model na rozhovor a na tvorbu úloh, kľúč. Ukladá sa do adresára state, nie do obrazu.",
        "Prihlasovanie — heslom, alebo cez jednotné prihlásenie z brány pred celou doménou.",
        "Zálohy — ručný snímok a zoznam snímek. Obnova prepíše súčasné dáta, preto chce opsanie slova OBNOVIT; pred obnovou sa vždy urobí poistka.",
      ]],
      ["Bezpečnosť a dáta", [
        "Tvoj R kód beží v oddelenej nádobe bez prístupu do siete — k svojim dátam sa dostane, von nič nedostane.",
        "Zálohy a databáza sú na tvojom serveri; pokiaľ správca nenastaví externý model, dáta neopúšťajú dom.",
      ]],
    ],
    klavesy: [["Ctrl + Enter", "spustiť kód"], ["Ctrl + Shift + Enter", "skontrolovať riešenie"],
              ["Esc", "zavrieť okno"]],
  },
};

function renderHelp() {
  const box = $("#help-obsah");
  if (!box) return;
  const jazyk = LANG;                         // kráčí s jazykem rozhraní
  const data = HELP[jazyk] || HELP.en;
  const odkazy = jazyk === "cs"
    ? "Detaily pro provoz (self-hosting, SSO, formát banky úloh) jsou v souborech docs/ v repozitáři."
    : "Operational details (self-hosting, SSO, task bank format) live in the docs/ folder of the repository.";
  box.innerHTML = `<div class="card">
      <h3>${esc(data.titulek)}</h3>
      ${data.sekce.map(([nadpis, odstavce]) => `<h4 class="tiny" style="margin-top:14px">${esc(nadpis)}</h4>
        <ul class="tiny muted">${odstavce.map(o => `<li>${esc(o)}</li>`).join("")}</ul>`).join("")}
      <h4 class="tiny" style="margin-top:14px">Klávesy</h4>
      <ul class="tiny muted">${data.klavesy.map(([k, v]) => `<li><code>${esc(k)}</code> — ${esc(v)}</li>`).join("")}</ul>
      <p class="tiny muted" style="margin-top:14px">${esc(odkazy)}</p>
    </div>`;
  translateDom(box);
}

/* --------------------------------------------- pohled na úlohu pro učitele */
function kodBlock(nadpis, text, jazyk) {
  const obsah = (text || "").trim();
  if (!obsah) return "";
  return `<h4 class="tiny" style="margin-top:14px">${esc(nadpis)}</h4>
    <pre class="code tiny"${jazyk ? "" : " style=\"white-space:pre-wrap\""}>${esc(obsah)}</pre>`;
}

async function openReview(id) {
  const starsi = document.getElementById("reviewmodal");
  if (starsi) starsi.remove();
  const modal = document.createElement("div");
  modal.className = "modal"; modal.id = "reviewmodal";
  modal.setAttribute("role", "dialog"); modal.setAttribute("aria-modal", "true");
  modal.innerHTML = `<div class="card" style="max-width:900px;width:min(900px,94vw);max-height:88vh;overflow:auto">
      <h3>${esc(t("Úloha detailně"))} <code class="tiny">${esc(id)}</code></h3>
      <p class="tiny muted">${esc(t("Lidská kontrola generované úlohy — solution i kontrolní kód jsou vidět celé."))}</p>
      <div id="rev-obsah" class="tiny muted">${esc(t("načítám…"))}</div>
      <div class="row end" style="margin-top:14px;flex-wrap:wrap;gap:6px">
        <button class="ghost" id="rev-close" type="button">${esc(t("zavřít"))}</button>
        <button class="ghost" id="rev-edit" type="button">${esc(t("upravit v editoru"))}</button>
        <button class="ghost" id="rev-ai" type="button">${esc(t("nechat zkontrolovat modelem"))}</button>
        <button class="ghost" id="rev-fix" type="button">${esc(t("nechat opravit modelem"))}</button>
        <button class="primary" id="rev-run" type="button">${esc(t("ověřit spuštěním"))}</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  translateDom(modal);
  modal.onclick = e => { if (e.target === modal) modal.remove(); };
  modal.querySelector("#rev-close").onclick = () => modal.remove();

  const d = await api(`/api/tasks/${id}/review`);
  if (!modal.isConnected) return;            // mezitím se zavřelo nebo otevřelo jiné
  const u = d.uloha || {};
  modal.querySelector("#rev-edit").onclick = () => { modal.remove(); upravUlohu({ ...u, id }); };
  modal.querySelector("#rev-fix").onclick = async () => {
    const vysledek = modal.querySelector("#rev-vysledek");
    if (!vysledek) return;
    vysledek.innerHTML = `<p class="tiny muted">${esc(t("model přepisuje úlohu, ať projde…"))}</p>`;
    let r;
    try { r = await api(`/api/tasks/${id}/autofix`, { method: "POST", body: "{}" }); }
    catch (e) { vysledek.innerHTML = `<p class="err">${esc(t("model není dostupný"))}</p>`; return; }
    if (!modal.isConnected) return;
    const detail = r.detail || {};
    vysledek.innerHTML = `<p class="${r.ok ? "ok" : "err"}">${
        r.ok ? "✓ " + esc(t("přepsáno a ověřeno — teď to projde"))
             : "✗ " + esc(t("po přepsání to pořád neprochází"))}</p>
      ${r.zprava ? `<p class="tiny">${esc(String(r.zprava))}</p>` : ""}
      <ul class="tiny muted">
        <li>${esc(t("řešení prošlo"))}: ${detail.reseni_proslo ? "✓" : "✗"} ·
          ${esc(t("prázdný kód"))}: ${detail.prazdny_kod_prosel ? "✗ " + esc(t("propustil kontrolu")) : "✓"} ·
          ${esc(t("startovací kostka"))}: ${detail.kostka_prosel ? "✗ " + esc(t("propustila kontrolu")) : "✓"}</li>
      </ul>
      ${r.opraveno ? `<h4 class="tiny" style="margin-top:10px">${esc(t("co model změnil"))}</h4>
        <p class="tiny">${esc(String((r.opraveno || {}).duvod || ""))}</p>
        <div class="row" style="margin-top:8px;gap:6px;flex-wrap:wrap">
          <button class="ghost" id="rev-reedit" type="button">${esc(t("upravit v editoru"))}</button>
        </div>` : ""}`;
    translateDom(vysledek);
    const znovu = vysledek.querySelector("#rev-reedit");
    if (znovu && r.uloha) znovu.onclick = () => { modal.remove(); upravUlohu(r.uloha); };
  };
  const stav = { draft: t("koncept"), approved: t("schváleno"), retired: t("schováno") }[u.status] || u.status;
  modal.querySelector("#rev-obsah").innerHTML = `
    <div class="row" style="gap:10px;flex-wrap:wrap">
      <span class="pill">${esc(stav)}</span>
      <span class="tiny muted">${esc(t("lekce"))} ${u.lesson} · ${esc(t("obdrž"))} ${Number(u.level).toFixed(1)}
        · ${(u.skills || []).join(", ")}</span>
      <span class="tiny muted">${esc(u.source || "")}</span>
    </div>
    <h4 class="tiny" style="margin-top:12px">${esc(t("zadání"))}</h4>
    <p style="white-space:pre-wrap">${esc(u.zadani || "")}</p>
    ${u.dataset ? `<p class="tiny">dataset: <code>${esc(u.dataset)}</code>
      ${d.nahled_dat && d.nahled_dat.stdout ? ` — <code>${esc(String(d.nahled_dat.stdout).slice(0, 400))}</code>` : ""}</p>` : ""}
    ${kodBlock(t("startovací kostka"), u.starter, true)}
    ${kodBlock(t("Řešení"), u.reseni, true)}
    ${kodBlock(t("kontrolní kód"), u.check, true)}
    <p class="tiny muted" style="margin-top:10px">${u.pokusy ? `${u.pokusy.pokusy} ${esc(t("pokusů"))}, ${u.pokusy.proselo} ${esc(t("prošlo"))}` : ""}</p>
    <div id="rev-vysledek" style="margin-top:10px"></div>`;
  translateDom(modal.querySelector("#rev-obsah"));

  modal.querySelector("#rev-run").onclick = async () => {
    const cil = modal.querySelector("#rev-vysledek");
    cil.innerHTML = `<p class="tiny muted">${esc(t("spouštím v sandboxu…"))}</p>`;
    let r;
    try {
      r = await api(`/api/tasks/${id}/verify`, { method: "POST", body: JSON.stringify({ schvalit: false }) });
    } catch (e) { cil.innerHTML = `<p class="err">${esc(t("ověření se nepovedlo"))}</p>`; return; }
    if (!modal.isConnected) return;
    const d2 = r.detail || {};
    cil.innerHTML = `<p class="${r.ok ? "ok" : "err"}">${r.ok ? "✓ " + esc(t("spočítáno a zkontrolováno"))
        : "✗ " + esc((d2.duvody || []).join(", ") || t("Úloha neprošla"))}</p>
      <ul class="tiny muted">
        <li>${esc(t("řešení prošlo"))}: ${d2.reseni_proslo ? "✓" : "✗"} · ${esc(t("prázdný kód"))}: ${d2.prazdny_kod_prosel ? "✗ " + t("propustil kontrolu") : "✓"}
          · ${esc(t("startovací kostka"))}: ${d2.kostka_prosel ? "✗ " + t("propustila kontrolu") : "✓"}</li>
        ${d2.graf ? `<li>${esc(t("vykreslil graf"))}</li>` : ""}
      </ul>
      ${d2.vystup_reseni ? `<pre class="code tiny">${esc(String(d2.vystup_reseni).slice(0, 1200))}</pre>` : ""}
      ${r.ok ? `<div class="row" style="margin-top:8px;gap:6px;flex-wrap:wrap">
        <button class="primary" id="rev-ok" type="button">${esc(t("schválit a pustit do nabídky"))}</button>
        <button class="ghost" id="rev-back" type="button">${esc(t("nechat v konceptech"))}</button></div>` : ""}`;
    translateDom(cil);
    if (r.ok) {
      modal.querySelector("#rev-ok").onclick = () => zmenStav(id, "approved");
      modal.querySelector("#rev-back").onclick = () => zmenStav(id, "draft");
    }
  };

  modal.querySelector("#rev-ai").onclick = async () => {
    const cil = modal.querySelector("#rev-vysledek");
    cil.innerHTML = `<p class="tiny muted">${esc(t("model přemýšlí…"))}</p>`;
    let n;
    try { n = await api(`/api/tasks/${id}/review-ai`, { method: "POST", body: "{}" }); }
    catch (e) { cil.innerHTML = `<p class="err">${esc(t("model není dostupný"))}</p>`; return; }
    if (!modal.isConnected) return;
    if (n.chyba) cil.innerHTML = `<p class="err">${esc(String(n.chyba))}</p>`;
    else cil.innerHTML = `<p class="${n.proslo ? "ok" : "err"}">${n.proslo ? "✓ " + esc(t("model neshledal závadu"))
        : "✗ " + esc(t("model našel závady"))}</p>
      ${(n.zavady || []).length ? `<ul class="tiny muted">${n.zavady.map(z => `<li>${esc(z)}</li>`).join("")}</ul>` : ""}
      ${n["obtížnost"] ? `<p class="tiny muted">${esc(t("obtížnost"))}: ${esc(n["obtížnost"])}</p>` : ""}
      ${n.ukázka ? `<pre class="code tiny">${esc(String(n.ukázka).slice(0, 400))}</pre>` : ""}`;
    translateDom(cil);
  };
}

async function zmenStav(id, status) {
  const r = await api(`/api/tasks/${id}/status`, { method: "POST", body: JSON.stringify({ status }) });
  if (r && r.ok) { toast(t("Úloha je teď: ") + status); const m = document.getElementById("reviewmodal"); if (m) m.remove(); loadLib(); }
  else toast((r && r.detail) || t("nepovedlo se"));
}

/* ------------------------------------------- poradce k vyberu poskytovatele */
/* Kde se bere adresa, kde klíč a jestliobecň je klíč vůbec potřeba — aby to
 * správce nemusel nikde hledat. Odkazy jsou jen na oficiální stránky. */
const PROVIDER_RADCE = {
  ollama: {
    klic: "Vlastní Ollama klíč nepotřebuje — proto je pole prázdné a přesto to funguje.",
    klic_vydajny: false,
    adresa: [
      ["Ollama na stejném stroji", "http://127.0.0.1:11434"],
      ["Ollama na jiném stroji v síti", "http://192.168.0.x:11434"],
    ],
    postup: "Modely nahraješ na serveru příkazem ollama pull <model>; seznam, který tu vidíš, " +
      "jde z adresy /api/tags.",
    odkazy: [["Dokumentace Ollamy", "https://docs.ollama.com"]],
  },
  openai: {
    klic: "Klíč musí být — bez něj brána vrátí 401. Vytvoříš ho u poskytovatele, jehož " +
      "adrese důvěruješ.",
    klic_vydajny: true,
    adresa: [
      ["OpenAI", "https://api.openai.com/v1"],
      ["GitHub Models (Copilot)", "https://models.inference.ai.azure.com"],
      ["Groq", "https://api.groq.com/openai/v1"],
      ["Together AI", "https://api.together.xyz/v1"],
      ["vlastní vLLM", "http://vlastni-server:8000/v1"],
    ],
    postup: "Tohle je OpenAI-kompatibilní rozhraní, takže dokud sedí adresa a klíč, je jedno, " +
      "kdo za ním stojí. Model se jmenuje přesně tak, jak ho poskytovatel vydává.",
    odkazy: [["OpenAI API keys", "https://platform.openai.com/api-keys"],
             ["GitHub Models", "https://github.com/marketplace/models"],
             ["Groq API keys", "https://console.groq.com/keys"],
             ["Together API keys", "https://api.together.xyz/settings/api-keys"]],
  },
  anthropic: {
    klic: "Klíč je povinný, posílá se hlavičkou x-api-key.",
    klic_vydajny: true,
    adresa: [["Anthropic", "https://api.anthropic.com"]],
    postup: "Jméno modelu je třeba claude-sonnet-4-5; max_tokens pro kontrolu doplňuje aplikace.",
    odkazy: [["Anthropic Console — API keys", "https://console.anthropic.com/settings/keys"]],
  },
  gemini: {
    klic: "Klíč je povinný; posílá se v adrese volání, proto ho nikam dál nedávej.",
    klic_vydajny: true,
    adresa: [["Google Gemini", "https://generativelanguage.googleapis.com"]],
    postup: "Modely mají verzi v názvu, např. gemini-2.5-flash; seznam se táhne z /v1beta/models.",
    odkazy: [["Google AI Studio — Get API key", "https://aistudio.google.com/apikey"]],
  },
};

function poradce(zkratka) {
  return PROVIDER_RADCE[zkratka] || { klic: "", klic_vydajny: false, adresa: [], postup: "", odkazy: [] };
}

/* -------------------------------------------------- karta: Modely (admin) */
async function renderAICard() {
  const box = $("#adm-ai");
  if (!box) return;
  let a;
  try { a = await api("/api/admin/ai"); } catch (e) { box.innerHTML = `<p class="err">${esc(t("není spojení"))}</p>`; return; }
  const moznosti = a.moznosti || [];
  const modely = a.modely || [];
  const vyberModelu = (ident, hodnota) => modely.length
    ? `<select id="${ident}">${modely.map(m => `<option value="${esc(m)}" ${m === hodnota ? "selected" : ""}>${esc(m)}</option>`).join("")}
       ${modely.includes(hodnota) ? "" : `<option value="${esc(hodnota)}" selected>${esc(hodnota)}</option>`}</select>`
    : `<input id="${ident}" value="${esc(hodnota || "")}" autocomplete="off" spellcheck="false"
         placeholder="jméno modelu, např. qwen3.5:9b">`;
  box.innerHTML = `
    <div class="grid g2">
      <div><label for="ai-provider">${esc(t("Poskytovatel"))}</label>
        <select id="ai-provider">${moznosti.map(p =>
          `<option value="${esc(p.zkratka)}" ${p.zkratka === a.poskytovatel ? "selected" : ""}>${esc(p.jmeno)}</option>`).join("")}</select></div>
      <div><label for="ai-adresa">${esc(t("Adresa serveru (endpoint)"))}</label>
        <input id="ai-adresa" value="${esc(a.adresa || "")}" autocomplete="off" spellcheck="false"></div>
    </div>
    <div class="rada" id="ai-rada"></div>
    <!-- pole s modely se generují, obě id jsou tahle: id="ai-model" id="ai-model-psani" -->
    <div class="grid g2">
      <div><label for="ai-model">${esc(t("Model pro povídání (kouč, nápovědy)"))}</label>
        ${vyberModelu("ai-model", a.model)}</div>
      <div><label for="ai-model-psani">${esc(t("Model pro tvorbu úloh"))}</label>
        ${vyberModelu("ai-model-psani", a.model_psani)}</div>
    </div>
    <label for="ai-klic">${esc(t("API klíč"))} <span class="tiny muted" id="ai-klic-popis"></span></label>
    <span class="pw"><input id="ai-klic" type="password" autocomplete="off"
        placeholder="${a.klic && a.klic.nastaveno ? esc(t("uloženo: ") + a.klic.ukazka) : esc(t("vyplň, pokud ho poskytovatel vyžaduje"))}">
      <button class="eye" type="button" data-eye="ai-klic" aria-pressed="false" title="${esc(t("ukázat"))}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg></button></span>
    <p class="tiny muted">${modely.length ? `${modely.length} ${esc(t("modelů stažených na adrese výše"))}`
      : esc(t("Seznam modelů se nezjistil — zkontroluj adresu a klíč, pak to zkus znovu."))}</p>
    <p class="tiny muted">${a.online ? "✓ " + esc(t("model odpovídá")) : "✗ " + esc(t("model neodpovídá"))} ${esc(a.hlaska || "")}</p>
    <p class="tiny muted" id="ai-stav" role="status"></p>
    <div class="row" style="margin-top:10px"><button id="ai-save" class="primary" type="button">${esc(t("uložit a vyzkoušet"))}</button></div>
    <p class="tiny muted" style="margin-top:8px">${esc(t("Volba platí pro celou instanci — uživatelé si model nevybírají. Klíč se ukládá do state/config.json (mód 600), do prohlížeče se nikdy nevrací."))}</p>`;
  translateDom(box);

  const poradenstvi = () => {
    const zkratka = $("#ai-provider").value;
    const r = poradce(zkratka);
    const p = moznosti.find(x => x.zkratka === zkratka) || {};
    $("#ai-rada").innerHTML = `
      <p class="tiny">${esc(r.postup || p.popis || "")}</p>
      ${r.adresa.length ? `<p class="tiny muted">${esc(t("Adresa se píše takto"))}:</p>
        <ul class="tiny muted">${r.adresa.map(([k, v]) => `<li>${esc(k)} — <code>${esc(v)}</code></li>`).join("")}</ul>` : ""}
      ${r.odkazy.length ? `<div class="row" style="gap:10px;flex-wrap:wrap;margin-top:4px">${
        r.odkazy.map(([k, v]) => `<a class="tiny" href="${esc(v)}" target="_blank" rel="noopener noreferrer">${esc(k)} ↗</a>`).join("")}</div>` : ""}`;
    const klic = $("#ai-klic");
    const vyzaduje = !!(p.venku || r.klic_vydajny);
    klic.required = vyzaduje;
    $("#ai-klic-popis").textContent = vyzaduje ? "— " + t("povinný") : "— " + t("nepovinný");
    klic.placeholder = (a.klic && a.klic.nastaveno && !klic.value)
      ? t("uloženo: ") + a.klic.ukazka : (vyzaduje ? t("bez klíče to nefunguje") : t("nechat prázdné"));
    // adresu vyměníme jen tehdy, je-li prázdná nebo patří jinému provideru
    const pole_adresa = $("#ai-adresa");
    const druha = moznosti.some(x => x.adresa === pole_adresa.value && x.zkratka !== $("#ai-provider").value);
    if (!pole_adresa.value || druha) pole_adresa.value = p.adresa || "";
    translateDom($("#ai-rada"));
  };
  $("#ai-provider").onchange = poradenstvi;
  poradenstvi();

  $("#ai-save").onclick = async () => {
    const stav = $("#ai-stav");
    const radek = poradce($("#ai-provider").value);
    const klic = $("#ai-klic").value.trim();
    const provider = moznosti.find(x => x.zkratka === $("#ai-provider").value) || {};
    if ((provider.venku || radek.klic_vydajny) && !klic && !(a.klic && a.klic.nastaveno)) {
      stav.className = "tiny err";
      stav.textContent = t("Tenhle poskytovatel klíč vyžaduje — bez něj to nebude mluvit.");
      $("#ai-klic").focus();
      return;
    }
    $("#ai-save").disabled = true;
    stav.className = "tiny muted"; stav.textContent = t("zkouším…");
    const r = await api("/api/admin/ai", { method: "POST", body: JSON.stringify({
      poskytovatel: $("#ai-provider").value, adresa: $("#ai-adresa").value.trim(),
      klic: klic || undefined, model: $("#ai-model").value.trim(),
      model_psani: $("#ai-model-psani").value.trim() }) });
    $("#ai-save").disabled = false;
    if (r && r.ok) {
      stav.innerHTML = r.online
        ? `✓ ${esc(t("uloženo, model odpovídá"))}`
        : `✗ ${esc(t("uloženo, ale model neodpovídá"))}: ${esc(r.hlaska || "")}`;
      toast(t("Nastavení modelu uloženo."));
      renderAICard();
    } else { stav.className = "tiny err"; stav.textContent = (r && r.detail) || t("nepovedlo se"); }
  };
}

/* ----------------------------------------- karta: Přihlašování (admin) */
const SSO_NAVOD = {
  cs: `<p>Brána ověří člověka a teprve pak pustí požadavek sem. Řekne jméno hlavičkou
    (výchozí <code>Remote-User</code>) a volitelně skupiny druhou hlavičkou, podle kterých
    určí roli. Aby tu někdo nemohl poslat <code>Remote-User: reditel</code> sám, posílá se
    ještě sdílené heslo hlavičkou <code>x-rpraxe-sso</code> — musí sedět na bráně i tady.</p>
    <p class="tiny muted">Kde to vzít: heslo vymysli ty — stiskni <em>vygenerovat</em> nebo na
    serveru <code>openssl rand -hex 32</code> — a <strong>stejné</strong> vepiš do nastavení
    brány (u Caddyho jako proměnnou prostředí <code>RPRAXE_SSO_SECRET</code>).</p>
    <pre class="code tiny">handle /r-praxe/* {
    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.priklad.example
        copy_headers Remote-User Remote-Groups
    }
    reverse_proxy rpraxe-app:8080 {
        header_up Remote-User {upstream_remote-user}
        header_up Remote-Groups {upstream_remote-groups}
        header_up X-Rpraxe-SSO {env.RPRAXE_SSO_SECRET}
    }
}</pre>
    <ul class="tiny muted">
      <li>Brána musí <code>Remote-User</code> <strong>přepisovat</strong>, ne jen přidávat.</li>
      <li>Ověř to: <code>curl -H 'Remote-User: kdokoliv' …/api/whoami</code> — musí hlásit odhlášení.</li>
      <li>Heslo nepatří do URL, jen do hlavičky.</li>
      <li>Účet se po prvním přihlášení přes bránu založí sám; heslo mu pak nastav ve Správě.</li>
      <li>Celé povídání je v <code>docs/sso.md</code> v repozitáři.</li>
    </ul>`,
  en: `<p>The gateway authenticates the person and only then forwards the request. It passes the
    user name in a header (default <code>Remote-User</code>) and optionally groups in another
    header, which is how the role is decided. To stop anyone sending their own
    <code>Remote-User: boss</code>, the gateway also sends a shared secret in the
    <code>x-rpraxe-sso</code> header — it has to match on both sides.</p>
    <p class="tiny muted">Where to get it: you invent it — press <em>generate</em> or run
    <code>openssl rand -hex 32</code> — and put the <strong>same</strong> value into the gateway.</p>
    <pre class="code tiny">handle /r-praxe/* {
    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.example.com
        copy_headers Remote-User Remote-Groups
    }
    reverse_proxy rpraxe-app:8080 {
        header_up Remote-User {upstream_remote-user}
        header_up Remote-Groups {upstream_remote-groups}
        header_up X-Rpraxe-SSO {env.RPRAXE_SSO_SECRET}
    }
}</pre>
    <ul class="tiny muted">
      <li>The gateway must <strong>overwrite</strong> <code>Remote-User</code>, not just add it.</li>
      <li>Test it: <code>curl -H 'Remote-User: anyone' …/api/whoami</code> must stay signed out.</li>
      <li>The secret belongs in a header, never in a URL.</li>
      <li>An account is created on first gateway login; set its password in Administration.</li>
    </ul>`,
};

async function renderLoginCard() {
  const box = $("#adm-login");
  if (!box) return;
  let l;
  try { l = await api("/api/admin/login"); } catch (e) { box.innerHTML = `<p class="err">${esc(t("není spojení"))}</p>`; return; }
  const skupiny = Object.entries(l.role_z_skupin || {}).map(([k, v]) => `${k}=${v}`).join("\n");
  const jazyk = (localStorage.rpraxe && localStorage.rpraxe.lang) || "cs";
  box.innerHTML = `
    <label class="checkrow"><input type="checkbox" id="lg-sso" ${l.sso ? "checked" : ""}>
      <span><strong>${esc(t("Přihlašovat přes bránu (SSO)"))}</strong><br>
      <span class="tiny muted">${esc(l.sso ? t("zapnuto — účet se založí sám podle hlavičky")
        : t("vypnuto — přihlašuje se heslem"))}</span></span></label>
    <div class="grid g2">
      <div><label for="lg-hlavka">${esc(t("Hlavička s jménem uživatele"))}</label>
        <input id="lg-hlavka" value="${esc(l.hlavka_jmeno || "Remote-User")}" autocomplete="off" spellcheck="false"></div>
      <div><label for="lg-hlavka-role">${esc(t("Hlavička se skupinami (pro role)"))}</label>
        <input id="lg-hlavka-role" value="${esc(l.hlavka_role || "")}" autocomplete="off"
               spellcheck="false" placeholder="Remote-Groups"></div>
    </div>
    <label for="lg-tajemstvi">${esc(t("Heslo brány (shared secret)"))}</label>
    <span class="pw"><input id="lg-tajemstvi" type="password" autocomplete="off"
        placeholder="${l.tajemstvi && l.tajemstvi.nastaveno ? esc(t("uloženo: ") + l.tajemstvi.ukazka) : esc(t("vygeneruj a vlož i do brány"))}">
      <button class="eye" type="button" data-eye="lg-tajemstvi" aria-pressed="false" title="${esc(t("ukázat"))}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg></button></span>
    <div class="row" style="gap:6px;margin-top:6px;flex-wrap:wrap">
      <button id="lg-gen" class="ghost" type="button">${esc(t("vygenerovat heslo brány"))}</button>
      <span class="tiny muted">${esc(t("hlavička s heslem"))}: <code>${esc(l.hlavka_tajemstvi)}</code></span>
    </div>
    <label for="lg-skupiny">${esc(t("Skupina → role (jeden na řádek, např. pedagogove=teacher)"))}</label>
    <textarea id="lg-skupiny" rows="3" spellcheck="false">${esc(skupiny)}</textarea>
    <p class="tiny muted">${esc(t("účty"))}: <code>${esc((l.ucity || []).join(", "))}</code></p>
    <p class="tiny muted">${esc(t("Co přišlo v tomto požadavku"))}: <code>${esc(JSON.stringify(l.sonda || {}))}</code></p>
    <details class="rada"><summary>${esc(t("Jak to nastavit v bráně (Authelia, Caddy…)"))}</summary>
      ${SSO_NAVOD[jazyk] || SSO_NAVOD.cs}</details>
    <p class="tiny muted" id="lg-stav" role="status"></p>
    <div class="row" style="margin-top:10px"><button id="lg-save" class="primary" type="button">${esc(t("uložit přihlašování"))}</button></div>`;
  translateDom(box);
  $("#lg-gen").onclick = () => {
    const pole = $("#lg-tajemstvi");
    pole.value = vyhheslo() + vyhheslo().slice(0, 8);
    pole.type = "text";
    const oko = document.querySelector('[data-eye="lg-tajemstvi"]');
    if (oko) oko.setAttribute("aria-pressed", "true");
    $("#lg-stav").className = "tiny muted";
    $("#lg-stav").textContent = t("Stejné heslo vlož i do nastavení brány.");
  };
  $("#lg-save").onclick = async () => {
    const stav = $("#lg-stav");
    const map = {};
    $("#lg-skupiny").value.split("\n").forEach(radek => {
      const casti = radek.split("=");
      if (casti.length === 2 && casti[0].trim()) map[casti[0].trim()] = casti[1].trim();
    });
    const r = await api("/api/admin/login", { method: "POST", body: JSON.stringify({
      sso: $("#lg-sso").checked, hlavka_jmeno: $("#lg-hlavka").value.trim(),
      hlavka_role: $("#lg-hlavka-role").value.trim(), tajemstvi: $("#lg-tajemstvi").value || undefined,
      role_z_skupin: map }) });
    if (r && r.ok) { toast(t("Přihlašování uloženo.")); renderLoginCard(); }
    else { stav.className = "tiny err"; stav.textContent = (r && r.detail) || t("nepovedlo se"); }
  };
}

/* --------------------------------------------------------------- třídy */
let TRIDY = [], TRIDA_VYBRANA = null;

async function loadTridy() {
  const box = $("#tridy");
  if (!box) return;
  box.innerHTML = `<p class="tiny muted">${esc(t("načítám…"))}</p>`;
  let d;
  try { d = await api("/api/classes"); } catch (e) { box.innerHTML = `<p class="err">${esc(t("není spojení"))}</p>`; return; }
  TRIDY = d.tridy || [];
  const zaci = d.zaci || [];
  const seznam = $("#tc-zaci");
  if (seznam) {
    //výběr žáků: klikací štítky — multiple select lidem nedojde
    const veTride = new Set((TRIDY.find(k => k.id === TRIDA_VYBRANA) || {}).students || []);
    seznam.innerHTML = zaci.length ? zaci.map(z => `
      <label class="zak"><input type="checkbox" value="${esc(z)}" ${veTride.has(z) ? "checked" : ""}>
        <span>${esc(z)}</span></label>`).join("")
      : `<p class="tiny muted">${esc(t("zatím žádný studentský účet"))}</p>`;
  }
  box.innerHTML = TRIDY.length ? `<div class="tridy">${TRIDY.map(k => `
      <div class="trida ${k.id === TRIDA_VYBRANA ? "on" : ""}" data-id="${esc(k.id)}" tabindex="0"
           role="button" aria-pressed="${k.id === TRIDA_VYBRANA}">
        <div class="row" style="justify-content:space-between;gap:6px">
          <strong>${esc(k.name)}</strong>${k.cizí ? ` <span class="pill">${esc(t("cizí"))}</span>` : ""}
        </div>
        <div class="tiny muted">${esc(t("učitel"))}: ${esc(k.teacher)} · ${k.students.length} ${esc(t("žáků"))}</div>
        ${k.note ? `<div class="tiny muted">${esc(k.note)}</div>` : ""}
        <div class="tiny">${k.students.length ? esc(k.students.join(", ")) : esc(t("zatím bez žáků"))}</div>
        ${k.cizí ? "" : `<button type="button" class="ghost js-smaz-tridu" data-id="${esc(k.id)}"
          style="margin-top:6px">${esc(t("smazat třídu"))}</button>`}
      </div>`).join("")}</div>`
    : `<p class="tiny muted">${esc(t("Zatím žádná třída — založ první níže."))}</p>`;
  translateDom(box);
  $$("#tridy .trida").forEach(karta => {
    const vyber = () => { TRIDA_VYBRANA = karta.dataset.id; vyplnTridu(); loadTridy(); };
    karta.onclick = (e) => { if (!e.target.closest(".js-smaz-tridu")) vyber(); };
    karta.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); vyber(); } };
  });
  $$("#tridy .js-smaz-tridu").forEach(tlacitko =>
    tlacitko.onclick = (e) => { e.stopPropagation(); smazTridu(tlacitko.dataset.id); });
}

/** Dosadí vybranou třídu do formuláře včetně zaškrtnutých žáků. */
function vyplnTridu() {
  const k = TRIDY.find(x => x.id === TRIDA_VYBRANA) || {};
  const jmeno = $("#tc-name"), poznamka = $("#tc-note");
  if (jmeno) jmeno.value = k.name || "";
  if (poznamka) poznamka.value = k.note || "";
  const veTride = new Set(k.students || []);
  $$("#tc-zaci input").forEach(pole => { pole.checked = veTride.has(pole.value); });
}

function novaTrida() {
  TRIDA_VYBRANA = null;
  $("#tc-name").value = "";
  $("#tc-note").value = "";
  $$("#tc-zaci input").forEach(pole => { pole.checked = false; });
  $("#tc-status").textContent = "";
  loadTridy();
  $("#tc-name").focus();
}

async function ulozTridu() {
  const stav = $("#tc-status");
  const jmeno = $("#tc-name").value.trim();
  if (!jmeno) { stav.className = "tiny err"; stav.textContent = t("Napiš aspoň název třídy."); return; }
  const zaci = $$("#tc-zaci input").filter(pole => pole.checked).map(pole => pole.value);
  const r = await api("/api/classes", { method: "POST", body: JSON.stringify({
    id: TRIDA_VYBRANA, name: jmeno,
    poznamka: $("#tc-note").value.trim(), zaci }) });
  if (r && r.ok) {
    TRIDA_VYBRANA = r.trida.id;
    stav.className = "tiny ok";
    stav.textContent = `${t("Třída uložena")}: ${r.trida.name} (${r.trida.students.length} ${t("žáků")})`;
    await loadTridy(); loadClass();
  } else { stav.className = "tiny err"; stav.textContent = (r && r.detail) || t("nepovedlo se"); }
}

/** Smaže třídu. Žáci zůstanou, zmizí jen jejich sdružení. */
function smazTridu(id) {
  const cislo = id || TRIDA_VYBRANA;
  if (!cislo) {
    const stav = $("#tc-status");
    stav.className = "tiny err";
    stav.textContent = t("Nejdřív klikni na třídu, kterou chceš smazat.");
    return;
  }
  const jmeno = (TRIDY.find(k => k.id === cislo) || {}).name || cislo;
  potvrd(`${t("Opravdu smazat třídu")} ${jmeno}? ${t("Žáci zůstanou, zmizí jen sdružení.")}`,
    async () => {
      const r = await api(`/api/classes/${encodeURIComponent(cislo)}`, { method: "DELETE" });
      if (r && r.ok) {
        if (TRIDA_VYBRANA === cislo) TRIDA_VYBRANA = null;
        toast(t("Třída smazána"));
        novaTrida(); loadClass();
      } else {
        const stav = $("#tc-status");
        stav.className = "tiny err";
        stav.textContent = (r && r.detail) || t("nepovedlo se");
      }
    }, t("smazat"));
}

/* ---------------------------------------------- správa: zálohy a obnova */
/** Co dělá pískoviště, data a přihlašovací brzda — vše na jednom místě. */
function renderProvoz(s) {
  const box = $("#adm-provoz");
  if (!box) return;
  const sandbox = s.sandbox || {};
  const data = s.data || {};
  const zaraza = s.prihlasovani_zaraza || {};
  const uklid = (data.osirele || []).length || (data.chybi || []).length;
  box.innerHTML = `
    <div class="row" style="gap:14px;flex-wrap:wrap">
      <div><div class="muted tiny">pískoviště</div><div class="tiny">
        ${sandbox.dostupne
          ? `CPU ${sandbox.cpu_s} s · zeď ${sandbox.stena_s} s · RAM ${sandbox.ram_mb} MB ·
             bez sítě · work ${sandbox.pracovni_mb} MB`
          : `nedostupné (${esc(sandbox.duvod || "runner neodpovídá")})`}</div></div>
      <div><div class="muted tiny">data</div><div class="tiny">
        ${data.souboru || 0} souborů${uklid ? ` · ${esc(t("úklid"))}: ${
            (data.chybi || []).length} chybí, ${(data.osirele || []).length} osiřelých`
          : ` · ${esc(t("v pořádku"))}`}</div></div>
      <div><div class="muted tiny">přihlašovací brzda</div><div class="tiny">
        ${(zaraza.zamcene || []).length
          ? `zadržené účty: ${(zaraza.zamcene || []).map(z => `${esc(z.ucet)} (${Math.round(z.do / 60)} min)`).join(", ")}`
          : `nikdo zadržený · ${zaraza.limit || "?"} pokusů, pak ${Math.round((zaraza.pauza_s || 0) / 60)} min pauza`}</div></div>
    </div>
    ${(data.chybi || []).length ? `<p class="tiny err">Úloha odkazuje na soubor, který v bance dat není:
      ${data.chybi.map(x => `${esc(x.soubor)} (${esc(x.ulohy.join(", "))})`).join("; ")}</p>` : ""}
    ${(data.osirele || []).length ? `<p class="tiny muted">Soubory, které žádná úloha nepoužívá:
      ${esc((data.osirele || []).join(", "))}</p>` : ""}
    <p class="tiny muted">Limity nastavuje <code>docker-compose.yml</code>
      (<code>RPRAXE_CPU_LIMIT</code>, <code>RPRAXE_WALL_LIMIT</code>, <code>RPRAXE_MEM_MB</code>).</p>`;
}

async function renderBackupCard() {
  const box = $("#adm-backups");
  if (!box) return;
  let data;
  try { data = await api("/api/admin/backups"); } catch (e) { box.innerHTML = `<p class="err">${esc(t("není spojení"))}</p>`; return; }
  const bk = data.prehled || {};
  const snimky = data.snimky || [];
  const last = bk.last || {};
  const co = [last.ucty && t("účty"), last.data && t("datasety"), last.banka && t("banka úloh")]
    .filter(Boolean).join(", ");
  box.innerHTML = `<p class="tiny muted">${esc(t("Poslední noční záloha"))}: ${
      last.at ? new Date(last.at * 1000).toLocaleString("cs-CZ")
        + ` <span class="tiny ${last.cerstva ? "ok" : "err"}">(${
            last.stari_h ?? "?"} ${esc(t("hod"))})</span>`
        + (co ? ` — ${esc(co)}` : "")
        : esc(t("zatím žádná"))}</p>
    ${last.at && !last.cerstva
      ? `<p class="tiny err">${esc(t("Záloha je starší než den — zkontroluj plánovaný úkol."))}</p>` : ""}
    ${!last.at ? `<p class="tiny muted">${esc(
        t("Zatím nebyla žádná noční záloha — spusť scripts/backup.sh nebo ji nastav v cronu."))}</p>` : ""}
    <div style="overflow:auto"><table id="bk-table">
      <tr><th>${esc(t("soubor"))}</th><th>${esc(t("pokusy"))}</th><th>${esc(t("náš"))}</th><th></th></tr>
      ${snimky.map(s => `<tr><td class="tiny">${esc(s.jmeno)}<div class="tiny muted">${
          new Date(s.cas * 1000).toLocaleString("cs-CZ")} · ${(s.bytes / 1024).toFixed(0)} kB</div></td>
        <td>${s.pouzitelna ? s.pokusy : "—"}</td>
        <td>${s.pouzitelna ? s.ulohy : "—"}</td>
        <td>${s.pouzitelna ? `<button class="ghost bk-load" data-jmeno="${esc(s.jmeno)}" type="button">${esc(t("načíst"))}</button>`
          : `<span class="tiny err">${esc(t("nepoužitelný"))}</span>`}</td></tr>`).join("")}
    </table></div>
    <div class="row" style="margin-top:10px;flex-wrap:wrap;gap:6px">
      <button id="adm-backup" class="ghost" type="button">${esc(t("udělat snímek teď"))}</button>
    </div>
    <p class="tiny muted" id="bk-stav" role="status"></p>`;
  translateDom(box);
  $("#adm-backup").onclick = async () => {
    const r = await api("/api/admin/backup", { method: "POST", body: "{}" });
    if (r && r.ok) { toast(`${t("Snímek uložen")}: ${r.name}`); renderBackupCard(); }
    else $("#bk-stav").textContent = (r && r.detail) || t("nepovedlo se");
  };
  $$("#bk-table .bk-load").forEach(tlacitko => {
    tlacitko.onclick = () => obnovZalohu(tlacitko.dataset.jmeno);
  });
}

async function obnovZalohu(jmeno) {
  const odpoved = await ptat(
    `${t("Načíst ze zálohy")} — ${jmeno}. ${t("Přepíšu databázi tímto snímkem; současná data se předtím uloží do souboru pred-obnovou-*.db.")}`,
    t("pro jistotu napiš: OBNOVIT"));
  if (!odpoved) return;
  const r = await api("/api/admin/restore", { method: "POST",
    body: JSON.stringify({ jmeno, potvrdit: String(odpoved).trim() }) });
  if (r && r.ok) {
    toast(`${t("Obnoveno")}: ${r.pokusy} ${t("pokusů")}, ${r.ulohy} ${t("úloh")} · ${t("pojistka")} ${r.pojistka}`);
    renderBackupCard();
  } else {
    const stav = document.getElementById("bk-stav");
    if (stav) stav.textContent = (r && r.detail) || t("nepovedlo se");
  }
}

function show(view) {
  $$("nav button").forEach(b => b.classList.toggle("on", b.dataset.view === view));
  $$(".view").forEach(v => v.classList.toggle("on", v.id === "v-" + view));
  if (view === "lib") loadLib();
  if (view === "prog") loadProg();
  if (view === "sheet") loadTahak();
  if (view === "class") loadClass();
  if (view === "admin") loadAdmin();
  if (view === "help") renderHelp();
  if (view === "today") loadBoot();
}

function toast(msg) {
  const t = document.createElement("div");
  t.className = "toast"; t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4200);
}

/* --------------------------------------------------------------- profil */
function closeUserMenu() {
  $("#usermenu").hidden = true;
  $("#btn-user").setAttribute("aria-expanded", "false");
}

function openPassword() {
  closeUserMenu();
  $("#pw-err").textContent = "";
  ["pw-cur", "pw-new", "pw-rep"].forEach(id => { $("#" + id).value = ""; });
  $("#pw-save").disabled = false;
  $("#pwmodal").hidden = false;
  $("#pw-cur").focus();
}

function closePassword() { $("#pwmodal").hidden = true; }

async function submitPassword() {
  const cur = $("#pw-cur").value, nw = $("#pw-new").value, rep = $("#pw-rep").value;
  const err = $("#pw-err");
  err.textContent = "";
  if (!cur) { err.textContent = "Zadej současné heslo."; $("#pw-cur").focus(); return; }
  if (nw.length < 8) { err.textContent = "Nové heslo musí mít aspoň 8 znaků."; $("#pw-new").focus(); return; }
  if (nw !== rep) { err.textContent = "Nová hesla se neshodují."; $("#pw-rep").focus(); return; }
  $("#pw-save").disabled = true;
  let r;
  try {
    r = await api("/api/password", {
      method: "POST", redirect401: false,
      body: JSON.stringify({ current: cur, new: nw, repeat: rep }) });
  } catch (e) {
    err.textContent = "Server se nepovedlo kontaktovat — zkus to znovu.";
    $("#pw-save").disabled = false;
    return;
  }
  $("#pw-save").disabled = false;
  if (r && r.ok) { closePassword(); toast("Heslo změněno — nové platí i při dalším přihlášení."); return; }
  err.textContent = (r && (r.detail || r.msg)) || "Změna se nezdařila.";
  $("#pw-cur").focus();
  $("#pw-cur").select();
}


async function showSolution() {
  if (!current) return;
  const r = await api("/api/solution", { method: "POST", body: JSON.stringify({ task_id: current.id }) });
  $("#hintbox").innerHTML = `<div class="coach"><strong>${t("Řešení")}:</strong></div><pre class="out">${esc(r.reseni)}</pre>
    <p class="tiny muted">${esc(r.note)}</p>`;
}

/* -------------------------------------------------- potvrzení bez prompt() */
let confirmCb = null;

function potvrd(text, onYes, labelYes = "ano") {
  let box = $("#okmodal");
  if (!box) {
    box = document.createElement("div");
    box.className = "modal"; box.id = "okmodal"; box.hidden = true;
    box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true");
    box.innerHTML = `<div class="card pwcard"><h3 id="ok-title">Prosím potvrz</h3>
      <p id="ok-text" class="tiny"></p>
      <div class="row end"><button id="ok-no" type="button" class="ghost">zrušit</button>
      <button id="ok-yes" type="button" class="primary"></button></div></div>`;
    document.body.appendChild(box);
    $("#ok-no").onclick = () => { box.hidden = true; confirmCb = null; };
    $("#ok-yes").onclick = () => { box.hidden = true; const cb = confirmCb; confirmCb = null; if (cb) cb(); };
    box.onclick = (e) => { if (e.target.id === "okmodal") { box.hidden = true; confirmCb = null; } };
  }
  $("#ok-text").textContent = text;
  $("#ok-yes").textContent = t(labelYes);
  confirmCb = onYes;
  box.hidden = false;
  $("#ok-yes").focus();
}

/* ------------------------------------------------------------- nastavení */
async function openSettings() {
  closeUserMenu();
  $("#set-err").textContent = "";
  if (!SETTINGS) {
    try { SETTINGS = await api("/api/settings"); }
    catch (e) { $("#set-err").textContent = "Nastavení se nepodařilo načíst."; }
  }
  const s = SETTINGS || {};
  const fill = (sel, items, currentVal, label) => {
    sel.innerHTML = items.map(([v, txt]) =>
      `<option value="${esc(v)}" ${String(v) === String(currentVal) ? "selected" : ""}>${esc(txt)}</option>`).join("");
    if (!items.some(([v]) => String(v) === String(currentVal))) sel.value = items[0][0];
  };
  fill($("#set-theme"), [["auto", t("Systémový")], ["dark", t("Tmavý")], ["light", t("Světlý")]], s.theme || "auto");
  // jen jazyky, které mají hotový překlad — jinak by se nabídla poloviština
  const langs = jazykySPrekladem(Object.entries(s.langs || { cs: "čeština" }));
  fill($("#set-lang"), langs, langs.some(([kod]) => kod === (s.lang || "cs")) ? (s.lang || "cs") : "cs");
  fill($("#set-min"), (s.budgets || [15, 20, 30, 45]).map(m => [m, `${m} min`]), s.minutes || 20);
  const ai = s.ai || {};
  $("#set-model-info").textContent = ai.model
    ? `${t("Model")}: ${ai.model}${ai.poskytovatel ? ` (${ai.poskytovatel})` : ""}`
    : (s.default_model ? `${t("Model")}: ${s.default_model}` : t("Model zatím nemá nastavený správce."));
  $("#set-ainote").textContent = t("Model volí správce — všichni v instanci mají stejného kouče.");
  $("#setmodal").hidden = false;
  $("#set-theme").focus();
}

async function saveSettings() {
  const body = {
    theme: $("#set-theme").value, lang: $("#set-lang").value,
    minutes: Number($("#set-min").value),
  };
  $("#set-save").disabled = true;
  let r;
  try {
    r = await api("/api/settings", { method: "POST", redirect401: false, body: JSON.stringify(body) });
  } catch (e) {
    r = { detail: "server nedostupný" };
  }
  $("#set-save").disabled = false;
  if (r && r.ok) {
    SETTINGS = { ...SETTINGS, ...body };
    applyTheme(body.theme); applyLang(body.lang);
    renderHelp();                       // nápis nápovědy patří do nového jazyka
    $("#setmodal").hidden = true;
    toast("Nastavení uložené.");
    await loadBoot();
    return;
  }
  $("#set-err").textContent = (r && (r.detail || r.msg)) || "Uložení se nezdařilo.";
}

/* ------------------------------------------------------------------ banka úloh
 * Jeden díl použít dvakrát: ve správě a v záložce Třída. Umí přenést úlohy
 * dovnitř (odkaz na GitHub, nebo soubor z počítače), ven (celá banka, filtr,
 * výběr) a pracovat s nimi hromadně i jednotlivě — založit, upravit, schválit,
 * zahodit, smazat. Studenti sem nedosáhnou, komponenta se jim nikdy nekreslí.
 */
const BANKA_HTML = (i) => `
  <p class="tiny muted">Vlož odkaz na repozitář nebo na soubor <code>ukoly.json</code>,
    nebo vyber JSON z počítače. Úlohy, které projdou spuštěním, se schválí samy;
    zbytek zůstane jako koncept ke čtení. Formát je v <code>docs/github.md</code>.</p>
  <div class="row" style="gap:6px;flex-wrap:wrap">
    <input id="${i("gh-url")}" placeholder="https://github.com/vlastnik/repo/ukoly.json"
           autocomplete="off" spellcheck="false" style="flex:1;min-width:220px">
    <button class="ghost js-gh" type="button">načíst z GitHubu</button>
  </div>
  <div class="row" style="gap:6px;flex-wrap:wrap;margin-top:6px">
    <input type="file" class="js-soubor" accept=".json,application/json" style="flex:1;min-width:220px">
    <button class="ghost js-nahraj" type="button">nahrát ze souboru</button>
  </div>
  <p class="tiny" id="${i("gh-status")}" role="status"></p>
  <div class="sep"></div>
  <p class="tiny muted">Sem patří i <strong>datové soubory</strong> (CSV/TSV), na které se
    úloha odkazuje — buď jsou součástí JSON jako pole <code>data</code>, nebo je nahraješ z počítače.</p>
  <div class="row" style="gap:6px;flex-wrap:wrap;margin-top:6px">
    <input type="file" class="js-dat" accept=".csv,.tsv,.txt,text/csv" style="flex:1;min-width:200px">
    <button class="ghost js-nahraj-data" type="button">nahrát data</button>
    <label class="checkrow" style="margin:0"><input type="checkbox" class="js-prepsat"> přepsat existující</label>
  </div>
  <p class="tiny js-datovy" role="status"></p>
  <div class="sep"></div>
  <div class="row" style="gap:6px;flex-wrap:wrap">
    <select class="js-stav" style="width:auto">
      <option value="">vše</option><option value="approved">schválené</option>
      <option value="draft">čeká na ověření</option><option value="retired">zahozené</option>
    </select>
    <select class="js-lekce" style="width:auto"><option value="">všechny lekce</option></select>
    <input class="js-q" placeholder="hledat v názvu/zadání…" style="flex:1;min-width:150px">
    <button class="ghost js-vse" type="button">vybrat vše</button>
  </div>
  <div class="row" style="gap:6px;flex-wrap:wrap;margin-top:8px">
    <button class="ghost js-nova" type="button">založit novou úlohu</button>
    <button class="ghost js-export" type="button">export vybraných</button>
    <button class="ghost js-export-filtr" type="button">export podle filtru</button>
    <button class="ghost js-export-banka" type="button">export celé banky</button>
  </div>
  <div style="overflow:auto;margin-top:10px"><table class="js-banka"></table></div>
  <p class="tiny js-stavovy" role="status"></p>`;

/** Nakreslí banku do nádoby a naváže ovládání. Podruhé jen přečte data. */
function nakresliBanku(cil, predpona) {
  if (!cil) return;
  if (cil.dataset.banka === "1") { nactiBanku(cil); return; }
  const id = (n) => (predpona ? predpona + "-" : "") + n;
  cil.classList.add("banka");
  cil.innerHTML = BANKA_HTML(id);
  cil.dataset.banka = "1";
  cil.querySelector(".js-gh").onclick = () => nacpiGithub(cil);
  cil.querySelector(".js-nahraj").onclick = () => nahrejSoubor(cil);
  cil.querySelector(".js-nahraj-data").onclick = () => nahrajData(cil);
  cil.querySelector(".js-nova").onclick = () => novaUloha();
  cil.querySelector(".js-vse").onclick = () => {
    const zaci = [...cil.querySelectorAll(".js-vyber")];
    const vse = zaci.length > 0 && zaci.every(pole => pole.checked);
    zaci.forEach(pole => { pole.checked = !vse; });
  };
  cil.querySelector(".js-export").onclick = () => exportujBanku(cil, "vyber");
  cil.querySelector(".js-export-filtr").onclick = () => exportujBanku(cil, "filtr");
  cil.querySelector(".js-export-banka").onclick = () => exportujBanku(cil, "vse");
  cil.querySelector(".js-stav").onchange = () => nactiBanku(cil);
  cil.querySelector(".js-lekce").onchange = () => nactiBanku(cil);
  cil.querySelector(".js-q").oninput = () => nactiBanku(cil);
  nactiBanku(cil);
  try {
    const minule = localStorage.getItem("rpraxe.github");
    const vstup = cil.querySelector("#" + id("gh-url"));
    if (minule && vstup && !vstup.value) vstup.value = minule;
  } catch (e) {}
}

/** Načte banku a vykreslí tabulku podle zrovna nastaveného filtru. */
async function nactiBanku(cil) {
  const tabulka = cil.querySelector(".js-banka");
  hlaska = cil.querySelector(".js-stavovy");
  if (!tabulka) return;
  if (!tabulka.dataset.nacteno) tabulka.innerHTML = `<tr><td>${esc(t("načítám…"))}</td></tr>`;
  let d;
  try { d = await api("/api/tasks"); }
  catch (e) { tabulka.innerHTML = `<tr><td>${esc(t("není spojení"))}</td></tr>`; return; }
  const ulohy = d.tasks || [];
  const lekce = cil.querySelector(".js-lekce");
  if (lekce && lekce.options.length <= 1) {
    lekce.innerHTML = `<option value="">${esc(t("všechny lekce"))}</option>`
      + Object.keys(d.lessons || {}).map(n =>
        `<option value="${esc(n)}">${esc(n)}. ${esc((d.lessons[n] || {}).title || n)}</option>`).join("");
  }
  const stav = cil.querySelector(".js-stav").value;
  const poLekci = lekce.value;
  const hledani = (cil.querySelector(".js-q").value || "").toLowerCase();
  const viditelne = ulohy.filter(u =>
    (!stav || u.status === stav) &&
    (!poLekci || String(u.lesson) === String(poLekci)) &&
    (!hledani || ((u.title || "") + " " + (u.zadani || "")).toLowerCase().includes(hledani)));
  const popisek = { approved: t("schváleno"), draft: t("koncept"), retired: t("zahozeno") };
  tabulka.dataset.nacteno = "1";
  tabulka.innerHTML = `<tr><th></th><th>${esc(t("úloha"))}</th><th>${esc(t("lekce"))}</th>
      <th>${esc(t("stav"))}</th><th>${esc(t("zdroj"))}</th><th></th></tr>`
    + (viditelne.length ? viditelne.map(u => `<tr data-id="${esc(u.id)}">
        <td><input type="checkbox" class="js-vyber" value="${esc(u.id)}"></td>
        <td><strong>${esc(u.title)}</strong>
          <div class="tiny muted">${esc((u.skills || []).join(", "))} · ${esc(u.id)}</div></td>
        <td>${u.lesson}</td>
        <td><span class="pill">${esc(popisek[u.status] || u.status)}</span></td>
        <td class="tiny muted">${esc(u.source || "")}</td>
        <td class="row" style="gap:4px;flex-wrap:wrap">
          <button class="ghost js-upravit" type="button">${esc(t("upravit"))}</button>
          ${u.status !== "approved" ? `<button class="ghost js-schvalit" type="button">${esc(t("schválit"))}</button>` : ""}
          ${u.status !== "retired" ? `<button class="ghost js-zahodit" type="button">${esc(t("zahodit"))}</button>`
                                   : `<button class="ghost js-vratit" type="button">${esc(t("vrátit zpět"))}</button>`}
          <button class="ghost js-smazat" type="button">${esc(t("smazat"))}</button>
        </td></tr>`).join("")
      : `<tr><td colspan="6" class="muted">${esc(t("nic tu neodpovídá filtru"))}</td></tr>`);
  hlaska.textContent = `${viditelne.length} ${t("z")} ${ulohy.length} ${t("úloh")}`;
  cil.querySelectorAll(".js-upravit").forEach(tlacitko => tlacitko.onclick = async () => {
    const id = tlacitko.closest("tr").dataset.id;
    const u = await api(`/api/tasks/${id}`);
    if (u && u.id) upravUlohu(u); else toast(t("úlohu jsem nenašel"));
  });
  cil.querySelectorAll(".js-schvalit").forEach(tlacitko =>
    tlacitko.onclick = () => zmenStav(tlacitko.closest("tr").dataset.id, "approved"));
  cil.querySelectorAll(".js-zahodit").forEach(tlacitko => tlacitko.onclick = () => {
    const id = tlacitko.closest("tr").dataset.id;
    potvrd(`${t("Opravdu zahodit")} ${id}? ${t("Studenti ji neuvidí; smazat se dá úplně později.")}`,
      () => zmenStav(id, "retired"), t("zahodit"));
  });
  cil.querySelectorAll(".js-vratit").forEach(tlacitko =>
    tlacitko.onclick = () => zmenStav(tlacitko.closest("tr").dataset.id, "draft"));
  cil.querySelectorAll(".js-smazat").forEach(tlacitko => tlacitko.onclick = () => {
    const id = tlacitko.closest("tr").dataset.id;
    potvrd(`${t("Opravdu smazat")} ${id}? ${t("Historie pokusů zůstane, úloha zmizí.")}`,
      async () => {
        const r = await api(`/api/tasks/${encodeURIComponent(id)}`, { method: "DELETE" });
        if (r && r.ok) { toast(`${id} ${t("smazána")}`); nactiBanku(cil); loadLib(); }
        else toast((r && r.detail) || t("nepovedlo se"));
      }, t("smazat"));
  });
}

/** Dovoz z GitHubu — funguje v kterékoliv nádobě banky. */
async function nacpiGithub(cil) {
  cil = cil || document;
  const hlaseni = cil.querySelector("#gh-status") || cil.querySelector(".js-stavovy");
  const vstup = cil.querySelector("#gh-url");
  const odkaz = ((vstup && vstup.value) || "").trim();
  if (!odkaz) {
    if (hlaseni) { hlaseni.className = "tiny err"; hlaseni.textContent = t("Vlož odkaz na repozitář nebo na soubor ukoly.json."); }
    return;
  }
  if (hlaseni) { hlaseni.className = "tiny muted"; hlaseni.textContent = t("stahuji a přezkouším…"); }
  let r;
  try { r = await api("/api/github/import", { method: "POST", body: JSON.stringify({ odkaz }) }); }
  catch (e) { r = { detail: t("server nedostupný") }; }
  if (r && r.ok) {
    if (hlaseni) {
      hlaseni.className = "tiny ok";
      hlaseni.textContent = `${r.pocet} ${t("přeneseno")}, ${r.schvaleno} ${t("schváleno")} — ${r.zdroj}`;
    }
    try { localStorage.setItem("rpraxe.github", odkaz); } catch (e) {}
    nactiBanku(cil); loadLib();
  } else if (hlaseni) {
    hlaseni.className = "tiny err";
    hlaseni.textContent = (r && (r.detail || r.zprava)) || t("nepovedlo se");
  }
}

/** Dovoz ze souboru, který člověk vybere v prohlížeči. */
async function nahrejSoubor(cil) {
  const vstup = cil.querySelector(".js-soubor");
  const hlaseni = cil.querySelector("#gh-status") || cil.querySelector(".js-stavovy");
  const soubor = vstup && vstup.files && vstup.files[0];
  if (!soubor) {
    if (hlaseni) { hlaseni.className = "tiny err"; hlaseni.textContent = t("Nejdřív vyber soubor s úlohami."); }
    return;
  }
  const text = await soubor.text();
  if (hlaseni) { hlaseni.className = "tiny muted"; hlaseni.textContent = t("ověřuji a přenáším…"); }
  let r;
  try {
    r = await api("/api/tasks/import", { method: "POST",
      body: JSON.stringify({ data: text, jmeno: soubor.name }) });
  } catch (e) { r = { detail: t("server nedostupný") }; }
  if (r && r.ok) {
    if (hlaseni) {
      hlaseni.className = "tiny ok";
      hlaseni.textContent = `${r.pocet} ${t("přeneseno")}, ${r.schvaleno} ${t("schváleno")} — ${soubor.name}`;
    }
    nactiBanku(cil); loadLib();
  } else if (hlaseni) {
    hlaseni.className = "tiny err";
    hlaseni.textContent = (r && (r.detail || r.zprava)) || t("nepovedlo se");
  }
}

/** Export: celá banka, filtr, nebo jen zaškrtnuté úlohy — JSON ke stažení. */
async function exportujBanku(cil, zpusob) {
  const parametry = new URLSearchParams();
  hlaska = cil.querySelector(".js-stavovy");
  if (zpusob === "filtr") {
    if (cil.querySelector(".js-stav").value) parametry.set("status", cil.querySelector(".js-stav").value);
    if (cil.querySelector(".js-lekce").value) parametry.set("lesson", cil.querySelector(".js-lekce").value);
    if (cil.querySelector(".js-q").value) parametry.set("q", cil.querySelector(".js-q").value);
  } else if (zpusob === "vyber") {
    const idy = [...cil.querySelectorAll(".js-vyber")].filter(pole => pole.checked).map(pole => pole.value);
    if (!idy.length) {
      if (hlaska) { hlaska.className = "tiny err"; hlaska.textContent = t("Zaškrtni aspoň jednu úlohu."); }
      return;
    }
    parametry.set("ids", idy.join(","));
  }
  const data = await api(`/api/tasks/export?${parametry.toString()}`);
  if (!data || !data.ukoly) { toast((data && data.detail) || t("nepovedlo se")); return; }
  const nazev = `ukoly-${zpusob === "vse" ? "banka" : zpusob}-${new Date().toISOString().slice(0, 10)}.json`;
  const blob = new Blob([JSON.stringify({ ukoly: data.ukoly }, null, 2)], { type: "application/json" });
  const odkaz = document.createElement("a");
  odkaz.href = URL.createObjectURL(blob);
  odkaz.download = nazev;
  document.body.appendChild(odkaz);
  odkaz.click();
  odkaz.remove();
  setTimeout(() => URL.revokeObjectURL(odkaz.href), 4000);
  if (hlaska) { hlaska.className = "tiny ok"; hlaska.textContent = `${data.pocet} ${t("úloh v souboru")} ${nazev}`; }
}

/** Nahraje CSV/TSV do banky dat a doplní ji do seznamu. */
async function nahrejSouborDat(cil, vstup, hlaseni, prepsat) {
  const soubor = vstup && vstup.files && vstup.files[0];
  if (!soubor) {
    if (hlaseni) { hlaseni.className = "tiny err"; hlaseni.textContent = t("Nejdřív vyber datový soubor (.csv, .tsv, .txt)."); }
    return;
  }
  const text = await soubor.text();
  if (hlaseni) { hlaseni.className = "tiny muted"; hlaseni.textContent = `${soubor.name}: ${t("kontroluji a ukládám…")}`; }
  let r;
  try {
    r = await api("/api/datasets", { method: "POST",
      body: JSON.stringify({ jmeno: soubor.name, data: text, prepsat: !!prepsat }) });
  } catch (e) { r = { detail: t("server nedostupný") }; }
  if (r && r.ok) {
    if (hlaseni) {
      hlaseni.className = "tiny ok";
      hlaseni.textContent = `${r.jmeno}: ${r.radku} ${t("řádků")}, ${t("sloupce")} ${r.sloupce.join(", ")}`;
    }
    nactiDatasety();
  } else if (hlaseni) {
    hlaseni.className = "tiny err";
    hlaseni.textContent = (r && r.detail) || t("nepovedlo se");
  }
  return r;
}

function nahrajData(cil) {
  return nahrejSouborDat(cil, cil.querySelector(".js-dat"),
    cil.querySelector(".js-datovy"), cil.querySelector(".js-prepsat")?.checked);
}

/** Seznam datových souborů, aby šel ve formuláři vybrat místo opsání. */
async function nactiDatasety() {
  const seznam = document.getElementById("datasety");
  if (!seznam) return;
  let d;
  try { d = await api("/api/datasets"); } catch (e) { return; }
  seznam.innerHTML = (d.datasets || []).map(n => `<option value="${esc(n)}"></option>`).join("");
}

/* ------------------------------------------------------------------ třída */
async function loadClass() {
  loadTridy();
  const bankaTrida = $("#trida-banka");
  if (bankaTrida) nakresliBanku(bankaTrida, "");
  const box = $("#class");
  if (!box) return;
  box.innerHTML = '<p class="muted tiny">načítám…</p>';
  const d = await api("/api/class");
  const zaci = d.students || [];
  box.innerHTML = "<tr><th>jméno</th><th>naposledy</th><th>úlohy</th><th>první dobrou</th>" +
    "<th>odklikáno</th><th>řada</th><th>slabé místa</th><th></th></tr>" + (zaci.length ? zaci.map(s => `
      <tr><td><strong>${esc(s.user)}</strong>${(s.tridy || []).length
        ? `<div class="tiny muted">${esc(s.tridy.join(", "))}</div>` : ""}</td>
      <td class="tiny muted">${s.last ? new Date(s.last * 1000).toLocaleString("cs-CZ") : "ještě nic"}</td>
      <td>${s.passed}/${s.total}</td><td>${s.first_try_rate ?? 0} %</td>
      <td>${s.minutes_total} min</td><td>${s.streak}</td>
      <td class="tiny">${esc((s.weak || []).join(", ") || "—")}</td>
      <td><button class="ghost" data-user="${esc(s.user)}">detail</button></td></tr>`).join("")
      : '<tr><td colspan="8" class="muted">zatím žádný student — přidej účet ve Správě.</td></tr>');
  $$("#class button[data-user]").forEach(b => b.onclick = () => showStudent(b.dataset.user));
}

async function showStudent(user) {
  const box = $("#studentdetail");
  box.innerHTML = '<p class="muted tiny">načítám…</p>';
  const p = await api("/api/class/" + encodeURIComponent(user));
  const doved = (p.skills || []).map(s => `<span class="pill">${esc(s.label)} ${Number(s.theta).toFixed(1)}</span>`).join(" ");
  const sk = p.skoly || {};
  const dluh = (sk.nacteno || 0) > 0 && (sk.hotovo || 0) < (sk.nacteno || 0)
    ? `<span class="pill hot">dnes ${sk.hotovo}/${sk.nacteno}</span>`
    : (sk.nacteno ? `<span class="pill">dnes hotovo ${sk.hotovo}/${sk.nacteno}</span>` : "");
  box.innerHTML = `<h3>${esc(user)} ${dluh}</h3>
    <p class="tiny muted">${p.total || 0} pokusů · ${p.passed || 0} správně ·
      ${p.first_try_rate ?? 0} % na první dobrou · ${p.days_active || 0} dní ·
      ${Math.round(p.minutes_total || 0)} min</p>
    <div class="row" style="gap:5px;flex-wrap:wrap">${doved || '<span class="muted tiny">zatím nic</span>'}</div>
    <table id="stud-recent" style="margin-top:10px"></table>`;
  $("#stud-recent").innerHTML = "<tr><th>kdy</th><th>úloha</th><th></th></tr>" + (p.recent || []).map(a =>
    `<tr><td class="tiny muted">${new Date(a.ts * 1000).toLocaleString("cs-CZ")}</td>
     <td>${esc(a.title || a.task)}</td><td>${a.ok ? "✓" : "✗"}</td></tr>`).join("");
  const poznamky = p.poznamky || [];
  box.insertAdjacentHTML("beforeend", `
    <h3 style="margin-top:14px">Poznámky žáka</h3>
    ${poznamky.length ? `<div style="overflow:auto"><table id="stud-poznamky"></table></div>
      <p class="tiny muted">Poznámku píše žák sám k úloze. Vidíš ji, abys poznal, kde to vázne —
        žák ji ale myslel jako svou poznámku, ne jako zprávu tobě.</p>`
      : '<p class="tiny muted">Žák zatím napsal žádné poznámky.</p>'}`);
  if (poznamky.length) {
    $("#stud-poznamky").innerHTML = "<tr><th>kdy</th><th>úloha</th><th>co napsal</th></tr>" +
      poznamky.map(x => `<tr><td class="tiny muted">${new Date(x.ts * 1000).toLocaleDateString("cs-CZ")}</td>
        <td class="tiny">${esc(x.titulek || x.task)}</td>
        <td class="tiny" style="white-space:pre-wrap">${esc(x.text)}</td></tr>`).join("");
  }
}

/** Stáhne CSV s výsledky vybrané třídy. */
function exportTridy() {
  const oznaceni = $("#tc-export-lbl");
  if (!TRIDA_VYBRANA) {
    if (oznaceni) oznaceni.textContent = "dřív klikni na třídu, kterou chceš exportovat";
    return;
  }
  const dni = ($("#tc-export-days") || {}).value || "90";
  window.location = `/api/classes/${encodeURIComponent(TRIDA_VYBRANA)}/export?days=${dni}`;
  if (oznaceni) oznaceni.textContent = "sestavuje se soubor…";
}

/** Otevře dialog s úlohou — prázdný argument znamená úplně vlastní úloha. */
function otorEditor(u) {
  const modal = $("#taskmodal");
  if (!modal) return;
  const vloz = (id, hodnota) => { const prvek = $(id); if (prvek) prvek.value = hodnota ?? ""; };
  const upravuje = !!(u && u.id);
  vloz("#nt-id", upravuje ? u.id : "");
  vloz("#nt-title", upravuje ? u.title : "");
  vloz("#nt-lesson", upravuje ? u.lesson : 4);
  vloz("#nt-min", upravuje ? u.minutes : 4);
  vloz("#nt-level", upravuje ? u.level : 2);
  vloz("#nt-skills", upravuje ? (u.skills || []).join(", ") : "");
  vloz("#nt-dataset", upravuje ? (u.dataset || "") : "");
  vloz("#nt-nacti", upravuje ? u.nacti : "");
  vloz("#nt-starter", upravuje ? u.starter : "");
  vloz("#nt-zadani", upravuje ? u.zadani : "");
  vloz("#nt-reseni", upravuje ? u.reseni : "");
  vloz("#nt-check", upravuje ? (u.check ?? u.check_r) : "");
  const napovedy = upravuje ? (u.hints || []) : [];
  vloz("#nt-hints", Array.isArray(napovedy) ? napovedy.join("\n") : String(napovedy || ""));
  const titulek = $("#taskeditor-title");
  if (titulek) titulek.textContent = upravuje ? `${t("Úprava úlohy")} ${u.id}` : t("Nová úloha");
  const hint = $("#nt-edit");
  if (hint) hint.style.display = upravuje ? "" : "none";
  // data do banky nahrává jen učitel a správce — žák si vystačí s těmi, která už v bance jsou
  ["#nt-dat", "#nt-dat-nahrat"].forEach((id) => {
    const prvek = $(id);
    if (prvek) prvek.style.display = ["teacher", "admin"].includes(ROLE) ? "" : "none";
  });
  const stav = $("#nt-status");
  if (stav) { stav.className = "tiny"; stav.textContent = ""; }
  modal.hidden = false;
  const prvni = $("#nt-title");
  if (prvni) setTimeout(() => prvni.focus(), 30);
}

function zavriEditor() {
  const modal = $("#taskmodal");
  if (modal) modal.hidden = true;
}

/** Učitel otevře existující úlohu — před uložením se zase ověří spuštěním. */
function upravUlohu(u) { nactiDatasety(); otorEditor(u); }

/** Úplně vlastní úloha od nuly. */
function novaUloha() { nactiDatasety(); otorEditor(null); }

async function saveTask(pres) {
  const num = (id, d) => { const v = parseFloat($(id).value); return Number.isFinite(v) ? v : d; };
  const body = {
    id: $("#nt-id").value.trim() || null,
    title: $("#nt-title").value.trim(),
    lesson: num("#nt-lesson", 0), minutes: num("#nt-min", 4), level: num("#nt-level", 1),
    skills: $("#nt-skills").value.split(",").map(s => s.trim()).filter(Boolean),
    dataset: $("#nt-dataset").value.trim() || null,
    nacti: $("#nt-nacti").value,
    starter: $("#nt-starter").value,
    zadani: $("#nt-zadani").value.trim(),
    reseni: $("#nt-reseni").value,
    check: $("#nt-check").value,
    hints: $("#nt-hints").value.split("\n").map(s => s.trim()).filter(Boolean),
    kontrola_ai: !!($("#nt-ai") && $("#nt-ai").checked),
    pres: !!pres,
  };
  const st = $("#nt-status");
  st.className = "tiny muted";
  st.textContent = body.kontrola_ai ? t("spouštím v sandboxu a nechám to číst modelem…")
                                    : t("ověřuji spuštěním…");
  $("#nt-save").disabled = true; if ($("#nt-force")) $("#nt-force").disabled = true;
  if (ROLE === "student") { delete body.kontrola_ai; delete body.pres; }
  let r;
  try {
    r = await api(ROLE === "student" ? "/api/own" : "/api/tasks",
                  { method: "POST", redirect401: false, body: JSON.stringify(body) });
  }
  catch (e) { r = { detail: t("server nedostupný") }; }
  $("#nt-save").disabled = false; if ($("#nt-force")) $("#nt-force").disabled = false;
  if (r && r.ulozeno && r.ok) {
    st.className = "tiny ok";
    st.textContent = `${t("úloha")} ${r.id} ${t("uložena a schválena")}`;
    $("#nt-id").value = r.id;
    if (ROLE === "student") { setTimeout(() => { zavriEditor(); loadLib(); }, 900); }
  } else if (r && r.ulozeno) {
    st.className = "tiny err";
    st.textContent = `${t("uloženo jako koncept — studenti ji nevidí")}: ${r.zprava || ""}`;
    $("#nt-id").value = r.id;
  } else {
    st.className = "tiny err";
    st.textContent = (r && (r.detail || r.zprava)) || t("uložení se nezdařilo");
  }
  if (r && (r.model || r.detail)) {
    const d = r.detail || {}, n = r.model || {};
    const doplnek = [];
    if (d.vystup_reseni) doplnek.push(t("výstup řešení") + ": " + String(d.vystup_reseni).slice(0, 300));
    if ((n.zavady || []).length) doplnek.push(t("model:") + " " + n.zavady.join("; "));
    if (n["obtížnost"]) doplnek.push(`${t("obtížnost")}: ${n["obtížnost"]}`);
    if (doplnek.length) st.textContent += " — " + doplnek.join(" | ");
  }
  loadLib();
}

/* ------------------------------------------------------------------ správa */
async function loadAdmin() {
  const kpi = $("#admin-kpis");
  if (!kpi) return;
  kpi.innerHTML = '<p class="muted tiny">načítám…</p>';
  let s;
  try { s = await api("/api/system"); } catch (e) { kpi.innerHTML = '<p class="err">není spojení</p>'; return; }
  kpi.innerHTML = [
    ["Úlohy", `${s.tasks}`, `${s.drafts} čeká na ověření`],
    ["Účty", s.users, `${s.attempts} pokusů celkem`],
    ["Databáze", `${(s.db_bytes / 1024).toFixed(0)} kB`, `verze ${s.version}`],
  ].map(([l, v, p]) => `<div class="card"><div class="muted tiny">${l}</div>
      <div class="kpi">${v}</div><div class="tiny muted">${esc(p)}</div></div>`).join("");

  const u = await api("/api/users");
  const prihlasen = (cas) => cas ? new Date(cas * 1000).toLocaleDateString("cs-CZ") : "ještě nic";
  $("#adm-users").innerHTML = "<tr><th>jméno</th><th>role</th><th>heslo</th><th>naposledy</th><th></th></tr>" +
    u.users.map(x => `<tr><td>${esc(x.user)}</td>
      <td><select data-user="${esc(x.user)}" class="rolepick">${u.roles.map(r =>
        `<option ${r === x.role ? "selected" : ""}>${r}</option>`).join("")}</select></td>
      <td>${x.generated_pw ? '<span class="pill">vygenerované</span>' : (x.changed ? "vlastní" : "výchozí")}</td>
      <td class="tiny muted">${prihlasen(x.prihlasen)}</td>
      <td class="row" style="gap:4px;flex-wrap:nowrap">
        <button class="ghost" data-newpw="${esc(x.user)}">nové heslo</button>
        <button class="ghost" data-logout="${esc(x.user)}" title="odhlásit všechny relace">odhlásit</button>
        <button class="ghost" data-smaz="${esc(x.user)}" title="smazat účet i s daty">smazat</button>
      </td></tr>`).join("");
  $$("#adm-users [data-logout]").forEach(b => b.onclick = () => {
    potvrd(`odhlásit účet ${b.dataset.logout} ve všech prohlížečích?`, async () => {
      await api(`/api/users/${encodeURIComponent(b.dataset.logout)}/logout`, { method: "POST", body: "{}" });
      toast("účet odhlášen ze všech zařízení");
    }, "odhlásit");
  });
  $$("#adm-users [data-smaz]").forEach(b => b.onclick = () => {
    ptat(`Smazání účtu je nevratné — napiš jméno účtu ${b.dataset.smaz}, pokud na to máš.`,
         b.dataset.smaz, "text", false).then(hodnota => {
      if (!hodnota) return;
      api(`/api/users/${encodeURIComponent(b.dataset.smaz)}?potvrdit=${encodeURIComponent(hodnota)}`,
          { method: "DELETE" })
        .then(() => { toast("účet smazán"); loadAdmin(); })
        .catch(e => toast(String(e.message || e)));
    });
  });
  $$("#adm-users .rolepick").forEach(sel => sel.onchange = async () => {
    await api(`/api/users/${sel.dataset.user}/role`, { method: "POST",
      body: JSON.stringify({ user: sel.dataset.user, role: sel.value }) });
    toast(`role účtu ${sel.dataset.user}: ${sel.value}`);
  });
  $$("#adm-users [data-newpw]").forEach(b => b.onclick = () => setNewPassword(b.dataset.newpw));
  $("#nu-role").innerHTML = u.roles.map(r => `<option>${r}</option>`).join("");

  renderBackupCard();

  renderProvoz(s);

  renderLoginCard();

  renderAICard();

  const bankaAdmin = $("#adm-bank");
  if (bankaAdmin) {
    bankaAdmin.innerHTML = `<p class="tiny">${s.tasks} ${t("úloh")} · lekce ${s.lesson_current} ${t("je aktuální")}</p>
      <p class="tiny muted">datasets: ${esc((s.datasets || []).slice(0, 6).join(", "))}${(s.datasets || []).length > 6 ? " …" : ""}</p>
      ${s.agent_note ? `<p class="tiny muted" style="margin-top:8px;white-space:pre-wrap">${esc(s.agent_note)}</p>` : ""}
      <div class="banka" id="adm-banka"></div>`;
    nakresliBanku($("#adm-banka"), "ab");
  }
}

async function setNewPassword(name) {
  /* heslo se NEptá přes prompt() — vlastní dialog, vícerádkový, bez blokujícího okna */
  let pw = await ptat(`Nové heslo pro účet ${name}`, "heslo (aspoň 8 znaků) — nebo nech prázdné a vygeneruju",
                      "password", true);
  if (pw === null || pw === undefined) return;
  if (!pw) pw = vyhheslo();
  if (pw.length < 8) { toast("heslo musí mít aspoň 8 znaků"); return; }
  const r = await api(`/api/users/${encodeURIComponent(name)}/password`,
    { method: "POST", redirect401: false, body: JSON.stringify({ user: name, password: pw }) });
  toast(r && r.ok ? `heslo pro ${name}: ${pw}` : ((r && r.detail) || "nepovedlo se"));
}

/**
 * Heslo jako čtyři slabiky + dva znaky: krátké na opsání hlasem, dost dlouhé na
 * to, aby ho neuhodl skript. Nevytváříme si iluzi bankovního hesla — účet je
 * doma v LAN a po prvním přihlášení si člověk heslo změní.
 */
function vyhheslo() {
  const hlasky = ["ka", "ne", "mi", "tov", "ple", "rdu", "sti", "kve", "lom", "ben", "drs", "tyk",
                  "hrad", "vice", "slun", "rove", "poto", "kamy", "vetr", "list"];
  const vyber = (arr) => arr[Math.floor(Math.random() * arr.length)];
  const cislice = () => String(Math.floor(Math.random() * 100)).padStart(2, "0");
  let slovo = "";
  do { slovo = vyber(hlasky) + vyber(hlasky) + vyber(hlasky) + vyber(hlasky) + cislice(); }
  while (slovo.length < 12);
  return slovo;
}

/** Malý dotazovací dialog s jedním polem — náhrada za window.prompt. */
function ptat(title, placeholder, type = "text", generuj = false) {
  return new Promise(resolve => {
    let box = $("#askmodal");
    if (!box) {
      box = document.createElement("div");
      box.className = "modal"; box.id = "askmodal"; box.hidden = true;
      box.innerHTML = `<div class="card pwcard"><h3 id="ask-title"></h3>
        <span class="pw"><input id="ask-input" autocomplete="off">
        <button class="eye" type="button" data-eye="ask-input" aria-pressed="false"
                title="ukázat heslo" aria-label="ukázat heslo">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/>
          <circle cx="12" cy="12" r="3"/></svg></button></span>
        <button id="ask-gen" type="button" class="ghost">vygenerovat</button>
        <p class="err tiny" id="ask-err"></p>
        <div class="row end"><button id="ask-no" type="button" class="ghost">zrušit</button>
        <button id="ask-yes" type="button" class="primary">uložit</button></div></div>`;
      document.body.appendChild(box);
    }
    $("#ask-title").textContent = title;
    const inp = $("#ask-input");
    inp.type = type; inp.placeholder = placeholder; inp.value = "";
    inp.autocomplete = type === "password" ? "new-password" : "off";
    $("#askmodal .pw").style.display = type === "password" ? "" : "none";
    $("#ask-gen").style.display = generuj ? "" : "none";
    $("#ask-gen").onclick = () => {
      inp.value = vyhheslo(); inp.type = "text";
      const oko = document.querySelector('[data-eye="ask-input"]');
      if (oko) oko.setAttribute("aria-pressed", "true");
    };
    $("#ask-err").textContent = "";
    box.hidden = false; inp.focus();
    const done = (val) => { box.hidden = true; inp.onkeydown = null; resolve(val); };
    $("#ask-yes").onclick = () => done(inp.value.trim());
    $("#ask-no").onclick = () => done("");
    box.onclick = (e) => { if (e.target.id === "askmodal") done(""); };
    inp.onkeydown = (e) => { if (e.key === "Enter") done(inp.value.trim()); };
  });
}

/* ---------------------------------------------------------------- init */
window.addEventListener("DOMContentLoaded", () => {
  $("#app").style.display = "flex";
  initEditor();
  watchTranslations();
  try { applyTheme(localStorage.getItem("rpraxe.theme") || "auto"); } catch (e) {}
  try { applyLang(localStorage.getItem("rpraxe.lang") || "cs"); } catch (e) {}
  $$("nav button").forEach(b => b.onclick = () => show(b.dataset.view));
  $("#btn-run").onclick = () => runCode(false);
  $("#btn-check").onclick = () => runCode(true);
  $("#btn-hint").onclick = async () => {
    if (!current) return;
    hintStep++;
    const r = await api("/api/hint", { method: "POST", body: JSON.stringify({
      task_id: current.id, step: hintStep, code: cm.getValue() }) });
    $("#hintbox").innerHTML = `<div class="coach"><strong>${r.source === "ai" ? "Kouč (doplněná napověda)" : "Napověď"}:</strong> ${esc(r.text)}</div>`;
  };
  $("#btn-sol").onclick = async () => {
    if (!current) return;
    potvrd("Otevřít řešení? Počítá se to jako nápověda — pak to přepiš bez koukání.", showSolution, "ukázat řešení");
    $("#hintbox").innerHTML = `<div class="coach"><strong>Řešení:</strong></div><pre class="out">${esc(r.reseni)}</pre>
      <p class="tiny muted">${esc(r.note)}</p>`;
  };
  $("#btn-note").onclick = openNote;
  $("#note-cancel").onclick = () => { $("#notemodal").hidden = true; };
  $("#note-save").onclick = () => ulozPoznamku($("#note-text").value);
  $("#note-delete").onclick = () => ulozPoznamku("");
  $("#notemodal").onclick = (e) => { if (e.target.id === "notemodal") $("#notemodal").hidden = true; };
  $("#btn-refresh").onclick = () => potvrd("Složit novou dnešní dávku? Dosavadní pokusy zůstanou v historii.",
    async () => { await api("/api/plan?refresh=1"); await loadBoot(); }, "nová dávka");
  $("#budget").onchange = async () => { await api(`/api/plan?minutes=${$("#budget").value}`); await loadBoot(); };
  const tlacitkoNové = $("#btn-nova");
  if (tlacitkoNové) tlacitkoNové.onclick = () => novaUloha();
  $("#btn-gen").onclick = async () => {
    $("#genstatus").textContent = "AI píše a ověřuje… (třeba minuta)";
    const r = await api("/api/generate?count=2", { method: "POST" });
    $("#genstatus").textContent = r.created.map(c => `${c.title}: ${c.validated ? "ověřeno" : "zastaveno"}`).join(" · ") || "nic nevzniklo";
    loadLib();
  };
  document.addEventListener("click", e => {
    const tlacitko = e.target.closest && e.target.closest("[data-eye]");
    if (!tlacitko) return;
    const pole = document.getElementById(tlacitko.dataset.eye);
    if (!pole) return;
    const odhaleno = pole.type === "password";
    pole.type = odhaleno ? "text" : "password";
    tlacitko.setAttribute("aria-pressed", String(odhaleno));
    tlacitko.title = odhaleno ? "skrýt heslo" : "ukázat heslo";
    tlacitko.setAttribute("aria-label", tlacitko.title);
    pole.focus();
  });
  $("#nu-gen").onclick = () => {
    const heslo = vyhheslo();
    const pole = $("#nu-pass");
    pole.value = heslo; pole.type = "text";
    const eye = document.querySelector('[data-eye="nu-pass"]');
    if (eye) { eye.setAttribute("aria-pressed", "true"); eye.title = "skrýt heslo"; }
    $("#nu-status").className = "tiny ok";
    $("#nu-status").textContent = `vygenerováno: ${heslo} — zkopíruj si ho, po založení už ho neuvidíš`;
  };
  $("#btn-settings").onclick = openSettings;
  $("#set-cancel").onclick = () => { $("#setmodal").hidden = true; };
  $("#set-save").onclick = saveSettings;
  $("#setmodal").onclick = (e) => { if (e.target.id === "setmodal") $("#setmodal").hidden = true; };
  $("#nt-save").onclick = () => saveTask(false);
  if ($("#nt-force")) $("#nt-force").onclick = () => saveTask(true);
  if ($("#tc-new")) $("#tc-new").onclick = novaTrida;
  if ($("#tc-save")) $("#tc-save").onclick = ulozTridu;
  if ($("#tc-del")) $("#tc-del").onclick = () => smazTridu(TRIDA_VYBRANA);
  $$(".js-nova-uloha").forEach(tlacitko => { tlacitko.onclick = novaUloha; });
  try {
    const minule = localStorage.getItem("rpraxe.github");
    if (minule && $("#gh-url")) $("#gh-url").value = minule;
  } catch (e) {}
  if ($("#taskmodal-close")) $("#taskmodal-close").onclick = zavriEditor;
  if ($("#nt-dat-nahrat")) $("#nt-dat-nahrat").onclick = async () => {
    const r = await nahrejSouborDat(document, $("#nt-dat"), $("#nt-dat-status"), $("#nt-dat-prepsat")?.checked);
    if (r && r.ok) $("#nt-dataset").value = r.jmeno;
  };
  const dialogEditor = $("#taskmodal");
  if (dialogEditor) dialogEditor.onclick = (e) => { if (e.target.id === "taskmodal") zavriEditor(); };
  $("#nt-clear").onclick = () => {
    ["nt-id", "nt-title", "nt-skills", "nt-dataset", "nt-nacti", "nt-starter", "nt-zadani",
     "nt-reseni", "nt-check", "nt-hints"].forEach(id => { $("#" + id).value = ""; });
    $("#nt-status").textContent = "";
  };
  $("#nu-add").onclick = async () => {
    const st = $("#nu-status");
    const r = await api("/api/users", { method: "POST", redirect401: false, body: JSON.stringify({
      user: $("#nu-name").value.trim(), password: $("#nu-pass").value, role: $("#nu-role").value }) });
    st.className = "tiny " + (r && r.ok ? "ok" : "err");
    st.textContent = r && r.ok ? `účet ${r.user} vytvořen (${r.role})` : ((r && r.detail) || "nepovedlo se");
    if (r && r.ok) { $("#nu-name").value = ""; $("#nu-pass").value = ""; loadAdmin(); }
  };
  $("#btn-user").onclick = (e) => {
    e.stopPropagation();
    const open = $("#usermenu").hidden;
    $("#usermenu").hidden = !open;
    $("#btn-user").setAttribute("aria-expanded", String(open));
  };
  $("#btn-pass").onclick = openPassword;
  const odhlasVse = $("#btn-logout-all");
  if (odhlasVse) odhlasVse.onclick = () => {
    closeUserMenu();
    potvrd("odhlásit tohle konto ve všech ostatních prohlížečích?", async () => {
      await api("/api/logout-all", { method: "POST", body: "{}" });
      toast("ostatní zařízení jsou odhlášená");
    }, "odhlásit");
  };
  const exportTridyTlacitko = $("#tc-export");
  if (exportTridyTlacitko) exportTridyTlacitko.onclick = exportTridy;
  $("#pw-cancel").onclick = closePassword;
  $("#pw-save").onclick = submitPassword;
  $("#pwmodal").onclick = (e) => { if (e.target.id === "pwmodal") closePassword(); };
  $("#pw-rep").addEventListener("keydown", e => { if (e.key === "Enter") submitPassword(); });
  document.addEventListener("keydown", e => {
    if (e.key !== "Escape") return;
    closePassword(); closeUserMenu();
    zavriEditor();
    ["#setmodal", "#notemodal", "#okmodal", "#askmodal"].forEach(s => { const el = $(s); if (el) el.hidden = true; });
  });
  document.addEventListener("click", (e) => {
    const t = e.target;
    if (!(t && t.closest && t.closest(".usermenu"))) closeUserMenu();
  });

  loadBoot();
});
