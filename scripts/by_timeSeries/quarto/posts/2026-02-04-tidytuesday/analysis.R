# =============================================================================
# TidyTuesday: S&P 500 Sector Performance
# Ad-hoc Analysis Script for Positron
# =============================================================================
# データソース: prepare_data.py で作成済みの data/sector_performance.parquet を参照
# Positron で自由に分析・修正してください。
# =============================================================================

# --- パッケージ読み込み -------------------------------------------------------
library(tidyverse)
library(arrow)
library(scales)
library(glue)

# --- データ読み込み -----------------------------------------------------------
# prepare_data.py で作成済みの parquet を参照
# Positron でプロジェクトルートから実行してもエラーにならないよう、複数のパスを試行

# オプション1: スクリプトと同じディレクトリから実行する場合（相対パス）
data_file <- "data/sector_performance.parquet"

# オプション2: プロジェクトルートから実行する場合（絶対パス）
if (!file.exists(data_file)) {
  data_file <- "scripts/by_timeSeries/quarto/posts/2026-02-04-tidytuesday/data/sector_performance.parquet"
}

# どちらのパスでも見つからない場合、詳細なエラーメッセージを表示
if (!file.exists(data_file)) {
  cat("\n=== エラー: データファイルが見つかりません ===\n")
  cat("現在の作業ディレクトリ:", getwd(), "\n\n")
  cat("Positron で実行する場合、以下のいずれかを試してください:\n")
  cat("1. ターミナルで作業ディレクトリを変更:\n")
  cat(
    "   setwd('scripts/by_timeSeries/quarto/posts/2026-02-04-tidytuesday')\n\n"
  )
  cat("2. または prepare_data.py を実行してデータを作成:\n")
  cat("   python prepare_data.py\n\n")
  stop("処理を中断しました。")
}

sector_data <- read_parquet(data_file)
cat("Data loaded successfully!\n")
cat(glue("Records: {nrow(sector_data)}\n"))
cat(glue("Data date: {unique(sector_data$data_date)}\n"))

# --- データ確認 ---------------------------------------------------------------
glimpse(sector_data)
head(sector_data)

# --- データ加工 ---------------------------------------------------------------
# Convert to long format for ggplot
sector_long <- sector_data |>
  select(sector, daily_return, ytd_return, sort_order) |>
  pivot_longer(
    cols = c(daily_return, ytd_return),
    names_to = "metric",
    values_to = "value"
  ) |>
  mutate(
    metric = factor(
      metric,
      levels = c("daily_return", "ytd_return"),
      labels = c("Daily", "Year-to-date")
    ),
    sector = factor(
      sector,
      levels = sector_data$sector[order(sector_data$sort_order)]
    )
  )

# Get data date for title
data_date <- unique(sector_data$data_date)
data_date_formatted <- format(as.Date(data_date), "%m/%d/%Y")

glimpse(sector_long)

# --- メインチャート: グループ化棒グラフ ---------------------------------------
colors <- c("Daily" = "#1e5aa8", "Year-to-date" = "#d4a012")

p <- ggplot(sector_long, aes(x = sector, y = value, fill = metric)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  geom_hline(yintercept = 0, color = "black", linewidth = 0.5) +
  geom_text(
    aes(
      label = sprintf("%.1f%%", value),
      vjust = ifelse(value >= 0, -0.5, 1.5),
      color = metric
    ),
    position = position_dodge(width = 0.7),
    size = 3,
    show.legend = FALSE
  ) +
  scale_fill_manual(values = colors) +
  scale_color_manual(values = colors) +
  scale_y_continuous(
    labels = label_percent(scale = 1, accuracy = 1),
    expand = expansion(mult = c(0.15, 0.15))
  ) +
  labs(
    title = glue("S&P 500 sector performance"),
    subtitle = glue("Date: {data_date_formatted} | Year-to-date"),
    x = NULL,
    y = NULL,
    fill = NULL
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 16, hjust = 0),
    plot.subtitle = element_text(size = 12, color = "gray40", hjust = 0),
    axis.text.x = element_text(size = 10, angle = 0, hjust = 0.5),
    axis.text.y = element_text(size = 10),
    legend.position = "top",
    legend.justification = "left",
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    plot.margin = margin(20, 20, 20, 20)
  )

print(p)

# チャート保存（必要に応じて）
# ggsave("chart-1.png", plot = p, width = 14, height = 7, dpi = 150, bg = "white")

# --- データテーブル -----------------------------------------------------------
sector_data |>
  select(
    Sector = sector,
    `Daily Return` = daily_return,
    `YTD Return` = ytd_return
  ) |>
  mutate(
    `Daily Return` = sprintf("%+.2f%%", `Daily Return`),
    `YTD Return` = sprintf("%+.2f%%", `YTD Return`)
  )

# --- 代替ビュー: ロリポップチャート -------------------------------------------
ytd_data <- sector_data |>
  mutate(
    sector = factor(sector, levels = sector[order(ytd_return)]),
    color = ifelse(ytd_return >= 0, "#22c55e", "#ef4444")
  )

p_lollipop <- ggplot(ytd_data, aes(x = sector, y = ytd_return)) +
  geom_segment(
    aes(x = sector, xend = sector, y = 0, yend = ytd_return, color = color),
    linewidth = 1.5,
    show.legend = FALSE
  ) +
  geom_point(aes(color = color), size = 4, show.legend = FALSE) +
  geom_hline(yintercept = 0, color = "gray50", linewidth = 0.5) +
  geom_text(
    aes(label = sprintf("%+.1f%%", ytd_return)),
    hjust = ifelse(ytd_data$ytd_return >= 0, -0.3, 1.3),
    size = 3.5
  ) +
  scale_color_identity() +
  scale_y_continuous(
    labels = label_percent(scale = 1, accuracy = 1),
    expand = expansion(mult = c(0.1, 0.1))
  ) +
  coord_flip() +
  labs(
    title = "S&P 500 Sector YTD Performance",
    subtitle = glue("As of {data_date_formatted}"),
    x = NULL,
    y = "Year-to-Date Return (%)"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 16),
    plot.subtitle = element_text(color = "gray40"),
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank()
  )

print(p_lollipop)

# =============================================================================
# 以下、自由に分析を追加してください
# =============================================================================

# 例: セクター別サマリー
# sector_data |>
#   summarise(
#     avg_daily = mean(daily_return),
#     avg_ytd = mean(ytd_return),
#     best_daily = sector[which.max(daily_return)],
#     best_ytd = sector[which.max(ytd_return)]
#   )
