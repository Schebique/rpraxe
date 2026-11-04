"""rpraxe runner — izolovaný běh R kódu + automatická kontrola.

POST /run {code, check?, datasets, libraries, plots}
Kód studenta běží jako neprivilegovaný uživatel `sandbox` v dočasném adresáři,
kam se zkopírují jen datové soubory, které úloha potřebuje. Limity: CPU, RAM,
velikost souboru, počet procesů, wall-clock timeout.
"""
from __future__ import annotations

import json
import os
import resource
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="rpraxe-runner", docs_url=None, redoc_url=None)

DATASETS = Path(os.environ.get("RPRAXE_DATASETS", "/data/datasets"))
SANDBOX_UID = int(os.environ.get("RPRAXE_SANDBOX_UID", "4242"))
SANDBOX_GID = int(os.environ.get("RPRAXE_SANDBOX_GID", "4242"))
CPU_LIMIT = int(os.environ.get("RPRAXE_CPU_LIMIT", "20"))
WALL_LIMIT = int(os.environ.get("RPRAXE_WALL_LIMIT", "30"))
MEM_MB = int(os.environ.get("RPRAXE_MEM_MB", "1500"))
OUT_BYTES = 40_000
REPORT_MARK = "@@RPRAXE@@"

R_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/tmp",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "R_LIBS_USER": "/usr/local/lib/R/site-library",
    "TZ": "Europe/Prague",
    "OMP_NUM_THREADS": "2",
    "OPENBLAS_NUM_THREADS": "2",
}

HELPERS = r"""
# --- pomocnici pro kontrolu ------------------------------------------------
.v_spam <- function(msg) list(pass = FALSE, msg = msg)
.v_ok   <- function(msg = "") list(pass = TRUE, msg = msg)
.v_num <- function(got, want, tol = 1e-4, msg_ok = "") {
  if (is.null(got)) return(.v_spam("Vysledek jsem v tvem kodu nenasel."))
  got <- suppressWarnings(as.numeric(unlist(got)))
  if (length(got) == 0 || all(is.na(got)))
    return(.v_spam("Vysledek neni cislo. Zkus `as.numeric()`, nebo zkontroluj chybejici hodnoty."))
  if (any(is.na(got)))
    return(.v_spam("Ve vysledku je NA — agreguj pres `na.rm = TRUE` nebo vyfiltruj chybejici radky."))
  want <- as.numeric(want)
  if (length(got) != length(want))
    return(.v_spam(paste0("Mel by to vratit ", length(want), " hodnot(y), mas je ", length(got), ".")))
  if (all(abs(got - want) <= tol * pmax(1, abs(want)))) .v_ok(msg_ok) else
    .v_spam("Cisla nesedi. Zkontroluj, jestli pocitavas presne ty radky, ktere zadani chce (filtr, na.rm).")
}
.v_txt <- function(got, want, msg_ok = "") {
  if (is.null(got)) return(.v_spam("Textovy vysledek jsem nenasel."))
  g <- trimws(as.character(unlist(got))[1]); w <- trimws(as.character(want))
  if (identical(g, w)) .v_ok(msg_ok) else
    .v_spam("Text nesedi presne. Pozor na velka/mala pismena, mezery a diakritiku.")
}
.v_contains <- function(got, pattern, msg_ok = "") {
  g <- tolower(paste(as.character(unlist(got)), collapse = " "))
  if (grepl(tolower(pattern), g, fixed = TRUE)) .v_ok(msg_ok) else
    .v_spam(paste0("V odpovedi mi chadi slovo/pojem `", pattern, "`."))
}
.v_plot <- function(got = NULL, msg_ok = "Graf je hotovy.") {
  if (is.null(got)) {
    .n <- if (exists(".plotres", envir = globalenv())) get("n", envir = .plotres) else 0L
    if (isTRUE(.n > 0L)) return(.v_ok(msg_ok))
    return(.v_spam("Graf jsem nevidel — zavolej plot(...) (nebo ggplot(...) a vykresli ho)."))
  }
  if (inherits(got, c("gg", "ggplot"))) .v_ok(msg_ok) else
    .v_spam("Vysledkem by mel byt objekt `ggplot`. Zkus `graf <- ggplot(...) + geom_...()`.")
}
.v_df <- function(got, want, msg_ok = "") {
  if (is.null(got) || !(is.data.frame(got) || inherits(got, "tbl_df")))
    return(.v_spam("Vysledkem ma byt tabulka (data frame / tibble)."))
  g <- as.data.frame(got, stringsAsFactors = FALSE)
  w <- as.data.frame(want, stringsAsFactors = FALSE)
  if (nrow(g) != nrow(w))
    return(.v_spam(paste0("Máš ", nrow(g), " radku, mit jich mit ", nrow(w), ".")))
  if (!setequal(tolower(names(g)), tolower(names(w))))
    return(.v_spam(paste0("Sloupce: mas ", paste(names(g), collapse = ", "),
                          "; mit tam byt ", paste(names(w), collapse = ", "), ".")))
  w <- w[, match(names(g), names(w)), drop = FALSE]
  num <- vapply(w, is.numeric, logical(1))
  if (any(num)) {
    gv <- as.matrix(as.data.frame(lapply(g[, num, drop = FALSE], as.numeric)))
    wv <- as.matrix(as.data.frame(lapply(w[, num, drop = FALSE], as.numeric)))
    if (!isTRUE(all.equal(as.numeric(gv), as.numeric(wv), tolerance = 1e-3)))
      return(.v_spam("V ciselnych sloupcich jsou jine hodnoty, nez maji byt."))
  }
  if (any(!num)) {
    gc <- as.matrix(as.data.frame(lapply(g[, !num, drop = FALSE], as.character)))
    wc <- as.matrix(as.data.frame(lapply(w[, !num, drop = FALSE], as.character)))
    if (!identical(sort(as.vector(gc)), sort(as.vector(wc))))
      return(.v_spam("Textove sloupce nesouhlasi — zkontroluj filtrovani a prejmenovani."))
  }
  .v_ok(msg_ok)
}
"""


class RunReq(BaseModel):
    code: str = ""
    check: str | None = None
    datasets: list[str] = []
    libraries: list[str] = []
    files: dict[str, str] = {}
    plots: bool = True


def _indent(text: str, pad: str = "  ") -> str:
    return "\n".join(pad + line if line.strip() else line for line in text.splitlines())


def _limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT, CPU_LIMIT + 2))
    resource.setrlimit(resource.RLIMIT_AS, (MEM_MB * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (20 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        resource.setrlimit(resource.RLIMIT_NPROC, (96, 96))
    except (ValueError, OSError):
        pass


def _trim(text: str | None) -> str:
    text = text or ""
    if len(text) > OUT_BYTES:
        return text[:OUT_BYTES] + f"\n…[vystup zkracen na {OUT_BYTES} znaku]"
    return text


def build_script(req: RunReq) -> str:
    libs = ", ".join(f'"{x}"' for x in dict.fromkeys(["jsonlite", "base64enc"] + req.libraries))
    do_plots = "TRUE" if req.plots else "FALSE"
    check = (req.check or "list(pass = NA, msg = '')").rstrip()
    return (
        "\n.libPaths(c(\"/usr/local/lib/R/site-library\", .libPaths()))\n"
        "rm(list = ls())\n"
        "for (.l in c(" + libs + ")) {\n"
        "  suppressMessages(suppressWarnings(try(require(.l, character.only = TRUE, quietly = TRUE), silent = TRUE)))\n"
        "}\n"
        "options(digits = 5, warn = 1, width = 88, scipen = 5, stringsAsFactors = FALSE, useFancyQuotes = FALSE)\n"
        ".rep <- list(plots = list(), error = NULL, check = NULL, last = \"\")\n"
        # počítadlo skutečně vykreslených base grafů: hook `plot.new` volá R až po
        # úspěšném založení nového obrázku, takže rozbitý plot() se nepočítá
        ".plotres <- new.env()\n.plotres$n <- 0L\n"
        "setHook(\"plot.new\", function() if (exists(\".plotres\", envir = globalenv())) assign(\"n\", get(\"n\", envir = .plotres) + 1L, envir = .plotres))\n"
        + HELPERS +
        "\nif (" + do_plots + ") {\n"
        "  grDevices::png(filename = file.path(getwd(), \"plot_%03d.png\"), width = 840, height = 540, res = 110, bg = \"white\")\n"
        "}\n"
        "\n# --- studentsky kod (semantika konzole) ------------------------------\n"
        ".exprs <- tryCatch(parse(text = readLines(\".rpraxe_user.R\", warn = FALSE), keep.source = FALSE),\n"
        "                   error = function(e) { .rep$error <- paste0(\"Chyba syntaxe: \", conditionMessage(e)); NULL })\n"
        "if (!is.null(.exprs)) {\n"
        "  for (.e in .exprs) {\n"
        "    .r <- tryCatch(withVisible(eval(.e, envir = globalenv())),\n"
        "                   error = function(e) structure(conditionMessage(e), class = \"rpraxeErr\"))\n"
        "    if (inherits(.r, \"rpraxeErr\")) { .rep$error <- paste0(.r); break }\n"
        "    if (isTRUE(.r$visible)) {\n"
        "      print(.r$value)\n"
        "      .rep$last <- paste(utils::capture.output(print(.r$value)), collapse = \"\\n\")\n"
        "    }\n"
        "  }\n"
        "}\n"
        "\n# --- kontrola ----------------------------------------------------------\n"
        "if (is.null(.rep$error)) {\n"
        "  .chk <- tryCatch({\n"
        "    .v_check <- function() {\n"
        + _indent(check) +
        "\n    }\n"
        "    environment(.v_check) <- globalenv()\n"
        "    .v_check()\n"
        "  }, error = function(e) paste0(\"Kontrola tvou odpoved nedokaze precist: \", conditionMessage(e)))\n"
        "  if (is.list(.chk) && !is.null(.chk$pass)) {\n"
        "    .rep$check <- list(pass = isTRUE(.chk$pass), msg = if (is.null(.chk$msg)) \"\" else paste(.chk$msg, collapse = \" \"))\n"
        "  } else if (is.logical(.chk) && length(.chk) == 1 && !is.na(.chk)) {\n"
        "    .rep$check <- list(pass = isTRUE(.chk), msg = \"\")\n"
        "  } else if (is.character(.chk) && length(.chk) == 1) {\n"
        "    .rep$check <- list(pass = FALSE, msg = .chk)\n"
        "  } else if (is.null(.chk)) {\n"
        "    .rep$check <- list(pass = TRUE, msg = \"kontrola proběhla bez výhrad\")\n"
        "  } else {\n"
        "    .rep$check <- list(pass = NA, msg = paste(\"kontrola nevrátila TRUE/FALSE, dostalo se:\", class(.chk)[1]))\n"
        "  }\n"
        "}\n"
        "\n# --- grafy -------------------------------------------------------------\n"
        "if (" + do_plots + ") {\n"
        "  invisible(try(grDevices::dev.off(), silent = TRUE))\n"
        "  for (.f in head(sort(list.files(getwd(), pattern = \"^plot_[0-9]+[.]png$\")), 4)) {\n"
        "    .p <- file.path(getwd(), .f)\n"
        "    if (!is.na(file.info(.p)$size) && file.info(.p)$size > 2000)\n"
        "      .rep$plots[[length(.rep$plots) + 1L]] <- jsonlite::base64_enc(readBin(.p, \"raw\", file.info(.p)$size))\n"
        "  }\n"
        "}\n"
        # co v prostředí zůstalo: když žák vše uložil do proměnných, R nic
        # nevypíše a vypadá to, že „kód nevrátil nic“ — tohle ukáže, co zůstalo
        "\nif (is.null(.rep$error)) {\n"
        "  .envr <- character(0)\n"
        "  for (.nm in ls(globalenv())) {\n"
        "    .v <- tryCatch(get(.nm, envir = globalenv()), error = function(e) NULL)\n"
        "    .d <- tryCatch(paste(utils::capture.output(utils::str(.v, vec.len = 3, structure.len = 2, max.level = 1)),\n"
        "                       collapse = \" \"), error = function(e) paste(class(.v), collapse = \"/\"))\n"
        "    .envr <- c(.envr, paste0(.nm, \" - \", substr(trimws(.d), 1, 120)))\n"
        "  }\n"
        "  .rep$env <- utils::head(.envr, 12L)\n"
        "}\n"
        "if (is.null(.rep$env)) .rep$env <- character(0)\n"
        "if (nchar(.rep$last) > 3000) .rep$last <- substr(.rep$last, 1, 3000)\n"
        "cat(\"" + REPORT_MARK + "\", jsonlite::toJSON(.rep, auto_unbox = TRUE, na = \"null\", null = \"null\"), sep = \"\", file = stderr())\n"
    )


def _run(workdir: Path, code: str, script: str) -> tuple[int, str, str]:
    (workdir / ".rpraxe_user.R").write_text(code, encoding="utf-8")
    (workdir / ".rpraxe_run.R").write_text(script, encoding="utf-8")
    os.chmod(workdir, 0o755)
    os.chown(workdir, SANDBOX_UID, SANDBOX_GID)
    for f in workdir.iterdir():
        if f.is_file():
            os.chmod(f, 0o644)
            os.chown(f, SANDBOX_UID, SANDBOX_GID)
    try:
        proc = subprocess.run(
            ["setpriv", "--reuid", str(SANDBOX_UID), "--regid", str(SANDBOX_GID), "--clear-groups", "--",
             "timeout", "--foreground", "-k", "2", str(WALL_LIMIT),
             "Rscript", "--vanilla", "--no-save", "--no-restore", ".rpraxe_run.R"],
            cwd=workdir, capture_output=True, text=True, timeout=WALL_LIMIT + 8,
            preexec_fn=_limits, env=R_ENV,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", (f"Skript bezel dele nez {WALL_LIMIT} s a byl zastaven. "
                         "Casto pomuze neopakovat ten stejny vypocet dokola nebo prestat nekonecnou smycku.")


def _parse_report(stderr_text: str) -> tuple[dict, str]:
    clean, report = [], {}
    for line in (stderr_text or "").splitlines():
        if REPORT_MARK in line:
            blob = line.split(REPORT_MARK, 1)[1].strip()
            try:
                report = json.loads(blob)
                continue
            except json.JSONDecodeError:
                pass
        clean.append(line)
    return report, "\n".join(clean)


@app.get("/health")
def health():
    p = subprocess.run(["Rscript", "-e", "cat(R.version.string)"], capture_output=True, text=True)
    return {"ok": True, "r": p.stdout.strip(),
            "datasets": sorted(p.name for p in DATASETS.glob("*") if p.is_file())[:60]}


@app.post("/run")
def run(req: RunReq) -> dict:
    t0 = time.time()
    if not (req.code or "").strip():
        return {"stdout": "", "stderr": "", "plots": [], "check": None,
                "error": "Kod je prazdny — napis aspon jeden prikaz.", "exit": 0, "ms": 0}

    workdir = Path(tempfile.mkdtemp(prefix="run-", dir="/work"))
    try:
        for name in req.datasets:
            src = (DATASETS / Path(name).name).resolve()
            if DATASETS.resolve() in src.parents and src.is_file():
                shutil.copy2(src, workdir / src.name)
        for name, content in req.files.items():
            (workdir / Path(name).name).write_text(str(content), encoding="utf-8")

        rc, out, err = _run(workdir, req.code, build_script(req))
        report, err_clean = _parse_report(err)
        if not report:
            report = {"plots": [], "check": None, "last": "",
                      "error": (err_clean or "").strip()[:1500] or f"Skript spadl (navratovy kod {rc})."}
        return {
            "stdout": _trim(out),
            "stderr": _trim(err_clean),
            "plots": (report.get("plots") or [])[:4],
            "check": report.get("check"),
            "error": report.get("error"),
            "last": report.get("last") or "",
            "env": report.get("env") or [],
            "exit": rc,
            "ms": int((time.time() - t0) * 1000),
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
