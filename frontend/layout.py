"""medMonitor v2 — Main layout con sidebar SaaS light."""

from dash import html, dcc
import dash_bootstrap_components as dbc

NAV_ITEMS = [
    {"label": "Dashboard",    "href": "/",             "icon": "📊"},
    {"label": "Storico",      "href": "/storico",      "icon": "📅"},
    {"label": "Allarmi",      "href": "/allarmi",      "icon": "🔔"},
    {"label": "Impostazioni", "href": "/impostazioni", "icon": "⚙️"},
    {"label": "Sistema",      "href": "/sistema",      "icon": "🖥️"},
]


def _nav_item(label: str, href: str, icon: str) -> html.A:
    extra = []
    if label == "Allarmi":
        extra = [
            html.Span(
                "0",
                id="sidebar-alert-badge",
                style={
                    "background": "#ef4444",
                    "color": "#fff",
                    "borderRadius": "10px",
                    "padding": "0 6px",
                    "fontSize": "10px",
                    "fontWeight": "700",
                    "display": "none",
                },
            )
        ]
    return html.A(
        [html.Span(icon, style={"marginRight": "8px"}), label] + extra,
        href=href,
        id=f"nav-{href.strip('/') or 'dashboard'}",
        className="mm-nav-item",
    )


def make_sidebar() -> html.Div:
    return html.Div(
        [
            html.Div("medMonitor", className="mm-sidebar-brand"),
            html.Hr(style={"borderColor": "#1e293b", "margin": "0 0 8px"}),
            html.Div(
                [_nav_item(i["label"], i["href"], i["icon"]) for i in NAV_ITEMS],
                style={"flex": 1},
            ),
            html.Div(
                [
                    html.Hr(style={"borderColor": "#1e293b", "margin": "8px 0"}),
                    html.Div(
                        [
                            html.Span(
                                "",
                                id="dot-mqtt",
                                className="mm-status-dot mm-dot-ok",
                                title="MQTT",
                                style={"marginRight": "4px"},
                            ),
                            html.Span(
                                "",
                                id="dot-scheduler",
                                className="mm-status-dot mm-dot-ok",
                                title="Scheduler",
                                style={"marginRight": "4px"},
                            ),
                            html.Span(
                                "",
                                id="dot-db",
                                className="mm-status-dot mm-dot-ok",
                                title="Database",
                            ),
                        ],
                        style={
                            "padding": "8px 16px 12px",
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                ]
            ),
        ],
        className="mm-sidebar",
    )


def make_layout() -> html.Div:
    return html.Div(
        [
            make_sidebar(),
            html.Div(
                [
                    dcc.Location(id="url", refresh=False),
                    html.Div(id="demo-banner-container"),
                    html.Div(id="page-content"),
                ],
                className="mm-main",
            ),
            # Intervals — globali, sempre attivi
            dcc.Interval(id="interval-5s",  interval=5_000,  n_intervals=0),
            dcc.Interval(id="interval-30s", interval=30_000, n_intervals=0),
            dcc.Interval(id="interval-60s", interval=60_000, n_intervals=0),
        ]
    )
