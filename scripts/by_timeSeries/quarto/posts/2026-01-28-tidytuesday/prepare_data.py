"""
TidyTuesday用データ準備スクリプト

daily_balance.parquetから月末データを抽出し、
data/monthly_balance.parquetとして保存する。

使用方法:
    cd scripts/by_timeSeries/quarto/posts/2026-01-28-tidytuesday
    python prepare_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

# プロジェクトルートを探す（stockTradingフォルダ）
base_path = Path(__file__).resolve().parent
while base_path.name != "05_stockTrading" and base_path.parent != base_path:
    base_path = base_path.parent

# フォールバック: dataフォルダを探す
if not (base_path / "data").exists():
    base_path = Path(__file__).resolve()
    while not (base_path / "data" / "trading_account").exists() and base_path.parent != base_path:
        base_path = base_path.parent

print(f"Project root: {base_path}")

# データファイルのパス
balance_file = base_path / "data" / "trading_account" / "account_balance" / "daily_balance.parquet"

if not balance_file.exists():
    print(f"ERROR: {balance_file} not found")
    print("Please run 'python run_all.py' first to generate the data.")
    exit(1)

# データ読み込み
print(f"Loading: {balance_file}")
daily_balance = pd.read_parquet(balance_file)
daily_balance['date'] = pd.to_datetime(daily_balance['date'])

print(f"Loaded {len(daily_balance)} daily records")

# 月末データを抽出
daily_balance['year_month'] = daily_balance['date'].dt.to_period('M').astype(str)

month_end = daily_balance.groupby(['year_month', 'broker']).apply(
    lambda x: x.loc[x['date'].idxmax()],
    include_groups=False
).reset_index()

# 必要なカラムのみ選択
output_cols = ['date', 'broker', 'pat_balance', 'exposure', 'exposure_ratio']
if 'exposure_ratio' not in month_end.columns:
    month_end['exposure_ratio'] = np.where(
        month_end['pat_balance'] != 0,
        month_end['exposure'] / np.abs(month_end['pat_balance']) * 100,
        np.nan
    )

# 存在するカラムのみフィルタ
available_cols = [c for c in output_cols if c in month_end.columns]
month_end = month_end[available_cols]

print(f"Extracted {len(month_end)} month-end records")
print(f"Date range: {month_end['date'].min().date()} to {month_end['date'].max().date()}")
print(f"Brokers: {month_end['broker'].unique().tolist()}")

# 出力ディレクトリ作成
output_dir = Path(__file__).parent / "data"
output_dir.mkdir(parents=True, exist_ok=True)

# 保存
output_file = output_dir / "monthly_balance.parquet"
month_end.to_parquet(output_file, index=False)
print(f"\nSaved: {output_file}")

# 確認用にCSVも出力（オプション）
csv_file = output_dir / "monthly_balance.csv"
month_end.to_csv(csv_file, index=False)
print(f"Saved: {csv_file}")

print("\n=== Data Preview ===")
print(month_end.tail(10).to_string())

print("\n✅ Data preparation complete!")
print("Now you can render the TidyTuesday post with GitHub Actions.")
