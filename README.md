<img src="docs/quarto/latest/assets/chokotto_ver01.png" alt="プロジェクトロゴ" width="200">

# Noise-to-Value

> **Portable information → signal, not noise → actionable value.**

「多様な情報からシグナルを発見する」ための個人学習プロジェクトです。
身銭を切って株式売買を行いデータを取得し、特徴量生成・KPI 計算・レポート生成・成果物公開までの一連のフローを管理しながら、AI 活用や分析手法を学習しています。

| | |
|---|---|
| **公開サイト** | [trading-dashboard](https://chiquitos-jp.github.io/trading-dashboard/quarto/latest/analysis.html) |
| **技術スタック** | Python (pandas, Plotly) · R (ggplot2) · Quarto · GitHub Actions · GitHub Pages |
| **実行環境** | Windows 11 ARM64 · PowerShell · `py` コマンド |

---

## データパイプライン

<details>
<summary><strong>処理フロー（メダリオンアーキテクチャ）</strong></summary>

```text
1. データ取得（Raw CSV）
   楽天証券 / SBI証券から手動ダウンロード
       ↓
   data/trading_account/{data_type}/raw/{broker}/

2. 正規化（Bronze）
       ↓ [optimized_data_pipeline.py]
   data/trading_account/{data_type}/bronze/
       ├── rakuten.parquet          # 楽天（正規化済み）
       └── rakuten_jp.parquet       # 楽天（国内銘柄）

3. 統合（Silver）
       ↓ [optimized_data_pipeline.py]
   data/trading_account/{data_type}/silver/
       └── realized_pl.parquet      # 全ブローカー統合

4. 集計・KPI（Gold）
       ↓ [kpi_analysis.py]
   data/trading_account/realized_pl/gold/
       ├── monthly_pl.parquet       # 月次損益
       ├── monthly_pl_jp.parquet    # 国内月次
       ├── monthly_pl_us.parquet    # 米国月次
       ├── monthly_pl_ytd.parquet   # 年初来
       └── kpi_metrics.parquet      # KPI指標

5. 可視化・分析
       ↓ [各種可視化スクリプト + AI分析]
   outputs/interim/{category}/      # 中間可視化（HTML）

6. レポート生成
       ↓ [Quarto レンダリング]
   docs/quarto/latest/              # 公開用ドキュメント
```

</details>

<details>
<summary><strong>ディレクトリ構造</strong></summary>

```text
data/trading_account/
├── realized_pl/                     # 実現損益データ
│   ├── raw/                         # 生 CSV（Source of Truth）
│   │   ├── rakuten/
│   │   └── sbi/
│   ├── bronze/                      # 正規化 Parquet（ブローカー別）
│   ├── silver/                      # 統合 Parquet
│   │   └── realized_pl.parquet
│   └── gold/                        # 集計・KPI
│       ├── monthly_pl.parquet
│       └── kpi_metrics.parquet
├── transaction/                     # 取引履歴データ
│   ├── raw/
│   │   ├── rakuten/
│   │   └── sbi/
│   ├── bronze/
│   └── silver/
│       └── transaction.parquet
└── account_balance/
    └── daily_balance.parquet        # 日次口座残高
```

</details>

---

## セットアップ & 実行

<details>
<summary><strong>環境構築</strong></summary>

```powershell
# Python 仮想環境のセットアップ
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**前提条件:**

- Python 3.12+（`py` コマンドで起動）
- Quarto CLI（ローカルインストール済み。R knitr エンジンはローカル不可）
- `.env` に `OPENAI_API_KEY` を設定（なくてもフォールバック動作する）
- インターネット接続（FRED 為替データ取得に必要）

</details>

<details>
<summary><strong>データ取得 & 格納</strong></summary>

以下の CSV を手動ダウンロードし、対応するフォルダに格納します。

| 証券会社 | データ種別 | 取得条件 | 格納先 |
|---|---|---|---|
| 楽天 | 実現損益 | すべて、期間指定なし | `data/.../realized_pl/raw/rakuten/` |
| 楽天 | 取引履歴 | すべて、期間指定なし | `data/.../transaction/raw/rakuten/` |
| SBI | 信用決済明細 | すべて、上限 5,000行 | `data/.../realized_pl/raw/sbi/` |
| SBI | 約定履歴 | すべて、過去2年間、上限 1,000行 | `data/.../transaction/raw/sbi/` |

</details>

<details>
<summary><strong>パイプライン実行</strong></summary>

```powershell
# 一括実行（推奨 — チェックポイント機能で処理済みステップは自動スキップ）
py scripts/by_timeSeries/runners/run_all.py
```

**実行ステップ:**

| # | ステップ | 内容 |
|---|---|---|
| 1 | データ処理 | マスターデータの差分更新・統合 |
| 2 | 為替取得 | FRED 為替レート更新 |
| 3 | KPI 分析 | KPI 指標の算出 |
| 4 | 可視化 | グラフ作成（保有期間、リスク、経済指標、マクロ、マーケット） |
| 5 | AI 分析 | KPI データに基づくコメント生成 |
| 6 | レビュー生成 | 週間レビュー記事（Weekly Review）の自動作成 |
| 7 | レンダリング | Quarto でレポートサイトを生成 |
| 8 | ダッシュボード | Panel 静的 HTML 出力 |

**オプション:**

```powershell
py scripts/by_timeSeries/runners/run_all.py --force               # 強制再実行（チェックポイント無視）
py scripts/by_timeSeries/runners/run_all.py --render-only          # Quarto レンダリングのみ
py scripts/by_timeSeries/runners/run_all.py --visualization-only   # 可視化のみ
py scripts/by_timeSeries/runners/run_all.py --data-only            # データ処理のみ
py scripts/by_timeSeries/runners/run_all.py --steps "楽天証券データ処理" "SBI証券データ処理"  # 特定ステップのみ
```

**部分実行用スクリプト:**

| スクリプト | 用途 |
|---|---|
| `run_weekly_review.py` | Weekly Review + Quarto + Dashboard |
| `run_weekly_posts.py` | TidyTuesday / MakeoverMonday |
| `run_visualization.py` | 可視化のみ |
| `run_quarto_rebuild.py` | 既存 .qmd の Quarto 再ビルド |

> これらは `scripts/by_timeSeries/runners/` に配置。
> 迷ったら `run_all.py` を実行すれば OK（チェックポイントで冪等）。

</details>

<details>
<summary><strong>成果物公開</strong></summary>

```powershell
git add .
git commit -m "Weekly review YYYY-MM-DD"
git push
```

Quarto 出力は `docs/quarto/latest/` に生成され、GitHub Pages で公開されます。

</details>

---

## 週次投稿（TidyTuesday / MakeoverMonday）

<details>
<summary><strong>投稿フローの概要</strong></summary>

**TidyTuesday（R）→ MakeoverMonday（Python）** の順でワークフローを回します。

| 投稿 | 言語 | 役割 | 投稿日 |
|---|---|---|---|
| **TidyTuesday** | R (ggplot2) | アイデア探索・プロトタイピング | 火曜 |
| **MakeoverMonday** | Python (Plotly) | 仕組化・再現性の確保 | 月曜 |

```text
TidyTuesday (R)               MakeoverMonday (Python)
    │                               │
    │ 1. アイデア探索               │ 3. 同じ題材を Python で実装
    │ 2. ggplot2 でプロトタイプ     │ 4. 仕組化・自動化可能な形に
    ▼                               ▼
  火曜投稿 ─────────────────────▶ 翌週月曜投稿
```

- 両者は **同じ題材・同じ可視化** を扱う
- TidyTuesday で試行錯誤し、MakeoverMonday で整理・仕組化
- R → Python の移植練習にもなる

**投稿フォルダ:**

```text
scripts/by_timeSeries/quarto/posts/
├── 2026-03-16-makeover-monday/   # MakeoverMonday（Python）
│   ├── index.qmd                 # Quarto ソース
│   └── thumbnail.svg             # サムネイル画像
├── 2026-03-17-tidytuesday/       # TidyTuesday（R）
│   ├── index.qmd
│   ├── thumbnail.svg
│   ├── prepare_data.py           # データ準備（必要に応じて）
│   └── data/                     # ローカルデータ
└── _template_*.qmd               # テンプレート
```

**命名規則**: `YYYY-MM-DD-{makeover-monday|tidytuesday}/`

</details>

<details>
<summary><strong>作成〜公開ワークフロー</strong></summary>

### Phase 1: ファイル作成（ローカル）

1. ディレクトリ・`index.qmd`・`thumbnail.svg` を作成
2. TidyTuesday の場合は `prepare_data.py` も作成

### Phase 2: レンダリング & 公開

```text
[ローカル]                              [GitHub Actions]
    │                                        │
    │ 1. MakeoverMonday (Python) をローカルレンダリング
    │    py scripts/by_timeSeries/runners/run_weekly_posts.py
    │                                        │
    │ 2. git push ──────────────────────────►│
    │                                        │
    │                                        │ 3. TidyTuesday (R) を Actions でレンダリング
    │                                        │    → render-posts.yml (post_type=tidytuesday)
    │                                        │    → prepare_data.py 実行 → quarto render
    │                                        │    → 自動 commit & push
    │◄───────────────────────────────────────│
    │ 4. git pull                            │
```

**CI コマンド（gh CLI）:**

```powershell
# レンダリング実行
gh workflow run "render-posts.yml" -f post_type=tidytuesday --repo Chiquitos-JP/trading-dashboard
gh workflow run "render-posts.yml" -f post_type=makeover-monday -f post_date=2026-03-16 --repo Chiquitos-JP/trading-dashboard

# 状況確認
gh run list --workflow=render-posts.yml --limit 3 --repo Chiquitos-JP/trading-dashboard
```

**ARM64 Windows の制約**: x64 版 R との互換性問題により、ローカルでの Quarto + R レンダリングは不可。TidyTuesday は GitHub Actions（x64 Linux）でレンダリングします。

</details>

<details>
<summary><strong>X (Twitter) 自動投稿</strong></summary>

### 仕組み（per-post frontmatter 方式）

各 `index.qmd` の YAML frontmatter にある `x-posted: true/false` で投稿状態を管理します。

1. 新規記事作成時に `x-posted: false` を設定
2. `post-to-x.yml` が `x-posted: false` の最古の記事を自動投稿
3. 投稿後に `x-posted: true` に更新し、自動 commit & push

### 自動投稿スケジュール

| 曜日 | 時刻 | 投稿タイプ |
|---|---|---|
| 月曜 | 9:00 JST | MakeoverMonday（最古の未投稿記事） |
| 火曜 | 9:00 JST | TidyTuesday（最古の未投稿記事） |

### 画像添付

| 投稿タイプ | 画像ソース |
|---|---|
| TidyTuesday (R) | `index_files/figure-html/*.png`（ggplot2 自動出力） |
| MakeoverMonday (Python) | `chart-1.png`（Plotly/Matplotlib 静的出力） |

MakeoverMonday では最初のチャートに画像出力処理を追加する必要があります。

```python
# Plotly の場合
fig.write_image("chart-1.png", width=1200, height=600, scale=2)

# Matplotlib の場合
fig.savefig("chart-1.png", dpi=150, bbox_inches='tight', facecolor='white')
```

### 手動実行

```powershell
gh workflow run "post-to-x.yml" -f post_type=makeover-monday --repo Chiquitos-JP/trading-dashboard
gh workflow run "post-to-x.yml" -f post_type=tidytuesday --repo Chiquitos-JP/trading-dashboard
```

### X API 設定

**GitHub Secrets（必須）:**

| Secret 名 | 説明 |
|---|---|
| `X_API_KEY` | X API Key |
| `X_API_SECRET` | X API Key Secret |
| `X_ACCESS_TOKEN` | X Access Token |
| `X_ACCESS_TOKEN_SECRET` | X Access Token Secret |

**料金**: Pay-per-use — $0.01/投稿。月 8 回投稿で約 $0.08/月。

</details>

---

## AI 開発環境

<details>
<summary><strong>Cursor IDE + Claude Code（CLI）デュアル環境</strong></summary>

本プロジェクトは **Cursor IDE** と **Claude Code（CLI）** の両方で AI エージェント駆動が可能です。

| ツール | 設定ファイル | 用途 |
|---|---|---|
| Cursor IDE | `.cursor/rules/*.mdc` | IDE 内での AI アシスタント（ルールベース） |
| Claude Code | `CLAUDE.md` + `.claude/` | CLI での自律エージェント駆動 |

### Claude Code エージェント

| エージェント | ファイル | 役割 |
|---|---|---|
| weekly-report | `.claude/agents/weekly-report.md` | 週次レビューの自律生成 |
| makeover-monday | `.claude/agents/makeover-monday.md` | MakeoverMonday 投稿作成 |
| tidytuesday | `.claude/agents/tidytuesday.md` | TidyTuesday 投稿作成 |
| ci-monitor | `.claude/agents/ci-monitor.md` | GitHub Actions 監視・修復 |

### Claude Code コマンド

| コマンド | 説明 |
|---|---|
| `/run-pipeline` | フルパイプライン実行 |
| `/weekly-review` | レビュー生成 + レンダリング |
| `/new-mm` | MakeoverMonday 投稿スキャフォールド |
| `/new-tt` | TidyTuesday 投稿スキャフォールド |
| `/render` | Quarto レンダリング |
| `/ci-status` | CI 実行状況確認 |

</details>

---

## リファレンス

<details>
<summary><strong>GitHub Actions ワークフロー一覧</strong></summary>

| ワークフロー | ファイル | 用途 |
|---|---|---|
| Render Weekly Posts | `render-posts.yml` | TidyTuesday / MakeoverMonday のレンダリング |
| Post to X (Twitter) | `post-to-x.yml` | X 自動投稿（月曜 MM / 火曜 TT） |
| Post Sunday Markets | `post-sunday-markets.yml` | 日曜マーケット情報投稿 |
| Post Weekly Calendar | `post-weekly-calendar.yml` | 週間経済カレンダー投稿 |

</details>

<details>
<summary><strong>ファイル・ディレクトリの説明</strong></summary>

**プロジェクトルート:**

| ファイル / ディレクトリ | 説明 |
|---|---|
| `scripts/` | 分析・可視化スクリプト（非公開） |
| `data/` | 取引・マクロデータ（非公開） |
| `outputs/` | 中間出力（非公開） |
| `docs/` | GitHub Pages 公開用（Quarto 出力先） |
| `config/` | 設定ファイル（非公開） |
| `.github/` | GitHub Actions ワークフロー・テンプレート |
| `CLAUDE.md` | Claude Code プロジェクトメモリ（セッション自動ロード） |
| `.claude/` | Claude Code 設定・エージェント・コマンド |
| `.cursor/` | Cursor IDE ルール（非公開） |
| `.venv/` | Python 仮想環境 |
| `requirements.txt` | Python パッケージ一覧（バージョン固定） |
| `.env` | 環境変数（API キー等、.gitignore 対象） |
| `.gitignore` | Git 管理対象外ファイルのリスト |

**R 関連（Positron で使用）:**

| ファイル | 説明 |
|---|---|
| `stockTrading.Rproj` | RStudio / Positron プロジェクトファイル |
| `.Rprofile` | R 起動時の設定ファイル |
| `.Renviron` | R 環境変数設定（API キー管理） |

**主要スクリプト（`scripts/by_timeSeries/`）:**

| パス | 役割 |
|---|---|
| `runners/run_all.py` | 一括実行パイプライン（推奨エントリポイント） |
| `common/optimized_data_pipeline.py` | データパイプライン（Raw → Bronze → Silver） |
| `realizedPl/ai_analyzer.py` | AI によるコメント生成 |
| `macroData/macro_data.py` | マクロデータ取得 |
| `cleanup_old_files.py` | 古い出力ファイルのクリーンアップ |

</details>

<details>
<summary><strong>トラブルシューティング</strong></summary>

| エラー | 原因 | 対処 |
|---|---|---|
| exit code 9009 | `python` コマンドが見つからない | `py` を使用 |
| `WinError 32` | Dropbox がファイルロック中 | 無視可（バックアップ失敗のみ） |
| NaTType エラー | マクロデータの欠損 | 無視可（該当チャートのみスキップ） |
| 402 Payment Required | X API クレジット不足 | [Developer Portal](https://developer.x.com/en/portal/dashboard) でクレジット購入 |
| 401 Unauthorized | X API 認証情報エラー | GitHub Secrets を再確認 |
| ARM64 + R knitr 失敗 | Windows ARM64 互換性問題 | TidyTuesday は GitHub Actions でレンダリング |

</details>

---

# English Summary

This project is a personal learning initiative that transforms raw market information into actionable signals. Trading data is acquired through actual stock trading, then processed through a full pipeline — from data ingestion and feature engineering to KPI calculation, AI-powered analysis, report generation, and publication via GitHub Pages.
