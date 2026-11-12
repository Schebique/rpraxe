# Ověří, že obraz obsahuje knihovny, na které se spoléhají úlohy i generátor dat.
# Spouští se v CI (`Rscript scripts/check_rpkgs.R`) i při buildu obrazu.
potrebne <- c("dplyr", "tidyr", "readr", "tibble", "stringr", "forcats", "lubridate",
              "purrr", "ggplot2", "jsonlite", "base64enc")
chybi <- setdiff(potrebne, rownames(installed.packages()))
if (length(chybi)) {
  cat("CHYBI KNIHOVNY:", paste(chybi, collapse = ", "), "\n")
  quit(status = 1)
}
cat("R", R.version.string, "| v poradku:", length(potrebne), "knihoven\n")
