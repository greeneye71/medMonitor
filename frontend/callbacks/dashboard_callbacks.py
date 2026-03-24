"""Dashboard callbacks — update metrics, zone cards, charts every 30s."""

import logging

import requests
from dash import Input, Output, html, callback, no_update
import dash_bootstrap_components as dbc

from frontend.components.metric_card import metric_card
from frontend.components.zone_card import zone_card
from frontend.components.demo_banner import demo_banner
from frontend.components.charts import temperature_line_chart, empty_chart

logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000/api"


def _fetch(endpoint: str, params: dict | None = None):
    """Fetch from backend API, return JSON or empty list on error."""
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("API fetch %s failed: %s", endpoint, e)
        return []


@callback(
    Output("metric-fridge", "children"),
    Output("metric-freezer", "children"),
    Output("metric-alerts", "children"),
    Output("metric-sensors", "children"),
    Input("interval-30s", "n_intervals"),
)
def update_metrics(_n):
    latest = _fetch("/readings/latest")
    alerts = _fetch("/alerts", {"limit": 100})

    fridge_temp = "—"
    freezer_temp = "—"
    fridge_color = "#6c757d"
    freezer_color = "#6c757d"

    for r in latest:
        if r.get("zone") == "fridge":
            fridge_temp = f"{r['temperature']:.1f}°C"
            fridge_color = "#1D9E75"
        elif r.get("zone") == "freezer":
            freezer_temp = f"{r['temperature']:.1f}°C"
            freezer_color = "#1D9E75"

    active_alerts = len([a for a in alerts if a.get("level") == "CRITICAL"])
    alert_color = "#E24B4A" if active_alerts > 0 else "#1D9E75"

    return (
        metric_card("Frigorifero", fridge_temp, fridge_color),
        metric_card("Freezer", freezer_temp, freezer_color),
        metric_card("Allarmi attivi", str(active_alerts), alert_color),
        metric_card("Sensori online", str(len(latest)), "#3B82F6"),
    )


@callback(
    Output("zone-card-fridge", "children"),
    Output("zone-card-freezer", "children"),
    Input("interval-30s", "n_intervals"),
)
def update_zone_cards(_n):
    latest = _fetch("/readings/latest")
    thresholds_data = _fetch("/thresholds")

    cards = [html.Div(), html.Div()]

    for r in latest:
        zone_name = r.get("zone", "")
        sensor_id = r.get("sensor_id", "")
        temp = r.get("temperature", 0)

        # Get effective thresholds
        eff_min, eff_max = 0.0, 30.0
        has_override = False
        if isinstance(thresholds_data, dict):
            sensors = thresholds_data.get("sensors", {})
            if sensor_id in sensors:
                s = sensors[sensor_id]
                eff_min = s.get("effective_min", 0)
                eff_max = s.get("effective_max", 30)
                has_override = s.get("override", False)
            else:
                defaults = thresholds_data.get("defaults", {})
                d = defaults.get(zone_name, {})
                eff_min = d.get("min", 0)
                eff_max = d.get("max", 30)

        # Determine status
        if temp < eff_min or temp > eff_max:
            status = "critical"
        else:
            status = "ok"

        label = "Frigorifero" if zone_name == "fridge" else "Freezer"
        card = zone_card(label, temp, eff_min, eff_max, status, sensor_id, has_override)

        if zone_name == "fridge":
            cards[0] = card
        else:
            cards[1] = card

    return cards[0], cards[1]


@callback(
    Output("chart-24h", "figure"),
    Input("interval-30s", "n_intervals"),
)
def update_chart(_n):
    readings = _fetch("/readings", {"limit": 500})
    if not readings:
        return empty_chart("In attesa di dati...")

    thresholds_data = _fetch("/thresholds")
    th = {}
    if isinstance(thresholds_data, dict):
        for sid, s in thresholds_data.get("sensors", {}).items():
            th[sid] = (s.get("effective_min", 0), s.get("effective_max", 30))

    return temperature_line_chart(readings, th)


@callback(
    Output("sensors-table", "children"),
    Input("interval-30s", "n_intervals"),
)
def update_sensors_table(_n):
    latest = _fetch("/readings/latest")
    if not latest:
        return html.P("Nessun sensore rilevato", className="text-muted")

    rows = []
    for r in latest:
        status_color = "#1D9E75"
        battery_text = f"{r['battery']}%" if r.get("battery") is not None else "—"

        rows.append(
            html.Tr([
                html.Td(html.Span("●", style={"color": status_color})),
                html.Td(r.get("sensor_id", "")),
                html.Td(r.get("zone", "")),
                html.Td(f"{r['temperature']:.1f}°C"),
                html.Td(battery_text),
                html.Td(str(r.get("timestamp", ""))[:19]),
            ])
        )

    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("", style={"width": "30px"}),
                html.Th("Sensore"),
                html.Th("Zona"),
                html.Th("Temperatura"),
                html.Th("Batteria"),
                html.Th("Ultimo aggiornamento"),
            ])),
            html.Tbody(rows),
        ],
        bordered=True,
        hover=True,
        responsive=True,
        className="table-dark",
    )


@callback(
    Output("demo-banner-container", "children"),
    Input("interval-30s", "n_intervals"),
)
def update_demo_banner(_n):
    data = _fetch("/demo/status")
    if isinstance(data, dict) and data.get("active"):
        return demo_banner(
            scenario=data.get("scenario", ""),
            speed=data.get("speed", ""),
            visible=True,
        )
    return html.Div()
