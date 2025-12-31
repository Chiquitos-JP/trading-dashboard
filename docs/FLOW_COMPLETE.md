# 完全パイプライン全体フロー

## 概要

本プロジェクトのデータ処理から最終 HTML レンダリングまでの完全なフローを説明します。

## エントリーポイント

### メインスクリプト

- **`scripts/by_timeSeries/run_full_pipeline.py`** - 完全パイプライン実行（推奨）

### 実行方法

```bash
# 完全実行（データ処理 + 分析・可視化 + レンダリング）
python scripts/by_timeSeries/run_full_pipeline.py

# データ処理のみ（Quartoレンダリングをスキップ）
python scripts/by_timeSeries/run_full_pipeline.py --data-only

# データ処理パイプラインをスキップ（分析から開始）
python scripts/by_timeSeries/run_full_pipeline.py --skip-data-pipeline

# 強制再実行（チェックポイントを無視）
python scripts/by_timeSeries/run_full_pipeline.py --force
```

---

## 全体フロー図

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: データ処理パイプライン (run_data_pipeline.py)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  1. 為替レート更新                   │
        │     forex/forex_fred.py              │
        │     → USD/JPY 月次為替レート取得     │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  2. 生データ処理（USD建て）          │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ Rakuten Transaction          │   │
        │  │ transaction_rakuten_00.py    │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ Rakuten Realized P/L        │   │
        │  │ realizedPl_rakuten_01.py     │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ SBI Transaction              │   │
        │  │ transaction_sbi_00.py        │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ SBI Realized P/L              │   │
        │  │ realizedPl_sbi_00.py          │   │
        │  └──────────────────────────────┘   │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  3. 円転処理（USD建て + JPY建て）    │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ Rakuten Transaction          │   │
        │  │ transaction_rakuten_01.py    │   │
        │  │ → JPY建てデータ生成           │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ Rakuten Realized P/L         │   │
        │  │ realizedPl_rakuten_01.py     │   │
        │  │ → JPY建てデータ生成           │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ SBI Transaction              │   │
        │  │ transaction_sbi_01.py        │   │
        │  │ → JPY建てデータ生成           │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ SBI Realized P/L             │   │
        │  │ realizedPl_sbi_01.py         │   │
        │  │ → JPY建てデータ生成           │   │
        │  └──────────────────────────────┘   │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  4. 統合マスターデータ作成           │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ Transaction 統合マスター      │   │
        │  │ create_merged_master_        │   │
        │  │   transaction.py             │   │
        │  │ → Rakuten + SBI 統合         │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ Realized P/L 統合マスター     │   │
        │  │ create_merged_master_         │   │
        │  │   realized_pl.py               │   │
        │  │ → Rakuten + SBI 統合         │   │
        │  └──────────────────────────────┘   │
        └─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Phase 2: 分析・可視化・レンダリング (run_all.py)               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  5. データ統合                      │
        │     realizedPl/mergedPl.py           │
        │     → Rakuten + SBI 月次データ統合  │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  6. KPI分析・計算                   │
        │     - 月次損益計算                  │
        │     - 累積損益計算                  │
        │     - 勝率・リスク指標計算           │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  7. 可視化・グラフ生成               │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ 実現損益グラフ               │   │
        │  │ - 月次損益推移               │   │
        │  │ - 累積損益推移               │   │
        │  │ - 銘柄別損益                 │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ 保有期間分析                 │   │
        │  │ holding_period_analysis.py    │   │
        │  │ holding_period_visualization.│   │
        │  │   py                         │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ マクロ経済データ可視化       │   │
        │  │ macro_data_visualization.py   │   │
        │  └──────────────────────────────┘   │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  8. 週間レビュー生成                │
        │     - 週次サマリー作成               │
        │     - 記事生成                      │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  9. Quartoレンダリング              │
        │     - index.html 生成               │
        │     - dashboard.html 生成           │
        │     - analysis.html 生成            │
        │     - 週間レビュー記事生成          │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  10. ダッシュボードHTML出力         │
        │      - dashboard_panel.html 生成    │
        │      - インタラクティブダッシュボード│
        └─────────────────────────────────────┘
```

---

## 詳細フロー説明

### Phase 1: データ処理パイプライン

#### 1. 為替レート更新

- **スクリプト**: `scripts/by_timeSeries/forex/forex_fred.py`
- **処理内容**:
  - FRED API から USD/JPY 月次為替レートを取得
  - `data/trading_account/forex/raw/fred/usd_to_jpy_monthly_fred.csv` に保存
- **チェックポイント**: 上記 CSV ファイルの更新日時

#### 2. 生データ処理（USD 建て）

各証券会社・データタイプごとに処理:

- **Rakuten Transaction**

  - スクリプト: `scripts/by_timeSeries/transaction/transaction_rakuten_00.py`
  - 入力: `data/trading_account/transaction/raw/rakuten/`
  - 出力: `data/trading_account/transaction/processed/transaction_{YYYYMMDD}/rakuten_transaction_all_{YYYYMMDD}.parquet`

- **Rakuten Realized P/L**

  - スクリプト: `scripts/by_timeSeries/realizedPl/realizedPl_rakuten_01.py`
  - 入力: `data/trading_account/realized_pl/raw/rakuten/`
  - 出力: `data/trading_account/realized_pl/processed/realizedPl_{YYYYMMDD}/rakuten_monthly_summary_en_{YYYYMMDD}.parquet`

- **SBI Transaction**

  - スクリプト: `scripts/by_timeSeries/transaction/transaction_sbi_00.py`
  - 入力: `data/trading_account/transaction/raw/sbi/`
  - 出力: `data/trading_account/transaction/processed/transaction_{YYYYMMDD}/sbi_transaction_all_{YYYYMMDD}.parquet`

- **SBI Realized P/L**
  - スクリプト: `scripts/by_timeSeries/realizedPl/realizedPl_sbi_00.py`
  - 入力: `data/trading_account/realized_pl/raw/sbi/`
  - 出力: `data/trading_account/realized_pl/processed/realizedPl_{YYYYMMDD}/sbi_monthly_summary_en_{YYYYMMDD}.parquet`

#### 3. 円転処理（USD 建て + JPY 建て）

各証券会社・データタイプごとに円転処理:

- **Rakuten Transaction**

  - スクリプト: `scripts/by_timeSeries/transaction/transaction_rakuten_01.py`
  - 入力: 上記の USD 建てデータ + 為替レート
  - 出力: `data/trading_account/transaction/processed/transaction_{YYYYMMDD}/rakuten_transaction_with_fx_{YYYYMMDD}.parquet`
  - 内容: USD 建てデータ + JPY 建てデータ（`*_jpy`列を追加）

- **Rakuten Realized P/L**

  - スクリプト: `scripts/by_timeSeries/realizedPl/realizedPl_rakuten_01.py`
  - 入力: 上記の USD 建てデータ + 為替レート
  - 出力: `data/trading_account/realized_pl/processed/realizedPl_{YYYYMMDD}/rakuten_monthly_summary_with_fx_{YYYYMMDD}.parquet`

- **SBI Transaction**

  - スクリプト: `scripts/by_timeSeries/transaction/transaction_sbi_01.py`
  - 入力: 上記の USD 建てデータ + 為替レート
  - 出力: `data/trading_account/transaction/processed/transaction_{YYYYMMDD}/sbi_transaction_with_fx_{YYYYMMDD}.parquet`
  - **注意**: `settlement_date`列のリネーム処理を含む

- **SBI Realized P/L**
  - スクリプト: `scripts/by_timeSeries/realizedPl/realizedPl_sbi_01.py`
  - 入力: 上記の USD 建てデータ + 為替レート
  - 出力: `data/trading_account/realized_pl/processed/realizedPl_{YYYYMMDD}/sbi_monthly_summary_with_fx_{YYYYMMDD}.parquet`

#### 4. 統合マスターデータ作成

各データタイプごとに統合マスターを作成:

- **Transaction 統合マスター**

  - スクリプト: `scripts/by_timeSeries/transaction/create_merged_master_transaction.py`
  - 入力: 各証券会社の円転済みデータ
  - 出力: `data/trading_account/transaction/raw/master/master_transaction_merged.parquet`
  - 内容: Rakuten + SBI の全取引データを統合

- **Realized P/L 統合マスター**
  - スクリプト: `scripts/by_timeSeries/realizedPl/create_merged_master_realized_pl.py`
  - 入力: 各証券会社の円転済みデータ
  - 出力: `data/trading_account/realized_pl/raw/master/master_realized_pl_merged.parquet`
  - 内容: Rakuten + SBI の月次実現損益データを統合

### Phase 2: 分析・可視化・レンダリング

#### 5. データ統合

- **スクリプト**: `scripts/by_timeSeries/realizedPl/mergedPl.py`
- **処理内容**:
  - 各証券会社の円転済み月次データを読み込み
  - `.parquet`ファイルを優先的に読み込み（`.csv`はフォールバック）
  - Rakuten + SBI を統合
  - 出力: `outputs/figures/realizedPl_{YYYYMMDD}/merged_monthly_summary_{YYYYMMDD}.parquet`

#### 6. KPI 分析・計算

- **スクリプト**: `scripts/by_timeSeries/realizedPl/run_all.py`内
- **処理内容**:
  - 月次損益計算
  - 累積損益計算
  - 勝率・リスク指標計算
  - 銘柄別損益集計

#### 7. 可視化・グラフ生成

- **実現損益グラフ**

  - 月次損益推移
  - 累積損益推移
  - 銘柄別損益

- **保有期間分析**

  - スクリプト:
    - `scripts/by_timeSeries/holdingPeriod/holding_period_analysis.py`
    - `scripts/by_timeSeries/holdingPeriod/holding_period_visualization.py`
  - 処理内容:
    - 個別取引データから保有期間を計算
    - 銘柄別・パラメーター別の分析
    - グラフ生成

- **マクロ経済データ可視化**
  - スクリプト: `scripts/by_timeSeries/macroData/macro_data_visualization.py`
  - 処理内容:
    - FRED からマクロ経済データを取得
    - 為替レート、金利、株価指数などを可視化
    - 重複インデックスの処理を含む

#### 8. 週間レビュー生成

- **スクリプト**: `scripts/by_timeSeries/realizedPl/run_all.py`内
- **処理内容**:
  - 週次サマリー作成
  - Quarto 記事生成
  - 出力: `docs/quarto/latest/posts/{YYYY-MM-DD}-weekly-review/`

#### 9. Quarto レンダリング

- **スクリプト**: `scripts/by_timeSeries/realizedPl/run_all.py`内
- **処理内容**:
  - `docs/quarto/latest/index.html` - メインページ
  - `docs/quarto/latest/dashboard.html` - ダッシュボード
  - `docs/quarto/latest/analysis.html` - 分析ページ
  - 週間レビュー記事

#### 10. ダッシュボード HTML 出力

- **スクリプト**: `scripts/by_timeSeries/realizedPl/run_all.py`内
- **処理内容**:
  - `docs/quarto/latest/dashboard_panel.html` - インタラクティブダッシュボード
  - Plotly を使用したインタラクティブな可視化

---

## データファイル形式

### 優先順位

1. **`.parquet`ファイル** - 優先的に読み込み（高速・効率的）
2. **`.csv`ファイル** - フォールバック（`.parquet`が存在しない場合）

### ファイル命名規則

- 日付付きフォルダ: `{data_type}_{YYYYMMDD}/`
- ファイル名: `{broker}_{data_type}_{suffix}_{YYYYMMDD}.{ext}`
- 例: `rakuten_transaction_with_fx_20251231.parquet`

---

## チェックポイント管理

各ステップの完了は、出力ファイルの更新日時で管理されます。

- **チェックポイント確認**: ファイルが存在し、今日の日付で更新されている場合、処理をスキップ
- **強制再実行**: `--force`オプションでチェックポイントを無視して再実行

---

## エラーハンドリング

### 主要な修正内容

1. **Unicode 文字エラー**

   - 絵文字（✅、❌、⚠️ など）を ASCII 文字（`[SUCCESS]`、`[ERROR]`、`[WARNING]`）に置き換え
   - Windows の cp932 エンコーディング問題を回避

2. **`settlement_date`列のリネーム**

   - `transaction_sbi_01.py`で`決済日`列を`settlement_date`に確実にリネーム
   - 複数のフォールバック処理を実装

3. **重複インデックスエラー**

   - `macro_data_visualization.py`で`reindex`前に重複インデックスを削除
   - `groupby().last()`を使用して重複を解消

4. **Parquet 保存エラー**
   - `config/py/utils.py`でパス正規化とエラーハンドリングを改善
   - 既存ファイルの削除処理を追加

---

## 最終アウトプット

実行完了後、以下の HTML ファイルが生成されます：

- `docs/quarto/latest/index.html` - メインページ
- `docs/quarto/latest/dashboard.html` - ダッシュボード
- `docs/quarto/latest/dashboard_panel.html` - インタラクティブダッシュボード
- `docs/quarto/latest/analysis.html` - 分析ページ
- `docs/quarto/latest/posts/{YYYY-MM-DD}-weekly-review/index.html` - 週間レビュー記事

---

## トラブルシューティング

### よくあるエラーと対処法

1. **`KeyError: 'settlement_date'`**

   - 原因: SBI 取引データの列名が正しくリネームされていない
   - 対処: `transaction_sbi_01.py`のリネーム処理を確認

2. **`UnicodeEncodeError: 'cp932' codec can't encode`**

   - 原因: 絵文字などの Unicode 文字が Windows の cp932 でエンコードできない
   - 対処: 全ての Unicode 文字を ASCII 文字に置き換え済み

3. **`ValueError: cannot reindex on an axis with duplicate labels`**

   - 原因: マクロ経済データに重複インデックスが存在
   - 対処: `macro_data_visualization.py`で重複インデックスを削除済み

4. **`FileNotFoundError`**
   - 原因: 必要なデータファイルが存在しない
   - 対処: 前段階の処理が正常に完了しているか確認

---

## 関連ドキュメント

- `scripts/by_timeSeries/README_FULL_PIPELINE.md` - 完全パイプライン実行ガイド
- `scripts/by_timeSeries/README_DATA_PIPELINE.md` - データ処理パイプライン詳細
- `PROJECT_STRUCTURE.md` - プロジェクト構造とデータフロー
