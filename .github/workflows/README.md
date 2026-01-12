# GitHub Actions ワークフロー

## render-posts.yml - Weekly Posts Renderer

TidyTuesday（R）と MakeoverMonday（Python）のポストをレンダリングするワークフロー。

### 使用方法

1. GitHub リポジトリの **Actions** タブに移動
2. **Render Weekly Posts (TidyTuesday/MakeoverMonday)** を選択
3. **Run workflow** をクリック
4. オプションを選択:
   - **Post type**: `all`, `tidytuesday`, `makeover-monday`
   - **Specific date**: 特定日付（空欄で全て）

### なぜ GitHub Actions を使うのか？

ARM64 Windows（Surface Laptop 7など）では、x64版 R との互換性問題により、
ローカルでの Quarto + R レンダリングが失敗することがあります。

GitHub Actions は x64 Linux 環境で実行されるため、この問題を回避できます。

### ローカルでの使用

```powershell
# MakeoverMonday（Python）のみレンダリング（ARM64環境でも動作）
py scripts/by_timeSeries/runners/render_posts.py --type makeover

# Rポストをスキップ（ARM64環境向け）
py scripts/by_timeSeries/runners/render_posts.py --skip-r

# 一覧表示のみ
py scripts/by_timeSeries/runners/render_posts.py --list
```

### ワークフローの流れ

```
[ローカル - ARM64 Windows]
    │
    ├─► MakeoverMonday（Python）→ ローカルでレンダリング可能
    │
    └─► TidyTuesday（R）→ GitHub Actions でレンダリング
                              │
                              ▼
                         [GitHub Actions - x64 Linux]
                              │
                              ▼
                         レンダリング完了 → 自動コミット&プッシュ
```

### 必要な設定

ワークフローが `docs/` フォルダにプッシュするため、リポジトリの **Settings → Actions → General** で以下を確認:

- **Workflow permissions**: `Read and write permissions` を選択
- **Allow GitHub Actions to create and approve pull requests**: チェック
