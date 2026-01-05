# -*- coding: utf-8 -*-
"""
社名変更・ティッカー変更に伴うstock_name/ticker補完マッピング

このファイルは、生データでstock_nameやtickerが空欄になっている場合に、
正しい値を補完するためのマッピングテーブルです。

使用方法:
    from config.py.stock_name_overrides import get_stock_name_override, get_ticker_override
    
    # stock_nameが空欄の場合、マッピングを適用
    if pd.isna(row['stock_name']) or row['stock_name'] == '':
        override = get_stock_name_override(row['ticker'], row.get('settlement_date'))
        if override:
            row['stock_name'] = override
    
    # tickerが空欄の場合、stock_nameから推論
    if pd.isna(row['ticker']) or row['ticker'] == '':
        override = get_ticker_override(row['stock_name'])
        if override:
            row['ticker'] = override
"""

from typing import Optional, Tuple
import pandas as pd
from datetime import datetime

# ==================== ティッカー変更マッピング ====================
# 形式: {old_ticker: new_ticker}
# 旧ティッカーを新ティッカーに変換

OLD_TO_NEW_TICKER_MAPPING = {
    # Tempur Sealy International → Somnigroup
    # 旧ティッカー: TPX → 新ティッカー: SGI
    'TPX': 'SGI',
}

# ==================== ティッカー→銘柄情報マッピング ====================
# 形式: {ticker: {'stock_name': 'Company Name', 'market': 'NYSE'}}
# 社名変更やティッカー変更に伴う空欄を補完するために使用

TICKER_TO_STOCK_INFO_MAPPING = {
    # 社名変更: Tempur Sealy International → Somnigroup
    # 新ティッカー: SGI (NYSE上場)
    'SGI': {'stock_name': 'Somnigroup', 'market': 'NYSE'},
    'TPX': {'stock_name': 'Somnigroup', 'market': 'NYSE'},  # 旧ティッカーでも同じ情報にマッピング
    
    # 上場廃止銘柄: Hawaiian Holdings, Inc. (HA)
    # 2024年9月18日にNASDAQで上場廃止（Alaska Air Groupに買収）
    # 上場廃止前はNASDAQで取引されていたため、marketをNASDAQに設定
    'HA': {'stock_name': 'Hawaiian Holdings, Inc.', 'market': 'NASDAQ'},
    
    # 将来的に他の社名変更が発生した場合、ここに追加
    # 'OLD_TICKER': {'stock_name': 'New Company Name', 'market': 'NASDAQ'},
}

# 後方互換性のため、stock_nameのみのマッピングも維持
TICKER_TO_STOCK_NAME_MAPPING = {k: v['stock_name'] for k, v in TICKER_TO_STOCK_INFO_MAPPING.items()}

# ==================== 銘柄名→ティッカー/銘柄情報マッピング ====================
# 形式: {stock_name_pattern: {'ticker': 'XXX', 'stock_name': 'Company Name', 'market': 'NYSE'}}
# 銘柄名からticker/stock_name/marketを推論するために使用

STOCK_NAME_TO_TICKER_MAPPING = {
    # Tempur Sealy International → Somnigroup (SGI)
    # 銘柄名の部分一致で判定
    'テンピュール': {'ticker': 'SGI', 'stock_name': 'Somnigroup', 'market': 'NYSE'},
    'TEMPUR': {'ticker': 'SGI', 'stock_name': 'Somnigroup', 'market': 'NYSE'},
    'SOMNIGROUP': {'ticker': 'SGI', 'stock_name': 'Somnigroup', 'market': 'NYSE'},
    
    # 将来的に他の銘柄名が発生した場合、ここに追加
}

# ==================== 日付範囲による適用（オプション） ====================
# 特定の日付範囲でのみマッピングを適用する場合に使用
# 形式: {ticker: {'stock_name': 'Company Name', 'start_date': '2024-01-01', 'end_date': '2024-12-31'}}

TICKER_TO_STOCK_NAME_WITH_DATE_RANGE = {
    # 例: 特定の期間のみ適用する場合
    # 'TPX': {
    #     'stock_name': 'Somnigroup',
    #     'start_date': '2024-01-01',  # この日以降に適用
    #     'end_date': None  # Noneの場合は制限なし
    # },
}

def normalize_ticker(ticker: str) -> str:
    """
    ティッカーを正規化（旧ティッカー→新ティッカーへの変換を含む）
    
    Args:
        ticker: ティッカーシンボル
        
    Returns:
        str: 正規化されたティッカー
    """
    if not ticker or pd.isna(ticker) or ticker == '':
        return ''
    
    ticker = str(ticker).strip().upper()
    
    # 旧ティッカーを新ティッカーに変換
    if ticker in OLD_TO_NEW_TICKER_MAPPING:
        return OLD_TO_NEW_TICKER_MAPPING[ticker]
    
    return ticker


def get_ticker_override(stock_name: str) -> Optional[str]:
    """
    銘柄名からtickerのオーバーライド値を取得
    
    Args:
        stock_name: 銘柄名
        
    Returns:
        str: オーバーライドするticker、該当なしの場合はNone
    """
    if not stock_name or pd.isna(stock_name) or stock_name == '':
        return None
    
    stock_name_upper = str(stock_name).strip().upper()
    
    # 銘柄名のパターンマッチング
    for pattern, mapping in STOCK_NAME_TO_TICKER_MAPPING.items():
        if pattern.upper() in stock_name_upper:
            return mapping['ticker']
    
    return None


def get_market_override(ticker: str) -> Optional[str]:
    """
    ティッカーからmarketのオーバーライド値を取得
    
    Args:
        ticker: ティッカーシンボル
        
    Returns:
        str: オーバーライドするmarket、該当なしの場合はNone
    """
    if not ticker or pd.isna(ticker) or ticker == '':
        return None
    
    ticker = str(ticker).strip().upper()
    normalized_ticker = normalize_ticker(ticker)
    
    if normalized_ticker in TICKER_TO_STOCK_INFO_MAPPING:
        return TICKER_TO_STOCK_INFO_MAPPING[normalized_ticker].get('market')
    
    return None


def get_stock_name_override(ticker: str, settlement_date: Optional[pd.Timestamp] = None) -> Optional[str]:
    """
    ティッカーからstock_nameのオーバーライド値を取得
    
    Args:
        ticker: ティッカーシンボル
        settlement_date: 決済日（日付範囲による適用の場合に使用）
        
    Returns:
        str: オーバーライドするstock_name、該当なしの場合はNone
    """
    if not ticker or pd.isna(ticker) or ticker == '':
        return None
    
    ticker = str(ticker).strip().upper()
    
    # 旧ティッカーを新ティッカーに正規化
    normalized_ticker = normalize_ticker(ticker)
    
    # 1. 日付範囲付きマッピングを確認
    if normalized_ticker in TICKER_TO_STOCK_NAME_WITH_DATE_RANGE:
        mapping = TICKER_TO_STOCK_NAME_WITH_DATE_RANGE[normalized_ticker]
        stock_name = mapping['stock_name']
        
        # 日付範囲のチェック
        if settlement_date is not None:
            start_date = mapping.get('start_date')
            end_date = mapping.get('end_date')
            
            if start_date:
                start_date = pd.to_datetime(start_date)
                if settlement_date < start_date:
                    return None
            
            if end_date:
                end_date = pd.to_datetime(end_date)
                if settlement_date > end_date:
                    return None
        
        return stock_name
    
    # 2. 通常のマッピングを確認
    if normalized_ticker in TICKER_TO_STOCK_NAME_MAPPING:
        return TICKER_TO_STOCK_NAME_MAPPING[normalized_ticker]
    
    return None


def get_ticker_and_stock_name_override(
    ticker: Optional[str], 
    stock_name: Optional[str],
    settlement_date: Optional[pd.Timestamp] = None,
    normalize_stock_name: bool = True
) -> Tuple[Optional[str], Optional[str]]:
    """
    tickerとstock_nameの両方を補完・正規化
    
    Args:
        ticker: ティッカーシンボル（空欄の場合もあり）
        stock_name: 銘柄名（空欄の場合もあり）
        settlement_date: 決済日
        normalize_stock_name: stock_nameも正規化するかどうか（デフォルトTrue）
        
    Returns:
        Tuple[str, str]: (補完後のticker, 補完後のstock_name)
    """
    result_ticker, result_stock_name, _ = get_full_stock_info_override(
        ticker, stock_name, None, settlement_date, normalize_stock_name
    )
    return result_ticker, result_stock_name


def get_full_stock_info_override(
    ticker: Optional[str], 
    stock_name: Optional[str],
    market: Optional[str] = None,
    settlement_date: Optional[pd.Timestamp] = None,
    normalize_stock_name: bool = True
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    ticker、stock_name、marketのすべてを補完・正規化
    
    Args:
        ticker: ティッカーシンボル（空欄の場合もあり）
        stock_name: 銘柄名（空欄の場合もあり）
        market: 市場（空欄の場合もあり）
        settlement_date: 決済日
        normalize_stock_name: stock_nameも正規化するかどうか（デフォルトTrue）
        
    Returns:
        Tuple[str, str, str]: (補完後のticker, 補完後のstock_name, 補完後のmarket)
    """
    result_ticker = ticker if ticker and not pd.isna(ticker) and str(ticker).strip() != '' else None
    result_stock_name = stock_name if stock_name and not pd.isna(stock_name) and str(stock_name).strip() != '' else None
    result_market = market if market and not pd.isna(market) and str(market).strip() != '' else None
    
    # 1. tickerが存在する場合、正規化と社名/market補完
    if result_ticker:
        result_ticker = normalize_ticker(result_ticker)
        # stock_nameも正規化（設定されている場合）
        if normalize_stock_name:
            override_stock_name = get_stock_name_override(result_ticker, settlement_date)
            if override_stock_name:
                result_stock_name = override_stock_name
        elif not result_stock_name:
            result_stock_name = get_stock_name_override(result_ticker, settlement_date)
        
        # marketが空欄の場合、補完
        if not result_market:
            result_market = get_market_override(result_ticker)
    
    # 2. tickerが空欄でstock_nameが存在する場合、tickerを推論
    if not result_ticker and result_stock_name:
        inferred_ticker = get_ticker_override(result_stock_name)
        if inferred_ticker:
            result_ticker = inferred_ticker
            # stock_nameも正規化
            if normalize_stock_name:
                override_stock_name = get_stock_name_override(inferred_ticker, settlement_date)
                if override_stock_name:
                    result_stock_name = override_stock_name
            # marketが空欄の場合、補完
            if not result_market:
                result_market = get_market_override(inferred_ticker)
    
    return result_ticker, result_stock_name, result_market


def apply_stock_name_overrides(df: pd.DataFrame, 
                                ticker_column: str = 'ticker',
                                stock_name_column: str = 'stock_name',
                                market_column: str = 'market',
                                date_column: Optional[str] = 'settlement_date') -> pd.DataFrame:
    """
    データフレームにticker/stock_name/marketオーバーライドを適用
    
    Args:
        df: 対象のデータフレーム
        ticker_column: ティッカー列名
        stock_name_column: stock_name列名
        market_column: market列名
        date_column: 日付列名（日付範囲による適用の場合に使用、Noneの場合は使用しない）
        
    Returns:
        pd.DataFrame: オーバーライド適用後のデータフレーム
    """
    df = df.copy()
    
    if ticker_column not in df.columns or stock_name_column not in df.columns:
        return df
    
    has_market_column = market_column in df.columns
    
    # 処理対象の行を特定（tickerまたはstock_nameが空欄、または旧ティッカー、またはマッピング対象の銘柄名、またはmarket空欄）
    def needs_processing(row):
        ticker = row[ticker_column]
        stock_name = row[stock_name_column]
        market = row[market_column] if has_market_column else None
        
        ticker_empty = pd.isna(ticker) or str(ticker).strip() == '' or str(ticker).strip() == 'None'
        stock_name_empty = pd.isna(stock_name) or str(stock_name).strip() == '' or str(stock_name).strip() == 'None'
        market_empty = has_market_column and (pd.isna(market) or str(market).strip() == '' or str(market).strip() == 'None')
        
        # 旧ティッカーの場合も処理対象
        is_old_ticker = not ticker_empty and str(ticker).strip().upper() in OLD_TO_NEW_TICKER_MAPPING
        
        # マッピング対象の銘柄名の場合も処理対象（stock_nameを正規化するため）
        is_mapping_target_stock_name = False
        if not stock_name_empty:
            stock_name_upper = str(stock_name).strip().upper()
            for pattern in STOCK_NAME_TO_TICKER_MAPPING.keys():
                if pattern.upper() in stock_name_upper:
                    is_mapping_target_stock_name = True
                    break
        
        # マッピング対象のティッカーでmarket空欄の場合も処理対象
        is_ticker_with_market_mapping = False
        if not ticker_empty and market_empty:
            normalized = normalize_ticker(str(ticker).strip().upper())
            if normalized in TICKER_TO_STOCK_INFO_MAPPING:
                is_ticker_with_market_mapping = True
        
        return ticker_empty or stock_name_empty or is_old_ticker or is_mapping_target_stock_name or is_ticker_with_market_mapping
    
    mask = df.apply(needs_processing, axis=1)
    
    if not mask.any():
        return df
    
    # オーバーライドを適用
    ticker_override_count = 0
    stock_name_override_count = 0
    market_override_count = 0
    
    for idx in df[mask].index:
        ticker = df.loc[idx, ticker_column]
        stock_name = df.loc[idx, stock_name_column]
        market = df.loc[idx, market_column] if has_market_column else None
        settlement_date = df.loc[idx, date_column] if date_column and date_column in df.columns else None
        
        # ticker/stock_name/marketの補完・正規化
        new_ticker, new_stock_name, new_market = get_full_stock_info_override(
            ticker, stock_name, market, settlement_date, normalize_stock_name=True
        )
        
        # 更新
        if new_ticker and (pd.isna(ticker) or str(ticker).strip() == '' or str(ticker).strip().upper() != new_ticker):
            df.loc[idx, ticker_column] = new_ticker
            ticker_override_count += 1
        
        if new_stock_name and (
            pd.isna(stock_name) or 
            str(stock_name).strip() == '' or 
            str(stock_name).strip() == 'None' or
            str(stock_name).strip() != new_stock_name  # stock_nameも正規化
        ):
            df.loc[idx, stock_name_column] = new_stock_name
            stock_name_override_count += 1
        
        if has_market_column and new_market and (
            pd.isna(market) or 
            str(market).strip() == '' or 
            str(market).strip() == 'None'
        ):
            df.loc[idx, market_column] = new_market
            market_override_count += 1
    
    if ticker_override_count > 0:
        print(f"[INFO] tickerオーバーライド適用: {ticker_override_count}行")
    if stock_name_override_count > 0:
        print(f"[INFO] stock_nameオーバーライド適用: {stock_name_override_count}行")
    if market_override_count > 0:
        print(f"[INFO] marketオーバーライド適用: {market_override_count}行")
    
    return df

