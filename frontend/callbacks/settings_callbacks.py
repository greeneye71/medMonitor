"""Settings page callbacks — save config, test email, manage demo."""

import logging

import requests
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, no_update, html, dcc, ALL, MATCH, ctx

logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000/api"
API = "http://localhost:8000"


def _safe_get(path):
    try:
        r = requests.get(f"{API}{path}", timeout=3)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def _safe_post(path, json=None):
    try:
        r = requests.post(f"{API}{path}", json=json, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def _safe_delete(path):
    try:
        r = requests.delete(f"{API}{path}", timeout=5)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


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


@callback(
    Output("settings-toast", "is_open", allow_duplicate=True),
    Input("btn-save-email", "n_clicks"),
    State("setting-smtp-host", "value"),
    State("setting-smtp-port", "value"),
    State("setting-smtp-tls", "value"),
    State("setting-smtp-user", "value"),
    State("setting-smtp-password", "value"),
    State("setting-smtp-recipients", "value"),
    State("setting-imap-host", "value"),
    State("setting-imap-port", "value"),
    State("setting-imap-ssl", "value"),
    State("setting-imap-user", "value"),
    State("setting-imap-password", "value"),
    State("setting-imap-folder", "value"),
    prevent_initial_call=True,
)
def save_email(_n, smtp_host, smtp_port, smtp_tls, smtp_user, smtp_password,
               recipients, imap_host, imap_port, imap_ssl, imap_user, imap_password, imap_folder):
    email_config = {}
    if smtp_host:
        email_config["smtp"] = {
            "host": smtp_host,
            "port": smtp_port or 587,
            "use_tls": bool(smtp_tls),
            "user": smtp_user or "",
            "password": smtp_password or "",
        }
    if recipients:
        email_config["recipients"] = [r.strip() for r in recipients.split(",") if r.strip()]
    if imap_host:
        email_config["imap"] = {
            "host": imap_host,
            "port": imap_port or 993,
            "use_ssl": bool(imap_ssl),
            "user": imap_user or "",
            "password": imap_password or "",
            "folder": imap_folder or "INBOX",
        }
    _patch("/config", {"email": email_config})
    return True


@callback(
    Output("settings-toast", "is_open", allow_duplicate=True),
    Input("btn-save-sensors", "n_clicks"),
    State("sensors-edit-grid", "rowData"),
    prevent_initial_call=True,
)
def save_sensors(_n, row_data):
    if not row_data:
        return no_update
    for row in row_data:
        sensor_id = row.get("sensor_id")
        if sensor_id:
            try:
                requests.put(
                    f"{API_BASE}/sensors/{sensor_id}",
                    json={
                        "name": row.get("name", ""),
                        "zone": row.get("zone", "fridge"),
                        "active": row.get("active", True),
                    },
                    timeout=5,
                )
            except Exception as e:
                logger.warning("Save sensor %s failed: %s", sensor_id, e)
    return True


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


@callback(
    Output("accept-sensor-modal-container", "children"),
    Input({"type": "accept-sensor-btn", "id": ALL}, "n_clicks"),
    State({"type": "accept-sensor-btn", "id": ALL}, "id"),
    prevent_initial_call=True,
)
def open_accept_modal(n_clicks_list, btn_ids):
    if not any(n for n in n_clicks_list if n):
        return no_update
    triggered_idx = next(i for i, n in enumerate(n_clicks_list) if n)
    sensor_id = btn_ids[triggered_idx]["id"]

    modal = dbc.Modal(
        [
            dbc.ModalHeader(f"Accetta sensore: {sensor_id}"),
            dbc.ModalBody([
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
            ]),
            dbc.ModalFooter([
                dbc.Button("Annulla", id="accept-cancel-btn", color="secondary", size="sm"),
                dbc.Button("Accetta", id="accept-confirm-btn", color="primary", size="sm"),
            ]),
        ],
        id="accept-sensor-modal",
        is_open=True,
    )
    return modal


@callback(
    Output("accept-sensor-modal", "is_open"),
    Output("discovered-sensors-list", "children", allow_duplicate=True),
    Input("accept-confirm-btn", "n_clicks"),
    Input("accept-cancel-btn", "n_clicks"),
    State("accept-sensor-id-store", "data"),
    State("accept-sensor-name", "value"),
    State("accept-sensor-zone", "value"),
    State("accept-sensor-min", "value"),
    State("accept-sensor-max", "value"),
    prevent_initial_call=True,
)
def confirm_accept_sensor(confirm, cancel, sensor_id, name, zone, min_val, max_val):
    if ctx.triggered_id == "accept-cancel-btn":
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


@callback(
    Output("zone-modal-container", "children"),
    Input("add-zone-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_add_zone_modal(n):
    modal = dbc.Modal(
        [
            dbc.ModalHeader("Aggiungi zona"),
            dbc.ModalBody([
                html.Label("Nome zona", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="new-zone-name", type="text",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px", "marginBottom": "10px"}),
                html.Label("Colore", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="new-zone-color", type="text", value="#64748b",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px", "marginBottom": "10px"}),
                html.Label("Soglia min (\u00b0C)", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="new-zone-min", type="number",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px", "marginBottom": "10px"}),
                html.Label("Soglia max (\u00b0C)", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="new-zone-max", type="number",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px"}),
            ]),
            dbc.ModalFooter([
                dbc.Button("Annulla", id="zone-modal-cancel", color="secondary", size="sm"),
                dbc.Button("Crea zona", id="zone-modal-confirm", color="primary", size="sm"),
            ]),
        ],
        id="add-zone-modal",
        is_open=True,
    )
    return modal


@callback(
    Output("add-zone-modal", "is_open"),
    Output("zones-threshold-list", "children", allow_duplicate=True),
    Input("zone-modal-confirm", "n_clicks"),
    Input("zone-modal-cancel", "n_clicks"),
    State("new-zone-name", "value"),
    State("new-zone-color", "value"),
    State("new-zone-min", "value"),
    State("new-zone-max", "value"),
    prevent_initial_call=True,
)
def confirm_add_zone(confirm, cancel, name, color, min_val, max_val):
    if ctx.triggered_id == "zone-modal-cancel":
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
    if not any(n for n in n_clicks_list if n):
        return no_update
    triggered_idx = next(i for i, n in enumerate(n_clicks_list) if n)
    zone_name = btn_ids[triggered_idx]["name"]
    result, err = _safe_delete(f"/api/zones/{zone_name}")
    if err and "409" in str(err):
        return html.Div(f"Impossibile eliminare: {err}",
                        style={"color": "#ef4444", "fontSize": "12px"})
    return no_update
