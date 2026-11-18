@echo off
rem ============================================================================
rem  MIGRA E RIPARA GLI ACCESSI DEMO
rem  1) applica le migrazioni (inclusa la rinomina smistatore -> gestore_delle_pratiche)
rem  2) riattiva gli account demo e reimposta la password demo
rem  Usa solo dati sintetici di sviluppo. Postgres deve essere acceso.
rem ============================================================================
title Esposti - migra e ripara gli accessi demo
setlocal
set "API=%~dp0..\backend\api"

cd /d "%API%"
if errorlevel 1 goto :manca_cartella
if not exist ".venv\Scripts\activate.bat" goto :prima_il_file_1
call ".venv\Scripts\activate.bat"
set "PYTHONPATH=.."
set "ESPOSTI_AMBIENTE=sviluppo"

echo.
echo [1/2] Applico le migrazioni del database...
python -m alembic upgrade head
if errorlevel 1 goto :errore_migrazione

echo.
echo [2/2] Controllo e ripristino le credenziali demo...
python -m api.accessi_demo --ripara
if errorlevel 1 goto :errore_riparazione

echo.
echo [OK] Ripristino completato.
echo.
echo Torna al browser, ricarica la pagina e inserisci le credenziali indicate.
goto :fine

:manca_cartella
echo.
echo [ERRORE] Non trovo la cartella %API%.
goto :fine

:prima_il_file_1
echo.
echo [ERRORE] Ambiente Python non pronto. Lancia prima avvia-1-api.bat.
goto :fine

:errore_migrazione
echo.
echo [ERRORE] Migrazione non riuscita. Controlla l'errore qui sopra:
echo - password authentication failed: controlla la connessione/credenziali Postgres;
echo - connection refused: avvia Postgres;
echo - altri errori: copia qui il messaggio completo.
goto :fine

:errore_riparazione
echo.
echo [ERRORE] Non sono riuscito a riparare gli accessi. Copia qui il messaggio completo.
goto :fine

:fine
echo.
pause
