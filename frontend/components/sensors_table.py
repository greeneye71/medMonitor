"""Compact sensors table for Dashboard."""

from dash import html


def sensors_table(sensors: list[dict]) -> html.Div:
    """
    Args:
        sensors: lista di {id, name, zone, zone_color, temp, battery_pct, last_seen_s}
    """
    if not sensors:
        return html.Div("Nessun sensore rilevato.", style={"color": "#94a3b8", "fontSize": "13px", "padding": "16px"})

    rows = []
    for s in sensors:
        bat = s.get("battery_pct")
        bat_pct = bat if bat is not None else 0
        bat_color = "#22c55e" if bat_pct > 50 else "#f59e0b" if bat_pct > 20 else "#ef4444"

        last = s.get("last_seen_s")
        last_str = f"{last}s fa" if last is not None else "–"
        color = s.get("zone_color", "#64748b")

        rows.append(
            html.Tr([
                html.Td(s.get("id", "?"), style={"fontSize": "11px", "color": "#94a3b8", "fontFamily": "monospace"}),
                html.Td(s.get("name") or s.get("id", "?"), style={"fontSize": "12px"}),
                html.Td(
                    html.Span(
                        s.get("zone", "–"),
                        style={"background": color + "22", "color": color, "borderRadius": "4px",
                               "padding": "1px 6px", "fontSize": "11px", "fontWeight": "600"},
                    )
                ),
                html.Td(
                    f"{s['temp']:.1f}°C" if s.get("temp") is not None else "–",
                    style={"fontSize": "13px", "fontWeight": "600"},
                ),
                html.Td(
                    html.Div(
                        html.Div(style={"width": f"{bat_pct}%", "height": "100%",
                                        "background": bat_color, "borderRadius": "2px"}),
                        title=f"{bat_pct}%",
                        style={"width": "40px", "height": "6px", "background": "#f1f5f9", "borderRadius": "2px"},
                    )
                ),
                html.Td(last_str, style={"fontSize": "11px", "color": "#94a3b8"}),
            ])
        )

    return html.Div(
        html.Table(
            [
                html.Thead(html.Tr([
                    html.Th("ID", style={"fontSize": "10px", "color": "#94a3b8", "fontWeight": "600", "padding": "4px 8px"}),
                    html.Th("Nome"),
                    html.Th("Zona"),
                    html.Th("Temp"),
                    html.Th("Batteria"),
                    html.Th("Ultimo"),
                ])),
                html.Tbody(rows),
            ],
            style={"width": "100%", "borderCollapse": "collapse", "fontSize": "12px"},
        ),
        className="mm-card",
        style={"overflowX": "auto"},
    )
