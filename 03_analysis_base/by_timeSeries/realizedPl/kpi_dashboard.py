"""
統合ダッシュボード生成システム
モジュラー設計によるコンポーネント統合の実装例
"""

import sys
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))

from components.kpi_table import KPITableComponent
from components.performance_chart import PerformanceChartComponent
from layouts.dashboard_layout import DashboardLayout


class KPIDashboard:
    """メインダッシュボードクラス - 全コンポーネントを統合"""
    
    def __init__(self, config=None):
        self.config = config or self._default_config()
        self.components = {}
        
    def _default_config(self):
        return {
            'data_sources': {
                'main_data': '03_ts_monthly_20251019.parquet',
                'fx_data': 'merged_trading_summary_20251019.csv'
            },
            'output': {
                'directory': '04_output/dashboards',
                'filename': f'kpi_dashboard_{datetime.now().strftime("%Y%m%d")}.html'
            },
            'layout': {
                'type': 'two_column',
                'responsive': True
            },
            'components': {
                'kpi_table': {'enabled': True, 'position': 'left'},
                'performance_charts': {'enabled': True, 'position': 'right'},
                'risk_metrics': {'enabled': True, 'position': 'right'}
            }
        }
    
    def initialize_components(self):
        """コンポーネントを初期化"""
        
        # KPIテーブルコンポーネント
        if self.config['components']['kpi_table']['enabled']:
            self.components['kpi_table'] = KPITableComponent(
                data_path=self.config['data_sources']['main_data'],
                fx_data_path=self.config['data_sources']['fx_data']
            )
        
        # パフォーマンスチャートコンポーネント
        if self.config['components']['performance_charts']['enabled']:
            self.components['performance_charts'] = PerformanceChartComponent(
                data=None  # 実際のデータを渡す
            )
    
    def generate_dashboard(self):
        """ダッシュボードを生成"""
        
        # コンポーネントを初期化
        self.initialize_components()
        
        # レイアウトマネージャーを作成
        layout = DashboardLayout(
            layout_type=self.config['layout']['type'],
            config={
                'title': 'Trading Performance Dashboard',
                'subtitle': f'分析期間: 2025-01-01 - {datetime.now().strftime("%Y-%m-%d")}'
            }
        )
        
        # 各コンポーネントを追加
        if 'kpi_table' in self.components:
            table_html = self.components['kpi_table'].generate_html()
            layout.add_component(table_html, position='left')
        
        if 'performance_charts' in self.components:
            charts = self.components['performance_charts']
            
            # 複数のチャートを生成
            cumulative_chart = charts.generate_cumulative_returns_chart()
            monthly_chart = charts.generate_monthly_performance_bars()
            risk_chart = charts.generate_risk_return_scatter()
            
            layout.add_component(cumulative_chart, position='right')
            layout.add_component(monthly_chart, position='right')
            layout.add_component(risk_chart, position='right')
        
        return layout
    
    def save_dashboard(self, custom_path=None):
        """ダッシュボードを保存"""
        
        layout = self.generate_dashboard()
        
        # 出力パスを決定
        if custom_path:
            output_path = Path(custom_path)
        else:
            output_dir = Path(self.config['output']['directory'])
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / self.config['output']['filename']
        
        # ダッシュボードを保存
        layout.save_dashboard(output_path)
        
        return output_path


def main():
    """メイン実行関数 - 使用例"""
    
    # カスタム設定（オプション）
    custom_config = {
        'layout': {'type': 'two_column'},
        'components': {
            'kpi_table': {'enabled': True},
            'performance_charts': {'enabled': True}
        }
    }
    
    # ダッシュボード生成
    dashboard = KPIDashboard(config=custom_config)
    output_path = dashboard.save_dashboard()
    
    print(f"Dashboard generated: {output_path}")


if __name__ == "__main__":
    main()


"""
使用方法の例:

1. 基本的な使用:
   dashboard = KPIDashboard()
   dashboard.save_dashboard()

2. カスタム設定:
   config = {
       'layout': {'type': 'grid'},
       'components': {'kpi_table': {'enabled': True}}
   }
   dashboard = KPIDashboard(config=config)
   
3. 個別コンポーネントの使用:
   kpi_table = KPITableComponent(data_path="data.parquet")
   html = kpi_table.generate_html()
   
4. 新しいコンポーネントの追加:
   - components/new_component.py を作成
   - DashboardLayoutで統合
   - 設定で有効化

この設計により、Rのパネル方式と同様の柔軟性を実現:
- 各コンポーネントは独立して開発・テスト可能
- 設定変更のみでレイアウト変更
- 新しい分析の追加が容易
- 既存コンポーネントの再利用性
"""