# -*- coding: utf-8 -*-
"""
Python共通初期化スクリプト

プロジェクト全体で使用するPython環境の初期化を行います。
"""

import sys
from pathlib import Path

# プロジェクトルートを取得
# config/py/bootstrap.py -> プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent

# プロジェクトルートをPythonパスに追加
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# config/py をPythonパスに追加
CONFIG_PY_DIR = Path(__file__).parent
if str(CONFIG_PY_DIR) not in sys.path:
    sys.path.insert(0, str(CONFIG_PY_DIR))

# データパス管理をインポート可能にする
# from data_paths import get_data_paths
# from utils import save_dataframe, parquet_to_csv

print(f"[Python Bootstrap] Project root: {PROJECT_ROOT}")
print(f"[Python Bootstrap] Config py dir: {CONFIG_PY_DIR}")

