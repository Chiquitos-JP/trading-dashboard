# -*- coding: utf-8 -*-
"""
ファイル操作共通ユーティリティ

日付フォルダの作成、ファイル保存など、ファイル操作の共通処理を提供します。
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional


def create_dated_folder(base_dir: Path, prefix: str = "", 
                       date_str: Optional[str] = None) -> Path:
    """
    日付付きフォルダを作成
    
    Args:
        base_dir: ベースディレクトリ
        prefix: フォルダ名のプレフィックス（例: "realizedPl_"）
        date_str: 日付文字列（YYYYMMDD形式、Noneの場合は今日）
        
    Returns:
        Path: 作成されたフォルダのパス
    """
    if date_str is None:
        date_str = datetime.today().strftime('%Y%m%d')
    
    folder_name = f"{prefix}{date_str}" if prefix else date_str
    dated_folder = base_dir / folder_name
    dated_folder.mkdir(parents=True, exist_ok=True)
    
    return dated_folder


def get_dated_output_path(base_dir: Path, filename: str,
                          prefix: str = "",
                          date_str: Optional[str] = None,
                          extension: str = ".parquet") -> Path:
    """
    日付付き出力ファイルパスを取得（フォルダも自動作成）
    
    Args:
        base_dir: ベースディレクトリ
        filename: ファイル名（拡張子なし、または拡張子付き）
        prefix: フォルダ名のプレフィックス
        date_str: 日付文字列（YYYYMMDD形式、Noneの場合は今日）
        extension: ファイル拡張子（filenameに拡張子がない場合に使用）
        
    Returns:
        Path: 出力ファイルのパス
    """
    dated_folder = create_dated_folder(base_dir, prefix, date_str)
    
    # 拡張子の処理
    if not filename.endswith(extension):
        filename = f"{filename}{extension}"
    
    return dated_folder / filename

