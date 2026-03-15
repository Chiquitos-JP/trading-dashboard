# Dataviz Lessons

MakeoverMonday / TidyTuesday 投稿のビジュアルデザイン教訓を蓄積するファイル。
投稿作成時に参照し、同じ問題を繰り返さない。

記録フォーマット: 日付、投稿タイプ、問題、修正、ルール

---

## レイアウト・タイトル

### 2026-03-16 MM: 凡例とタイトルの重複

- **投稿**: [2026-03-16-makeover-monday](https://chiquitos-jp.github.io/trading-dashboard/quarto/latest/posts/2026-03-16-makeover-monday/)
- **問題**: Plotly で `legend=dict(orientation="h", yanchor="bottom", y=1.02)` と `title="..."` を併用すると、凡例がプロット上部（y=1.02）に配置され、グラフタイトルと重なって見づらい
- **修正**: 凡例をチャート下部に移動する
  ```python
  legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5),
  margin=dict(b=80),  # 凡例用の余白を確保
  ```
- **ルール**: 凡例とタイトルが重ならないよう、凡例は `y=1.02`（上部）を避け、下部（`y=-0.12`）か右側（`x=1.02`）に配置する

---

## データ・前処理

### 2026-03-16 MM: 外部 CSV のカラム名にスペース

- **投稿**: 2026-03-16-makeover-monday
- **問題**: 外部 CSV のカラム名 `Global Sales`（スペース区切り）をコード内で `Global_Sales`（アンダースコア）として参照し `KeyError` でレンダリング失敗
- **修正**: `pd.read_csv()` 直後に `df.columns = df.columns.str.replace(" ", "_")` でカラム名を正規化
- **ルール**: 外部データ読み込み直後にカラム名を正規化する（スペース → アンダースコア）。`df.columns.tolist()` で実際のカラム名を確認してからコードを書く

---

## Plotly スタイル

### 2026-03-16 MM: plotly_dark よりも plotly_white がページ埋め込みに適する

- **投稿**: [2026-03-16-makeover-monday](https://chiquitos-jp.github.io/trading-dashboard/quarto/latest/posts/2026-03-16-makeover-monday/)
- **問題**: `plotly_dark` テーマはページの白背景と乖離し、埋め込み時に浮いて見える
- **修正**: `template="plotly_white"` + `paper_bgcolor="white"` + `plot_bgcolor="#f8fafc"` に変更
- **ルール**: Quarto 埋め込みチャートは `plotly_white` 基本。dark テーマはスタンドアロン用途のみ

### 2026-03-16 MM: THEME dict に title を含めると update_layout で重複エラー

- **問題**: 共通 `THEME = dict(..., title=dict(...))` を `**THEME` で展開しつつ `title=dict(...)` を同時に渡すと `TypeError: multiple values for keyword argument 'title'`
- **修正**: `THEME` から `title` を除外し、ヘルパー関数 `make_title(text)` を用意して各チャートで明示的に渡す
  ```python
  def make_title(text):
      return dict(text=text, font=dict(size=15, color="#1e293b"), x=0, xanchor="left")
  ```
- **ルール**: 共通スタイル dict には `title` を含めない。タイトルは都度 `make_title()` で指定する

### 2026-03-16 MM: タイトルはインサイト文にする

- **問題**: "Top 15 Mario Titles by Global Sales" のような「何を見ているか」説明型タイトルは読者に解釈を委ねる
- **修正**: "Mario's blockbusters dominate: top 5 titles = 64% of franchise sales" のように「結論を先に示す」インサイト型タイトルに変更
- **ルール**: チャートタイトルは「{metric} by {dimension}」ではなく「{insight}」形式にする。データから動的に計算した数値を埋め込むと説得力が増す

### 2026-03-16 MM: 4分類以下の構成比に treemap は不要

- **問題**: 地域構成（NA/EU/JP/Other）を treemap で表示しても面積比が直感的に伝わらない
- **修正**: 横方向 100% stacked bar 1本に変更。各セグメント内に直接ラベルを表示
- **ルール**: 4区分以下のカテゴリには treemap より横棒または stacked bar が明快。5区分以上・階層構造がある場合のみ treemap を検討する

### 2026-03-16 MM: 凡例より直接ラベルで視線移動を減らす

- **問題**: 凡例を別置きにすると「凡例確認 → チャート確認 → 凡例確認」と視線が往復して読解コストが高い
- **修正**: `textposition="outside"` で棒の外側に数値ラベル、折れ線の終端に `add_annotation` でシリーズ名を直接記入
- **ルール**: 系列数が 5 以下なら直接ラベル/アノテーションを優先し、`showlegend=False` にする

### 2026-03-16 MM: グレー+単一強調色パレット

- **問題**: 多色使いはカテゴリを等価に扱う印象を与え、主メッセージが埋もれる
- **修正**: ベース色 `#94a3b8`（グレー）、強調色 `#e63946`（赤）の2色構成。Top 3 やランク1位のみに強調色を使用
- **ルール**: 「色 = 意味」の原則。色は主張が必要な要素にのみ使う。それ以外はグレーに統一する

### 2026-03-16 MM: Hero チャートで結論を先に見せる

- **問題**: 4チャートを同格に並べると読者がどこから読むか迷う
- **修正**: 「Hero（ヒット集中度）→ 分解（地域・ジャンル）→ 文脈（時系列）」の3段構成
- **ルール**: ページの冒頭に「1秒で主メッセージが伝わる Hero チャート」を置き、以降の図でその主張を補強する構成にする

---

## ggplot2 スタイル（TidyTuesday 用）

（今後の教訓をここに追記）
