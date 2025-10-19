# メインスクリプト方針 ----
# メインに“意図”が残る（どの段階で何を足しているかが読める）
# 重い/煩雑な処理は helper 内に隔離（保守しやすい）

# A) Loading_data ----
## A-1. Loading_local_file ----
# フォルダパスの指定
folder_path <- "C:/Users/alpac/Dropbox/03_individual_work/05_stockTrading/01_data/raw/"
# CSVファイルの一覧を取得
csv_files <- list.files(path = folder_path, pattern = "\\.csv$", full.names = TRUE)

# ファイル名から日付を抽出（_YYYYMMDD の形式に一致）
file_dates <- str_extract(basename(csv_files), "_\\d{8}") %>%
  str_remove("_") %>%
  as.Date(format = "%Y%m%d")

# 最新日付のファイルを特定
latest_file <- csv_files[which.max(file_dates)]

# 読み込み
# merged_csv_data <- read_csv(latest_file)
merged_csv_data <- vroom::vroom(latest_file)

# ファイル名を記録したい場合（オプション）
merged_csv_data <- merged_csv_data %>%
  mutate(source_file = basename(latest_file)) %>% 
  clean_names()

# merged_csv_data %>% glimpse() %>% view()

# B) Wrangling ----
## B-1. 年月の列を作成・追加 ----
merged_csv_data <- merged_csv_data %>%
  dplyr::mutate(
    year_month        = stringr::str_trim(year_month),                     # 人間向け表記を保持（例: "Jan-24"）
    year_month_date   = lubridate::parse_date_time(
      year_month, orders = c("b-y","b-Y","Y-m"), quiet = TRUE
    ) %>% lubridate::floor_date("month") %>% as.Date(),
    year_month_iso    = format(year_month_date, "%Y-%m")                   # ← 内部処理用ISOキー
  )

# colnames(merged_csv_data)  # 列名の確認
# merged_csv_data %>% glimpse()  # データ構造の確認

# *data_checkpoint_1 ----
# 保存したいデータフレーム名、サブフォルダ名、.rds形式の保存名
# ▼目的：
#   ・元の生データ（CSVを読み込んだ直後）の状態を保存
#   ・ファイル名や整形処理を加えた“最初のクリーンな状態”を再利用できるように
# ▼活用方法：
#   ・異なる集計・分析に分岐する際の起点としてロード可能
#   ・不具合が出た時に「読み込み直後」に戻って検証できる
save_checkpoint(merged_csv_data, "raw_import", "merged_csv_data")

## B-2. 時系列の設定 ----
# 1) year_month 一覧 → NYSEの営業日数テーブルを作成（列名を _cal に）
# nyse_open_days: で定義
ym_tbl <- merged_csv_data %>% dplyr::distinct(year_month_iso, year_month)
# market_days_tbl <- ym_tbl %>%
#   dplyr::transmute( # trasmuteはmutateの仲間。ただし残したい列以外は除外する。
#     year_month,
#     market_open_days_cal = purrr::map_int(year_month, nyse_open_days)
#   )

market_days_tbl <- ym_tbl %>%
  dplyr::transmute(
    year_month_iso,
    market_open_days_cal = nyse_open_days_vec(year_month_iso)
  )

# 2) 結合 → 計算値優先で一本化 → 片付け
merged_with_mdays <- merged_csv_data %>%
  dplyr::left_join(market_days_tbl, by = "year_month_iso") %>%
  dplyr::mutate(market_open_days = dplyr::coalesce(market_open_days_cal, market_open_days)) %>%
  dplyr::select(-market_open_days_cal)

merged_with_mdays %>% glimpse()

# *data_checkpoint_2 ----
# ▼目的：
#   ・NYSE営業日数などを結合し、時系列解析に使える形にしたデータを保存
#   ・「取引明細」→「マーケットカレンダー付きデータ」という
#     1段進んだ状態を再利用可能にする
# ▼活用方法：
#   ・将来、営業日数や休日補正など別のロジックを試すときに
#     この段階からやり直せば良い
save_checkpoint(merged_with_mdays, "merged", "merged_with_mdays")

# 2) 月次で9列を再計算（brokerは無視）
ts_monthly <- merged_with_mdays %>%
  group_by(year_month_iso) %>%
  summarise(
    # 合計
    ttl_gain_realized_jpy = sum(ttl_gain_realized_jpy, na.rm = TRUE),
    
    # 勝ち件数（アカウント別win_rate×件数の合計）
    # ※整数にしたければ round() を付ける：round(sum(win_rate * num_of_trades, na.rm = TRUE))
    num_of_win_trades = round(sum(win_rate * num_of_trades, na.rm = TRUE)),
    
    # 総取引件数
    num_of_trades = sum(num_of_trades, na.rm = TRUE),
    
    # 月全体の勝率＝勝ち件数 / 総取引件数
    win_rate = ifelse(num_of_trades > 0,
                      num_of_win_trades / num_of_trades, NA_real_),
    
    # 実現損益/取引（再計算）
    avg_gain_realized_per_trade_jpy = ifelse(num_of_trades > 0,
                                             ttl_gain_realized_jpy / num_of_trades, NA_real_),
    
    # リターン率を再計算
    ttl_amt_settlement_jpy   = sum(ttl_amt_settlement_jpy, na.rm = TRUE),
    ttl_cost_acquisition_jpy = sum(ttl_cost_acquisition_jpy, na.rm = TRUE),
    return_on_cost  = ifelse(ttl_cost_acquisition_jpy > 0,
                             ttl_gain_realized_jpy / ttl_cost_acquisition_jpy, NA_real_),
    return_on_sales = ifelse(ttl_amt_settlement_jpy > 0,
                             ttl_gain_realized_jpy / ttl_amt_settlement_jpy, NA_real_),
    
    # actual trade days は月内の最大
    actual_trade_days = if (all(is.na(actual_trade_days))) NA_real_
    else max(actual_trade_days, na.rm = TRUE),
    
    # market open days（同月は同値）
    market_open_days = dplyr::first(market_open_days),
    
    # 1日あたり
    avg_gain_per_day_jpy = ifelse(actual_trade_days > 0,
                                  ttl_gain_realized_jpy / actual_trade_days, NA_real_),
    avg_num_of_trades_per_day = ifelse(actual_trade_days > 0,
                                       num_of_trades / actual_trade_days, NA_real_),
    
    .groups = "drop"
  ) %>%
  # 表示用に人間向けラベルも保持（その月の先頭の表記を採用）
  dplyr::left_join(ym_tbl, by = "year_month_iso") %>%
  # 集計した後に見たいテーブルに整形する
  select(
    year_month_iso,                # ISOキー（内部処理）
    year_month,                    # 人間向けラベル（例: "Jan-24"）
    ttl_cost_acquisition_jpy,      # 取得コスト
    ttl_gain_realized_jpy,         # 実現損益（JPY）
    num_of_win_trades,             # ← 追加
    win_rate,                      # 勝率
    avg_gain_realized_per_trade_jpy, # 取引あたりの実現損益（JPY）
    num_of_trades,                   # 総取引件数
    actual_trade_days,               # 実際の取引日数
    market_open_days,                # NYSEの営業日数
    # Unit_Economics
    ## 日別評価
    avg_gain_per_day_jpy, # 1日あたりの実現損益（JPY）
    avg_num_of_trades_per_day, # 1日あたりの取引件数
    return_on_cost, # ROIとしてはこちらか？
    return_on_sales
  ) %>%
  arrange(year_month) # 年月を昇順に（小さい順番に）

# ts_monthly %>% glimpse() %>% view()  # データ構造の確認

# *data_checkpoint_3 ----
# ▼目的：
#   ・月次単位で集計した KPI（損益・勝率・ROI 等）を保存
#   ・グラフや KPI 算出の基本単位となる“月次テーブル”を固定化
# ▼活用方法：
#   ・レポート生成やシミュレーションはこの月次データから開始すれば良い
#   ・中間生成物を直接 Notion や Excel に吐き出して確認するのも容易
save_checkpoint(ts_monthly, "ts_monthly", "ts_monthly")

# C) シミュレーション_時系列templateを結合 ----
## C-1. 既存データの最終月を自動認識。 ----
## 加えて2026年12月までテーブルを読込。
tmpl_future <- make_month_template(
  mode = "after_last", # mode指定
  end_ym = "2026-12",　# 将来の終了月（"YYYY-MM"）時点を指定
  data = ts_monthly,   # 既存データのテーブル名を指定
  ym_col = "year_month_iso" # 年月の列名を指定（ISO形式）
)

## C-2. 実データ側にも月初Dateを用意（結合に使う） ----
ts_monthly_d <- ts_monthly %>%
  # year_month_iso が無いケースにも備えて生成
  dplyr::mutate(
    year_month_iso  = dplyr::coalesce(.data$year_month_iso, to_ym_iso(.data$year_month)),
    year_month_date = safe_parse_month(.data$year_month_iso)  # ← ここがポイント
  ) %>%
  dplyr::select(year_month_iso, year_month, year_month_date, dplyr::everything())

# ts_monthly_d %>% view()

# *data_checkpoint_4 ----
# ▼目的：
#   ・月次集計結果に「ISO形式キー」と「月初日(Date)カラム」を追加し、
#     時系列処理や ggplot の日付軸に使いやすい形に整備
#   ・Quarto レポートや KPI 計算で直接利用する基盤データ
# ▼活用方法：
#   ・毎週の KPI レポートは基本的にこの checkpoint を読み込めばOK
#   ・履歴管理で「2025-09-14 時点の集計済みデータ」を再現可能
save_checkpoint(ts_monthly_d, "ts_monthly_d", "ts_monthly_d")

## C-3. 過去~将来時間軸の作成 ----
## 日付列×3列だけのフレーム
## 軸の“型”：実データの月と将来テンプレの月を合わせてユニーク化
## mpl_future は make_month_template(..., ym_col = "year_month_iso") で作成済みを想定
axis_full <- dplyr::bind_rows(
  ts_monthly_d %>% dplyr::select(year_month_iso, year_month, year_month_date),
  tmpl_future   %>% dplyr::select(year_month, year_month_date) %>%
    dplyr::mutate(year_month_iso = format(year_month_date, "%Y-%m"))
) %>%
  dplyr::distinct(year_month_iso, .keep_all = TRUE) %>%     # ISOキーで一意化
  dplyr::arrange(year_month_date)

# axis_full %>% view()

## C-4. 結合 + 0補完 ----
## 土台フレーム：軸（全期間）× 実データ（欠けはNA）→ 0補完（結合のみ）
plot_base <- axis_full %>%
  dplyr::left_join(
    ts_monthly_d,
    by = c("year_month_iso", "year_month_date")
  ) %>%
  dplyr::arrange(year_month_date)

# plot_base %>% glimpse() %>% view()

# *data_checkpoint_5 ----
# ▼目的：
#   ・過去(実績)＋現在＋将来テンプレートを結合した
#     “完全な時系列フレーム”を保存
#   ・グラフ描画や予測準備のベースになるデータ
# ▼活用方法：
#   ・毎週のグラフ作成(P1〜P9)はこの checkpoint を読み込むだけで良い
#   ・履歴管理で「当時の未来予測前提つきレポート」を再現可能
save_checkpoint(plot_base, "past_present_future", "plot_base")

# D) Plotting ----
## D-1. 期間設定（日付型で保持）変数 ----
start_date <- lubridate::ymd("2025-01-01")
end_date   <- lubridate::ymd("2025-12-01")

## D-2. 欠け月は0補完 + 符号列追加 ----
plot_df <- plot_base %>%
  dplyr::mutate(
    ttl_gain_realized_jpy = tidyr::replace_na(ttl_gain_realized_jpy, 0),
    gain_sign = dplyr::if_else(ttl_gain_realized_jpy >= 0, "positive", "negative"),
    gain_sign = factor(gain_sign, levels = c("negative", "positive"))
  ) %>%
  # 期間指定
  dplyr::filter(
    year_month_date >= start_date,
    year_month_date <= end_date
  )

# plot_df %>% glimpse() %>% view()

# *data_checkpoint_6 ----
# ▼目的：
#   ・期間指定済み
#   ・可視化直前のデータ（符号列や補完済み）を保存
#   ・毎週の P1〜P9 はこの checkpoint を基に作成
save_checkpoint(plot_df, "plot_ready", "plot_df")

## D-3. Left_panel ----
### P1_折れ線_傾向 ----
### 累積損益
### 期間（既存の変数をそのまま使う想定）
### start_date <- lubridate::ymd("2025-01-01")
### end_date   <- lubridate::ymd("2025-12-01")

# 1) 累積用のプロットデータ作成（実績/将来のフラグ、累積、色ラベル）
plot_data_full <- plot_base %>%
  dplyr::filter(year_month_date >= start_date,
                year_month_date <= end_date) %>%
  dplyr::arrange(year_month_date) %>%
  dplyr::mutate(
    is_actual = !is.na(ttl_gain_realized_jpy),                 # 実績フラグ
    gain_for_cum = tidyr::replace_na(ttl_gain_realized_jpy, 0),# 将来は0でフラットに
    capital_gain_cumsum = cumsum(gain_for_cum),                # 累積
    sign_label = if_else(capital_gain_cumsum >= 0, "profit", "loss")
  )

# *data_checkpoint_7 ----
# ▼目的：
#   ・累積損益や実績/将来フラグを持つ「拡張済みプロットデータ」を保存
#   ・累積推移グラフ、基準線交点、将来予測などの再利用に便利
# ▼活用方法：
#   ・毎週のレポートでは P1〜P9 以外の累積系グラフに活用可能
#   ・履歴管理により「当時の累積損益や予測準備データ」を再現可能
save_checkpoint(plot_data_full, "plot_cumsum", "plot_data_full")

# 2) 線分データ（隣接点を結ぶ）: 実績区間かどうかを判定
line_segments <- plot_data_full %>%
  dplyr::mutate(
    xend = dplyr::lead(year_month_date), # 隣接点のx座標
    yend = dplyr::lead(capital_gain_cumsum), # 隣接点のy座標
    is_actual_segment = is_actual & dplyr::lead(is_actual)
  ) %>%
  dplyr::filter(!is.na(xend), !is.na(yend))

# line_segments %>% glimpse() %>% view()

# 3) 実績線分の色分け（基準線クロス判定、基準線はゼロの水平線とする場合）
zero_ref_line <- 0

# 1) 隣接点（ベース）
# 「微分の前段階で作る差分ペア」＝「今回の線分データ」
seg_base <- plot_data_full %>%
  arrange(year_month_date) %>%
  transmute(
    x    = year_month_date,
    y    = capital_gain_cumsum,
    xend = lead(year_month_date),
    yend = lead(capital_gain_cumsum),
    is_actual_segment = is_actual & lead(is_actual)
  ) %>%
  filter(!is.na(xend), !is.na(yend))

# 2) 実績線分：基準線クロス判定 & 交点（Date型で作る）
# ざっくり言うと、実績の各線分が基準線（zero_ref_line）を横切るかを判定し、横切るなら“どこで交差するか”の x（日時）を線形補間で求めている処理です。
seg_actual <- seg_base %>%
  filter(is_actual_segment) %>%
  mutate(
    s1 = sign(y - zero_ref_line),
    s2 = sign(yend - zero_ref_line),
    crosses = (s1 * s2) == -1 & (yend != y),
    
    # t_cross: [0,1] で線分内の位置
    t_cross = if_else(crosses, (zero_ref_line - y) / (yend - y), NA_real_),
    
    # Dateを一旦 numeric（日数）にして線形補間 → Dateに戻す
    x_cross_num = as.numeric(x) + t_cross * (as.numeric(xend) - as.numeric(x)),
    x_cross     = as.Date(x_cross_num, origin = "1970-01-01")
  )

# 2a) 交点まで（前半）
seg_actual_1 <- seg_actual %>%
  mutate(
    x2 = if_else(crosses, x_cross, xend),
    y2 = if_else(crosses, zero_ref_line, yend),
    color = if_else(y >= zero_ref_line, "profit", "loss")
  ) %>%
  transmute(x, y, xend = x2, yend = y2, color)

# 2b) 交点から（後半：crosses行のみ）
seg_actual_2 <- seg_actual %>%
  filter(crosses) %>%
  mutate(
    x1 = x_cross, y1 = zero_ref_line,
    color = if_else(yend >= zero_ref_line, "profit", "loss")
  ) %>%
  transmute(x = x1, y = y1, xend, yend, color)

# 実績線分（色つき）は前半＋後半
line_segments_colored  <- bind_rows(seg_actual_1, seg_actual_2)
# 予測線分（点線グレー）
line_segments_forecast <- seg_base %>% filter(!is_actual_segment)

# *data_checkpoint_7a,7b ----
# ▼目的：
#   ・累積損益グラフ(P1)専用の線分データを保存
#   ・基準線交差や将来区間の区別を再現可能にする
# ▼保存場所：
#   plot_cumsum/plot_segments/ に格納して整理
save_checkpoint(line_segments_colored,  file.path("plot_cumsum", "plot_segments"), "line_segments_colored")
save_checkpoint(line_segments_forecast, file.path("plot_cumsum", "plot_segments"), "line_segments_forecast")

# プロット：累積損益の線分グラフ
P1 <- ggplot() +
  # 基準線（薄いグレー）
  geom_hline(yintercept = zero_ref_line, color = "gray50", alpha = 0.5, linewidth = 0.6) +
  
  # 予測：点線グレー
  geom_segment(
    data = line_segments_forecast,
    aes(x = x, y = y, xend = xend, yend = yend),
    color = "gray50", linetype = "dashed", linewidth = 1, alpha = 0.5
  ) +
  
  # 実績：交点で色が変わる（profit=青 / loss=赤）
  geom_segment(
    data = line_segments_colored,
    aes(x = x, y = y, xend = xend, yend = yend, color = color),
    linewidth = 1
  ) +
  # 実績点
  geom_point(
    data = dplyr::filter(plot_data_full, is_actual),
    aes(x = year_month_date, y = capital_gain_cumsum,
        color = ifelse(capital_gain_cumsum >= zero_ref_line, "profit", "loss")),
    size = 1.5
  ) +
  # 予測点
  geom_point(
    data = dplyr::filter(plot_data_full, !is_actual),
    aes(x = year_month_date, y = capital_gain_cumsum),
    size = 1.5, color = "gray50", alpha = 0.5
  ) +
  scale_color_manual(values = c(profit = "steelblue", loss = "firebrick"), guide = "none") +
  scale_y_continuous(#labels = scales::label_number(scale_cut = scales::cut_short_scale()), # 1K、!M
    labels = scales::label_comma(),  # ← comma区切りの場合
    name = "Cumulative Capital Gain (JPY)") +
  scale_x_date(date_labels = "%Y-%m", date_breaks = "1 month") +
  labs(title = "Cumulative Capital Gain",
       subtitle = "Cumulative Trend",
       caption = str_wrap("Note: From 2025-01 to 2025-12 | grey dashed line = just for reference", width = 30),
       x = NULL) +
  theme_minimal(base_family = "roboto") +
  theme(
    axis.text.x = element_blank(), # 非表示: axis.text.x = element_text(angle = 45, hjust = 1)
    axis.text.y = element_text(size = 8),
    axis.title.y = element_text(size = 9),
    plot.title = element_text(size = 12, face = "bold"),
    plot.subtitle = element_text(size = 9, color = "gray50"),
    plot.caption = element_text(face = "italic", color = "gray50", size = 8, hjust = 0)
  )

# preview
# P1

# **viz_checkpoint_1 ----
save_viz_checkpoint(P1, "P1")

### P2_棒グラフ_傾向----
### monthly Capital gain
P2 <- ggplot(plot_df,
             aes(x = year_month_date,
                 y = ttl_gain_realized_jpy,
                 fill = gain_sign)) +
  geom_col(width = 25) + # 月単位の棒幅を調整
  scale_fill_manual(
    values = c("positive" = "steelblue", "negative" = "firebrick"),
    guide = "none"
  ) +
  scale_y_continuous(
    # labels = scales::label_number(scale_cut = scales::cut_short_scale()),　# 1K、1Mの省略形の場合
    labels = scales::label_comma(),  # ← comma区切りの場合
    name = "Capital Gain (JPY)"
  ) +
  scale_x_date(
    date_labels = "%Y-%m",
    date_breaks = "1 month",
    expand = expansion(mult = c(0.01, 0.01)) # 左右に余白追加
  ) +
  labs(
    title = "Monthly Capital Gain",
    subtitle = "Breakdown of Cumulative Gain/Loss",
    caption = str_wrap("Note: monthly-terend, contribution to the cumulative gain or loss", width = 30),
    x = NULL
  ) +
  theme_minimal(base_family = "roboto") + #sans
  theme(
    axis.text.x = element_blank(), #非表示:axis.text.x = element_blank(), element_text(angle = 45, hjust = 1), 
    axis.ticks.x = element_blank(), #非表示：axis.ticks.x = element_blank(), 表示：element_line()
    axis.text.y = element_text(size = 8),
    axis.title.y = element_text(size = 9),
    plot.title = element_text(size = 12, face = "bold"),
    plot.subtitle = element_text(size = 9, color = "gray50"),
    plot.caption = element_text(face = "italic", color = "gray50", size = 8, hjust = 0)
  )

### プレビュー
# P2
# **viz_checkpoint_2 ----
save_viz_checkpoint(P2, "P2")

# panel_half <- P2/P1
# panel_half

### P3_折れ線_傾向 ----
### 1日あたりの平均損益
# 平均日次損益の折れ線

# 月番号を追加（X軸に数値をつけるため）
plot_df <- plot_df %>%
  dplyr::mutate(
    month_num = lubridate::month(year_month_date)  # ★ 追加: 1～12 の数値に変換
  )

P3 <- ggplot(plot_df, aes(x = month_num, y = avg_gain_per_day_jpy)) + # YYYY-MM形式の場合：x = year_month_date
  geom_line(color = "darkgreen", linewidth = 1) +
  geom_point(color = "darkgreen", size = 1.5) +
  # ★ ゼロ基準の水平線を追加
  geom_hline(yintercept = 0, color = "gray50", linewidth = 0.6) +
  scale_y_continuous(
    labels = scales::label_comma(),
    name = "Avg Gain per Day (JPY)"
  ) +
  # scale_x_date(                                         # ★ YYYY-MM形式の日付軸をコメントアウト
  #   date_labels = "%Y-%m",
  #   date_breaks = "1 month",
  #   expand = expansion(mult = c(0.01, 0.01))
  # ) +
  scale_x_continuous(                                    # ★ 追加: 数値軸で 1～12 を表示
    breaks = 1:12,
    labels = 1:12,
    name = ""　# month
  ) +
  labs(
    title = "Avg Daily Capital Gain",
    subtitle = " Daily-target",
    caption = str_wrap("Note: Monthly_Gain = Daily_Gain × Trading_Days", width = 30)
    # x = NULL                                           # ★ 削除: scale_x_continuous で name 指定するので不要
  ) +
  theme_minimal(base_family = "roboto") +
  theme(
    axis.text.x = element_text(size = 8), #角度付ける場合：element_text(angle = 45, hjust = 1)
    axis.text.y = element_text(size = 8),
    axis.title.y = element_text(size = 9),
    plot.title = element_text(size = 12, face = "bold"),
    plot.subtitle = element_text(size = 9, color = "gray50"),
    plot.caption = element_text(face = "italic", color = "gray50", size = 8, hjust = 0)
  )

# preview
# P3

# **viz_checkpoint_3 ----
save_viz_checkpoint(P3, "P3")

#### merge_left_panel ---- 
left_panel <- P1/P2/P3

## Cafe) 極端値・NA値の確認 ----
## NA値の確認
# ts_monthly_d %>%
#   filter(!is.finite(avg_gain_per_day_jpy)) %>%
#   select(year_month, ttl_gain_realized_jpy, actual_trade_days, avg_gain_per_day_jpy)
# 
# ## 欠損値や非有限値（NaN, Inf）があるか確認
# plot_df %>%
#   filter(!is.finite(avg_gain_per_day_jpy) | is.na(avg_gain_per_day_jpy)) %>%
#   select(year_month_iso, year_month_date, ttl_gain_realized_jpy, actual_trade_days, avg_gain_per_day_jpy)
# 
# ## Y軸（avg_gain_per_day_jpy）の極端値を確認
# summary(plot_df$avg_gain_per_day_jpy)
# range(plot_df$avg_gain_per_day_jpy, na.rm = TRUE)
# 
# ## X軸（日付）の範囲を確認
# range(plot_df$year_month_date, na.rm = TRUE)


## D-4. Center_panel ----
## 年次比較用データ準備
ts_monthly_comp <- ts_monthly_d %>%
  mutate(
    year = lubridate::year(year_month_date),
    month = lubridate::month(year_month_date, label = TRUE, abbr = TRUE) # 月名（Jan, Feb...）
  )

# ビジネス用カラーパレット（ブルー基調＋補助にグレー）
biz_colors <- c("2024" = "#1F77B4",   # muted blue
                "2025" = "#2CA02C",   # muted green
                "2026" = "#FF7F0E",   # muted orange
                "2027" = "#7F7F7F")   # muted grey（必要なら）

### P4_折れ線_傾向 ----
### 月次Win Rate 
P4 <- ggplot(ts_monthly_comp, aes(x = month, y = win_rate, group = factor(year), color = factor(year))) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_y_continuous(
    labels = scales::percent_format(accuracy = 1),
    name = "Win Rate"
  ) +
  scale_color_manual(values = biz_colors, name = "Year") +   # ← カラー適用
  labs(
    title = "Monthly Win Rate",
    subtitle = "Yearly-Comps",
    caption = str_wrap("Note: Return rate", width = 30), 
    x = "" #Month
  ) +
  theme_minimal(base_family = "roboto") +
  theme(
    axis.text.x = element_blank(), # 非表示：axis.text.x = element_blank()、表示：element_text(size = 8)
    axis.text.y = element_blank(),  # 非表示：axis.text.y = element_blank()、表示：element_text(size = 8),
    axis.title.y = element_text(size = 9),
    plot.title = element_text(size = 12, face = "bold"),
    plot.subtitle = element_text(size = 9, color = "gray50"),
    legend.position = "right",
    plot.caption = element_text(face = "italic", color = "gray50", size = 8, hjust = 0)
  )

# プレビュー
# P4

# **viz_checkpoint_4 ----
save_viz_checkpoint(P4, "P4")

### P5_棒グラフ_傾向 ----
### 月次取引回数
### P5: 年ごとの取引件数を月次で比較（棒グラフ)
P5 <- ggplot(ts_monthly_comp, aes(x = month, y = num_of_trades, fill = factor(year))) +
  geom_col(position = "dodge") +
  scale_y_continuous(
    labels = scales::comma,
    name = "Number of Trades"
  ) +
  scale_fill_manual(values = biz_colors, name = "Year") +    # ← カラー適用
  labs(
    title = "Monthly Number of Trades",
    subtitle = "Yearly-Comps",
    caption = str_wrap("Note: Number of trials or days-of-non-positions", width = 30),
    x = "" #Month
  ) +
  theme_minimal(base_family = "roboto") +
  theme(
    axis.text.x = element_blank(), # 非表示：axis.text.x = element_blank()、表示：element_text(size = 8)
    axis.text.y = element_blank(),  # 非表示：axis.text.y = element_blank()、表示：element_text(size = 8),
    axis.title.y = element_text(size = 9),
    plot.title = element_text(size = 12, face = "bold"),
    plot.subtitle = element_text(size = 9, color = "gray50"),
    legend.position = "right",
    plot.caption = element_text(face = "italic", color = "gray50", size = 8, hjust = 0)
  )

# プレビュー
# P5
# **viz_checkpoint_5 ----
save_viz_checkpoint(P5, "P5")

### P6_棒グラフ_年次別 ----
### 月次 actual_trade_days
P6 <- ggplot(ts_monthly_comp, 
             aes(x = as.numeric(month), y = actual_trade_days, fill = factor(year))) +
  geom_col(position = "dodge") +
  scale_x_continuous(
    breaks = 1:12,
    labels = 1:12,
    name = "" #Month
  ) +
  scale_y_continuous(
    labels = scales::comma,
    name = "Actual Trade Days"
  ) +
  scale_fill_manual(values = biz_colors, name = "Year") +
  labs(
    title = "Monthly Actual Trade Days",
    subtitle = "Yearly-Comps",
    caption = str_wrap("Note: Intensity of trading activity or days-of-non-positions", width = 30),
  ) +
  theme_minimal(base_family = "roboto") +
  theme(
    axis.text.x  = element_text(size = 8),
    axis.text.y  = element_text(size = 8),
    axis.title.y = element_text(size = 9),
    plot.title   = element_text(size = 12, face = "bold"),
    plot.subtitle= element_text(size = 9, color = "gray50"),
    legend.position = "right",
    plot.caption = element_text(face = "italic", color = "gray50", size = 8, hjust = 0)
  )

# **viz_checkpoint_6 ----
save_viz_checkpoint(P6, "P6")

### P6B_facet_wrap ----
# P6B <- ggplot(ts_monthly_comp, 
#               aes(x = month, y = actual_trade_days, fill = factor(year))) +
#   geom_col() +
#   scale_y_continuous(labels = scales::comma, name = "Actual Trade Days") +
#   scale_fill_manual(values = biz_colors, name = "Year") +
#   labs(
#     title = "Monthly Actual Trade Days by Year (Facet)",
#     subtitle = "Each year shown separately",
#     x = "Month"
#   ) +
#   facet_wrap(~year, ncol = 1) +
#   theme_minimal(base_family = "roboto")

### P6C_折れ線 ----
# P6C <- ggplot(ts_monthly_comp, 
#               aes(x = month, y = actual_trade_days, group = factor(year), color = factor(year))) +
#   geom_line(linewidth = 1) +
#   geom_point(size = 2) +
#   scale_y_continuous(labels = scales::comma, name = "Actual Trade Days") +
#   scale_color_manual(values = biz_colors, name = "Year") +
#   labs(
#     title = "Monthly Actual Trade Days by Year (Line)",
#     subtitle = "Year-over-year comparison",
#     x = "Month"
#   ) +
#   theme_minimal(base_family = "roboto")

### P6D_相関散布図_分類 ----
### 勝率と取引回数
# 勝率と取引回数の相関
# 相関係数を計算（ピアソン相関）
# cor(ts_monthly$win_rate, ts_monthly$num_of_trades, use = "complete.obs", method = "pearson")
# # 散布図と回帰直線
# library(dplyr)
# library(ggplot2)
# library(ggrepel)
# 
# # 年列を追加
# ts_monthly_labeled <- ts_monthly %>%
#   mutate(
#     year = substr(year_month_iso, 1, 4)  # "2024" or "2025"
#   )
# 
# P6 <- ggplot(ts_monthly_labeled,
#              aes(x = num_of_trades, y = win_rate, color = year)) +
#   geom_point(size = 2) +
#   geom_smooth(method = "lm", se = TRUE,
#               color = "red", linetype = "dashed") +
#   geom_text_repel(
#     aes(label = year_month),
#     size = 3, family = "roboto"
#   ) +
#   scale_color_manual(
#     values = c("2024" = "skyblue", "2025" = "darkblue"), # ← パレットはそのまま
#     name = "Year"
#   ) +
#   scale_y_continuous(
#     labels = scales::percent_format(accuracy = 1),
#     name = "Win Rate"
#   ) +
#   scale_x_continuous(
#     labels = scales::comma,
#     name = "Number of Trades"
#   ) +
#   labs(
#     title = "Win Rate vs Number of Trades",
#     subtitle = "Year-over-year correlation"
#   ) +
#   theme_minimal(base_family = "roboto") +
#   theme(
#     axis.text.x  = element_text(size = 8),
#     axis.text.y  = element_text(size = 8),
#     axis.title.x = element_text(size = 9),
#     axis.title.y = element_text(size = 9),
#     plot.title   = element_text(size = 12, face = "bold"),
#     plot.subtitle= element_text(size = 9, color = "gray50"),
#     legend.position = "right"
#   )

#### merge_Center_Panel ----
center_panel <- P4 / P5 / P6

#### merge_Left_Center_Panel ----
left_center_panel <- left_panel | center_panel

## D-5. Right_panel----
### P7_ROI_年次比較折れ線 ----
# X軸文字列版
# ts_monthly_roi <- ts_monthly_d %>%
#   mutate(
#     year  = lubridate::year(year_month_date),
#     month = lubridate::month(year_month_date, label = TRUE, abbr = TRUE)
#   )

ts_monthly_roi <- ts_monthly_d %>%
  mutate(
    year      = lubridate::year(year_month_date),
    month     = lubridate::month(year_month_date, label = TRUE, abbr = TRUE),
    month_num = lubridate::month(year_month_date)   # ★ 追加: 1～12の数値を直接抽出
  )


P7 <- ggplot(ts_monthly_roi,
             aes(x = month_num, y = return_on_cost,                 # ★ 修正: xをmonth → month_numに変更
                 group = factor(year), color = factor(year))) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_y_continuous(
    labels = scales::percent_format(accuracy = 1),
    name = "Return on Cost (ROI)"
  ) +
  # scale_x_xxx はカテゴリ用なので削除
  scale_x_continuous(                                     # ★ 追加: 数値軸で 1～12 を表示
    breaks = 1:12,
    labels = 1:12,
    name = "" #month
  ) +
  scale_color_manual(values = biz_colors, name = "Year") +  # ← P4/P5 と同じ色を再利用
  labs(
    title = "Monthly ROI",
    subtitle = "Return rate",
    caption = str_wrap("Note: Return on Cost = (Total Gain / Total Acquisition Cost) × 100", width = 30),
    # x = "Month" は scale_x_continuous で指定済みなので不要
  ) +
  theme_minimal(base_family = "roboto") +
  theme(
    axis.text.x  = element_blank(),   # ★ 数値なので角度指定は不要、element_text(size = 8),
    axis.text.y  = element_text(size = 8),
    axis.title.y = element_text(size = 9),
    plot.title   = element_text(size = 12, face = "bold"),
    plot.subtitle= element_text(size = 9, color = "gray50"),
    legend.position = "right",
    plot.caption = element_text(face = "italic", color = "gray50", size = 8, hjust = 0)
  )

# プレビュー
# P7
# **viz_checkpoint_7 ----
save_viz_checkpoint(P7, "P7")

### P8_Avg_AcquisitionCost_perTrade ----
# X軸：文字列版
# ts_monthly_cost <- ts_monthly_d %>%
#   mutate(
#     avg_acquisition_per_trade = ifelse(num_of_trades > 0,
#                                        ttl_cost_acquisition_jpy / num_of_trades,
#                                        NA_real_),
#     year  = lubridate::year(year_month_date),
#     month = lubridate::month(year_month_date, label = TRUE, abbr = TRUE)
#   )

# X軸：数値版
ts_monthly_cost <- ts_monthly_d %>%
  mutate(
    avg_acquisition_per_trade = ifelse(num_of_trades > 0,
                                       ttl_cost_acquisition_jpy / num_of_trades,
                                       NA_real_),
    year      = lubridate::year(year_month_date),
    month     = lubridate::month(year_month_date, label = TRUE, abbr = TRUE), # ★ ラベル用
    month_num = lubridate::month(year_month_date)                             # ★ 追加: 数値1～12
  )

P8 <- ggplot(ts_monthly_cost,
             aes(x = month_num, y = avg_acquisition_per_trade,                # ★ 修正: month → month_num
                 group = factor(year), color = factor(year))) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_y_continuous(
    labels = scales::comma,
    name = "Avg Acquisition Cost per Trade (JPY)"
  ) +
  scale_x_continuous(                                                         # ★ 追加: 数値1～12のX軸
    breaks = 1:12,
    labels = 1:12,
    name   = ""　#month
  ) +
  scale_color_manual(values = biz_colors, name = "Year") +
  labs(
    title = "Monthly Avg Acquisition Cost per Trade",
    subtitle = "",
    caption = str_wrap("Note: total acquisition cost ÷ number of trades", width = 30)
    # x = "Month" は scale_x_continuous で指定済みなので削除
  ) +
  theme_minimal(base_family = "roboto") +
  theme(
    axis.text.x  = element_text(size = 8),   # ★ 数字だけなら角度不要
    axis.text.y  = element_text(size = 8),
    axis.title.y = element_text(size = 9),
    plot.title   = element_text(size = 12, face = "bold"),
    plot.subtitle= element_text(size = 9, color = "gray50"),
    legend.position = "right",
    plot.caption = element_text(face = "italic", color = "gray50", size = 8, hjust = 0)
  )

# プレビュー
# P8

# **viz_checkpoint_8 ----
save_viz_checkpoint(P8, "P8")


### P9_Risk Reward_月次平均損益 & RR (非累積) ----
risk_reward_df <- ts_monthly_d %>%
  filter(year_month_date >= ymd("2025-01-01"),
         year_month_date <= ymd("2025-12-31")) %>%
  arrange(year_month_date) %>%
  mutate(
    avg_gain_per_trade = ifelse(num_of_trades > 0,
                                ttl_gain_realized_jpy / num_of_trades, 0),
    avg_profit = ifelse(num_of_win_trades > 0,
                        ttl_gain_realized_jpy / num_of_win_trades, NA_real_),
    avg_loss   = ifelse((num_of_trades - num_of_win_trades) > 0,
                        abs(ttl_gain_realized_jpy) / (num_of_trades - num_of_win_trades), NA_real_),
    rr_monthly = ifelse(!is.na(avg_loss) & avg_loss > 0, avg_profit / avg_loss, NA_real_),
    month_num = lubridate::month(year_month_date)
  )

# *data_checkpoint_risk_reward ----
# ▼目的：
#   ・P9 の元データとなる risk_reward_df を保存
#   ・Quarto 側で再計算・リスケールが可能
# ▼活用方法：
#   ・固定の P9.rds を使う代わりに、risk_reward_df.rds を読み込んで再計算も可能
save_checkpoint(risk_reward_df, "plot_ready", "risk_reward_df")

# 正規化係数を計算
scale_factor     <- max(abs(risk_reward_df$avg_gain_per_trade), na.rm = TRUE) /
  max(risk_reward_df$rr_monthly, na.rm = TRUE)
sec_scale_factor <- max(risk_reward_df$rr_monthly, na.rm = TRUE) /
  max(abs(risk_reward_df$avg_gain_per_trade), na.rm = TRUE)

# プロット用の列を追加
risk_reward_df <- risk_reward_df %>%
  mutate(rr_scaled = rr_monthly * scale_factor)

# プロット
P9 <- ggplot(data = risk_reward_df, aes(x = month_num)) +
  geom_col(aes(y = avg_gain_per_trade,
               fill = avg_gain_per_trade >= 0), width = 0.6, alpha = 0.6) +
  
  geom_line(aes(y = rr_scaled), color = "darkgreen", linewidth = 1) +
  geom_point(aes(y = rr_scaled), color = "darkgreen", size = 1.5) +
  
  scale_fill_manual(values = c("TRUE" = "steelblue", "FALSE" = "firebrick"), guide = "none") +
  scale_y_continuous(
    labels = scales::comma,
    name = "Avg Gain per Trade (JPY, monthly)",
    sec.axis = sec_axis(~ . * sec_scale_factor,
                        name = "Monthly Risk Reward Ratio")
  ) +
  scale_x_continuous(breaks = 1:12, labels = 1:12, name = "") +
  labs(
    title = "Monthly Risk Reward",
    subtitle = str_wrap("Avg Gain per Trade (bars) and Risk Reward Ratio (line)", width = 30),
    caption = str_wrap(paste("Note: RR = Avg Profit ÷ Avg Loss (monthly, not cumulative) | YTD as of",
                             format(Sys.Date(), "%B %d, %Y")), width = 30)
  ) +
  theme_minimal(base_family = "roboto") +
  theme(
    axis.text.x = element_text(size = 8),
    axis.text.y = element_text(size = 8),
    axis.title.y = element_text(size = 9),
    axis.title.y.right = element_text(size = 9, color = "darkgreen"),
    plot.title = element_text(size = 12, face = "bold"),
    plot.subtitle = element_text(size = 9, color = "gray50"),
    plot.caption = element_text(face = "italic", color = "gray50", size = 8, hjust = 0)
  )

# **viz_checkpoint_9 ----
save_viz_checkpoint(P9, "P9")

### P9a_Raincloud_ROI ----
# library(gghalves)  # Raincloud表現用（半バイオリン＋ジッター）
# 
# # --- 統計量計算 ---
# roi_stats <- ts_monthly_d %>%
#   group_by(year = lubridate::year(year_month_date)) %>%
#   summarise(
#     Q3     = quantile(return_on_cost, 0.75, na.rm = TRUE),
#     Median = median(return_on_cost, na.rm = TRUE),
#     Mean   = mean(return_on_cost, na.rm = TRUE),
#     Q1     = quantile(return_on_cost, 0.25, na.rm = TRUE),
#     IQR    = IQR(return_on_cost, na.rm = TRUE),
#     .groups = "drop"
#   ) %>%
#   mutate(across(-year, ~ scales::percent(.x, accuracy = 0.1)))
# 
# # --- 行列を転置（行=統計量, 列=年） ---
# roi_stats_t <- roi_stats %>%
#   tidyr::pivot_longer(-year, names_to = "Stat", values_to = "Value") %>%
#   tidyr::pivot_wider(names_from = year, values_from = Value)
# 
# # --- 表を作成 ---
# table_grob <- gridExtra::tableGrob(
#   roi_stats_t,
#   rows = NULL,
#   theme = gridExtra::ttheme_default(
#     core = list(fg_params = list(cex = 0.75)),
#     colhead = list(fg_params = list(cex = 0.8, fontface = "bold"))
#   )
# )
# 
# # --- Raincloudプロット ---
# P9_plot <- ggplot(ts_monthly_d,
#                   aes(x = factor(lubridate::year(year_month_date)),
#                       y = return_on_cost,
#                       fill = factor(lubridate::year(year_month_date)))) +
#   gghalves::geom_half_violin(side = "l", alpha = 0.6, trim = FALSE) +
#   geom_boxplot(width = 0.2, outlier.shape = NA, alpha = 0.6) +
#   gghalves::geom_half_point(side = "r", alpha = 0.6, size = 1.8) +
#   scale_y_continuous(labels = scales::percent_format(accuracy = 1),
#                      name = "Monthly ROI") +
#   scale_fill_manual(values = biz_colors, name = "Year") +
#   labs(
#     title = "Distribution of Monthly ROI by Year",
#     subtitle = "Raincloud plot + summary stats table (transposed)",
#     x = "Year"
#   ) +
#   theme_minimal(base_family = "roboto") +
#   theme(legend.position = "none")
# 
# # --- 横並びに配置 ---
# P9 <- P9_plot | table_grob

# プレビュー
# P9


#### merge_Right_Panel ----
right_panel <- P7 / P8 / P9

#### merge_Right_Panel ----
left_center_right_panel <- left_panel | center_panel | right_panel

### PX_ヒストグラム ----
### トレード当たり損益分布
### 元データ（取引単位）がある場合はそちらを使うのがベスト
### ここでは月次から平均を取るのではなく、各取引のデータフレームを想定
### 例: merged_csv_data に "gain_per_trade_jpy" 列がある場合

# # 取引単位の損益列を用意（もし無ければ計算）
# trade_df <- merged_csv_data %>%
#   mutate(gain_per_trade_jpy = ttl_gain_realized_jpy / num_of_trades)
# 
# PX <- ggplot(trade_df, aes(x = gain_per_trade_jpy)) +
#   geom_histogram(
#     bins = 50,               # 棒の数（調整可）
#     fill = "steelblue", 
#     color = "white", 
#     alpha = 0.8
#   ) +
#   geom_vline(
#     aes(xintercept = mean(gain_per_trade_jpy, na.rm = TRUE)),
#     color = "red", linetype = "dashed", linewidth = 1
#   ) +
#   scale_x_continuous(
#     labels = scales::comma,
#     name = "Gain per Trade (JPY)"
#   ) +
#   scale_y_continuous(
#     labels = scales::comma,
#     name = "Frequency"
#   ) +
#   labs(
#     title = "Distribution of Gain per Trade",
#     subtitle = "Histogram with mean line (dashed red)"
#   ) +
#   theme_minimal(base_family = "roboto") +
#   theme(
#     axis.text = element_text(size = 8),
#     axis.title = element_text(size = 9),
#     plot.title = element_text(size = 12, face = "bold"),
#     plot.subtitle = element_text(size = 9, color = "gray50")
#   )
# 
# # プレビュー
# P7

# 月ごとにヒストグラム
# P6_monthly <- ggplot(trade_df, aes(x = gain_per_trade_jpy)) +
#   geom_histogram(bins = 30, fill = "steelblue", color = "white", alpha = 0.8) +
#   facet_wrap(~ year_month, scales = "free_y") +  # 月ごとに分けて比較
#   geom_vline(
#     data = trade_df %>% group_by(year_month) %>% 
#       summarise(avg_gain = mean(gain_per_trade_jpy, na.rm = TRUE)),
#     aes(xintercept = avg_gain),
#     color = "red", linetype = "dashed", linewidth = 0.8
#   ) +
#   scale_x_continuous(labels = scales::comma, name = "Gain per Trade (JPY)") +
#   scale_y_continuous(labels = scales::comma, name = "Frequency") +
#   labs(title = "Monthly Distribution of Gain per Trade",
#        subtitle = "Dashed line = Monthly Mean") +
#   theme_minimal(base_family = "roboto") +
#   theme(
#     strip.text = element_text(size = 8),
#     axis.text.x = element_text(size = 7)
#   )

## D-6. Caption追加 ----
## left_panel <- add_caption(left_panel)
## panel_half
## panel_half <- add_caption(P2 / P1, family = "Arial", size = 9, italic = TRUE)
# left_center_panel <- add_caption(left_center_panel)

left_center_right_panel <- add_caption(left_center_right_panel)

## D-7. Titile追加 ----
## subtitleに日付を入れる場合
asof_date <- format(Sys.Date(), "%B %d, %Y")  # e.g. "August 17, 2025"

## Title作成
hdr <- make_title(
  title = "Investing Casually: One-Pager",
  subtitle =  paste0("2025 YTD as of ", asof_date)
)
# panel <- add_title(left_center_panel, hdr = hdr)
panel <- add_title(left_center_right_panel, hdr = hdr)

# Key Insightsが無しの場合
panel

# E) Key Insights ----
# --- KPI計算 ---
# start_date <- lubridate::ymd("2025-01-01")
# end_date   <- lubridate::ymd("2025-12-01")
# summary(ts_monthly)
# skimr::skim(ts_monthly)

## E-1. date型に変換 ----
ts_monthly_d <- ts_monthly %>%
  mutate(year_month_date = ym(year_month_iso)) 
# unique(ts_monthly$year_month)
# unique(ts_monthly$year_month_iso)

# ts_monthly_d %>% glimpse()

## E-2. KPI計算 ---- 
## KPIに改めて期間適用して観察したいKPIを再計算する手順になっている 
kpi_df <- ts_monthly_d %>%
  dplyr::filter(year_month_date >= start_date,
                year_month_date <= end_date)

# kpi_df %>% glimpse() %>% view()

# 損益合計
ytd_gain <- sum(kpi_df$ttl_gain_realized_jpy, na.rm = TRUE)
# 勝率
win_rate <- with(kpi_df,
                 sum(num_of_win_trades, na.rm = TRUE) /
                   sum(num_of_trades, na.rm = TRUE))
# 日次平均損益
avg_day  <- with(kpi_df,
                 sum(ttl_gain_realized_jpy, na.rm = TRUE) /
                   sum(actual_trade_days, na.rm = TRUE))

# 月次平均の取引件数
avg_trades_monthly <- mean(kpi_df$num_of_trades, na.rm = TRUE)

# 日当たり平均取引件数
avg_trades_daily <- mean(kpi_df$avg_num_of_trades_per_day, na.rm = TRUE)

# リターン率（取得コストに対するリターン率）
ROI <- with(kpi_df,
            sum(ttl_gain_realized_jpy, na.rm = TRUE) /
              sum(ttl_cost_acquisition_jpy, na.rm = TRUE))

# # 取引当たりの取得コスト
# avg_trade_amount_acquisition <- with(kpi_df,
#                          sum(ttl_cost_acquisition_jpy, na.rm = TRUE) /
#                            sum(num_of_trades, na.rm = TRUE))

# 取引当たりの取得コスト
# dplyrを利用した方がデバックが簡単。部分的な計算を見えるかした方が良い。
avg_trade_amount_acquisition <- kpi_df %>%
  summarise(
    total_cost   = sum(ttl_cost_acquisition_jpy, na.rm = TRUE),
    total_trades = sum(num_of_trades, na.rm = TRUE),
    avg_trade_amount = total_cost / total_trades
  ) %>%
  pull(avg_trade_amount)

# 取引日数合計
total_trade_days <- kpi_df %>%
  summarise(total_days = sum(actual_trade_days, na.rm = TRUE)) %>%
  pull(total_days)

# 取引月数合計
total_months <- kpi_df %>%
  summarise(months = n_distinct(year_month_date)) %>%
  pull(months)

# # 表示用に整形_list形式
# kpis <- list(
#   "YTD cumulative" = paste(scales::comma(ytd_gain), "JPY"),
#   "Win rate"       = scales::percent(win_rate, accuracy = 0.1), # accuracy = 0.1 は小数点以下1桁
#   "Avg profit / day"    = paste(scales::comma(round(avg_day)), "JPY"),
#   "Avg trades / month"  = scales::comma(round(avg_trades_monthly, 1)),
#   "Avg trades / day"    = scales::comma(round(avg_trades_daily, 1))
# )

# kpi用テキスト_pasteO形式
# 段落替え
# kpi_text <- paste0(
#   "<b>YTD cumulative:</b> ", scales::comma(ytd_gain), " JPY<br>",
#   "<b>Win rate:</b> ", scales::percent(win_rate, accuracy = 0.1), "<br>",
#   "<b>Avg profit/day:</b> ", scales::comma(round(avg_day)), " JPY<br>",
#   "<b>Avg trades/month:</b> ", scales::comma(round(avg_trades_monthly, 1)), "<br>",
#   "<b>Avg trades/day:</b> ", scales::comma(round(avg_trades_daily, 1))
# )

# KPIとnarrativeを一緒にする形式__pasteO形式
kpi_text <- paste0(
  # 計測期間
  "<b>Period:</b> ", format(as.Date(paste0(format(Sys.Date(), "%Y"), "-01-01")), "%B %d, %Y"),
  " – ", format(Sys.Date(), "%B %d, %Y"), " | ",   # ← 2025-01-01 〜 今日
  "<b>Trade Days:</b> ", scales::comma(total_trade_days), " ( ",
  "<b>Months:</b> ", scales::comma(total_months), " ) <br>",
  
  # 最終KPI
  "<b>YTD cumulative:</b> ", scales::comma(ytd_gain), " JPY | ",
  "<b>Win rate:</b> ", scales::percent(win_rate, accuracy = 0.1), " | ",
  "<b>ROI:</b> ", scales::percent(ROI, accuracy = 0.1), " | ",
  "<b>Avg Amount_acquisition/trade: </b> ", scales::comma(avg_trade_amount_acquisition), " JPY<br>",
  
  # 中間KPI
  "<b>Avg profit/day:</b> ", scales::comma(round(avg_day)), " JPY | ",
  "<b>Avg trades/day:</b> ", scales::comma(round(avg_trades_daily, 1)), " times ( ",
  "<b>Avg trades/month:</b> ", scales::comma(round(avg_trades_monthly, 1)), " ) <br><br>",
  
  # 先行KPI
  
  # 分析用KPI
  
  # コメント
  "Note:実際の取引回数が57日は印象として少ない。ポジションを保有しないデイトレをスタイルとしておきながら実はポジション残している事が原因？", "<br>",
  "Target:利回り0.5%-1.0%であれば良い！", "<br>",
  "今後todo：グラフのデザイン改良、RightPanelの作成、日次データテー物の生成byPython、保有期間"
)


## E-3. Key Insightsパネル作成 ---- 
# Key Insights の本文HTML（改行区切り）
# body_html <- build_kv_lines(kpis, label_bold = TRUE, between = "<br>")
# 
# body_html <- paste0(
#   "<span style='display:inline-block; width:180px'><b>YTD cumulative</b>: ", scales::comma(ytd_gain), " JPY</span>",
#   "<span style='display:inline-block; width:150px'><b>Win rate</b>: ", scales::percent(win_rate, accuracy = 0.1), "</span><br>",
#   "<span style='display:inline-block; width:180px'><b>Avg profit / day</b>: ", scales::comma(round(avg_day)), " JPY</span>",
#   "<span style='display:inline-block; width:150px'><b>Avg trades / month</b>: ", scales::comma(round(avg_trades_monthly, 1)), "</span><br>",
#   "<span style='display:inline-block; width:180px'><b>Avg trades / day</b>: ", scales::comma(round(avg_trades_daily, 1)), "</span>"
# )
# 
# body_html <- paste0(
#   "<span style='display:inline-block; width:300px'><b>YTD cumulative</b>: ", scales::comma(ytd_gain), " JPY</span>",
#   "<span style='display:inline-block; width:200px; margin-left:40px'><b>Win rate</b>: ", scales::percent(win_rate, accuracy = 0.1), "</span><br>",
#   
#   "<span style='display:inline-block; width:300px'><b>Avg profit / day</b>: ", scales::comma(round(avg_day)), " JPY</span>",
#   "<span style='display:inline-block; width:200px; margin-left:40px'><b>Avg trades / month</b>: ", scales::comma(round(avg_trades_monthly, 1)), "</span><br>",
#   
#   "<span style='display:inline-block; width:300px'><b>Avg trades / day</b>: ", scales::comma(round(avg_trades_daily, 1)), "</span>"
# )

## E-4. 
# *data_checkpoint_KPI ----
# ▼目的：
#   ・包括的な KPI データフレームを作成して保存
#   ・月次詳細 + 期間サマリーを同時に含む
#   ・Quarto レポートから即利用できる

# 期間指定
start_date <- lubridate::ymd("2025-01-01")
end_date   <- Sys.Date()

# 月次kpiのdf
kpi_master <- ts_monthly_d %>%
  filter(year_month_date >= start_date,
         year_month_date <= end_date) %>%
  mutate(
    # 補助列
    year  = lubridate::year(year_month_date),
    month = lubridate::month(year_month_date),
    
    # トレードあたり平均損益
    avg_gain_per_trade = ifelse(num_of_trades > 0,
                                ttl_gain_realized_jpy / num_of_trades, NA_real_),
    
    # 勝ちトレード平均損益
    avg_profit = ifelse(num_of_win_trades > 0,
                        ttl_gain_realized_jpy / num_of_win_trades, NA_real_),
    
    # 負けトレード平均損失
    avg_loss   = ifelse((num_of_trades - num_of_win_trades) > 0,
                        abs(ttl_gain_realized_jpy) / (num_of_trades - num_of_win_trades), NA_real_),
    
    # 月次 Risk Reward
    rr_monthly = ifelse(!is.na(avg_loss) & avg_loss > 0, avg_profit / avg_loss, NA_real_)
  )

# サマリー行を tibble に追加_今週までの累計kpiのdf
kpi_summary <- tibble::tibble(
  type             = "summary",
  as_of_date       = Sys.Date(),
  period_start     = start_date,
  period_end       = end_date,
  ytd_gain         = sum(kpi_master$ttl_gain_realized_jpy, na.rm = TRUE),
  win_rate         = sum(kpi_master$num_of_win_trades, na.rm = TRUE) / 
    sum(kpi_master$num_of_trades, na.rm = TRUE),
  ROI              = sum(kpi_master$ttl_gain_realized_jpy, na.rm = TRUE) / 
    sum(kpi_master$ttl_cost_acquisition_jpy, na.rm = TRUE),
  avg_trade_amount = sum(kpi_master$ttl_cost_acquisition_jpy, na.rm = TRUE) /
    sum(kpi_master$num_of_trades, na.rm = TRUE),
  total_trade_days = sum(kpi_master$actual_trade_days, na.rm = TRUE),
  total_months     = dplyr::n_distinct(kpi_master$year_month_date)
)

# kpi_summary %>% glimpse() %>% view()

# master + summary を一緒にリスト保存
kpi_bundle <- list(
  detail  = kpi_master,
  summary = kpi_summary
)

# *kpi_datacheckpoint ----
save_checkpoint(kpi_bundle, "kpi", "kpi_master")

# ### パネル用関数 ----
# key_panel <- make_key_insights_panel(body_html)

# --- コメント追加用ブロック関数<make_text_block()を利用> ---
# rm(make_text_block)

key_panel <- make_text_block(
  kpi_text,
  family = "notojp",   # ← 定型のroboto ではなく notojp
  size_pt = 9,
  color = "black"
)

# key_panel

# 上段を合成（KPI + コメント）
# top_text_panel <- key_panel / comment_panel


# F) 最終レイアウト ----
# --- レイアウト合成 ---
# 分析の後でしか纏めは作成できないが、報告時点では上に持ってくるという逆転現象が生じる。
# panel_top <- key_panel / left_panel + plot_layout(heights = c(0.55, 2.45))
## F-1. Top_panel: Key Insights + Left_Center_panel ----

## key_panelを含めて配置する場合
## panel_top <- key_panel / left_center_right_panel + plot_layout(heights = c(0.55, 2.45))

## key_panel を除外して配置する場合
panel_top <- left_center_right_panel +
  plot_layout(heights = 1)


# panel_top <- (key_panel / comment_panel / left_center_panel) +
#   plot_layout(heights = c(0.3, 0.3, 2.4))
# class(panel_top)

## F-2. タイトル・キャプション追加 ----
# 関数を利用する場合
# panel_top <- add_title(panel_top, hdr = hdr)
# panel_top <- add_caption(panel_top)

# 日付文字列を生成
# --- 日付文字列 ---
asof_date <- format(Sys.Date(), "%B %d, %Y")  # e.g. "September 05, 2025"

# tile, subtitle
# make_title / make_caption を使って HTML 付きテキストを生成
hdr <- make_title(
  title    = "Investing Casually",
  subtitle = paste0("2025 YTD as of ", asof_date)
)

# caption
cap <- make_caption()  # 既存の関数を利用（フォント・色設定付き）

# patchwork にタイトル・サブタイトル・キャプションを適用
panel_top <- panel_top +
  plot_annotation(
    title    = hdr$title,
    subtitle = hdr$subtitle,
    caption  = cap,
    theme = theme(
      plot.title    = ggtext::element_markdown(hjust = 0.5, lineheight = 1.05), # left=0, center=0.5, right=1
      plot.subtitle = ggtext::element_markdown(hjust = 0.5, lineheight = 1.05), # left=0, center=0.5, right=1
      plot.caption  = ggtext::element_markdown(hjust = 1, lineheight = 1),
      plot.margin   = margin(t = 20, r = 10, b = 10, l = 10)  # 上に余白を追加
    )
  )

## F-3. 出力 ----
panel_top

# panel_top を即時プレビュー
library(ggview) #利用できない
# save_ggplot(panel_top, "my_plot.png")

# ggsave("onepager_top_keyinsights.png", panel_top, width = 12, height = 14, dpi = 300)

# **viz_checkpoint ----
# ▼目的：
#   ・完成版の panel_top を毎週履歴付きで保存
# ▼活用方法：
#   ・readRDS() + print() ですぐ再描画可能
save_viz_checkpoint(panel_top, "panel_top")

# **picture_checkpoint ----
# 04_output/report に保存
save_output_png(panel_top, "panel_top")

# --- パネル3: リスク ---
# risk_metrics <- make_risk_metrics(plot_df)

# risk_panel <- risk_metrics %>%
#   pivot_longer(everything(), names_to = "metric", values_to = "value") %>%
#   ggplot(aes(x = metric, y = value, fill = metric)) +
#   geom_col(show.legend = FALSE) +
#   geom_text(aes(label = round(value, 2)), vjust = -0.5) +
#   labs(
#     title = "Risk Indicators",
#     subtitle = paste("as of", format(end_date, "%B %d, %Y")),
#     x = NULL, y = NULL
#   ) +
#   theme_minimal(base_size = 14)
# 

# 1st_Column --- 
# 上段：Key Insights
# # 中段：収益性パネル (P2/P1)
# # 下段：リスクパネル
# panel_full <- key_panel / (P2 / P1) / risk_panel +
#   plot_layout(heights = c(0.5, 2, 1.2))
# 
# panel_full <- add_title(panel_full, hdr = hdr)
# panel_full <- add_caption(panel_full)


# Others ----
## Next Action note: ---- 
# シンプルにする：
# 月次集計時のKPIデータは元々のテーブルから引っ張る形式にして再計算する必要性はないようにした方が良い。
# 中央値なと統計的な集計を視覚的に評価しやすくする。So what?の状態をなくす事が大事。

# Center_panel:
## 期間指定して平均値など代表値を計算する。
## monthly_number of daysが必要。
## monthly_roi

# right_panel:
## 日次のデータをpythonで整理した後、そのデータでrisk panelを作成する。
## 日次分析の結果をプロットする。
## 或いは、月次として見に行きたいものにするか。
## 一旦月次データとしても良いかもしれない。


## EDA_Explorer_Data_Analysis ----
### 全体像 ----
### glimpse(merged_csv_data)
### skimr::skim(merged_csv_data)
### summary(merged_csv_data)

### library(summarytools)
### dfSummary(merged_csv_data) %>% tibble::view()
### dfSummary(merged_csv_data) %>% summarytools::view()

### 出現頻度 ----
### table(merged_csv_data$year_month)

# 
# library(explore)
# explore(merged_csv_data)

## Rstudioの動作確認 ----
# sessionInfo()
# # RStudioのバージョンを取得
# rstudioapi::versionInfo()$version
# # メモリ使用量の多いオブジェクト TOP10
# obj_sizes <- sort(sapply(ls(), function(x) object.size(get(x))), decreasing = TRUE)
# lapply(obj_sizes[1:10], format, units = "MB")
# 
# gc()  # Rが確保しているメモリと解放状況
# Rprof(tmp <- tempfile())
# # ここで普段の処理を実行
# Sys.sleep(2)  # 例
# Rprof()
# summaryRprof(tmp)$by.total[1:10, ]  # CPUを多く使っている関数トップ10
# 
# # install.packages("lobstr")
# library(lobstr)
# mem_used()   # 現在のメモリ使用量
# 
# # オブジェクトごとのサイズ
# obj_sizes <- sapply(ls(), function(x) obj_size(get(x)))
# sort(obj_sizes, decreasing = TRUE)[1:10]


# Quick-Check ----
# ts_monthly %>%
#   select(year_month, ttl_gain_realized_jpy) %>%
#   arrange(year_month)


# # API初期設定 ----
# library(httr2)
# notion_token <- Sys.getenv("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")  # .Renvironに保存しておく
# 
# req <- request("https://api.notion.com/v1/pages") %>%
#   req_headers(
#     "Authorization" = paste("Bearer", notion_token),
#     "Content-Type" = "application/json",
#     "Notion-Version" = "2022-06-28"
#   )



