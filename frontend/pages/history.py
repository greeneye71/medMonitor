"""History page — date range temperature history with CSV export."""

import dash_bootstrap_components as dbc
from dash import html, dcc

from frontend.components.charts import empty_chart


def layout():
    """Create history page layout."""
    return html.Div(
        [
            html.H4("Storico temperature", className="mb-3"),

            # Filters
            dbc.Card(
                dbc.CardBody(
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Periodo", className="small"),
                                    dcc.DatePickerRange(
                                        id="history-date-range",
                                        display_format="DD/MM/YYYY",
                                        className="w-100",
                                    ),
                                ],
                                md=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Zona", className="small"),
                                    dbc.Select(
                                        id="history-zone-filter",
                                        options=[
                                            {"label": "Tutte", "value": ""},
                                            {"label": "Frigorifero", "value": "fridge"},
                                            {"label": "Freezer", "value": "freezer"},
                                        ],
                                        value="",
                                    ),
                                ],
                                md=2,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Sensori", className="small"),
                                    dcc.Dropdown(
                                        id="history-sensor-filter",
                                        multi=True,
                                        placeholder="Tutti i sensori",
                                    ),
                                ],
                                md=3,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("\u00A0", className="small d-block"),
                                    dbc.Button(
                                        "Cerca",
                                        id="btn-history-search",
                                        color="primary",
                                        className="me-2",
                                    ),
                                    dbc.Button(
                                        "Esporta CSV",
                                        id="btn-export-csv",
                                        color="secondary",
                                        outline=True,
                                    ),
                                ],
                                md=3,
                                className="d-flex align-items-end",
                            ),
                        ],
                    ),
                ),
                className="mb-3",
            ),

            # Chart
            dbc.Card(
                dbc.CardBody(
                    dcc.Graph(
                        id="history-chart",
                        figure=empty_chart("Seleziona un periodo e clicca Cerca"),
                        config={"displayModeBar": True},
                        style={"height": "400px"},
                    ),
                ),
                className="mb-3",
            ),

            # Statistics
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H6("Statistiche periodo", className="mb-2"),
                        html.Div(id="history-stats"),
                    ]
                ),
            ),

            # CSV download component
            dcc.Download(id="download-csv"),
        ]
    )
