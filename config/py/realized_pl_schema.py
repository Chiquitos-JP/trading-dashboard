# -*- coding: utf-8 -*-
"""
実現損益（Realized P/L）マスターデータの統一スキーマ定義

両社（楽天、SBI）のマスターデータを統一フォーマットに変換するための
列定義と変換関数を提供します。
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional

# ==================== 統一列定義 ====================
# 両社のマスターデータで共通に持つべき列（順序も統一）

UNIFIED_COLUMNS = [
    # 基本情報
    "settlement_date",        # 決済日
    "contract_date",          # 約定日
    "ticker",                 # ティッカー
    "stock_name",             # 銘柄名
    "market",                 # 市場（NYSE, NASDAQ等）
    "broker",                 # 証券会社
    
    # 取引情報
    "transaction_type",       # 取引種別
    "custody_type",           # 口座種別（特定/一般）
    "num_of_shares",          # 株数
    
    # 価格情報（USD）
    "contract_UnitPrice_usd",         # 約定単価（USD）
    "avg_UnitPrice_settlement_usd",   # 決済単価（USD）
    "ttl_amt_settlement_usd",         # 決済金額（USD）
    "fees_usd",                       # 手数料（USD）
    "ttl_gain_realized_usd",          # 実現損益（USD）
    
    # 価格情報（JPY）
    "contract_UnitPrice_jpy",         # 約定単価（JPY）
    "avg_UnitPrice_settlement_jpy",   # 決済単価（JPY）
    "ttl_amt_settlement_jpy",         # 決済金額（JPY）
    "fees_jpy",                       # 手数料（JPY）
    "ttl_gain_realized_jpy",          # 実現損益（JPY）
    
    # 為替情報
    "fx_rate",                # 適用為替レート
    "currency",               # 通貨
    
    # メタ情報
    "year_month",             # 年月（YYYY-MM）
]

# 各列のデータ型
COLUMN_DTYPES = {
    "settlement_date": "datetime64[ns]",
    "contract_date": "datetime64[ns]",
    "ticker": "object",
    "stock_name": "object",
    "market": "object",
    "broker": "object",
    "transaction_type": "object",
    "custody_type": "object",
    "num_of_shares": "Int64",
    "contract_UnitPrice_usd": "float64",
    "avg_UnitPrice_settlement_usd": "float64",
    "ttl_amt_settlement_usd": "float64",
    "fees_usd": "float64",
    "ttl_gain_realized_usd": "float64",
    "contract_UnitPrice_jpy": "float64",
    "avg_UnitPrice_settlement_jpy": "float64",
    "ttl_amt_settlement_jpy": "float64",
    "fees_jpy": "float64",
    "ttl_gain_realized_jpy": "float64",
    "fx_rate": "float64",
    "currency": "object",
    "year_month": "object",
}


def load_fx_rates(fx_file_path: Path) -> pd.DataFrame:
    """
    為替レートファイルを読み込む
    
    Args:
        fx_file_path: 為替レートファイルのパス
        
    Returns:
        pd.DataFrame: 為替レートデータ（year_monthをインデックス）
    """
    if not fx_file_path.exists():
        raise FileNotFoundError(f"為替レートファイルが見つかりません: {fx_file_path}")
    
    df_fx = pd.read_csv(fx_file_path)
    
    # year_month列を作成
    if 'year_month' not in df_fx.columns:
        if 'date' in df_fx.columns:
            df_fx['year_month'] = pd.to_datetime(df_fx['date']).dt.strftime('%Y-%m')
        elif 'observation_date' in df_fx.columns:
            df_fx['year_month'] = pd.to_datetime(df_fx['observation_date']).dt.strftime('%Y-%m')
    
    # usd_to_jpy列を確認
    fx_col = None
    for col in ['usd_to_jpy_avg', 'DEXJPUS', 'rate']:
        if col in df_fx.columns:
            fx_col = col
            break
    
    if fx_col is None:
        raise ValueError(f"為替レート列が見つかりません。利用可能な列: {list(df_fx.columns)}")
    
    # year_monthとfx_rateのみを返す
    df_fx = df_fx[['year_month', fx_col]].rename(columns={fx_col: 'fx_rate'})
    df_fx = df_fx.drop_duplicates(subset=['year_month'], keep='first')
    
    return df_fx.set_index('year_month')


def convert_usd_to_jpy(df: pd.DataFrame, df_fx: pd.DataFrame, usd_columns: list) -> pd.DataFrame:
    """
    USD列をJPYに変換
    
    Args:
        df: データフレーム
        df_fx: 為替レートデータ
        usd_columns: 変換するUSD列のリスト
        
    Returns:
        pd.DataFrame: JPY列が追加されたデータフレーム
    """
    df = df.copy()
    
    # 為替レートをマージ
    if 'year_month' not in df.columns:
        df['year_month'] = pd.to_datetime(df['settlement_date']).dt.strftime('%Y-%m')
    
    if 'fx_rate' not in df.columns:
        df = df.merge(df_fx, left_on='year_month', right_index=True, how='left')
    
    # USD→JPY変換
    for usd_col in usd_columns:
        if usd_col in df.columns:
            jpy_col = usd_col.replace('_usd', '_jpy')
            if jpy_col not in df.columns or df[jpy_col].isna().all():
                df[jpy_col] = df[usd_col] * df['fx_rate']
    
    return df


def convert_jpy_to_usd(df: pd.DataFrame, df_fx: pd.DataFrame, jpy_columns: list) -> pd.DataFrame:
    """
    JPY列をUSDに変換
    
    Args:
        df: データフレーム
        df_fx: 為替レートデータ
        jpy_columns: 変換するJPY列のリスト
        
    Returns:
        pd.DataFrame: USD列が追加されたデータフレーム
    """
    df = df.copy()
    
    # 為替レートをマージ
    if 'year_month' not in df.columns:
        df['year_month'] = pd.to_datetime(df['settlement_date']).dt.strftime('%Y-%m')
    
    if 'fx_rate' not in df.columns:
        df = df.merge(df_fx, left_on='year_month', right_index=True, how='left')
    
    # JPY→USD変換
    for jpy_col in jpy_columns:
        if jpy_col in df.columns:
            usd_col = jpy_col.replace('_jpy', '_usd')
            if usd_col not in df.columns or df[usd_col].isna().all():
                df[usd_col] = df[jpy_col] / df['fx_rate']
    
    return df


def standardize_columns(df: pd.DataFrame, broker: str) -> pd.DataFrame:
    """
    データフレームの列を統一フォーマットに変換
    
    Args:
        df: データフレーム
        broker: 証券会社名（"Rakuten" or "SBI"）
        
    Returns:
        pd.DataFrame: 統一フォーマットのデータフレーム
    """
    df = df.copy()
    
    # broker列を追加
    if 'broker' not in df.columns:
        df['broker'] = broker
    
    # 不足している列を追加
    for col in UNIFIED_COLUMNS:
        if col not in df.columns:
            # データ型に応じたデフォルト値
            if COLUMN_DTYPES.get(col) == "datetime64[ns]":
                df[col] = pd.NaT
            elif COLUMN_DTYPES.get(col) in ["float64", "Int64"]:
                df[col] = np.nan
            else:
                df[col] = ""
    
    # 列の順序を統一
    existing_unified = [col for col in UNIFIED_COLUMNS if col in df.columns]
    extra_cols = [col for col in df.columns if col not in UNIFIED_COLUMNS]
    df = df[existing_unified + extra_cols]
    
    return df


def apply_unified_schema(df: pd.DataFrame, broker: str, fx_file_path: Optional[Path] = None) -> pd.DataFrame:
    """
    統一スキーマを適用
    
    Args:
        df: データフレーム
        broker: 証券会社名
        fx_file_path: 為替レートファイルのパス
        
    Returns:
        pd.DataFrame: 統一スキーマ適用後のデータフレーム
    """
    df = df.copy()
    
    # 為替レートを読み込み
    if fx_file_path and fx_file_path.exists():
        df_fx = load_fx_rates(fx_file_path)
        
        # USD列があればJPYに変換
        usd_cols = [c for c in df.columns if c.endswith('_usd') and c.replace('_usd', '_jpy') in UNIFIED_COLUMNS]
        if usd_cols:
            df = convert_usd_to_jpy(df, df_fx, usd_cols)
        
        # JPY列があればUSDに変換
        jpy_cols = [c for c in df.columns if c.endswith('_jpy') and c.replace('_jpy', '_usd') in UNIFIED_COLUMNS]
        if jpy_cols:
            df = convert_jpy_to_usd(df, df_fx, jpy_cols)
    
    # 列を統一
    df = standardize_columns(df, broker)
    
    return df

