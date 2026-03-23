"""Zone card component — temperature display with gauge bar."""

import dash_bootstrap_components as dbc
from dash import html


def zone_card(
    zone: str,
    temperature: float,
    temp_min: float,
    temp_max: float,
    status: str = "ok",
    sensor_id: str = "",
    has_override: bool = False,
) -> dbc.Card:
    """Create a zone card with gauge bar and status indicator.

    Args:
        zone: Zone name (e.g., "Frigorifero", "Freezer")
        temperature: Current temperature
        temp_min: Effective minimum threshold
        temp_max: Effective maximum threshold
        status: "ok", "warning", or "critical"
        sensor_id: Sensor identifier
        has_override: Whether sensor has individual thresholds
    """
    color_map = {
        "ok": "#1D9E75",
        "warning": "#BA7517",
        "critical": "#E24B4A",
    }
    color = color_map.get(status, color_map["ok"])
    border_class = f"border-{status}"

    # Gauge bar: calculate fill percentage
    total_range = temp_max - temp_min
    if total_range > 0:
        fill_pct = max(0, min(100, (temperature - temp_min) / total_range * 100))
    else:
        fill_pct = 50

    override_badge = html.Span(
        "★", title="Soglie individuali", className="ms-1 text-warning",
    ) if has_override else None

    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Span(
                            status.upper(),
                            className=f"badge bg-{'success' if status == 'ok' else 'warning' if status == 'warning' else 'danger'}",
                        ),
                        html.Span(
                            [zone, override_badge],
                            className="fw-bold ms-2",
                        ),
                    ],
                    className="d-flex align-items-center mb-2",
                ),
                html.Div(
                    f"{temperature:.1f}°C",
                    className="fs-2 fw-bold",
                    style={"color": color},
                ),
                # Gauge bar
                html.Div(
                    html.Div(
                        style={
                            "width": f"{fill_pct}%",
                            "height": "6px",
                            "backgroundColor": color,
                            "borderRadius": "3px",
                            "transition": "width 0.5s ease",
                        },
                    ),
                    style={
                        "width": "100%",
                        "height": "6px",
                        "backgroundColor": "#2d3748",
                        "borderRadius": "3px",
                        "marginTop": "8px",
                    },
                ),
                html.Div(
                    [
                        html.Small(f"{temp_min:.0f}°C", className="text-muted"),
                        html.Small(f"{temp_max:.0f}°C", className="text-muted"),
                    ],
                    className="d-flex justify-content-between mt-1",
                ),
                html.Small(sensor_id, className="text-muted d-block mt-1") if sensor_id else None,
            ]
        ),
        className=f"{border_class}",
        style={"borderLeft": f"3px solid {color}"},
    )
