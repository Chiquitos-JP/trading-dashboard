# -*- coding: utf-8 -*-
"""
共通ユーティリティ関数
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
import warnings


def normalize_dataframe_schema(df: pd.DataFrame, 
                               date_columns: Optional[list] = None,
                               string_columns: Optional[list] = None) -> pd.DataFrame:
    """
    データフレームのスキーマを正規化（データ型の統一、エンコーディング処理）
    
    Args:
        df: 正規化するデータフレーム
        date_columns: 日付列のリスト（datetime64[ns]に統一）
        string_columns: 文字列列のリスト（object型に統一、UTF-8エンコーディング）
        
    Returns:
        pd.DataFrame: 正規化されたデータフレーム
    """
    df = df.copy()
    date_columns = date_columns or []
    string_columns = string_columns or []
    
    # 日付列をdatetime64[ns]に統一
    for col in date_columns:
        if col in df.columns:
            if df[col].dtype != 'datetime64[ns]':
                df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # 文字列列をobject型に統一（UTF-8エンコーディング）
    for col in string_columns:
        if col in df.columns:
            if df[col].dtype != 'object':
                df[col] = df[col].astype(str)
            # 文字列列のnull値を空文字列に統一（NaNはNoneに変換してから空文字列に）
            df[col] = df[col].fillna('')
            # 文字列のエンコーディングを確認（必要に応じてUTF-8に変換）
            try:
                # 既にUTF-8として扱える文字列はそのまま
                df[col] = df[col].astype(str)
            except Exception as e:
                warnings.warn(f"列 '{col}' のエンコーディング変換で警告: {e}")
    
    # float型のNaNを明示的にNoneに変換（Parquet保存時の一貫性のため）
    for col in df.select_dtypes(include=[np.number]).columns:
        df[col] = df[col].replace([np.inf, -np.inf], np.nan)
    
    return df


def save_dataframe(df: pd.DataFrame, parquet_path: str, csv_path: Optional[str] = None, 
                   save_csv: bool = False, encoding: str = 'utf-8-sig',
                   normalize_schema: bool = True,
                   date_columns: Optional[list] = None,
                   string_columns: Optional[list] = None) -> None:
    """
    データフレームをParquet形式で保存（必要に応じてCSVも保存）
    スキーマの正規化も実行
    
    Args:
        df: 保存するデータフレーム
        parquet_path: Parquetファイルのパス
        csv_path: CSVファイルのパス（Noneの場合はparquet_pathから自動生成）
        save_csv: CSVも保存するかどうか（デフォルト: False）
        encoding: CSV保存時のエンコーディング（デフォルト: 'utf-8-sig')
        normalize_schema: スキーマを正規化するかどうか（デフォルト: True）
        date_columns: 日付列のリスト（normalize_schema=Trueの場合）
        string_columns: 文字列列のリスト（normalize_schema=Trueの場合）
    """
    # スキーマの正規化
    if normalize_schema:
        df = normalize_dataframe_schema(df, date_columns=date_columns, string_columns=string_columns)
    
    # Parquet形式で保存（常に実行）
    # パスを正規化（絶対パスに変換）
    import os
    import tempfile
    import shutil
    
    parquet_path_obj = Path(parquet_path).resolve()
    
    # 親ディレクトリを作成
    try:
        parquet_path_obj.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"    [WARNING] ディレクトリ作成エラー: {e}")
        # 相対パスで再試行
        parquet_path_obj = Path(parquet_path)
        parquet_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    # データフレームに無効なデータ型がないか確認
    # object型の列にNaNが含まれている場合、Noneに変換
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].isna().any():
            df[col] = df[col].where(df[col].notna(), None)
    
    try:
        # パスを文字列に変換（os.path.normpathで正規化）
        parquet_path_str = os.path.normpath(str(parquet_path_obj))
        
        # 既存ファイルがある場合は削除（Windowsのファイルロック問題を回避）
        if parquet_path_obj.exists():
            try:
                parquet_path_obj.unlink()
            except Exception:
                pass  # 削除に失敗しても続行
        
        # Parquet保存時にエラーが発生しないよう、データ型を確認
        df.to_parquet(parquet_path_str, index=False, engine='pyarrow', compression='snappy')
        print(f"    [SUCCESS] Parquet保存完了: {Path(parquet_path).name} ({len(df)}行, {len(df.columns)}列)")
    except Exception as e:
        # エラーが発生した場合、詳細を出力して再試行
        print(f"    [WARNING] Parquet保存エラー: {e}")
        print(f"    データ型を確認して再試行します...")
        # データ型を確認
        print(f"    データ型情報:")
        for col in df.columns:
            print(f"      {col}: {df[col].dtype}")
        raise
    
    # CSV形式で保存（必要時のみ）
    if save_csv:
        if csv_path is None:
            csv_path = str(Path(parquet_path).with_suffix('.csv'))
        df.to_csv(csv_path, index=False, encoding=encoding)
        print(f"    [INFO] CSVも保存: {csv_path}")


def parquet_to_csv(parquet_path: str, csv_path: Optional[str] = None, 
                   encoding: str = 'utf-8-sig') -> str:
    """
    ParquetファイルをCSVに変換（必要時のみ使用）
    
    Args:
        parquet_path: Parquetファイルのパス
        csv_path: 出力CSVファイルのパス（Noneの場合は自動生成）
        encoding: CSV保存時のエンコーディング
        
    Returns:
        str: CSVファイルのパス
    """
    df = pd.read_parquet(parquet_path)
    
    if csv_path is None:
        csv_path = str(Path(parquet_path).with_suffix('.csv'))
    
    df.to_csv(csv_path, index=False, encoding=encoding)
    return csv_path
