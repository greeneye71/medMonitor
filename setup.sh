#!/usr/bin/env bash
set -euo pipefail

echo "=== medMonitor Setup ==="
echo

# Check Python 3.11+
if ! command -v python3 &>/dev/null; then
    echo "ERRORE: Python3 non trovato. Installa Python 3.11+ dal tuo package manager."
    exit 1
fi

PYVER=$(python3 -c 'import sys; print(".".join(map(str,sys.version_info[:2])))')
echo "Python trovato: $PYVER"

# Create virtual environment if missing
if [ ! -d "venv" ]; then
    echo "Creazione ambiente virtuale..."
    python3 -m venv venv
fi

# Install dependencies
echo "Installazione dipendenze..."
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Create data directory
if [ ! -d "data" ]; then
    mkdir -p data
    echo "Creata directory data/"
fi

# Copy .env if missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "Creato .env da .env.example"
    echo "IMPORTANTE: modifica .env con le tue credenziali prima di avviare."
fi

echo
echo "=== Setup completato! ==="
echo
echo "Comandi per avviare il sistema (in terminali separati):"
echo "  Backend:   source venv/bin/activate && uvicorn backend.main:app --reload --port 8000"
echo "  Frontend:  source venv/bin/activate && python frontend/app.py"
echo
echo "Oppure con Docker:"
echo "  docker compose up -d"
echo
