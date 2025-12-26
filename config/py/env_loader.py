# -*- coding: utf-8 -*-
"""
環境変数読み込みユーティリティ

.envファイルから環境変数を読み込む汎用関数を提供します。
"""

import os
from pathlib import Path
from typing import Dict, Optional, List


def load_env_file(env_path: Optional[Path] = None, 
                 search_paths: Optional[List[Path]] = None) -> Dict[str, str]:
    """
    .envファイルから環境変数を読み込む
    
    Args:
        env_path: .envファイルのパス（指定しない場合は自動検索）
        search_paths: 検索パスのリスト（デフォルト: プロジェクトルート、カレントディレクトリ）
        
    Returns:
        Dict[str, str]: 環境変数の辞書
    """
    env_vars = {}
    
    # 検索パスの決定
    if search_paths is None:
        # このファイルからプロジェクトルートを推定
        config_py_dir = Path(__file__).parent
        project_root = config_py_dir.parent.parent
        search_paths = [
            project_root / ".env",
            Path.cwd() / ".env",
        ]
    
    # 指定されたパスがある場合は優先
    if env_path and env_path.exists():
        search_paths = [env_path] + search_paths
    
    # 各パスから読み込み
    for env_path in search_paths:
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 空行、コメント行をスキップ
                    if not line or line.startswith('#'):
                        continue
                    
                    # KEY=VALUE形式をパース
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # 引用符を除去
                        value = value.strip('"').strip("'")
                        key = key.strip()
                        env_vars[key] = value
                        # 環境変数にも設定
                        os.environ[key] = value
    
    return env_vars


def get_env(key: str, default: Optional[str] = None, 
           env_path: Optional[Path] = None) -> Optional[str]:
    """
    環境変数を取得（.envファイルからも自動読み込み）
    
    Args:
        key: 環境変数名
        default: デフォルト値
        env_path: .envファイルのパス（指定しない場合は自動検索）
        
    Returns:
        str: 環境変数の値、見つからない場合はdefault
    """
    # 既に環境変数に設定されている場合はそれを返す
    value = os.getenv(key)
    if value:
        return value
    
    # .envファイルから読み込み
    if env_path or not value:
        load_env_file(env_path)
        value = os.getenv(key)
    
    return value if value is not None else default

