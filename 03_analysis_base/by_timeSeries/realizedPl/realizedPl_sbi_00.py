# %% SBIの処理 --- #
import pandas as pd
from datetime import datetime
import os
from glob import glob
import pandas_market_calendars as mcal  # ← 米国市場の営業日取得用に追加

# %% ▼ フォルダパス設定
input_folder = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\01_data\trading_account\realized_pl\raw\sbi"
output_folder = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\01_data\trading_account\realized_pl\processed"

# %% ▼ 最新ファイル取得
file_pattern = os.path.join(input_folder, "*.csv")
matching_files = glob(file_pattern)

if not matching_files:
    raise FileNotFoundError(f"パターン '{file_pattern}' にマッチするファイルが見つかりません。")

input_file = max(matching_files, key=os.path.getctime)
print(f"[INFO] 読み込んだ最新ファイル: {input_file}")

# ▼ データ読み込み（9行目から、複数エンコーディング対応）
def safe_read_csv(file_path, skiprows=8):
    """安全なCSV読み込み（エンコーディング自動判定）"""
    encodings_to_try = ['shift-jis', 'cp932', 'utf-8', 'utf-8-sig']
    
    for encoding in encodings_to_try:
        try:
            print(f"[INFO] エンコーディング '{encoding}' で読み込み試行中...")
            df = pd.read_csv(file_path, encoding=encoding, skiprows=skiprows)
            print(f"[SUCCESS] エンコーディング '{encoding}' で読み込み成功")
            return df
        except UnicodeDecodeError:
            print(f"[WARNING] エンコーディング '{encoding}' で読み込み失敗")
            continue
        except Exception as e:
            print(f"[ERROR] エンコーディング '{encoding}' で予期しないエラー: {e}")
            continue
    
    raise ValueError("すべてのエンコーディングで読み込みに失敗しました")

df_sbi = safe_read_csv(input_file)

# %% ▼ 日付パターン自動検出関数
def analyze_date_patterns(series, column_name):
    """日付列のパターンを分析して最適な変換方法を決定"""
    print(f"\n{'='*50}")
    print(f"[ANALYSIS] '{column_name}' 日付パターン分析")
    print(f"{'='*50}")
    
    # サンプルデータを取得（NaN除外）
    sample_data = series.dropna().astype(str).str.strip()
    if len(sample_data) == 0:
        print(f"[WARNING] '{column_name}' に有効なデータがありません")
        return None
    
    print(f"[INFO] 有効データ数: {len(sample_data)}/{len(series)}")
    print(f"[INFO] サンプル値: {list(sample_data.head(10))}")
    print(f"[INFO] データ範囲: {sample_data.min()} ～ {sample_data.max()}")
    
    # 各フォーマットの検出率をテスト
    date_formats = [
        ("%Y/%m/%d", "YYYY/MM/DD"),
        ("%Y-%m-%d", "YYYY-MM-DD"), 
        ("%Y年%m月%d日", "YYYY年MM月DD日"),
        ("%m/%d/%Y", "MM/DD/YYYY"),
        ("%d/%m/%Y", "DD/MM/YYYY"),
        ("%Y%m%d", "YYYYMMDD"),
        ("%m-%d-%Y", "MM-DD-YYYY"),
        ("%d-%m-%Y", "DD-MM-YYYY")
    ]
    
    format_scores = []
    
    for fmt, fmt_name in date_formats:
        try:
            parsed = pd.to_datetime(sample_data, format=fmt, errors='coerce')
            success_rate = parsed.notna().sum() / len(sample_data)
            
            if success_rate > 0:
                # 年の妥当性チェック（1900-2030年の範囲）
                valid_years = parsed.dt.year.between(1900, 2030).sum()
                year_validity = valid_years / parsed.notna().sum() if parsed.notna().sum() > 0 else 0
                
                # 総合スコア（成功率 × 年妥当性）
                total_score = success_rate * year_validity
                
                format_scores.append({
                    'format': fmt,
                    'format_name': fmt_name,
                    'success_rate': success_rate,
                    'year_validity': year_validity,
                    'total_score': total_score,
                    'sample_parsed': parsed.dropna().head(3).tolist()
                })
                
                print(f"[TEST] {fmt_name:<15} | 成功率: {success_rate:.1%} | 年妥当性: {year_validity:.1%} | スコア: {total_score:.3f}")
        except Exception as e:
            print(f"[ERROR] {fmt_name}: {e}")
    
    if not format_scores:
        print(f"[ERROR] 適用可能な日付フォーマットが見つかりません")
        return None
    
    # 最高スコアのフォーマットを選択
    best_format = max(format_scores, key=lambda x: x['total_score'])
    
    print(f"\n[RESULT] 最適フォーマット: {best_format['format_name']} ({best_format['format']})")
    print(f"[RESULT] 成功率: {best_format['success_rate']:.1%}")
    print(f"[RESULT] サンプル解析結果: {best_format['sample_parsed']}")
    
    # 年の分布を確認
    try:
        test_parsed = pd.to_datetime(sample_data, format=best_format['format'], errors='coerce')
        year_dist = test_parsed.dt.year.value_counts().sort_index()
        print(f"[RESULT] 年の分布: {dict(year_dist)}")
        
        # 月の分布（直近年のみ）
        latest_year = test_parsed.dt.year.max()
        latest_year_data = test_parsed[test_parsed.dt.year == latest_year]
        if len(latest_year_data) > 0:
            month_dist = latest_year_data.dt.month.value_counts().sort_index()
            print(f"[RESULT] {latest_year}年の月分布: {dict(month_dist)}")
    except Exception as e:
        print(f"[WARNING] 年月分布の分析中にエラー: {e}")
    
    print(f"{'='*50}\n")
    return best_format

# %% ▼ 日付パターン自動検出関数
def analyze_date_patterns(series, column_name):
    """日付列のパターンを分析して最適な変換方法を決定"""
    print(f"\n{'='*50}")
    print(f"[ANALYSIS] '{column_name}' 日付パターン分析")
    print(f"{'='*50}")
    
    # サンプルデータを取得（NaN除外）
    sample_data = series.dropna().astype(str).str.strip()
    if len(sample_data) == 0:
        print(f"[WARNING] '{column_name}' に有効なデータがありません")
        return None
    
    print(f"[INFO] 有効データ数: {len(sample_data)}/{len(series)}")
    print(f"[INFO] サンプル値: {list(sample_data.head(10))}")
    print(f"[INFO] データ範囲: {sample_data.min()} ～ {sample_data.max()}")
    
    # 各フォーマットの検出率をテスト
    date_formats = [
        ("%Y/%m/%d", "YYYY/MM/DD"),
        ("%Y-%m-%d", "YYYY-MM-DD"), 
        ("%Y年%m月%d日", "YYYY年MM月DD日"),
        ("%m/%d/%Y", "MM/DD/YYYY"),
        ("%d/%m/%Y", "DD/MM/YYYY"),
        ("%Y%m%d", "YYYYMMDD"),
        ("%m-%d-%Y", "MM-DD-YYYY"),
        ("%d-%m-%Y", "DD-MM-YYYY")
    ]
    
    format_scores = []
    
    for fmt, fmt_name in date_formats:
        try:
            parsed = pd.to_datetime(sample_data, format=fmt, errors='coerce')
            success_rate = parsed.notna().sum() / len(sample_data)
            
            if success_rate > 0:
                # 年の妥当性チェック（1900-2030年の範囲）
                valid_years = parsed.dt.year.between(1900, 2030).sum()
                year_validity = valid_years / parsed.notna().sum() if parsed.notna().sum() > 0 else 0
                
                # 総合スコア（成功率 × 年妥当性）
                total_score = success_rate * year_validity
                
                format_scores.append({
                    'format': fmt,
                    'format_name': fmt_name,
                    'success_rate': success_rate,
                    'year_validity': year_validity,
                    'total_score': total_score,
                    'sample_parsed': parsed.dropna().head(3).tolist()
                })
                
                print(f"[TEST] {fmt_name:<15} | 成功率: {success_rate:.1%} | 年妥当性: {year_validity:.1%} | スコア: {total_score:.3f}")
        except Exception as e:
            print(f"[ERROR] {fmt_name}: {e}")
    
    if not format_scores:
        print(f"[ERROR] 適用可能な日付フォーマットが見つかりません")
        return None
    
    # 最高スコアのフォーマットを選択
    best_format = max(format_scores, key=lambda x: x['total_score'])
    
    print(f"\n[RESULT] 最適フォーマット: {best_format['format_name']} ({best_format['format']})")
    print(f"[RESULT] 成功率: {best_format['success_rate']:.1%}")
    print(f"[RESULT] サンプル解析結果: {best_format['sample_parsed']}")
    
    # 年の分布を確認
    try:
        test_parsed = pd.to_datetime(sample_data, format=best_format['format'], errors='coerce')
        year_dist = test_parsed.dt.year.value_counts().sort_index()
        print(f"[RESULT] 年の分布: {dict(year_dist)}")
        
        # 月の分布（直近年のみ）
        latest_year = test_parsed.dt.year.max()
        latest_year_data = test_parsed[test_parsed.dt.year == latest_year]
        if len(latest_year_data) > 0:
            month_dist = latest_year_data.dt.month.value_counts().sort_index()
            print(f"[RESULT] {latest_year}年の月分布: {dict(month_dist)}")
    except Exception as e:
        print(f"[WARNING] 年月分布の分析中にエラー: {e}")
    
    print(f"{'='*50}\n")
    return best_format

# %% ▼ データクリーニング関数
def clean_numeric_column(series, column_name):
    """数値列のクリーニング（文字化け・特殊文字対応）"""
    print(f"[INFO] '{column_name}' 列をクリーニング中...")
    
    # 文字列に変換
    cleaned = series.astype(str)
    
    # 一般的な文字化け・特殊文字を除去
    cleaned = cleaned.str.replace(",", "", regex=False)  # カンマ除去
    cleaned = cleaned.str.replace("¥", "", regex=False)   # 円マーク除去
    cleaned = cleaned.str.replace("$", "", regex=False)   # ドルマーク除去
    cleaned = cleaned.str.replace("株", "", regex=False)   # 株除去
    cleaned = cleaned.str.replace("円", "", regex=False)   # 円除去
    cleaned = cleaned.str.replace("+", "", regex=False)   # プラス記号除去
    cleaned = cleaned.str.replace("　", "", regex=False)  # 全角スペース除去
    cleaned = cleaned.str.strip()                        # 前後空白除去
    
    # NaN, None, 空文字列を処理
    cleaned = cleaned.replace(['', 'nan', 'NaN', 'None', 'null'], pd.NA)
    
    # 数値変換
    numeric_result = pd.to_numeric(cleaned, errors="coerce")
    
    # 変換結果の確認
    success_count = numeric_result.notna().sum()
    total_count = len(series)
    print(f"[INFO] '{column_name}': {success_count}/{total_count} 行が正常に変換されました")
    
    if success_count < total_count:
        failed_values = cleaned[numeric_result.isna() & cleaned.notna()].unique()[:5]
        print(f"[WARNING] 変換失敗値の例: {failed_values}")
    
    return numeric_result

# %% ▼ 日付パターンの事前分析
print(f"\n{'='*60}")
print(f"[PREPROCESSING] 日付列のパターン分析")
print(f"{'='*60}")

# 日付列の自動検出（カラム名変更前に実行）
date_column_mapping = {
    "決済日(国内約定日)": "settlement_date",
    "建日(国内約定日)": "contract_date"
}

detected_formats = {}
for original_col, target_col in date_column_mapping.items():
    if original_col in df_sbi.columns:
        detected_format = analyze_date_patterns(df_sbi[original_col], original_col)
        detected_formats[target_col] = detected_format
    else:
        print(f"[WARNING] 列 '{original_col}' が見つかりません")
        detected_formats[target_col] = None

# %% ▼ カラム英訳
# SBIは楽天と違って取得単価の内訳や手数料情報が細かく分かれている
col_rename_map = {
    "建日(国内約定日)": "contract_date",
    "決済日(国内約定日)": "settlement_date",
    "預り区分": "custody_type", #特定 or 一般
    "取引": "transaction_type", #返買 or 返売
    "ティッカー": "ticker",
    "銘柄": "stock_name",
    "数量": "num_of_shares",
    # 平均単価
    "決済単価": "avg_UnitPrice_settlement_usd",
    "建単価": "contract_UnitPrice_usd", # あくまで建単価であり、手数料を含めた平均取得単価ではない
    # 合計金額
    "決済損益": "ttl_gain_realized_usd", # 実現損益の合計しかない。従って、決済合計金額、及び、取得金額合計は逆算で算出。
    # 費用_共通
    "決済手数料(税込)": "settlement_fee_usd",
    "諸経費等": "fees_usd",
    "新規手数料(税込)": "new_order_fee_usd",
    "管理費(税込)": "management_fee_usd",
    "権利処理等手数料(税込)": "rights_processing_fee_usd", #主に売り建て
    # 費用_買い建て
    "金利": "interest_usd",
    # 費用_売り建て
    "貸株料": "stock_lending_fee_usd",
    # その他
    "市場": "market"
}

print(f"[INFO] 読み込み前列数: {len(df_sbi.columns)}")
print(f"[INFO] 読み込み前行数: {len(df_sbi)}")

df_sbi = df_sbi.rename(columns=col_rename_map)

# %% ▼ 通貨列追加
df_sbi["currency"] = "USD"

# %% ▼ 改良された数値変換（丁寧なクリーニング）
numeric_cols = [
    "num_of_shares", 
    "contract_UnitPrice_usd", 
    "avg_UnitPrice_settlement_usd", 
    "fees_usd", 
    "ttl_gain_realized_usd",
    "new_order_fee_usd", 
    "settlement_fee_usd", 
    "interest_usd", 
    "stock_lending_fee_usd",
    "management_fee_usd", 
    "rights_processing_fee_usd"
]

print(f"\n[INFO] 数値列のクリーニングを開始...")
for col in numeric_cols:
    if col in df_sbi.columns:
        df_sbi[col] = clean_numeric_column(df_sbi[col], col)
    else:
        print(f"[WARNING] 列 '{col}' が見つかりません")

# %% ▼ 日付変換（改良版：自動検出機能付き）
print(f"\n[INFO] 日付列の変換を開始...")

def clean_date_column(series, column_name, detected_format=None):
    """日付列のクリーニング（自動検出結果を優先使用）"""
    print(f"\n[INFO] '{column_name}' 列を日付変換中...")
    
    # 文字列に変換して基本的なクリーニング
    cleaned = series.astype(str).str.strip()
    
    result_dates = pd.Series(index=series.index, dtype='datetime64[ns]')
    
    # 検出されたフォーマットを最優先で使用
    if detected_format:
        print(f"[INFO] 検出されたフォーマット '{detected_format['format']}' を使用")
        try:
            result_dates = pd.to_datetime(cleaned, format=detected_format['format'], errors='coerce')
            success_count = result_dates.notna().sum()
            print(f"[SUCCESS] 検出フォーマットで {success_count}/{len(series)} 行が変換されました")
            
            # 検出フォーマットで十分な成功率（90%以上）が得られた場合はそれを使用
            if success_count / len(series) >= 0.9:
                return result_dates
        except Exception as e:
            print(f"[WARNING] 検出フォーマットでエラー: {e}")
    
    # フォールバック: 複数フォーマットを順次試行
    print(f"[INFO] フォールバックモードで追加フォーマットを試行...")
    fallback_formats = [
        "%Y/%m/%d",
        "%Y-%m-%d", 
        "%Y年%m月%d日",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y%m%d",
        "%m-%d-%Y",
        "%d-%m-%Y"
    ]
    
    for fmt in fallback_formats:
        try:
            mask = result_dates.isna()
            if mask.any():
                temp_dates = pd.to_datetime(cleaned[mask], format=fmt, errors='coerce')
                result_dates[mask] = temp_dates
                success_this_format = temp_dates.notna().sum()
                if success_this_format > 0:
                    print(f"[INFO] フォールバック '{fmt}' で {success_this_format} 行が変換されました")
        except Exception as e:
            print(f"[WARNING] フォールバック '{fmt}' でエラー: {e}")
    
    # 最後の手段：汎用的な日付解析
    remaining_mask = result_dates.isna()
    if remaining_mask.any():
        try:
            general_dates = pd.to_datetime(cleaned[remaining_mask], errors='coerce')
            result_dates[remaining_mask] = general_dates
            success_general = general_dates.notna().sum()
            if success_general > 0:
                print(f"[INFO] 汎用解析で {success_general} 行が変換されました")
        except Exception as e:
            print(f"[WARNING] 汎用日付解析でエラー: {e}")
    
    success_count = result_dates.notna().sum()
    total_count = len(series)
    print(f"[FINAL] '{column_name}': {success_count}/{total_count} 行が正常に変換されました")
    
    return result_dates

# 日付列を変換（検出結果を使用）
date_columns = ["settlement_date", "contract_date"]
for col in date_columns:
    if col in df_sbi.columns:
        detected_format = detected_formats.get(col)
        df_sbi[col] = clean_date_column(df_sbi[col], col, detected_format)
        
        # 変換後の品質チェック
        if df_sbi[col].notna().sum() > 0:
            date_range = f"{df_sbi[col].min()} ～ {df_sbi[col].max()}"
            print(f"[QUALITY] '{col}' 最終範囲: {date_range}")
        else:
            print(f"[ERROR] '{col}' の変換に完全に失敗しました")

# %% ▼ 年月カラム追加（改良版）
df_sbi["year_month"] = df_sbi["settlement_date"].dt.to_period("M").astype(str)

# %% ▼ データ処理結果の詳細確認
print(f"\n{'='*60}")
print(f"[INFO] データ処理完了後の詳細確認")
print(f"{'='*60}")

print(f"[INFO] 処理後データ形状: {df_sbi.shape}")
print(f"[INFO] 決済日範囲: {df_sbi['settlement_date'].min()} ～ {df_sbi['settlement_date'].max()}")

# 10月データの詳細確認（改良版：複数年対応）
print(f"\n[CRITICAL] 10月データ詳細分析:")
october_patterns = ["2024-10", "2025-10"]  # 複数年の10月をチェック

total_october_trades = 0
total_october_gain = 0

for pattern in october_patterns:
    october_data = df_sbi[df_sbi["year_month"] == pattern]
    if len(october_data) > 0:
        trades_count = len(october_data)
        total_gain = october_data['ttl_gain_realized_usd'].sum()
        
        total_october_trades += trades_count
        total_october_gain += total_gain
        
        print(f"\n[{pattern}] 10月データ:")
        print(f"  - 取引件数: {trades_count} 件")
        print(f"  - 実現損益合計: {total_gain:.2f} USD")
        print(f"  - 主要銘柄:")
        ticker_summary = october_data.groupby('ticker')['ttl_gain_realized_usd'].sum().sort_values(ascending=False)
        for ticker, amount in ticker_summary.head(5).items():
            print(f"    {ticker}: {amount:.2f} USD")
        
        # NaN値の確認
        nan_gains = october_data['ttl_gain_realized_usd'].isna().sum()
        if nan_gains > 0:
            print(f"  - [WARNING] NaN値の取引: {nan_gains} 件")

if total_october_trades == 0:
    print(f"[ERROR] 10月データが見つかりません！")
    print(f"[DEBUG] 利用可能な年月: {sorted(df_sbi['year_month'].unique())}")
else:
    print(f"\n[SUMMARY] 全10月合計:")
    print(f"  - 総取引件数: {total_october_trades} 件")
    print(f"  - 総実現損益: {total_october_gain:.2f} USD")

# 全期間の月次サマリー
monthly_summary = df_sbi.groupby("year_month")["ttl_gain_realized_usd"].agg(['count', 'sum']).round(2)
print(f"\n[INFO] 月次サマリー:")
print(monthly_summary)

# %% ▼ 決済金額列（ttl_settlement_amount_usd）
df_sbi["ttl_amt_settlement_usd"] = df_sbi["avg_UnitPrice_settlement_usd"] * df_sbi["num_of_shares"]

# %% ▼ 整形済みデータ保存（列名変更済・数値変換済）
today = datetime.today().strftime('%Y%m%d')
dated_folder = os.path.join(output_folder, f"realizedPl_{today}")
os.makedirs(dated_folder, exist_ok=True)

# 整形済みデータ
output_path_cleaned = os.path.join(
    dated_folder,
    f"sbi_trading_cleaned_{today}.csv"
)
df_sbi.to_csv(output_path_cleaned, index=False, encoding="utf-8-sig")

# %% ▼ 月次集計（合計）
monthly_numeric_cols = numeric_cols + ["ttl_amt_settlement_usd"]
df_sbi_monthly = df_sbi.groupby("year_month")[monthly_numeric_cols].sum().reset_index()
df_sbi_monthly["currency"] = "USD"

# %% ▼ 月次ベースで取得コストを逆算（ttl_cost_acquisition_usd, avg_UnitCost_acquisition_usd）
df_sbi_monthly["ttl_cost_acquisition_usd"] = (
    df_sbi_monthly["ttl_amt_settlement_usd"] - df_sbi_monthly["ttl_gain_realized_usd"]
)

df_sbi_monthly["avg_UnitCost_acquisition_usd"] = (
    df_sbi_monthly["ttl_cost_acquisition_usd"] / df_sbi_monthly["num_of_shares"]
)
# num_of_sharesが0の場合、平均取得単価はNaNにする
df_sbi_monthly.loc[df_sbi_monthly["num_of_shares"] == 0, ["ttl_cost_acquisition_usd", "avg_UnitCost_acquisition_usd"]] = None

# %% ▼ 取引件数・銘柄数・取引日数
filtered = df_sbi[df_sbi["transaction_type"].isin(["返買", "返売"])]
filtered["contract_date"] = pd.to_datetime(filtered["contract_date"], errors="coerce")
num_of_trades = filtered.groupby("year_month").size().reset_index(name="num_of_trades")
num_of_symbols = filtered.groupby("year_month")["ticker"].nunique().reset_index(name="num_of_symbols")
actual_trade_days = filtered.dropna(subset=["contract_date"]).groupby("year_month")["contract_date"].nunique().reset_index(name="actual_trade_days")

# %% ▼ 営業日数の推定（米国市場を前提）
# ↓ CustomBusinessDay → NYSE 実営業日に差し替え（正確な祝日対応）
nyse = mcal.get_calendar("NYSE")
market_days_list = []
for ym in df_sbi_monthly["year_month"].unique():
    ym_date = pd.to_datetime(ym + "-01")
    end_date = ym_date + pd.offsets.MonthEnd(0)
    schedule = nyse.schedule(start_date=ym_date, end_date=end_date)
    market_days_list.append({"year_month": ym, "market_open_days": len(schedule)})
market_open_days = pd.DataFrame(market_days_list)

# %% ▼ 追加指標算出
# --- 勝率 ---
filtered["win"] = filtered["ttl_gain_realized_usd"] > 0
win_rate = filtered.groupby("year_month")["win"].mean().reset_index(name="win_rate")

# --- 平均損益/1取引 ---
avg_gain_per_trade = filtered.groupby("year_month")["ttl_gain_realized_usd"].mean().reset_index(name="avg_gain_realized_perTrade_usd")

# --- 平均決済額/取得額/1取引 ---
avg_amt_per_trade = filtered.groupby("year_month")["ttl_amt_settlement_usd"].mean().reset_index(name="avg_amt_settlement_perTrade_usd")
avg_cost_per_trade = filtered.groupby("year_month").apply(lambda x: (x["ttl_amt_settlement_usd"] - x["ttl_gain_realized_usd"]).mean()).reset_index(name="avg_cost_acquisition_perTrade_usd")

# --- Sharpe Ratio（簡易） ---
sharpe_ratio = filtered.groupby("year_month")["ttl_gain_realized_usd"].agg(["mean", "std"]).reset_index()
sharpe_ratio["sharpe_ratio"] = sharpe_ratio["mean"] / sharpe_ratio["std"]
sharpe_ratio = sharpe_ratio[["year_month", "sharpe_ratio"]]

# %% ▼ 月次指標マージ
df_sbi_monthly = (
    df_sbi_monthly
    .merge(num_of_trades, on="year_month", how="left")
    .merge(num_of_symbols, on="year_month", how="left")
    .merge(actual_trade_days, on="year_month", how="left")
    .merge(market_open_days, on="year_month", how="left")
    .merge(win_rate, on="year_month", how="left")  # ← 追加
    .merge(avg_gain_per_trade, on="year_month", how="left")  # ← 追加
    .merge(avg_amt_per_trade, on="year_month", how="left")  # ← 追加
    .merge(avg_cost_per_trade, on="year_month", how="left")  # ← 追加
    .merge(sharpe_ratio, on="year_month", how="left")  # ← 追加
)

# %% ▼ 投資効率指標（USDベース）の追加
df_sbi_monthly["return_on_cost"] = df_sbi_monthly["ttl_gain_realized_usd"] / df_sbi_monthly["ttl_cost_acquisition_usd"]
df_sbi_monthly["return_on_sales"] = df_sbi_monthly["ttl_gain_realized_usd"] / df_sbi_monthly["ttl_amt_settlement_usd"]
df_sbi_monthly["trading_activity_ratio"] = df_sbi_monthly["actual_trade_days"] / df_sbi_monthly["market_open_days"]
df_sbi_monthly["avg_gain_per_day_usd"] = df_sbi_monthly["ttl_gain_realized_usd"] / df_sbi_monthly["actual_trade_days"]
df_sbi_monthly["avg_num_of_trades_per_day"] = df_sbi_monthly["num_of_trades"] / df_sbi_monthly["actual_trade_days"]

# %% ▼ 月次ファイル保存
output_path_monthly = os.path.join(
    dated_folder,
    f"sbi_monthly_summary_en_{today}.csv"
)
df_sbi_monthly.to_csv(output_path_monthly, index=False, encoding="utf-8-sig")

# %%
