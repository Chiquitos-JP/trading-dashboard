# プロジェクト構造とデータフロー

## ディレクトリ構成

```
project/
├── config/              # 設定・初期化スクリプト
│   ├── py/             # Python共通ユーティリティ
│   └── R/              # R共通ユーティリティ
├── data/                # データストレージ
│   ├── trading_account/    # 取引アカウントデータ
│   │   ├── raw/            # 生データ（変更不可）
│   │   ├── processed/       # 処理済みデータ
│   │   └── checkpoints/     # チェックポイント
│   ├── macro_economy/       # マクロ経済データ
│   ├── market_data/         # 市場データ
│   └── economicCalendar/     # 経済指標カレンダー
├── scripts/             # 分析スクリプト
│   └── by_timeSeries/   # 時系列分析
├── outputs/             # 出力ディレクトリ（統一）
│   ├── figures/         # 最終図表
│   ├── interim/         # 中間生成物
│   └── reports/         # レポート（将来拡張用）
└── docs/                # 公開用ドキュメント
    └── quarto/          # Quarto出力
```

## データ処理フロー

### 1. データ取得

```
外部ソース（証券会社、API等）
    ↓
data/raw/{source}/      # 生データ（変更不可）
```

### 2. データ処理

```
data/raw/
    ↓ [処理スクリプト]
data/processed/{data_type}_{YYYYMMDD}/  # 処理済みデータ
```

### 3. 可視化・分析

```
data/processed/
    ↓ [分析スクリプト]
outputs/interim/{category}/  # 中間可視化（HTML、CSV）
```

### 4. 最終成果物

```
outputs/interim/
    ↓ [統合処理]
outputs/figures/{analysis_type}_{YYYYMMDD}/  # 最終図表
```

### 5. レポート生成

```
outputs/figures/
    ↓ [Quartoレンダリング]
docs/quarto/latest/     # 公開用ドキュメント
```

## パス管理

### Python（推奨）

```python
from data_paths import get_data_paths

paths = get_data_paths()

# データパス
raw_data = paths.raw_trading_account("sbi", "realized_pl")
processed_data = paths.processed_trading_account("realized_pl", "20251226")

# 出力パス
figures_dir = paths.outputs_figures("realizedPl", "20251226")
interim_dir = paths.outputs_interim("economicCalendar")
```

### R

```r
# 環境変数またはconfig/R/init.Rで設定
P$raw    # data/
P$output # outputs/figures/
P$site   # docs/
```

## 命名規則

### データファイル

- **生データ**: 取得元の形式を維持
- **処理済み**: `{data_type}_{YYYYMMDD}.parquet`
- **最新版**: `{data_name}_latest.parquet`

### 出力ファイル

- **最終図表**: `outputs/figures/{analysis_type}_{YYYYMMDD}/`
- **中間生成物**: `outputs/interim/{category}/`

## クリーンアップポリシー

- **生データ**: 絶対に削除しない
- **処理済みデータ**: 再生成可能なため削除可能
- **チェックポイント**: 7 日以内を超えたものは自動削除
- **最終図表**: 最新 5 件 + 30 日以内を保持
- **中間生成物**: 必要に応じて手動削除可能
