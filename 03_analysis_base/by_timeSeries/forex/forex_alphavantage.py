# %%
import os
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
from io import StringIO

# %%
# ▼ .env ファイル読み込み（APIキー取得）
env_path = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\.env"
load_dotenv(env_path)

api_key = os.getenv("ALPHAVANTAGE_API_KEY")
if not api_key:
    raise ValueError("❌ .envからALPHAVANTAGE_API_KEYが取得できませんでした。")

# ▼ 期間設定
start_date = pd.to_datetime("2024-01-01")
end_date = pd.to_datetime(datetime.today().date())

# ▼ APIリクエスト（CSV形式）
url = (
    f"https://www.alphavantage.co/query?"
    f"function=FX_DAILY&from_symbol=USD&to_symbol=JPY"
    f"&outputsize=full&datatype=csv&apikey={api_key}"
)
response = requests.get(url)
response.encoding = "utf-8"

# ▼ データFrame変換
df = pd.read_csv(StringIO(response.text))
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.rename(columns={"timestamp": "date", "close": "usd_to_jpy"})

# ▼ フィルタ：日付範囲で抽出
df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# ▼ 月次集計
df["year_month"] = df["date"].dt.to_period("M")

monthly = df.groupby("year_month").agg(
    usd_to_jpy_avg=("usd_to_jpy", "mean"),
    usd_to_jpy_last=("usd_to_jpy", "last"),
    total_days=("usd_to_jpy", "size"),
    valid_days=("usd_to_jpy", lambda x: x.notna().sum()),
    month_start=("date", "min"),
    month_end=("date", "max")
).reset_index()

# ✅ year_month を "yyyy/m/d" 形式の文字列（例: 2024/1/1）に変換
monthly["year_month"] = monthly["year_month"].dt.to_timestamp().dt.strftime("%Y/%#m/%#d")

monthly["mom_change"] = monthly["usd_to_jpy_avg"].pct_change() * 100
monthly["mom_change"] = monthly["mom_change"].round(2)

# ▼ 保存フォルダとファイル名（変数で管理）
output_folder = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\01_data\macro_economy\processed\forex"
output_filename = "usd_to_jpy_monthly_alphavantage.csv"
output_path = os.path.join(output_folder, output_filename)

# ▼ 保存
os.makedirs(output_folder, exist_ok=True)
monthly.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"✅ 為替月次データを保存しました: {output_path}")

# %%
