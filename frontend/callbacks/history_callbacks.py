"""History page callbacks — search, chart, stats, CSV export."""

import io
import logging
from datetime import datetime

import requests
from dash import Input, Output, State, callback, no_update, dcc

from frontend.components.charts import temperature_line_chart, empty_chart

logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000/api"


def _fetch(endpoint, params=None):
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("API fetch %s failed: %s", endpoint, e)
        return []


@callback(
    Output("history-sensor-filter", "options"),
    Input("interval-60s", "n_intervals"),
)
def populate_sensor_filter(_n):
    latest = _fetch("/readings/latest")
    if not latest:
        return []
    return [{"label": r.get("sensor_id", ""), "value": r.get("sensor_id", "")} for r in latest]


@callback(
    Output("history-chart", "figure"),
    Output("history-stats", "children"),
    Input("btn-history-search", "n_clicks"),
    State("history-date-range", "start_date"),
    State("history-date-range", "end_date"),
    State("history-zone-filter", "value"),
    State("history-sensor-filter", "value"),
    prevent_initial_call=True,
)
def search_history(_n, start_date, end_date, zone, sensors):
    params = {"limit": 5000}
    if start_date:
        params["from"] = start_date
    if end_date:
        params["to"] = end_date
    if zone:
        params["zone"] = zone

    readings = _fetch("/readings", params)

    if sensors:
        readings = [r for r in readings if r.get("sensor_id") in sensors]

    if not readings:
        from dash import html
        return empty_chart("Nessun dato nel periodo selezionato"), html.P("—", className="text-muted")

    # Get thresholds for bands
    thresholds_data = _fetch("/thresholds")
    th = {}
    if isinstance(thresholds_data, dict):
        for sid, s in thresholds_data.get("sensors", {}).items():
            th[sid] = (s.get("effective_min", 0), s.get("effective_max", 30))

    fig = temperature_line_chart(readings, th, title="Storico temperature")

    # Calculate statistics
    from dash import html
    import dash_bootstrap_components as dbc

    temps = [r["temperature"] for r in readings]
    stats = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Media", className="text-muted"),
            html.Div(f"{sum(temps)/len(temps):.1f}°C", className="fs-5 fw-bold"),
        ]), className="text-center"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Min", className="text-muted"),
            html.Div(f"{min(temps):.1f}°C", className="fs-5 fw-bold text-info"),
        ]), className="text-center"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Max", className="text-muted"),
            html.Div(f"{max(temps):.1f}°C", className="fs-5 fw-bold text-danger"),
        ]), className="text-center"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Letture", className="text-muted"),
            html.Div(str(len(temps)), className="fs-5 fw-bold"),
        ]), className="text-center"), md=3),
    ])

    return fig, stats


@callback(
    Output("download-csv", "data"),
    Input("btn-export-csv", "n_clicks"),
    State("history-date-range", "start_date"),
    State("history-date-range", "end_date"),
    State("history-zone-filter", "value"),
    prevent_initial_call=True,
)
def export_csv(_n, start_date, end_date, zone):
    params = {"limit": 10000}
    if start_date:
        params["from"] = start_date
    if end_date:
        params["to"] = end_date
    if zone:
        params["zone"] = zone

    readings = _fetch("/readings", params)
    if not readings:
        return no_update

    # Build CSV
    lines = ["timestamp,zone,sensor_id,temperature,humidity,battery"]
    for r in readings:
        lines.append(
            f"{r.get('timestamp','')},{r.get('zone','')},{r.get('sensor_id','')},"
            f"{r.get('temperature','')},{r.get('humidity','')},{r.get('battery','')}"
        )

    csv_content = "\n".join(lines)
    return dcc.send_string(csv_content, filename="medMonitor_export.csv")
