# -*- coding: utf-8 -*-
"""
データメタデータ管理ユーティリティ

データファイルのメタデータ（作成日時、バージョン、データソースなど）を管理します。
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json
import pandas as pd


class DataMetadata:
    """
    データメタデータ管理クラス
    """
    
    def __init__(self, data_root: Path):
        """
        初期化
        
        Args:
            data_root: データルートディレクトリ
        """
        self.data_root = Path(data_root)
        self.metadata_dir = self.data_root / ".metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def get_metadata_file(self, data_path: Path) -> Path:
        """
        データファイルに対応するメタデータファイルのパスを取得
        
        Args:
            data_path: データファイルのパス
            
        Returns:
            Path: メタデータファイルのパス
        """
        # データファイルの相対パスを取得
        rel_path = data_path.relative_to(self.data_root)
        # メタデータファイル名（拡張子を.jsonに変更）
        metadata_name = str(rel_path).replace("/", "_").replace("\\", "_") + ".json"
        return self.metadata_dir / metadata_name
    
    def save_metadata(self, data_path: Path, metadata: Dict[str, Any]) -> None:
        """
        データファイルのメタデータを保存
        
        Args:
            data_path: データファイルのパス
            metadata: メタデータ辞書
        """
        metadata_file = self.get_metadata_file(data_path)
        
        # デフォルトのメタデータ
        default_metadata = {
            "data_path": str(data_path.relative_to(self.data_root)),
            "created_at": datetime.now().isoformat(),
            "file_size": data_path.stat().st_size if data_path.exists() else 0,
            "file_modified": datetime.fromtimestamp(data_path.stat().st_mtime).isoformat() if data_path.exists() else None,
        }
        
        # デフォルトとユーザー指定のメタデータをマージ
        full_metadata = {**default_metadata, **metadata}
        
        # 保存
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(full_metadata, f, indent=2, ensure_ascii=False)
    
    def load_metadata(self, data_path: Path) -> Optional[Dict[str, Any]]:
        """
        データファイルのメタデータを読み込み
        
        Args:
            data_path: データファイルのパス
            
        Returns:
            Dict: メタデータ辞書、見つからない場合はNone
        """
        metadata_file = self.get_metadata_file(data_path)
        
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_data_info(self, data_path: Path) -> Dict[str, Any]:
        """
        データファイルの情報を取得（メタデータ + ファイル情報）
        
        Args:
            data_path: データファイルのパス
            
        Returns:
            Dict: データ情報辞書
        """
        info = {
            "path": str(data_path),
            "exists": data_path.exists(),
        }
        
        if data_path.exists():
            stat = data_path.stat()
            info.update({
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
            
            # Parquetファイルの場合は追加情報を取得
            if data_path.suffix == ".parquet":
                try:
                    df = pd.read_parquet(data_path, nrows=0)  # ヘッダーのみ読み込み
                    info.update({
                        "columns": list(df.columns),
                        "num_columns": len(df.columns),
                    })
                except Exception as e:
                    info["error"] = str(e)
        
        # メタデータを追加
        metadata = self.load_metadata(data_path)
        if metadata:
            info["metadata"] = metadata
        
        return info


def get_data_metadata(data_root: Optional[Path] = None) -> DataMetadata:
    """
    データメタデータ管理インスタンスを取得
    
    Args:
        data_root: データルートディレクトリ（Noneの場合は自動検出）
        
    Returns:
        DataMetadata: データメタデータ管理インスタンス
    """
    if data_root is None:
        from data_paths import get_data_paths
        paths = get_data_paths()
        data_root = paths.data_root
    
    return DataMetadata(data_root)

