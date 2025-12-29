# -*- coding: utf-8 -*-
"""
汎用的なマスターデータ管理クラス

様々なデータタイプ（realized_pl, transaction, 将来のデータタイプ）に
対応できる設計
"""

import pandas as pd
import shutil
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from data_paths import DataPaths


class MasterDataManager:
    """
    汎用的なマスターデータ管理クラス
    
    様々なデータタイプ（realized_pl, transaction, 将来のデータタイプ）に
    対応できる設計
    """
    
    def __init__(self, broker: str, data_type: str, key_columns: List[str], 
                 numeric_rounding: Dict[str, int] = None,
                 date_columns: List[str] = None):
        """
        初期化
        
        Args:
            broker: 証券会社名（"rakuten", "sbi"）
            data_type: データタイプ（"realized_pl", "transaction"）
            key_columns: 重複判定用のキー列
            numeric_rounding: 数値列の丸め桁数（列名: 桁数）
            date_columns: 日付列のリスト（自動変換用）
        """
        self.broker = broker
        self.data_type = data_type
        self.key_columns = key_columns
        self.numeric_rounding = numeric_rounding or {}
        self.date_columns = date_columns or []
        
    def get_master_file_path(self, paths: DataPaths) -> Path:
        """マスターファイルのパスを取得"""
        master_folder = paths.raw_trading_account_master(self.broker, self.data_type)
        return master_folder / f"master_{self.data_type}_{self.broker}.parquet"
    
    def load_master_data(self, paths: DataPaths, 
                        convert_to_datetime_func=None) -> Optional[pd.DataFrame]:
        """
        マスターデータを読み込む
        
        Args:
            paths: DataPathsインスタンス
            convert_to_datetime_func: 日付変換関数（オプション）
            
        Returns:
            pd.DataFrame: マスターデータ、存在しない場合はNone
        """
        master_file = self.get_master_file_path(paths)
        
        if not master_file.exists():
            return None
        
        try:
            print(f"[INFO] マスターデータ読み込み: {master_file}")
            df_master = pd.read_parquet(master_file)
            print(f"   マスターデータ行数: {len(df_master)}")
            
            # 日付列の変換
            if convert_to_datetime_func:
                for col in self.date_columns:
                    if col in df_master.columns:
                        if df_master[col].dtype != "datetime64[ns]":
                            df_master[col] = convert_to_datetime_func(df_master[col])
            
            return df_master
        except Exception as e:
            print(f"   [WARNING] マスターデータ読み込みエラー: {e}")
            return None
    
    def apply_numeric_rounding(self, df: pd.DataFrame) -> pd.DataFrame:
        """数値列の丸め処理を適用"""
        df = df.copy()
        for col, decimals in self.numeric_rounding.items():
            if col in df.columns:
                # 数値型に変換してから丸め処理
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].round(decimals)
        return df
    
    def deduplicate(self, df_new: pd.DataFrame, 
                   df_master: Optional[pd.DataFrame]) -> pd.DataFrame:
        """
        重複除去処理
        
        Args:
            df_new: 新しいデータ
            df_master: マスターデータ（Noneの場合は新規データをそのまま返す）
            
        Returns:
            pd.DataFrame: 重複除去後の新しいデータ
        """
        # 数値の丸め処理
        df_new = self.apply_numeric_rounding(df_new)
        
        if df_master is None:
            return df_new
        
        # マスターデータも丸め処理
        df_master = self.apply_numeric_rounding(df_master)
        
        # パフォーマンス最適化: 最新データの日付範囲でフィルタリング
        if len(df_master) > 10000 and self.date_columns:
            # 最初の日付列を使用
            date_col = self.date_columns[0]
            if date_col in df_new.columns and date_col in df_master.columns:
                min_date = df_new[date_col].min()
                df_master_filtered = df_master[
                    df_master[date_col] >= min_date - pd.Timedelta(days=90)
                ]
                print(f"   フィルタリング後: {len(df_master_filtered)}行（90日以内）")
            else:
                df_master_filtered = df_master
        else:
            df_master_filtered = df_master
        
        # 重複除去：マスターデータに存在する行を新しいデータから除外
        # キー列が存在することを確認
        missing_keys = [col for col in self.key_columns 
                       if col not in df_new.columns or col not in df_master_filtered.columns]
        if missing_keys:
            print(f"   [WARNING] キー列が不足しています: {missing_keys}")
            return df_new
        
        df_merged_check = df_new[self.key_columns].merge(
            df_master_filtered[self.key_columns],
            on=self.key_columns,
            how="left",
            indicator=True
        )
        df_new_unique = df_new[df_merged_check["_merge"] == "left_only"].copy()
        
        print(f"   新規データ行数: {len(df_new)}")
        print(f"   重複除外後: {len(df_new_unique)}")
        
        return df_new_unique
    
    def merge_with_master(self, df_new: pd.DataFrame, 
                          df_master: Optional[pd.DataFrame]) -> tuple[pd.DataFrame, bool]:
        """
        マスターデータと統合
        
        Args:
            df_new: 新しいデータ
            df_master: マスターデータ
            
        Returns:
            tuple[pd.DataFrame, bool]: (統合後のデータ, 更新が必要かどうか)
        """
        df_new_unique = self.deduplicate(df_new, df_master)
        
        if len(df_new_unique) > 0:
            if df_master is not None:
                df_merged = pd.concat([df_master, df_new_unique], ignore_index=True)
                print(f"   統合後行数: {len(df_merged)}")
                return df_merged, True
            else:
                print(f"   統合後行数: {len(df_new_unique)}")
                return df_new_unique, True
        else:
            if df_master is not None:
                print("   [WARNING] 新規データがありませんでした")
                return df_master, False
            else:
                print("   [WARNING] データがありません")
                return df_new, False
    
    def save_master_data(self, df: pd.DataFrame, paths: DataPaths) -> bool:
        """
        マスターデータを保存
        
        Args:
            df: 保存するデータ
            paths: DataPathsインスタンス
            
        Returns:
            bool: 成功時True
        """
        try:
            master_file = self.get_master_file_path(paths)
            master_folder = master_file.parent
            
            # バックアップ
            if master_file.exists():
                backup_file = master_folder / (
                    f"master_{self.data_type}_{self.broker}_backup_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
                )
                shutil.copy2(master_file, backup_file)
                print(f"[INFO] マスターデータバックアップ: {backup_file.name}")
            
            # ディレクトリ作成
            master_folder.mkdir(parents=True, exist_ok=True)
            
            # 保存
            df.to_parquet(master_file, index=False)
            print(f"[INFO] マスターデータ保存完了: {master_file} ({len(df)}行)")
            return True
        except Exception as e:
            print(f"[WARNING] マスターデータ保存エラー: {e}")
            return False

