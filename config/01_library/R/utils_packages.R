# 11_lib/R/utils_packages.R
# 目的：必要パッケージを attach し、最後に conflicted の優先関数を宣言するだけ
# 依存の導入は renv::restore() で事前に行う（実行時に install はしない）

attach_packages <- function() {
  # 1) パッケージ一覧（用途ごとに並べる）
  pkgs <- c(
    # 基本セット
    "tidyverse",      # dplyr / ggplot2 / readr / purrr / tidyr / tibble / stringr / forcats
    "lubridate",      # 日付操作
    "scales",         # 表示の整形（通貨, % など）
    
    # データ取得・整形
    "bizdays",        # 取引所カレンダー
    "readxl",         # Excel 読み込み
    "janitor",        # 列名の掃除、tabyl 等
    # "timeDate",     # 必要なときだけ有効化（S4依存が重いことがある）
    
    # 可視化
    "patchwork",      # プロットの組み合わせ
    "ggtext",         # リッチテキスト
    "gridtext",       # テキストボックス
    "gt",             # 表
    "showtext",       # 日本語フォント（自動有効化は _setup.R で）
    
    # 衝突検出
    "conflicted"
  )
  
  # 2) attach（未インストールなら停止して案内）
  for (p in pkgs) {
    ok <- suppressPackageStartupMessages(
      require(p, character.only = TRUE, quietly = TRUE)
    )
    if (!ok) {
      stop(
        "Package not installed: ", p,
        "\n→ 事前に renv::restore() もしくは install.packages('", p, "') を実行してください。"
      )
    }
  }
  
  # 3) 衝突ポリシー（attach 後に必ず設定）
  conflicted::conflicts_prefer(
    dplyr::filter,
    dplyr::lag,
    dplyr::select,
    dplyr::arrange
  )
  
  message("Packages attached: ", paste(pkgs, collapse = ", "))
}

# ----（開発用オプション：必要なら一時的に使う）----------------------------
# 開発マシンでだけ自動インストールしたい場合は、上の attach の前に下を一時的に有効化
# missing <- setdiff(pkgs, rownames(utils::installed.packages()))
# if (length(missing)) utils::install.packages(missing)
