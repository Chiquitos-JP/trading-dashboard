# -*- coding: utf-8 -*-
"""
共通ユーティリティ関数
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
import warnings


def normalize_dataframe_schema(df: pd.DataFrame, 
                               date_columns: Optional[list] = None,
                               string_columns: Optional[list] = None) -> pd.DataFrame:
    """
    データフレームのスキーマを正規化（データ型の統一、エンコーディング処理）
    
    Args:
        df: 正規化するデータフレーム
        date_columns: 日付列のリスト（datetime64[ns]に統一）
        string_columns: 文字列列のリスト（object型に統一、UTF-8エンコーディング）
        
    Returns:
        pd.DataFrame: 正規化されたデータフレーム
    """
    df = df.copy()
    date_columns = date_columns or []
    string_columns = string_columns or []
    
    # 日付列をdatetime64[ns]に統一
    for col in date_columns:
        if col in df.columns:
            if df[col].dtype != 'datetime64[ns]':
                df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # 文字列列をobject型に統一（UTF-8エンコーディング）
    for col in string_columns:
        if col in df.columns:
            if df[col].dtype != 'object':
                df[col] = df[col].astype(str)
            # 文字列列のnull値を空文字列に統一（NaNはNoneに変換してから空文字列に）
            df[col] = df[col].fillna('')
            # 文字列のエンコーディングを確認（必要に応じてUTF-8に変換）
            try:
                # 既にUTF-8として扱える文字列はそのまま
                df[col] = df[col].astype(str)
            except Exception as e:
                warnings.warn(f"列 '{col}' のエンコーディング変換で警告: {e}")
    
    # float型のNaNを明示的にNoneに変換（Parquet保存時の一貫性のため）
    for col in df.select_dtypes(include=[np.number]).columns:
        df[col] = df[col].replace([np.inf, -np.inf], np.nan)
    
    return df


def _get_ticker_to_stock_name_mapping_from_transaction(paths, broker: str) -> dict:
    """
    トランザクションデータからticker→stock_nameのマッピングを取得
    
    Args:
        paths: DataPathsインスタンス
        broker: 証券会社名（"rakuten", "sbi"）
        
    Returns:
        dict: ticker→stock_nameのマッピング
    """
    try:
        transaction_master_path = paths.raw_trading_account_master(broker, "transaction")
        transaction_master_file = transaction_master_path / f"master_transaction_{broker}.parquet"
        
        if not transaction_master_file.exists():
            return {}
        
        df_transaction = pd.read_parquet(transaction_master_file)
        
        # 列名を文字列に変換
        df_transaction.columns = [str(col) for col in df_transaction.columns]
        
        # 列名のマッピング（日本語→英語）
        col_mapping = {
            "ティッカーコード": "ticker",
            "ティッカー": "ticker",
            "銘柄名": "stock_name",
            "銘柄": "stock_name",
        }
        rename_dict = {}
        for jp_col, en_col in col_mapping.items():
            for col in df_transaction.columns:
                if jp_col in col:
                    rename_dict[col] = en_col
                    break
        if rename_dict:
            df_transaction = df_transaction.rename(columns=rename_dict)
        
        # ticker/stock_name列が存在しない場合
        if 'ticker' not in df_transaction.columns or 'stock_name' not in df_transaction.columns:
            return {}
        
        # 有効なstock_nameを持つ行からマッピングを作成
        valid_mask = (
            df_transaction['ticker'].notna() & 
            (df_transaction['ticker'].astype(str).str.strip() != '') &
            df_transaction['stock_name'].notna() & 
            (df_transaction['stock_name'].astype(str).str.strip() != '') &
            (df_transaction['stock_name'].astype(str).str.strip() != 'None')
        )
        
        mapping = df_transaction[valid_mask].groupby('ticker')['stock_name'].first().to_dict()
        return mapping
        
    except Exception as e:
        warnings.warn(f"トランザクションマッピング取得エラー: {e}")
        return {}


def complete_stock_name_from_transaction_inference(
    df_realized_pl: pd.DataFrame,
    paths,
    broker: str,
    ticker_column: str = 'ticker',
    stock_name_column: str = 'stock_name',
    settlement_date_column: str = 'settlement_date',
    num_of_shares_column: str = 'num_of_shares',
    price_column: str = 'avg_UnitPrice_settlement_usd',
    tolerance_days: int = 7,
    price_tolerance: float = 0.01
) -> pd.DataFrame:
    """
    トランザクションデータからtickerとstock_nameを推論して補完
    
    Args:
        df_realized_pl: realized_plデータフレーム
        paths: DataPathsインスタンス
        broker: 証券会社名（"rakuten", "sbi"）
        ticker_column: ティッカー列名
        stock_name_column: stock_name列名
        settlement_date_column: 決済日列名
        num_of_shares_column: 数量列名
        price_column: 価格列名
        tolerance_days: 決済日の許容誤差（日数）
        price_tolerance: 価格の許容誤差（比率）
        
    Returns:
        pd.DataFrame: 補完後のデータフレーム
    """
    df = df_realized_pl.copy()
    
    # tickerとstock_nameが両方空欄の行を特定
    missing_mask = (
        (df[ticker_column].isna() | (df[ticker_column].astype(str).str.strip() == '')) &
        (df[stock_name_column].isna() | (df[stock_name_column].astype(str).str.strip() == ''))
    )
    
    if not missing_mask.any():
        return df
    
    print(f"[INFO] トランザクションデータからの推論補完を試行: {missing_mask.sum()}行")
    
    # トランザクションマスターデータを読み込み
    try:
        transaction_master_path = paths.raw_trading_account_master(broker, "transaction")
        transaction_master_file = transaction_master_path / f"master_transaction_{broker}.parquet"
        
        if not transaction_master_file.exists():
            print(f"[WARNING] トランザクションマスターデータが見つかりません: {transaction_master_file}")
            return df
        
        df_transaction = pd.read_parquet(transaction_master_file)
        print(f"[INFO] トランザクションデータ読み込み: {len(df_transaction)}行")
        
        # 列名の正規化（日本語列名を英語に変換）
        # 列名を文字列に変換
        df_transaction.columns = [str(col) for col in df_transaction.columns]
        
        # 列名のマッピング（部分一致も含む）
        col_mapping = {
            "ティッカーコード": "ticker",
            "ティッカー": "ticker",
            "銘柄名": "stock_name",
            "決済日": "settlement_date",
            "約定数量": "quantity",
            "数量": "quantity",
            "約定単価": "price_usd",
            "価格": "price_usd"
        }
        
        # マッピングを適用（完全一致）
        rename_dict = {}
        for jp_col, en_col in col_mapping.items():
            if jp_col in df_transaction.columns and en_col not in df_transaction.columns:
                rename_dict[jp_col] = en_col
        
        # 部分一致でマッピング（完全一致で見つからなかった場合）
        for jp_col, en_col in col_mapping.items():
            if en_col not in df_transaction.columns and en_col not in rename_dict.values():
                for col in df_transaction.columns:
                    if jp_col in col and col not in rename_dict:
                        rename_dict[col] = en_col
                        break
        
        if rename_dict:
            df_transaction = df_transaction.rename(columns=rename_dict)
            print(f"[INFO] トランザクションデータの列名を正規化: {len(rename_dict)}列 ({list(rename_dict.items())})")
        
        # 必要な列が存在するか確認（tickerはオプション、stock_nameがあれば可）
        required_cols = ['stock_name', 'settlement_date', 'quantity', 'price_usd']
        missing_cols = [col for col in required_cols if col not in df_transaction.columns]
        if missing_cols:
            print(f"[WARNING] トランザクションデータに必要な列が不足: {missing_cols}")
            print(f"  利用可能な列: {list(df_transaction.columns)[:15]}")
            return df
        
        # ticker列の有無を確認
        has_ticker = 'ticker' in df_transaction.columns
        if not has_ticker:
            print(f"[INFO] トランザクションデータにticker列がありません。stock_nameのみで補完します。")
        
        # 日付列をdatetimeに変換
        if df_transaction['settlement_date'].dtype != 'datetime64[ns]':
            df_transaction['settlement_date'] = pd.to_datetime(df_transaction['settlement_date'], errors='coerce')
        if df[settlement_date_column].dtype != 'datetime64[ns]':
            df[settlement_date_column] = pd.to_datetime(df[settlement_date_column], errors='coerce')
        
        # 推論補完を実行
        inferred_count = 0
        for idx in df[missing_mask].index:
            row = df.loc[idx]
            settlement_date = row[settlement_date_column]
            num_of_shares = row[num_of_shares_column] if num_of_shares_column in df.columns else None
            price = row[price_column] if price_column in df.columns else None
            
            if pd.isna(settlement_date):
                continue
            
            # トランザクションデータから一致する取引を検索
            # 1. 決済日が近い（±tolerance_days以内）
            date_range = pd.Timedelta(days=tolerance_days)
            transaction_candidates = df_transaction[
                (df_transaction['settlement_date'] >= settlement_date - date_range) &
                (df_transaction['settlement_date'] <= settlement_date + date_range) &
                df_transaction['settlement_date'].notna()
            ].copy()
            
            if len(transaction_candidates) == 0:
                continue
            
            # 2. 数量が一致（または近い）
            if pd.notna(num_of_shares):
                # 数量のマッチング（完全一致または±10%以内）
                transaction_candidates = transaction_candidates[
                    (transaction_candidates['quantity'] == num_of_shares) |
                    (abs(transaction_candidates['quantity'] - num_of_shares) / max(abs(num_of_shares), 1) <= 0.1)
                ]
            
            if len(transaction_candidates) == 0:
                continue
            
            # 3. 価格が近い（±price_tolerance以内）
            if pd.notna(price) and price > 0:
                transaction_candidates = transaction_candidates[
                    transaction_candidates['price_usd'].notna() &
                    (abs(transaction_candidates['price_usd'] - price) / price <= price_tolerance)
                ]
            
            if len(transaction_candidates) == 0:
                continue
            
            # 最も一致度が高い取引を選択（決済日が最も近い）
            date_diff = (transaction_candidates['settlement_date'] - settlement_date).abs()
            best_match_idx = date_diff.idxmin()
            best_match = transaction_candidates.loc[best_match_idx]
            
            # tickerとstock_nameを補完（tickerが空欄でもstock_nameがあれば使用）
            stock_name_val = ''
            if pd.notna(best_match['stock_name']):
                stock_name_val = str(best_match['stock_name']).strip()
            
            ticker_val = ''
            if has_ticker and pd.notna(best_match.get('ticker')):
                ticker_val = str(best_match['ticker']).strip()
            
            # stock_nameがあれば補完（tickerが空欄でも可）
            if stock_name_val != '' and stock_name_val != 'nan' and stock_name_val != 'None':
                # stock_name_overridesのマッピングを使ってticker/stock_nameを正規化
                try:
                    from config.py.stock_name_overrides import get_ticker_and_stock_name_override
                    override_ticker, override_stock_name = get_ticker_and_stock_name_override(
                        ticker_val if ticker_val and ticker_val != 'nan' and ticker_val != 'None' else None,
                        stock_name_val,
                        settlement_date
                    )
                    if override_ticker:
                        ticker_val = override_ticker
                    if override_stock_name:
                        stock_name_val = override_stock_name
                except ImportError:
                    pass
                
                # 補完を適用
                if ticker_val and ticker_val != '' and ticker_val != 'nan' and ticker_val != 'None':
                    df.loc[idx, ticker_column] = ticker_val
                df.loc[idx, stock_name_column] = stock_name_val
                inferred_count += 1
        
        if inferred_count > 0:
            print(f"[INFO] トランザクションデータからの推論補完: {inferred_count}行を補完しました")
        else:
            remaining_missing = missing_mask.sum()
            print(f"[INFO] トランザクションデータからの推論補完: 一致する取引が見つかりませんでした（残り{remaining_missing}行）")
            
    except Exception as e:
        print(f"[WARNING] トランザクションデータからの推論補完でエラー: {e}")
        import traceback
        traceback.print_exc()
    
    return df


def complete_stock_name_from_ticker(df: pd.DataFrame,
                                     ticker_column: str = 'ticker',
                                     stock_name_column: str = 'stock_name',
                                     date_column: Optional[str] = 'settlement_date',
                                     apply_overrides: bool = True,
                                     use_transaction_inference: bool = False,
                                     paths = None,
                                     broker: Optional[str] = None) -> pd.DataFrame:
    """
    stock_nameをtickerから補完（オーバーライドマッピング + 既存データからの補完 + トランザクションデータからの推論）
    
    Args:
        df: 対象のデータフレーム
        ticker_column: ティッカー列名
        stock_name_column: stock_name列名
        date_column: 日付列名
        apply_overrides: オーバーライドマッピングを適用するか
        use_transaction_inference: トランザクションデータからの推論を使用するか
        paths: DataPathsインスタンス（use_transaction_inference=Trueの場合に必要）
        broker: 証券会社名（use_transaction_inference=Trueの場合に必要）
        
    Returns:
        pd.DataFrame: 補完後のデータフレーム
    """
    df = df.copy()
    
    if ticker_column not in df.columns or stock_name_column not in df.columns:
        return df
    
    # 1. オーバーライドマッピングを適用（ticker/stock_name/market補完）
    if apply_overrides:
        try:
            from stock_name_overrides import apply_stock_name_overrides
            df = apply_stock_name_overrides(
                df,
                ticker_column=ticker_column,
                stock_name_column=stock_name_column,
                market_column='market',  # market列も補完
                date_column=date_column
            )
        except ImportError:
            warnings.warn("stock_name_overridesモジュールのインポートに失敗しました。オーバーライドをスキップします。")
    
    # 2. 既存データからの補完（tickerが存在する場合）
    mask = (
        (df[stock_name_column].isna()) | 
        (df[stock_name_column].astype(str).str.strip() == '') |
        (df[stock_name_column].astype(str).str.strip() == 'None')
    ) & df[ticker_column].notna()
    
    if mask.any():
        # tickerとstock_nameのマッピングを作成（有効なstock_nameから）
        ticker_to_name = df[
            df[stock_name_column].notna() & 
            (df[stock_name_column].astype(str).str.strip() != '') & 
            (df[stock_name_column].astype(str).str.strip() != 'None')
        ].groupby(ticker_column)[stock_name_column].first()
        
        # 補完
        df.loc[mask, stock_name_column] = df.loc[mask, ticker_column].map(ticker_to_name)
        remaining_missing = mask.sum() - (df.loc[mask, stock_name_column].notna().sum())
        if remaining_missing < mask.sum():
            print(f"   stock_name補完（同一データ内）: {mask.sum() - remaining_missing}行を補完しました")
    
    # 2.5. トランザクションデータからのticker→stock_nameマッピング補完
    if use_transaction_inference and paths is not None and broker is not None:
        # 残りの空欄行を再確認
        mask_still_missing = (
            (df[stock_name_column].isna()) | 
            (df[stock_name_column].astype(str).str.strip() == '') |
            (df[stock_name_column].astype(str).str.strip() == 'None')
        ) & df[ticker_column].notna()
        
        if mask_still_missing.any():
            # トランザクションデータからticker→stock_nameマッピングを取得
            transaction_mapping = _get_ticker_to_stock_name_mapping_from_transaction(paths, broker)
            if transaction_mapping:
                df.loc[mask_still_missing, stock_name_column] = df.loc[mask_still_missing, ticker_column].map(transaction_mapping)
                completed = mask_still_missing.sum() - (df.loc[mask_still_missing, stock_name_column].isna() | (df.loc[mask_still_missing, stock_name_column].astype(str).str.strip() == '')).sum()
                if completed > 0:
                    print(f"   stock_name補完（取引履歴から）: {completed}行を補完しました")
    
    # 3. トランザクションデータからの推論（tickerとstock_nameが両方空欄の場合）
    if use_transaction_inference and paths is not None and broker is not None:
        df = complete_stock_name_from_transaction_inference(
            df,
            paths=paths,
            broker=broker,
            ticker_column=ticker_column,
            stock_name_column=stock_name_column,
            settlement_date_column=date_column or 'settlement_date'
        )
    
    return df


def save_dataframe(df: pd.DataFrame, parquet_path: str, csv_path: Optional[str] = None, 
                   save_csv: bool = False, encoding: str = 'utf-8-sig',
                   normalize_schema: bool = True,
                   date_columns: Optional[list] = None,
                   string_columns: Optional[list] = None) -> None:
    """
    データフレームをParquet形式で保存（必要に応じてCSVも保存）
    スキーマの正規化も実行
    
    Args:
        df: 保存するデータフレーム
        parquet_path: Parquetファイルのパス
        csv_path: CSVファイルのパス（Noneの場合はparquet_pathから自動生成）
        save_csv: CSVも保存するかどうか（デフォルト: False）
        encoding: CSV保存時のエンコーディング（デフォルト: 'utf-8-sig')
        normalize_schema: スキーマを正規化するかどうか（デフォルト: True）
        date_columns: 日付列のリスト（normalize_schema=Trueの場合）
        string_columns: 文字列列のリスト（normalize_schema=Trueの場合）
    """
    # スキーマの正規化
    if normalize_schema:
        df = normalize_dataframe_schema(df, date_columns=date_columns, string_columns=string_columns)
    
    # Parquet形式で保存（常に実行）
    # パスを正規化（絶対パスに変換）
    import os
    import tempfile
    import shutil
    
    parquet_path_obj = Path(parquet_path).resolve()
    
    # 親ディレクトリを作成
    try:
        parquet_path_obj.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"    [WARNING] ディレクトリ作成エラー: {e}")
        # 相対パスで再試行
        parquet_path_obj = Path(parquet_path)
        parquet_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    # データフレームに無効なデータ型がないか確認
    # object型の列にNaNが含まれている場合、Noneに変換
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].isna().any():
            df[col] = df[col].where(df[col].notna(), None)
    
    try:
        # パスを文字列に変換（os.path.normpathで正規化）
        parquet_path_str = os.path.normpath(str(parquet_path_obj))
        
        # 既存ファイルがある場合は削除（Windowsのファイルロック問題を回避）
        if parquet_path_obj.exists():
            try:
                parquet_path_obj.unlink()
            except Exception:
                pass  # 削除に失敗しても続行
        
        # Parquet保存時にエラーが発生しないよう、データ型を確認
        df.to_parquet(parquet_path_str, index=False, engine='pyarrow', compression='snappy')
        print(f"    [SUCCESS] Parquet保存完了: {Path(parquet_path).name} ({len(df)}行, {len(df.columns)}列)")
    except Exception as e:
        # エラーが発生した場合、詳細を出力して再試行
        print(f"    [WARNING] Parquet保存エラー: {e}")
        print(f"    データ型を確認して再試行します...")
        # データ型を確認
        print(f"    データ型情報:")
        for col in df.columns:
            print(f"      {col}: {df[col].dtype}")
        raise
    
    # CSV形式で保存（必要時のみ）
    if save_csv:
        if csv_path is None:
            csv_path = str(Path(parquet_path).with_suffix('.csv'))
        df.to_csv(csv_path, index=False, encoding=encoding)
        print(f"    [INFO] CSVも保存: {csv_path}")


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


def cleanup_backup_files(backup_dir: Path, 
                         prefix: str = "master_realized_pl",
                         keep_latest_n: int = 10,
                         keep_daily_only: bool = True) -> int:
    """
    バックアップファイルをクリーンアップ
    
    Args:
        backup_dir: バックアップファイルが保存されているディレクトリ
        prefix: バックアップファイル名のプレフィックス（例: "master_realized_pl_rakuten_backup"）
        keep_latest_n: 最新N件を保持（keep_daily_only=Falseの場合）
        keep_daily_only: Trueの場合、同一日の最新バックアップのみ保持
        
    Returns:
        int: 削除されたファイル数
    """
    if not backup_dir.exists():
        return 0
    
    # バックアップファイルを検索
    backup_pattern = f"{prefix}_backup_*.parquet"
    backup_files = sorted(backup_dir.glob(backup_pattern), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if len(backup_files) == 0:
        return 0
    
    deleted_count = 0
    
    if keep_daily_only:
        # 日次バックアップのみ保持（同一日の最新のみ）
        from datetime import datetime
        from collections import defaultdict
        
        # 日付ごとにグループ化
        daily_backups = defaultdict(list)
        for backup_file in backup_files:
            # ファイル名から日付を抽出（例: master_realized_pl_rakuten_backup_20260104_162422.parquet）
            try:
                # ファイル名のパターン: prefix_backup_YYYYMMDD_HHMMSS.parquet
                name_parts = backup_file.stem.split('_backup_')
                if len(name_parts) == 2:
                    date_time = name_parts[1]
                    date_str = date_time.split('_')[0]  # YYYYMMDD部分
                    daily_backups[date_str].append(backup_file)
            except Exception:
                # パターンが一致しない場合はスキップ
                continue
        
        # 各日の最新バックアップ以外を削除
        for date_str, files in daily_backups.items():
            if len(files) > 1:
                # 最新（最も新しい）を保持、他を削除
                files_sorted = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
                for old_backup in files_sorted[1:]:
                    try:
                        old_backup.unlink()
                        deleted_count += 1
                        print(f"  [CLEANUP] 削除: {old_backup.name}")
                    except Exception as e:
                        print(f"  [WARNING] 削除失敗: {old_backup.name} ({e})")
    else:
        # 最新N件のみ保持
        if len(backup_files) > keep_latest_n:
            for old_backup in backup_files[keep_latest_n:]:
                try:
                    old_backup.unlink()
                    deleted_count += 1
                    print(f"  [CLEANUP] 削除: {old_backup.name}")
                except Exception as e:
                    print(f"  [WARNING] 削除失敗: {old_backup.name} ({e})")
    
    if deleted_count > 0:
        print(f"[INFO] バックアップクリーンアップ完了: {deleted_count}件削除")
    
    return deleted_count


def complete_market_from_yfinance(
    df: pd.DataFrame,
    ticker_column: str = 'ticker',
    market_column: str = 'market',
    broker_column: str = 'broker',
    broker_name: str = 'Rakuten',
    cache: Optional[Dict[str, str]] = None,
    use_cache: bool = True
) -> pd.DataFrame:
    """
    yfinanceを使用してmarketとbrokerを補完
    
    Args:
        df: 補完対象のデータフレーム
        ticker_column: ticker列名
        market_column: market列名
        broker_column: broker列名
        broker_name: brokerに設定する値（デフォルト: 'Rakuten'）
        cache: キャッシュ辞書（ticker -> market）
        use_cache: キャッシュを使用するか
        
    Returns:
        pd.DataFrame: 補完されたデータフレーム
    """
    try:
        import yfinance as yf
    except ImportError:
        print("[WARNING] yfinanceがインストールされていません。pip install yfinance を実行してください。")
        return df
    
    if cache is None:
        cache = {}
    
    df = df.copy()
    
    # broker列が存在しない場合は作成
    if broker_column not in df.columns:
        df[broker_column] = ''
    
    # market列が存在しない場合は作成
    if market_column not in df.columns:
        df[market_column] = ''
    
    # 補完が必要な行を特定
    missing_market_mask = (df[market_column].isna() | (df[market_column] == '')) & \
                          df[ticker_column].notna() & (df[ticker_column] != '')
    missing_broker_mask = (df[broker_column].isna() | (df[broker_column] == '')) & \
                          df[ticker_column].notna() & (df[ticker_column] != '')
    
    if not missing_market_mask.any() and not missing_broker_mask.any():
        return df
    
    # ユニークなtickerを取得
    unique_tickers = df.loc[missing_market_mask | missing_broker_mask, ticker_column].unique()
    
    print(f"[INFO] yfinanceから市場情報を取得中: {len(unique_tickers)}種類のticker")
    
    # 手動マッピングを確認（stock_name_overridesから）
    try:
        from config.py.stock_name_overrides import TICKER_TO_STOCK_INFO_MAPPING
        manual_mapping = TICKER_TO_STOCK_INFO_MAPPING
    except ImportError:
        manual_mapping = {}
    
    # 各tickerから市場情報を取得
    ticker_to_market = {}
    for i, ticker in enumerate(unique_tickers):
        ticker_str = str(ticker).strip().upper()
        
        # キャッシュを確認
        if use_cache and ticker_str in cache:
            ticker_to_market[ticker_str] = cache[ticker_str]
            continue
        
        # 手動マッピングを優先的に確認
        if ticker_str in manual_mapping:
            market_from_manual = manual_mapping[ticker_str].get('market', '')
            if market_from_manual:
                ticker_to_market[ticker_str] = market_from_manual
                cache[ticker_str] = market_from_manual  # キャッシュに保存
                continue
        
        try:
            # yfinanceから情報を取得
            stock = yf.Ticker(ticker_str)
            info = stock.info
            
            # exchange情報から市場を判定
            exchange = info.get('exchange', '').upper()
            market = ''
            
            if 'NASDAQ' in exchange or 'NMS' in exchange:
                market = 'NASDAQ'
            elif 'NYSE' in exchange or 'NYQ' in exchange:
                market = 'NYSE'
            elif 'AMEX' in exchange or 'ASE' in exchange:
                market = 'AMEX'
            elif 'OTC' in exchange:
                market = 'OTC'
            elif 'TSX' in exchange:
                market = 'TSX'
            elif 'LSE' in exchange:
                market = 'LSE'
            else:
                # exchangeが取得できたが、判定できない場合はそのまま使用
                market = exchange if exchange else ''
            
            ticker_to_market[ticker_str] = market
            cache[ticker_str] = market  # キャッシュに保存
            
            if (i + 1) % 10 == 0:
                print(f"  進捗: {i + 1}/{len(unique_tickers)} ticker処理完了")
            
            # APIレート制限を考慮して少し待機
            import time
            time.sleep(0.1)
            
        except Exception as e:
            print(f"  [WARNING] {ticker_str}の市場情報取得失敗: {e}")
            ticker_to_market[ticker_str] = ''
            cache[ticker_str] = ''  # エラーもキャッシュに保存（再試行を避ける）
    
    # market列を補完
    if missing_market_mask.any():
        market_completed = 0
        for idx in df.index[missing_market_mask]:
            ticker_str = str(df.loc[idx, ticker_column]).strip().upper()
            if ticker_str in ticker_to_market and ticker_to_market[ticker_str]:
                df.loc[idx, market_column] = ticker_to_market[ticker_str]
                market_completed += 1
        
        print(f"[INFO] market補完完了: {market_completed}行")
    
    # broker列を補完
    if missing_broker_mask.any():
        broker_completed = missing_broker_mask.sum()
        df.loc[missing_broker_mask, broker_column] = broker_name
        print(f"[INFO] broker補完完了: {broker_completed}行")
    
    return df


def complete_contract_date_from_settlement(
    df: pd.DataFrame,
    settlement_date_column: str = 'settlement_date',
    contract_date_column: str = 'contract_date',
    transaction_type_column: str = 'transaction_type',
    market_column: str = 'market',
    default_days: int = 2
) -> pd.DataFrame:
    """
    settlement_dateからcontract_dateを補完
    
    既存データからsettlement_dateとcontract_dateの関係性を分析し、
    取引タイプや市場に応じた日数差を使用してcontract_dateを補完します。
    
    Args:
        df: 補完対象のデータフレーム
        settlement_date_column: settlement_date列名
        contract_date_column: contract_date列名
        transaction_type_column: transaction_type列名
        market_column: market列名
        default_days: デフォルトの日数差（settlement_dateから何日前がcontract_dateか）
        
    Returns:
        pd.DataFrame: 補完されたデータフレーム
    """
    df = df.copy()
    
    # 日付列をdatetime型に変換
    if settlement_date_column in df.columns:
        df[settlement_date_column] = pd.to_datetime(df[settlement_date_column], errors='coerce')
    if contract_date_column in df.columns:
        df[contract_date_column] = pd.to_datetime(df[contract_date_column], errors='coerce')
    
    # 補完が必要な行を特定
    missing_contract_mask = (df[contract_date_column].isna() | (df[contract_date_column] == '')) & \
                           df[settlement_date_column].notna()
    
    if not missing_contract_mask.any():
        return df
    
    # 既存データから日数差のパターンを分析
    both_exist = df[df[contract_date_column].notna() & 
                    df[settlement_date_column].notna()].copy()
    
    # 日数差を計算
    if len(both_exist) > 0:
        both_exist['_days_diff'] = (both_exist[settlement_date_column] - 
                                    both_exist[contract_date_column]).dt.days
        
        # 取引タイプと市場の組み合わせで最頻値を計算
        days_diff_map = {}
        
        if transaction_type_column in both_exist.columns and market_column in both_exist.columns:
            # 取引タイプ + 市場の組み合わせ
            for trans_type in both_exist[transaction_type_column].dropna().unique():
                for market in both_exist[market_column].dropna().unique():
                    if market and market != '':
                        subset = both_exist[
                            (both_exist[transaction_type_column] == trans_type) &
                            (both_exist[market_column] == market)
                        ]
                        if len(subset) > 0:
                            mode_value = subset['_days_diff'].mode()
                            if len(mode_value) > 0:
                                key = (str(trans_type), str(market))
                                days_diff_map[key] = int(mode_value.iloc[0])
            
            # 取引タイプのみ
            for trans_type in both_exist[transaction_type_column].dropna().unique():
                subset = both_exist[both_exist[transaction_type_column] == trans_type]
                if len(subset) > 0:
                    mode_value = subset['_days_diff'].mode()
                    if len(mode_value) > 0:
                        key = (str(trans_type), None)
                        days_diff_map[key] = int(mode_value.iloc[0])
            
            # 市場のみ
            for market in both_exist[market_column].dropna().unique():
                if market and market != '':
                    subset = both_exist[both_exist[market_column] == market]
                    if len(subset) > 0:
                        mode_value = subset['_days_diff'].mode()
                        if len(mode_value) > 0:
                            key = (None, str(market))
                            days_diff_map[key] = int(mode_value.iloc[0])
        
        # 全体の最頻値
        if len(both_exist) > 0:
            overall_mode = both_exist['_days_diff'].mode()
            if len(overall_mode) > 0:
                days_diff_map[(None, None)] = int(overall_mode.iloc[0])
        
        # 補完実行
        completed_count = 0
        for idx in df.index[missing_contract_mask]:
            settlement_date = df.loc[idx, settlement_date_column]
            if pd.notna(settlement_date):
                # 最適な日数差を決定
                days_diff = default_days
                
                trans_type = str(df.loc[idx, transaction_type_column]) if transaction_type_column in df.columns else None
                market = str(df.loc[idx, market_column]) if market_column in df.columns else None
                
                # 優先順位: (取引タイプ, 市場) > (取引タイプ, None) > (None, 市場) > (None, None) > デフォルト
                if (trans_type, market) in days_diff_map:
                    days_diff = days_diff_map[(trans_type, market)]
                elif (trans_type, None) in days_diff_map:
                    days_diff = days_diff_map[(trans_type, None)]
                elif (None, market) in days_diff_map:
                    days_diff = days_diff_map[(None, market)]
                elif (None, None) in days_diff_map:
                    days_diff = days_diff_map[(None, None)]
                
                # contract_dateを計算（settlement_dateから日数差を引く）
                contract_date = settlement_date - pd.Timedelta(days=days_diff)
                df.loc[idx, contract_date_column] = contract_date
                completed_count += 1
        
        print(f"[INFO] contract_date補完完了: {completed_count}行（settlement_dateから逆算）")
    else:
        # 既存データがない場合はデフォルト値を使用
        completed_count = 0
        for idx in df.index[missing_contract_mask]:
            settlement_date = df.loc[idx, settlement_date_column]
            if pd.notna(settlement_date):
                contract_date = settlement_date - pd.Timedelta(days=default_days)
                df.loc[idx, contract_date_column] = contract_date
                completed_count += 1
        
        print(f"[INFO] contract_date補完完了: {completed_count}行（デフォルト{default_days}日差）")
    
    return df
