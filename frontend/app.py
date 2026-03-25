"""medMonitor — Plotly Dash frontend entry point."""

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import dash
import dash_bootstrap_components as dbc
from dash import html, Input, Output, callback

from frontend.layout import make_layout

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="medMonitor",
    update_title="medMonitor — Aggiornamento...",
    suppress_callback_exceptions=True,
)

server = app.server
app.layout = make_layout()

# Import callbacks to register them
import frontend.callbacks.dashboard_callbacks   # noqa: F401
import frontend.callbacks.history_callbacks     # noqa: F401
import frontend.callbacks.alerts_callbacks      # noqa: F401
import frontend.callbacks.settings_callbacks    # noqa: F401
import frontend.callbacks.system_callbacks      # noqa: F401


@callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def display_page(pathname):
    if pathname == "/" or pathname is None:
        from frontend.pages.dashboard import layout
        return layout()
    elif pathname == "/storico":
        from frontend.pages.history import layout
        return layout()
    elif pathname == "/allarmi":
        from frontend.pages.alerts import layout
        return layout()
    elif pathname == "/impostazioni":
        from frontend.pages.settings import layout
        return layout()
    elif pathname == "/sistema":
        from frontend.pages.system import layout
        return layout()
    else:
        return html.Div(
            [
                html.H4("404 — Pagina non trovata"),
                html.P(f"Il percorso '{pathname}' non esiste."),
            ],
            style={"textAlign": "center", "marginTop": "80px"},
        )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
