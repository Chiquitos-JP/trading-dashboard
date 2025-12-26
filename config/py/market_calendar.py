# -*- coding: utf-8 -*-
"""
市場カレンダー関連ユーティリティ

営業日数の計算など、市場カレンダーに関する共通処理を提供します。
"""

import pandas as pd
from typing import List, Optional
try:
    import pandas_market_calendars as mcal
    HAS_MCAL = True
except ImportError:
    HAS_MCAL = False
    print("[WARNING] pandas_market_calendars がインストールされていません。市場カレンダー機能は使用できません。")


def get_market_open_days(year_months: List[str], 
                        calendar_name: str = "NYSE",
                        start_date: Optional[pd.Timestamp] = None,
                        end_date: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    """
    月ごとの営業日数を取得
    
    Args:
        year_months: 年月リスト（例: ["2024-01", "2024-02"]）
        calendar_name: カレンダー名（デフォルト: "NYSE"）
        start_date: 開始日（指定しない場合は自動計算）
        end_date: 終了日（指定しない場合は自動計算）
        
    Returns:
        pd.DataFrame: year_month, market_open_days を含むデータフレーム
    """
    if not HAS_MCAL:
        raise ImportError("pandas_market_calendars が必要です。pip install pandas_market_calendars")
    
    # 年月から日付範囲を計算
    if start_date is None or end_date is None:
        dates = [pd.to_datetime(ym + "-01") for ym in year_months]
        if dates:
            start_date = min(dates)
            end_date = max(dates) + pd.offsets.MonthEnd(0)
    
    # カレンダーを取得
    calendar = mcal.get_calendar(calendar_name)
    
    # 営業日スケジュールを取得
    schedule = calendar.schedule(start_date=start_date, end_date=end_date)
    
    # 年月カラムを追加
    schedule["year_month"] = schedule.index.to_series().dt.to_period("M").astype(str)
    
    # 月別営業日数
    market_days_df = schedule.groupby("year_month").size().reset_index(name="market_open_days")
    
    return market_days_df


def get_market_open_days_for_dataframe(df: pd.DataFrame,
                                      year_month_column: str = "year_month",
                                      calendar_name: str = "NYSE") -> pd.DataFrame:
    """
    データフレームの年月列から営業日数を取得してマージ
    
    Args:
        df: データフレーム
        year_month_column: 年月列名
        calendar_name: カレンダー名
        
    Returns:
        pd.DataFrame: market_open_days が追加されたデータフレーム
    """
    if year_month_column not in df.columns:
        raise ValueError(f"列 '{year_month_column}' が見つかりません")
    
    year_months = df[year_month_column].unique().tolist()
    market_days_df = get_market_open_days(year_months, calendar_name)
    
    # マージ
    result = df.merge(market_days_df, on=year_month_column, how="left")
    
    return result

