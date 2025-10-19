"""
取引データ分析パイプライン - 一括実行スクリプト

実行順序:
1. realizedPl_rakuten_00.py  - 楽天証券データ処理
2. realizedPl_sbi_00.py      - SBI証券データ処理
3. realizedPl_sbi_01.py      - SBI為替変換
4. mergedPl.py               - データ統合
5. kpi_analysis.py           - KPI分析
6. kpi_visualization.py      - グラフ作成
7. kpi_calc_ytd_monthly_simple.py - YTD/月次KPI計算

使い方:
    python run_all.py
"""

import subprocess
import sys
from pathlib import Path

# スクリプトのディレクトリを取得
SCRIPT_DIR = Path(__file__).parent

# 実行するスクリプトのリスト（順序重要）
SCRIPTS = [
    ("楽天証券データ処理", "realizedPl_rakuten_00.py"),
    ("SBI証券データ処理", "realizedPl_sbi_00.py"),
    ("SBI為替変換", "realizedPl_sbi_01.py"),
    ("データ統合", "mergedPl.py"),
    ("KPI分析", "kpi_analysis.py"),
    ("グラフ作成", "kpi_visualization.py"),
    ("YTD/月次KPI計算", "kpi_calc_ytd_monthly_simple.py"),
]

def run_script(name: str, script_path: Path) -> bool:
    """
    Pythonスクリプトを実行
    
    Args:
        name: スクリプトの説明
        script_path: スクリプトのパス
    
    Returns:
        bool: 成功時True、失敗時False
    """
    print(f"\n{'='*60}")
    print(f"[実行中] {name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=False,  # 出力を直接表示
            text=True
        )
        print(f"✅ {name} - 完了")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"❌ {name} - 失敗（終了コード: {e.returncode}）")
        return False
    
    except FileNotFoundError:
        print(f"❌ {name} - ファイルが見つかりません: {script_path}")
        return False


def main():
    """メイン処理"""
    print("="*60)
    print("取引データ分析パイプライン - 一括実行")
    print("="*60)
    
    success_count = 0
    failed_scripts = []
    
    for i, (name, script_file) in enumerate(SCRIPTS, 1):
        script_path = SCRIPT_DIR / script_file
        
        print(f"\n[{i}/{len(SCRIPTS)}] {name}")
        
        if run_script(name, script_path):
            success_count += 1
        else:
            failed_scripts.append(name)
            print(f"\n⚠️  エラーが発生しました。処理を中断します。")
            break
    
    # 結果サマリー
    print("\n" + "="*60)
    print("実行結果サマリー")
    print("="*60)
    print(f"成功: {success_count}/{len(SCRIPTS)}")
    
    if failed_scripts:
        print(f"失敗: {', '.join(failed_scripts)}")
        sys.exit(1)
    else:
        print("✅ 全ての処理が正常に完了しました")
        sys.exit(0)


if __name__ == "__main__":
    main()
