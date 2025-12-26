# %%
import pandas as pd

# 10月の取引データ（添付CSVから抽出）
oct_trades = [
    {"date": "2025/10/14", "ticker": "OKLO", "gain": 825.65},
    {"date": "2025/10/14", "ticker": "SOFI", "gain": 3025.53},  # 注目：この取引が大きい
    {"date": "2025/10/09", "ticker": "BWXT", "gain": 632.66},
    {"date": "2025/10/08", "ticker": "AMD", "gain": -7.66},
    {"date": "2025/10/08", "ticker": "AMD", "gain": -2.64},
    {"date": "2025/10/08", "ticker": "SOFI", "gain": 3236.17},  # 注目：この取引も大きい
    {"date": "2025/10/08", "ticker": "SOFI", "gain": 670.00},
    {"date": "2025/10/07", "ticker": "HIMS", "gain": 617.20},
    {"date": "2025/10/07", "ticker": "IOT", "gain": 1167.71},   # 注目：この取引も大きい
    {"date": "2025/10/06", "ticker": "PLTR", "gain": 455.95},
    {"date": "2025/10/03", "ticker": "HMY", "gain": 729.33},
    {"date": "2025/10/03", "ticker": "RBRK", "gain": 36.34},
    {"date": "2025/10/02", "ticker": "SOFI", "gain": 2442.13},  # 注目：この取引も大きい
    {"date": "2025/10/01", "ticker": "SMCI", "gain": 1588.86},  # 注目：この取引も大きい
]

total_gain = sum([trade["gain"] for trade in oct_trades])
print(f"添付データの10月実現損益合計: {total_gain:.2f}ドル")

# 不足分を確認
current_processed = 3956.83
difference = total_gain - current_processed
print(f"現在処理済み: {current_processed:.2f}ドル")
print(f"差分: {difference:.2f}ドル")

# 取引別詳細
print(f"\n各取引の詳細:")
for trade in oct_trades:
    print(f"{trade['date']} {trade['ticker']:6s}: {trade['gain']:>8.2f}ドル")

print(f"\n大きな利益の取引（1000ドル以上）:")
big_trades = [t for t in oct_trades if t["gain"] >= 1000]
for trade in big_trades:
    print(f"{trade['date']} {trade['ticker']:6s}: {trade['gain']:>8.2f}ドル")

print(f"\n大きな利益の合計: {sum([t['gain'] for t in big_trades]):.2f}ドル")

# %%