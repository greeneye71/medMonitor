"""Impostazioni v2 — 5 tab: Sensori, Soglie, Email/Alert, Generale, Demo."""

import dash_bootstrap_components as dbc
from dash import html, dcc


def layout():
    return html.Div(
        [
            html.Div(
                html.H1("Impostazioni", className="mm-page-title"),
                className="mm-page-header",
            ),
            dbc.Tabs(
                [
                    dbc.Tab(_tab_sensors(), label="Sensori", tab_id="tab-sensors"),
                    dbc.Tab(_tab_thresholds(), label="Soglie", tab_id="tab-thresholds"),
                    dbc.Tab(_tab_email(), label="Email / Alert", tab_id="tab-email"),
                    dbc.Tab(_tab_general(), label="Generale", tab_id="tab-general"),
                    dbc.Tab(_tab_demo(), label="Demo", tab_id="tab-demo"),
                ],
                id="settings-tabs",
                active_tab="tab-sensors",
            ),
            dcc.Store(id="settings-save-trigger"),
        ]
    )


def _tab_sensors():
    return html.Div(
        [
            # Discovered sensors
            html.Div(
                [
                    html.Div("Rilevati automaticamente",
                             style={"fontSize": "13px", "fontWeight": "700", "marginBottom": "8px"}),
                    html.Div(id="discovered-sensors-list"),
                    html.Div(id="accept-sensor-modal-container"),
                ],
                className="mm-card",
                style={"marginBottom": "16px", "marginTop": "16px"},
            ),
            # Configured sensors
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Sensori configurati",
                                     style={"fontSize": "13px", "fontWeight": "700"}),
                            html.Button("+ Aggiungi manualmente", id="add-sensor-manual-btn",
                                        n_clicks=0,
                                        style={"background": "#0f172a", "color": "#fff", "border": "none",
                                               "borderRadius": "6px", "padding": "6px 12px", "fontSize": "12px",
                                               "cursor": "pointer"}),
                        ],
                        style={"display": "flex", "justifyContent": "space-between",
                               "alignItems": "center", "marginBottom": "12px"},
                    ),
                    html.Div(id="configured-sensors-grid"),
                ],
                className="mm-card",
            ),
        ]
    )


def _tab_thresholds():
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Zone e soglie",
                             style={"fontSize": "13px", "fontWeight": "700"}),
                    html.Button("+ Aggiungi zona", id="add-zone-btn", n_clicks=0,
                                style={"background": "#0f172a", "color": "#fff", "border": "none",
                                       "borderRadius": "6px", "padding": "6px 12px", "fontSize": "12px",
                                       "cursor": "pointer"}),
                ],
                style={"display": "flex", "justifyContent": "space-between",
                       "alignItems": "center", "marginBottom": "16px", "marginTop": "16px"},
            ),
            # Zone list with RangeSlider per zone (populated by callback)
            html.Div(id="zones-threshold-list"),
            html.Div(id="zone-modal-container"),
        ]
    )


def _tab_email():
    return html.Div(
        [
            html.Div("Email / Alert",
                     style={"fontSize": "13px", "fontWeight": "700", "marginBottom": "16px", "marginTop": "16px"}),
            html.Div(id="email-settings-form"),
            html.Button("Salva", id="save-email-btn", n_clicks=0,
                        style={"background": "#0f172a", "color": "#fff", "border": "none",
                               "borderRadius": "6px", "padding": "8px 16px", "fontSize": "13px", "cursor": "pointer"}),
            html.Div(id="email-save-result", style={"marginTop": "8px", "fontSize": "12px"}),
        ]
    )


def _tab_general():
    return html.Div(
        [
            html.Div("Impostazioni generali",
                     style={"fontSize": "13px", "fontWeight": "700", "marginBottom": "16px", "marginTop": "16px"}),
            html.Div(
                [
                    html.Label("Nome impianto", style={"fontSize": "12px", "fontWeight": "600"}),
                    dcc.Input(id="setting-app-name", type="text", debounce=True,
                              style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                     "borderRadius": "6px", "fontSize": "13px", "marginBottom": "12px"}),
                    html.Label("Intervallo polling (minuti)", style={"fontSize": "12px", "fontWeight": "600"}),
                    dcc.Input(id="setting-polling-interval", type="number", min=1, max=60, debounce=True,
                              style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                     "borderRadius": "6px", "fontSize": "13px", "marginBottom": "12px"}),
                    html.Label("Archiviazione dati dopo (giorni)", style={"fontSize": "12px", "fontWeight": "600"}),
                    dcc.Input(id="setting-archive-days", type="number", min=30, max=3650, debounce=True,
                              style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                     "borderRadius": "6px", "fontSize": "13px", "marginBottom": "12px"}),
                    html.Div(
                        "Dopo questo numero di giorni, i dati vengono esportati in CSV e rimossi dal database.",
                        style={"fontSize": "11px", "color": "#94a3b8", "marginBottom": "16px"},
                    ),
                ],
                className="mm-card",
                style={"maxWidth": "480px", "marginBottom": "16px"},
            ),
            html.Button("Salva", id="save-general-btn", n_clicks=0,
                        style={"background": "#0f172a", "color": "#fff", "border": "none",
                               "borderRadius": "6px", "padding": "8px 16px", "fontSize": "13px", "cursor": "pointer"}),
            html.Div(id="general-save-result", style={"marginTop": "8px", "fontSize": "12px"}),
        ]
    )


def _tab_demo():
    return html.Div(
        [
            html.Div("Modalità demo",
                     style={"fontSize": "13px", "fontWeight": "700", "marginBottom": "16px", "marginTop": "16px"}),
            html.Div(id="demo-settings-content"),
        ]
    )
