"""Alerts page callbacks — filter and update AG Grid."""

import logging

import requests
from dash import Input, Output, State, callback, no_update

logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000/api"


def _fetch(endpoint, params=None):
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("API fetch %s failed: %s", endpoint, e)
        return []


@callback(
    Output("alerts-grid", "rowData"),
    Output("badge-warning-count", "children"),
    Output("badge-critical-count", "children"),
    Input("btn-alerts-filter", "n_clicks"),
    Input("interval-60s", "n_intervals"),
    State("alerts-zone-filter", "value"),
    State("alerts-level-filter", "value"),
    State("alerts-date-range", "start_date"),
    State("alerts-date-range", "end_date"),
)
def update_alerts(_n_clicks, _n_interval, zone, level, start_date, end_date):
    params = {"limit": 500}
    if zone:
        params["zone"] = zone
    if level:
        params["level"] = level
    if start_date:
        params["from"] = start_date
    if end_date:
        params["to"] = end_date

    alerts = _fetch("/alerts", params)

    # Format data for AG Grid
    rows = []
    for a in alerts:
        rows.append({
            "timestamp": str(a.get("timestamp", ""))[:19],
            "zone": a.get("zone", ""),
            "sensor_id": a.get("sensor_id", ""),
            "temperature": a.get("temperature", 0),
            "level": a.get("level", ""),
            "message": a.get("message", ""),
        })

    warning_count = sum(1 for r in rows if r["level"] == "WARNING")
    critical_count = sum(1 for r in rows if r["level"] == "CRITICAL")

    return (
        rows,
        f"{warning_count} WARNING",
        f"{critical_count} CRITICAL",
    )


@callback(
    Output("navbar-alert-badge", "children"),
    Output("navbar-alert-badge", "color"),
    Input("interval-60s", "n_intervals"),
)
def update_navbar_badge(_n):
    alerts = _fetch("/alerts", {"limit": 50})
    critical = sum(1 for a in alerts if a.get("level") == "CRITICAL")

    if critical > 0:
        return f"{critical} allarmi", "danger"
    elif alerts:
        return f"{len(alerts)} avvisi", "warning"
    return "0 allarmi", "success"
