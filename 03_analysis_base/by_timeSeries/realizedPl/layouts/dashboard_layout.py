"""
Dashboard Layout Manager - レイアウト管理とコンポーネント統合
"""
from pathlib import Path
from datetime import datetime


class DashboardLayout:
    def __init__(self, layout_type='two_column', config=None):
        self.layout_type = layout_type
        self.config = config or self._default_config()
        self.components = []
        
    def _default_config(self):
        return {
            'title': 'KPI Dashboard',
            'subtitle': f'集計期間: {datetime.now().strftime("%Y-%m-%d")}',
            'responsive': True,
            'grid_columns': 2,
            'component_spacing': '20px'
        }
    
    def add_component(self, component_html, position='auto', width='auto'):
        """コンポーネントを追加"""
        self.components.append({
            'html': component_html,
            'position': position,
            'width': width
        })
    
    def generate_layout(self):
        """レイアウトHTMLを生成"""
        if self.layout_type == 'two_column':
            return self._generate_two_column_layout()
        elif self.layout_type == 'grid':
            return self._generate_grid_layout()
        else:
            return self._generate_single_column_layout()
    
    def _generate_two_column_layout(self):
        """2列レイアウト（左：テーブル、右：チャート）"""
        return f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config['title']}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        {self._get_base_styles()}
        {self._get_two_column_styles()}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <header class="dashboard-header">
            <h1>{self.config['title']}</h1>
            <p class="subtitle">{self.config['subtitle']}</p>
        </header>
        
        <div class="dashboard-content">
            <div class="left-panel">
                <!-- テーブルコンポーネント -->
                <div class="component-wrapper">
                    {self._get_component_by_type('table')}
                </div>
            </div>
            
            <div class="right-panel">
                <!-- チャートコンポーネント -->
                <div class="charts-grid">
                    {self._get_component_by_type('chart')}
                </div>
            </div>
        </div>
        
        <footer class="dashboard-footer">
            <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </footer>
    </div>
</body>
</html>
        """
    
    def _get_base_styles(self):
        """基本スタイル"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background-color: #f8fafc;
            color: #1a202c;
            line-height: 1.5;
        }
        
        .dashboard-container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .dashboard-header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
        }
        
        .component-wrapper {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        """
    
    def _get_two_column_styles(self):
        """2列レイアウト用スタイル"""
        return """
        .dashboard-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .left-panel {
            overflow-x: auto;
        }
        
        .charts-grid {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        @media (max-width: 1200px) {
            .dashboard-content {
                grid-template-columns: 1fr;
            }
        }
        """
    
    def _get_component_by_type(self, component_type):
        """タイプ別にコンポーネントを取得"""
        # 実際の実装では、登録されたコンポーネントから該当するものを返す
        if component_type == 'table':
            return '<!-- KPI Table Component -->'
        elif component_type == 'chart':
            return '<!-- Chart Components -->'
        return ''
    
    def save_dashboard(self, output_path):
        """ダッシュボードをファイルに保存"""
        html_content = self.generate_layout()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path