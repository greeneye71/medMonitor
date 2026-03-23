#!/usr/bin/env bash
# medMonitor — avvio backend + frontend

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Avvio backend..."
source venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Avvio frontend..."
python frontend/app.py &
FRONTEND_PID=$!

echo ""
echo "medMonitor avviato!"
echo "  Dashboard: http://localhost:8050"
echo "  API docs:  http://localhost:8000/docs"
echo ""
echo "Premi Ctrl+C per fermare."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
