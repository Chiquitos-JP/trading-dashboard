
# B) プロジェクト別のユニーク設定 ----
## B-1. NYSEのカレンダー取得 ----
##（bizdays::load_quantlib_calendars("UnitedStates/NYSE")）

# 期間を変数で設定
calendar_from <- as.Date("2000-01-01")
calendar_to   <- as.Date("2100-12-31")


# CRAN の RQuantLib バイナリは x64（Intel/AMD）向けです。
# Windows ARM64（Snapdragon 等）用は提供されていません。
# そのため ARM64 の R では読み込みに失敗します（今回のエラーの原因）。

# # カレンダーのロード
# bizdays::load_quantlib_calendars(
#   "UnitedStates/NYSE",
#   from = calendar_from,
#   to   = calendar_to
# )
# 
# # 実際に登録されているカレンダー名は、bizdays::calendars()で確認。
# NYSE_CAL <- "QuantLib/UnitedStates/NYSE"

#### 営業日数を返す関数 ----
# 年月文字列を安全に日付化するユーティリティ
# nyse_open_days <- function(ym) {
#   d0 <- as.Date(paste0(ym, "-01")) # 月初＝ym+_01で定義
#   d1 <- ceiling_date(d0, "month") - days(1) # 月末 = 翌月-1で定義
#   length(bizdays::bizseq(d0, d1, NYSE_CAL)) #（月初、月末、基本とするカレンダー）は営業日の要素を全て取り出して並べる処理を行う。lengthはそれをカウントする。
# }

# timeDate から NYSE の祝日を作って bizdays のカレンダーとして登録
suppressPackageStartupMessages({
  library(bizdays)
  library(lubridate)
  library(timeDate)
})

# --- 既存 "QuantLib/UnitedStates/NYSE" を安全に削除 ---
target_cal <- "QuantLib/UnitedStates/NYSE"

cal_raw <- try(bizdays::calendars(), silent = TRUE)
cal_names <- character()

if (!inherits(cal_raw, "try-error") && !is.null(cal_raw)) {
  if (is.environment(cal_raw)) {
    cal_names <- ls(cal_raw, all.names = TRUE)      # ← ここがポイント
  } else if (is.character(cal_raw)) {
    cal_names <- cal_raw
  } else if (is.list(cal_raw)) {
    cal_names <- names(cal_raw)
    if (is.null(cal_names)) cal_names <- unlist(cal_raw, use.names = FALSE)
  } else {
    suppressWarnings(cal_names <- as.character(cal_raw))
    cal_names <- cal_names[!is.na(cal_names)]
  }
}

if (length(cal_names) && target_cal %in% cal_names) {
  try(bizdays::remove.calendar(target_cal), silent = TRUE)
}

# --- RQuantLib なしで NYSE カレンダーを自作（timeDate 由来の祝日） ---
# 期間は既存変数 calendar_from / calendar_to をそのまま利用
yrs <- seq(lubridate::year(calendar_from), lubridate::year(calendar_to))
nyse_holidays <- as.Date(timeDate::holidayNYSE(yrs))
nyse_holidays <- sort(unique(nyse_holidays[!is.na(nyse_holidays)]))

bizdays::create.calendar(
  name        = target_cal,
  holidays    = nyse_holidays,
  weekdays    = c("saturday", "sunday"),
  adjust.from = "next",
  adjust.to   = "previous",
  financial   = TRUE
)

# 動作チェック（例）
# bizdays::is.bizday(as.Date("2025-01-01"), target_cal)  # → FALSE(祝日) ならOK
# bizdays::bizdays(as.Date("2025-01-02"), as.Date("2025-01-10"), target_cal)

# 実際に登録されているカレンダー名は、bizdays::calendars()で確認。
NYSE_CAL <- "QuantLib/UnitedStates/NYSE"

# 営業日数関数（文字列フォーマットを気にせずOK）
nyse_open_days <- function(ym) {
  ym <- trimws(as.character(ym))
  d0 <- suppressWarnings(
    lubridate::parse_date_time(ym, orders = c("b-y","b-Y","Y-m"), tz = "UTC")
  )
  if (is.na(d0)) return(NA_integer_)
  d0 <- as.Date(lubridate::floor_date(d0, "month"))
  d1 <- as.Date(lubridate::ceiling_date(d0, "month") - lubridate::days(1))
  all_days <- seq(d0, d1, by = "day")
  wd <- lubridate::wday(all_days, week_start = 1)
  weekdays_only <- all_days[wd %in% 1:5]
  yrs <- seq(lubridate::year(d0), lubridate::year(d1))
  nyse_holidays <- as.Date(timeDate::holidayNYSE(yrs))
  biz <- setdiff(weekdays_only, nyse_holidays)
  length(biz)
}

# 複数の年月をまとめて処理するベクトル版
nyse_open_days_vec <- function(ym_chr) {
  vapply(ym_chr, nyse_open_days, integer(1L))
}

## B-2. 時系列Simulation ----
# 関数: make_month_template
# 概要:
#   可視化や時系列分析で使うための「月ごとのテンプレート日付」を作成します。
#   - mode = "by_year"    : 任意の基準年から、指定年数分（= years × 12ヶ月）を生成
#   - mode = "after_last" : 実データの最終月の “翌月” から未来の月を生成
#       * end_year を指定      → その年の12月までを自動生成
#       * end_year を未指定    → months_ahead ヵ月分を生成
#
# 引数:
#   mode            : "by_year" または "after_last"（必須）
#   year_base       : 基準年（by_year 用、例: 2025）
#   years           : 生成する年数（by_year 用、例: 2 → 2年=24ヶ月）
#   months_ahead    : 未来に何ヵ月作るか（after_last 用、end_year 未指定時に使用）
#   last_year_month : 最終年月を手動指定（例: "2025-08"）。未指定なら data から自動検出
#   end_year        : 未来の終端年（例: 2026）。指定時はその年の12月まで生成
#   data            : 実データのデータフレーム（after_last で自動検出する場合に使用）
#   ym_col          : 実データの年月カラム名（既定: "year_month", "YYYY-MM" 文字列想定）
#
# 挙動の注意:
#   - after_last で last_year_month を省略した場合、data[[ym_col]] の最大値を最終月として採用
#   - end_year 指定時、開始（最終月の翌月）が end_year-12-01 より後なら、空のテンプレを返す
#
# 戻り値（tibble）:
#   year_month_date : 月初日の Date（例: 2025-09-01）
#   year_month      : "YYYY-MM" 形式の文字列（例: "2025-09"）
#   is_future       : 未来行フラグ（本関数の出力は TRUE 固定。実データ結合後に上書き可）

# # ダミーデータ（最終月が 2025-08 と仮定）
# dummy <- tibble(year_month = c("2025-06","2025-07","2025-08"))
# 
# # A) 自動で最新月を認知し、2026年末までを作る
# tmpl_until_2026 <- make_month_template(
#   mode = "after_last",
#   end_year = 2026,
#   data = dummy, ym_col = "year_month"
# )
# print(tmpl_until_2026)
# 
# # B) 自動で最新月を認知し、先12ヵ月だけ作る（従来挙動）
# tmpl_next12 <- make_month_template(
#   mode = "after_last",
#   months_ahead = 12,
#   data = dummy, ym_col = "year_month"
# )
# print(tmpl_next12)
# 
# # C) by_year で 2025年〜2026年の2年分を作る
# tmpl_2025_2026 <- make_month_template(
#   mode = "by_year",
#   year_base = 2025,
#   years = 2
# )
# print(tmpl_2025_2026)

# データの最終月を自動認識し、2026年3月まで（終了月を指定）
# tmpl_auto_to_mar26 <- make_month_template(
#   mode = "after_last",
#   end_ym = "2026-03",
#   data = ts_monthly, ym_col = "year_month"
# )
# 
# # by_year: 2025年開始で、2026年03月まで
# tmpl_2025_to_mar26 <- make_month_template(
#   mode = "by_year",
#   year_base = 2025,
#   end_ym = "2026-03"
# )

## 月のパース（ISO形式や Jan-24 形式をまとめて解釈）
# 月のパース（ベクトル入力OK・安全）
safe_parse_month <- function(x) {
  x <- stringr::str_trim(as.character(x))
  x <- stringr::str_replace_all(x, "\u3000", " ")   # 全角スペース→半角
  
  # "202401" → "2024-01" に正規化（ここはベクトル演算にする）
  idx <- !is.na(x) & nchar(x) == 6 & grepl("^\\d{6}$", x)
  x[idx] <- paste0(substr(x[idx], 1, 4), "-", substr(x[idx], 5, 6))
  
  d <- suppressWarnings(lubridate::parse_date_time(
    x, orders = c("Y-m", "b-y", "b-Y"), tz = "UTC"
  ))
  as.Date(lubridate::floor_date(d, "month"))
}

# 動作チェック
# safe_parse_month(c("2024-01", "Jan-24", "Jan-2024", "202401", NA))

# ISO（YYYY-MM）文字列に変換（ベクトル対応）
to_ym_iso <- function(d) {
  d <- if (inherits(d, "Date")) d else safe_parse_month(d)
  format(d, "%Y-%m")
}

# 動作チェック
# to_ym_iso(c("2024-01", "Jan-24", "202401"))


# 未来の月テンプレを作るユーティリティ
# 優先度: end_ym（YYYY-MM） > end_year > months_ahead
# ▼ 月テンプレ生成（将来シミュレーション用）
make_month_template <- function(mode = c("after_last", "full"),
                                end_ym,
                                data,
                                ym_col = "year_month") {
  mode <- match.arg(mode)
  
  # 既存データの年月をパース
  ym_vec   <- data[[ym_col]]
  ym_dates <- safe_parse_month(ym_vec)
  
  if (all(is.na(ym_dates))) {
    stop("既存データの `", ym_col, "` を月として解釈できません。")
  }
  
  start_month <- min(ym_dates, na.rm = TRUE)
  last_month  <- max(ym_dates, na.rm = TRUE)
  
  # 終了月
  end_month <- safe_parse_month(end_ym)
  if (is.na(end_month)) stop("`end_ym` を月として解釈できません: ", end_ym)
  
  from <- if (mode == "after_last") last_month %m+% months(1) else start_month
  
  # from > end のときは空 tibble を返す
  if (from > end_month) {
    return(tibble::tibble(
      year_month      = character(0),
      year_month_date = as.Date(character(0))
    ))
  }
  
  seq_months <- seq(from, end_month, by = "month")
  tibble::tibble(
    year_month      = format(seq_months, "%Y-%m"),  # ISO表記
    year_month_date = as.Date(seq_months)           # Date型（月初）
  )
}
