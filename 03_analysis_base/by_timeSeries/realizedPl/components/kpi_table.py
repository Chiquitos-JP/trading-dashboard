"""
KPI Table Component - モジュラー設計
既存のテーブル機能を独立したコンポーネントとして分離
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

class KPITableComponent:
    def __init__(self, data_path, fx_data_path=None, config=None):
        self.data_path = data_path
        self.fx_data_path = fx_data_path
        self.config = config or self._default_config()
        
    def _default_config(self):
        """デフォルト設定"""
        return {
            'period_start': '2025-01-01',
            'period_end': datetime.now().strftime('%Y-%m-%d'),
            'style': {
                'theme': 'tech',  # 'tech', 'finance', 'minimal'
                'color_scheme': 'blue',
                'font_family': 'system'
            }
        }
    
    def generate_html(self, output_path=None):
        """HTMLテーブルを生成"""
        # 既存のロジックをここに移植
        html_content = self._build_html()
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        return html_content
    
    def _build_html(self):
        """HTML構築（既存コードを移植）"""
        # 既存のHTMLビルドロジックをここに配置
        return """
        <div class="kpi-table-component">
            <!-- テーブルコンテンツ -->
        </div>
        """
    
    def get_summary_stats(self):
        """サマリー統計を取得（他のコンポーネントで使用）"""
        return {
            'total_trades': 505,
            'win_rate': 0.7287,
            'total_pnl': 11131798,
            # その他の統計
        }