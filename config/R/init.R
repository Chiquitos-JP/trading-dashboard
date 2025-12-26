
# config/R/init.R
suppressPackageStartupMessages({library(fs)})

# 1) パス辞書 P（.Rproject、及び、各種データ読込元になりそうな箇所を記載） ----
root <- Sys.getenv("PROJECT_ROOT")
P <- list(
  root      = root,
  raw       = Sys.getenv("RAW_DIR",       file.path(root, "data")),
  output    = Sys.getenv("OUTPUT_DIR",    file.path(root, "outputs", "figures")),
  site      = Sys.getenv("SITE_DIR",      file.path(root, "docs"))
)

# 2) utils の所在 ----
# プロジェクト相対位置を優先（場所を動かしても動くように）
utils_dir_rel <- file.path(P$root, "config", "R")
# 旧パス（config/init.R）との互換性のため
utils_dir_old <- file.path(P$root, "config", "init.R")
# 旧パス（01_library）との互換性のため
utils_dir_old2 <- file.path(P$root, "config", "01_library", "R")
# 旧パス（00_config）との互換性のため
utils_dir_old3 <- file.path(P$root, "00_config", "01_library", "R")
# 絶対パス（フォールバック、環境変数から取得可能）
utils_dir_abs <- Sys.getenv("UTILS_DIR_ABS", "")
utils_dir <- if (dir_exists(utils_dir_rel)) {
  utils_dir_rel
} else if (dir_exists(utils_dir_old)) {
  utils_dir_old
} else if (dir_exists(utils_dir_old2)) {
  utils_dir_old2
} else if (dir_exists(utils_dir_old3)) {
  utils_dir_old3
} else if (nzchar(utils_dir_abs) && dir_exists(utils_dir_abs)) {
  utils_dir_abs
} else {
  utils_dir_rel  # デフォルトは相対パス
}

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
  
  # packages ローダと init.R は除外（すでに読み込み済み）
  files <- files[basename(files) != "utils_packages.R"]
  files <- files[basename(files) != "init.R"]
  
  # 拡張子が .R でないファイルがあれば無視されます（例: utils_timeSeries ← .R を付けて下さい）
  for (f in sort(files)) sys.source(f, envir = .GlobalEnv)
  }

# --- 5) 必要なら軽い既定（任意） ------------------------------------------
# fs::dir_create(P$raw, P$processed, P$output, P$site, recurse = TRUE)
# options(stringsAsFactors = FALSE)


# End) Loading Confirmation ----
message("[No.2 init.R loaded]")




