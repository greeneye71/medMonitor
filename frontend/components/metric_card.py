"""Metric card component — summary statistic display."""

import dash_bootstrap_components as dbc
from dash import html


def metric_card(title: str, value: str, color: str = "#1D9E75", icon: str = "") -> dbc.Card:
    """Create a compact metric card.

    Args:
        title: Card label (e.g., "Frigorifero", "Allarmi attivi")
        value: Display value (e.g., "4.2°C", "0")
        color: Value color hex
        icon: Optional icon text
    """
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Span(icon, className="me-1") if icon else None,
                        html.Small(title, className="text-muted"),
                    ],
                    className="mb-1",
                ),
                html.Div(
                    value,
                    className="fs-4 fw-bold",
                    style={"color": color},
                ),
            ],
            className="py-2 px-3",
        ),
        className="h-100",
    )
