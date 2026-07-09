"""Settings page callbacks — save config, test email, manage demo."""

import logging

import requests
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, no_update, html, dcc, ALL, MATCH, ctx
from frontend.utils import safe_get as _safe_get, safe_post as _safe_post, safe_delete as _safe_delete

logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000/api"
API = "http://localhost:8000"


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
    Output("general-save-result", "children"),
    Input("save-general-btn", "n_clicks"),
    State("setting-app-name", "value"),
    State("setting-polling-interval", "value"),
    State("setting-archive-days", "value"),
    prevent_initial_call=True,
)
def save_general(_n, app_name, polling_interval, archive_days):
    payload = {}
    if app_name is not None:
        payload["app_name"] = app_name
    if polling_interval is not None:
        payload["polling_interval_minutes"] = polling_interval
    if archive_days is not None:
        payload["archive_after_days"] = archive_days  # Bug 3 fix: was data_retention_days
    result = _patch("/config", payload)
    if result.get("status") == "error":
        return html.Div(f"Errore: {result.get('message', 'sconosciuto')}",
                        style={"color": "#ef4444", "fontSize": "12px"})
    return html.Div("✓ Impostazioni salvate.", style={"color": "#22c55e", "fontSize": "12px"})


@callback(
    Output("email-save-result", "children"),
    Input("save-email-btn", "n_clicks"),
    State("setting-smtp-host", "value"),
    State("setting-smtp-user", "value"),
    State("setting-smtp-password", "value"),
    prevent_initial_call=True,
)
def save_email(_n, smtp_host, smtp_user, smtp_password):
    # Bug 4 fix: actually call the API with email config fields
    payload = {}
    if smtp_host is not None:
        payload["smtp_host"] = smtp_host
    if smtp_user is not None:
        payload["smtp_user"] = smtp_user
    if smtp_password is not None:
        payload["smtp_password"] = smtp_password
    if not payload:
        return html.Div("Nessun campo da salvare.", style={"color": "#94a3b8", "fontSize": "12px"})
    result, err = _safe_post("/api/config", payload)
    if err:
        return html.Div(f"Errore: {err}", style={"color": "#ef4444", "fontSize": "12px"})
    return html.Div("✓ Configurazione email aggiornata.", style={"color": "#22c55e", "fontSize": "12px"})


# ── New Impostazioni v2 callbacks ─────────────────────────────────────────────

@callback(
    Output("discovered-sensors-list", "children"),
    Input("interval-60s", "n_intervals"),
    Input("settings-tabs", "active_tab"),
)
def update_discovered(n, active_tab):
    if active_tab != "tab-sensors":
        return no_update
    sensors, err = _safe_get("/api/sensors/discovered")
    if err or not sensors:
        return html.Div("Nessun sensore nuovo rilevato.",
                        style={"color": "#94a3b8", "fontSize": "13px"})
    rows = []
    for s in sensors:
        rows.append(html.Div(
            [
                html.Span(s["sensor_id"], style={"fontFamily": "monospace", "fontSize": "12px",
                                                  "color": "#374151", "marginRight": "8px"}),
                html.Span("NUOVO", className="mm-badge-new"),
                html.Button(
                    "Accetta",
                    id={"type": "accept-sensor-btn", "id": s["sensor_id"]},
                    n_clicks=0,
                    style={"marginLeft": "12px", "background": "#0f172a", "color": "#fff",
                           "border": "none", "borderRadius": "6px", "padding": "3px 10px",
                           "fontSize": "11px", "cursor": "pointer"},
                ),
            ],
            style={"display": "flex", "alignItems": "center", "padding": "6px 0",
                   "borderBottom": "1px solid #f1f5f9"},
        ))
    return rows


@callback(
    Output("zones-threshold-list", "children"),
    Input("interval-60s", "n_intervals"),
    Input("settings-tabs", "active_tab"),
)
def update_zones_list(n, active_tab):
    if active_tab != "tab-thresholds":
        return no_update
    zones, err = _safe_get("/api/zones")
    if err or not zones:
        return html.Div("Nessuna zona configurata.", style={"color": "#94a3b8"})
    rows = []
    for z in zones:
        color = z.get("color", "#64748b")
        t_min = z.get("threshold_min", -30)
        t_max = z.get("threshold_max", 30)
        slider_min = t_min - 10
        slider_max = t_max + 10
        rows.append(html.Div(
            [
                html.Div(
                    [
                        html.Span("\u25a0", style={"color": color, "marginRight": "8px"}),
                        html.Span(z["name"], style={"fontWeight": "600", "fontSize": "13px", "flex": 1}),
                        html.Button(
                            "\U0001f5d1",
                            id={"type": "delete-zone-btn", "name": z["name"]},
                            n_clicks=0,
                            title="Elimina zona",
                            style={"background": "none", "border": "none", "cursor": "pointer",
                                   "fontSize": "14px", "color": "#ef4444"},
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "marginBottom": "8px"},
                ),
                dcc.RangeSlider(
                    id={"type": "zone-threshold-slider", "name": z["name"]},
                    min=slider_min, max=slider_max, step=0.5,
                    value=[t_min, t_max],
                    marks={slider_min: f"{slider_min}\u00b0C", 0: "0\u00b0C", slider_max: f"{slider_max}\u00b0C"},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),
                html.Div(id={"type": "zone-threshold-save-result", "name": z["name"]},
                         style={"fontSize": "11px", "marginTop": "4px"}),
            ],
            className="mm-card",
            style={"marginBottom": "12px", "borderLeft": f"4px solid {color}"},
        ))
    return rows


@callback(
    Output({"type": "zone-threshold-save-result", "name": MATCH}, "children"),
    Input({"type": "zone-threshold-slider", "name": MATCH}, "value"),
    State({"type": "zone-threshold-slider", "name": MATCH}, "id"),
    prevent_initial_call=True,
)
def save_zone_threshold(slider_value, slider_id):
    zone_name = slider_id["name"]
    min_val, max_val = slider_value
    zones, _ = _safe_get("/api/zones")
    current_color = "#64748b"
    if zones:
        match = next((z for z in zones if z["name"] == zone_name), None)
        if match:
            current_color = match.get("color", "#64748b")
    result, err = _safe_post("/api/zones", json={
        "name": zone_name, "color": current_color,
        "threshold_min": min_val, "threshold_max": max_val,
    })
    if err:
        return html.Span(f"Errore: {err}", style={"color": "#ef4444"})
    return html.Span(f"\u2713 Salvato ({min_val}\u00b0C \u2013 {max_val}\u00b0C)", style={"color": "#22c55e"})


@callback(
    Output("configured-sensors-grid", "children"),
    Input("interval-60s", "n_intervals"),
    Input("settings-tabs", "active_tab"),
)
def update_configured_sensors(n, active_tab):
    if active_tab != "tab-sensors":
        return no_update
    sensors, err = _safe_get("/api/sensors")
    if err or not sensors:
        return html.Div("Nessun sensore configurato.", style={"color": "#94a3b8"})
    row_data = [{"id": s["id"], "name": s.get("name", ""), "zone": s.get("zone", ""),
                 "active": s.get("active", True)} for s in sensors]
    return dag.AgGrid(
        id="sensors-ag-grid",
        rowData=row_data,
        columnDefs=[
            {"field": "id",     "headerName": "ID",     "width": 140},
            {"field": "name",   "headerName": "Nome",   "flex": 1, "editable": True},
            {"field": "zone",   "headerName": "Zona",   "width": 120, "editable": True},
            {"field": "active", "headerName": "Attivo", "width": 90,
             "cellRenderer": "agCheckboxCellRenderer", "editable": True},
        ],
        className="ag-theme-quartz",
        style={"height": "300px"},
    )


# Bug 2 fix: open_accept_modal now writes to static modal body + opens static modal
@callback(
    Output("accept-sensor-modal-body", "children"),
    Output("accept-sensor-modal", "is_open"),
    Input({"type": "accept-sensor-btn", "id": ALL}, "n_clicks"),
    State({"type": "accept-sensor-btn", "id": ALL}, "id"),
    prevent_initial_call=True,
)
def open_accept_modal(n_clicks_list, btn_ids):
    if not ctx.triggered_id:
        return no_update, no_update
    sensor_id = ctx.triggered_id["id"]

    body = [
        html.P(f"Sensore: {sensor_id}", style={"fontFamily": "monospace", "fontSize": "12px",
                                                "color": "#374151", "marginBottom": "10px"}),
        html.Label("Nome", style={"fontSize": "12px", "fontWeight": "600"}),
        dcc.Input(id="accept-sensor-name", type="text",
                  style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                         "borderRadius": "6px", "marginBottom": "10px"}),
        html.Label("Zona", style={"fontSize": "12px", "fontWeight": "600"}),
        dcc.Input(id="accept-sensor-zone", type="text",
                  style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                         "borderRadius": "6px", "marginBottom": "10px"}),
        html.Label("Soglia min (opzionale)", style={"fontSize": "12px", "fontWeight": "600"}),
        dcc.Input(id="accept-sensor-min", type="number",
                  style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                         "borderRadius": "6px", "marginBottom": "10px"}),
        html.Label("Soglia max (opzionale)", style={"fontSize": "12px", "fontWeight": "600"}),
        dcc.Input(id="accept-sensor-max", type="number",
                  style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                         "borderRadius": "6px"}),
        dcc.Store(id="accept-sensor-id-store", data=sensor_id),
    ]
    return body, True


# Bug 2 fix: confirm uses static modal IDs (accept-sensor-confirm-btn / accept-sensor-cancel-btn)
@callback(
    Output("accept-sensor-modal", "is_open", allow_duplicate=True),
    Output("discovered-sensors-list", "children", allow_duplicate=True),
    Input("accept-sensor-confirm-btn", "n_clicks"),
    Input("accept-sensor-cancel-btn", "n_clicks"),
    State("accept-sensor-id-store", "data"),
    State("accept-sensor-name", "value"),
    State("accept-sensor-zone", "value"),
    State("accept-sensor-min", "value"),
    State("accept-sensor-max", "value"),
    prevent_initial_call=True,
)
def confirm_accept_sensor(confirm, cancel, sensor_id, name, zone, min_val, max_val):
    if ctx.triggered_id == "accept-sensor-cancel-btn":
        return False, no_update
    if not name or not zone:
        return True, no_update
    body = {"name": name, "zone": zone}
    if min_val is not None:
        body["min"] = min_val
    if max_val is not None:
        body["max"] = max_val
    _safe_post(f"/api/sensors/{sensor_id}/accept", json=body)
    return False, html.Div("Sensore accettato. Ricarica per aggiornare.",
                            style={"color": "#22c55e", "fontSize": "12px"})


# Bug 2 fix: open_add_zone_modal opens static modal (returns is_open=True)
@callback(
    Output("add-zone-modal", "is_open"),
    Input("add-zone-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_add_zone_modal(n):
    return True


# Bug 2 fix: confirm_add_zone reads from static modal inputs
@callback(
    Output("add-zone-modal", "is_open", allow_duplicate=True),
    Output("zones-threshold-list", "children", allow_duplicate=True),
    Input("add-zone-confirm-btn", "n_clicks"),
    Input("add-zone-cancel-btn", "n_clicks"),
    State("zone-name-input", "value"),
    State("zone-color-input", "value"),
    State("zone-min-input", "value"),
    State("zone-max-input", "value"),
    prevent_initial_call=True,
)
def confirm_add_zone(confirm, cancel, name, color, min_val, max_val):
    if ctx.triggered_id == "add-zone-cancel-btn":
        return False, no_update
    if not name or min_val is None or max_val is None:
        return True, no_update
    _safe_post("/api/zones", json={
        "name": name, "color": color or "#64748b",
        "threshold_min": min_val, "threshold_max": max_val,
    })
    return False, html.Div("Zona aggiunta. Ricarica per aggiornare.",
                            style={"color": "#22c55e", "fontSize": "12px"})


@callback(
    Output("zones-threshold-list", "children", allow_duplicate=True),
    Input({"type": "delete-zone-btn", "name": ALL}, "n_clicks"),
    State({"type": "delete-zone-btn", "name": ALL}, "id"),
    prevent_initial_call=True,
)
def delete_zone(n_clicks_list, btn_ids):
    if not ctx.triggered_id:
        return no_update
    zone_name = ctx.triggered_id["name"]
    result, err = _safe_delete(f"/api/zones/{zone_name}")
    if err and "409" in str(err):
        return html.Div(f"Impossibile eliminare: {err}",
                        style={"color": "#ef4444", "fontSize": "12px"})
    if err:
        return html.Div(f"Errore: {err}", style={"color": "#ef4444", "fontSize": "12px"})
    # Success: return a message; list will refresh on next interval tick
    return html.Div(f"✓ Zona '{zone_name}' eliminata. Ricarica per aggiornare.",
                    style={"color": "#22c55e", "fontSize": "12px"})
