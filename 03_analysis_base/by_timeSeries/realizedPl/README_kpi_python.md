# KPI 分析・可視化スクリプト（Python 版）

R スクリプトを Python に移植した、取引 KPI の分析・可視化ツールです。

## 📁 ファイル構成

```text
03_analysis_base/by_timeSeries/realizedPl/
├── kpi_analysis.py         # データ読込・前処理・月次集計
├── kpi_visualization.py    # グラフ作成（P1-P9）
└── README_kpi_python.md    # このファイル
```

## 🚀 使い方

### 1. データ分析（前処理・集計）

```powershell
python kpi_analysis.py
```

**処理内容:**

- `merged_trading_summary_*.csv` を読込（最新の日付フォルダから自動検索）
- 年月列の整形（ISO 形式: YYYY-MM）
- NYSE 営業日数の計算・結合
- ブローカー別 → 月次全体集計
- 将来テンプレート作成（2026-12 まで）
- 累積損益計算

**出力:**

- `checkpoints/01_raw_import_YYYYMMDD.pkl` - 生データ
- `checkpoints/02_merged_with_mdays_YYYYMMDD.pkl` - 営業日数結合後
- `checkpoints/03_ts_monthly_YYYYMMDD.pkl` - 月次集計
- `checkpoints/04_plot_base_YYYYMMDD.pkl` - プロットベース
- `checkpoints/05_plot_df_YYYYMMDD.pkl` - プロット用データ

### 2. 可視化（グラフ作成）

```powershell
python kpi_visualization.py
```

**処理内容:**

- checkpoint 5 (`plot_df`) を読込
- 9 つのパネルグラフを作成（P1-P9）

**出力:**

- `04_output/figures/realizedPl_YYYYMMDD/P1_cumulative_trend_YYYYMMDD.png`
- `04_output/figures/realizedPl_YYYYMMDD/P2_monthly_gain_YYYYMMDD.png`
- ... (P9 まで)

## 📊 作成されるグラフ

### Left Panel

- **P1: 累積損益** - 折れ線グラフ（実績/予測、ゼロクロス色分け）
- **P2: 月次損益** - 棒グラフ（プラス/マイナス色分け）
- **P3: 日次平均損益** - 折れ線グラフ

### Center Panel

- **P4: Win Rate** - 年次比較折れ線
- **P5: 取引回数** - 年次比較棒グラフ
- **P6: 実取引日数** - 年次比較棒グラフ

### Right Panel

- **P7: ROI** - 年次比較折れ線
- **P8: 平均取得コスト/取引** - 年次比較折れ線
- **P9: Risk Reward** - 棒グラフ（左軸）+ 折れ線（右軸）

## 🔄 ワークフロー

```text
1. mergedPl.py を実行
   ↓
   merged_trading_summary_YYYYMMDD.csv 生成

2. kpi_analysis.py を実行
   ↓
   checkpoints/*.pkl 生成

3. kpi_visualization.py を実行
   ↓
   04_output/figures/realizedPl_YYYYMMDD/*.png 生成
```

## 📦 依存パッケージ

```bash
pip install pandas numpy matplotlib seaborn pandas-market-calendars
```

または:

```bash
pip install -r requirements.txt
```

## 🔧 カスタマイズ

### 期間変更

`kpi_visualization.py` 内:

```python
start_date = pd.to_datetime("2025-01-01")
end_date = pd.to_datetime("2025-12-01")
```

### カラーパレット変更

```python
COLOR_PROFIT = '#1F77B4'  # 利益の色
COLOR_LOSS = '#D62728'    # 損失の色

BIZ_COLORS = {
    2024: '#1F77B4',
    2025: '#2CA02C',
    2026: '#FF7F0E',
}
```

### グラフサイズ変更

```python
fig, ax = plt.subplots(figsize=(10, 4))  # (幅, 高さ)
```

## 💾 Checkpoint 機能

各処理段階で pickle 形式保存:

```python
# checkpoint読込例
import pandas as pd

# 月次集計データ
ts_monthly = pd.read_pickle("checkpoints/03_ts_monthly_20251013.pkl")

# プロット用データ
plot_df = pd.read_pickle("checkpoints/05_plot_df_20251013.pkl")
```

## 📝 注意事項

1. **入力ファイル**: `merged_trading_summary_*.csv` が必須
2. **日付フォルダ**: 当日の `realizedPl_YYYYMMDD/` から自動検索
3. **営業日数**: `pandas_market_calendars` 未インストール時は 21 日固定
4. **グラフフォント**: 日本語表示には別途フォント設定が必要

## 🆚 R 版との違い

| 項目       | R 版                      | Python 版       |
| ---------- | ------------------------- | --------------- |
| データ保存 | `.rds`                    | `.pkl` (pickle) |
| グラフ保存 | `patchwork`               | `matplotlib`    |
| 営業日計算 | `pandas_market_calendars` | 同左            |
| レイアウト | 自動統合                  | 個別 PNG 保存   |

## 🔮 今後の拡張

- [ ] 統合レイアウト（1 枚のダッシュボード）
- [ ] Quarto/Jupyter レポート対応
- [ ] インタラクティブグラフ（Plotly）
- [ ] KPI サマリーテーブル生成
- [ ] 日次データ分析

## 📧 問い合わせ

エラーや改善提案は Issues または PR で報告してください。
