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
8. Quartoレンダリング        - レポートサイト生成

使い方:
    python run_all.py
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path
from datetime import datetime

# スクリプトのディレクトリを取得
SCRIPT_DIR = Path(__file__).parent

# 実行するスクリプトのリスト（順序重要）
SCRIPTS = [
    ("FRED為替更新", "../forex/forex_fred.py"),  # 為替レート更新（月次CSV再生成）
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


def create_latest_link() -> bool:
    """最新のQuarto出力へのコピーを作成"""
    today = datetime.now().strftime("%Y%m%d")
    ROOT_DIR = SCRIPT_DIR.parents[2]
    
    output_base = ROOT_DIR / "docs" / "quarto"
    latest_dir = output_base / "latest"
    current_dir = output_base / f"quarto_{today}"
    
    # 既存の latest を削除
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    
    # 新しいコピーを作成
    shutil.copytree(current_dir, latest_dir, dirs_exist_ok=True)
    print(f"✅ latest コピー作成: {latest_dir}")
    
    return True


def create_root_landing_page() -> bool:
    """docs/index.html にランディングページを作成"""
    ROOT_DIR = SCRIPT_DIR.parents[2]
    landing_page = ROOT_DIR / "docs" / "index.html"
    
    html_content = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="0; url=quarto/latest/index.html">
    <title>Trading KPI Reports</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            text-align: center;
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 0.5em;
        }
        p {
            font-size: 1.2em;
        }
        a {
            color: #fff;
            text-decoration: none;
            border-bottom: 2px solid #fff;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Trading KPI Reports</h1>
        <p>自動的にリダイレクトします...</p>
        <p><a href="quarto/latest/index.html">最新のレポートを見る →</a></p>
    </div>
</body>
</html>'''
    
    landing_page.write_text(html_content, encoding='utf-8')
    print(f"✅ ランディングページ作成: {landing_page}")
    return True


def create_nojekyll() -> bool:
    """Jekyll を無効化（GitHub Pages 用）"""
    ROOT_DIR = SCRIPT_DIR.parents[2]
    nojekyll = ROOT_DIR / "docs" / ".nojekyll"
    nojekyll.touch()
    print(f"✅ .nojekyll 作成")
    return True


def run_quarto() -> bool:
    """
    Quarto でサイトをレンダリング
    
    Returns:
        bool: 成功時True、失敗時False
    """
    # Quartoがインストールされているか確認
    quarto_path = shutil.which("quarto")
    if not quarto_path:
        print("⚠️ Quarto が見つかりません")
        print("インストール方法: winget install --id Quarto.Quarto -e")
        return False
    
    # Quartoプロジェクトのパス(realizedPl/ の親の quarto/)
    QUARTO_DIR = (SCRIPT_DIR.parent / "quarto").resolve()
    
    if not QUARTO_DIR.exists():
        print(f"⚠️ Quartoディレクトリが見つかりません: {QUARTO_DIR}")
        return False
    
    # 日付ベースの出力先ディレクトリを作成
    today = datetime.now().strftime("%Y%m%d")
    ROOT_DIR = SCRIPT_DIR.parents[2]
    output_base = ROOT_DIR / "docs" / "quarto"
    output_dir = output_base / f"quarto_{today}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"[実行中] Quarto レンダリング")
    print(f"{'='*60}")
    print(f"📁 Quartoプロジェクト: {QUARTO_DIR}")
    print(f"📁 出力先: {output_dir}")
    
    # 環境変数でQuartoに出力先を指示
    env = os.environ.copy()
    env["QUARTO_PROJECT_OUTPUT_DIR"] = str(output_dir)
    
    # レンダリング対象の .qmd ファイル
    qmd_files = ["index.qmd", "analysis.qmd"]
    
    for qmd in qmd_files:
        qmd_path = QUARTO_DIR / qmd
        
        if not qmd_path.exists():
            print(f"⚠️ スキップ: {qmd} が見つかりません")
            continue
        
        try:
            subprocess.run(
                [quarto_path, "render", str(qmd_path), "--no-clean", "--output-dir", str(output_dir)],
                check=True,
                cwd=str(QUARTO_DIR),
                env=env
            )
            print(f"✅ {qmd} レンダリング完了")
        
        except subprocess.CalledProcessError as e:
            print(f"❌ {qmd} レンダリング失敗(終了コード: {e.returncode})")
            return False
    
    # 出力先の確認
    if output_dir.exists():
        print(f"\n📄 出力先: {output_dir}")
        print(f"   - {output_dir / 'index.html'}")
        print(f"   - {output_dir / 'analysis.html'}")
        
        # GitHub Pages用の追加処理
        create_latest_link()
        create_root_landing_page()
        create_nojekyll()
    
    return True


def main():
    """メイン処理"""
    print("="*60)
    print("取引データ分析パイプライン - 一括実行")
    print("="*60)
    
    success_count = 0
    failed_scripts = []
    
    for i, (name, script_file) in enumerate(SCRIPTS, 1):
        script_path = (SCRIPT_DIR / script_file).resolve()
        
        print(f"\n[{i}/{len(SCRIPTS)}] {name}")
        
        if run_script(name, script_path):
            success_count += 1
        else:
            failed_scripts.append(name)
            print(f"\n⚠️  エラーが発生しました。処理を中断します。")
            break
    
    # すべてのPythonスクリプトが成功した場合のみ Quarto を実行
    if not failed_scripts:
        print(f"\n[{len(SCRIPTS) + 1}/{len(SCRIPTS) + 1}] Quartoレンダリング")
        if run_quarto():
            success_count += 1
        else:
            failed_scripts.append("Quartoレンダリング")
    
    # 結果サマリー
    print("\n" + "="*60)
    print("実行結果サマリー")
    print("="*60)
    print(f"成功: {success_count}/{len(SCRIPTS) + 1}")  # +1 for Quarto
    
    if failed_scripts:
        print(f"失敗: {', '.join(failed_scripts)}")
        sys.exit(1)
    else:
        print("✅ 全ての処理が正常に完了しました")
        print(f"\n📊 最新のレポートは以下で確認できます:")
        
        # 最新のQuarto出力を表示
        today = datetime.now().strftime("%Y%m%d")
        output_dir = SCRIPT_DIR.parents[2] / "docs" / "quarto" / f"quarto_{today}"
        if output_dir.exists():
            print(f"   {output_dir / 'index.html'}")
        
        sys.exit(0)


if __name__ == "__main__":
    main()
