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
        <td>${t.status === "draft" ? '<span class="pill">ověřit</span>' : ""}
            <button data-id="${esc(t.id)}" class="ghost pick">do dneška</button></td></tr>`).join("");
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

async function loadProg() {
  const p = await api("/api/progress");
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
  const zmerenе = (p.skills || []).filter(s => (s.n || 0) > 0);
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
  if (lbl) lbl.textContent = zmerenе.length
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
  loadTahak();
  nactiPoznamky().then(vykresliSeznamPoznamek);
  $$("#hard a").forEach(a => a.onclick = e => { e.preventDefault(); openTask(a.dataset.id); show("today"); });
}

function show(view) {
  $$("nav button").forEach(b => b.classList.toggle("on", b.dataset.view === view));
  $$(".view").forEach(v => v.classList.toggle("on", v.id === "v-" + view));
  if (view === "lib") loadLib();
  if (view === "prog") loadProg();
  if (view === "sheet") loadTahak();
  if (view === "class") loadClass();
  if (view === "admin") loadAdmin();
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
  const langs = Object.entries(s.langs || { cs: "čeština" });
  fill($("#set-lang"), langs, s.lang || "cs");
  fill($("#set-min"), (s.budgets || [15, 20, 30, 45]).map(m => [m, `${m} min`]), s.minutes || 20);
  const models = [["", t("Výchozí") + (s.default_model ? ` (${s.default_model})` : "")]]
    .concat((s.models || []).map(m => [m, m]));
  fill($("#set-model"), models, s.model || "");
  $("#set-ainote").textContent = s.ai_online
    ? `${(s.models || []).length} modelů na lokální Ollamě; data neopouštějí dům.`
    : "Lokální model je zrovna nedostupný — kouč odpovídá z banky napověd.";
  $("#setmodal").hidden = false;
  $("#set-theme").focus();
}

async function saveSettings() {
  const body = {
    theme: $("#set-theme").value, lang: $("#set-lang").value,
    model: $("#set-model").value, minutes: Number($("#set-min").value),
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
    $("#setmodal").hidden = true;
    toast("Nastavení uložené.");
    await loadBoot();
    return;
  }
  $("#set-err").textContent = (r && (r.detail || r.msg)) || "Uložení se nezdařilo.";
}

/* ------------------------------------------------------------------ třída */
async function loadClass() {
  const box = $("#class");
  if (!box) return;
  box.innerHTML = '<p class="muted tiny">načítám…</p>';
  const d = await api("/api/class");
  const zaci = d.students || [];
  box.innerHTML = "<tr><th>jméno</th><th>naposledy</th><th>úlohy</th><th>první dobrou</th>" +
    "<th>odklikáno</th><th>řada</th><th>slabé místa</th><th></th></tr>" + (zaci.length ? zaci.map(s => `
      <tr><td><strong>${esc(s.user)}</strong></td>
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
  box.innerHTML = `<h3>${esc(user)}</h3>
    <p class="tiny muted">${p.total || 0} pokusů · ${p.passed || 0} správně ·
      ${p.first_try_rate ?? 0} % na první dobrou · ${p.days_active || 0} dní ·
      ${Math.round(p.minutes_total || 0)} min</p>
    <div class="row" style="gap:5px;flex-wrap:wrap">${doved || '<span class="muted tiny">zatím nic</span>'}</div>
    <table id="stud-recent" style="margin-top:10px"></table>`;
  $("#stud-recent").innerHTML = "<tr><th>kdy</th><th>úloha</th><th></th></tr>" + (p.recent || []).map(a =>
    `<tr><td class="tiny muted">${new Date(a.ts * 1000).toLocaleString("cs-CZ")}</td>
     <td>${esc(a.title || a.task)}</td><td>${a.ok ? "✓" : "✗"}</td></tr>`).join("");
}

async function saveTask() {
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
  };
  const st = $("#nt-status");
  st.className = "tiny muted"; st.textContent = "ověřuji spuštěním…";
  $("#nt-save").disabled = true;
  let r;
  try { r = await api("/api/tasks", { method: "POST", redirect401: false, body: JSON.stringify(body) }); }
  catch (e) { r = { detail: "server nedostupný" }; }
  $("#nt-save").disabled = false;
  if (r && r.ok) {
    st.className = "tiny ok"; st.textContent = `úloha ${r.id} uložena a ověřena`;
    $("#nt-id").value = r.id; loadLib();
  } else {
    st.className = "tiny err";
    st.textContent = (r && (r.detail || r.msg)) || "uložení se nezdařilo";
  }
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
  $("#adm-users").innerHTML = "<tr><th>jméno</th><th>role</th><th>heslo</th><th></th></tr>" +
    u.users.map(x => `<tr><td>${esc(x.user)}</td>
      <td><select data-user="${esc(x.user)}" class="rolepick">${u.roles.map(r =>
        `<option ${r === x.role ? "selected" : ""}>${r}</option>`).join("")}</select></td>
      <td>${x.generated_pw ? '<span class="pill">vygenerované</span>' : (x.changed ? "vlastní" : "výchozí")}</td>
      <td><button class="ghost" data-newpw="${esc(x.user)}">nové heslo</button></td></tr>`).join("");
  $$("#adm-users .rolepick").forEach(sel => sel.onchange = async () => {
    await api(`/api/users/${sel.dataset.user}/role`, { method: "POST",
      body: JSON.stringify({ user: sel.dataset.user, role: sel.value }) });
    toast(`role účtu ${sel.dataset.user}: ${sel.value}`);
  });
  $$("#adm-users [data-newpw]").forEach(b => b.onclick = () => setNewPassword(b.dataset.newpw));
  $("#nu-role").innerHTML = u.roles.map(r => `<option>${r}</option>`).join("");

  const bk = s.backups || {};
  $("#adm-backups").innerHTML = `<p class="tiny muted">Poslední noční záloha:
      ${bk.last && bk.last.at ? new Date(bk.last.at * 1000).toLocaleString("cs-CZ") + ` → ${esc(bk.last.dest || "NAS")}`
                               : "zatím žádná (skript běží v noci)"}
    </p><ul class="tiny muted">` +
    (bk.local || []).map(f => `<li>${esc(f.name)} · ${(f.bytes / 1024).toFixed(0)} kB ·
      ${new Date(f.mtime * 1000).toLocaleString("cs-CZ")}</li>`).join("") + "</ul>";

  const sso = s.sso || {};
  $("#adm-login").innerHTML = `<p class="tiny">${sso.zapnuto ? "✓ heslo + brána" : "✓ přihlášení heslem"}</p>
    <p class="tiny muted">${esc(sso.popis || "")}</p>` +
    (sso.zapnuto
      ? `<p class="tiny muted">hlavička jméno: <code>${esc(sso.hlavka_jmeno)}</code>${
          sso.hlavka_role ? `, role: <code>${esc(sso.hlavka_role)}</code>` : ""}</p>`
      : `<p class="tiny muted">Přihlášení přes bránu (SSO) se zapne v <code>rpraxe.env</code>:
          <code>RPRAXE_SSO_SECRET</code> a <code>RPRAXE_SSO_HEADER</code> — pak se na přihlašovací
          stránce objeví druhé tlačítko. Postup a vzor pro Caddy/Authelia je v <code>docs/sso.md</code>.</p>`);

  $("#adm-ai").innerHTML = `<p class="tiny">${s.ai_online ? "✓ model dostupný" : "✗ model nedostupný"}</p>
    <p class="tiny muted">píše: <code>${esc(s.model_write)}</code></p>
    <ul class="tiny muted">` + (s.models || []).map(m => `<li><code>${esc(m)}</code></li>`).join("") + "</ul>";

  $("#adm-bank").innerHTML = `<p class="tiny">${s.tasks} úloh · lekce ${s.lesson_current} je aktuální</p>
    <p class="tiny muted">datasets: ${esc((s.datasets || []).slice(0, 6).join(", "))}${(s.datasets||[]).length>6?" …":""}</p>
    ${s.agent_note ? `<p class="tiny muted" style="margin-top:8px;white-space:pre-wrap">${esc(s.agent_note)}</p>` : ""}`;
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
  $("#nt-save").onclick = saveTask;
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
  $("#adm-backup").onclick = async () => {
    const b = $("#adm-backup"); b.disabled = true; b.textContent = "tvářím snímek…";
    const r = await api("/api/admin/backup", { method: "POST", redirect401: false });
    b.disabled = false; b.textContent = "udělat snímek teď";
    toast(r && r.ok ? `snímek ${r.name} (${(r.bytes / 1024).toFixed(0)} kB)` : "záloha se nezdařila");
    loadAdmin();
  };
  $("#btn-user").onclick = (e) => {
    e.stopPropagation();
    const open = $("#usermenu").hidden;
    $("#usermenu").hidden = !open;
    $("#btn-user").setAttribute("aria-expanded", String(open));
  };
  $("#btn-pass").onclick = openPassword;
  $("#pw-cancel").onclick = closePassword;
  $("#pw-save").onclick = submitPassword;
  $("#pwmodal").onclick = (e) => { if (e.target.id === "pwmodal") closePassword(); };
  $("#pw-rep").addEventListener("keydown", e => { if (e.key === "Enter") submitPassword(); });
  document.addEventListener("keydown", e => {
    if (e.key !== "Escape") return;
    closePassword(); closeUserMenu();
    ["#setmodal", "#notemodal", "#okmodal", "#askmodal"].forEach(s => { const el = $(s); if (el) el.hidden = true; });
  });
  document.addEventListener("click", (e) => {
    const t = e.target;
    if (!(t && t.closest && t.closest(".usermenu"))) closeUserMenu();
  });

  loadBoot();
});
