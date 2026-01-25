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
1. データ取得（Raw CSV）
   外部ソース（楽天証券、SBI証券）
       ↓
   data/trading_account/{data_type}/raw/{broker}/  # 生データ（ソース）

2. マスターデータ更新（Optimized Pipeline）
   data/.../raw/
       ↓ [optimized_data_pipeline.py]
   data/trading_account/{data_type}/master/        # 統合マスター（Parquet）
       ├── realized_pl_merged.parquet              # 実現損益マスター（全ブローカー統合）
       ├── realized_pl_rakuten.parquet             # 楽天個別マスター
       └── realized_pl_sbi.parquet                 # SBI個別マスター

3. 集計データ生成
   data/.../master/
       ↓ [自動生成]
   data/trading_account/{data_type}/aggregated/    # 集計データ
       ├── monthly_summary.parquet                 # 月次サマリー
       └── kpi_metrics.parquet                     # KPI指標

4. 可視化・分析
   data/.../master/ + data/.../aggregated/
       ↓ [分析スクリプト]
   outputs/interim/{category}/                     # 中間可視化（HTML）

5. レポート生成
   outputs/interim/
       ↓ [Quartoレンダリング]
   docs/quarto/latest/                             # 公開用ドキュメント
```

</details>

<details>
<summary><strong>ディレクトリ構造</strong></summary>

```text
data/trading_account/
├── realized_pl/                    # 実現損益データ
│   ├── raw/                        # 生CSV（ソース of truth）
│   │   ├── rakuten/               # 楽天証券
│   │   └── sbi/                   # SBI証券
│   ├── master/                     # マスターParquet（統合・正規化済み）
│   │   ├── realized_pl_merged.parquet
│   │   ├── realized_pl_rakuten.parquet
│   │   ├── realized_pl_sbi.parquet
│   │   └── show_tbl.R             # マスター確認用Rスクリプト
│   └── aggregated/                 # 集計データ
│       ├── monthly_summary.parquet
│       └── kpi_metrics.parquet
└── transaction/                    # 取引履歴データ
    ├── raw/
    │   ├── rakuten/
    │   └── sbi/
    └── master/
        ├── transaction_merged.parquet
        ├── transaction_rakuten.parquet
        └── transaction_sbi.parquet
```

</details>

<details>
<summary><strong>実行手順</strong></summary>

1. **初期設定・環境構築**
   - Python 仮想環境のセットアップ（`scripts/setup_python_env.ps1` または VSCode タスク「Py: setup venv」）
   - R 環境の初期化（`config/R/init.R`）

2. **データ取得・格納**
   - `data/trading_account/realized_pl/raw/` 配下に楽天・SBIの生CSVを格納
   - `data/trading_account/transaction/raw/` 配下に取引履歴CSVを格納
   
   **生データの取得方法:**
   | 証券会社 | データ種別 | 取得条件 | 出力形式 |
   |---------|-----------|---------|---------|
   | 楽天 | 実現損益 | すべて、期間指定なし | CSV |
   | 楽天 | 取引履歴 | すべて、期間指定なし | CSV |
   | SBI | 信用決済明細 | すべて、期間指定なし、行数上限5,000行 | CSV |
   | SBI | 約定履歴 | すべて、期間指定なし（過去2年間のみ）、行数上限1,000行 | CSV |

3. **パイプライン実行（一括）**
   ```bash
   python scripts/by_timeSeries/runners/run_all.py
   ```
   これにより以下が自動実行されます:
   - マスターデータの差分更新
   - 月次サマリー・KPI生成
   - 週間レビュー生成
   - Quartoレンダリング
   - ダッシュボードHTML出力

4. **成果物公開**
   - VSCode タスク「Publish: build & push」でGitコミット＆プッシュ

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

<details>
<summary><strong>主要スクリプト</strong></summary>

**実行系（scripts/by_timeSeries/runners/）**
- `run_all.py`：一括実行スクリプト（推奨）
- `run_visualization_only.py`：可視化のみ実行
- `run_render_only.py`：レンダリングのみ実行
- `run_quarto_only.py`：Quartoのみ実行

**分析系（scripts/by_timeSeries/）**
- `common/optimized_data_pipeline.py`：データパイプライン（マスター更新・集計生成）
- `holdingPeriod/risk_analysis.py`：リスク分析・ポジション計算
- `holdingPeriod/holding_period_visualization.py`：保有期間可視化
- `cleanup_old_files.py`：古い出力ファイルのクリーンアップ

</details>

</details>

<details>
<summary><strong>TidyTuesday / MakeoverMonday 投稿フロー</strong></summary>

週次データビジュアライゼーション投稿の作成・レンダリング手順です。  
`run_all.py`や週間レビュー（`run_weekly_review.py`）とは別管理で、専用スクリプト `run_weekly_posts.py` を使用します。

<details>
<summary><strong>ディレクトリ構造</strong></summary>

```text
scripts/by_timeSeries/quarto/posts/
├── 2026-01-27-makeover-monday/    # MakeoverMonday投稿（Python）
│   ├── index.qmd                  # Quartoソース
│   └── thumbnail.svg              # サムネイル画像
├── 2026-01-28-tidytuesday/        # TidyTuesday投稿（R）
│   ├── index.qmd                  # Quartoソース
│   ├── thumbnail.svg              # サムネイル画像
│   ├── prepare_data.py            # データ準備スクリプト（必要に応じて）
│   └── data/                      # ローカルデータ（.gitignore対象）
│       └── monthly_balance.parquet
└── ...
```

**命名規則**: `YYYY-MM-DD-{makeover-monday|tidytuesday}/`  
**日付**: 月曜日=MakeoverMonday、火曜日=TidyTuesday

</details>

<details>
<summary><strong>完全ワークフロー（アイデアから公開まで）</strong></summary>

### Phase 1: アイデア・企画
1. **題材を決定**: 可視化したいデータや分析テーマを決める
2. **チャート設計**: どのような可視化が効果的か検討
   - 時系列チャート、散布図、積み上げグラフ等

### Phase 2: ファイル作成
3. **ディレクトリ作成**
   ```powershell
   mkdir scripts/by_timeSeries/quarto/posts/2026-01-27-makeover-monday
   mkdir scripts/by_timeSeries/quarto/posts/2026-01-28-tidytuesday
   mkdir scripts/by_timeSeries/quarto/posts/2026-01-28-tidytuesday/data
   ```

4. **index.qmd 作成**（各フォルダに）
   - MakeoverMonday: Python + Plotly/Matplotlib
   - TidyTuesday: R + ggplot2

5. **thumbnail.svg 作成**（400x300px推奨）

6. **prepare_data.py 作成**（TidyTuesday用、データ準備が必要な場合）

### Phase 3: レンダリング＆公開

**Step 1: TidyTuesday用データ準備**
```powershell
cd scripts/by_timeSeries/quarto/posts/2026-01-28-tidytuesday
py prepare_data.py
```

**Step 2: MakeoverMonday（Python）レンダリング**
```powershell
cd scripts/by_timeSeries/runners
py run_weekly_posts.py --date 2026-01-27
```
または直接Quartoでレンダリング:
```powershell
cd scripts/by_timeSeries/quarto
quarto render "posts\2026-01-27-makeover-monday\index.qmd"
```

**Step 3: Git同期**
```powershell
git add .
git commit -m "Add MakeoverMonday/TidyTuesday posts"
git push
```

**Step 4: TidyTuesday（R）GitHub Actionsでレンダリング**
1. GitHub → **Actions** タブ
2. **Render Weekly Posts (TidyTuesday/MakeoverMonday)** を選択
3. **Run workflow** → Post type: `tidytuesday` を選択
4. 自動でレンダリング→コミット→プッシュ

**Step 5: ローカル同期（必要に応じて）**
```powershell
git pull
```

</details>

<details>
<summary><strong>ワークフロー全体図</strong></summary>

```text
[ローカル - Cursor]                          [GitHub Actions]
    │                                             │
    │ 1. アイデア決定・ファイル作成               │
    │    ├── index.qmd (Python/R)                 │
    │    ├── thumbnail.svg                        │
    │    └── prepare_data.py (TidyTuesday用)      │
    │                                             │
    │ 2. TidyTuesday用データ準備                  │
    │    py prepare_data.py                       │
    │    → data/monthly_balance.parquet生成       │
    │                                             │
    │ 3. MakeoverMonday (Python) レンダリング     │
    │    py run_weekly_posts.py                   │
    │    → docs/quarto/latest/ にHTML生成         │
    │                                             │
    │ 4. git push                                 │
    └─────────────────────────────────────────────►
                                                  │
                                                  │ 5. TidyTuesday (R) レンダリング
                                                  │    Actions → Run workflow
                                                  │    ├── prepare_data.py 実行
                                                  │    ├── quarto render 実行
                                                  │    └── 自動コミット&プッシュ
                                                  │
    ◄─────────────────────────────────────────────┘
    │
    │ 6. git pull（GitHub Actions完了後）
    │
    ▼
  [公開完了] https://chiquitos-jp.github.io/trading-dashboard/quarto/latest/analysis.html
```

</details>

<details>
<summary><strong>コマンドリファレンス</strong></summary>

**run_weekly_posts.py オプション**
```powershell
# MakeoverMondayのみレンダリング（デフォルト）
py run_weekly_posts.py

# 特定日付のポストをレンダリング
py run_weekly_posts.py --date 2026-01-27

# 全ポスト（TidyTuesday含む）をレンダリング
py run_weekly_posts.py --type all

# 一覧表示のみ（レンダリングしない）
py run_weekly_posts.py --list

# プレビュー起動
py run_weekly_posts.py --preview
```

**GitHub Actions ワークフロー**
- ワークフロー名: `Render Weekly Posts (TidyTuesday/MakeoverMonday)`
- ファイル: `.github/workflows/render-posts.yml`
- Post type選択肢: `all` / `tidytuesday` / `makeover-monday`

</details>

<details>
<summary><strong>注意事項</strong></summary>

**TidyTuesdayの`data/`フォルダ**
- `.gitignore`で除外されているため、GitHub Actionsでは`prepare_data.py`で生成
- ローカルで実行する場合は先に`py prepare_data.py`を実行

**ARM64 Windows環境（Surface Laptop 7等）**
- x64版Rとの互換性問題により、ローカルでのQuarto + Rレンダリングが失敗する
- TidyTuesdayはGitHub Actions（x64 Linux環境）でレンダリング推奨

**ランディングページ（analysis.html）**
- Quartoの`listing`機能により、`posts/`フォルダ内の全投稿が自動リストアップ
- 投稿フォルダとindex.qmdが存在すれば、レンダリング前でもサムネイルと概要が表示される

</details>

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

### run_all.py のオプション

**実行前の準備:**

- プロジェクトルート（`stockTrading/`）に移動
- Python 仮想環境を有効化（`.venv\Scripts\Activate.ps1`）

```bash
# 全実行
python scripts/by_timeSeries/runners/run_all.py

# レンダリングのみ（データ処理をスキップ）
python scripts/by_timeSeries/runners/run_all.py --render-only

# 可視化のみ（データ処理をスキップ）
python scripts/by_timeSeries/runners/run_visualization_only.py

# 強制再実行（キャッシュ無視）
python scripts/by_timeSeries/runners/run_all.py --force
```

### マスターデータの確認（R）

```r
# Rで実行
source("data/trading_account/realized_pl/master/show_tbl.R")
```

### データパイプラインの単独実行

```bash
python scripts/by_timeSeries/common/optimized_data_pipeline.py
```

</details>

</details>

---

# English Summary

This project is a learning initiative that enables the transformation of information into portable signals. Unfortunately, we do not have access to free, high-quality data, so we acquire data by actually trading stocks at our own expense. This project manages the entire workflow from data acquisition to feature generation, KPI calculation, report and dashboard creation, and publication of deliverables.
