"""Dashboard page layout v2."""

from dash import html, dcc


def layout():
    return html.Div(
        [
            # Page header
            html.Div(
                [
                    html.H1("Dashboard", className="mm-page-title"),
                    html.Div(
                        [
                            html.Span("–", id="dashboard-updated-ts",
                                      style={"fontSize": "12px", "color": "#94a3b8", "marginRight": "8px"}),
                            html.Button("↻ Aggiorna", id="dashboard-refresh-btn",
                                        style={"background": "none", "border": "1px solid #e2e8f0",
                                               "borderRadius": "6px", "padding": "4px 10px",
                                               "fontSize": "12px", "cursor": "pointer", "color": "#64748b"}),
                        ],
                        style={"display": "flex", "alignItems": "center"},
                    ),
                ],
                className="mm-page-header",
            ),
            # Error banner (hidden by default)
            html.Div(id="dashboard-error-banner", style={"display": "none"}),
            # Zone cards grid
            html.Div(id="dashboard-zone-cards",
                     style={"display": "grid",
                            "gridTemplateColumns": "repeat(auto-fill, minmax(280px, 1fr))",
                            "gap": "16px", "marginBottom": "20px"}),
            # 24h chart
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Temperatura — ultime 24h", style={"fontSize": "14px", "fontWeight": "700"}),
                            html.Div(
                                [
                                    html.Button("6h",  id="chart-range-6h",  n_clicks=0,
                                                style={"background": "#f1f5f9", "border": "none", "borderRadius": "6px",
                                                       "padding": "4px 10px", "fontSize": "11px", "color": "#64748b", "cursor": "pointer"}),
                                    html.Button("24h", id="chart-range-24h", n_clicks=0,
                                                style={"background": "#0f172a", "border": "none", "borderRadius": "6px",
                                                       "padding": "4px 10px", "fontSize": "11px", "color": "#fff", "cursor": "pointer"}),
                                    html.Button("7g",  id="chart-range-7d",  n_clicks=0,
                                                style={"background": "#f1f5f9", "border": "none", "borderRadius": "6px",
                                                       "padding": "4px 10px", "fontSize": "11px", "color": "#64748b", "cursor": "pointer"}),
                                ],
                                style={"display": "flex", "gap": "4px"},
                            ),
                        ],
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                               "marginBottom": "12px"},
                    ),
                    dcc.Graph(id="dashboard-chart", config={"displayModeBar": False},
                              style={"height": "300px"}),
                ],
                className="mm-card",
                style={"marginBottom": "20px"},
            ),
            # Sensors table
            html.Div(
                [
                    html.Div("Sensori", style={"fontSize": "14px", "fontWeight": "700", "marginBottom": "12px"}),
                    html.Div(id="dashboard-sensors-table"),
                ],
                className="mm-card",
            ),
        ]
    )
