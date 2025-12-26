
# 00_config/init.R
suppressPackageStartupMessages({library(fs)})

# 1) パス辞書 P（.Rproject、及び、各種データ読込元になりそうな箇所を記載） ----
root <- Sys.getenv("PROJECT_ROOT")
P <- list(
  root      = root,
  raw       = Sys.getenv("RAW_DIR",       file.path(root, "01_data")),
  output    = Sys.getenv("OUTPUT_DIR",    file.path(root, "04_output")),
  site      = Sys.getenv("SITE_DIR",      file.path(root, "05_site"))
)

# 2) utils の所在 ----
utils_dir_abs <- "C:/Users/alpac/Dropbox/03_individual_work/05_stockTrading/00_config/01_library/R"
# プロジェクト相対位置（場所を動かしても動くように）
utils_dir_rel <- file.path(P$root, "00_config", "01_library", "R")
utils_dir <- if (dir_exists(utils_dir_abs)) utils_dir_abs else utils_dir_rel

if (!dir_exists(utils_dir)) {
  warning("utils フォルダが見つかりません: ", utils_dir)
} else {
  # 3) 先にパッケージローダ（任意） ----
  pkg_loader <- file.path(utils_dir, "utils_packages.R")
  if (file_exists(pkg_loader)) {
    sys.source(pkg_loader, envir = .GlobalEnv)
    if (exists("attach_packages", mode = "function")) {
      try(attach_packages(), silent = TRUE)
    }
    }

  # 4) 残りの utils/*.R を読み込み ----
  files <- dir_ls(utils_dir, type = "file", glob = "*.R")
  
  # packages ローダは除外（すでに読み込み済み）
  files <- files[basename(files) != "utils_packages.R"]
  
  # 拡張子が .R でないファイルがあれば無視されます（例: utils_timeSeries ← .R を付けて下さい）
  for (f in sort(files)) sys.source(f, envir = .GlobalEnv)
  }

# --- 5) 必要なら軽い既定（任意） ------------------------------------------
# fs::dir_create(P$raw, P$processed, P$output, P$site, recurse = TRUE)
# options(stringsAsFactors = FALSE)


# End) Loading Confirmation ----
message("[No.2 init.R loaded]")



