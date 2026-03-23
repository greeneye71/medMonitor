"""Settings page callbacks — save config, test email, manage demo."""

import logging

import requests
from dash import Input, Output, State, callback, no_update

logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000/api"


def _post(endpoint, json_data=None):
    try:
        resp = requests.post(f"{API_BASE}{endpoint}", json=json_data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("API POST %s failed: %s", endpoint, e)
        return {"status": "error", "message": str(e)}


def _patch(endpoint, json_data=None):
    try:
        resp = requests.patch(f"{API_BASE}{endpoint}", json=json_data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("API PATCH %s failed: %s", endpoint, e)
        return {"status": "error", "message": str(e)}


def _get(endpoint):
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("API GET %s failed: %s", endpoint, e)
        return {}


@callback(
    Output("settings-toast", "is_open", allow_duplicate=True),
    Input("btn-save-general", "n_clicks"),
    State("setting-app-name", "value"),
    State("setting-theme", "value"),
    State("setting-log-level", "value"),
    prevent_initial_call=True,
)
def save_general(_n, app_name, theme, log_level):
    _patch("/config", {
        "app_name": app_name,
        "app_theme": theme,
        "log_level": log_level,
    })
    return True


@callback(
    Output("settings-toast", "is_open", allow_duplicate=True),
    Input("btn-save-thresholds", "n_clicks"),
    State("slider-fridge-defaults", "value"),
    State("slider-freezer-defaults", "value"),
    prevent_initial_call=True,
)
def save_thresholds(_n, fridge_range, freezer_range):
    _patch("/thresholds/defaults", {
        "fridge": {"min": fridge_range[0], "max": fridge_range[1]},
        "freezer": {"min": freezer_range[0], "max": freezer_range[1]},
    })
    return True


@callback(
    Output("settings-toast", "is_open", allow_duplicate=True),
    Input("btn-save-system", "n_clicks"),
    State("setting-polling-interval", "value"),
    State("setting-cooldown", "value"),
    State("setting-retention", "value"),
    prevent_initial_call=True,
)
def save_system(_n, polling, cooldown, retention):
    _patch("/config", {
        "polling_interval_minutes": polling,
        "alert_cooldown_minutes": cooldown,
        "data_retention_days": retention,
    })
    return True


@callback(
    Output("badge-smtp-status", "children"),
    Output("badge-smtp-status", "color"),
    Input("btn-test-smtp", "n_clicks"),
    State("setting-smtp-user", "value"),
    prevent_initial_call=True,
)
def test_smtp(_n, smtp_user):
    if not smtp_user:
        return "Compila i campi SMTP", "warning"
    result = _post("/config/test-email", {"email": smtp_user})
    if result.get("status") == "ok":
        return "OK", "success"
    return "Errore", "danger"


@callback(
    Output("badge-imap-status", "children"),
    Output("badge-imap-status", "color"),
    Input("btn-test-imap", "n_clicks"),
    prevent_initial_call=True,
)
def test_imap(_n):
    result = _post("/config/test-imap")
    if result.get("status") == "ok":
        return "OK", "success"
    return "Errore", "danger"


@callback(
    Output("demo-status-text", "children"),
    Input("btn-start-demo", "n_clicks"),
    State("setting-demo-scenario", "value"),
    State("setting-demo-speed", "value"),
    prevent_initial_call=True,
)
def start_demo(_n, scenario, speed):
    result = _post("/demo/start", {"scenario": scenario, "speed": speed})
    if result.get("status") == "ok":
        return f"Demo avviata: {scenario} a {speed}"
    return f"Errore: {result.get('message', 'sconosciuto')}"


@callback(
    Output("demo-status-text", "children", allow_duplicate=True),
    Input("btn-stop-demo-settings", "n_clicks"),
    prevent_initial_call=True,
)
def stop_demo(_n):
    _post("/demo/stop")
    return "Demo fermata"


@callback(
    Output("demo-status-text", "children", allow_duplicate=True),
    Input("btn-reset-demo", "n_clicks"),
    prevent_initial_call=True,
)
def reset_demo(_n):
    result = _post("/demo/reset")
    msg = result.get("message", "Dati demo cancellati")
    return msg
