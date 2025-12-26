![alt text](image.png)# 株式トレーディング分析プロジェクト README

## 概要

本プロジェクトは、株式トレーディングのデータ分析・レポート生成を自動化する R/Python 混在プロジェクトです。データ取得から特徴量生成、KPI 計算、レポート・ダッシュボード生成、成果物公開まで一連のフローを管理します。

## 全体フロー

### データ処理フロー

```
1. データ取得
   外部ソース（証券会社、API等）
       ↓
   data/raw/{source}/          # 生データ（変更不可）

2. データ処理
   data/raw/
       ↓ [処理スクリプト]
   data/processed/{data_type}_{YYYYMMDD}/  # 処理済みデータ

3. 可視化・分析
   data/processed/
       ↓ [分析スクリプト]
   outputs/interim/{category}/  # 中間可視化（HTML、CSV）

4. 最終成果物
   outputs/interim/
       ↓ [統合処理]
   outputs/figures/{analysis_type}_{YYYYMMDD}/  # 最終図表

5. レポート生成
   outputs/figures/
       ↓ [Quartoレンダリング]
   docs/quarto/latest/         # 公開用ドキュメント
```

### 実行手順

1. **初期設定・環境構築**
   - Python 仮想環境のセットアップ（`scripts/setup_python_env.ps1` または VSCode タスク「Py: setup venv」）
   - R 環境の初期化（`config/R/init.R`）
2. **データ取得・格納**
   - `data/raw/`配下に生データ・経済指標・市場データ・取引履歴等を日付ごとに保存
3. **特徴量生成・KPI 計算**
   - R スクリプト（例: `R: build features`, `R: KPI calc`タスク）や Python スクリプトで分析・計算
4. **中間生成物の出力**
   - `outputs/interim/`に HTML, CSV, 図表などを一時保存
5. **レポート・ダッシュボード生成**
   - Quarto や R/Python スクリプトで`outputs/figures/`や`docs/`に最終成果物を出力
6. **成果物公開**
   - VSCode タスク「Publish: build & push」でレポート・サイト生成＋ Git コミット＆プッシュ

## 各種ファイル・ディレクトリの説明

### Git 関連

- `.github/`：GitHub 上でコードを自動実行（テストやデプロイ）したり、バグ報告・機能要望のテンプレートを管理するための設定フォルダ。通常は触る必要はありません。
- `.gitignore`：Git 管理対象外ファイル・ディレクトリのリスト
- `.env`：環境変数ファイル（API キーやパスワード等、機密情報はここに記載し.gitignore 推奨）

### VSCode 関連

- `.vscode/`：VSCode 用の設定（タスク、拡張機能、デバッグ構成など）

### R 関連

- `stockTrading.Rproj`：RStudio プロジェクトファイル（RStudio での作業用）
- `.Rprofile`：R 起動時に実行される設定ファイル（カスタム設定やパッケージ自動読込等）
- `.Renviron`：R の環境変数設定ファイル（API キー等の管理に利用）
- `.Rhistory`：R のコマンド履歴ファイル（自動生成、共有不要）
- `.Rproj.user/`：RStudio プロジェクトのユーザー設定（自動生成、共有不要）

### Python 関連

- `.venv/`：Python 仮想環境ディレクトリ（依存パッケージ管理、共有不要、環境そのもの）
- `requirements_backup.txt`：Python パッケージのバックアップリスト（`pip freeze`等で生成、依存パッケージのメモ書き）

## 参考

- **プロジェクト構造**: `PROJECT_STRUCTURE.md` を参照
- **データ構造**: `data/README.md` を参照
- **出力構造**: `outputs/README.md` を参照
- **Python 共通ユーティリティ**: `config/py/README.md` を参照
- **詳細なワークフロー**: `scripts/by_timeSeries/holdingPeriod/README.md` を参照
- **R/Python の連携**: `config/R/init.R` や `config/py/bootstrap.py` で制御

---

# English Summary

This project automates stock trading analytics using R and Python. See above for the workflow and file descriptions. For details, refer to the scripts and config files in each directory.
