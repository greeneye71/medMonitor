"""Dashboard callbacks v2 — zone dinamiche, resilienza API."""

from datetime import datetime
from dash import Input, Output, callback, html, ctx
from frontend.components.zone_card import zone_card
from frontend.components.sensors_table import sensors_table
from frontend.components.charts import temperature_line_chart, empty_chart
from frontend.utils import safe_get as _safe_get


@callback(
    Output("dashboard-zone-cards", "children"),
    Output("dashboard-sensors-table", "children"),
    Output("dashboard-updated-ts", "children"),
    Output("dashboard-error-banner", "children"),
    Output("dashboard-error-banner", "style"),
    Input("interval-30s", "n_intervals"),
    Input("dashboard-refresh-btn", "n_clicks"),
)
def update_dashboard(n, _clicks):
    zones, err1 = _safe_get("/api/zones")
    readings, err2 = _safe_get("/api/readings/latest")
    sensors_cfg, err3 = _safe_get("/api/sensors")

    if err1 or err2 or err3:
        error_msg = html.Div(
            f"⚠ Backend non raggiungibile: {err1 or err2 or err3}",
            style={"background": "#fef3c7", "border": "1px solid #f59e0b",
                   "borderRadius": "8px", "padding": "10px 16px",
                   "fontSize": "13px", "color": "#92400e", "marginBottom": "16px"},
        )
        return [], html.Div("–"), "–", error_msg, {"display": "block"}

    # Build zone cards
    readings_map = {r["sensor_id"]: r for r in (readings or [])}
    sensor_map = {s["id"]: s for s in (sensors_cfg or [])}

    zone_cards = []
    all_sensor_rows = []

    for zone in (zones or []):
        zone_name = zone["name"]
        zone_color = zone.get("color", "#64748b")
        t_min = zone.get("threshold_min", 0)
        t_max = zone.get("threshold_max", 30)

        zone_sensors = [s for s in sensor_map.values() if s.get("zone") == zone_name]
        sensor_data = []
        temps = []
        for s in zone_sensors:
            r = readings_map.get(s["id"], {})
            t = r.get("temperature")
            if t is not None:
                temps.append(t)
            sensor_data.append({
                "id": s["id"], "name": s.get("name", s["id"]),
                "temp": t, "battery_pct": r.get("battery"),
            })
            all_sensor_rows.append({
                "id": s["id"], "name": s.get("name", s["id"]),
                "zone": zone_name, "zone_color": zone_color,
                "temp": t, "battery_pct": r.get("battery"),
                "last_seen_s": r.get("age_seconds"),
            })

        avg_temp = sum(temps) / len(temps) if temps else None
        if avg_temp is None:
            status = "OK"
        elif t_min <= avg_temp <= t_max:
            status = "OK"
        elif avg_temp < t_min - 5 or avg_temp > t_max + 5:
            status = "CRITICAL"
        else:
            status = "WARNING"

        zone_cards.append(zone_card(zone_name, zone_color, status, avg_temp,
                                    sensor_data, t_min, t_max))

    ts = datetime.now().strftime("Aggiornato alle %H:%M:%S")
    return zone_cards, sensors_table(all_sensor_rows), ts, "", {"display": "none"}


@callback(
    Output("dashboard-chart", "figure"),
    Input("interval-30s", "n_intervals"),
    Input("chart-range-6h", "n_clicks"),
    Input("chart-range-24h", "n_clicks"),
    Input("chart-range-7d", "n_clicks"),
)
def update_chart(n, _6h, _24h, _7d):
    # Determine hours from which button was clicked
    triggered = ctx.triggered_id
    if triggered == "chart-range-6h":
        hours = 6
    elif triggered == "chart-range-7d":
        hours = 168
    else:
        hours = 24  # default: 24h

    # NOTE: hours filtering is future work if /api/readings doesn't support it yet
    readings, err = _safe_get(f"/api/readings?limit=500&hours={hours}")
    if err or not readings:
        return empty_chart("In attesa di dati...")

    thresholds_data, _ = _safe_get("/api/thresholds")
    th = {}
    if isinstance(thresholds_data, dict):
        for sid, s in thresholds_data.get("sensors", {}).items():
            th[sid] = (s.get("effective_min", 0), s.get("effective_max", 30))

    return temperature_line_chart(readings, th)


@callback(
    Output("sidebar-alert-badge", "children"),
    Output("sidebar-alert-badge", "style"),
    Input("interval-60s", "n_intervals"),
)
def update_alert_badge(n):
    base_style = {"background": "#ef4444", "color": "#fff", "borderRadius": "10px",
                  "padding": "0 6px", "fontSize": "10px", "fontWeight": "700"}
    data, err = _safe_get("/api/alerts?acknowledged=false&limit=100")
    if err or data is None:
        return "0", {**base_style, "display": "none"}
    # data may be a list or a dict with "alerts" key — handle both
    items = data if isinstance(data, list) else data.get("alerts", [])
    count = len(items)
    if count == 0:
        return "0", {**base_style, "display": "none"}
    return str(count), {**base_style, "display": "inline"}
