"""Alerts page — AG Grid alert table with filtering."""

import dash_bootstrap_components as dbc
from dash import html, dcc
import dash_ag_grid as dag


def layout():
    """Create alerts page layout."""
    return html.Div(
        [
            html.H4("Storico allarmi", className="mb-3"),

            # Filters
            dbc.Card(
                dbc.CardBody(
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Zona", className="small"),
                                    dbc.Select(
                                        id="alerts-zone-filter",
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
                                    dbc.Label("Livello", className="small"),
                                    dbc.Select(
                                        id="alerts-level-filter",
                                        options=[
                                            {"label": "Tutti", "value": ""},
                                            {"label": "WARNING", "value": "WARNING"},
                                            {"label": "CRITICAL", "value": "CRITICAL"},
                                        ],
                                        value="",
                                    ),
                                ],
                                md=2,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Periodo", className="small"),
                                    dcc.DatePickerRange(
                                        id="alerts-date-range",
                                        display_format="DD/MM/YYYY",
                                        className="w-100",
                                    ),
                                ],
                                md=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("\u00A0", className="small d-block"),
                                    dbc.Button(
                                        "Filtra",
                                        id="btn-alerts-filter",
                                        color="primary",
                                    ),
                                ],
                                md=2,
                                className="d-flex align-items-end",
                            ),
                        ],
                    ),
                ),
                className="mb-3",
            ),

            # Alert count badges
            html.Div(
                [
                    dbc.Badge("0 WARNING", id="badge-warning-count", color="warning", className="me-2 fs-6"),
                    dbc.Badge("0 CRITICAL", id="badge-critical-count", color="danger", className="fs-6"),
                ],
                className="mb-3",
            ),

            # AG Grid table
            dag.AgGrid(
                id="alerts-grid",
                columnDefs=[
                    {"field": "timestamp",    "headerName": "Data/Ora",  "width": 150},
                    {"field": "zone",         "headerName": "Zona",       "width": 120},
                    {"field": "sensor_id",    "headerName": "Sensore",    "width": 120},
                    {"field": "temperature",  "headerName": "Temp (°C)",  "width": 100},
                    {"field": "level",        "headerName": "Livello",    "width": 100},
                    {"field": "duration_min", "headerName": "Durata",     "width": 90},
                    {"field": "message",      "headerName": "Messaggio",  "flex": 1},
                ],
                rowData=[],
                defaultColDef={"resizable": True},
                className="ag-theme-quartz",
                style={"height": "500px"},
                rowClassRules={
                    "alert-row-critical": "params.data.level === 'CRITICAL'",
                    "alert-row-warning":  "params.data.level === 'WARNING'",
                },
                dashGridOptions={"pagination": True, "paginationPageSize": 25},
            ),
        ]
    )
