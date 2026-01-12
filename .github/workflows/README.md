# GitHub Actions ワークフロー

## render-posts.yml - Weekly Posts Renderer

TidyTuesday（R）のポストをレンダリングするワークフロー。
MakeoverMonday（Python）はローカルでレンダリングします。

### 使用方法

1. GitHub リポジトリの **Actions** タブに移動
2. **Render Weekly Posts (TidyTuesday/MakeoverMonday)** を選択
3. **Run workflow** をクリック
4. オプションを選択:
   - **Post type**: `tidytuesday`（推奨）, `all`, `makeover-monday`
   - **Specific date**: 特定日付（空欄で全て）

### なぜ GitHub Actions を使うのか？

ARM64 Windows（Surface Laptop 7など）では、x64版 R との互換性問題により、
ローカルでの Quarto + R レンダリングが失敗します。

GitHub Actions は x64 Linux 環境で実行されるため、この問題を回避できます。

### ローカルでの使用

```powershell
# MakeoverMonday（Python）をレンダリング（デフォルト）
py scripts/by_timeSeries/runners/render_posts.py

# プレビュー起動
py scripts/by_timeSeries/runners/render_posts.py --preview

# 一覧表示のみ
py scripts/by_timeSeries/runners/render_posts.py --list
```

### ワークフローの流れ

```
[ローカル - Cursor]                    [GitHub Actions]
    │                                       │
    │ 1. MakeoverMonday (Python)            │
    │    py render_posts.py                 │
    │    → docs/ にHTML生成                 │
    │                                       │
    │ 2. git push                           │
    └───────────────────────────────────────►
                                            │
                                            │ 3. TidyTuesday (R)
                                            │    Actions → Run workflow
                                            │    → docs/ にHTML生成
                                            │    → 自動コミット&プッシュ
                                            │
    ◄───────────────────────────────────────┘
    │
    │ 4. git pull（必要に応じて）
```

### 必要な設定

ワークフローが `docs/` フォルダにプッシュするため、リポジトリの **Settings → Actions → General** で以下を確認:

- **Workflow permissions**: `Read and write permissions` を選択
- **Allow GitHub Actions to create and approve pull requests**: チェック
