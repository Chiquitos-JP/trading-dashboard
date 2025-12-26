# Copilot Instructions for AI Agents

## 概要

このリポジトリは、株式トレーディングのデータ分析・レポート生成を目的とした R/Python 混在プロジェクトです。データ取得、特徴量生成、KPI 計算、レポート・ダッシュボード生成までを自動化しています。

## ディレクトリ構成と主要コンポーネント

- `00_config/`：設定ファイル（`config.yml`）、初期化スクリプト（`init.R`/`python_bootstrap.py`）
- `data/`：データストレージ（生データ・加工済みデータ、経済指標、市場データ、取引履歴等）
- `output_intermediate/`：中間生成物（HTML, CSV, 図表）
- `scripts/`：分析ロジック（by_timeSeries 配下に各種分析）
- `output/`：最終成果物（レポート、図表、ページ）
- `docs/`：公開用ドキュメント、Quarto 出力

## 主要ワークフロー

- **Python 仮想環境セットアップ**：
  - `scripts/setup_python_env.ps1` または VSCode タスク「Py: setup venv」
- **特徴量生成・KPI 計算・レポート生成**：
  - R スクリプトは `Rscript` コマンドまたは VSCode タスク（例:「R: build features」「R: KPI calc」「R: render report」）
  - Python 分析は `scripts/by_timeSeries/xxx/run_all.py` などを直接実行
- **成果物公開**：
  - VSCode タスク「Publish: build & push」でレポート・サイト生成＋ Git コミット＆プッシュ

## プロジェクト固有のパターン・注意点

- R と Python の連携は`00_config/init.R`や`python_bootstrap.py`で制御
- データは日付ごとにサブディレクトリ/ファイルで管理（例: `output/figures/holdingPeriod_YYYYMMDD/`）
- 分析スクリプトは「by_timeSeries」配下に時系列ごとに整理
- 新しい分析を追加する場合は、`run_all.py`や SCRIPTS リストへの登録を推奨
- 設定値やパスは`config.yml`を参照

## 依存・外部連携

- R: tidyverse, data.table, lubridate 等
- Python: pandas, numpy, pyarrow 等
- Quarto でドキュメント/ダッシュボード生成
- Git でバージョン管理、成果物公開

## 参考ファイル

- `scripts/by_timeSeries/holdingPeriod/README.md`：データ入出力例、分析追加方法
- `00_config/config.yml`：全体設定
- `scripts/setup_python_env.ps1`：Python 環境構築

---

# English Summary

- This project automates stock trading analytics using R and Python.
- Data flows: raw data → feature/KPI generation → report/dashboard output.
- Use VSCode tasks or scripts for builds; see above for key commands.
- Add new analyses under `scripts/by_timeSeries/` and register in `run_all.py`.
- See `scripts/by_timeSeries/holdingPeriod/README.md` for concrete workflow examples.
