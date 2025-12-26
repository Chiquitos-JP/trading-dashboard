# Python共通ユーティリティ

このディレクトリには、プロジェクト全体で使用する汎用的なPython関数を格納しています。
**他プロジェクトでも使用できる、汎用性の高い機能に限定**しています。

## ファイル構成

### `data_paths.py`
データパス管理ユーティリティ
- プロジェクト全体で統一されたデータアクセスを提供
- 新しいデータソースを追加しやすい設計
- **データパス**: `raw_trading_account()`, `processed_trading_account()`, `macro_fred()` など
- **出力パス**: `outputs_figures()`, `outputs_interim()`, `outputs_reports()`

### `data_processing.py`
データ処理共通ユーティリティ
- **ファイル読み込み**: `get_latest_file()`, `safe_read_csv()`
- **日付処理**: `detect_date_format()`, `convert_to_datetime()`, `add_year_month_column()`
- **数値処理**: `clean_numeric_column()`, `clean_numeric_columns()`
- **文字列処理**: `normalize_column_names()`
- **データフィルタリング**: `remove_summary_rows()`

### `market_calendar.py`
市場カレンダー関連ユーティリティ
- **営業日数計算**: `get_market_open_days()`, `get_market_open_days_for_dataframe()`
- NYSEなどの市場カレンダーに対応

### `trading_metrics.py`
トレーディング指標計算ユーティリティ
- **勝率計算**: `calculate_win_rate()`
- **シャープレシオ計算**: `calculate_sharpe_ratio()`
- **利益/損失分離**: `calculate_gain_loss_split()`
- **一括指標計算**: `calculate_trading_metrics()`

### `utils.py`
その他の共通ユーティリティ
- **データ保存**: `save_dataframe()` (Parquet/CSV)
- **形式変換**: `parquet_to_csv()`

### `file_operations.py`
ファイル操作共通ユーティリティ
- **日付フォルダ作成**: `create_dated_folder()`
- **日付付き出力パス取得**: `get_dated_output_path()`

### `env_loader.py`
環境変数読み込みユーティリティ
- **.envファイル読み込み**: `load_env_file()`
- **環境変数取得**: `get_env()`

### `data_metadata.py`
データメタデータ管理
- データファイルのメタデータ（作成日時、バージョンなど）を管理

### `bootstrap.py`
Python共通初期化スクリプト
- プロジェクトルートと`config/py`をPythonパスに追加

## 使用例

### 基本的なデータ読み込み

```python
from data_paths import get_data_paths
from data_processing import get_latest_file, safe_read_csv

paths = get_data_paths()
input_file = get_latest_file(paths.raw_trading_account("rakuten", "realized_pl"), "*.csv")
df = safe_read_csv(input_file)
```

### 日付・数値の処理

```python
from data_processing import (
    convert_to_datetime, clean_numeric_columns, 
    add_year_month_column, remove_summary_rows
)

# 日付変換
df["settlement_date"] = convert_to_datetime(df["settlement_date"])

# 数値列のクリーニング
df = clean_numeric_columns(df, ["num_of_shares", "ttl_gain_realized_jpy"])

# 年月カラム追加
df = add_year_month_column(df, "settlement_date")

# 合計/小計行の削除
df = remove_summary_rows(df, date_columns=["settlement_date"])
```

### トレーディング指標の計算

```python
from trading_metrics import calculate_win_rate, calculate_sharpe_ratio
from market_calendar import get_market_open_days_for_dataframe

# 勝率
win_rate_df = calculate_win_rate(df, "ttl_gain_realized_jpy", "year_month")

# シャープレシオ
sharpe_df = calculate_sharpe_ratio(df, "ttl_gain_realized_jpy", "settlement_date")

# 営業日数
df = get_market_open_days_for_dataframe(df, calendar_name="NYSE")
```

### データ保存と出力パス

```python
from utils import save_dataframe
from file_operations import get_dated_output_path
from data_paths import get_data_paths

paths = get_data_paths()

# データ保存（処理済みデータ）
output_path = get_dated_output_path(
    base_dir=paths.processed_trading_account("realized_pl"),
    filename="monthly_summary",
    prefix="realizedPl_",
    extension=".parquet"
)
save_dataframe(df, str(output_path))

# 最終図表の保存
figures_dir = paths.outputs_figures("realizedPl", "20251226")
save_dataframe(df, str(figures_dir / "summary.parquet"))

# 中間生成物の保存
interim_dir = paths.outputs_interim("economicCalendar")
save_dataframe(df, str(interim_dir / "calendar.html"))
```

### 環境変数の読み込み

```python
from env_loader import get_env, load_env_file

# .envファイルを自動読み込みして環境変数を取得
api_key = get_env("ALPHAVANTAGE_API_KEY")

# または明示的に読み込み
load_env_file()
api_key = os.getenv("ALPHAVANTAGE_API_KEY")
```

## 設計方針

1. **汎用性**: 他プロジェクトでも使用できる機能に限定
2. **独立性**: プロジェクト固有のロジックは含めない
3. **再利用性**: 複数のスクリプトで共通して使用される処理を抽出
4. **拡張性**: 新しい機能を追加しやすい設計

## 注意事項

- プロジェクト固有の処理は、各スクリプト内に残す
- 汎用性の低い処理は、このディレクトリに追加しない
- 関数の引数は、できるだけ柔軟に設計する

