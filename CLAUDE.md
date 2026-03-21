# Noise-to-Value Project

個人投資データの分析・可視化・レポート生成・公開を行うプロジェクト。
Cursor IDE と Claude Code (CLI) の両方で AI エージェント駆動が可能。

## デュアル環境設計（Cursor / Claude Code 対応マップ）

本プロジェクトは同一のコードベース・パイプラインに対して、Cursor と Claude Code のどちらからでも AI エージェントを駆動できる設計。ドメイン知識は両環境で重複管理し、各ツールが独立して動作できることを優先する。

### コンテキスト（常時ロード）

| Cursor | Claude Code | 内容 |
|---|---|---|
| `.cursor/rules/environment.mdc` | `CLAUDE.md`（本ファイル） | 実行環境・パイプライン・CI/CD |
| `.cursor/rules/workflow-orchestration.mdc` | `CLAUDE.md`（本ファイル） | 自己改善・検証・バグ修正プロトコル |
| `.cursor/rules/weekly-routine.mdc` | `CLAUDE.md`（本ファイル） | 週次ルーティン・コマンド判断基準 |

### 条件付きルール（対象ファイル作業時のみロード）

| Cursor（`globs:`） | Claude Code（`paths:`） | 対象パス |
|---|---|---|
| `.cursor/rules/makeover-monday.mdc` | `.claude/rules/makeover-monday.md` | `*-makeover-monday/**` |
| `.cursor/rules/tidytuesday.mdc` | `.claude/rules/tidytuesday.md` | `*-tidytuesday/**` |
| `.cursor/rules/thumbnail-svg.mdc` | `.claude/rules/svg-thumbnails.md` | `**/*.svg` |
| `.cursor/rules/quarto-post-conventions.mdc` | `.claude/rules/quarto-post-conventions.md` | `**/posts/**/*.qmd` |

### エージェント・コマンド（Claude Code 固有）

| 種別 | ファイル | 説明 |
|---|---|---|
| Agent | `.claude/agents/weekly-report.md` | 週次レビュー自律生成 |
| Agent | `.claude/agents/makeover-monday.md` | MM 投稿作成 |
| Agent | `.claude/agents/tidytuesday.md` | TT 投稿作成 |
| Agent | `.claude/agents/ci-monitor.md` | GitHub Actions 監視・修復 |
| Command | `.claude/commands/run-pipeline.md` | `/run-pipeline` — フルパイプライン実行 |
| Command | `.claude/commands/weekly-review.md` | `/weekly-review` — レビュー生成 |
| Command | `.claude/commands/new-mm.md` | `/new-mm` — MM 投稿スキャフォールド |
| Command | `.claude/commands/new-tt.md` | `/new-tt` — TT 投稿スキャフォールド |
| Command | `.claude/commands/render.md` | `/render` — Quarto レンダリング |
| Command | `.claude/commands/ci-status.md` | `/ci-status` — CI 実行状況確認 |

### 共有リソース（両環境から参照）

| ファイル | 用途 |
|---|---|
| `tasks/lessons.md` | エラー教訓の蓄積・参照 |
| `tasks/dataviz-lessons.md` | 可視化デザイン教訓の蓄積・参照 |
| `.claude/settings.json` | 権限強制（`python` 禁止, `.env` 読み取り禁止） |

## 実行環境（マルチ PC）

本プロジェクトは Dropbox 経由で **Windows PC** と **Mac** の両方から作業可能。
セッション開始時に OS を判別し、適切なコマンドを使用する。

### ツールバージョン管理表（2026-03-21 時点）

| ツール | Windows | Mac | CI (GitHub Actions) |
|---|---|---|---|
| Python | 3.13.0 | 3.12.13 | 3.12 |
| R | 4.5.1 | 4.3.1 | release (最新) |
| Quarto | 1.9.36 | 1.9.36 | 最新安定版 (1.9.x) |

### タスク別ローカル実行可否

| タスク | Windows | Mac | CI | 制約 |
|---|---|---|---|---|
| Weekly Review | OK | OK | - | Python のみ |
| MakeoverMonday (render) | OK | OK | OK | Python/jupyter。ローカル render 推奨 |
| TidyTuesday (render) | **不可** | **未検証** | **OK** | Win: ARM64 で不可。Mac: Apple Silicon + R 4.3.1 で要テスト |
| TidyTuesday (ソース作成) | OK | OK | - | `.qmd` + `prepare_data.py` 作成のみ |

Quarto のバージョンを揃えないと `docs/` に大量差分が出る。バージョン統一を維持すること。

### OS 自動判別

| 判別基準 | Windows | Mac |
|---|---|---|
| ワークスペースパス | `C:\Users\alpac\Dropbox\...` | `/Users/ogatamasaru/Library/CloudStorage/Dropbox/...` |
| `os.name` (Python) | `nt` | `posix` |
| Shell | PowerShell | zsh |

### Windows 環境

- OS: Windows 11 ARM64
- Python: **`py`** コマンドで起動（`python` は PATH にない — 使用禁止）
- Shell: PowerShell（bash コマンドは使えない）
- 仮想環境: `.venv/`（`Scripts/` レイアウト。pip: `.venv/Scripts/pip`）
- Quarto: 1.9.36
- R: 4.5.1 — ARM64 制約で TT render 不可
- ストレージ: Dropbox 上（`WinError 32` は無視可 — Dropbox ロック由来）

### Mac 環境

- 機種: MacBook Air (MacBookAir10,1)
- チップ: Apple M1（8コア: 高性能4 + 高効率4）
- メモリ: 16 GB LPDDR4
- ストレージ: 256 GB SSD（空き約 11 GB — 注意）
- OS: macOS 26.3.1 (Darwin 25.3.0) ARM64 (Apple Silicon M1)
- Python: **`python3`** コマンドで起動。`py` / `python` は使用不可
  - Homebrew Python 3.12.13 (`/opt/homebrew/bin/python3.12`)
  - venv 内: `.venv-mac/bin/python3`
- Shell: zsh（bash コマンド使用可能）
- 仮想環境: `.venv-mac/`（`bin/` レイアウト。pip: `.venv-mac/bin/pip`）
  - `.venv/` は Windows 用のため Mac では使用不可
  - venv 再構築: `python3.12 -m venv .venv-mac && .venv-mac/bin/pip install -r requirements.txt`
  - `pywinpty` は Windows 専用のため Mac ではスキップ（`grep -v pywinpty requirements.txt` で除外）
- Quarto: 1.9.36（`~/opt/bin/quarto`、PATH に追加済み）
- R: 4.3.1 — Apple Silicon + R 4.3.1 で TT render 未検証（要テスト）
- gh CLI: v2.87.3（Homebrew）
- cairo: Homebrew でインストール済み（CairoSVG の依存）
- ストレージ: Dropbox 上（CloudStorage 経由マウント）

### コマンド対応表

| 操作 | Windows | Mac |
|---|---|---|
| Python 実行 | `py script.py` | `python3 script.py` |
| パイプライン | `py scripts/by_timeSeries/runners/run_all.py` | `python3 scripts/by_timeSeries/runners/run_all.py` |
| pip install | `.venv/Scripts/pip install <pkg>` | `.venv-mac/bin/pip install <pkg>` |
| pip freeze | `.venv/Scripts/pip freeze > requirements.txt` | `.venv-mac/bin/pip freeze > requirements.txt` |
| venv activate | `.venv/Scripts/Activate.ps1` | `source .venv-mac/bin/activate` |

`.venv/`（Windows）と `.venv-mac/`（Mac）はそれぞれの OS 専用。もう一方の venv を触らない。

### Preflight Version Check（レンダリング前に必須）

ローカルレンダリング前に必ず実行し、ツールバージョンの一致を確認する。

| 操作 | Windows | Mac |
|---|---|---|
| 実行 | `py scripts/preflight_check.py` | `python3 scripts/preflight_check.py` |

- 期待バージョンは `config/tool_versions.json` で管理（Dropbox 同期で両マシン共有）
- Quarto 不一致時は `docs/` に大量差分が出るためレンダリングを中止し、更新を案内する
- CI は独自にバージョン管理するため対象外

## データアーキテクチャ（メダリオン 4 層）

```
raw/     → 生 CSV（Source of Truth、手動配置）
bronze/  → 正規化 Parquet（ブローカー別、型変換・カラム名統一）
silver/  → 統合 Parquet（全ブローカー結合）
gold/    → 集計・KPI テーブル（月次損益、KPI指標）
```

- パス管理: `config/py/data_paths.py`（`DataPaths` クラス）
- 生データ: `data/trading_account/realized_pl/raw/{rakuten,sbi}/`
- 口座残高: `data/trading_account/account_balance/daily_balance.parquet`
- マクロデータ: FRED API 等からランタイム取得（インターネット接続必須）

## パイプライン

エントリポイント:
- Windows: `py scripts/by_timeSeries/runners/run_all.py`
- Mac: `python3 scripts/by_timeSeries/runners/run_all.py`

| オプション | 動作 |
|---|---|
| （なし） | フル実行（チェックポイントで冪等） |
| `--force` | 強制再実行 |
| `--render-only` | Quarto レンダリングのみ |
| `--visualization-only` | 可視化のみ |
| `--data-only` | データ処理のみ |

部分実行スクリプト:
- `run_weekly_review.py` — Weekly Review + Quarto + Dashboard
- `run_weekly_posts.py` — TidyTuesday / MakeoverMonday
- `run_visualization.py` — 可視化のみ
- `run_quarto_rebuild.py` — 既存 .qmd の Quarto 再ビルド

すべて `scripts/by_timeSeries/runners/` に配置。迷ったら `run_all.py` を実行する。

## 週次ルーティン

### Weekly Review（投資レビュー）

- ローカルで `run_all.py` + AI 分析により生成
- 投稿は手動（自動投稿なし）
- テンプレート: `scripts/by_timeSeries/quarto/posts/_template_weekly_review.qmd`

### MakeoverMonday（Python / Plotly）— ローカル完結

- ローカルで `index.qmd` + `thumbnail.svg` + `chart-1.png` を作成
- **ローカルで `quarto render` まで実行**（CI レンダリング不要）
- レンダリング済み `docs/` を含めて `git push` → 公開完了
- X 自動投稿（月曜 9:00 JST）は CI スケジュール
- テンプレート: `scripts/by_timeSeries/quarto/posts/_template_makeover_monday.qmd`

フロー: 作成 → ローカル render → `git push`（ソース + docs/）

### TidyTuesday（R / ggplot2）— CI 必須

- ローカルで `index.qmd` + `thumbnail.svg` + `prepare_data.py` を作成
- **ローカルレンダリング**: Windows は ARM64 で不可。Mac は未検証（Apple Silicon + R 4.3.1、要テスト）
- `git push` 後に `gh workflow run` で CI レンダリング起動
- X 自動投稿（火曜 9:00 JST）は CI スケジュール
- テンプレート: `scripts/by_timeSeries/quarto/posts/_template_tidytuesday.qmd`
- `engine: knitr` を frontmatter に必ず含める

フロー: 作成 → `git push`（ソースのみ）→ `gh workflow run` → CI 完了確認

## CI/CD（GitHub Actions）

| ワークフロー | ファイル | 用途 |
|---|---|---|
| Render Weekly Posts | `render-posts.yml` | TT / MM の Quarto レンダリング + リスティング再生成 → `docs/` に commit |
| Post to X | `post-to-x.yml` | X 自動投稿（月曜 MM / 火曜 TT） |
| Post Weekly Calendar | `post-weekly-calendar.yml` | 週間経済カレンダー X 投稿（日曜 22:00 JST） |
| Post Sunday Markets | `post-sunday-markets.yml` | 日曜マーケット画像キャプチャ + X 投稿（日曜 12:00 JST） |

```bash
# レンダリング実行
gh workflow run "render-posts.yml" -f post_type=all --repo Chiquitos-JP/trading-dashboard
gh workflow run "render-posts.yml" -f post_type=makeover-monday -f post_date=YYYY-MM-DD --repo Chiquitos-JP/trading-dashboard

# X 投稿（手動）
gh workflow run "post-to-x.yml" -f post_type=makeover-monday --repo Chiquitos-JP/trading-dashboard

# 実行状況確認
gh run list --workflow=render-posts.yml --limit 3 --repo Chiquitos-JP/trading-dashboard

# ログ確認
gh run view <run_id> --log --repo Chiquitos-JP/trading-dashboard
```

## Quarto 出力構成

- Quarto プロジェクト: `scripts/by_timeSeries/quarto/`
- 出力先: `docs/quarto/latest/`（`_quarto.yml` の `output-dir`）
- サイト URL: `https://chiquitos-jp.github.io/trading-dashboard/quarto/latest/`
- GitHub Pages ソース: `docs/` フォルダ（`.nojekyll` あり）
- `docs/index.html` → `docs/quarto/latest/index.html` へリダイレクト
- **リスティングページ**: `analysis.qmd` → `analysis.html`（ブログ一覧）
  - CI が個別ポストレンダリング後に自動で再生成する
  - Weekly Review のソースは gitignore のため、CI は `search.json` からスタブ QMD を生成
  - `analysis.qmd` は git 追跡対象（`.gitignore` で例外指定済み）

## 投稿規約（概要）

フォルダ命名: `posts/YYYY-MM-DD-{makeover-monday|tidytuesday|weekly-review}/`

新規投稿の必須 frontmatter: `x-posted: false`, `image: "thumbnail.svg"`, `twitter-card`

詳細なドメイン固有ルールは `.claude/rules/` に分離（パス指定付き高優先度で自動ロード）:

| ルールファイル | 対象パス | 内容 |
|---|---|---|
| `.claude/rules/makeover-monday.md` | `*-makeover-monday/**` | MM のレンダリング・画像出力・データ前処理 |
| `.claude/rules/tidytuesday.md` | `*-tidytuesday/**` | TT の CI レンダリング・R パッケージ制約・パス安全規則 |
| `.claude/rules/svg-thumbnails.md` | `**/*.svg` | SVG の XML 互換性・cairosvg 対応 |
| `.claude/rules/quarto-post-conventions.md` | `**/posts/**/*.qmd` | QMD の YAML / 本文ルール・テンプレート |

Cursor 環境では同等のルールが `.cursor/rules/` にあり、`globs:` で同じパスに対応。

## エラーパターンと自動対処

| エラー | OS | 対処 |
|---|---|---|
| `exit code 9009` / `python not recognized` | Windows | `py` コマンドを使用する |
| `command not found: py` | Mac | `python3` コマンドを使用する |
| `WinError 32` | Windows | Dropbox ロック由来 — 無視して続行 |
| `NaTType` エラー | 共通 | マクロデータ欠損 — 該当チャートのみスキップ |
| `ModuleNotFoundError` | Windows | `.venv/Scripts/pip install <pkg>` → `requirements.txt` 更新 |
| `ModuleNotFoundError` | Mac | `.venv-mac/bin/pip install <pkg>` → `requirements.txt` 更新 |
| CI failure | 共通 | `gh run view --log` でログ取得 → 原因特定 → 修正 push |
| タイムアウト | 共通 | 長時間コマンドには十分な待機時間を設定 |

## 自己改善ループ

- ユーザーから修正・指摘を受けたら `tasks/lessons.md` に教訓を追記する
- ビジュアルデザインの指摘は `tasks/dataviz-lessons.md` に追記する
- セッション開始時に両ファイルを確認し、同じ失敗を繰り返さない
- MakeoverMonday / TidyTuesday 作成時は `tasks/dataviz-lessons.md` を参照する

## 検証プロトコル

### パイプライン実行後

1. exit code: 0 を確認
2. 「成功: N/N」の N が一致していることを確認
3. 生成ファイルの存在確認（QMD、HTML）
4. 失敗ステップがあればログを解析し、原因を報告

### CI 実行後

1. `gh run list` でステータスを確認
2. 失敗時は `gh run view <run_id> --log` でログを取得
3. 成功時は `docs/` の更新を確認
4. `analysis.html` に新しい投稿が含まれていることを確認（リスティングページ）

### 一般タスク

- 完了を宣言する前に「スタッフエンジニアがこの diff を承認するか？」と自問する
- バグ報告を受けたらユーザーに確認せずまず自分で修正を試みる

## 禁止事項

- Windows で `python` コマンドの使用（`py` を使う）
- Mac で `py` コマンドの使用（`python3` を使う）
- `.env` ファイルの読み取り
- Windows でのローカル TidyTuesday レンダリング（R 未インストール）
- `thumbnail.png` のリポジトリコミット（CI 自動生成）
- X への自動投稿（投稿は手動 or スケジュール CI のみ）
- 他の OS の venv を改変しない（`.venv/` は Windows 専用、`.venv-mac/` は Mac 専用）

## 依存管理

- `requirements.txt`: ルートに配置、バージョン固定
- pip install 実行後は対応する venv の pip freeze で更新:
  - Windows: `.venv/Scripts/pip freeze > requirements.txt`
  - Mac: `.venv-mac/bin/pip freeze > requirements.txt`

## 公開範囲（.gitignore 方針）

- `docs/` のみ GitHub Pages で公開
- `scripts/`, `data/`, `config/` は非公開
- 例外: TT / MM の投稿ソース（`index.qmd`, `prepare_data.py`, `data/`, `thumbnail.svg`）は公開
- `.cursor/` は非公開、`.claude/` は公開（agents, commands, settings.json）
