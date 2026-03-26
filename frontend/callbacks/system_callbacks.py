"""Sistema page callbacks — health, logs, service controls, archive."""

from datetime import datetime
from dash import Input, Output, State, callback, html, ALL, ctx, MATCH
from frontend.components.service_status import service_card
from frontend.utils import safe_get as _safe_get, safe_post as _safe_post


def _uptime_str(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"attivo da {h}h {m}m" if h > 0 else f"attivo da {m}m"


@callback(
    Output("service-cards-container", "children"),
    Output("system-metrics-container", "children"),
    Output("system-updated-ts", "children"),
    Output("dot-mqtt", "className"),
    Output("dot-scheduler", "className"),
    Output("dot-db", "className"),
    Input("interval-30s", "n_intervals"),
)
def update_system_status(n):
    health, err = _safe_get("/api/health")
    ts = datetime.now().strftime("Aggiornato alle %H:%M:%S")

    if err or health is None:
        error_card = html.Div("⚠ Backend non raggiungibile",
                              style={"background": "#fef3c7", "border": "1px solid #f59e0b",
                                     "borderRadius": "8px", "padding": "12px", "fontSize": "13px"})
        return error_card, html.Div("–"), ts, "mm-status-dot mm-dot-error", "mm-status-dot mm-dot-error", "mm-status-dot mm-dot-error"

    mqtt = health.get("mqtt", {})
    sched = health.get("scheduler", {})
    db = health.get("db", {})
    sys_info = health.get("system", {})

    mqtt_status = mqtt.get("status", "disconnected")
    sched_status = sched.get("status", "stopped")
    db_status = db.get("status", "error")

    def dot_cls(s):
        if s in ("connected", "running", "ok"):
            return "mm-status-dot mm-dot-ok"
        elif s in ("degraded",):
            return "mm-status-dot mm-dot-warn"
        return "mm-status-dot mm-dot-error"

    cards = [
        service_card("mqtt", "MQTT", mqtt_status,
                     _uptime_str(mqtt.get("uptime_s", 0)),
                     details=mqtt.get("broker", ""),
                     supports_stop=True),
        service_card("scheduler", "APScheduler", sched_status,
                     _uptime_str(sched.get("uptime_s", 0)),
                     details=f"next: {sched.get('next_run', '–')}",
                     supports_stop=True),
        service_card("db", "Database", db_status,
                     _uptime_str(db.get("uptime_s", 0)),
                     details=f"{db.get('backend', '?')} · {db.get('size_mb', 0):.1f} MB",
                     supports_stop=False),
    ]

    # Archive status
    arc, _ = _safe_get("/api/archive/status")
    last_arc = "mai" if not arc or not arc.get("last_run") else arc["last_run"][:10]
    last_rows = arc.get("last_rows_archived", 0) if arc else 0

    metrics = html.Div(
        [
            _metric("Uptime sistema", _uptime_str(sys_info.get("uptime_s", 0))),
            _metric("Versione", sys_info.get("version", "?")),
            _metric("Dimensione DB", f"{db.get('size_mb', 0):.1f} MB"),
            _metric("Ultima archiviazione", f"{last_arc} ({last_rows} righe)"),
        ],
        className="mm-card",
    )

    return cards, metrics, ts, dot_cls(mqtt_status), dot_cls(sched_status), dot_cls(db_status)


def _metric(label: str, value: str) -> html.Div:
    return html.Div(
        [
            html.Div(label, style={"fontSize": "11px", "color": "#94a3b8", "textTransform": "uppercase",
                                    "letterSpacing": "0.5px", "fontWeight": "600"}),
            html.Div(value, style={"fontSize": "14px", "fontWeight": "700", "color": "#0f172a", "marginBottom": "10px"}),
        ]
    )


@callback(
    Output("log-panel-content", "children"),
    Output("log-filter-store", "data"),
    Input("interval-5s", "n_intervals"),
    Input("log-filter-ALL", "n_clicks"),
    Input("log-filter-INFO", "n_clicks"),
    Input("log-filter-WARNING", "n_clicks"),
    Input("log-filter-ERROR", "n_clicks"),
    State("log-filter-store", "data"),
)
def update_logs(n, _all, _info, _warn, _err, current_filter):
    triggered = ctx.triggered_id
    level = current_filter
    if triggered in ("log-filter-ALL", "log-filter-INFO", "log-filter-WARNING", "log-filter-ERROR"):
        level = triggered.replace("log-filter-", "")

    entries, err = _safe_get(f"/api/logs?level={level}&limit=200")
    if err or entries is None:
        return html.Div("–"), level

    lines = []
    for e in reversed(entries):
        lvl = e.get("level", "INFO")
        cls = {"WARNING": "mm-log-warning", "ERROR": "mm-log-error"}.get(lvl, "mm-log-info")
        ts = e.get("timestamp", "")[:19].replace("T", " ")
        lines.append(html.Div(
            f"[{ts}] {lvl:8s} {e.get('service', '')} — {e.get('message', '')}",
            className=cls,
            style={"marginBottom": "1px", "whiteSpace": "pre-wrap", "wordBreak": "break-all"},
        ))
    return lines, level


@callback(
    Output("archive-result", "children"),
    Input("archive-now-btn", "n_clicks"),
    prevent_initial_call=True,
)
def run_archive(n_clicks):
    result, err = _safe_post("/api/archive/run")
    if err:
        return html.Span(f"Errore: {err}", style={"color": "#ef4444"})
    rows = result.get("rows_archived", 0)
    return html.Span(f"✓ {rows} righe archiviate", style={"color": "#22c55e"})


@callback(
    Output({"type": "service-btn", "service": MATCH, "action": MATCH}, "disabled"),
    Input({"type": "service-btn", "service": MATCH, "action": MATCH}, "n_clicks"),
    State({"type": "service-btn", "service": MATCH, "action": MATCH}, "id"),
    prevent_initial_call=True,
)
def handle_service_action(n_clicks, btn_id):
    service = btn_id["service"]
    action  = btn_id["action"]
    _safe_post(f"/api/services/{service}/{action}")
    return False  # re-enable button after action
