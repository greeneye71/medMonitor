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
                    {
                        "field": "timestamp",
                        "headerName": "Data/Ora",
                        "sortable": True,
                        "filter": True,
                        "width": 180,
                    },
                    {
                        "field": "zone",
                        "headerName": "Zona",
                        "sortable": True,
                        "filter": True,
                        "width": 120,
                    },
                    {
                        "field": "sensor_id",
                        "headerName": "Sensore",
                        "sortable": True,
                        "filter": True,
                        "width": 180,
                    },
                    {
                        "field": "temperature",
                        "headerName": "Temp (°C)",
                        "sortable": True,
                        "width": 100,
                        "valueFormatter": {"function": "d3.format('.1f')(params.value)"},
                    },
                    {
                        "field": "level",
                        "headerName": "Livello",
                        "sortable": True,
                        "filter": True,
                        "width": 120,
                        "cellStyle": {
                            "styleConditions": [
                                {"condition": "params.value === 'CRITICAL'", "style": {"color": "#E24B4A", "fontWeight": "bold"}},
                                {"condition": "params.value === 'WARNING'", "style": {"color": "#BA7517", "fontWeight": "bold"}},
                            ]
                        },
                    },
                    {
                        "field": "message",
                        "headerName": "Messaggio",
                        "flex": 1,
                        "minWidth": 200,
                    },
                ],
                rowData=[],
                defaultColDef={"resizable": True},
                className="ag-theme-alpine-dark",
                style={"height": "500px"},
                dashGridOptions={
                    "pagination": True,
                    "paginationPageSize": 20,
                    "animateRows": True,
                },
            ),
        ]
    )
