"""Quarto部分のみを実行する補助スクリプト.

既存の `run_all.py` で定義されている `run_quarto` 関数を再利用し、
前段のPython処理をスキップしてサイトの再レンダリングだけを行う。
"""

from __future__ import annotations

import sys
from pathlib import Path

# run_all.py を同じディレクトリからインポートするための準備
CURRENT_DIR = Path(__file__).parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from run_all import run_quarto  # noqa: E402


def main() -> None:
    print("=" * 60)
    print("Quarto レンダリングのみ実行")
    print("=" * 60)

    if run_quarto():
        print("\n✅ Quarto レンダリングが完了しました")
        sys.exit(0)

    print("\n❌ Quarto レンダリングに失敗しました")
    sys.exit(1)


if __name__ == "__main__":
    main()
