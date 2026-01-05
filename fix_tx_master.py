"""取引マスターデータを生CSVから完全に再構築（重複処理スクリプトを無効化）"""
import pandas as pd
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("取引マスターデータ完全再構築")
print("=" * 60)

# 生CSVを読み込み
header_names = ['約定日', '受渡日', 'ティッカーコード', '銘柄名', '口座', '取引区分', '取引種別', 
                '信用区分', '決済期限', '決済通貨', '約定数量', '約定単価', '約定金額', 
                '為替レート', '手数料USD', '税USD', '受渡金額USD', '受渡金額円']

df = pd.read_csv('data/trading_account/transaction/raw/rakuten/tradehistory(US)__20210715_20251229.csv', 
                 encoding='cp932', skiprows=1, names=header_names, header=None)

print(f"生CSV行数: {len(df)}")

# 列名を英語化
rename_map = {
    '約定日': 'trade_date', '受渡日': 'settlement_date', 'ティッカーコード': 'ticker',
    '銘柄名': 'stock_name', '口座': 'account_type', '取引区分': 'transaction_category',
    '取引種別': 'trade_type', '信用区分': 'credit_type', '決済期限': 'settlement_deadline',
    '決済通貨': 'currency', '約定数量': 'quantity', '約定単価': 'price_usd',
    '約定金額': 'amount_usd', '為替レート': 'fx_rate', '手数料USD': 'fees_usd',
    '税USD': 'tax_usd', '受渡金額USD': 'net_amount_usd', '受渡金額円': 'net_amount_jpy'
}
df = df.rename(columns=rename_map)

# 数値変換
for col in ['quantity', 'price_usd', 'amount_usd', 'fx_rate', 'fees_usd', 'tax_usd', 'net_amount_usd', 'net_amount_jpy']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace(',', '').str.replace('-', '').replace('', '0')
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# 日付変換
df['trade_date'] = pd.to_datetime(df['trade_date'], errors='coerce')
df['settlement_date'] = pd.to_datetime(df['settlement_date'], errors='coerce')
df['year_month'] = df['settlement_date'].dt.strftime('%Y-%m')

# マスターファイルを上書き保存
master_path = Path('data/trading_account/transaction/raw/rakuten/master/master_transaction_rakuten.parquet')
df.to_parquet(master_path, index=False)
print(f"マスターデータ保存完了: {len(df)}行")

# 処理済みフォルダを削除
processed_dir = Path('data/trading_account/transaction/processed')
for folder in processed_dir.glob('transaction_*'):
    if folder.is_dir():
        import shutil
        shutil.rmtree(folder)
        print(f"削除: {folder.name}")

# 検証
print("\n=== 検証 ===")
# SOFIの確認
sofi = df[(df['ticker'] == 'SOFI') & (df['trade_type'].isin(['買建', '売埋']))]
buy = sofi[sofi['trade_type'] == '買建']['quantity'].sum()
sell = sofi[sofi['trade_type'] == '売埋']['quantity'].sum()
print(f"SOFI: 買建{buy:,.0f} - 売埋{sell:,.0f} = {buy-sell:,.0f}")

