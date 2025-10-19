# %%
import pandas as pd
import os
from datetime import datetime
from glob import glob

# %%
# --------- 📁 入出力パス設定 --------- #
base_folder = r"C:\Users\alpac\Dropbox\03_individual_work\05_stockTrading\01_data\trading_account\realized_pl\processed"
today_str = datetime.today().strftime("%Y%m%d")
dated_folder = os.path.join(base_folder, f"realizedPl_{today_str}")
os.makedirs(dated_folder, exist_ok=True)  # 既存なら流用、なければ作成

# --------- 📄 最新ファイル取得 --------- #
# Rakuten: 当日フォルダ > 任意の日付フォルダ > ルート直下
rakuten_patterns = [
    os.path.join(dated_folder, "rakuten_monthly_summary_en_*.csv"),
    os.path.join(base_folder, "realizedPl_*", "rakuten_monthly_summary_en_*.csv"),
    os.path.join(base_folder, "rakuten_monthly_summary_en_*.csv"),
]
rakuten_files = []
for p in rakuten_patterns:
    rakuten_files.extend(glob(p))

if not rakuten_files:
    raise FileNotFoundError(f"Rakuten月次ファイルが見つかりません。検索パターン: {' | '.join(rakuten_patterns)}")

rakuten_path = max(rakuten_files, key=os.path.getctime)

# SBI: 為替適用済みファイルを検索
sbi_patterns = [
    os.path.join(dated_folder, "sbi_monthly_summary_with_fx_applied_*.csv"),
    os.path.join(base_folder, "realizedPl_*", "sbi_monthly_summary_with_fx_applied_*.csv"),
    os.path.join(base_folder, "sbi_monthly_summary_with_fx_applied_*.csv"),
]
sbi_files = []
for p in sbi_patterns:
    sbi_files.extend(glob(p))

if not sbi_files:
    raise FileNotFoundError(f"SBI月次（為替適用済）ファイルが見つかりません。検索パターン: {' | '.join(sbi_patterns)}")

sbi_path = max(sbi_files, key=os.path.getctime)

print(f"📄 Rakuten 読込ファイル: {os.path.basename(rakuten_path)}")
print(f"📄 SBI 読込ファイル: {os.path.basename(sbi_path)}")

# --------- 📥 データ読み込み --------- #
df_rakuten = pd.read_csv(rakuten_path, encoding="utf-8-sig")
df_sbi = pd.read_csv(sbi_path, encoding="utf-8-sig")

# --------- 🏷️ 証券会社のフラグ追加 --------- #
df_rakuten["broker"] = "Rakuten"
df_sbi["broker"] = "SBI"

# --------- 🧩 カラムの補完（必要に応じてNaN追加） --------- #
all_cols = set(df_rakuten.columns).union(df_sbi.columns)
for col in all_cols:
    if col not in df_rakuten.columns:
        df_rakuten[col] = None
    if col not in df_sbi.columns:
        df_sbi[col] = None

# --------- 🔗 結合 --------- #
df_merged = pd.concat([df_rakuten, df_sbi], ignore_index=True)

# --------- 💾 保存（処理日付フォルダへ格納） --------- #
output_path = os.path.join(dated_folder, f"merged_trading_summary_{today_str}.csv")
df_merged.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"✅ 統合データ保存完了: {output_path}")
print(f"📊 統合行数: {len(df_merged)} 行")

# %%
