"""Dashboard page — real-time temperature monitoring."""

import dash_bootstrap_components as dbc
from dash import html, dcc

from frontend.components.metric_card import metric_card
from frontend.components.charts import empty_chart


def layout():
    """Create dashboard page layout."""
    return html.Div(
        [
            html.H4("Dashboard", className="mb-3"),

            # Metric cards row
            dbc.Row(
                [
                    dbc.Col(html.Div(id="metric-fridge"), md=3),
                    dbc.Col(html.Div(id="metric-freezer"), md=3),
                    dbc.Col(html.Div(id="metric-alerts"), md=3),
                    dbc.Col(html.Div(id="metric-sensors"), md=3),
                ],
                className="mb-3",
            ),

            # Zone cards row
            dbc.Row(
                [
                    dbc.Col(html.Div(id="zone-card-fridge"), md=6),
                    dbc.Col(html.Div(id="zone-card-freezer"), md=6),
                ],
                className="mb-3",
            ),

            # Temperature chart
            dbc.Card(
                dbc.CardBody(
                    dcc.Graph(
                        id="chart-24h",
                        figure=empty_chart("In attesa di dati..."),
                        config={"displayModeBar": False},
                        style={"height": "350px"},
                    ),
                ),
                className="mb-3",
            ),

            # Sensors table
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H6("Sensori", className="mb-2"),
                        html.Div(id="sensors-table"),
                    ]
                ),
            ),
        ]
    )
