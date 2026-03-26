"""Zone card v2 — Modern SaaS Light design."""

from dash import html


def zone_card(zone_name: str, zone_color: str, status: str,
              temp: float | None, sensors: list[dict],
              threshold_min: float, threshold_max: float) -> html.Div:
    """
    Args:
        sensors: lista di {name, temp, battery_pct}
    """
    status_class = {"OK": "mm-badge-ok", "WARNING": "mm-badge-warn", "CRITICAL": "mm-badge-critical"}.get(status, "mm-badge-info")
    card_class = {"OK": "mm-card-ok", "WARNING": "mm-card-warn", "CRITICAL": "mm-card-critical"}.get(status, "")
    temp_class = {"OK": "mm-temp-ok", "WARNING": "mm-temp-warn", "CRITICAL": "mm-temp-critical"}.get(status, "")

    temp_str = f"{temp:.1f}°C" if temp is not None else "–"

    # Progress bar position
    if temp is not None and threshold_max > threshold_min:
        pct = max(0, min(100, (temp - threshold_min) / (threshold_max - threshold_min) * 100))
    else:
        pct = 0

    sensor_rows = []
    for s in sensors:
        bat = s.get("battery_pct")
        bat_str = f"🔋 {bat}%" if bat is not None else ""
        sensor_rows.append(
            html.Div(
                [
                    html.Span(s.get("name", s.get("id", "?")), style={"fontSize": "11px", "color": "#374151"}),
                    html.Span(
                        f"{s['temp']:.1f}°C" if s.get("temp") is not None else "–",
                        style={"fontSize": "11px", "color": "#64748b", "marginLeft": "6px"},
                    ),
                    html.Span(bat_str, style={"fontSize": "10px", "color": "#94a3b8", "marginLeft": "6px"}),
                ],
                style={"display": "flex", "alignItems": "center", "padding": "2px 0"},
            )
        )

    return html.Div(
        [
            html.Div(
                [
                    html.Span(zone_name.upper(), style={"fontSize": "11px", "fontWeight": "600", "color": "#64748b"}),
                    html.Span(status, className=status_class),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "8px"},
            ),
            html.Div(temp_str, style={"fontSize": "36px", "fontWeight": "800", "lineHeight": "1"}, className=temp_class),
            html.Div(sensor_rows, style={"margin": "8px 0"}),
            # Progress bar
            html.Div(
                html.Div(
                    style={"width": f"{pct}%", "height": "100%", "background": zone_color, "borderRadius": "2px", "transition": "width 0.5s"},
                ),
                style={"height": "4px", "background": "#f1f5f9", "borderRadius": "2px", "marginTop": "8px"},
            ),
            html.Div(
                [
                    html.Span(f"{threshold_min}°C", style={"fontSize": "10px", "color": "#94a3b8"}),
                    html.Span(f"{threshold_max}°C", style={"fontSize": "10px", "color": "#94a3b8"}),
                ],
                style={"display": "flex", "justifyContent": "space-between", "marginTop": "3px"},
            ),
        ],
        className=f"mm-card {card_class}",
        style={"borderLeft": f"4px solid {zone_color}"},
    )
