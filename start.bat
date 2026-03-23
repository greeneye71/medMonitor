@echo off
title medMonitor

echo Avvio backend...
start "medMonitor Backend" cmd /k "cd /d %~dp0 && venv\Scripts\activate && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

echo Avvio frontend...
start "medMonitor Frontend" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python frontend/app.py"

echo.
echo medMonitor avviato!
echo   Dashboard: http://localhost:8050
echo   API docs:  http://localhost:8000/docs
echo.
pause
