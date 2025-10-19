"""
Performance Chart Component - パフォーマンス可視化
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


class PerformanceChartComponent:
    def __init__(self, data, config=None):
        self.data = data
        self.config = config or self._default_config()
    
    def _default_config(self):
        return {
            'width': 600,
            'height': 400,
            'theme': 'plotly_white',
            'colors': ['#4299e1', '#63b3ed', '#90cdf4'],
            'show_legend': True
        }
    
    def generate_cumulative_returns_chart(self, kpi_data=None):
        """累積リターンチャート"""
        fig = go.Figure()
        
        if kpi_data is not None and hasattr(kpi_data, 'columns'):
            # 実際のKPIデータから月次リターンを抽出
            months, returns, pnl_data = self._extract_monthly_data(kpi_data)
            
            # 累積リターンを計算
            cumulative_returns = np.cumsum(returns)
            
            fig.add_trace(go.Scatter(
                x=months,
                y=cumulative_returns,
                mode='lines+markers',
                name='Cumulative Returns',
                line=dict(color=self.config['colors'][0], width=3),
                marker=dict(size=6)
            ))
        else:
            # サンプルデータ（実際のデータがない場合）
            dates = pd.date_range('2025-01-01', periods=10, freq='M')
            months = [date.strftime('%b') for date in dates]
            cumulative_returns = np.cumsum([0.07, -0.14, -5.48, 0.84, 0.75, 0.86, 1.08, 0.78, 0.96, 1.2])
            
            fig.add_trace(go.Scatter(
                x=months,
                y=cumulative_returns,
                mode='lines+markers',
                name='Cumulative Returns',
                line=dict(color=self.config['colors'][0], width=3),
                marker=dict(size=6)
            ))
        
        fig.update_layout(
            title='Cumulative Returns (%)',
            xaxis_title='Month',
            yaxis_title='Cumulative Returns (%)',
            template=self.config['theme'],
            width=self.config['width'],
            height=self.config['height'],
            showlegend=self.config['show_legend']
        )
        
        return fig.to_html(include_plotlyjs='inline', div_id="cumulative-returns")
    
    def generate_monthly_performance_bars(self):
        """月次パフォーマンス棒グラフ"""
        months = ['Jan', 'Feb', 'Mar', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct']
        returns = [0.07, -0.14, -5.48, 0.84, 0.75, 0.86, 1.08, 0.78, 0.96]
        
        colors = ['green' if r > 0 else 'red' for r in returns]
        
        fig = go.Figure(data=[
            go.Bar(x=months, y=returns, marker_color=colors)
        ])
        
        fig.update_layout(
            title='Monthly Returns (%)',
            xaxis_title='Month',
            yaxis_title='Return (%)',
            template=self.config['theme'],
            width=self.config['width'],
            height=self.config['height']
        )
        
        return fig.to_html(include_plotlyjs=False, div_id="monthly-performance")
    
    def generate_risk_return_scatter(self):
        """リスク・リターン散布図"""
        # 実装例
        fig = px.scatter(
            x=[0.1, 0.2, 0.15], 
            y=[0.05, 0.08, 0.06],
            title="Risk vs Return"
        )
        
        return fig.to_html(include_plotlyjs=False, div_id="risk-return")
    
    def _extract_monthly_data(self, kpi_data):
        """KPIデータから月次データを抽出"""
        months = []
        returns = []
        pnl_data = []
        
        # ROI行とTotal Net P/L行を取得
        roi_row = kpi_data[kpi_data['Metric'] == 'ROI']
        pnl_row = kpi_data[kpi_data['Metric'] == 'Total Net P/L (JPY)']
        
        if not roi_row.empty and not pnl_row.empty:
            # 月次列を取得（YTDを除く）
            month_columns = [col for col in kpi_data.columns if col not in ['Metric', 'YTD in 2025', 'is_header']]
            
            for col in month_columns:
                if col and roi_row[col].iloc[0] != '' and roi_row[col].iloc[0] != '—':
                    months.append(col.replace('-2025', ''))
                    
                    # ROIからパーセントを数値に変換
                    roi_val = roi_row[col].iloc[0]
                    if isinstance(roi_val, str) and '%' in roi_val:
                        returns.append(float(roi_val.replace('%', '')))
                    else:
                        returns.append(0)
                    
                    # P&Lデータを数値に変換
                    pnl_val = pnl_row[col].iloc[0]
                    if isinstance(pnl_val, str):
                        pnl_clean = pnl_val.replace(',', '').replace('—', '0')
                        try:
                            pnl_data.append(float(pnl_clean))
                        except ValueError:
                            pnl_data.append(0)
                    else:
                        pnl_data.append(float(pnl_val) if pnl_val else 0)
        
        return months, returns, pnl_data