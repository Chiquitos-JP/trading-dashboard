<img src="docs/quarto/latest/assets/chokotto_ver01.png" alt="プロジェクトロゴ" width="200">

# Noise-to-Value README

**Portable information → signal, not noise → actionable value.**

## 概要

本プロジェクトは、「情報を持ち運び可能なシグナルに加工する」ことを可能にするための学習プロジェクトです。残念ながら無料で程良いデータは保有していないため、身銭を切って株式売買を行う事でデータを取得します。
データ取得から特徴量生成、KPI 計算、レポート・ダッシュボード生成、成果物公開まで一連のフローを管理します。

<details>
<summary><strong>全体フロー</strong></summary>

<details>
<summary><strong>データ処理フロー</strong></summary>

```text
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

</details>

<details>
<summary><strong>実行手順</strong></summary>

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

</details>

</details>

<details>
<summary><strong>各種ファイル・ディレクトリの説明</strong></summary>

<details>
<summary><strong>Git 関連</strong></summary>

- `.github/`：GitHub 上でコードを自動実行（テストやデプロイ）したり、バグ報告・機能要望のテンプレートを管理するための設定フォルダ。通常は触る必要はありません。
- `.gitignore`：Git 管理対象外ファイル・ディレクトリのリスト
- `.env`：環境変数ファイル（API キーやパスワード等、機密情報はここに記載し.gitignore 推奨）

</details>

<details>
<summary><strong>VSCode 関連</strong></summary>

- `.vscode/`：VSCode 用の設定（タスク、拡張機能、デバッグ構成など）

</details>

<details>
<summary><strong>R 関連</strong></summary>

- `stockTrading.Rproj`：RStudio プロジェクトファイル（RStudio での作業用）
- `.Rprofile`：R 起動時に実行される設定ファイル（カスタム設定やパッケージ自動読込等）
- `.Renviron`：R の環境変数設定ファイル（API キー等の管理に利用）
- `.Rhistory`：R のコマンド履歴ファイル（自動生成、共有不要）
- `.Rproj.user/`：RStudio プロジェクトのユーザー設定（自動生成、共有不要）

</details>

<details>
<summary><strong>Python 関連</strong></summary>

- `.venv/`：Python 仮想環境ディレクトリ（依存パッケージ管理、共有不要、環境そのもの）
- `requirements_backup.txt`：Python パッケージのバックアップリスト（`pip freeze`等で生成、依存パッケージのメモ書き）

</details>

</details>

<details>
<summary><strong>参考</strong></summary>

- **プロジェクト構造**: `PROJECT_STRUCTURE.md` を参照
- **データ構造**: `data/README.md` を参照
- **出力構造**: `outputs/README.md` を参照
- **Python 共通ユーティリティ**: `config/py/README.md` を参照
- **詳細なワークフロー**: `scripts/by_timeSeries/holdingPeriod/README.md` を参照
- **R/Python の連携**: `config/R/init.R` や `config/py/bootstrap.py` で制御

</details>

<details>
<summary><strong>tips</strong></summary>

<details>
<summary><strong>特定のファイルだけ再レンダリング（キャッシュクリアあり）</strong></summary>

```bash
cd scripts/by_timeSeries/quarto
quarto render index.qmd --no-cache
```

</details>

<details>
<summary><strong>オプション実行</strong></summary>

### マーケットデータ可視化のキャッシュ機能

マーケットデータ可視化スクリプトは、SPY とセクター ETF データをキャッシュして処理時間を短縮します。通常実行ではキャッシュが有効な限り API 呼び出しをスキップします。

**実行前の準備:**

- プロジェクトルート（`stockTrading/`）に移動
- Python 仮想環境を有効化（`.venv\Scripts\Activate.ps1`）

```bash
# 通常実行（キャッシュ使用）
python scripts/by_timeSeries/marketData/market_data_visualization.py

# 強制更新（キャッシュを無視して最新データを取得）
python scripts/by_timeSeries/marketData/market_data_visualization.py --force-update
```

### run_all.py のオプション

**実行前の準備:**

- プロジェクトルート（`stockTrading/`）に移動
- Python 仮想環境を有効化（`.venv\Scripts\Activate.ps1`）

```bash
# 全実行（チェックポイント有効）
python scripts/by_timeSeries/realizedPl/run_all.py

# 強制再実行（チェックポイント無視）
python scripts/by_timeSeries/realizedPl/run_all.py --force

# 特定ステップのみ実行
python scripts/by_timeSeries/realizedPl/run_all.py --steps "楽天証券データ処理" "SBI証券データ処理"

# チェックポイント機能を無効化
python scripts/by_timeSeries/realizedPl/run_all.py --skip-checkpoint

# 可視化のみ実行（データ取得・処理をスキップ）
python scripts/by_timeSeries/realizedPl/run_visualization_only.py
```

</details>

</details>

---

# English Summary

This project is a learning initiative that enables the transformation of information into portable signals. Unfortunately, we do not have access to free, high-quality data, so we acquire data by actually trading stocks at our own expense. This project manages the entire workflow from data acquisition to feature generation, KPI calculation, report and dashboard creation, and publication of deliverables.
