# 共通初期化
# A) "init.R"の読み込み ----
if (file.exists("00_config/init.R")) {
  source("00_config/init.R", local = TRUE)
}

# # B) "init_local.R"の読み込み ----
# # マシン固有初期化（git管理外）
# if (file.exists("00_config/init_local.R")) {
#   source("00_config/init_local.R", local = TRUE)
# }

message("[No.1 Rprofile loaded] cwd=", getwd())

# debugの確認
# list.files("00_config", all.files = TRUE)
# file.exists("00_config/init.R")
# file.exists("00_config/init_local.R")

# Z) Reference ----
## https://stevenponce.netlify.app/data_visualizations.html
## Z-1. metaデータ管理
# title:
# subtitle:
# description:
# author:
# date:
# categories:
# tags:

## Z-2. link作成ヘルパー
# create_link <- function(text, url) {
#   paste0("[", text, "](", url, ")")
# }

## Z-3. link作成ヘルパー
# setup_fonts()
# base_theme <- create_base_theme(colors)
# weekly_theme <- extend_weekly_theme(base_theme, theme(...))

## Z-4. Custom scale
# format_euro <- function(x) {
#   paste0("€", scales::comma(x, accuracy = 1))
# }

## Z-5. 補助関数
# get_theme_colors()
# save_plot_patchwork()
# create_mm_caption()

## Z-6. ファイル単位のモジュール化
# utils/fonts.R
# utils/social_icons.R
# themes/base_theme.R

## Z-7. revv_仮想空間 ----
# プロジェクト毎でlibraryなども分けたい場合、堅牢にしたい場合にはこちら。
# install.packages("renv")  # 初回だけ
# renv::init()              # プロジェクトを renv 化（以後このプロジェクト専用ライブラリを使用）
# パッケージを入れ替えたら…
# renv::snapshot()          # 現在の状態をロックファイルに保存
# 別PCでは…
# renv::restore()           # ロックに従って同じ環境を復元








