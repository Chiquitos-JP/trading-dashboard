# -*- coding: utf-8 -*-
"""
データ処理共通ユーティリティ

CSV読み込み、日付変換、数値変換など、データ処理の共通処理を提供します。
他プロジェクトでも汎用的に使用できる機能に限定しています。
"""

import pandas as pd
import os
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from glob import glob
import unicodedata


# ==================== ファイル読み込み ====================

def get_latest_file(directory: Path, pattern: str = "*.csv") -> Optional[Path]:
    """
    ディレクトリ内の最新ファイルを取得
    
    Args:
        directory: 検索ディレクトリ
        pattern: ファイルパターン（glob形式）
        
    Returns:
        Path: 最新ファイルのパス、見つからない場合はNone
    """
    if not directory.exists():
        return None
    
    matching_files = list(directory.glob(pattern))
    if not matching_files:
        return None
    
    return max(matching_files, key=lambda p: p.stat().st_mtime)


def safe_read_csv(file_path: Path, skiprows: int = 0, 
                  encodings: Optional[List[str]] = None) -> pd.DataFrame:
    """
    安全なCSV読み込み（エンコーディング自動判定）
    
    Args:
        file_path: CSVファイルのパス
        skiprows: スキップする行数
        encodings: 試行するエンコーディングのリスト（デフォルト: ['shift-jis', 'cp932', 'utf-8', 'utf-8-sig']）
        
    Returns:
        pd.DataFrame: 読み込んだデータフレーム
        
    Raises:
        ValueError: すべてのエンコーディングで読み込みに失敗した場合
    """
    if encodings is None:
        encodings = ['shift-jis', 'cp932', 'utf-8', 'utf-8-sig']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding, skiprows=skiprows)
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"[WARNING] エンコーディング '{encoding}' で予期しないエラー: {e}")
            continue
    
    raise ValueError(f"すべてのエンコーディングで読み込みに失敗しました: {file_path}")


def robust_read_csv(file_path: Path, skiprows: int = 0, 
                   encodings: Optional[List[str]] = None,
                   expected_columns: Optional[int] = None,
                   on_bad_lines: str = 'warn') -> pd.DataFrame:
    """
    堅牢なCSV読み込み（エンコーディング自動判定、不正行の処理）
    
    Args:
        file_path: CSVファイルのパス
        skiprows: スキップする行数
        encodings: 試行するエンコーディングのリスト（デフォルト: ['shift-jis', 'cp932', 'utf-8', 'utf-8-sig']）
        expected_columns: 期待される列数（Noneの場合は最初の有効行から自動検出）
        on_bad_lines: 不正行の処理方法（'warn', 'skip', 'error'）
        
    Returns:
        pd.DataFrame: 読み込んだデータフレーム
    """
    if encodings is None:
        encodings = ['shift-jis', 'cp932', 'utf-8', 'utf-8-sig']
    
    for encoding in encodings:
        try:
            # まず、ファイルの構造を確認
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                lines = f.readlines()
            
            if len(lines) <= skiprows:
                raise ValueError(f"ファイルが短すぎます（{len(lines)}行、スキップ行数: {skiprows}）")
            
            # ヘッダー行を確認
            header_line = lines[skiprows].strip()
            if not header_line:
                # 空行の場合は次の行を探す
                for i in range(skiprows + 1, min(skiprows + 5, len(lines))):
                    if lines[i].strip():
                        header_line = lines[i].strip()
                        skiprows = i
                        break
            
            # 期待される列数を自動検出（カンマで分割、引用符を考慮）
            if expected_columns is None:
                # 簡易的な列数カウント（引用符内のカンマは考慮しない）
                expected_columns = len(header_line.split(','))
            
            # データ読み込み（不正行をスキップ）
            # pandasのバージョンを確認
            pandas_version = pd.__version__
            use_on_bad_lines = tuple(map(int, pandas_version.split('.')[:2])) >= (1, 3)
            
            read_params = {
                'filepath_or_buffer': file_path,
                'encoding': encoding,
                'skiprows': skiprows,
                'skipinitialspace': True,
                'na_values': ['', ' ', '  ', 'NULL', 'null', 'None', 'none', 'nan', 'NaN'],
                'keep_default_na': False,
                'engine': 'python',  # より柔軟な処理
                'quoting': 1,  # QUOTE_ALL（すべてのフィールドを引用符で囲む）
                'quotechar': '"',  # 引用符文字
                'doublequote': True,  # 引用符のエスケープ処理
                'escapechar': None  # エスケープ文字（Noneの場合はdoublequoteを使用）
            }
            
            # on_bad_linesパラメータの処理（pandasのバージョンに応じて）
            if use_on_bad_lines:
                if on_bad_lines == 'skip':
                    read_params['on_bad_lines'] = 'skip'
                elif on_bad_lines == 'warn':
                    read_params['on_bad_lines'] = 'warn'
            else:
                # 古いpandasバージョンの場合
                if on_bad_lines == 'skip':
                    read_params['error_bad_lines'] = False
                    read_params['warn_bad_lines'] = False
            
            try:
                df = pd.read_csv(**read_params)
            except Exception as e:
                # エンジンpythonで失敗した場合、cエンジンで再試行
                print(f"[WARNING] pythonエンジンで読み込み失敗、cエンジンで再試行: {e}")
                read_params['engine'] = 'c'
                if 'on_bad_lines' in read_params:
                    del read_params['on_bad_lines']
                if 'error_bad_lines' in read_params:
                    del read_params['error_bad_lines']
                if 'warn_bad_lines' in read_params:
                    del read_params['warn_bad_lines']
                df = pd.read_csv(**read_params)
            
            # 空行を削除
            df = df.dropna(how='all')
            
            # すべての列が空の行を削除
            df = df[~(df.isna().all(axis=1))]
            
            # 列数が期待値と大きく異なる行を警告
            if expected_columns is not None:
                # 実際の列数と期待値の差を確認
                if len(df.columns) != expected_columns:
                    print(f"[WARNING] 列数が期待値と異なります: 期待={expected_columns}, 実際={len(df.columns)}")
            
            print(f"[INFO] 読み込み成功: {len(df)}行, {len(df.columns)}列（エンコーディング: {encoding}）")
            return df
            
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"[WARNING] エンコーディング '{encoding}' で予期しないエラー: {e}")
            continue
    
    raise ValueError(f"すべてのエンコーディングで読み込みに失敗しました: {file_path}")


# ==================== 日付処理 ====================

def detect_date_format(series: pd.Series, sample_size: int = 100) -> Optional[Dict[str, Any]]:
    """
    日付列のフォーマットを自動検出
    
    Args:
        series: 日付列（文字列または日付型）
        sample_size: サンプルサイズ
        
    Returns:
        Dict: 検出されたフォーマット情報、見つからない場合はNone
    """
    # サンプルデータを取得
    sample_data = series.dropna().astype(str).str.strip()
    if len(sample_data) == 0:
        return None
    
    # サンプルサイズを制限
    if len(sample_data) > sample_size:
        sample_data = sample_data.sample(n=sample_size, random_state=42)
    
    # 試行するフォーマット
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
                    'total_score': total_score
                })
        except Exception:
            continue
    
    if not format_scores:
        return None
    
    # 最高スコアのフォーマットを選択
    best_format = max(format_scores, key=lambda x: x['total_score'])
    return best_format


def convert_to_datetime(series: pd.Series, detected_format: Optional[Dict[str, Any]] = None) -> pd.Series:
    """
    日付列を変換（自動検出結果を優先使用）
    
    Args:
        series: 日付列
        detected_format: 検出されたフォーマット情報
        
    Returns:
        pd.Series: 変換された日付列
    """
    # 文字列に変換して基本的なクリーニング
    cleaned = series.astype(str).str.strip()
    result_dates = pd.Series(index=series.index, dtype='datetime64[ns]')
    
    # 検出されたフォーマットを最優先で使用
    if detected_format:
        try:
            result_dates = pd.to_datetime(cleaned, format=detected_format['format'], errors='coerce')
            success_count = result_dates.notna().sum()
            
            # 検出フォーマットで十分な成功率（90%以上）が得られた場合はそれを使用
            if success_count / len(series) >= 0.9:
                return result_dates
        except Exception:
            pass
    
    # フォールバック: 複数フォーマットを順次試行
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
        except Exception:
            continue
    
    # 最後の手段：汎用的な日付解析
    remaining_mask = result_dates.isna()
    if remaining_mask.any():
        try:
            general_dates = pd.to_datetime(cleaned[remaining_mask], errors='coerce')
            result_dates[remaining_mask] = general_dates
        except Exception:
            pass
    
    return result_dates


# ==================== 数値処理 ====================

def clean_numeric_column(series: pd.Series, column_name: str = "") -> pd.Series:
    """
    数値列のクリーニング（文字化け・特殊文字対応）
    
    Args:
        series: 数値列
        column_name: 列名（ログ出力用）
        
    Returns:
        pd.Series: クリーニングされた数値列
    """
    # 文字列に変換
    cleaned = series.astype(str)
    
    # 「-」を0に変換（該当なし = 0として扱う）
    # 楽天の手数料、税金、受渡金額で「-」が使用される
    cleaned = cleaned.replace('-', '0')
    
    # 一般的な文字化け・特殊文字を除去
    replacements = {
        ",": "",
        "¥": "",
        "$": "",
        "株": "",
        "円": "",
        "+": "",
        "　": "",  # 全角スペース
    }
    
    for old, new in replacements.items():
        cleaned = cleaned.str.replace(old, new, regex=False)
    
    cleaned = cleaned.str.strip()
    
    # NaN, None, 空文字列を処理
    cleaned = cleaned.replace(['', 'nan', 'NaN', 'None', 'null'], pd.NA)
    
    # 数値変換
    numeric_result = pd.to_numeric(cleaned, errors="coerce")
    
    return numeric_result


def clean_numeric_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """
    複数の数値列を一括でクリーニング
    
    Args:
        df: データフレーム
        columns: クリーニングする列名のリスト
        
    Returns:
        pd.DataFrame: クリーニングされたデータフレーム
    """
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = clean_numeric_column(df[col], col)
    return df


# ==================== 文字列処理 ====================

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    列名の正規化（全角→半角、空白除去）
    
    Args:
        df: データフレーム
        
    Returns:
        pd.DataFrame: 列名が正規化されたデータフレーム
    """
    df = df.copy()
    df.columns = [unicodedata.normalize('NFKC', col).strip() for col in df.columns]
    return df


# ==================== データフィルタリング ====================

def remove_summary_rows(df: pd.DataFrame, 
                       date_columns: List[str],
                       summary_keywords: List[str] = None) -> pd.DataFrame:
    """
    合計/小計行を削除
    
    Args:
        df: データフレーム
        date_columns: 日付列名のリスト
        summary_keywords: 合計/小計を示すキーワード（デフォルト: ["合計額", "合計", "小計"]）
        
    Returns:
        pd.DataFrame: 合計/小計行が削除されたデータフレーム
    """
    if summary_keywords is None:
        summary_keywords = ["合計額", "合計", "小計"]
    
    # パターン作成
    pattern = "|".join(summary_keywords)
    
    # 文字列化（NaN対策）
    df_str = df.astype(str)
    
    # 「合計/小計キーワード」を含む行
    mask_word = df_str.apply(lambda s: s.str.contains(pattern, na=False)).any(axis=1)
    
    # 日付列が空の行
    def _is_blank(s):
        return s.isna() | (s.astype(str).str.strip() == "")
    
    mask_no_dates = pd.Series(False, index=df.index)
    for col in date_columns:
        if col in df.columns:
            mask_no_dates = mask_no_dates | _is_blank(df[col])
    
    # 合計/小計っぽく、かつ日付が無い → 削除
    df = df.loc[~(mask_word & mask_no_dates)].copy()
    
    return df


# ==================== 年月処理 ====================

def add_year_month_column(df: pd.DataFrame, date_column: str, 
                         output_column: str = "year_month") -> pd.DataFrame:
    """
    年月カラムを追加
    
    Args:
        df: データフレーム
        date_column: 日付列名
        output_column: 出力列名
        
    Returns:
        pd.DataFrame: 年月カラムが追加されたデータフレーム
    """
    df = df.copy()
    if date_column in df.columns:
        df[output_column] = pd.to_datetime(df[date_column], errors='coerce').dt.to_period("M").astype(str)
    return df


# ==================== 取引データ統合 ====================

def aggregate_split_transactions(df: pd.DataFrame,
                                 group_keys: List[str] = None,
                                 sum_columns: List[str] = None,
                                 price_round_decimals: int = 1) -> pd.DataFrame:
    """
    分割された取引を統合
    
    同一注文が分割されて記録されているケースを統合します。
    例: 同じ日に同じ銘柄を同じ価格で複数レコードある場合 → 1レコードに統合
    
    価格は指定した小数点桁数で丸めて比較します（デフォルト1桁）。
    これにより、28.0820と28.0827のような微小な価格差も同一取引として統合されます。
    
    Args:
        df: データフレーム
        group_keys: グループ化に使用するキー列（デフォルト: trade_date, settlement_date, ticker, trade_type, price_usd）
        sum_columns: 合計する列（デフォルト: quantity, amount_usd, fees_usd など）
        price_round_decimals: 価格を丸める小数点桁数（デフォルト: 1）
        
    Returns:
        pd.DataFrame: 統合されたデータフレーム
    """
    if len(df) == 0:
        return df
    
    df = df.copy()
    
    # デフォルトのグループ化キー
    if group_keys is None:
        group_keys = ['trade_date', 'settlement_date', 'ticker', 'trade_type', 'price_usd']
    
    # 存在するキーのみ使用
    existing_keys = [k for k in group_keys if k in df.columns]
    
    if not existing_keys:
        print("[WARNING] グループ化キーが見つかりません")
        return df
    
    # price_usd が存在する場合、丸め列を作成してキーを置換
    use_rounded_price = False
    if 'price_usd' in existing_keys and 'price_usd' in df.columns:
        df['_price_usd_rounded'] = df['price_usd'].round(price_round_decimals)
        existing_keys = [k if k != 'price_usd' else '_price_usd_rounded' for k in existing_keys]
        use_rounded_price = True
    
    # デフォルトの合計対象列
    if sum_columns is None:
        sum_columns = [
            'quantity', 'amount_usd', 'fees_usd', 'tax_usd', 
            'net_amount_usd', 'net_amount_jpy', 'settlement_amount',
            'amount_jpy', 'fees_jpy', 'tax_jpy'
        ]
    
    # 存在する合計対象列のみ使用
    existing_sum_cols = [c for c in sum_columns if c in df.columns]
    
    # 最初の値を取る列（グループ内で同じはず）
    # 丸め列とキー列、合計列を除外
    exclude_cols = set(existing_keys + existing_sum_cols + ['_price_usd_rounded'])
    first_cols = [c for c in df.columns if c not in exclude_cols]
    
    # 集計定義
    agg_dict = {}
    for col in existing_sum_cols:
        agg_dict[col] = 'sum'
    for col in first_cols:
        agg_dict[col] = 'first'
    
    # price_usdは加重平均で計算（統合後も正確な平均単価を保持）
    if use_rounded_price and 'price_usd' in df.columns and 'quantity' in df.columns:
        # 加重平均用の一時列を作成
        df['_weighted_price'] = df['price_usd'] * df['quantity']
        agg_dict['_weighted_price'] = 'sum'
        # price_usdは後で計算するのでfirst_colsから除外
        if 'price_usd' in agg_dict:
            del agg_dict['price_usd']
    
    # グループ化前の行数
    before_count = len(df)
    
    # 集計実行
    df_aggregated = df.groupby(existing_keys, as_index=False, dropna=False).agg(agg_dict)
    
    # price_usdを加重平均から復元
    if use_rounded_price and '_weighted_price' in df_aggregated.columns and 'quantity' in df_aggregated.columns:
        df_aggregated['price_usd'] = df_aggregated['_weighted_price'] / df_aggregated['quantity']
        df_aggregated = df_aggregated.drop(columns=['_weighted_price'])
    
    # 丸め列を削除
    if '_price_usd_rounded' in df_aggregated.columns:
        df_aggregated = df_aggregated.drop(columns=['_price_usd_rounded'])
    
    after_count = len(df_aggregated)
    if before_count != after_count:
        print(f"[INFO] 分割取引を統合: {before_count}行 → {after_count}行 ({before_count - after_count}件統合)")
    
    return df_aggregated

