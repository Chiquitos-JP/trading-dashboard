# Copilot Instructions for AI Agents

## 概要

このリポジトリは、株式トレーディングのデータ分析・レポート生成を目的とした R/Python 混在プロジェクトです。データ取得、マスターデータ管理、KPI 計算、レポート・ダッシュボード生成までを自動化しています。

## ディレクトリ構成

```
stockTrading/
├── scripts/
│   ├── runners/                    # 実行エントリーポイント
│   │   ├── run_all.py             # 全実行（推奨）
│   │   ├── run_visualization_only.py
│   │   ├── run_render_only.py
│   │   └── run_quarto_only.py
│   ├── by_timeSeries/              # 分析・可視化スクリプト
│   │   ├── common/                # 共通モジュール（optimized_data_pipeline.py）
│   │   ├── realizedPl/            # 実現損益分析
│   │   ├── holdingPeriod/         # 保有期間分析
│   │   ├── quarto/                # Quartoテンプレート・設定
│   │   └── ...
│   └── cleanup_old_files.py
├── data/
│   └── trading_account/
│       ├── realized_pl/
│       │   ├── raw/               # 生CSV（ソース）
│       │   ├── master/            # 統合マスター（Parquet）
│       │   └── aggregated/        # 集計データ
│       └── transaction/
├── config/
│   ├── py/                        # Python設定・ユーティリティ
│   └── R/                         # R設定・ユーティリティ
├── outputs/                       # 中間出力（figures, interim）
├── docs/                          # GitHub Pages公開用
│   └── quarto/latest/            # 最新レポート
└── README.md
```

## 主要ワークフロー

### パイプライン実行

```bash
# 全実行（データ処理→可視化→レンダリング）
python scripts/runners/run_all.py

# 可視化のみ（データ処理済みの場合）
python scripts/runners/run_visualization_only.py

# レンダリングのみ（週間レビュー生成＋Quarto）
python scripts/runners/run_render_only.py

# オプション
python scripts/runners/run_all.py --force        # キャッシュ無視
python scripts/runners/run_all.py --render-only  # レンダリングのみ
```

### データフロー

```
raw CSV → optimized_data_pipeline.py → master Parquet → 分析スクリプト → outputs/ → Quarto → docs/
```

## プロジェクト固有のパターン

- **マスターデータ**: `data/trading_account/*/master/` に統合 Parquet を保持
- **差分更新**: `optimized_data_pipeline.py` が新規レコードのみ処理
- **パス管理**: `config/py/data_paths.py` で統一管理
- **キャッシュ**: 可視化スクリプトはソースデータ更新時のみ再生成

## 依存

- Python: pandas, polars, plotly, pyarrow, great_tables
- R: tidyverse, data.table, lubridate
- Quarto: ドキュメント/ダッシュボード生成

## 参考

- `README.md`: プロジェクト全体の説明
- `config/py/README.md`: Python 設定ファイルの説明

---

# English Summary

- This project automates stock trading analytics using R and Python.
- Entry points are in `scripts/runners/` (run_all.py is the main script).
- Data flows: raw CSV → master Parquet → analysis → Quarto reports.
- Add new analyses under `scripts/by_timeSeries/` and register in run_all.py's SCRIPTS list.
