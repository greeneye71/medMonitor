"""Service status card component."""

from dash import html


def service_card(
    service_id: str,
    display_name: str,
    status: str,
    uptime_str: str,
    details: str = "",
    supports_stop: bool = True,
) -> html.Div:
    dot_class = {
        "connected": "mm-dot-ok", "running": "mm-dot-ok", "ok": "mm-dot-ok",
        "stopping": "mm-dot-warn", "degraded": "mm-dot-warn",
        "disconnected": "mm-dot-error", "stopped": "mm-dot-error", "error": "mm-dot-error",
    }.get(status, "mm-dot-warn")

    # disabled=False must be set explicitly so pattern-matching Output("disabled") works in Dash
    buttons = [
        html.Button(
            "Restart",
            id={"type": "service-btn", "service": service_id, "action": "restart"},
            n_clicks=0,
            disabled=False,
            style={"background": "#f1f5f9", "border": "1px solid #e2e8f0", "borderRadius": "6px",
                   "padding": "3px 10px", "fontSize": "11px", "cursor": "pointer", "marginLeft": "4px"},
        )
    ]
    if supports_stop:
        buttons.insert(0, html.Button(
            "Stop",
            id={"type": "service-btn", "service": service_id, "action": "stop"},
            n_clicks=0,
            disabled=False,
            style={"background": "#fee2e2", "color": "#991b1b", "border": "none", "borderRadius": "6px",
                   "padding": "3px 10px", "fontSize": "11px", "cursor": "pointer"},
        ))

    return html.Div(
        [
            html.Div(
                [
                    html.Div([
                        html.Span("", className=f"mm-status-dot {dot_class}", style={"marginRight": "8px"}),
                        html.Span(display_name, style={"fontWeight": "600", "fontSize": "13px"}),
                    ], style={"display": "flex", "alignItems": "center"}),
                    html.Div(buttons, style={"display": "flex"}),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
            ),
            html.Div(uptime_str, style={"fontSize": "11px", "color": "#94a3b8", "marginTop": "4px"}),
            html.Div(details, style={"fontSize": "10px", "color": "#64748b", "marginTop": "2px"}) if details else None,
        ],
        className="mm-card",
        style={"marginBottom": "12px"},
    )
