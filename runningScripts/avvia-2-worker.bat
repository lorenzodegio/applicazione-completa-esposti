@echo off
rem ============================================================================
rem  TERMINALE 2 di 3 - Worker del motore (FINTO, nello stesso processo)
rem  Elabora i documenti caricati dall'interfaccia: senza questo restano "in analisi".
rem  Avviare DOPO il file 1 (serve il database gia' migrato). Fermare con Ctrl+C.
rem ============================================================================
title Esposti - 2 Worker motore
setlocal
set "API=%~dp0..\backend\api"

if not exist "%API%\.venv\Scripts\activate.bat" goto :manca_venv

cd /d "%API%"
call ".venv\Scripts\activate.bat"
set "PYTHONPATH=.."
set "ESPOSTI_AMBIENTE=sviluppo"

echo.
echo Worker acceso (finto motore). Il nome del file caricato sceglie lo scenario:
echo     riscontro, manoscritto, errore o .pages, illeggibile, scaduto, instabile, occupato, invalido
echo Lascia questa finestra aperta mentre provi l'interfaccia.
echo.
python -m api.worker
goto :fine

:manca_venv
echo.
echo [ERRORE] Manca l'ambiente virtuale: %API%\.venv  (vedi il file 1)

:fine
echo.
pause
