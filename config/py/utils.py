# -*- coding: utf-8 -*-
"""
共通ユーティリティ関数
"""

import pandas as pd
from pathlib import Path
from typing import Optional


def save_dataframe(df: pd.DataFrame, parquet_path: str, csv_path: Optional[str] = None, 
                   save_csv: bool = False, encoding: str = 'utf-8-sig') -> None:
    """
    データフレームをParquet形式で保存（必要に応じてCSVも保存）
    
    Args:
        df: 保存するデータフレーム
        parquet_path: Parquetファイルのパス
        csv_path: CSVファイルのパス（Noneの場合はparquet_pathから自動生成）
        save_csv: CSVも保存するかどうか（デフォルト: False）
        encoding: CSV保存時のエンコーディング（デフォルト: 'utf-8-sig'）
    """
    # Parquet形式で保存（常に実行）
    Path(parquet_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(parquet_path, index=False)
    
    # CSV形式で保存（必要時のみ）
    if save_csv:
        if csv_path is None:
            csv_path = str(Path(parquet_path).with_suffix('.csv'))
        df.to_csv(csv_path, index=False, encoding=encoding)
        print(f"    📄 CSVも保存: {csv_path}")


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

