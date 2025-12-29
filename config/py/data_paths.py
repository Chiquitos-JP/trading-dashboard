# -*- coding: utf-8 -*-
"""
データパス管理ユーティリティ

プロジェクト全体で統一されたデータパス管理を提供します。
拡張性を考慮した設計で、新しいデータソースを追加しやすくなっています。
"""

from pathlib import Path
from typing import Optional, Dict
import os


class DataPaths:
    """
    データパス管理クラス
    
    プロジェクト全体で統一されたデータアクセスを提供します。
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        初期化
        
        Args:
            project_root: プロジェクトルートディレクトリ（Noneの場合は自動検出）
        """
        if project_root is None:
            # このファイルからプロジェクトルートを自動検出
            # config/py/data_paths.py -> プロジェクトルート
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = Path(project_root)
        
        # 環境変数からも取得可能
        env_root = os.getenv("PROJECT_ROOT")
        if env_root:
            self.project_root = Path(env_root)
        
        self.data_root = self.project_root / "data"
    
    # ==================== 生データ（Raw Data） ====================
    
    def raw_trading_account(self, broker: str, data_type: str) -> Path:
        """
        取引アカウントの生データパス
        
        Args:
            broker: 証券会社名（"rakuten", "sbi"）
            data_type: データタイプ（"realized_pl", "transaction"）
            
        Returns:
            Path: 生データディレクトリのパス
        """
        return self.data_root / "trading_account" / data_type / "raw" / broker
    
    def raw_trading_account_master(self, broker: str, data_type: str) -> Path:
        """
        取引アカウントのマスターデータパス（rawフォルダ内）
        
        Args:
            broker: 証券会社名（"rakuten", "sbi"）
            data_type: データタイプ（"realized_pl", "transaction"）
            
        Returns:
            Path: マスターデータディレクトリのパス
        """
        return self.data_root / "trading_account" / data_type / "raw" / broker / "master"
    
    def raw_forex(self, source: str) -> Path:
        """
        為替レートの生データパス
        
        Args:
            source: データソース（"fred", "alphavantage"）
            
        Returns:
            Path: 生データファイルのパス
        """
        return self.data_root / "macro_economy" / "forex" / "raw" / source
    
    # ==================== 処理済みデータ（Processed Data） ====================
    
    def processed_trading_account(self, data_type: str, date_str: Optional[str] = None) -> Path:
        """
        取引アカウントの処理済みデータパス
        
        Args:
            data_type: データタイプ（"realized_pl", "transaction"）
            date_str: 日付文字列（YYYYMMDD形式、Noneの場合は最新を想定）
            
        Returns:
            Path: 処理済みデータディレクトリのパス
        """
        base = self.data_root / "trading_account" / data_type / "processed"
        if date_str:
            return base / f"{data_type}_{date_str}"
        return base
    
    def processed_forex(self) -> Path:
        """
        為替レートの処理済みデータパス
        
        Returns:
            Path: 処理済みデータディレクトリのパス
        """
        return self.data_root / "macro_economy" / "forex" / "processed"
    
    # ==================== チェックポイント（Checkpoints） ====================
    
    def checkpoints(self, data_type: str) -> Path:
        """
        チェックポイントデータパス
        
        Args:
            data_type: データタイプ（"realized_pl", "transaction"）
            
        Returns:
            Path: チェックポイントディレクトリのパス
        """
        return self.data_root / "trading_account" / data_type / "checkpoints"
    
    # ==================== 経済指標・市場データ ====================
    
    def economic_calendar(self, date_str: Optional[str] = None, latest: bool = False) -> Path:
        """
        経済指標カレンダーデータパス
        
        Args:
            date_str: 日付文字列（YYYYMMDD形式）
            latest: 最新版を取得するかどうか
            
        Returns:
            Path: データファイルのパス
        """
        base = self.data_root / "economicCalendar"
        if latest:
            return base / "economic_calendar_latest.parquet"
        elif date_str:
            return base / f"economic_calendar_{date_str}.parquet"
        return base
    
    def macro_fred(self, series_id: Optional[str] = None) -> Path:
        """
        FREDマクロ経済データパス
        
        Args:
            series_id: シリーズID（例: "VIXCLS", "FEDFUNDS"、Noneの場合はディレクトリ）
            
        Returns:
            Path: データファイルまたはディレクトリのパス
        """
        base = self.data_root / "macro_economy" / "fred"
        if series_id:
            return base / f"{series_id}.parquet"
        return base
    
    def market_data(self, data_type: str) -> Path:
        """
        市場データパス
        
        Args:
            data_type: データタイプ（"sp500", "sector_rotation"）
            
        Returns:
            Path: データファイルのパス
        """
        base = self.data_root / "market_data"
        if data_type == "sp500":
            return base / "sp500" / "ad_line.parquet"
        elif data_type == "sector_rotation":
            return base / "sector_rotation" / "sector_rotation.parquet"
        return base / data_type
    
    # ==================== その他 ====================
    
    def pictures(self) -> Path:
        """
        画像ファイルディレクトリパス
        
        Returns:
            Path: 画像ディレクトリのパス
        """
        return self.data_root / "picture"
    
    def custom_events(self) -> Path:
        """
        カスタムイベントファイルパス
        
        Returns:
            Path: カスタムイベントCSVファイルのパス
        """
        return self.data_root / "economicCalendar" / "custom_events.csv"
    
    def market_holidays(self) -> Path:
        """
        市場祝日ファイルパス
        
        Returns:
            Path: 市場祝日CSVファイルのパス
        """
        return self.data_root / "economicCalendar" / "us_market_holidays.csv"
    
    # ==================== ユーティリティ ====================
    
    def get_latest_file(self, directory: Path, pattern: str = "*.parquet", 
                       key_func: Optional[callable] = None) -> Optional[Path]:
        """
        ディレクトリ内の最新ファイルを取得
        
        Args:
            directory: 検索ディレクトリ
            pattern: ファイルパターン（glob形式）
            key_func: ソート用のキー関数（Noneの場合は更新日時）
            
        Returns:
            Path: 最新ファイルのパス、見つからない場合はNone
        """
        if not directory.exists():
            return None
        
        files = list(directory.glob(pattern))
        if not files:
            return None
        
        if key_func is None:
            key_func = lambda p: p.stat().st_mtime
        
        return max(files, key=key_func)
    
    def ensure_dir(self, path: Path) -> Path:
        """
        ディレクトリが存在しない場合は作成
        
        Args:
            path: ディレクトリパス
            
        Returns:
            Path: 作成されたディレクトリパス
        """
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    # ==================== 出力パス（Output Paths） ====================
    
    def outputs_figures(self, analysis_type: Optional[str] = None, 
                       date_str: Optional[str] = None) -> Path:
        """
        最終図表の出力パス
        
        Args:
            analysis_type: 分析タイプ（"realizedPl", "holdingPeriod", "riskAnalysis"など）
            date_str: 日付文字列（YYYYMMDD形式、Noneの場合はベースディレクトリ）
            
        Returns:
            Path: 出力ディレクトリのパス
        """
        base = self.project_root / "outputs" / "figures"
        if analysis_type and date_str:
            return base / f"{analysis_type}_{date_str}"
        elif analysis_type:
            return base / analysis_type
        return base
    
    def outputs_interim(self, category: Optional[str] = None) -> Path:
        """
        中間生成物の出力パス
        
        Args:
            category: カテゴリ（"economicCalendar", "macro", "market"など）
            
        Returns:
            Path: 出力ディレクトリのパス
        """
        base = self.project_root / "outputs" / "interim"
        if category:
            return base / category
        return base
    
    def outputs_reports(self) -> Path:
        """
        レポートの出力パス
        
        Returns:
            Path: レポートディレクトリのパス
        """
        return self.project_root / "outputs" / "reports"


# グローバルインスタンス（デフォルト）
_default_paths = None


def get_data_paths(project_root: Optional[Path] = None) -> DataPaths:
    """
    データパス管理インスタンスを取得（シングルトン）
    
    Args:
        project_root: プロジェクトルートディレクトリ
        
    Returns:
        DataPaths: データパス管理インスタンス
    """
    global _default_paths
    if _default_paths is None or project_root is not None:
        _default_paths = DataPaths(project_root)
    return _default_paths

