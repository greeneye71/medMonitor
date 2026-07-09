@echo off
setlocal enabledelayedexpansion
echo === medMonitor Setup ===
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRORE: Python non trovato. Installa Python 3.11+ da https://python.org
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Python trovato: %PYVER%

REM Create virtual environment if missing
if not exist "venv\" (
    echo Creazione ambiente virtuale...
    python -m venv venv
    if errorlevel 1 (
        echo ERRORE: impossibile creare l'ambiente virtuale
        exit /b 1
    )
)

REM Install dependencies
echo Installazione dipendenze...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
if errorlevel 1 (
    echo ERRORE: installazione dipendenze fallita
    exit /b 1
)

REM Create data directory
if not exist "data\" (
    mkdir data
    echo Creata directory data\
)

REM Copy .env if missing
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo Creato .env da .env.example
        echo IMPORTANTE: modifica .env con le tue credenziali prima di avviare.
    ) else (
        echo ATTENZIONE: .env.example non trovato, crea manualmente il file .env
    )
)

echo.
echo === Setup completato! ===
echo.
echo Comandi per avviare il sistema (in terminali separati):
echo   Backend:   venv\Scripts\activate ^& uvicorn backend.main:app --reload --port 8000
echo   Frontend:  venv\Scripts\activate ^& python frontend\app.py
echo.
echo Oppure con Docker:
echo   docker compose up -d
echo.
