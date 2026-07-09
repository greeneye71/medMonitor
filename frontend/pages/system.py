"""Pagina Sistema — monitoraggio e controllo servizi backend."""

from dash import html
from frontend.components.service_status import service_card
from frontend.components.log_panel import log_panel


def layout():
    return html.Div(
        [
            html.Div(
                [
                    html.H1("Sistema", className="mm-page-title"),
                    html.Div(
                        html.Span("–", id="system-updated-ts",
                                  style={"fontSize": "12px", "color": "#94a3b8"}),
                    ),
                ],
                className="mm-page-header",
            ),
            html.Div(
                [
                    # Colonna 1 — Servizi
                    html.Div(
                        [
                            html.Div("Servizi", style={"fontWeight": "700", "fontSize": "13px",
                                                        "marginBottom": "12px", "color": "#64748b",
                                                        "textTransform": "uppercase", "letterSpacing": "0.5px"}),
                            html.Div(id="service-cards-container"),
                        ],
                        style={"flex": "1", "minWidth": "220px"},
                    ),
                    # Colonna 2 — Log
                    html.Div(
                        log_panel(),
                        style={"flex": "2", "minWidth": "320px"},
                    ),
                    # Colonna 3 — Metriche
                    html.Div(
                        [
                            html.Div("Metriche", style={"fontWeight": "700", "fontSize": "13px",
                                                          "marginBottom": "12px", "color": "#64748b",
                                                          "textTransform": "uppercase", "letterSpacing": "0.5px"}),
                            html.Div(id="system-metrics-container"),
                            html.Button(
                                "📦 Archivia ora",
                                id="archive-now-btn",
                                n_clicks=0,
                                style={"marginTop": "16px", "background": "#0f172a", "color": "#fff",
                                       "border": "none", "borderRadius": "8px", "padding": "8px 16px",
                                       "fontSize": "13px", "cursor": "pointer", "width": "100%"},
                            ),
                            html.Div(id="archive-result", style={"marginTop": "8px", "fontSize": "12px"}),
                        ],
                        style={"flex": "1", "minWidth": "200px"},
                    ),
                ],
                style={"display": "flex", "gap": "20px", "flexWrap": "wrap"},
            ),
        ]
    )
