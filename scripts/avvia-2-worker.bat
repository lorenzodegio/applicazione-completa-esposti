@echo off
rem ============================================================================
rem  TERMINALE 2 di 3 - Worker del motore (FINTO, nello stesso processo)
rem  Elabora i documenti caricati dall'interfaccia: senza questo restano "in analisi".
rem  Avviare DOPO il file 1 (serve il database gia' migrato). Fermare con Ctrl+C.
rem ============================================================================
title Esposti - 2 Worker motore
setlocal
set "API=%~dp0..\backend\api"

cd /d "%API%"
if errorlevel 1 goto :manca_cartella
if not exist ".venv\Scripts\activate.bat" goto :prima_il_file_1
call ".venv\Scripts\activate.bat"
python -c "import fastapi, uvicorn, sqlalchemy, alembic, psycopg, argon2, pydantic_settings, multipart, httpx" >nul 2>&1
if errorlevel 1 goto :prima_il_file_1

set "PYTHONPATH=.."
set "ESPOSTI_AMBIENTE=sviluppo"

echo.
echo Worker acceso (finto motore). Il nome del file caricato sceglie lo scenario:
echo     riscontro, manoscritto, errore o .pages, illeggibile, scaduto, instabile, occupato, invalido
echo Lascia questa finestra aperta mentre provi l'interfaccia.
echo.
python -m api.worker
goto :fine

:manca_cartella
echo.
echo [ERRORE] Non trovo la cartella %API%
goto :fine

:prima_il_file_1
echo.
echo [ERRORE] L'ambiente Python non e' pronto. Lancia prima avvia-1-api.bat: lo prepara lui.

:fine
echo.
pause
