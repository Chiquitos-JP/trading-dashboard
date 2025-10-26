# kpi_calc_ytd_monthly_simple.py
"""
KPI YTD & Monthly Summary Calculator
年初来(YTD)と月次のKPIを計算し、テーブル形式で表示

R版: kpi_calc_ytd_monthly_simple.R の Python実装
"""

import os
import sys
from pathlib import Path
from datetime import datetime, date
from glob import glob
import pandas as pd
import numpy as np
import html  # HTMLエスケープ用

# ===== プロジェクトルート設定 =====
base_path = Path(__file__).resolve().parents[3]
print(f"[INFO] Base path: {base_path}")

# ===== 日付設定 =====
today_str = datetime.now().strftime("%Y%m%d")
start_date = pd.to_datetime("2025-01-01")
end_date = pd.to_datetime(date.today())

print("="*60)
print("KPI YTD & Monthly Summary Calculator")
print("="*60)
print(f"[PERIOD] {start_date.date()} - {end_date.date()}")
print()

# ===== データ読込 =====
checkpoint_folder = base_path / "01_data" / "trading_account" / "realized_pl" / "checkpoints"

# ts_monthly checkpoint (03_ts_monthly_*.parquet) を読込
ts_monthly_pattern = str(checkpoint_folder / "03_ts_monthly_*.parquet")
ts_monthly_files = glob(ts_monthly_pattern)

if not ts_monthly_files:
    raise FileNotFoundError(f"ts_monthly checkpointファイルが見つかりません。\n先にkpi_analysis.pyを実行してください。")

ts_monthly_file = max(ts_monthly_files, key=os.path.getctime)
print(f"[LOAD] {os.path.basename(ts_monthly_file)}")

ts_monthly_d = pd.read_parquet(ts_monthly_file, engine='pyarrow')
print(f"[OK] Data shape: {ts_monthly_d.shape}")

# 為替レート情報取得のため、merged dataも読込
processed_folder = base_path / "01_data" / "trading_account" / "realized_pl" / "processed"
merged_pattern = str(processed_folder / "**/merged_trading_summary_*.csv")
merged_files = glob(merged_pattern, recursive=True)

if merged_files:
    merged_file = max(merged_files, key=os.path.getctime)
    print(f"[LOAD FX] {os.path.basename(merged_file)}")
    merged_data = pd.read_csv(merged_file)
    print(f"[OK] Merged data shape: {merged_data.shape}")
else:
    print(f"[WARNING] 為替レート情報用のmerged dataが見つかりません")
    merged_data = None

print()

# ===== 計測期間でフィルタ =====
kpi_df = ts_monthly_d[
    (ts_monthly_d['year_month_date'] >= start_date) &
    (ts_monthly_d['year_month_date'] <= end_date)
].copy()

print(f"[OK] Filtered: {kpi_df.shape[0]} months")

# ===== 為替レート情報を月次で集計 =====
fx_rate_monthly = None
if merged_data is not None:
    # SBIデータ（USDベース）のみを抽出し、為替レートを月次で集計
    sbi_data = merged_data[merged_data['broker'] == 'SBI'].copy()
    if len(sbi_data) > 0:
        # applied_fx_rateの月次平均を計算
        fx_rate_monthly = sbi_data.groupby('year_month')['applied_fx_rate'].mean().reset_index()
        fx_rate_monthly.columns = ['year_month', 'avg_fx_rate']
        print(f"[OK] FX rate data: {fx_rate_monthly.shape[0]} months")
    else:
        print(f"[WARNING] SBIデータが見つかりません")

print()

# ===== 税金計算関数 =====
def calc_tax(profit_before_tax):
    """
    税金を計算（利益がプラスの場合のみ）
    
    税率構造:
    - 所得税: 15%
    - 住民税: 5%
    - 復興特別所得税: 0.315% (所得税の2.1%)
    - 合計: 20.315%
    
    Parameters:
    -----------
    profit_before_tax : float
        税引前利益
        
    Returns:
    --------
    dict : 税金の内訳と税引後利益
    """
    if pd.isna(profit_before_tax) or profit_before_tax <= 0:
        return {
            'Income Tax (所得税)': 0,
            'Resident Tax (住民税)': 0,
            'Special Reconstruction Tax (復興特別所得税)': 0,
            'Total Tax (税額)': 0,
            'Profit After Tax (PAT)': profit_before_tax if not pd.isna(profit_before_tax) else 0
        }
    
    # 税率定義
    income_tax_rate = 0.15  # 15%
    resident_tax_rate = 0.05  # 5%
    reconstruction_tax_rate = 0.00315  # 0.315% (所得税の2.1%)
    
    # 各税額計算
    income_tax = profit_before_tax * income_tax_rate
    resident_tax = profit_before_tax * resident_tax_rate
    reconstruction_tax = profit_before_tax * reconstruction_tax_rate
    
    total_tax = income_tax + resident_tax + reconstruction_tax
    pat = profit_before_tax - total_tax
    
    return {
        'Income Tax (所得税)': income_tax,
        'Resident Tax (住民税)': resident_tax,
        'Special Reconstruction Tax (復興特別所得税)': reconstruction_tax,
        'Total Tax (税額)': total_tax,
        'Profit After Tax (PAT)': pat
    }

# ===== KPI計算関数 =====
def calc_metrics(df, fx_data=None, year_month=None):
    """
    KPI指標を計算
    
    Parameters:
    -----------
    df : pd.DataFrame
        月次データ
    fx_data : pd.DataFrame, optional
        為替レートデータ
    year_month : str, optional
        対象年月（為替レート取得用）
        
    Returns:
    --------
    dict : 計算されたKPI指標
    """
    total_trades = df['num_of_trades'].sum()
    total_win_trades = df['num_of_win_trades'].sum() if 'num_of_win_trades' in df.columns else 0
    total_net_pl = df['ttl_gain_realized_jpy'].sum()
    
    # 為替レート取得
    avg_fx_rate = np.nan
    if fx_data is not None and year_month is not None:
        fx_match = fx_data[fx_data['year_month'] == year_month]
        if len(fx_match) > 0:
            avg_fx_rate = fx_match['avg_fx_rate'].iloc[0]
    
    # 利益と損失を分離（新しい列を使用）
    if 'ttl_gain_only' in df.columns and 'ttl_loss_only' in df.columns:
        # 月次集計済みデータの場合（kpi_analysis.pyで計算済み）
        total_gain = df['ttl_gain_only'].sum()
        total_loss = df['ttl_loss_only'].sum()
    else:
        # 日次データの場合（フォールバック）
        gains = df['ttl_gain_realized_jpy'][df['ttl_gain_realized_jpy'] > 0]
        losses = df['ttl_gain_realized_jpy'][df['ttl_gain_realized_jpy'] < 0]
        total_gain = gains.sum() if len(gains) > 0 else 0
        total_loss = abs(losses.sum()) if len(losses) > 0 else 0
    
    total_investment = df['ttl_cost_acquisition_jpy'].sum()
    
    # Win Rate
    win_rate = total_win_trades / total_trades if total_trades > 0 else np.nan
    
    # Loss Rate
    total_loss_trades = total_trades - total_win_trades
    loss_rate = total_loss_trades / total_trades if total_trades > 0 else np.nan
    
    # Average Capital Invested per trade
    avg_capital_invested = total_investment / total_trades if total_trades > 0 else np.nan
    
    # Average Gain per Trade
    avg_gain = total_gain / total_win_trades if total_win_trades > 0 else np.nan
    
    # Average Loss per Trade
    avg_loss = total_loss / total_loss_trades if total_loss_trades > 0 else np.nan
    
    # デバッグ出力（一時的）
    period_label = year_month if year_month else "YTD"
    avg_loss_str = f"{avg_loss:,.2f}" if not np.isnan(avg_loss) else "N/A"
    print(f"[DEBUG] {period_label}: total_loss={total_loss:,.2f} JPY, total_loss_trades={total_loss_trades}, avg_loss={avg_loss_str} JPY")
    
    # Risk/Reward Ratio
    risk_reward = avg_gain / avg_loss if not np.isnan(avg_loss) and avg_loss > 0 else np.nan
    
    # ROI
    roi = total_net_pl / total_investment if total_investment > 0 else np.nan
    
    # Mean Profit Rate & Mean Loss Rate
    mean_profit_rate = avg_gain / avg_capital_invested if not np.isnan(avg_gain) and avg_capital_invested > 0 else np.nan
    mean_loss_rate = avg_loss / avg_capital_invested if not np.isnan(avg_loss) and avg_capital_invested > 0 else np.nan
    
    # Expectancy
    if not np.isnan(win_rate) and not np.isnan(mean_profit_rate) and not np.isnan(mean_loss_rate):
        expectancy = win_rate * mean_profit_rate - (1 - win_rate) * mean_loss_rate
    else:
        expectancy = np.nan
    
    # 税金計算（税引前利益 = Total Net P/L）
    tax_info = calc_tax(total_net_pl)
    
    # 税引き後ROI
    roi_after_tax = tax_info['Profit After Tax (PAT)'] / total_investment if total_investment > 0 else np.nan
    
    return {
        'Expectancy (E)': expectancy,
        'Win Rate (WR)': win_rate,
        'Loss Rate (LR)': loss_rate,
        'Mean Profit Rate (G)': mean_profit_rate,
        'Mean Loss Rate (L)': mean_loss_rate,
        'Mean Gain per Trade (JPY)': avg_gain,
        'Mean Loss per Trade (JPY)': avg_loss,
        'Mean Capital Invested per trade (JPY) / Mean Position Size': avg_capital_invested,
        'Risk/Reward Ratio (RRR)': risk_reward,
        'ROI': roi,
        'Total Trades': total_trades,
        'Total Win Trades': total_win_trades,
        'Total Loss Trades': total_loss_trades,
        'Total Net P/L (JPY)': total_net_pl,
        'Total Gain (JPY)': total_gain,
        'Total Loss (JPY)': total_loss,
        'Total Investment (JPY)': total_investment,
        'Income Tax (所得税)': tax_info['Income Tax (所得税)'],
        'Resident Tax (住民税)': tax_info['Resident Tax (住民税)'],
        'Special Reconstruction Tax (復興特別所得税)': tax_info['Special Reconstruction Tax (復興特別所得税)'],
        'Total Tax (税額)': tax_info['Total Tax (税額)'],
        'Profit After Tax (PAT)': tax_info['Profit After Tax (PAT)'],
        'ROI After Tax': roi_after_tax
    }

# ===== YTD集計 =====
print("="*60)
print("YTD集計")
print("="*60)

trade_days = kpi_df['actual_trade_days'].sum()
market_days = kpi_df['market_open_days'].sum()

ytd_metrics = calc_metrics(kpi_df)

# YTD為替レート（取引量加重平均）
ytd_avg_fx_rate = np.nan
if fx_rate_monthly is not None and merged_data is not None:
    # SBIデータでYTD期間のUSD取引量と為替レートを取得
    sbi_ytd = merged_data[
        (merged_data['broker'] == 'SBI') & 
        (merged_data['year_month'].isin(kpi_df['year_month'].unique()))
    ].copy()
    
    if len(sbi_ytd) > 0:
        # USDベースの取引量（絶対値）で加重平均を計算
        sbi_ytd['abs_usd_amount'] = sbi_ytd['ttl_gain_realized_usd'].abs()
        
        # 取引量加重平均レート = Σ(為替レート × USD取引量) / Σ(USD取引量)
        total_weighted_rate = (sbi_ytd['applied_fx_rate'] * sbi_ytd['abs_usd_amount']).sum()
        total_usd_volume = sbi_ytd['abs_usd_amount'].sum()
        
        if total_usd_volume > 0:
            ytd_avg_fx_rate = total_weighted_rate / total_usd_volume
            print(f"[INFO] YTD FX Rate: 取引量加重平均 {ytd_avg_fx_rate:.2f} (総取引量: ${total_usd_volume:,.0f})")
        else:
            # フォールバック: 月次平均
            ytd_months = kpi_df['year_month'].unique()
            ytd_fx_data = fx_rate_monthly[fx_rate_monthly['year_month'].isin(ytd_months)]
            if len(ytd_fx_data) > 0:
                ytd_avg_fx_rate = ytd_fx_data['avg_fx_rate'].mean()
                print(f"[INFO] YTD FX Rate: 月次単純平均 {ytd_avg_fx_rate:.2f} (フォールバック)")
    else:
        print(f"[WARNING] YTD期間のSBIデータが見つかりません")

# YTD結果を辞書に追加
ytd_data = {
    'Trading Days': trade_days,
    'Market Open Days': market_days,
    'Average Exchange Rate (JPY/USD)': ytd_avg_fx_rate,
    **ytd_metrics
}

print(f"[OK] YTD trade days: {trade_days}")
print(f"[OK] YTD market open days: {market_days}")
print(f"[OK] YTD net P/L: {ytd_data['Total Net P/L (JPY)']:,.0f} JPY")
print()

# ===== 月次集計 =====
print("="*60)
print("月次集計")
print("="*60)

monthly_data = {}

for ym_date, group_df in kpi_df.groupby('year_month_date'):
    month_label = ym_date.strftime("%b-%Y")  # Jan-2025形式
    month_str = ym_date.strftime("%Y-%m")  # 2025-01形式（為替レート検索用）
    
    trade_days_m = group_df['actual_trade_days'].sum()
    market_days_m = group_df['market_open_days'].sum()
    
    monthly_metrics = calc_metrics(group_df)
    
    # 為替レート取得
    monthly_fx_rate = np.nan
    if fx_rate_monthly is not None:
        fx_match = fx_rate_monthly[fx_rate_monthly['year_month'] == month_str]
        if len(fx_match) > 0:
            monthly_fx_rate = fx_match['avg_fx_rate'].iloc[0]
    
    monthly_data[month_label] = {
        'Trading Days': trade_days_m,
        'Market Open Days': market_days_m,
        'Average Exchange Rate (JPY/USD)': monthly_fx_rate,
        **monthly_metrics
    }

print(f"[OK] Monthly data: {len(monthly_data)} months")
print()

# ===== データフレーム構築 =====
print("="*60)
print("テーブル作成")
print("="*60)

# カテゴリ別メトリック定義
assumption_metrics = ['Trading Days', 'Market Open Days', 'Average Exchange Rate (JPY/USD)']
lagging_metrics = ['Expectancy (E)', 'Win Rate (WR)', 'Loss Rate (LR)', 'Mean Profit Rate (G)', 'Mean Loss Rate (L)', 
                  'Mean Gain per Trade (JPY)', 'Mean Loss per Trade (JPY)', 
                  'Mean Capital Invested per trade (JPY) / Mean Position Size', 
                  'Risk/Reward Ratio (RRR)', 'ROI']
interim_metrics = ['Total Trades', 'Total Win Trades', 'Total Loss Trades']
leading_metrics = []  # 将来的な指標用
summary_metrics = ['Total Net P/L (JPY)', 'Total Gain (JPY)', 'Total Loss (JPY)', 'Total Investment (JPY)']
tax_metrics = ['Income Tax (所得税)', 'Resident Tax (住民税)', 'Special Reconstruction Tax (復興特別所得税)', 
               'Total Tax (税額)', 'Profit After Tax (PAT)', 'ROI After Tax']

# 月列を日付順にソート
month_cols_sorted = sorted(monthly_data.keys(), 
                           key=lambda x: datetime.strptime(x, "%b-%Y"))

# データフレーム構築（カテゴリ別）
rows = []

# Assumption セクション
rows.append({'Metric': 'ASSUMPTIONS', 'YTD in 2025': '', **{m: '' for m in month_cols_sorted}, 'is_header': True})
for metric in assumption_metrics:
    row = {'Metric': metric, 'YTD in 2025': ytd_data[metric], 'is_header': False}
    for month in month_cols_sorted:
        row[month] = monthly_data[month][metric]
    rows.append(row)

# Lagging Indicators セクション
rows.append({'Metric': 'LAGGING INDICATORS', 'YTD in 2025': '', **{m: '' for m in month_cols_sorted}, 'is_header': True})
for metric in lagging_metrics:
    if metric in ytd_metrics:  # メトリックが存在する場合のみ追加
        row = {'Metric': metric, 'YTD in 2025': ytd_data[metric], 'is_header': False}
        for month in month_cols_sorted:
            row[month] = monthly_data[month][metric]
        rows.append(row)

# Interim Indicators セクション
rows.append({'Metric': 'INTERIM INDICATORS', 'YTD in 2025': '', **{m: '' for m in month_cols_sorted}, 'is_header': True})
for metric in interim_metrics:
    if metric in ytd_metrics:
        row = {'Metric': metric, 'YTD in 2025': ytd_data[metric], 'is_header': False}
        for month in month_cols_sorted:
            row[month] = monthly_data[month][metric]
        rows.append(row)

# Leading Indicators セクション（将来的に追加予定）
if leading_metrics:
    rows.append({'Metric': 'LEADING INDICATORS', 'YTD in 2025': '', **{m: '' for m in month_cols_sorted}, 'is_header': True})
    for metric in leading_metrics:
        if metric in ytd_metrics:
            row = {'Metric': metric, 'YTD in 2025': ytd_data[metric], 'is_header': False}
            for month in month_cols_sorted:
                row[month] = monthly_data[month][metric]
            rows.append(row)

# Summary セクション
rows.append({'Metric': 'SUMMARY', 'YTD in 2025': '', **{m: '' for m in month_cols_sorted}, 'is_header': True})
for metric in summary_metrics:
    if metric in ytd_metrics:
        row = {'Metric': metric, 'YTD in 2025': ytd_data[metric], 'is_header': False}
        for month in month_cols_sorted:
            row[month] = monthly_data[month][metric]
        rows.append(row)

# Tax セクション
rows.append({'Metric': 'TAX CALCULATION', 'YTD in 2025': '', **{m: '' for m in month_cols_sorted}, 'is_header': True})
for metric in tax_metrics:
    if metric in ytd_metrics:
        row = {'Metric': metric, 'YTD in 2025': ytd_data[metric], 'is_header': False}
        for month in month_cols_sorted:
            row[month] = monthly_data[month][metric]
        rows.append(row)

kpi_results = pd.DataFrame(rows)

# ===== 値のフォーマット =====
def format_value(metric, value):
    """値をメトリックに応じてフォーマット"""
    if pd.isna(value):
        return "—"
    
    # パーセント表示
    if metric in ['Expectancy (E)', 'Win Rate (WR)', 'Loss Rate (LR)', 'Mean Profit Rate (G)', 
                  'Mean Loss Rate (L)', 'ROI', 'ROI After Tax']:
        return f"{value:.2%}"
    
    # 金額表示（カンマ区切り）
    elif metric in ['Mean Gain per Trade (JPY)', 'Mean Loss per Trade (JPY)',
                    'Total Gain (JPY)', 'Total Loss (JPY)', 'Total Investment (JPY)', 'Total Net P/L (JPY)',
                    'Income Tax (所得税)', 'Resident Tax (住民税)', 'Special Reconstruction Tax (復興特別所得税)', 
                    'Total Tax (税額)', 'Profit After Tax (PAT)']:
        return f"{value:,.0f}"
    
    # Mean Position Size（整数表示）
    elif 'Mean Position Size' in metric:
        return f"{int(value):,}"
    
    # 為替レート表示
    elif metric == 'Applied FX Rate (JPY/USD)':
        return f"{value:.2f}"
    
    # Risk/Reward Ratio
    elif metric == 'Risk/Reward Ratio (RRR)':
        return f"{value:.2f}"
    
    # 為替レート表示
    elif metric == 'Average Exchange Rate (JPY/USD)':
        return f"{value:.1f}"
    
    # 整数（取引回数など）
    elif metric in ['Trading Days', 'Market Open Days', 'Total Trades', 'Total Win Trades', 'Total Loss Trades']:
        return f"{int(value)}"
    
    else:
        return str(value)

# 全ての値列にフォーマットを適用
value_cols = ['YTD in 2025'] + month_cols_sorted
for col in value_cols:
    kpi_results[col] = kpi_results.apply(
        lambda row: format_value(row['Metric'], row[col]), axis=1
    )

# ===== 説明行を追加 =====
period_row = pd.DataFrame([{
    'Metric': 'Period',
    'YTD in 2025': f"{start_date.date()} - {end_date.date()}",
    **{m: "" for m in month_cols_sorted}
}])

reference_row = pd.DataFrame([{
    'Metric': 'Reference',
    'YTD in 2025': 'E = WR × Mean Profit Rate − (1 − WR) × Mean Loss Rate',
    **{m: "" for m in month_cols_sorted}
}])

# PeriodとReference情報を別途保存
period_info = f"{start_date.date()} - {end_date.date()}"
reference_info = 'E = WR × Mean Profit Rate − (1 − WR) × Mean Loss Rate'
note_info = [
    '①楽天とSBI証券では諸経費は差し引かれているものの、実現損益のデータには税金が含まれていない。',
    '②適用為替はFREDの日別データから抜粋（<a href="https://fred.stlouisfed.org/series/DEXJPUS" target="_blank" rel="noopener noreferrer">リンク先</a>）。開示されていない場合には直近の開示情報を活用している。なお、通算損益は加重平均した為替情報を記載。'
]

# kpi_resultsにはPeriodとReferenceを含めない
# kpi_results = pd.concat([period_row, kpi_results, reference_row], ignore_index=True)

print("[OK] Table created")
print()

# ===== 表示 =====
# is_header列を除外して表示用データフレーム作成
kpi_results_display = kpi_results.drop(columns=['is_header'], errors='ignore')

print("="*60)
print("KPI YTD & Monthly Summary")
print("="*60)
print()
print(kpi_results_display.to_string(index=False))
print()

# ===== CSV保存 =====
output_folder = base_path / "04_output" / "figures" / f"realizedPl_{today_str}"
output_folder.mkdir(parents=True, exist_ok=True)

csv_path = output_folder / f"kpi_ytd_monthly_{today_str}.csv"
kpi_results_display.to_csv(csv_path, index=False, encoding='utf-8-sig')
print(f"[SAVE] CSV: {csv_path}")
print()

# ===== HTML保存（オプション） =====
html_path = output_folder / f"kpi_ytd_monthly_{today_str}.html"

# テーブルHTMLを手動構築（見出し行対応）
table_rows = []
for idx, row in kpi_results.iterrows():
    is_header = row.get('is_header', False)
    
    if is_header:
        # 見出し行の処理 - colspan を使用してカテゴリ全体をスパンする
        escaped_text = html.escape(str(row["Metric"]))
        col_count = len([col for col in kpi_results.columns if col != 'is_header'])
        table_rows.append(f'<tr class="header-row"><th scope="row" class="section-header metric-col header-cell" colspan="{col_count}">{escaped_text}</th></tr>')
    else:
        # 通常の行の処理
        cells = []
        for col_idx, col in enumerate(kpi_results.columns):
            if col == 'is_header':  # is_header列はスキップ
                continue
            value = row[col]
            if col_idx == 0:  # Metric列
                escaped_value = html.escape(str(value))
                cells.append(f'<th scope="row" class="metric-col">{escaped_value}</th>')
            else:
                cell_class = 'value-col'
                escaped_value = html.escape(str(value))
                cells.append(f'<td class="{cell_class}">{escaped_value}</td>')
        
        table_rows.append(f'<tr>{"".join(cells)}</tr>')

# ヘッダー行の構築（is_header列を除外）
header_cells = []
for col in kpi_results.columns:
    if col != 'is_header':  # is_header列は表示しない
        header_cells.append(f'<th scope="col">{col}</th>')

table_html = f"""
<table aria-label="KPI YTD and Monthly Summary Table">
    <caption>
        KPI指標の年初来(YTD)および月次サマリー
    </caption>
    <thead>
        <tr>
            {''.join(header_cells)}
        </tr>
    </thead>
    <tbody>
        {''.join(table_rows)}
    </tbody>
</table>
"""

html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KPI YTD & Monthly Summary</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'SF Pro Display', 'Roboto', sans-serif;
            background-color: #fafbfc;
            color: #1a202c;
            line-height: 1.5;
            padding: 32px 16px;
            font-feature-settings: 'kern' 1, 'liga' 1;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background-color: white;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        h1 {{
            background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%);
            color: white;
            font-size: 20px;
            font-weight: 700;
            padding: 24px 32px;
            margin: 0;
            letter-spacing: 0.025em;
        }}
        .subtitle {{
            background-color: #f7fafc;
            color: #718096;
            font-size: 13px;
            padding: 12px 32px;
            border-bottom: 1px solid #e2e8f0;
            font-weight: 400;
        }}
        .table-wrapper {{
            overflow-x: auto;
            overflow-y: auto;
            max-height: 80vh;
            position: relative;
        }}
        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 12px;
            background-color: white;
            table-layout: fixed;
            font-variant-numeric: tabular-nums;
        }}
        caption {{
            display: none;
        }}
        thead th {{
            background-color: #2c3e50;
            color: white;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 20;
            font-size: 10px;
            letter-spacing: 0.3px;
            padding: 12px;
            text-align: center;
        }}
        thead th:first-child {{
            text-align: left;
            width: 240px;
            max-width: 240px;
            position: sticky;
            left: 0;
            z-index: 25;
            box-shadow: 1px 0 3px rgba(0,0,0,0.1);
        }}
        thead th:not(:first-child) {{
            width: 100px;
            min-width: 100px;
        }}
        thead th:first-child {{
            border-top-left-radius: 8px;
        }}
        thead th:last-child {{
            border-top-right-radius: 8px;
        }}
        tbody td, tbody th {{
            padding: 12px 10px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tbody tr:hover:not(.header-row) {{
            background-color: #e8f4f8;
        }}
        .header-row {{
            background-color: transparent !important;
            position: sticky;
            top: 45px;
            z-index: 15;
        }}
        .header-row th {{
            background-color: white;
            color: #2d3748;
            font-weight: 700;
            font-size: 12px;
            text-align: left;
            padding: 16px 12px 8px 12px;
            letter-spacing: 0.025em;
            border-bottom: 3px solid #4299e1;
            text-transform: uppercase;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
        }}
        .header-row th[colspan] {{
            position: sticky;
            left: 0;
            z-index: 20;
            box-shadow: 1px 0 3px rgba(0,0,0,0.1);
            width: auto;
            min-width: 240px;
            white-space: normal;
            word-wrap: break-word;
        }}
        .section-header {{
            position: relative;
        }}
        .section-header::after {{
            content: '';
            position: absolute;
            bottom: -3px;
            left: 12px;
            right: 12px;
            height: 3px;
            background: linear-gradient(90deg, #4299e1 0%, #63b3ed 100%);
            border-radius: 1.5px;
        }}
        tbody tr {{
            border-bottom: 1px solid #f1f2f6;
        }}
        tbody tr:nth-child(even):not(.header-row) {{
            background-color: #fafbfc;
        }}
        .metric-col {{
            font-weight: 500;
            color: #2d3748;
            background-color: #f7fafc;
            text-align: left;
            white-space: normal;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: auto;
            width: 240px;
            min-width: 240px;
            max-width: 240px;
            padding: 12px 16px;
            position: sticky;
            left: 0;
            z-index: 10;
            box-shadow: 1px 0 3px rgba(0,0,0,0.05);
            line-height: 1.3;
            vertical-align: top;
        }}
        .metric-col.header-cell {{
            z-index: 20;
            background-color: white;
        }}
        .value-col {{
            text-align: right;
            font-family: 'SF Mono', 'Monaco', 'Roboto Mono', 'Consolas', monospace;
            color: #4a5568;
            padding: 12px 16px;
            font-variant-numeric: tabular-nums;
            font-size: 11px;
        }}
        .period-row {{
            background-color: #fff9c4 !important;
            font-weight: bold;
        }}
        .period-row td {{
            border-top: 2px solid #fbc02d;
            border-bottom: 2px solid #fbc02d;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .period-row .metric-col {{
            white-space: normal;
            word-wrap: break-word;
            overflow: visible;
            text-overflow: unset;
            width: 240px !important;
            min-width: 240px !important;
            max-width: 240px !important;
            position: sticky;
            left: 0;
            z-index: 10;
            background-color: #fff9c4;
            line-height: 1.3;
        }}
        .reference-row {{
            background-color: #e3f2fd !important;
            font-style: italic;
        }}
        .reference-row td {{
            border-top: 2px solid #2196f3;
            font-size: 12px;
            color: #1565c0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .reference-row .metric-col {{
            position: sticky;
            left: 0;
            z-index: 10;
            background-color: #e3f2fd;
            width: 240px !important;
            min-width: 240px !important;
            max-width: 240px !important;
            white-space: normal;
            word-wrap: break-word;
            overflow: visible;
            text-overflow: unset;
            line-height: 1.3;
        }}
        .table-info {{
            margin-top: 20px;
            padding: 12px;
            background-color: #fafafa;
            border-radius: 6px;
            border-left: 3px solid #bdc3c7;
            font-size: 11px;
            color: #7f8c8d;
        }}
        .info-row {{
            margin-bottom: 6px;
            display: flex;
            align-items: center;
        }}
        .info-row:last-child {{
            margin-bottom: 0;
        }}
        .info-label {{
            font-weight: 500;
            color: #95a5a6;
            min-width: 80px;
            margin-right: 12px;
            font-size: 11px;
        }}
        .info-content {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #7f8c8d;
            flex: 1;
            font-size: 11px;
        }}
        .period-row td:nth-child(2) {{
            white-space: nowrap;
            min-width: 200px;
            width: auto;
        }}
        .footer {{
            margin-top: 30px;
            padding: 20px 32px;
            border-top: 1px solid #ecf0f1;
            font-size: 12px;
            color: #95a5a6;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
        }}
        .footer p {{
            margin: 5px 0;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            background-color: #3498db;
            color: white;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1> KPI YTD & Monthly Summary <span class="badge">2025</span></h1>
        <p class="subtitle">集計期間: {start_date.date()} 〜 {end_date.date()}</p>
        
        <div class="table-wrapper">
            {table_html}
        </div>
        
        <div class="table-info">
            <div class="info-row">
                <span class="info-label">Period:</span>
                <span class="info-content">{period_info}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Reference:</span>
                <span class="info-content">{reference_info}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Note:</span>
                <span class="info-content">
                    {'<br>'.join(note_info)}
                </span>
            </div>
        </div>
        
        <div class="footer">
            <div>
                <p><strong>生成日時:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>データソース:</strong> {os.path.basename(ts_monthly_file)}</p>
            </div>
            <div>
                <p><strong>総取引回数:</strong> {kpi_results.loc[kpi_results['Metric'] == 'Total Trades', 'YTD in 2025'].values[0]}</p>
                <p><strong>勝率:</strong> {kpi_results.loc[kpi_results['Metric'] == 'Win Rate (WR)', 'YTD in 2025'].values[0]} | <strong>敗率:</strong> {kpi_results.loc[kpi_results['Metric'] == 'Loss Rate (LR)', 'YTD in 2025'].values[0]}</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"[SAVE] HTML: {html_path}")
print()

print("="*60)
print("[DONE] Processing completed")
print("="*60)
