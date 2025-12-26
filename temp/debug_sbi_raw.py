# %%
import pandas as pd
import os
from glob import glob

# 最新のSBI生データを読み込み
input_folder = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\01_data\trading_account\realized_pl\raw\sbi"
file_pattern = os.path.join(input_folder, "*.csv")
matching_files = glob(file_pattern)

if matching_files:
    input_file = max(matching_files, key=os.path.getctime)
    print(f"最新のSBI生データファイル: {input_file}")
    
    # データ読み込み（9行目から、shift-jis）
    df_sbi = pd.read_csv(input_file, encoding="shift-jis", skiprows=8)
    
    # カラム英訳
    col_rename_map = {
        "建日(国内約定日)": "contract_date",
        "決済日(国内約定日)": "settlement_date", 
        "決済損益": "ttl_gain_realized_usd",
        "ティッカー": "ticker",
        "数量": "num_of_shares",
    }
    
    df_sbi = df_sbi.rename(columns=col_rename_map)
    
    # 数値列の型変換
    df_sbi["ttl_gain_realized_usd"] = pd.to_numeric(df_sbi["ttl_gain_realized_usd"], errors="coerce")
    df_sbi["num_of_shares"] = pd.to_numeric(df_sbi["num_of_shares"], errors="coerce")
    
    # 決済日から年月を作成
    df_sbi["settlement_date"] = pd.to_datetime(df_sbi["settlement_date"], errors="coerce")
    df_sbi["year_month"] = df_sbi["settlement_date"].dt.strftime("%Y-%m")
    
    # 2025年10月のデータをフィルタ
    oct_data = df_sbi[df_sbi["year_month"] == "2025-10"]
    
    print(f"\n2025年10月の取引数: {len(oct_data)}件")
    
    if len(oct_data) > 0:
        print(f"実現損益の合計: {oct_data['ttl_gain_realized_usd'].sum():.2f}ドル")
        print(f"取引数量の合計: {oct_data['num_of_shares'].sum():,}株")
        
        print(f"\n各取引の損益:")
        for i, row in oct_data.iterrows():
            print(f"{row['settlement_date'].strftime('%m/%d')} {row['ticker']:6s} {row['num_of_shares']:>6}株 {row['ttl_gain_realized_usd']:>8.2f}ドル")
            
        print(f"\n銘柄別損益:")
        ticker_summary = oct_data.groupby('ticker')['ttl_gain_realized_usd'].sum().sort_values(ascending=False)
        for ticker, gain in ticker_summary.items():
            print(f"{ticker:6s}: {gain:>8.2f}ドル")
    else:
        print("2025年10月のデータが見つかりません")
        print(f"利用可能な年月: {sorted(df_sbi['year_month'].unique())}")
        
else:
    print("SBI生データファイルが見つかりません")

# %%