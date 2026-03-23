"""medMonitor — Plotly Dash frontend entry point."""

import dash
import dash_bootstrap_components as dbc
from dash import html

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.SLATE],
    title="medMonitor",
    update_title="medMonitor — Aggiornamento...",
    suppress_callback_exceptions=True,
)

server = app.server

app.layout = dbc.Container(
    [
        dbc.Navbar(
            dbc.Container(
                dbc.NavbarBrand("medMonitor", className="ms-2"),
                fluid=True,
            ),
            color="dark",
            dark=True,
            className="mb-4",
        ),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H4("Sistema in configurazione", className="card-title"),
                            html.P(
                                "Backend API: http://localhost:8000/docs",
                                className="card-text",
                            ),
                            html.P(
                                "Frontend attivo sulla porta 8050.",
                                className="card-text text-muted",
                            ),
                        ]
                    ),
                ),
                width=6,
                className="mx-auto",
            ),
        ),
    ],
    fluid=True,
    className="py-3",
)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
