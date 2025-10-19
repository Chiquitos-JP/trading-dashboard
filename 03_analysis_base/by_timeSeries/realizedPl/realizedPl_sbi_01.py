# %% 📦 ライブラリの読み込み
import pandas as pd
import os
from glob import glob

# %% 📁 パス設定
sbi_folder = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\01_data\trading_account\realized_pl\processed"
forex_folder = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\01_data\macro_economy\forex\raw\fred"  # FREDデータを使用
today = pd.Timestamp.today().strftime('%Y%m%d')
dated_folder = os.path.join(sbi_folder, f"realizedPl_{today}")
os.makedirs(dated_folder, exist_ok=True)  # 既存なら流用、なければ作成

# %% 🔍 最新ファイルの読み込み（処理日付フォルダ優先で検索）
# 1) 当日フォルダ > 2) 任意の日付フォルダ > 3) ルート直下（後方互換）
sbi_search_patterns = [
    os.path.join(dated_folder, "sbi_monthly_summary_en_*.csv"),
    os.path.join(sbi_folder, "realizedPl_*", "sbi_monthly_summary_en_*.csv"),
    os.path.join(sbi_folder, "sbi_monthly_summary_en_*.csv"),
]

sbi_files = []
for p in sbi_search_patterns:
    sbi_files.extend(glob(p))

if not sbi_files:
    patterns_str = " | ".join(sbi_search_patterns)
    raise FileNotFoundError(f"SBI月次ファイルが見つかりませんでした。検索パターン: {patterns_str}")

sbi_file = max(sbi_files, key=os.path.getctime)
print(f"[INFO] 最新のSBI月次ファイル: {sbi_file}")

fx_pattern = os.path.join(forex_folder, "*.csv")
fx_files = glob(fx_pattern)

if not fx_files:
    raise FileNotFoundError(f"パターン '{fx_pattern}' にマッチするファイルが見つかりません。")

fx_file = max(fx_files, key=os.path.getctime)
print(f"[INFO] 最新の為替ファイル: {fx_file}")

# %% 📄 CSVの読み込み
df_sbi = pd.read_csv(sbi_file, encoding="utf-8-sig")
df_fx = pd.read_csv(fx_file, encoding="utf-8-sig")

# %% 🔧 year_month の形式統一
df_sbi["year_month"] = pd.to_datetime(
    df_sbi["year_month"],
    errors="coerce",
    format="mixed"  # ★混在に対応
).dt.strftime("%Y-%m")

df_fx["year_month"] = pd.to_datetime(
    df_fx["year_month"],
    errors="coerce"
).dt.strftime("%Y-%m")

# チェック
# print(df_sbi["year_month"].unique())
# print(df_fx["year_month"].unique())

# %% 🚫 通貨列削除
if "currency" in df_sbi.columns:
    df_sbi = df_sbi.drop(columns=["currency"])

# %% 🔁 USD列を "_usd" にリネーム（SBI新フォーマット対応）
usd_cols = [
    "avg_UnitPrice_settlement", 
    "avg_UnitCost_acquisition",
    "ttl_gain_realized",
    "ttl_amt_settlement",
    "ttl_cost_acquisition", 
    "contract_UnitPrice", 
    "fees", 
    "new_order_fee", 
    "settlement_fee", 
    "interest", 
    "stock_lending_fee",
    "management_fee", 
    "rights_processing_fee", 
    "avg_gain_realized_perTrade",
    "avg_amt_settlement_perTrade",
    "avg_cost_acquisition_perTrade",
    "avg_gain_per_day"
]
rename_map = {
    col: f"{col}_usd"
    for col in usd_cols
    if f"{col}_usd" in df_sbi.columns or col in df_sbi.columns
}
df_sbi = df_sbi.rename(columns=rename_map)

# %% 🔄 為替情報マージ
df_merged = pd.merge(
    df_sbi,
    df_fx[["year_month", 
           "usd_to_jpy_avg", 
           "usd_to_jpy_last"]],
    on="year_month",
    how="left"
)

# %% ⚙️ 適用為替レートの設定
fx_type_to_apply = "avg"  # ← "last" にすれば月末適用

if fx_type_to_apply == "avg":
    df_merged["applied_fx_rate"] = df_merged["usd_to_jpy_avg"]
elif fx_type_to_apply == "last":
    df_merged["applied_fx_rate"] = df_merged["usd_to_jpy_last"]
else:
    raise ValueError("❌ fx_type_to_apply は 'avg' または 'last' のいずれかにしてください。")

# %% 💴 円建て列の追加
for col in rename_map.values():
    if col in df_merged.columns:
        jpy_col = col.replace("_usd", "_jpy")
        df_merged[jpy_col] = df_merged[col] * df_merged["applied_fx_rate"]

# %% 💾 保存（処理日付フォルダへ格納）
output_path = os.path.join(
    dated_folder,
    f"sbi_monthly_summary_with_fx_applied_{today}.csv"
)
df_merged.to_csv(output_path, index=False, encoding="utf-8-sig")
print(f"[SUCCESS] 円転結果を保存しました: {output_path}")

# df_merged
# df_merged[["year_month", "usd_to_jpy_avg", "applied_fx_rate"]].tail()

# ====
# debug
# print(df_sbi["year_month"].unique())
# print(df_fx["year_month"].unique())
# print(df_merged[["year_month", "usd_to_jpy_avg", "usd_to_jpy_last"]].head(10))
# print(df_merged[["year_month", "usd_to_jpy_avg", "usd_to_jpy_last"]].tail(10))
# print(df_fx.columns)

# %%
