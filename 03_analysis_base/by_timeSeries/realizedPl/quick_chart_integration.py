"""
既存ファイルへの最小変更でのグラフ統合例
kpi_calc_ytd_monthly_simple.py の拡張版
"""

# 既存コードの末尾に追加する関数群

def generate_performance_charts(kpi_results, monthly_data):
    """パフォーマンスチャートを生成"""
    
    # 月次データを抽出
    months, returns, pnl_data = extract_monthly_data(kpi_results)
    
    # 月次リターンの棒グラフ
    monthly_chart = create_monthly_returns_chart(months, returns)
    
    # 累積P&Lの線グラフ
    cumulative_chart = create_cumulative_pnl_chart(months, pnl_data)
    
    # Win Rateトレンドチャート
    winrate_chart = create_winrate_trend_chart(kpi_results)
    
    return {
        'monthly_returns': monthly_chart,
        'cumulative_pnl': cumulative_chart,
        'winrate_trend': winrate_chart
    }

def extract_monthly_data(kpi_results):
    """データフレームから月次データを抽出"""
    months = []
    returns = []
    pnl_data = []
    
    # ROI行とTotal Net P/L行を取得
    roi_row = kpi_results[kpi_results['Metric'] == 'ROI']
    pnl_row = kpi_results[kpi_results['Metric'] == 'Total Net P/L (JPY)']
    
    if not roi_row.empty and not pnl_row.empty:
        # 月次列を取得（YTDを除く）
        month_columns = [col for col in kpi_results.columns if col not in ['Metric', 'YTD in 2025', 'is_header']]
        
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

def create_monthly_returns_chart(months, returns):
    """月次リターンの可視化"""
    months_js = str(months).replace("'", '"')
    returns_js = str(returns)
    
    return f"""
    <div class="chart-container">
        <h4>月次パフォーマンス (%)</h4>
        <canvas id="monthlyReturns" width="400" height="250"></canvas>
        <script>
        const ctx1 = document.getElementById('monthlyReturns').getContext('2d');
        new Chart(ctx1, {{
            type: 'bar',
            data: {{
                labels: {months_js},
                datasets: [{{
                    label: 'Monthly Returns (%)',
                    data: {returns_js},
                    backgroundColor: function(context) {{
                        const value = context.parsed.y;
                        return value >= 0 ? '#10b981' : '#ef4444';
                    }},
                    borderRadius: 4,
                    borderSkipped: false
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.parsed.y.toFixed(2) + '%';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: function(value) {{
                                return value + '%';
                            }}
                        }}
                    }}
                }}
            }}
        }});
        </script>
    </div>
    """

def create_cumulative_pnl_chart(months, pnl_data):
    """累積P&Lチャートを生成"""
    # 累積値を計算
    cumulative_pnl = []
    running_total = 0
    for pnl in pnl_data:
        running_total += pnl
        cumulative_pnl.append(running_total)
    
    months_js = str(months).replace("'", '"')
    cumulative_js = str(cumulative_pnl)
    
    return f"""
    <div class="chart-container">
        <h4>累積P&L (JPY)</h4>
        <canvas id="cumulativePnl" width="400" height="250"></canvas>
        <script>
        const ctx2 = document.getElementById('cumulativePnl').getContext('2d');
        new Chart(ctx2, {{
            type: 'line',
            data: {{
                labels: {months_js},
                datasets: [{{
                    label: 'Cumulative P&L',
                    data: {cumulative_js},
                    borderColor: '#4299e1',
                    backgroundColor: 'rgba(66, 153, 225, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return new Intl.NumberFormat('ja-JP').format(context.parsed.y) + ' JPY';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        ticks: {{
                            callback: function(value) {{
                                return new Intl.NumberFormat('ja-JP', {{notation: 'compact'}}).format(value);
                            }}
                        }}
                    }}
                }}
            }}
        }});
        </script>
    </div>
    """

def create_winrate_trend_chart(kpi_results):
    """勝率トレンドチャートを生成"""
    winrate_row = kpi_results[kpi_results['Metric'] == 'Win Rate (WR)']
    
    if winrate_row.empty:
        return '<div class="chart-container"><p>勝率データがありません</p></div>'
    
    months = []
    winrates = []
    month_columns = [col for col in kpi_results.columns if col not in ['Metric', 'YTD in 2025', 'is_header']]
    
    for col in month_columns:
        if col and winrate_row[col].iloc[0] != '' and winrate_row[col].iloc[0] != '—':
            months.append(col.replace('-2025', ''))
            wr_val = winrate_row[col].iloc[0]
            if isinstance(wr_val, str) and '%' in wr_val:
                winrates.append(float(wr_val.replace('%', '')))
            else:
                winrates.append(0)
    
    months_js = str(months).replace("'", '"')
    winrates_js = str(winrates)
    
    return f"""
    <div class="chart-container">
        <h4>勝率トレンド (%)</h4>
        <canvas id="winrateTrend" width="400" height="250"></canvas>
        <script>
        const ctx3 = document.getElementById('winrateTrend').getContext('2d');
        new Chart(ctx3, {{
            type: 'line',
            data: {{
                labels: {months_js},
                datasets: [{{
                    label: 'Win Rate (%)',
                    data: {winrates_js},
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    borderWidth: 3,
                    pointBackgroundColor: '#8b5cf6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.parsed.y.toFixed(1) + '%';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        min: 0,
                        max: 100,
                        ticks: {{
                            callback: function(value) {{
                                return value + '%';
                            }}
                        }}
                    }}
                }}
            }}
        }});
        </script>
    </div>
    """

def integrate_charts_in_html(table_html, charts):
    """既存HTMLにチャートを統合"""
    
    chart_section = f"""
    <div class="dashboard-grid">
        <div class="table-section">
            {table_html}
        </div>
        <div class="charts-section">
            <div class="charts-header">
                <h3>Performance Analysis</h3>
                <p class="charts-subtitle">月次パフォーマンスの可視化</p>
            </div>
            <div class="charts-grid">
                {charts.get('monthly_returns', '')}
                {charts.get('cumulative_pnl', '')}
                {charts.get('winrate_trend', '')}
            </div>
        </div>
    </div>
    
    <style>
    .dashboard-grid {{
        display: grid;
        grid-template-columns: 1.2fr 1fr;
        gap: 30px;
        margin-top: 20px;
        align-items: start;
    }}
    
    .table-section {{
        min-height: 600px;
    }}
    
    .charts-section {{
        display: flex;
        flex-direction: column;
        gap: 20px;
    }}
    
    .charts-header {{
        padding: 0 20px;
    }}
    
    .charts-header h3 {{
        color: #2d3748;
        font-size: 18px;
        margin-bottom: 5px;
        font-weight: 600;
    }}
    
    .charts-subtitle {{
        color: #718096;
        font-size: 13px;
        margin: 0;
    }}
    
    .charts-grid {{
        display: flex;
        flex-direction: column;
        gap: 15px;
    }}
    
    .chart-container {{
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
        height: 300px;
        position: relative;
    }}
    
    .chart-container h4 {{
        color: #2d3748;
        font-size: 14px;
        font-weight: 600;
        margin: 0 0 15px 0;
        padding-bottom: 10px;
        border-bottom: 2px solid #e2e8f0;
    }}
    
    .chart-container canvas {{
        max-height: 220px;
    }}
    
    @media (max-width: 1400px) {{
        .dashboard-grid {{
            grid-template-columns: 1fr;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
    }}
    
    @media (max-width: 768px) {{
        .dashboard-grid {{
            gap: 20px;
        }}
        
        .charts-grid {{
            grid-template-columns: 1fr;
        }}
        
        .chart-container {{
            height: 280px;
        }}
    }}
    </style>
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    """
    
    return chart_section

# 使用例：kpi_calc_ytd_monthly_simple.py の末尾に追加：
"""
# 既存のHTML生成部分の後に追加
import sys
sys.path.append('.')
from quick_chart_integration import generate_performance_charts, integrate_charts_in_html

# チャートを生成
charts = generate_performance_charts(kpi_results, monthly_data)

# 既存のHTMLと統合
enhanced_html = integrate_charts_in_html(table_html, charts)

# HTMLファイルとして保存
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(enhanced_html)

print(f"[SAVE] Enhanced Dashboard: {html_path}")
"""