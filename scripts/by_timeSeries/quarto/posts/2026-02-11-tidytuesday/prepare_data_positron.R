# prepare_data_positron.R
# Positron (R) 用: prepare_data.py と同じ指標を計算し CSV で保存
# R の arrow パッケージで parquet を読み取る (Python ARM64 では pyarrow 不可のため)

library(arrow)
library(dplyr)
library(tidyr)

# --- パス設定 ---
# プロジェクトルートを探す
find_base <- function() {
  # .Rprofile で cwd が設定されている前提
  candidates <- c(
    getwd(),
    Sys.getenv("STOCK_TRADING_ROOT", unset = NA)
  )
  for (p in candidates) {
    if (!is.na(p) && dir.exists(file.path(p, "data", "trading_account"))) {
      return(p)
    }
  }
  # フォールバック: スクリプト位置から上に辿る
  if (
    requireNamespace("rstudioapi", quietly = TRUE) &&
      rstudioapi::isAvailable()
  ) {
    script_dir <- dirname(rstudioapi::getSourceEditorContext()$path)
  } else {
    script_dir <- "."
  }
  d <- normalizePath(script_dir, winslash = "/")
  while (basename(d) != "05_stockTrading" && dirname(d) != d) {
    d <- dirname(d)
  }
  d
}

base_path <- find_base()

pl_path <- file.path(
  base_path,
  "data",
  "trading_account",
  "realized_pl",
  "silver",
  "realized_pl.parquet"
)
balance_path <- file.path(
  base_path,
  "data",
  "trading_account",
  "account_balance",
  "daily_balance.parquet"
)

# 出力先: スクリプトと同じディレクトリの data/
script_dir <- if (
  requireNamespace("rstudioapi", quietly = TRUE) &&
    rstudioapi::isAvailable()
) {
  dirname(rstudioapi::getSourceEditorContext()$path)
} else {
  file.path(
    base_path,
    "scripts",
    "by_timeSeries",
    "quarto",
    "posts",
    "2026-02-11-tidytuesday"
  )
}
output_dir <- file.path(script_dir, "data")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# --- 計算 ---
metrics <- list()
daily_pl <- NULL

if (file.exists(pl_path)) {
  df <- read_parquet(pl_path)
  df$settlement_date <- as.Date(df$settlement_date)

  # 日次集計
  daily_pl <- df |>
    group_by(date = settlement_date) |>
    summarise(
      profit_jpy = sum(profit_jpy, na.rm = TRUE),
      n_trades = n(),
      .groups = "drop"
    )

  wins <- daily_pl |> filter(profit_jpy > 0)
  losses <- daily_pl |> filter(profit_jpy < 0)
  n_days <- nrow(daily_pl)
  n_win_days <- nrow(wins)

  win_rate <- if (n_days > 0) n_win_days / n_days * 100 else 0
  avg_profit_jpy <- if (nrow(wins) > 0) mean(wins$profit_jpy) else 0
  avg_loss_jpy <- if (nrow(losses) > 0) mean(losses$profit_jpy) else 0

  r_multiple <- if (avg_loss_jpy != 0) {
    avg_profit_jpy / abs(avg_loss_jpy)
  } else {
    if (avg_profit_jpy > 0) 1.0 else 0.5
  }

  # 最大連敗日数
  daily_pl_tmp <- daily_pl |>
    arrange(date) |>
    mutate(
      is_loss = profit_jpy < 0,
      streak_id = cumsum(!is_loss)
    )
  losing_streaks <- daily_pl_tmp |>
    filter(is_loss) |>
    count(streak_id)
  max_consecutive <- if (nrow(losing_streaks) > 0) max(losing_streaks$n) else 0L

  metrics$win_rate_pct <- round(win_rate, 2)
  metrics$r_multiple <- round(r_multiple, 3)
  metrics$avg_profit_jpy <- round(avg_profit_jpy, 0)
  metrics$avg_loss_jpy <- round(avg_loss_jpy, 0)
  metrics$n_trades_total <- nrow(df)
  metrics$n_days_traded <- as.integer(n_days)
  metrics$max_consecutive_losing_days <- as.integer(max_consecutive)
} else {
  metrics$win_rate_pct <- 55.0
  metrics$r_multiple <- 1.5
  metrics$avg_profit_jpy <- 0
  metrics$avg_loss_jpy <- 0
  metrics$n_trades_total <- 0L
  metrics$n_days_traded <- 0L
  metrics$max_consecutive_losing_days <- 0L
}

if (file.exists(balance_path)) {
  balance <- read_parquet(balance_path)
  balance$date <- as.Date(balance$date)

  equity <- balance |>
    group_by(date) |>
    summarise(pat_balance = sum(pat_balance, na.rm = TRUE), .groups = "drop") |>
    arrange(date) |>
    mutate(
      cummax = cummax(pat_balance),
      drawdown_pct = ifelse(
        cummax > 0,
        pmin((cummax - pat_balance) / cummax * 100, 100),
        0
      )
    )

  metrics$max_drawdown_pct <- round(min(max(equity$drawdown_pct), 100), 2)
  metrics$account_size_jpy <- round(tail(equity$pat_balance, 1), 0)
} else {
  metrics$max_drawdown_pct <- 0
  metrics$account_size_jpy <- 0
}

metrics$position_size_pct <- 2.0

# --- 保存 ---
risk_df <- as.data.frame(metrics)
write.csv(risk_df, file.path(output_dir, "risk_metrics.csv"), row.names = FALSE)
cat("Saved:", file.path(output_dir, "risk_metrics.csv"), "\n")

if (!is.null(daily_pl)) {
  write.csv(daily_pl, file.path(output_dir, "daily_pl.csv"), row.names = FALSE)
  cat("Saved:", file.path(output_dir, "daily_pl.csv"), "\n")
}

cat("\n--- Risk Metrics ---\n")
print(t(risk_df))
