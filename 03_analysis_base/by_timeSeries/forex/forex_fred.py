# %%
import os
import pandas as pd
from datetime import datetime
from pandas_datareader import data as web
from pandas.api.types import is_string_dtype
import tempfile
import shutil

# %%
# ================================
# ▼ パラメータ設定（柔軟な変更用）
# ================================
START_DATE = pd.Timestamp("2024-01-01")  # ← 必要に応じて変更可能
END_DATE = datetime.today()

# %%
# ▼ 入出力関連
BASE_DIR = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading"  # ← 必要に応じて変更可能
FOREX_DIR = os.path.join(BASE_DIR, "01_data", "macro_economy", "forex", "raw", "fred")  # ← 修正
os.makedirs(FOREX_DIR, exist_ok=True)
OUTPUT_PATH = os.path.join(FOREX_DIR, "usd_to_jpy_monthly_fred.csv")

# %%
# ▼ 環境変数パス（現状未使用ですが明示）
ENV_PATH = os.path.join(BASE_DIR, ".env")

# ================================
# ▼ 既存ファイルの読み込み処理
# ================================
if os.path.exists(OUTPUT_PATH):
    df_existing = pd.read_csv(OUTPUT_PATH, encoding="utf-8-sig")

    try:
        if is_string_dtype(df_existing["year_month"]):
            df_existing["year_month"] = pd.to_datetime(df_existing["year_month"], errors="coerce")
            df_existing = df_existing.dropna(subset=["year_month"])
            df_existing["year_month"] = df_existing["year_month"].dt.to_period("M")
    except Exception as e:
        print(f"❌ 'year_month'列の変換に失敗しました: {e}")
        df_existing = pd.DataFrame()
else:
    df_existing = pd.DataFrame()

# ================================
# ▼ FREDから為替データ取得
# ================================
try:
    df_fred = web.DataReader("DEXJPUS", "fred", START_DATE, END_DATE)
except Exception as e:
    print(f"❌ FREDからのデータ取得に失敗: {e}")
    raise

df_fred = df_fred.rename(columns={"DEXJPUS": "usd_to_jpy"})

# df_fred
#df_fred.loc["2025-08-01":"2025-09-26"]

# %%
# ================================
# ▼ 月次集計処理
# ================================
df_fred["year_month"] = df_fred.index.to_period("M")

monthly_stats = df_fred.groupby("year_month").agg(
    usd_to_jpy_avg=("usd_to_jpy", "mean"),
    usd_to_jpy_last=("usd_to_jpy", "last"),
    total_days=("usd_to_jpy", "size"),
    num_nans=("usd_to_jpy", lambda x: x.isna().sum()),
    valid_days=("usd_to_jpy", lambda x: x.notna().sum()),
    month_start=("usd_to_jpy", lambda x: x.index.min().date()),
    month_end=("usd_to_jpy", lambda x: x.index.max().date())
).reset_index()

# %%
# ▼ MoM変化率
monthly_stats["mom_change"] = monthly_stats["usd_to_jpy_avg"].pct_change() * 100
monthly_stats["mom_change"] = monthly_stats["mom_change"].round(2)

# ▼ 結合して重複削除
monthly_stats["year_month"] = monthly_stats["year_month"].astype(str)
if not df_existing.empty:
    df_existing["year_month"] = df_existing["year_month"].astype(str)
df_combined = (
    pd.concat([df_existing, monthly_stats])
    .drop_duplicates(subset="year_month", keep="last")   # ← ここを追加
    .sort_values("year_month")
    .reset_index(drop=True)
)
# df_combined

# ▼ 暫定値の自動補完（FREDがまだ更新していない今月のデータを前月値で埋める）
if not df_combined.empty:
    # 今月のYYYY-MMを計算
    current_month = pd.Timestamp.today().strftime("%Y-%m")
    # 既に今月の行が無ければ追加
    if current_month not in df_combined["year_month"].values:
        print(f"[INFO] 今月 {current_month} の行が存在しないため暫定行を追加します")
        df_combined = pd.concat([
            df_combined,
            pd.DataFrame([{"year_month": current_month,
                           "usd_to_jpy_avg": None,
                           "usd_to_jpy_last": None}])
        ], ignore_index=True)
        df_combined = df_combined.sort_values("year_month").reset_index(drop=True)

    # 前月の有効値を取得
    last_valid_avg = df_combined["usd_to_jpy_avg"].ffill().iloc[-2]  # 前月値
    last_valid_last = df_combined["usd_to_jpy_last"].ffill().iloc[-2]

    # 今月の行を埋める
    last_row = df_combined.iloc[-1]
    if pd.isna(last_row["usd_to_jpy_avg"]):
        print(f"[INFO] 今月 {last_row['year_month']} のFREDデータが未更新のため前月値で補完します")
        df_combined.loc[df_combined.index[-1], "usd_to_jpy_avg"] = last_valid_avg
        df_combined.loc[df_combined.index[-1], "usd_to_jpy_last"] = last_valid_last


# %%
# ================================
# ▼ 一時ファイル経由で保存
# ================================
with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding="utf-8-sig", newline="") as tmp:
    df_combined.to_csv(tmp.name, index=False)
    tmp_path = tmp.name

try:
    shutil.move(tmp_path, OUTPUT_PATH)
    print(f"✅ 為替データ保存完了: {OUTPUT_PATH}")
except PermissionError:
    print("❌ 保存に失敗：CSVファイルを閉じてから再実行してください。")

# %%
# ================================
# ▼ 最終結果の確認用
# ================================
print("\n" + "="*60)
print("最終データ確認")
print("="*60)
print(f"\nデータ形状: {df_combined.shape}")
print(f"\n最初の5行:")
print(df_combined.head())
print(f"\n最後の5行:")
print(df_combined.tail())
print(f"\n基本統計:")
print(df_combined.describe())

# インタラクティブウィンドウで確認したい場合は下記を実行
# df_combined  # ← この行でShift+Enterを押すとデータフレームが表示される

# df_combined

# %%
