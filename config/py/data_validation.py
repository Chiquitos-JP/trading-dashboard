# -*- coding: utf-8 -*-
"""
データ検証ユーティリティ

データの整合性チェック、必須列の検証などを行います。
"""

import pandas as pd
from typing import List, Dict, Optional, Set
import warnings


def validate_required_columns(df: pd.DataFrame, required_columns: List[str], 
                             data_name: str = "データ") -> bool:
    """
    必須列の存在を検証
    
    Args:
        df: 検証するデータフレーム
        required_columns: 必須列名のリスト
        data_name: データ名（エラーメッセージ用）
        
    Returns:
        bool: すべての必須列が存在する場合True
        
    Raises:
        ValueError: 必須列が不足している場合
    """
    missing_columns = set(required_columns) - set(df.columns)
    
    if missing_columns:
        raise ValueError(
            f"{data_name}に必須列が不足しています: {missing_columns}\n"
            f"存在する列: {list(df.columns)}"
        )
    
    return True


def validate_currency_consistency(df: pd.DataFrame, 
                                  jpy_columns: List[str],
                                  data_name: str = "データ") -> bool:
    """
    通貨単位の一貫性を検証（JPY列の存在確認）
    
    Args:
        df: 検証するデータフレーム
        jpy_columns: JPY列名のリスト（例: ['ttl_gain_realized_jpy']）
        data_name: データ名（エラーメッセージ用）
        
    Returns:
        bool: 検証成功時True
    """
    missing_jpy_columns = []
    for col in jpy_columns:
        if col not in df.columns:
            missing_jpy_columns.append(col)
    
    if missing_jpy_columns:
        warnings.warn(
            f"{data_name}にJPY列が不足しています: {missing_jpy_columns}\n"
            f"通貨単位の統一が不完全な可能性があります。"
        )
        return False
    
    return True


def validate_data_types(df: pd.DataFrame,
                        type_spec: Dict[str, str],
                        data_name: str = "データ") -> bool:
    """
    データ型の検証
    
    Args:
        df: 検証するデータフレーム
        type_spec: 列名と期待される型の辞書（例: {'year_month': 'object', 'ttl_gain_realized_jpy': 'float64'}）
        data_name: データ名（エラーメッセージ用）
        
    Returns:
        bool: 検証成功時True
    """
    type_mismatches = []
    
    for col, expected_type in type_spec.items():
        if col not in df.columns:
            continue
        
        actual_type = str(df[col].dtype)
        if actual_type != expected_type:
            type_mismatches.append(f"{col}: 期待={expected_type}, 実際={actual_type}")
    
    if type_mismatches:
        warnings.warn(
            f"{data_name}のデータ型が期待と異なります:\n" + "\n".join(type_mismatches)
        )
        return False
    
    return True


def validate_numeric_range(df: pd.DataFrame,
                          column: str,
                          min_value: Optional[float] = None,
                          max_value: Optional[float] = None,
                          allow_negative: bool = True,
                          data_name: str = "データ") -> bool:
    """
    数値列の範囲検証
    
    Args:
        df: 検証するデータフレーム
        column: 検証する列名
        min_value: 最小値（Noneの場合はチェックしない）
        max_value: 最大値（Noneの場合はチェックしない）
        allow_negative: 負の値を許可するか
        data_name: データ名（エラーメッセージ用）
        
    Returns:
        bool: 検証成功時True
    """
    if column not in df.columns:
        warnings.warn(f"{data_name}に列 '{column}' が存在しません")
        return False
    
    series = pd.to_numeric(df[column], errors='coerce')
    
    # NaNチェック
    nan_count = series.isna().sum()
    if nan_count > 0:
        warnings.warn(f"{data_name}の列 '{column}' に {nan_count} 個のNaNが含まれています")
    
    # 範囲チェック
    if min_value is not None:
        below_min = (series < min_value).sum()
        if below_min > 0:
            warnings.warn(
                f"{data_name}の列 '{column}' に {below_min} 個の値が最小値 {min_value} を下回っています"
            )
    
    if max_value is not None:
        above_max = (series > max_value).sum()
        if above_max > 0:
            warnings.warn(
                f"{data_name}の列 '{column}' に {above_max} 個の値が最大値 {max_value} を上回っています"
            )
    
    if not allow_negative:
        negative_count = (series < 0).sum()
        if negative_count > 0:
            warnings.warn(
                f"{data_name}の列 '{column}' に {negative_count} 個の負の値が含まれています"
            )
    
    return True


def validate_date_consistency(df: pd.DataFrame,
                              date_column: str,
                              data_name: str = "データ") -> bool:
    """
    日付列の整合性検証
    
    Args:
        df: 検証するデータフレーム
        date_column: 日付列名
        data_name: データ名（エラーメッセージ用）
        
    Returns:
        bool: 検証成功時True
    """
    if date_column not in df.columns:
        warnings.warn(f"{data_name}に日付列 '{date_column}' が存在しません")
        return False
    
    # 日付として解析可能かチェック
    try:
        dates = pd.to_datetime(df[date_column], errors='coerce')
        invalid_dates = dates.isna().sum()
        
        if invalid_dates > 0:
            warnings.warn(
                f"{data_name}の日付列 '{date_column}' に {invalid_dates} 個の無効な日付が含まれています"
            )
            return False
        
        # 日付範囲の妥当性チェック（1900-2100年）
        year_range = dates.dt.year
        invalid_years = ((year_range < 1900) | (year_range > 2100)).sum()
        
        if invalid_years > 0:
            warnings.warn(
                f"{data_name}の日付列 '{date_column}' に {invalid_years} 個の異常な年が含まれています"
            )
            return False
        
        return True
        
    except Exception as e:
        warnings.warn(f"{data_name}の日付列 '{date_column}' の検証中にエラー: {e}")
        return False


def validate_merged_data(df: pd.DataFrame) -> Dict[str, bool]:
    """
    統合データの包括的検証
    
    Args:
        df: 検証するデータフレーム（統合データ）
        
    Returns:
        Dict[str, bool]: 検証結果の辞書
    """
    results = {}
    
    # 必須列の検証
    required_columns = [
        'year_month', 'broker', 'ttl_gain_realized_jpy',
        'ttl_amt_settlement_jpy', 'ttl_cost_acquisition_jpy'
    ]
    try:
        results['required_columns'] = validate_required_columns(
            df, required_columns, "統合データ"
        )
    except ValueError:
        results['required_columns'] = False
    
    # 通貨単位の検証
    jpy_columns = [
        'ttl_gain_realized_jpy', 'ttl_amt_settlement_jpy',
        'ttl_cost_acquisition_jpy'
    ]
    results['currency_consistency'] = validate_currency_consistency(
        df, jpy_columns, "統合データ"
    )
    
    # broker列の検証
    if 'broker' in df.columns:
        unique_brokers = df['broker'].unique()
        results['broker_validation'] = set(unique_brokers) == {'Rakuten', 'SBI'}
        if not results['broker_validation']:
            warnings.warn(f"broker列に予期しない値が含まれています: {unique_brokers}")
    else:
        results['broker_validation'] = False
    
    # 数値列の範囲検証
    if 'ttl_gain_realized_jpy' in df.columns:
        results['gain_range'] = validate_numeric_range(
            df, 'ttl_gain_realized_jpy', allow_negative=True, data_name="統合データ"
        )
    
    # 日付列の検証
    if 'year_month' in df.columns:
        results['date_consistency'] = validate_date_consistency(
            df, 'year_month', "統合データ"
        )
    
    return results

