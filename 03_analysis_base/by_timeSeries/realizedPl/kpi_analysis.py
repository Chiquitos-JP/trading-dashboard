# %% 📚 ライブラリ
import pandas as pd
import numpy as np
import os
from datetime import datetime, date
from glob import glob
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定（必要に応じて）
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# %% 📁 パス設定
today_str = datetime.today().strftime('%Y%m%d')
realized_pl_folder = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\01_data\trading_account\realized_pl"
processed_folder = os.path.join(realized_pl_folder, "processed")
dated_folder = os.path.join(processed_folder, f"realizedPl_{today_str}")
output_folder = os.path.join(r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\04_output", "figures")
checkpoint_folder = os.path.join(realized_pl_folder, "checkpoints")

# フォルダ作成
os.makedirs(output_folder, exist_ok=True)
os.makedirs(checkpoint_folder, exist_ok=True)

# %% A) データ読込
print("=" * 60)
print("A) データ読込")
print("=" * 60)

# %% A-1. 最新のmergedファイルを取得
merged_pattern = os.path.join(dated_folder, "merged_trading_summary_*.csv")
merged_files = glob(merged_pattern)

if not merged_files:
    # dated_folder になければ、過去の日付フォルダを検索
    fallback_pattern = os.path.join(processed_folder, "realizedPl_*", "merged_trading_summary_*.csv")
    merged_files = glob(fallback_pattern)

if not merged_files:
    raise FileNotFoundError(f"merged_trading_summary_*.csv が見つかりません。")

merged_file = max(merged_files, key=os.path.getctime)
print(f"📄 読込ファイル: {os.path.basename(merged_file)}")

# データ読込
df = pd.read_csv(merged_file, encoding="utf-8-sig")
df['source_file'] = os.path.basename(merged_file)

print(f"✅ データ形状: {df.shape}")
print(f"✅ 列名: {list(df.columns)}")

# %% B) データ整形
print("\n" + "=" * 60)
print("B) データ整形")
print("=" * 60)

# %% B-1. 年月列の整形
# year_monthを整形（前後の空白削除、ISO形式に変換）
df['year_month'] = df['year_month'].str.strip()

# year_month_isoを作成（ISO形式: YYYY-MM）
def parse_year_month(ym_str):
    """年月文字列を解析してDate型に変換"""
    if pd.isna(ym_str):
        return pd.NaT
    try:
        # YYYY-MM形式
        return pd.to_datetime(ym_str, format='%Y-%m')
    except:
        try:
            # Jan-24形式など
            return pd.to_datetime(ym_str, format='%b-%y')
        except:
            return pd.NaT

df['year_month_date'] = df['year_month'].apply(parse_year_month)
df['year_month_iso'] = df['year_month_date'].dt.strftime('%Y-%m')

print(f"✅ 年月範囲: {df['year_month_iso'].min()} 〜 {df['year_month_iso'].max()}")

# %% *checkpoint_1: 生データ保存
checkpoint_path = os.path.join(checkpoint_folder, f"01_raw_import_{today_str}.parquet")
df.to_parquet(checkpoint_path, engine='pyarrow', compression='snappy', index=False)
print(f"💾 Checkpoint 1 保存: {checkpoint_path}")

# %% B-2. NYSE営業日数の計算
print("\n--- NYSE営業日数計算 ---")

# pandas_market_calendarsを使用してNYSE営業日を計算
try:
    import pandas_market_calendars as mcal
    
    def calculate_nyse_days(year_month_iso):
        """指定月のNYSE営業日数を計算"""
        if pd.isna(year_month_iso):
            return np.nan
        
        try:
            ym_date = pd.to_datetime(year_month_iso + "-01")
            end_date = ym_date + pd.offsets.MonthEnd(0)
            
            nyse = mcal.get_calendar("NYSE")
            schedule = nyse.schedule(start_date=ym_date, end_date=end_date)
            return len(schedule)
        except:
            return np.nan
    
    # ユニークな年月リストを取得
    unique_months = df[['year_month_iso', 'year_month']].drop_duplicates()
    unique_months['market_open_days_cal'] = unique_months['year_month_iso'].apply(calculate_nyse_days)
    
    print(f"✅ {len(unique_months)}ヶ月分の営業日数を計算")
    
except ImportError:
    print("⚠️ pandas_market_calendarsがインストールされていません。")
    print("   代替として、月の営業日数を21日と仮定します。")
    unique_months = df[['year_month_iso', 'year_month']].drop_duplicates()
    unique_months['market_open_days_cal'] = 21

# データに結合
df = df.merge(unique_months[['year_month_iso', 'market_open_days_cal']], 
              on='year_month_iso', how='left')

# market_open_daysカラムがあれば統合、なければcalを使用
if 'market_open_days' in df.columns:
    df['market_open_days'] = df['market_open_days'].fillna(df['market_open_days_cal'])
else:
    df['market_open_days'] = df['market_open_days_cal']

df = df.drop(columns=['market_open_days_cal'], errors='ignore')

print(f"✅ 営業日数を結合")

# %% *checkpoint_2: 営業日数結合後
checkpoint_path = os.path.join(checkpoint_folder, f"02_merged_with_mdays_{today_str}.parquet")
df.to_parquet(checkpoint_path, engine='pyarrow', compression='snappy', index=False)
print(f"💾 Checkpoint 2 保存: {checkpoint_path}")

# %% C) 月次集計
print("\n" + "=" * 60)
print("C) 月次集計")
print("=" * 60)

# %% C-1. broker無視の月次集計
# 勝ち件数を計算（各brokerの win_rate × num_of_trades の合計）
df['num_of_win_trades'] = (df['win_rate'] * df['num_of_trades']).fillna(0)

# 月次で集計
ts_monthly = df.groupby('year_month_iso').agg({
    'ttl_gain_realized_jpy': 'sum',
    'num_of_win_trades': lambda x: round(x.sum()),  # 勝ち件数
    'num_of_trades': 'sum',
    'ttl_amt_settlement_jpy': 'sum',
    'ttl_cost_acquisition_jpy': 'sum',
    'actual_trade_days': 'max',  # 月内の最大値
    'market_open_days': 'first'  # 同月は同値
}).reset_index()

# 月次勝率を再計算
ts_monthly['win_rate'] = np.where(
    ts_monthly['num_of_trades'] > 0,
    ts_monthly['num_of_win_trades'] / ts_monthly['num_of_trades'],
    np.nan
)

# 取引あたり実現損益
ts_monthly['avg_gain_realized_per_trade_jpy'] = np.where(
    ts_monthly['num_of_trades'] > 0,
    ts_monthly['ttl_gain_realized_jpy'] / ts_monthly['num_of_trades'],
    np.nan
)

# リターン率
ts_monthly['return_on_cost'] = np.where(
    ts_monthly['ttl_cost_acquisition_jpy'] > 0,
    ts_monthly['ttl_gain_realized_jpy'] / ts_monthly['ttl_cost_acquisition_jpy'],
    np.nan
)

ts_monthly['return_on_sales'] = np.where(
    ts_monthly['ttl_amt_settlement_jpy'] > 0,
    ts_monthly['ttl_gain_realized_jpy'] / ts_monthly['ttl_amt_settlement_jpy'],
    np.nan
)

# 日あたり指標
ts_monthly['avg_gain_per_day_jpy'] = np.where(
    ts_monthly['actual_trade_days'] > 0,
    ts_monthly['ttl_gain_realized_jpy'] / ts_monthly['actual_trade_days'],
    np.nan
)

ts_monthly['avg_num_of_trades_per_day'] = np.where(
    ts_monthly['actual_trade_days'] > 0,
    ts_monthly['num_of_trades'] / ts_monthly['actual_trade_days'],
    np.nan
)

# year_month_dateを追加
ts_monthly['year_month_date'] = pd.to_datetime(ts_monthly['year_month_iso'] + '-01')

# 人間向けラベルを追加（元のyear_monthから取得）
month_labels = df[['year_month_iso', 'year_month']].drop_duplicates()
ts_monthly = ts_monthly.merge(month_labels, on='year_month_iso', how='left')

# 列順を整理
cols_order = [
    'year_month_iso', 'year_month', 'year_month_date',
    'ttl_cost_acquisition_jpy', 'ttl_gain_realized_jpy',
    'num_of_win_trades', 'win_rate', 'avg_gain_realized_per_trade_jpy',
    'num_of_trades', 'actual_trade_days', 'market_open_days',
    'avg_gain_per_day_jpy', 'avg_num_of_trades_per_day',
    'return_on_cost', 'return_on_sales'
]

# 存在する列のみ選択
available_cols = [c for c in cols_order if c in ts_monthly.columns]
ts_monthly = ts_monthly[available_cols]

# 日付順にソート
ts_monthly = ts_monthly.sort_values('year_month_date').reset_index(drop=True)

print(f"✅ 月次集計完了: {len(ts_monthly)}行")
print(f"   期間: {ts_monthly['year_month_iso'].iloc[0]} 〜 {ts_monthly['year_month_iso'].iloc[-1]}")

# %% *checkpoint_3: 月次集計
checkpoint_path = os.path.join(checkpoint_folder, f"03_ts_monthly_{today_str}.parquet")
ts_monthly.to_parquet(checkpoint_path, engine='pyarrow', compression='snappy', index=False)
print(f"💾 Checkpoint 3 保存: {checkpoint_path}")

# %% C-2. 将来テンプレート作成（2026-12まで）
print("\n--- 将来テンプレート作成 ---")

# 最終月を取得
last_month = ts_monthly['year_month_date'].max()
end_month = pd.to_datetime('2026-12-01')

# 将来の月リストを生成
future_months = pd.date_range(
    start=last_month + pd.DateOffset(months=1),
    end=end_month,
    freq='MS'  # Month Start
)

if len(future_months) > 0:
    tmpl_future = pd.DataFrame({
        'year_month_date': future_months,
        'year_month_iso': future_months.strftime('%Y-%m'),
        'year_month': future_months.strftime('%b-%y')
    })
    print(f"✅ 将来テンプレート: {len(tmpl_future)}ヶ月")
else:
    tmpl_future = pd.DataFrame(columns=['year_month_date', 'year_month_iso', 'year_month'])
    print(f"✅ 将来テンプレート: なし")

# %% C-3. 過去〜将来の時間軸を作成
axis_full = pd.concat([
    ts_monthly[['year_month_iso', 'year_month', 'year_month_date']],
    tmpl_future[['year_month_iso', 'year_month', 'year_month_date']]
]).drop_duplicates(subset=['year_month_iso']).sort_values('year_month_date').reset_index(drop=True)

print(f"✅ 完全な時間軸: {len(axis_full)}ヶ月")

# %% C-4. 結合 + 0補完
plot_base = axis_full.merge(ts_monthly, on=['year_month_iso', 'year_month_date'], 
                             how='left', suffixes=('', '_y'))

# 重複列を削除
plot_base = plot_base.loc[:, ~plot_base.columns.str.endswith('_y')]

print(f"✅ プロットベース作成: {len(plot_base)}行")

# %% *checkpoint_4: プロットベース
checkpoint_path = os.path.join(checkpoint_folder, f"04_plot_base_{today_str}.parquet")
plot_base.to_parquet(checkpoint_path, engine='pyarrow', compression='snappy', index=False)
print(f"💾 Checkpoint 4 保存: {checkpoint_path}")

# %% D) プロット準備
print("\n" + "=" * 60)
print("D) プロット準備")
print("=" * 60)

# %% D-1. 期間設定
start_date = pd.to_datetime("2025-01-01")
end_date = pd.to_datetime("2025-12-01")

# %% D-2. プロット用データフレーム作成
plot_df = plot_base[
    (plot_base['year_month_date'] >= start_date) &
    (plot_base['year_month_date'] <= end_date)
].copy()

# 0補完と符号列追加
plot_df['ttl_gain_realized_jpy'] = plot_df['ttl_gain_realized_jpy'].fillna(0)
plot_df['gain_sign'] = np.where(plot_df['ttl_gain_realized_jpy'] >= 0, 'positive', 'negative')

# 実績フラグ
plot_df['is_actual'] = plot_df['num_of_trades'].notna()

# 累積損益
plot_df['gain_for_cum'] = plot_df['ttl_gain_realized_jpy'].fillna(0)
plot_df['capital_gain_cumsum'] = plot_df['gain_for_cum'].cumsum()

# 月番号（1-12）
plot_df['month_num'] = plot_df['year_month_date'].dt.month

print(f"✅ プロット用データ作成: {len(plot_df)}ヶ月")
print(f"   実績: {plot_df['is_actual'].sum()}ヶ月")
print(f"   予測: {(~plot_df['is_actual']).sum()}ヶ月")

# %% *checkpoint_5: プロット用データ
checkpoint_path = os.path.join(checkpoint_folder, f"05_plot_df_{today_str}.parquet")
plot_df.to_parquet(checkpoint_path, engine='pyarrow', compression='snappy', index=False)
print(f"💾 Checkpoint 5 保存: {checkpoint_path}")

print("\n" + "=" * 60)
print("✅ データ準備完了")
print("=" * 60)
print(f"\n次のステップ:")
print(f"1. 可視化スクリプト (kpi_visualization.py) を実行")
print(f"2. または、各checkpointファイルを読み込んで分析を続行")
print(f"\nCheckpointファイル:")
for i in range(1, 6):
    pattern = os.path.join(checkpoint_folder, f"0{i}_*_{today_str}.parquet")
    files = glob(pattern)
    if files:
        print(f"  - Checkpoint {i}: {os.path.basename(files[0])}")
