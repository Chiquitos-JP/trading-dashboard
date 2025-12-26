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

