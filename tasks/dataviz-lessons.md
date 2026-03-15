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

（今後の教訓をここに追記）

---

## ggplot2 スタイル（TidyTuesday 用）

（今後の教訓をここに追記）
