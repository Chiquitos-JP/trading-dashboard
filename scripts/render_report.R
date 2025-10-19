## ==========================================================
## render_report.R — Quarto優先 → rmarkdown → knit→pandoc
## .qmd を毎回生成し、その同じ .qmd をフォールバックでも利用
## ログをコンソール＋テキストで出力
## ==========================================================

suppressPackageStartupMessages({
  library(fs); library(stringr); library(withr)
  library(rmarkdown); library(knitr); library(quarto)
})

##設定（必要に応じて修正）----
source_dir   <- "C:/Users/alpac/Dropbox/03_individual_work/05_stockTrading/05_site/pages"
template_qmd <- file.path(source_dir, "Report_Template_TradingDashboard.qmd")

today_tag   <- format(Sys.Date(), "%Y%m%d")
output_root <- "C:/Users/alpac/Dropbox/03_individual_work/05_stockTrading/05_site/pages/reports"
output_dir  <- file.path(output_root, paste0("weekly_report_", today_tag))
dir_create(output_dir, recurse = TRUE)

stub        <- paste0("WeeklyReport_", today_tag)
target_qmd  <- file.path(output_dir, paste0(stub, ".qmd"))
target_html <- file.path(output_dir, paste0(stub, ".html"))
mid_dir     <- file.path(output_dir, "_intermediate"); dir_create(mid_dir, recurse = TRUE)
pre_md      <- file.path(mid_dir, paste0(stub, ".md"))

## --------- ロガー ----------
stamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
log_path <- file.path(output_dir, paste0("render_log_", stamp, ".txt"))
log_lines <- character(0)
log <- function(level, ...) {
  line <- sprintf("[%s] %-5s %s", format(Sys.time(), "%H:%M:%S"), level, paste(..., collapse=" "))
  message(line); assign("log_lines", c(get("log_lines", inherits=TRUE), line), inherits=TRUE)
}
flush_log <- function() writeLines(log_lines, log_path, useBytes = TRUE)

log("INFO", "Start rendering:", stub)
log("INFO", "Output dir     :", output_dir)

## --------- KPI 等の前処理（任意）---------
kpi_script <- "C:/Users/alpac/Dropbox/03_individual_work/03_Whats_going_on/Work-wise/01_X_auto_tweets/02_R_stockTrade/01_analysis/01_byTimeSeries/kpi_calc.R"
if (file.exists(kpi_script)) {
  log("INFO","Source KPI script:", kpi_script)
  tryCatch(source(kpi_script), error=function(e) log("ERROR","KPI error:", e$message))
}

## --------- 当日 .qmd 生成/更新 ----------
file_copy(template_qmd, target_qmd, overwrite = TRUE)
qmd_txt <- readLines(target_qmd, warn = FALSE, encoding = "UTF-8")
qmd_txt <- gsub("\\{\\{DATE\\}\\}", today_tag, qmd_txt)

# YAML に keep-md を確保（rmarkdown/pandoc 復旧に使う）
if (!any(grepl("^format\\s*:", qmd_txt))) {
  qmd_txt <- c(qmd_txt, "", "format:", "  html:", "    toc: true", "    toc-depth: 3", "    keep-md: true")
} else if (!any(grepl("keep-md\\s*:\\s*true", qmd_txt))) {
  qmd_txt <- c(qmd_txt, "    keep-md: true")
}
writeLines(qmd_txt, target_qmd, useBytes = TRUE)
log("INFO", "Prepared qmd:", target_qmd)

## --------- 1) Quarto（最優先） ----------
rs <- normalizePath(Sys.which("Rscript"), winslash = "/", mustWork = TRUE)
log("INFO", "Try: Quarto render")
qres <- try(
  with_envvar(
    c(QUARTO_R = rs, QUARTO_R_ARGS = "--no-save --no-restore", QUARTO_LOG_LEVEL = "INFO"),
    quarto::quarto_render(
      input       = target_qmd,
      output_file = basename(target_html),
      execute_dir = output_dir,   # 依存パスの安定化
      quiet       = FALSE
    )
  ), silent = TRUE
)
if (!inherits(qres, "try-error") && file.exists(target_html)) {
  log("INFO", "✅ Quarto OK →", target_html)
  writeLines(c(log_lines, paste("RESULT: method_used = quarto"),
               paste("HTML   :", target_html)), log_path, useBytes = TRUE)
  quit(save="no")
} else {
  if (inherits(qres, "try-error")) log("WARN", "Quarto failed:", conditionMessage(attr(qres,"condition")))
  else log("WARN","Quarto finished but HTML not found")
}

## --------- 2) rmarkdown::render（.qmd のまま） ----------
log("INFO","Try: rmarkdown::render(.qmd)")
r1 <- try(
  rmarkdown::render(
    input          = target_qmd,           # .qmdを直接
    output_file    = basename(target_html),
    output_dir     = output_dir,
    knit_root_dir  = output_dir,           # 相対パスの安定化（画像等）
    output_options = list(self_contained = TRUE),
    envir          = new.env(),
    quiet          = FALSE
  ), silent = TRUE
)
if (!inherits(r1,"try-error") && file.exists(target_html)) {
  log("INFO","✅ rmarkdown OK →", target_html)
  writeLines(c(log_lines, paste("RESULT: method_used = rmarkdown::render"),
               paste("HTML   :", target_html)), log_path, useBytes = TRUE)
  quit(save="no")
} else {
  if (inherits(r1, "try-error")) log("WARN","rmarkdown failed:", conditionMessage(attr(r1,"condition")))
  else log("WARN","rmarkdown finished but HTML not found")
}

## --------- 3) knit → pandoc ----------
log("INFO","Try: knitr::knit(.qmd -> .md)")
k1 <- try({
  knitr::opts_chunk$set(fig.path = file.path("_figs/", stub, "_"), dev = "png", dpi = 150)
  knitr::opts_knit$set(root.dir = output_dir)
  with_dir(output_dir, {
    knitr::knit(input = target_qmd, output = pre_md, quiet = TRUE, envir = new.env())
  })
}, silent = TRUE)

if (!inherits(k1,"try-error") && file.exists(pre_md)) {
  log("INFO","Try: pandoc_convert(.md -> .html)")
  p1 <- try(
    rmarkdown::pandoc_convert(
      input   = pre_md,
      from    = "markdown+raw_html",
      to      = "html",
      output  = target_html,
      options = c("--standalone","--self-contained","--toc","--toc-depth=2",
                  "--metadata=pagetitle:Weekly Report",
                  "--metadata=header-includes:<style>.main-container{max-width:1200px}</style>")
    ), silent = TRUE
  )
  if (!inherits(p1,"try-error") && file.exists(target_html)) {
    log("INFO","✅ knit->pandoc OK →", target_html)
    writeLines(c(log_lines, paste("RESULT: method_used = knit->pandoc"),
                 paste("HTML   :", target_html)), log_path, useBytes = TRUE)
    quit(save="no")
  } else {
    if (inherits(p1, "try-error")) log("ERROR","pandoc_convert error:", conditionMessage(attr(p1,"condition")))
    else log("ERROR","pandoc_convert finished but HTML not found")
  }
} else {
  if (inherits(k1,"try-error")) log("ERROR","knit error:", conditionMessage(attr(k1,"condition")))
  else log("ERROR","knit finished but md not found")
}

## --------- 4) 最終: raw pandoc（コード未実行の可能性） ----------
log("INFO","Final: raw pandoc (.qmd -> .html, no code exec)")
p2 <- try(
  rmarkdown::pandoc_convert(
    input   = target_qmd,
    from    = "markdown+raw_html",
    to      = "html",
    output  = target_html,
    options = c("--standalone","--self-contained","--toc","--toc-depth=2",
                "--metadata=pagetitle: Weekly Report (pandoc only)")
  ), silent = TRUE
)
if (!inherits(p2,"try-error") && file.exists(target_html)) {
  log("INFO","⚠️ raw pandoc OK（コード未実行の可能性）→", target_html)
  writeLines(c(log_lines, paste("RESULT: method_used = raw pandoc"),
               paste("HTML   :", target_html)), log_path, useBytes = TRUE)
} else {
  log("ERROR","All methods failed.")
  flush_log()
  stop("All rendering methods failed. See log: ", log_path)
}
