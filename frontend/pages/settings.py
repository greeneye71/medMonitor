"""Settings page — 7 tabs for full system configuration."""

import dash_bootstrap_components as dbc
from dash import html, dcc


def layout():
    """Create settings page layout with 7 tabs."""
    return html.Div(
        [
            html.H4("Impostazioni", className="mb-3"),

            dbc.Tabs(
                [
                    dbc.Tab(_tab_general(), label="Generale", tab_id="tab-general"),
                    dbc.Tab(_tab_thresholds(), label="Soglie", tab_id="tab-thresholds"),
                    dbc.Tab(_tab_sensors(), label="Sensori", tab_id="tab-sensors"),
                    dbc.Tab(_tab_email(), label="Email", tab_id="tab-email"),
                    dbc.Tab(_tab_database(), label="Database", tab_id="tab-database"),
                    dbc.Tab(_tab_system(), label="Sistema", tab_id="tab-system"),
                    dbc.Tab(_tab_demo(), label="Demo", tab_id="tab-demo"),
                ],
                id="settings-tabs",
                active_tab="tab-general",
            ),

            # Toast for save confirmations
            dbc.Toast(
                "Impostazioni salvate",
                id="settings-toast",
                header="Salvato",
                is_open=False,
                duration=3000,
                icon="success",
                style={"position": "fixed", "top": 66, "right": 10, "zIndex": 1050},
            ),
        ]
    )


def _tab_general():
    """Tab 1 — General settings."""
    return dbc.Card(dbc.CardBody([
        dbc.Row([
            dbc.Col([
                dbc.Label("Nome impianto"),
                dbc.Input(id="setting-app-name", type="text", value="medMonitor"),
            ], md=4),
            dbc.Col([
                dbc.Label("Tema UI"),
                dbc.Select(
                    id="setting-theme",
                    options=[
                        {"label": "SLATE (dark)", "value": "slate"},
                        {"label": "VAPOR (dark viola)", "value": "vapor"},
                        {"label": "FLATLY (light)", "value": "flatly"},
                        {"label": "COSMO (light minimal)", "value": "cosmo"},
                    ],
                    value="slate",
                ),
            ], md=3),
            dbc.Col([
                dbc.Label("Log level"),
                dbc.Select(
                    id="setting-log-level",
                    options=[
                        {"label": "DEBUG", "value": "DEBUG"},
                        {"label": "INFO", "value": "INFO"},
                        {"label": "WARNING", "value": "WARNING"},
                        {"label": "ERROR", "value": "ERROR"},
                    ],
                    value="INFO",
                ),
            ], md=2),
        ], className="mb-3"),
        dbc.Button("Salva", id="btn-save-general", color="primary"),
    ]), className="mt-3")


def _tab_thresholds():
    """Tab 2 — Temperature thresholds."""
    return dbc.Card(dbc.CardBody([
        html.H6("Default di zona", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Frigorifero (°C)"),
                dcc.RangeSlider(
                    id="slider-fridge-defaults",
                    min=-10, max=50, step=0.5,
                    value=[0, 30],
                    marks={-10: "-10", 0: "0", 10: "10", 20: "20", 30: "30", 40: "40", 50: "50"},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),
            ], md=6),
            dbc.Col([
                dbc.Label("Freezer (°C)"),
                dcc.RangeSlider(
                    id="slider-freezer-defaults",
                    min=-50, max=10, step=0.5,
                    value=[-30, 0],
                    marks={-50: "-50", -40: "-40", -30: "-30", -20: "-20", -10: "-10", 0: "0", 10: "10"},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),
            ], md=6),
        ], className="mb-4"),

        html.Hr(),
        html.H6("Soglie per sensore", className="mb-3"),
        html.Div(id="sensor-threshold-cards"),
        dbc.Button("Salva soglie", id="btn-save-thresholds", color="primary", className="mt-3"),
    ]), className="mt-3")


def _tab_sensors():
    """Tab 3 — Sensor management."""
    import dash_ag_grid as dag
    return dbc.Card(dbc.CardBody([
        html.H6("Sensori registrati", className="mb-3"),
        dag.AgGrid(
            id="sensors-edit-grid",
            columnDefs=[
                {"field": "sensor_id", "headerName": "ID Sensore", "editable": False, "width": 200},
                {"field": "name", "headerName": "Nome", "editable": True, "flex": 1},
                {"field": "zone", "headerName": "Zona", "editable": True, "width": 120,
                 "cellEditor": "agSelectCellEditor",
                 "cellEditorParams": {"values": ["fridge", "freezer"]}},
                {"field": "active", "headerName": "Attivo", "editable": True, "width": 100},
            ],
            rowData=[],
            defaultColDef={"resizable": True},
            className="ag-theme-alpine-dark",
            style={"height": "300px"},
            dashGridOptions={"editType": "fullRow"},
        ),
        dbc.Button("Salva sensori", id="btn-save-sensors", color="primary", className="mt-3"),
    ]), className="mt-3")


def _tab_email():
    """Tab 4 — Email SMTP + IMAP configuration."""
    return dbc.Card(dbc.CardBody([
        dbc.Row([
            dbc.Col([
                html.H6("SMTP (invio)", className="mb-3"),
                dbc.Label("Host"),
                dbc.Input(id="setting-smtp-host", type="text", placeholder="smtp.example.com"),
                dbc.Label("Porta", className="mt-2"),
                dbc.Input(id="setting-smtp-port", type="number", value=587),
                dbc.Checkbox(id="setting-smtp-tls", label="Usa TLS", value=True, className="mt-2"),
                dbc.Label("Utente", className="mt-2"),
                dbc.Input(id="setting-smtp-user", type="email"),
                dbc.Label("Password", className="mt-2"),
                dbc.Input(id="setting-smtp-password", type="password"),
                dbc.Label("Destinatari allarmi", className="mt-2"),
                dbc.Textarea(id="setting-smtp-recipients", placeholder="email1@example.com, email2@example.com", rows=2),
                dbc.Button("Test SMTP", id="btn-test-smtp", color="info", outline=True, className="mt-3 me-2"),
                dbc.Badge("", id="badge-smtp-status", className="ms-2"),
            ], md=6),
            dbc.Col([
                html.H6("IMAP (ricezione)", className="mb-3"),
                dbc.Label("Host"),
                dbc.Input(id="setting-imap-host", type="text", placeholder="imap.example.com"),
                dbc.Label("Porta", className="mt-2"),
                dbc.Input(id="setting-imap-port", type="number", value=993),
                dbc.Checkbox(id="setting-imap-ssl", label="Usa SSL", value=True, className="mt-2"),
                dbc.Label("Utente", className="mt-2"),
                dbc.Input(id="setting-imap-user", type="email"),
                dbc.Label("Password", className="mt-2"),
                dbc.Input(id="setting-imap-password", type="password"),
                dbc.Label("Cartella", className="mt-2"),
                dbc.Input(id="setting-imap-folder", type="text", value="INBOX"),
                dbc.Label("Intervallo controllo (sec)", className="mt-2"),
                dbc.Input(id="setting-imap-interval", type="number", value=120),
                dbc.Button("Test IMAP", id="btn-test-imap", color="info", outline=True, className="mt-3 me-2"),
                dbc.Badge("", id="badge-imap-status", className="ms-2"),
            ], md=6),
        ]),
        html.Hr(className="mt-4"),
        dbc.Button("Salva configurazione email", id="btn-save-email", color="primary"),
    ]), className="mt-3")


def _tab_database():
    """Tab 5 — Database configuration."""
    return dbc.Card(dbc.CardBody([
        html.H6("Backend database", className="mb-3"),
        dbc.RadioItems(
            id="setting-db-backend",
            options=[
                {"label": "TinyFlux (file locale, consigliato per inizio)", "value": "tinyflux"},
                {"label": "TimescaleDB (PostgreSQL, produzione)", "value": "timescale"},
            ],
            value="tinyflux",
            className="mb-3",
        ),

        html.Div(id="db-tinyflux-info", children=[
            dbc.Label("Capacita TinyFlux"),
            dbc.Progress(id="tinyflux-capacity", value=0, className="mb-2"),
            html.Small(id="tinyflux-capacity-text", className="text-muted"),
        ]),

        html.Hr(),
        html.H6("Migrazione dati"),
        html.P("Migra i dati da TinyFlux a TimescaleDB mantenendo tutto lo storico.", className="text-muted"),
        dbc.Button("Migra dati", id="btn-migrate-db", color="warning", outline=True, className="me-2"),
        dbc.Progress(id="migrate-progress", value=0, className="mt-2", style={"display": "none"}),
    ]), className="mt-3")


def _tab_system():
    """Tab 6 — System settings."""
    return dbc.Card(dbc.CardBody([
        dbc.Row([
            dbc.Col([
                dbc.Label("Intervallo polling (minuti)"),
                dbc.Input(id="setting-polling-interval", type="number", value=10, min=1, max=60),
            ], md=3),
            dbc.Col([
                dbc.Label("Cooldown allarmi (minuti)"),
                dbc.Input(id="setting-cooldown", type="number", value=30, min=5, max=120),
            ], md=3),
            dbc.Col([
                dbc.Label("Retention dati (giorni)"),
                dbc.Input(id="setting-retention", type="number", value=365, min=30, max=3650),
            ], md=3),
        ], className="mb-4"),

        html.Hr(),
        html.H6("Backup e ripristino"),
        dbc.Row([
            dbc.Col([
                dbc.Button("Esporta configurazione", id="btn-export-config", color="secondary", outline=True),
            ], md=3),
            dbc.Col([
                dcc.Upload(
                    id="upload-config",
                    children=dbc.Button("Importa configurazione", color="secondary", outline=True),
                ),
            ], md=3),
        ]),
        dbc.Button("Salva sistema", id="btn-save-system", color="primary", className="mt-4"),
    ]), className="mt-3")


def _tab_demo():
    """Tab 7 — Demo mode."""
    return dbc.Card(dbc.CardBody([
        html.H6("Modalita demo", className="mb-3"),
        html.P(
            "La modalita demo genera dati simulati per testare il sistema.",
            className="text-muted",
        ),
        dbc.Row([
            dbc.Col([
                dbc.Label("Scenario"),
                dbc.Select(
                    id="setting-demo-scenario",
                    options=[
                        {"label": "Normale — temperature stabili", "value": "normal"},
                        {"label": "Allarme frigo — porta aperta", "value": "fridge_alarm"},
                        {"label": "Allarme freezer — guasto termostato", "value": "freezer_alarm"},
                        {"label": "Blackout — entrambe le zone", "value": "power_loss"},
                        {"label": "Batteria scarica — sensore offline", "value": "sensor_battery_low"},
                        {"label": "Stress test — tutti gli scenari", "value": "full_stress"},
                    ],
                    value="full_stress",
                ),
            ], md=4),
            dbc.Col([
                dbc.Label("Velocita"),
                dbc.Select(
                    id="setting-demo-speed",
                    options=[
                        {"label": "1x (tempo reale)", "value": "1x"},
                        {"label": "10x (consigliato)", "value": "10x"},
                        {"label": "60x (veloce)", "value": "60x"},
                        {"label": "600x (stress test)", "value": "600x"},
                    ],
                    value="10x",
                ),
            ], md=3),
        ], className="mb-3"),
        dbc.Button("Avvia demo", id="btn-start-demo", color="success", className="me-2"),
        dbc.Button("Ferma demo", id="btn-stop-demo-settings", color="warning", outline=True, className="me-2"),
        dbc.Button("Reset dati demo", id="btn-reset-demo", color="danger", outline=True),
        html.Div(id="demo-status-text", className="mt-3"),
    ]), className="mt-3")
