"""Demo banner component — shown when demo mode is active."""

import dash_bootstrap_components as dbc
from dash import html


def demo_banner(scenario: str = "", speed: str = "", visible: bool = False) -> html.Div:
    """Create demo mode banner.

    Args:
        scenario: Active demo scenario name
        speed: Simulation speed (e.g., "10x")
        visible: Whether to show the banner
    """
    if not visible:
        return html.Div()

    return dbc.Alert(
        [
            html.Strong("MODALITA DEMO"),
            html.Span(f" — Scenario: {scenario} — Velocita: {speed}", className="ms-2"),
            dbc.Button(
                "Ferma demo",
                id="btn-stop-demo",
                color="warning",
                size="sm",
                className="ms-3",
            ),
        ],
        color="warning",
        className="mb-0 rounded-0 text-center py-2",
        dismissable=False,
    )
