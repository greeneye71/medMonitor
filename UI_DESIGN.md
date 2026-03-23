# UI Design

## Stack

- `dash` + `dash-bootstrap-components` (Bootstrap 5)
- `plotly` per grafici interattivi
- `dash-iconify` per icone
- `dash-ag-grid` per tabelle avanzate
```bash
pip install dash dash-bootstrap-components plotly dash-iconify dash-ag-grid
```

## Tema default: SLATE (dark)
```python
import dash_bootstrap_components as dbc
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE])
```

Temi selezionabili da UI:
- SLATE — dark grigio-blu (default)
- VAPOR — dark viola
- FLATLY — light flat
- COSMO — light minimal

## Layout
```
NAVBAR  [logo] medMonitor   ● Sistema attivo   [1 allarme]
──────────────────────────────────────────────────────────────────
SIDEBAR (160px) │ CONTENUTO
                │
[▐] Dashboard   │  [4.2°C OK] [-31.4°C !!] [1 allarme] [2/2 sens]
    Storico     │
    Allarmi     │  ┌── Frigorifero ──┐  ┌── Freezer ─────────┐
    ────        │  │ OK      4.2°C  │  │ ALLARME  -31.4°C  │
    Impostazioni│  │ ████░░░░░░░░░  │  │ █░░░░░░░░░░░░░░░  │
                │  │ 0°C      30°C  │  │ -30°C        0°C  │
                │  └────────────────┘  └───────────────────┘
                │
                │  [Grafico linea 24h con bande soglia per sensore]
                │
                │  [Tabella sensori: stato, batteria, ultimo aggiornamento]
```

## Colori semantici

| Stato | Hex | Uso |
|---|---|---|
| OK | #1D9E75 | bordo card 3px, temperatura, dot sensore |
| WARNING | #BA7517 | badge, temperatura gialla |
| CRITICAL | #E24B4A | bordo card 3px, badge, linee soglia |

## Zone card

- Bordo sinistro 3px colorato per stato
- Mostra soglie **effettive del sensore** (non quelle di zona)
- Icona ★ se override=True con tooltip "Soglie individuali"
- Gauge bar 6px fill colorato

## Pagine

1. **Dashboard** — real-time, dcc.Interval 30s
2. **Storico** — DatePickerRange, grafici Plotly, export CSV
3. **Allarmi** — AG Grid con filtri, badge WARNING/CRITICAL
4. **Impostazioni** — tabs: Generale, Soglie, Sensori, Email (SMTP+IMAP), Database, Sistema, Demo

## Sezione Soglie (Impostazioni)

Due livelli:
1. Default di zona — RangeSlider per fridge e freezer
2. Per sensore — card con dbc.Switch toggle override + RangeSlider sincronizzato

Pattern MATCH di Dash per gestire N sensori dinamicamente.
Slider disabilitato se override=False.

## Struttura frontend
```
frontend/
├── app.py
├── layout.py          # Navbar + sidebar
├── pages/
│   ├── dashboard.py
│   ├── history.py
│   ├── alerts.py
│   └── settings.py
├── components/
│   ├── zone_card.py   # Card con gauge e badge stato
│   ├── metric_card.py
│   ├── demo_banner.py # Banner giallo demo attiva
│   └── charts.py
├── callbacks/
└── assets/custom.css
```