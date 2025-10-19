"""
段階的移行ガイド - 既存コードからモジュラー設計への移行

Phase 1: 既存テーブルのコンポーネント化
Phase 2: チャート機能の追加
Phase 3: レイアウトシステムの統合
Phase 4: 設定駆動型への拡張
"""

# Phase 1: 既存コードの分離
def migrate_existing_table():
    """
    既存のkpi_calc_ytd_monthly_simple.pyから
    KPITableComponentへの移行手順
    """
    steps = [
        "1. 既存のformat_value()をKPITableComponent._format_value()に移動",
        "2. HTML生成ロジックをKPITableComponent._build_html()に移動", 
        "3. データ処理ロジックをKPITableComponent._process_data()に移動",
        "4. CSS StylesをKPITableComponent._get_styles()に移動",
        "5. メインロジックでKPITableComponentを使用するよう変更"
    ]
    return steps

# Phase 2: 可視化ライブラリの選択指針
VISUALIZATION_OPTIONS = {
    'plotly': {
        'pros': ['インタラクティブ', 'HTML統合簡単', 'プロ品質'],
        'cons': ['ファイルサイズ大', '学習コスト'],
        'use_case': 'リッチなダッシュボード'
    },
    'matplotlib + seaborn': {
        'pros': ['軽量', '高度カスタマイズ', '静的画像'],
        'cons': ['インタラクティブ性なし'],
        'use_case': 'レポート生成'
    },
    'altair': {
        'pros': ['文法的', '軽量', 'JSON設定'],
        'cons': ['機能限定'],
        'use_case': '設定駆動型チャート'
    }
}

# Phase 3: 設定駆動型の拡張例
DASHBOARD_TEMPLATES = {
    'executive_summary': {
        'layout': 'single_column',
        'components': ['summary_metrics', 'key_chart'],
        'style': 'minimal'
    },
    'detailed_analysis': {
        'layout': 'two_column', 
        'components': ['kpi_table', 'performance_charts', 'risk_analysis'],
        'style': 'tech'
    },
    'risk_focused': {
        'layout': 'grid',
        'components': ['risk_metrics', 'drawdown_chart', 'var_analysis'],
        'style': 'finance'
    }
}

# Phase 4: 自動化とCI/CD統合
def automation_examples():
    """
    自動化の実装例
    """
    return {
        'scheduled_reports': 'cron + dashboard.generate()',
        'data_update_trigger': 'ファイル監視 + 自動再生成',
        'multi_format_output': 'HTML + PDF + Email送信',
        'version_control': 'Git統合でレポート履歴管理'
    }