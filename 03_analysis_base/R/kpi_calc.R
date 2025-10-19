# kpi_calc_ytd_monthly_simple.R
library(dplyr)
library(tidyr)
library(scales)

# ===== データ読み込み =====
load_latest_checkpoint <- function(name, stage, root = Sys.getenv("PROJECT_ROOT")) {
  dir_path <- file.path(root, "03_data_checkpoint", stage)
  files <- list.files(
    dir_path,
    pattern = paste0("^", name, "_\\d{8}\\.rds$"),
    full.names = TRUE
  )
  if (length(files) == 0) stop("No checkpoint found for: ", stage, "/", name)
  latest <- files[which.max(file.mtime(files))]
  message("Loaded checkpoint: ", latest)
  readRDS(latest)
}

ts_monthly_d <- load_latest_checkpoint("ts_monthly_d", "ts_monthly_d")

# ts_monthly_d %>% glimpse() %>% View()

# ===== 計測期間 =====
start_date <- as.Date("2025-01-01")
end_date   <- Sys.Date()

kpi_df <- ts_monthly_d %>%
  filter(year_month_date >= start_date,
         year_month_date <= end_date)

# ===== KPI計算関数 =====
calc_metrics <- function(df) {
  total_trades     <- sum(df$num_of_trades, na.rm = TRUE)
  total_win_trades <- sum(df$num_of_win_trades, na.rm = TRUE)
  total_net_pl     <- sum(df$ttl_gain_realized_jpy, na.rm = TRUE) # 純損益
  total_gain       <- sum(df$ttl_gain_realized_jpy[df$ttl_gain_realized_jpy > 0], na.rm = TRUE) # 利益のみ
  total_loss       <- abs(sum(df$ttl_gain_realized_jpy[df$ttl_gain_realized_jpy < 0], na.rm = TRUE)) # 損失のみ
  total_investment <- sum(df$ttl_cost_acquisition_jpy, na.rm = TRUE)
  
  win_rate <- ifelse(total_trades > 0, total_win_trades / total_trades, NA_real_)
  avg_capital_invested <- ifelse(total_trades > 0, total_investment / total_trades, NA_real_)
  avg_gain <- ifelse(total_win_trades > 0,
                     sum(replace_na(df$ttl_gain_realized_jpy[df$ttl_gain_realized_jpy > 0], 0)) / total_win_trades,
                     NA_real_)
  avg_loss <- ifelse((total_trades - total_win_trades) > 0,
                     abs(sum(replace_na(df$ttl_gain_realized_jpy[df$ttl_gain_realized_jpy < 0], 0))) /
                       (total_trades - total_win_trades),
                     NA_real_)
  risk_reward <- ifelse(!is.na(avg_loss) & avg_loss > 0, avg_gain / avg_loss, NA_real_)
  ROI <- ifelse(total_investment > 0, total_net_pl / total_investment, NA_real_)
  mean_profit_rate <- ifelse(!is.na(avg_gain) & avg_capital_invested > 0, avg_gain / avg_capital_invested, NA_real_)
  mean_loss_rate   <- ifelse(!is.na(avg_loss) & avg_capital_invested > 0, avg_loss / avg_capital_invested, NA_real_)
  expectancy <- ifelse(!is.na(win_rate) & !is.na(mean_profit_rate) & !is.na(mean_loss_rate),
                       win_rate * mean_profit_rate - (1 - win_rate) * mean_loss_rate,
                       NA_real_)
  
  tibble(
    `Expectancy (E)`            = expectancy,
    `Win Rate (WR)`             = win_rate,
    `Mean Profit Rate (G)`      = mean_profit_rate,
    `Mean Loss Rate (L)`        = mean_loss_rate,
    `Avg Gain per Trade (JPY)`  = avg_gain,
    `Avg Loss per Trade (JPY)`  = avg_loss,
    `Avg Capital Invested per trade (JPY)` = avg_capital_invested,
    `Risk/Reward Ratio (RRR)`   = risk_reward, # 勝ちの平均/負けの平均
    `ROI`                       = ROI,
    `Total Trades`              = total_trades,
    `Total Win Trades`          = total_win_trades,
    `Total Net P/L (JPY)`       = total_net_pl,
    `Total Gain (JPY)`          = total_gain,
    `Total Loss (JPY)`          = total_loss,     # ★ ここを追加
    `Total Investment (JPY)`    = total_investment
  )
}


# ===== YTD集計 =====
trade_days <- sum(kpi_df$actual_trade_days, na.rm = TRUE)  #★ YTDは実取引日数の合計を使う
market_days <- sum(kpi_df$market_open_days,  na.rm = TRUE)  #★ 市場営業日数を追加

# This part of the code is creating a data frame `ytd_raw` by combining three different sources of data:
ytd_raw <- bind_rows(
  tibble(Metric = as.character("Trade_Days"), YTD = as.numeric(trade_days)),
  tibble(Metric = as.character("Market_Open_Days"), YTD = as.numeric(market_days)),   #★ 追加
  calc_metrics(kpi_df) %>%
    # Pivot all columns to long format; update 'everything()' if calc_metrics output columns change
    pivot_longer(cols = everything(), names_to = "Metric", values_to = "YTD")
    mutate(Metric = as.character(Metric), YTD = as.numeric(YTD))
)

# # ===== YTD集計 =====
# ytd_raw <- calc_metrics(kpi_df) %>%>
#   pivot_longer(cols = everything(), names_to = "Metric", values_to = "YTD")

# ===== 月次集計 =====
monthly_raw <- kpi_df %>%
  group_by(year_month = format(year_month_date, "%b-%Y")) %>%
  group_modify(~ {
    metrics <- calc_metrics(.x) %>%
      pivot_longer(cols = everything(), names_to = "Metric", values_to = "val")
    #★ actual_trade_days カラムをそのまま利用
    days_in_period <- sum(.x$actual_trade_days, na.rm = TRUE)
    market_days_m <- sum(.x$market_open_days,   na.rm = TRUE)  #★ 追加
    bind_rows(
      tibble(Metric = "Trade_Days", val = days_in_period),
      tibble(Metric = "Market_Open_Days",  val = market_days_m),  #★ 追加
      metrics
    )
  }) %>%
  pivot_wider(names_from = year_month, values_from = val)

# ===== 結合 =====
kpi_raw <- ytd_raw %>% left_join(monthly_raw, by = "Metric")

# ===== 値のフォーマット関数（シンプル版） =====
format_value <- function(metric, x){
  if (metric %in% c("Expectancy (E)", "Win Rate (WR)", "Mean Profit Rate (G)", "Mean Loss Rate (L)", "ROI")) {
    percent(x, accuracy = 0.01)
  } else if (metric %in% c("Avg Gain per Trade (JPY)", "Avg Loss per Trade (JPY)",
                           "Avg Capital Invested per trade (JPY)", "Total Gain (JPY)", "Total Loss (JPY)", "Total Investment (JPY)", "Total Net P/L (JPY)")) {
    comma(x, accuracy = 1)
  } else if (metric == "Risk/Reward Ratio (RRR)") {
    ifelse(!is.na(x), round(x, 2), NA)
  } else {
    x
  }
}

# ===== 月列を1月→最新月の昇順に並べ替え =====
month_cols <- setdiff(names(kpi_raw), c("Metric", "YTD"))
month_cols <- month_cols[order(as.Date(paste0("01-", month_cols), format = "%d-%b-%Y"))]

# ===== 数値を整形 =====
kpi_results <- kpi_raw %>%
  mutate(
    YTD = mapply(format_value, Metric, YTD),
    across(all_of(month_cols), ~ mapply(format_value, Metric, .x))
  ) %>%
  rename(`YTD in 2025` = YTD) %>%
  select(Metric, `YTD in 2025`, all_of(month_cols))

# ===== Period & Reference追加 =====
kpi_results <- bind_rows(
  tibble(Metric = "Period",
         `YTD in 2025` = paste0(format(start_date, "%Y-%m-%d"), " 〜 ", format(end_date, "%Y-%m-%d"))),
  kpi_results,
  tibble(Metric = "Reference",
         `YTD in 2025` = "E = WR × Mean Profit Rate − (1 − WR) × Mean Loss Rate")
)

kpi_results
# kpi_results %>% glimpse() %>% view()


library(gt)

# kpi_resultsをgtテーブルに変換
kpi_results %>%
  gt() %>%
  tab_header(
    title = md("**KPI YTD & Monthly Summary**"),
    subtitle = paste0(format(start_date, "%Y-%m-%d"), " 〜 ", format(end_date, "%Y-%m-%d"))
  ) %>%
  fmt_number(
    columns = where(is.numeric),
    decimals = 2
  ) %>%
  tab_options(
    table.font.size = px(12),
    heading.align = "left",
    table.width = pct(100)
  )

library(flextable)
kpi_results %>%
  flextable() %>%
  autofit() %>%
  bold(part = "header") %>%
  theme_vanilla()


# tinytableで作成 -----
# # ちょっと時間かかる。最新版になったら試すでよい。
# library(dplyr)
# library(tinytable)
# テーブル作成
# ===== tinytable 0.14.0 対応版 =====
# # tinytable出力
# kpi_tt <- kpi_results %>%
#   tt() %>%
#   style_tt(
#     caption = "**KPI YTD & Monthly Summary**",
#     position = "center",
#     theme = "striped",
#     line_color = "grey80",
#     line_width = 0.3,
#     fontsize = 10,
#     padding = 1.5
#   )
# 
# # ===== HTML出力 (CSS付き) =====
# html_out <- paste0(
#   "<style>
#      body { zoom: 0.3; }             /* 全体を縮小（0.3 = 30%） */
#      table { font-size: 10pt; width: 80%; margin: auto; }
#      th, td { padding: 4px; text-align: left; }
#      h3 { text-align: left; font-size: 14pt; font-weight: bold; }
#      p.notes { text-align: left; font-size: 9pt; color: #666; }
#    </style>",
#   "<h3>KPI YTD & Monthly Summary</h3>",
#   print(kpi_tt, output = "html"),
#   sprintf("<p class='notes'>集計期間: %s ～ %s</p>",
#           format(start_date, "%Y-%m-%d"), format(end_date, "%Y-%m-%d"))
# )
# 
# # 保存してブラウザで開く
# writeLines(html_out, "kpi_summary.html")
# browseURL("kpi_summary.html")


# packageVersion("tinytable")

# shinyで表示 ====
library(shiny)
library(DT)

ui <- fluidPage(
  h2("KPI YTD & Monthly Summary"),
  DTOutput("kpi_table")
)

server <- function(input, output, session) {
  output$kpi_table <- renderDT({
    datatable(kpi_results,
              options = list(pageLength = 20, scrollX = TRUE),
              caption = htmltools::tags$caption(
                style = 'caption-side: top; text-align: left;',
                paste0("集計期間: ", format(start_date, "%Y-%m-%d"), " ～ ", format(end_date, "%Y-%m-%d"))
              ))
  })
}

shinyApp(ui, server)


library(shiny)
library(reactable)

ui <- fluidPage(
  h2("KPI YTD & Monthly Summary"),
  reactableOutput("kpi_table")
)

server <- function(input, output, session) {
  output$kpi_table <- renderReactable({
    reactable(kpi_results,
              searchable = TRUE,
              pagination = TRUE,
              defaultPageSize = 20,
              highlight = TRUE,
              bordered = TRUE,
              striped = TRUE)
  })
}

shinyApp(ui, server)

