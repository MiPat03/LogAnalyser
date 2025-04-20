import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3

# Function to create Dash app
def create_dash_app(flask_app):
    # Create a Dash app
    dash_app = dash.Dash(
        __name__,
        server=flask_app,
        url_base_pathname='/dash/',
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}]
    )

    # Set to True for production
    dash_app.config.suppress_callback_exceptions = True

    # Define the layout
    dash_app.layout = html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H2("Log Analytics Dashboard", className="text-primary mb-4"),
                    html.P("Interactive visualizations of your log data", className="lead")
                ], width=12)
            ], className="mb-4"),

            # Data Summary section at the top
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Data Summary"),
                        dbc.CardBody([
                            html.Div(id="data-summary")
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=12)
            ]),

            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Filter Options"),
                        dbc.CardBody([
                            html.Label("Select File:"),
                            dcc.Dropdown(id='file-dropdown', className="mb-3"),

                            html.Label("Date Range:"),
                            dcc.DatePickerRange(
                                id='date-range',
                                className="mb-3",
                                start_date_placeholder_text="Start Date",
                                end_date_placeholder_text="End Date"
                            ),

                            html.Label("Status Code:"),
                            dcc.RangeSlider(
                                id='status-slider',
                                min=100,
                                max=599,
                                step=100,
                                marks={
                                    100: '1xx',
                                    200: '2xx',
                                    300: '3xx',
                                    400: '4xx',
                                    500: '5xx'
                                },
                                value=[100, 599],
                                className="mb-3"
                            ),

                            dbc.Button("Apply Filters", id="apply-filters", color="primary", className="mt-2")
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=3),

                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Status Code Distribution"),
                                dbc.CardBody([
                                    dcc.Graph(id="status-pie-chart", style={"height": "300px"})
                                ])
                            ], className="mb-4 shadow-sm h-100")
                        ], width=6),

                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Request Type Distribution"),
                                dbc.CardBody([
                                    dcc.Graph(id="request-bar-chart", style={"height": "300px"})
                                ])
                            ], className="mb-4 shadow-sm h-100")
                        ], width=6)
                    ]),

                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Top 10 IP Addresses"),
                                dbc.CardBody([
                                    dcc.Graph(id="ip-bar-chart", style={"height": "300px"})
                                ])
                            ], className="mb-4 shadow-sm h-100")
                        ], width=6),

                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Top 5 APIs"),
                                dbc.CardBody([
                                    dcc.Graph(id="api-bar-chart", style={"height": "300px"})
                                ])
                            ], className="mb-4 shadow-sm h-100")
                        ], width=6)
                    ]),

                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("User Agent Distribution"),
                                dbc.CardBody([
                                    dcc.Graph(id="user-agent-chart", style={"height": "300px"})
                                ])
                            ], className="mb-4 shadow-sm h-100")
                        ], width=12)
                    ])
                ], width=9)
            ])
        ], fluid=True)
    ], className="p-4")

    # Helper function to get database connection
    def get_db_connection():
        conn = sqlite3.connect('log_data.db', timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL;')
        return conn

    # Callback to populate file dropdown
    @dash_app.callback(
        Output('file-dropdown', 'options'),
        Output('file-dropdown', 'value'),
        Input('apply-filters', 'n_clicks')
    )
    def update_file_dropdown(n_clicks):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT file_name FROM files ORDER BY upload_date DESC')
            files = cursor.fetchall()
            options = [{'label': file['file_name'], 'value': file['file_name']} for file in files]
            default_value = options[0]['value'] if options else None
            return options, default_value
        finally:
            conn.close()

    # Callback for status code pie chart
    @dash_app.callback(
        Output('status-pie-chart', 'figure'),
        Input('file-dropdown', 'value'),
        Input('status-slider', 'value')
    )
    def update_status_chart(file_name, status_range):
        if not file_name:
            return go.Figure().update_layout(title="No data available")
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Query for status code distribution
            query = '''
            SELECT status_code, COUNT(*) as count 
            FROM logs 
            WHERE file_name = ? AND status_code BETWEEN ? AND ?
            GROUP BY status_code 
            ORDER BY count DESC
            '''
            cursor.execute(query, (file_name, status_range[0], status_range[1]))
            data = cursor.fetchall()
            
            if not data:
                return go.Figure().update_layout(title="No data available")
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=['status_code', 'count'])
            
            # Create pie chart
            fig = px.pie(
                df, 
                values='count', 
                names='status_code',
                # title='Status Code Distribution',
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
            )
            
            return fig
        finally:
            conn.close()

    # Callback for request type bar chart
    @dash_app.callback(
        Output('request-bar-chart', 'figure'),
        Input('file-dropdown', 'value'),
        Input('status-slider', 'value')
    )
    def update_request_chart(file_name, status_range):
        if not file_name:
            return go.Figure().update_layout(title="No data available")
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Query for request type distribution
            query = '''
            SELECT request_type, COUNT(*) as count 
            FROM logs 
            WHERE file_name = ? AND status_code BETWEEN ? AND ?
            GROUP BY request_type 
            ORDER BY count DESC
            '''
            cursor.execute(query, (file_name, status_range[0], status_range[1]))
            data = cursor.fetchall()
            
            if not data:
                return go.Figure().update_layout(title="No data available")
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=['request_type', 'count'])
            
            # Create bar chart
            fig = px.bar(
                df, 
                x='request_type', 
                y='count',
                # title='Request Type Distribution',
                color='request_type',
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            
            fig.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                xaxis_title="",
                yaxis_title="Count",
                legend_title="Request Type"
            )
            
            return fig
        finally:
            conn.close()

    # Callback for top IPs bar chart
    @dash_app.callback(
        Output('ip-bar-chart', 'figure'),
        Input('file-dropdown', 'value'),
        Input('status-slider', 'value')
    )
    def update_ip_chart(file_name, status_range):
        if not file_name:
            return go.Figure().update_layout(title="No data available")
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Query for top 10 IPs
            query = '''
            SELECT ip, COUNT(*) as count 
            FROM logs 
            WHERE file_name = ? AND status_code BETWEEN ? AND ?
            GROUP BY ip 
            ORDER BY count DESC 
            LIMIT 10
            '''
            cursor.execute(query, (file_name, status_range[0], status_range[1]))
            data = cursor.fetchall()
            
            if not data:
                return go.Figure().update_layout(title="No data available")
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=['ip', 'count'])
            
            # Create horizontal bar chart
            fig = px.bar(
                df, 
                y='ip', 
                x='count',
                # title='Top 10 IP Addresses',
                orientation='h',
                color='count',
                color_continuous_scale=px.colors.sequential.Viridis
            )
            
            fig.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                xaxis_title="Count",
                yaxis_title="",
                yaxis={'categoryorder':'total ascending'}
            )
            
            return fig
        finally:
            conn.close()

    # Callback for top APIs bar chart
    @dash_app.callback(
        Output('api-bar-chart', 'figure'),
        Input('file-dropdown', 'value'),
        Input('status-slider', 'value')
    )
    def update_api_chart(file_name, status_range):
        if not file_name:
            return go.Figure().update_layout(title="No data available")
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Query for top 5 APIs
            query = '''
            SELECT api, COUNT(*) as count 
            FROM logs 
            WHERE file_name = ? AND status_code BETWEEN ? AND ?
            GROUP BY api 
            ORDER BY count DESC 
            LIMIT 5
            '''
            cursor.execute(query, (file_name, status_range[0], status_range[1]))
            data = cursor.fetchall()
            
            if not data:
                return go.Figure().update_layout(title="No data available")
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=['api', 'count'])
            
            # Create horizontal bar chart
            fig = px.bar(
                df, 
                y='api', 
                x='count',
                # title='Top 5 APIs',
                orientation='h',
                color='count',
                color_continuous_scale=px.colors.sequential.Plasma
            )
            
            fig.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                xaxis_title="Count",
                yaxis_title="",
                yaxis={'categoryorder':'total ascending'}
            )
            
            return fig
        finally:
            conn.close()

    # Callback for time series chart
    @dash_app.callback(
        Output('time-series-chart', 'figure'),
        Input('file-dropdown', 'value'),
        Input('status-slider', 'value')
    )
    def update_time_series(file_name, status_range):
        if not file_name:
            return go.Figure().update_layout(title="No data available")
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Query for time series data
            query = '''
            SELECT 
                strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                COUNT(*) as count 
            FROM logs 
            WHERE file_name = ? AND status_code BETWEEN ? AND ?
            GROUP BY hour 
            ORDER BY hour
            '''
            cursor.execute(query, (file_name, status_range[0], status_range[1]))
            data = cursor.fetchall()
            
            if not data:
                return go.Figure().update_layout(title="No data available")
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=['hour', 'count'])
            
            # Create time series chart
            fig = px.line(
                df, 
                x='hour', 
                y='count',
                # title='Traffic Over Time',
                markers=True
            )
            
            fig.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                xaxis_title="Time",
                yaxis_title="Request Count"
            )
            
            return fig
        finally:
            conn.close()

    # Callback for response time chart
    @dash_app.callback(
        Output('response-time-chart', 'figure'),
        Input('file-dropdown', 'value'),
        Input('status-slider', 'value')
    )
    def update_response_time(file_name, status_range):
        if not file_name:
            return go.Figure().update_layout(title="No data available")
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Query for response time data
            query = '''
            SELECT 
                api,
                AVG(response_time) as avg_time,
                MIN(response_time) as min_time,
                MAX(response_time) as max_time
            FROM logs 
            WHERE file_name = ? AND status_code BETWEEN ? AND ?
            GROUP BY api 
            ORDER BY avg_time DESC
            LIMIT 10
            '''
            cursor.execute(query, (file_name, status_range[0], status_range[1]))
            data = cursor.fetchall()
            
            if not data:
                return go.Figure().update_layout(title="No data available")
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=['api', 'avg_time', 'min_time', 'max_time'])
            
            # Create response time chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=df['api'],
                y=df['avg_time'],
                name='Average Response Time',
                marker_color='rgb(55, 83, 109)'
                # title='Response Time Analysis (Top 5 APIs by Avg Time)',
            ))
            
            fig.add_trace(go.Scatter(
                x=df['api'],
                y=df['max_time'],
                mode='markers',
                name='Max Response Time',
                marker=dict(
                    color='red',
                    size=10,
                    symbol='triangle-up'
                )
            ))
            
            fig.update_layout(
                # title='Response Time Analysis (Top 5 APIs by Avg Time)',
                xaxis_title='API',
                yaxis_title='Response Time (seconds)',
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            return fig
        finally:
            conn.close()

    # Callback for user agent chart
    @dash_app.callback(
        Output('user-agent-chart', 'figure'),
        Input('file-dropdown', 'value'),
        Input('status-slider', 'value')
    )
    def update_user_agent(file_name, status_range):
        if not file_name:
            return go.Figure().update_layout(title="No data available")
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Query for user agent data
            query = '''
            SELECT 
                CASE
                    WHEN user_agent LIKE '%Chrome%' THEN 'Chrome'
                    WHEN user_agent LIKE '%Firefox%' THEN 'Firefox'
                    WHEN user_agent LIKE '%Safari%' THEN 'Safari'
                    WHEN user_agent LIKE '%Edge%' THEN 'Edge'
                    WHEN user_agent LIKE '%MSIE%' OR user_agent LIKE '%Trident%' THEN 'Internet Explorer'
                    WHEN user_agent LIKE '%bot%' OR user_agent LIKE '%Bot%' OR user_agent LIKE '%spider%' THEN 'Bot'
                    WHEN user_agent LIKE '%curl%' OR user_agent LIKE '%Wget%' THEN 'API Tool'
                    WHEN user_agent LIKE '%Mobile%' OR user_agent LIKE '%Android%' OR user_agent LIKE '%iPhone%' THEN 'Mobile'
                    ELSE 'Other'
                END as browser,
                COUNT(*) as count
            FROM logs 
            WHERE file_name = ? AND status_code BETWEEN ? AND ?
            GROUP BY browser 
            ORDER BY count DESC
            '''
            cursor.execute(query, (file_name, status_range[0], status_range[1]))
            data = cursor.fetchall()
            
            if not data:
                return go.Figure().update_layout(title="No data available")
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=['browser', 'count'])
            
            # Create user agent chart
            fig = px.pie(
                df, 
                values='count', 
                names='browser',
                # title='User Agent Distribution',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            
            return fig
        finally:
            conn.close()

    # Callback for data summary
    @dash_app.callback(
        Output('data-summary', 'children'),
        Input('file-dropdown', 'value'),
        Input('status-slider', 'value')
    )
    def update_data_summary(file_name, status_range):
        if not file_name:
            return html.P("No data available")
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Query for summary data
            query = '''
            SELECT 
                COUNT(*) as total_logs,
                COUNT(DISTINCT ip) as unique_ips,
                COUNT(DISTINCT api) as unique_apis,
                SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count,
                AVG(response_time) as avg_response_time
            FROM logs 
            WHERE file_name = ? AND status_code BETWEEN ? AND ?
            '''
            cursor.execute(query, (file_name, status_range[0], status_range[1]))
            data = cursor.fetchone()
            
            if not data:
                return html.P("No data available")
            
            # Create summary cards
            return dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Total Logs", className="card-title text-muted"),
                            html.H3(f"{data['total_logs']:,}", className="card-text text-primary")
                        ])
                    ], className="text-center shadow-sm")
                ], width=2),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Unique IPs", className="card-title text-muted"),
                            html.H3(f"{data['unique_ips']:,}", className="card-text text-success")
                        ])
                    ], className="text-center shadow-sm")
                ], width=2),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Unique APIs", className="card-title text-muted"),
                            html.H3(f"{data['unique_apis']:,}", className="card-text text-info")
                        ])
                    ], className="text-center shadow-sm")
                ], width=2),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Error Rate", className="card-title text-muted"),
                            html.H3(f"{data['error_count'] / data['total_logs'] * 100:.1f}%", 
                                    className="card-text text-danger")
                        ])
                    ], className="text-center shadow-sm")
                ], width=2),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Avg Response Time", className="card-title text-muted"),
                            html.H3(f"{data['avg_response_time']:.3f}s", className="card-text text-warning")
                        ])
                    ], className="text-center shadow-sm")
                ], width=2),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("File", className="card-title text-muted"),
                            html.H6(file_name, className="card-text text-dark", style={"wordBreak": "break-all"})
                        ])
                    ], className="text-center shadow-sm")
                ], width=2)
            ])
        finally:
            conn.close()

    # Return the Dash app
    return dash_app
