# -*- coding: utf-8 -*-
"""
トレーディング指標計算ユーティリティ

勝率、シャープレシオ、各種効率指標など、トレーディング分析で使用する指標を計算します。
"""

import pandas as pd
import numpy as np
from typing import Optional, List


def calculate_win_rate(df: pd.DataFrame,
                      gain_column: str,
                      group_by: Optional[str] = None) -> pd.DataFrame:
    """
    勝率を計算
    
    Args:
        df: データフレーム
        gain_column: 損益列名
        group_by: グループ化する列名（Noneの場合は全体）
        
    Returns:
        pd.DataFrame: 勝率を含むデータフレーム
    """
    df = df.copy()
    df['is_win'] = df[gain_column] > 0
    
    if group_by:
        win_rate_df = (
            df.groupby(group_by)
            .agg(
                win_trades=('is_win', 'sum'),
                total_trades=('is_win', 'count')
            )
            .assign(win_rate=lambda x: x['win_trades'] / x['total_trades'])
            .reset_index()[[group_by, 'win_rate']]
        )
    else:
        win_trades = df['is_win'].sum()
        total_trades = len(df)
        win_rate_df = pd.DataFrame({
            'win_rate': [win_trades / total_trades if total_trades > 0 else 0]
        })
    
    return win_rate_df


def calculate_sharpe_ratio(df: pd.DataFrame,
                          gain_column: str,
                          date_column: str,
                          group_by: str = "year_month") -> pd.DataFrame:
    """
    シャープレシオを計算（日次損益の標準偏差ベース）
    
    Args:
        df: データフレーム
        gain_column: 損益列名
        date_column: 日付列名
        group_by: グループ化する列名
        
    Returns:
        pd.DataFrame: sharpe_ratio を含むデータフレーム
    """
    # 日次損益を計算
    daily_returns = (
        df.groupby([group_by, date_column])[gain_column]
        .sum()
        .reset_index()
    )
    
    # 月次標準偏差
    monthly_std = (
        daily_returns.groupby(group_by)[gain_column]
        .std()
        .reset_index()
        .rename(columns={gain_column: 'daily_gain_std'})
    )
    
    # 月次平均損益
    monthly_mean = (
        daily_returns.groupby(group_by)[gain_column]
        .mean()
        .reset_index()
        .rename(columns={gain_column: 'avg_daily_gain'})
    )
    
    # シャープレシオ = 平均損益 / 標準偏差
    sharpe_df = monthly_mean.merge(monthly_std, on=group_by, how='left')
    sharpe_df['sharpe_ratio'] = sharpe_df['avg_daily_gain'] / sharpe_df['daily_gain_std']
    sharpe_df = sharpe_df[[group_by, 'sharpe_ratio']]
    
    return sharpe_df


def calculate_trading_metrics(df: pd.DataFrame,
                             gain_column: str,
                             group_by: str = "year_month",
                             date_column: Optional[str] = None) -> pd.DataFrame:
    """
    各種トレーディング指標を一括計算
    
    Args:
        df: データフレーム
        gain_column: 損益列名
        group_by: グループ化する列名
        date_column: 日付列名（シャープレシオ計算用）
        
    Returns:
        pd.DataFrame: 各種指標を含むデータフレーム
    """
    metrics_list = []
    
    # 勝率
    win_rate_df = calculate_win_rate(df, gain_column, group_by)
    metrics_list.append(win_rate_df)
    
    # 平均損益/1取引
    avg_gain_per_trade = (
        df.groupby(group_by)[gain_column]
        .mean()
        .reset_index()
        .rename(columns={gain_column: 'avg_gain_per_trade'})
    )
    metrics_list.append(avg_gain_per_trade)
    
    # シャープレシオ（日付列がある場合）
    if date_column:
        sharpe_df = calculate_sharpe_ratio(df, gain_column, date_column, group_by)
        metrics_list.append(sharpe_df)
    
    # すべての指標をマージ
    result = metrics_list[0]
    for metric_df in metrics_list[1:]:
        result = result.merge(metric_df, on=group_by, how='outer')
    
    return result


def calculate_gain_loss_split(df: pd.DataFrame,
                             gain_column: str,
                             group_by: str = "year_month") -> pd.DataFrame:
    """
    利益と損失を分離して集計
    
    Args:
        df: データフレーム
        gain_column: 損益列名
        group_by: グループ化する列名
        
    Returns:
        pd.DataFrame: ttl_gain_only, ttl_loss_only を含むデータフレーム
    """
    df = df.copy()
    df['gain_only'] = df[gain_column].apply(lambda x: x if x > 0 else 0)
    df['loss_only'] = df[gain_column].apply(lambda x: abs(x) if x < 0 else 0)
    
    result = (
        df.groupby(group_by)
        .agg(
            ttl_gain_only=('gain_only', 'sum'),
            ttl_loss_only=('loss_only', 'sum')
        )
        .reset_index()
    )
    
    return result

