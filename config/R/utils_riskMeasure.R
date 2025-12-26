
## B-2. Risk指標 ----
make_risk_metrics <- function(df) {
  # df: 日次 or 月次のトレード損益データ
  df <- dplyr::arrange(df, year_month_date)
  
  # 累積損益
  cum_gain <- cumsum(tidyr::replace_na(df$ttl_gain_realized_jpy, 0))
  
  # 最大ドローダウン
  running_max <- cummax(cum_gain)
  dd <- running_max - cum_gain
  max_dd <- max(dd, na.rm = TRUE)
  
  # ボラティリティ（標準偏差）
  vol <- sd(df$ttl_gain_realized_jpy, na.rm = TRUE)
  
  # シャープレシオ
  avg_ret <- mean(df$ttl_gain_realized_jpy, na.rm = TRUE)
  sharpe <- ifelse(vol > 0, avg_ret / vol, NA_real_)
  
  tibble::tibble(
    `Max Drawdown` = max_dd,
    `Volatility`   = vol,
    `Sharpe Ratio` = sharpe
  )
}

