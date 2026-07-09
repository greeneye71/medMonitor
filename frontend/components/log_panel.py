"""Log panel component — terminal dark style."""

from dash import html, dcc


def log_panel() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Log di sistema", style={"fontWeight": "700", "fontSize": "13px"}),
                    html.Div(
                        [
                            html.Button("ALL",     id="log-filter-ALL",     n_clicks=1,
                                        style={"background": "#0f172a", "color": "#fff", "border": "none",
                                               "borderRadius": "4px", "padding": "2px 8px", "fontSize": "10px", "cursor": "pointer"}),
                            html.Button("INFO",    id="log-filter-INFO",    n_clicks=0,
                                        style={"background": "#f1f5f9", "color": "#64748b", "border": "none",
                                               "borderRadius": "4px", "padding": "2px 8px", "fontSize": "10px", "cursor": "pointer", "marginLeft": "2px"}),
                            html.Button("WARNING", id="log-filter-WARNING", n_clicks=0,
                                        style={"background": "#f1f5f9", "color": "#64748b", "border": "none",
                                               "borderRadius": "4px", "padding": "2px 8px", "fontSize": "10px", "cursor": "pointer", "marginLeft": "2px"}),
                            html.Button("ERROR",   id="log-filter-ERROR",   n_clicks=0,
                                        style={"background": "#f1f5f9", "color": "#64748b", "border": "none",
                                               "borderRadius": "4px", "padding": "2px 8px", "fontSize": "10px", "cursor": "pointer", "marginLeft": "2px"}),
                        ],
                        style={"display": "flex"},
                    ),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                       "marginBottom": "8px"},
            ),
            html.Div(id="log-panel-content", className="mm-log-panel"),
            dcc.Store(id="log-filter-store", data="ALL"),
        ],
        className="mm-card",
    )
