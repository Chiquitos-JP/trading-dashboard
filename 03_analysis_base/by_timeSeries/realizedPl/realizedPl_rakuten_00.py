# %% 📚 ライブラリ
import pandas as pd
import os
from datetime import datetime
from glob import glob
import unicodedata  # ← 正規化用
import pandas_market_calendars as mcal

# %% 📁 パス設定
input_folder = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\01_data\trading_account\realized_pl\raw\rakuten"
output_folder = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\01_data\trading_account\realized_pl\processed"

# %% 📄 最新ファイル取得と読込
file_pattern = os.path.join(input_folder, "realized_pl(US)_*.csv")
matching_files = glob(file_pattern)

if not matching_files:
    raise FileNotFoundError(f"パターン '{file_pattern}' にマッチするファイルが見つかりません。")

input_file = max(matching_files, key=os.path.getctime)
print(f"📄 処理対象: {os.path.basename(input_file)}")
df = pd.read_csv(input_file, encoding="shift-jis")

# %% 🛠️ 列名の正規化（全角→半角、空白除去）
df.columns = [unicodedata.normalize('NFKC', col).strip() for col in df.columns]

# %% 🏷️ 列名変換（正規化後）
# 正規化後の列名に対応した rename_map（全角→半角 & 空白除去後）
# 信用取引のため、settlement、acquisition、contractに関する平均単価は定義をしておく必要性がある。売りから入る場合もあるため、sellingではなく、settlementとする。
rename_map = {
    "約定日": "contract_date",
    "受渡日": "settlement_date",
    "口座": "custody_type", #特定口座 or 一般口座
    "取引": "transaction_type", # 売付 or 売埋 or 買埋 or 現渡
    "ティッカーコード": "ticker",
    "銘柄名": "stock_name",
    "数量[株]": "num_of_shares",
    "売却/決済単価[USドル]":"avg_UnitPrice_settlement_usd",
    "売却/決済額[円]": "ttl_amt_settlement_jpy",
    "平均取得価額[円]": "avg_UnitCost_acquisition_jpy",
    "実現損益[円]": "ttl_gain_realized_jpy"
}
df = df.rename(columns=rename_map)

# %%
# ▼ 合計/小計行・空行を落とす（受渡日ベースでの集計を壊さないための前清掃）
#   - どこかのセルに「合計」「小計」「合計額」が含まれる
#   - かつ、約定日・受渡日に値がない（NaN or 空文字）
tot_pattern = r"(合計額|合計|小計)"

# 文字列化（NaN対策）
df_str = df.astype(str)

# 「合計/小計キーワード」を含む行。

mask_word = df_str.apply(lambda s: s.str.contains(tot_pattern, na=False)).any(axis=1)

# 約定日/受渡日の“実データが無い”行（空文字やNaNを除外）
def _is_blank(s):
    return s.isna() | (s.astype(str).str.strip() == "")

mask_no_dates = (
    _is_blank(df.get("contract_date")) &
    _is_blank(df.get("settlement_date"))
)

# ① 合計/小計っぽく、② 日付が無い → 完全に集計対象外
df = df.loc[~(mask_word & mask_no_dates)].copy()

# さらに保険：取引種別が無い行（合計行にありがち）も除外
df = df.loc[df["transaction_type"].notna()].copy()

# %% 🔢 数値変換
numeric_cols = ["num_of_shares","avg_UnitPrice_settlement_usd", "ttl_amt_settlement_jpy", "avg_UnitCost_acquisition_jpy", "ttl_gain_realized_jpy"]
df[numeric_cols] = df[numeric_cols].apply(lambda x: pd.to_numeric(x.astype(str).str.replace(",", ""), errors="coerce"))
df["avg_UnitPrice_settlement_usd"] = pd.to_numeric(df["avg_UnitPrice_settlement_usd"], errors="coerce")

# %% 📅 月次キー作成 & 対象取引抽出
"""
契約日ベース
df["contract_date"] = pd.to_datetime(df["contract_date"], errors="coerce")
df["year_month"] = df["contract_date"].dt.to_period("M").astype(str)
target_types = ["売付", "売埋", "買埋", "現渡"]
df_filtered = df[df["transaction_type"].isin(target_types)].copy()
"""
# NEW: 受渡日ベース
df["settlement_date"] = pd.to_datetime(df["settlement_date"], errors="coerce")
df["year_month"] = df["settlement_date"].dt.to_period("M").astype(str)

target_types = ["売付", "売埋", "買埋", "現渡"]
df_filtered = df[df["transaction_type"].isin(target_types)].copy()

# %% ✅ 取得総額の計算
df_filtered["ttl_cost_acquisition_jpy"] = df_filtered["ttl_amt_settlement_jpy"] - df_filtered["ttl_gain_realized_jpy"]

# %% 📊 実取引日数のカウント
# actual_trade_daysは、売買のいずれかが行われた日数をカウント
# Contract  days baseでOK
actual_trade_days_df = (
    df_filtered.dropna(subset=["contract_date"])
    .groupby("year_month")["contract_date"]
    .nunique()
    .reset_index()
    .rename(columns={"contract_date": "actual_trade_days"})
)

# %% 📊 月次集計 + 基本指標
monthly_summary = (
    df_filtered.groupby("year_month")
    .agg(
        # 取引回数、取扱銘柄数、株数
        num_of_trades=("transaction_type", "count"),
        num_of_symbols=("stock_name", "nunique"),
        num_of_shares=("num_of_shares", "sum"),
        # 平均単価（取得単価・売却単価）
        avg_UnitPrice_settlement_usd=("avg_UnitPrice_settlement_usd", "mean"),
        avg_UnitCost_acquisition_jpy=("avg_UnitCost_acquisition_jpy", "mean"),
        # 金額合計
        ttl_amt_settlement_jpy=("ttl_amt_settlement_jpy", "sum"),
        ttl_cost_acquisition_jpy=("ttl_cost_acquisition_jpy", "sum"),
        ttl_gain_realized_jpy=("ttl_gain_realized_jpy", "sum")
    )
    .reset_index()
    .assign(
        # 取引あたりの指標
        avg_amt_settlement_perTrade_jpy=lambda x: x["ttl_amt_settlement_jpy"] / x["num_of_trades"],
        avg_cost_acquisition_perTrade_jpy=lambda x: x["ttl_cost_acquisition_jpy"] / x["num_of_trades"],
        avg_gain_realized_perTrade_jpy=lambda x: x["ttl_gain_realized_jpy"] / x["num_of_trades"],
    )
)

# 実取引日数の統合
monthly_summary = pd.merge(monthly_summary, actual_trade_days_df, on="year_month", how="left")

# %% 月次の営業日数をカウント
# NYSE（米国株式市場）のカレンダーを取得
nyse = mcal.get_calendar('NYSE')

# 分析対象期間を取得
"""
min_date = df["contract_date"].min().replace(day=1)
max_date = df["contract_date"].max().replace(day=28) + pd.DateOffset(days=4)  # 月末を超えるため
max_date = max_date.replace(day=1)  # 翌月1日へ切り上げ
"""
# NEW: 受渡日ベースで期間を決定
min_date = df["settlement_date"].min().replace(day=1)
max_date = df["settlement_date"].max().replace(day=28) + pd.DateOffset(days=4)
max_date = max_date.replace(day=1)

# 月ごとの営業日（米国市場）
schedule = nyse.schedule(start_date=min_date, end_date=max_date)
schedule["year_month"] = schedule.index.to_series().dt.to_period("M").astype(str)

# 月別営業日数
market_days_df = schedule.groupby("year_month").size().reset_index(name="market_open_days")
# ▼ 追加（actual_trade_days_df の下あたり）
monthly_summary = pd.merge(monthly_summary, market_days_df, on="year_month", how="left")

# %% 日当たり指標を追加
monthly_summary = monthly_summary.assign(
    avg_gain_per_day_jpy=lambda x: x["ttl_gain_realized_jpy"] / x["actual_trade_days"],
    avg_num_of_trades_per_day=lambda x: x["num_of_trades"] / x["actual_trade_days"]
)

# %% 勝率（利益トレードの割合）
# = 実現利益がプラスの取引数 ÷ 実現利益プラスマイナスの合計取引数
win_rate_df = (
    df_filtered.assign(is_win=df_filtered["ttl_gain_realized_jpy"] > 0)
    .groupby("year_month")
    .agg(
        win_trades=("is_win", "sum"),
        total_trades=("is_win", "count")
    )
    .assign(win_rate=lambda x: x["win_trades"] / x["total_trades"])
    .reset_index()[["year_month", "win_rate"]]
)

monthly_summary = pd.merge(monthly_summary, win_rate_df, on="year_month", how="left")

# %% 財務的指標
monthly_summary = monthly_summary.assign(
    return_on_cost=lambda x: x["ttl_gain_realized_jpy"] / (x["num_of_shares"] * x["avg_UnitCost_acquisition_jpy"]),
    return_on_sales=lambda x: x["ttl_gain_realized_jpy"] / x["ttl_amt_settlement_jpy"]
    )

# %% シャープレシオ計算：日次損益の標準偏差（月次）
# 「どれだけ安定して利益を出せているか（＝収益の安定性）」を測る。
# 数値が高いほど、「リターン効率の良い（安定的な）」トレードができていることを意味します。
# Sharp Ratio = 日次平均利益 ÷ 日次平均利益の標準偏差（日次利益の平均的なバラつき＝リスクの大きさ）
"""
daily_returns = (
    df_filtered.groupby(["year_month", "contract_date"])["ttl_gain_realized_jpy"]
    .sum()
    .reset_index()
)
"""

# NEW: 受渡日で日次損益を作る
daily_returns = (
    df_filtered.groupby(["year_month", "settlement_date"])["ttl_gain_realized_jpy"]
    .sum().reset_index()
    .rename(columns={"settlement_date": "trade_date"})
)

monthly_std = (
    daily_returns.groupby("year_month")["ttl_gain_realized_jpy"]
    .std()
    .reset_index()
    .rename(columns={"ttl_gain_realized_jpy": "daily_gain_std"})
)
monthly_summary = pd.merge(monthly_summary, monthly_std, on="year_month", how="left")
monthly_summary["sharpe_ratio"] = monthly_summary["avg_gain_per_day_jpy"] / monthly_summary["daily_gain_std"]

# %% 追加指標
# 取引活動比率 = 実際の取引日数 ÷ 月の営業日数
monthly_summary = monthly_summary.assign(
    trading_activity_ratio=lambda x: x["actual_trade_days"] / x["market_open_days"]
)

# %% 列名の並び替え
# 推奨する並び順
ordered_columns = [
    # 🗓️ 日付キー
    "year_month",
    # 🗓️ 結果指標
    "ttl_gain_realized_jpy", 
    "win_rate",
    "avg_gain_realized_perTrade_jpy",
    "sharpe_ratio",
    # 📊 取引規模
    "num_of_trades", 
    "num_of_symbols", 
    # 🧮 成果指標
    "return_on_cost", 
    "return_on_sales", 
    # 💴 金額合計
    "ttl_amt_settlement_jpy", 
    "ttl_cost_acquisition_jpy",
    # 📈 単価平均
    "avg_UnitPrice_settlement_usd", 
    "avg_UnitCost_acquisition_jpy",
    # 📏 1取引あたり指標
    "avg_amt_settlement_perTrade_jpy", 
    "avg_cost_acquisition_perTrade_jpy", 
    # 📆 日数
    "actual_trade_days", 
    "market_open_days",
    # ⏱️ 日次効率性
    "avg_gain_per_day_jpy", 
    "avg_num_of_trades_per_day",
    # その他
    "num_of_shares"
]

# 列の並び替えを適用
monthly_summary = monthly_summary[ordered_columns]


# %% 💾 保存
today = datetime.today().strftime("%Y%m%d")
dated_folder = os.path.join(output_folder, f"realizedPl_{today}")
os.makedirs(dated_folder, exist_ok=True)
output_path = os.path.join(dated_folder, f"rakuten_monthly_summary_en_{today}.csv")
monthly_summary.to_csv(output_path, index=False, encoding="utf-8-sig")
print(f"✅ 保存完了: {output_path}")

# %%

# 📋 列名の確認
print(monthly_summary.columns.tolist())

"""
#
# Assumptions
    'year_month', 
    'actual_trade_days', #実際に片側のトレードをした日数
    'num_of_trades', 
    'num_of_symbols',
    'num_of_operational_days' #営業日数

# Factual_Trade_Information
    'quantity', 
    'unitPrice_settlement_usd'
    'avg_acquisition_cost_jpy'

# Financial_Indicators
## Settlement_Amounts_Gains_or_Losses
    'ttl_amt_settlement_jpy',
    'acquisition_total_jpy',
    'ttl_gain_realized_jpy',

## Unit_Economics
### per_Trade
    'settlement_amt_perTrade',
    (settlement_amt_perTrade =lambda x: x["quantity"] / x["num_of_trades"]) 
    'gain_per_trade', 
    'gain_per_share', 

### per_Day
    'avg_gain_per_day_jpy', 
    'avg_num_of_trades_per_day', 
    'gross_volume_per_day_jpy', 

###
    'win_rate',
    'return_on_cost', 
    'return_on_sales', 
    'gross_profit_margin', 
    'daily_gain_std', 
    'sharpe_ratio'

win rate = (number of winning trades) / (total number of trades)
・Win rateを改善するためには、①分母を小さくする、②分子を大きくする、のいずれか。
・分母を小さくするのは、具体的には、負けているトレードを減らすこと。
・仮にそれが出来れば、分子は結果的に大きくなる。
・勝率の深堀は、銘柄別分析の際に深堀を行う。原因分析を実施するには、銘柄別情報が必要になるため。

## note
## Profitability_ratio (PL÷PL)
(Net Income / Sales)

## Activity_ratio (PL÷BS)
(Sales / Total Assets)

## Solvency_ratio (BS÷BS)
(Total Assets / Shareholder’s equity)

ROE = (Net Income / Sales) × (Sales / Total Assets) × (Total Assets / Shareholder’s equity)
ROE = Profitability_ratio × Activity_ratio × Solvency_ratio
"""