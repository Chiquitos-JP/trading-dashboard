# %% 📚 ライブラリ
import pandas as pd
import numpy as np
import os
from datetime import datetime
from glob import glob
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import matplotlib.patches as mpatches
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# %% 📁 パス設定
today_str = datetime.today().strftime('%Y%m%d')
realized_pl_folder = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\01_data\trading_account\realized_pl"
checkpoint_folder = os.path.join(realized_pl_folder, "checkpoints")
output_folder = os.path.join(r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\04_output", "figures")
dated_output_folder = os.path.join(output_folder, f"realizedPl_{today_str}")

os.makedirs(dated_output_folder, exist_ok=True)

# %% データ読込
print("=" * 60)
print("データ読込")
print("=" * 60)

# checkpoint 5 (plot_df) を読込
checkpoint_pattern = os.path.join(checkpoint_folder, f"05_plot_df_{today_str}.parquet")
checkpoint_files = glob(checkpoint_pattern)

if not checkpoint_files:
    # 今日のファイルがなければ最新を取得
    checkpoint_pattern = os.path.join(checkpoint_folder, "05_plot_df_*.parquet")
    checkpoint_files = glob(checkpoint_pattern)
    
if not checkpoint_files:
    raise FileNotFoundError(f"plot_df checkpointファイルが見つかりません。\n先にkpi_analysis.pyを実行してください。")

checkpoint_file = max(checkpoint_files, key=os.path.getctime)
print(f"📄 読込: {os.path.basename(checkpoint_file)}")

plot_df = pd.read_parquet(checkpoint_file, engine='pyarrow')

# ts_monthly も読込（年次比較用）
ts_monthly_pattern = os.path.join(checkpoint_folder, "03_ts_monthly_*.parquet")
ts_monthly_files = glob(ts_monthly_pattern)
if ts_monthly_files:
    ts_monthly_file = max(ts_monthly_files, key=os.path.getctime)
    ts_monthly = pd.read_parquet(ts_monthly_file, engine='pyarrow')
    print(f"📄 読込: {os.path.basename(ts_monthly_file)}")
else:
    ts_monthly = plot_df[plot_df['is_actual']].copy()

print(f"✅ データ読込完了")

# %% スタイル設定
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# カラーパレット
COLOR_PROFIT = '#1F77B4'  # steelblue
COLOR_LOSS = '#D62728'    # firebrick
COLOR_NEUTRAL = '#7F7F7F' # gray
COLOR_FORECAST = '#BCBD22' # olive

BIZ_COLORS = {
    2024: '#1F77B4',  # muted blue
    2025: '#2CA02C',  # muted green
    2026: '#FF7F0E',  # muted orange
    2027: '#7F7F7F'   # muted grey
}

# %% P1: 累積損益（折れ線）
print("\n--- P1: 累積損益 ---")

fig, ax = plt.subplots(figsize=(10, 4))

# 実績データと予測データを分離
actual_df = plot_df[plot_df['is_actual']].copy()
forecast_df = plot_df[~plot_df['is_actual']].copy()

# ゼロ基準線
ax.axhline(y=0, color='gray', alpha=0.5, linewidth=0.6, zorder=1)

# 予測線（点線）
if len(forecast_df) > 0:
    # 実績の最後と予測の最初をつなぐ
    if len(actual_df) > 0:
        last_actual = actual_df.iloc[-1]
        forecast_start = pd.DataFrame([{
            'year_month_date': last_actual['year_month_date'],
            'capital_gain_cumsum': last_actual['capital_gain_cumsum']
        }])
        forecast_plot = pd.concat([forecast_start, forecast_df])
    else:
        forecast_plot = forecast_df
    
    ax.plot(forecast_plot['year_month_date'], forecast_plot['capital_gain_cumsum'],
            color=COLOR_NEUTRAL, linestyle='--', linewidth=1, alpha=0.5,
            label='Forecast', zorder=2)

# 実績線（色分け）
if len(actual_df) > 0:
    for i in range(len(actual_df) - 1):
        x1, y1 = actual_df.iloc[i]['year_month_date'], actual_df.iloc[i]['capital_gain_cumsum']
        x2, y2 = actual_df.iloc[i+1]['year_month_date'], actual_df.iloc[i+1]['capital_gain_cumsum']
        
        # 線分の色を決定（両端点の符号で判定）
        if y1 >= 0 and y2 >= 0:
            color = COLOR_PROFIT
        elif y1 < 0 and y2 < 0:
            color = COLOR_LOSS
        else:
            # ゼロをまたぐ場合：2つに分割
            if y1 != y2:  # ゼロ除算回避
                t = (0 - y1) / (y2 - y1)
                x_cross = x1 + (x2 - x1) * t
                
                # 前半
                color1 = COLOR_PROFIT if y1 >= 0 else COLOR_LOSS
                ax.plot([x1, x_cross], [y1, 0], color=color1, linewidth=1.5, zorder=3)
                
                # 後半
                color2 = COLOR_PROFIT if y2 >= 0 else COLOR_LOSS
                ax.plot([x_cross, x2], [0, y2], color=color2, linewidth=1.5, zorder=3)
                continue
            else:
                color = COLOR_PROFIT if y1 >= 0 else COLOR_LOSS
        
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=1.5, zorder=3)
    
    # 実績点
    colors = [COLOR_PROFIT if y >= 0 else COLOR_LOSS for y in actual_df['capital_gain_cumsum']]
    ax.scatter(actual_df['year_month_date'], actual_df['capital_gain_cumsum'],
               c=colors, s=20, zorder=4, edgecolors='white', linewidth=0.5)

# 予測点
if len(forecast_df) > 0:
    ax.scatter(forecast_df['year_month_date'], forecast_df['capital_gain_cumsum'],
               color=COLOR_NEUTRAL, s=20, alpha=0.5, zorder=4)

# 軸設定
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))

ax.set_ylabel('Cumulative Capital Gain (JPY)', fontsize=9)
ax.set_title('Cumulative Capital Gain', fontsize=12, fontweight='bold')
ax.text(0.02, 0.98, 'Cumulative Trend', transform=ax.transAxes,
        fontsize=9, va='top', color='gray')

plt.setp(ax.xaxis.get_majorticklabels(), visible=False)
plt.xticks(rotation=0)
plt.tight_layout()

# 保存
p1_path = os.path.join(dated_output_folder, f"P1_cumulative_trend_{today_str}.png")
plt.savefig(p1_path, dpi=300, bbox_inches='tight')
print(f"✅ P1保存: {os.path.basename(p1_path)}")
plt.close()

# %% P2: 月次損益（棒グラフ）
print("--- P2: 月次損益 ---")

fig, ax = plt.subplots(figsize=(10, 3))

# 棒グラフ
colors = [COLOR_PROFIT if x >= 0 else COLOR_LOSS for x in plot_df['ttl_gain_realized_jpy']]
ax.bar(plot_df['year_month_date'], plot_df['ttl_gain_realized_jpy'],
       width=25, color=colors, alpha=0.6)

# 軸設定
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
ax.set_ylabel('Capital Gain (JPY)', fontsize=9)
ax.set_title('Monthly Capital Gain', fontsize=12, fontweight='bold')
ax.text(0.02, 0.98, 'Breakdown of Cumulative Gain/Loss', transform=ax.transAxes,
        fontsize=9, va='top', color='gray')

plt.setp(ax.xaxis.get_majorticklabels(), visible=False)
plt.tight_layout()

p2_path = os.path.join(dated_output_folder, f"P2_monthly_gain_{today_str}.png")
plt.savefig(p2_path, dpi=300, bbox_inches='tight')
print(f"✅ P2保存: {os.path.basename(p2_path)}")
plt.close()

# %% P3: 1日あたりの平均損益（折れ線）
print("--- P3: 1日あたり平均損益 ---")

fig, ax = plt.subplots(figsize=(10, 3))

# 実績データのみプロット
actual_df = plot_df[plot_df['is_actual'] & plot_df['avg_gain_per_day_jpy'].notna()].copy()

if len(actual_df) > 0:
    ax.plot(actual_df['month_num'], actual_df['avg_gain_per_day_jpy'],
            color='darkgreen', linewidth=1, marker='o', markersize=4)
    
    # ゼロ基準線
    ax.axhline(y=0, color='gray', linewidth=0.6)
    
    # 軸設定
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(range(1, 13), fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
    ax.set_ylabel('Avg Gain per Day (JPY)', fontsize=9)
    ax.set_title('Avg Daily Capital Gain', fontsize=12, fontweight='bold')
    ax.text(0.02, 0.98, 'Daily-target', transform=ax.transAxes,
            fontsize=9, va='top', color='gray')

plt.tight_layout()

p3_path = os.path.join(dated_output_folder, f"P3_daily_avg_{today_str}.png")
plt.savefig(p3_path, dpi=300, bbox_inches='tight')
print(f"✅ P3保存: {os.path.basename(p3_path)}")
plt.close()

# %% 年次比較用データ準備
ts_monthly_comp = ts_monthly.copy()
ts_monthly_comp['year'] = ts_monthly_comp['year_month_date'].dt.year
ts_monthly_comp['month'] = ts_monthly_comp['year_month_date'].dt.month

# %% P4: 月次Win Rate（年次比較）
print("--- P4: 月次Win Rate ---")

fig, ax = plt.subplots(figsize=(10, 3))

for year in sorted(ts_monthly_comp['year'].unique()):
    year_data = ts_monthly_comp[ts_monthly_comp['year'] == year]
    ax.plot(year_data['month'], year_data['win_rate'],
            label=str(year), color=BIZ_COLORS.get(year, 'gray'),
            linewidth=1, marker='o', markersize=4)

ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0%}'))
ax.set_ylabel('Win Rate', fontsize=9)
ax.set_title('Monthly Win Rate', fontsize=12, fontweight='bold')
ax.text(0.02, 0.98, 'Yearly-Comps', transform=ax.transAxes,
        fontsize=9, va='top', color='gray')
ax.legend(loc='upper right', fontsize=8)

plt.setp(ax.xaxis.get_majorticklabels(), visible=False)
plt.tight_layout()

p4_path = os.path.join(dated_output_folder, f"P4_win_rate_{today_str}.png")
plt.savefig(p4_path, dpi=300, bbox_inches='tight')
print(f"✅ P4保存: {os.path.basename(p4_path)}")
plt.close()

# %% P5: 月次取引回数（年次比較）
print("--- P5: 月次取引回数 ---")

fig, ax = plt.subplots(figsize=(10, 3))

years = sorted(ts_monthly_comp['year'].unique())
months = range(1, 13)
width = 0.8 / len(years)

for i, year in enumerate(years):
    year_data = ts_monthly_comp[ts_monthly_comp['year'] == year]
    offset = (i - len(years)/2 + 0.5) * width
    positions = [m + offset for m in year_data['month']]
    ax.bar(positions, year_data['num_of_trades'],
           width=width, label=str(year), color=BIZ_COLORS.get(year, 'gray'))

ax.set_xticks(months)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
ax.set_ylabel('Number of Trades', fontsize=9)
ax.set_title('Monthly Number of Trades', fontsize=12, fontweight='bold')
ax.text(0.02, 0.98, 'Yearly-Comps', transform=ax.transAxes,
        fontsize=9, va='top', color='gray')
ax.legend(loc='upper right', fontsize=8)

plt.setp(ax.xaxis.get_majorticklabels(), visible=False)
plt.tight_layout()

p5_path = os.path.join(dated_output_folder, f"P5_num_trades_{today_str}.png")
plt.savefig(p5_path, dpi=300, bbox_inches='tight')
print(f"✅ P5保存: {os.path.basename(p5_path)}")
plt.close()

# %% P6: 実取引日数（年次比較）
print("--- P6: 実取引日数 ---")

fig, ax = plt.subplots(figsize=(10, 3))

for i, year in enumerate(years):
    year_data = ts_monthly_comp[ts_monthly_comp['year'] == year]
    offset = (i - len(years)/2 + 0.5) * width
    positions = [m + offset for m in year_data['month']]
    ax.bar(positions, year_data['actual_trade_days'],
           width=width, label=str(year), color=BIZ_COLORS.get(year, 'gray'))

ax.set_xticks(months)
ax.set_xticklabels(months, fontsize=8)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
ax.set_ylabel('Actual Trade Days', fontsize=9)
ax.set_title('Monthly Actual Trade Days', fontsize=12, fontweight='bold')
ax.text(0.02, 0.98, 'Yearly-Comps', transform=ax.transAxes,
        fontsize=9, va='top', color='gray')
ax.legend(loc='upper right', fontsize=8)

plt.tight_layout()

p6_path = os.path.join(dated_output_folder, f"P6_trade_days_{today_str}.png")
plt.savefig(p6_path, dpi=300, bbox_inches='tight')
print(f"✅ P6保存: {os.path.basename(p6_path)}")
plt.close()

# %% P7: ROI（年次比較）
print("--- P7: ROI ---")

fig, ax = plt.subplots(figsize=(10, 3))

for year in sorted(ts_monthly_comp['year'].unique()):
    year_data = ts_monthly_comp[ts_monthly_comp['year'] == year]
    ax.plot(year_data['month'], year_data['return_on_cost'],
            label=str(year), color=BIZ_COLORS.get(year, 'gray'),
            linewidth=1, marker='o', markersize=4)

ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0%}'))
ax.set_ylabel('Return on Cost (ROI)', fontsize=9)
ax.set_title('Monthly ROI', fontsize=12, fontweight='bold')
ax.text(0.02, 0.98, 'Return rate', transform=ax.transAxes,
        fontsize=9, va='top', color='gray')
ax.legend(loc='upper right', fontsize=8)

plt.setp(ax.xaxis.get_majorticklabels(), visible=False)
plt.tight_layout()

p7_path = os.path.join(dated_output_folder, f"P7_roi_{today_str}.png")
plt.savefig(p7_path, dpi=300, bbox_inches='tight')
print(f"✅ P7保存: {os.path.basename(p7_path)}")
plt.close()

# %% P8: 平均取得コスト/取引（年次比較）
print("--- P8: 平均取得コスト ---")

# 取引あたり平均取得コストを計算
ts_monthly_comp['avg_acquisition_per_trade'] = np.where(
    ts_monthly_comp['num_of_trades'] > 0,
    ts_monthly_comp['ttl_cost_acquisition_jpy'] / ts_monthly_comp['num_of_trades'],
    np.nan
)

fig, ax = plt.subplots(figsize=(10, 3))

for year in sorted(ts_monthly_comp['year'].unique()):
    year_data = ts_monthly_comp[ts_monthly_comp['year'] == year]
    ax.plot(year_data['month'], year_data['avg_acquisition_per_trade'],
            label=str(year), color=BIZ_COLORS.get(year, 'gray'),
            linewidth=1, marker='o', markersize=4)

ax.set_xticks(months)
ax.set_xticklabels(months, fontsize=8)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
ax.set_ylabel('Avg Acquisition Cost per Trade (JPY)', fontsize=9)
ax.set_title('Monthly Avg Acquisition Cost per Trade', fontsize=12, fontweight='bold')
ax.legend(loc='upper right', fontsize=8)

plt.tight_layout()

p8_path = os.path.join(dated_output_folder, f"P8_avg_cost_{today_str}.png")
plt.savefig(p8_path, dpi=300, bbox_inches='tight')
print(f"✅ P8保存: {os.path.basename(p8_path)}")
plt.close()

# %% P9: Risk Reward（月次）
print("--- P9: Risk Reward ---")

# 2025年のデータのみ
risk_reward_df = ts_monthly_comp[
    (ts_monthly_comp['year_month_date'] >= pd.to_datetime("2025-01-01")) &
    (ts_monthly_comp['year_month_date'] <= pd.to_datetime("2025-12-31"))
].copy()

# Risk Reward計算
risk_reward_df['avg_gain_per_trade'] = np.where(
    risk_reward_df['num_of_trades'] > 0,
    risk_reward_df['ttl_gain_realized_jpy'] / risk_reward_df['num_of_trades'], 0
)

risk_reward_df['avg_profit'] = np.where(
    risk_reward_df['num_of_win_trades'] > 0,
    risk_reward_df['ttl_gain_realized_jpy'] / risk_reward_df['num_of_win_trades'],
    np.nan
)

risk_reward_df['avg_loss'] = np.where(
    (risk_reward_df['num_of_trades'] - risk_reward_df['num_of_win_trades']) > 0,
    np.abs(risk_reward_df['ttl_gain_realized_jpy']) / 
    (risk_reward_df['num_of_trades'] - risk_reward_df['num_of_win_trades']),
    np.nan
)

risk_reward_df['rr_monthly'] = np.where(
    (risk_reward_df['avg_loss'].notna()) & (risk_reward_df['avg_loss'] > 0),
    risk_reward_df['avg_profit'] / risk_reward_df['avg_loss'],
    np.nan
)

fig, ax1 = plt.subplots(figsize=(10, 4))

# 棒グラフ（左軸）
colors = [COLOR_PROFIT if x >= 0 else COLOR_LOSS for x in risk_reward_df['avg_gain_per_trade']]
ax1.bar(risk_reward_df['month'], risk_reward_df['avg_gain_per_trade'],
        width=0.6, color=colors, alpha=0.6, label='Avg Gain per Trade')

ax1.set_xlabel('')
ax1.set_ylabel('Avg Gain per Trade (JPY, monthly)', fontsize=9)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
ax1.set_xticks(range(1, 13))
ax1.set_xticklabels(range(1, 13), fontsize=8)

# 折れ線（右軸）
ax2 = ax1.twinx()
ax2.plot(risk_reward_df['month'], risk_reward_df['rr_monthly'],
         color='darkgreen', linewidth=1, marker='o', markersize=4,
         label='Risk Reward Ratio')
ax2.set_ylabel('Monthly Risk Reward Ratio', fontsize=9, color='darkgreen')
ax2.tick_params(axis='y', labelcolor='darkgreen')

ax1.set_title('Monthly Risk Reward', fontsize=12, fontweight='bold')

plt.tight_layout()

p9_path = os.path.join(dated_output_folder, f"P9_risk_reward_{today_str}.png")
plt.savefig(p9_path, dpi=300, bbox_inches='tight')
print(f"✅ P9保存: {os.path.basename(p9_path)}")
plt.close()

# %% 完了メッセージ
print("\n" + "=" * 60)
print("✅ 全グラフ作成完了")
print("=" * 60)
print(f"\n保存先: {dated_output_folder}")
print(f"\n作成したグラフ:")
for i in range(1, 10):
    pattern = os.path.join(dated_output_folder, f"P{i}_*.png")
    files = glob(pattern)
    if files:
        print(f"  - P{i}: {os.path.basename(files[0])}")
