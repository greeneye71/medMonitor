"""Main layout — navbar + sidebar for multi-page app."""

import dash_bootstrap_components as dbc
from dash import html, dcc

SIDEBAR_ITEMS = [
    {"label": "Dashboard", "href": "/", "icon": "mdi:view-dashboard"},
    {"label": "Storico", "href": "/storico", "icon": "mdi:chart-line"},
    {"label": "Allarmi", "href": "/allarmi", "icon": "mdi:bell-alert"},
    {"label": "Impostazioni", "href": "/impostazioni", "icon": "mdi:cog"},
]


def make_navbar():
    """Create top navigation bar."""
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand(
                    [
                        html.I(className="me-2"),
                        "medMonitor",
                    ],
                    className="ms-2 fw-bold",
                ),
                dbc.Nav(
                    [
                        html.Span(
                            [
                                html.Span("●", id="system-status-dot", className="me-1 status-ok"),
                                html.Span("Sistema attivo", id="system-status-text"),
                            ],
                            className="me-3 small",
                        ),
                        dbc.Badge(
                            "0 allarmi",
                            id="navbar-alert-badge",
                            color="success",
                            className="me-2",
                        ),
                    ],
                    className="ms-auto d-flex align-items-center",
                    navbar=True,
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        sticky="top",
    )


def make_sidebar():
    """Create left sidebar with navigation links."""
    items = []
    for item in SIDEBAR_ITEMS:
        items.append(
            dbc.NavLink(
                item["label"],
                href=item["href"],
                active="exact",
                className="sidebar-link",
            )
        )
        if item["label"] == "Allarmi":
            items.append(html.Hr(className="my-2"))

    return html.Div(
        [
            dbc.Nav(items, vertical=True, pills=True, className="flex-column"),
        ],
        className="sidebar bg-dark p-3",
        style={
            "width": "160px",
            "position": "fixed",
            "top": "56px",
            "left": 0,
            "bottom": 0,
            "overflowY": "auto",
        },
    )


def make_layout():
    """Create the full page layout with navbar, sidebar, and content area."""
    return html.Div(
        [
            make_navbar(),
            html.Div(
                id="demo-banner-container",
            ),
            html.Div(
                [
                    make_sidebar(),
                    html.Div(
                        [
                            dcc.Location(id="url", refresh=False),
                            html.Div(id="page-content", className="p-4"),
                        ],
                        style={"marginLeft": "160px"},
                    ),
                ],
            ),
            dcc.Interval(id="interval-30s", interval=30_000, n_intervals=0),
            dcc.Interval(id="interval-60s", interval=60_000, n_intervals=0),
        ]
    )
