@echo off
rem ============================================================================
rem  CONTROLLA E RIPARA GLI ACCESSI DEMO
rem  Guarda nel database quali utenti demo esistono e se la password funziona.
rem  Se mancano (database vuoto) li crea insieme ai dati demo; se ci sono ma sono
rem  disattivati o con un'altra password, li riattiva e rimette la password demo.
rem  Non serve che il server API sia acceso, ma Postgres si'. Ripetibile senza danni.
rem  Solo dati sintetici di sviluppo.
rem ============================================================================
title Esposti - controlla e ripara gli accessi demo
setlocal
set "API=%~dp0..\backend\api"

cd /d "%API%"
if errorlevel 1 goto :manca_cartella
if not exist ".venv\Scripts\activate.bat" goto :prima_il_file_1
call ".venv\Scripts\activate.bat"
set "PYTHONPATH=.."
set "ESPOSTI_AMBIENTE=sviluppo"

echo.
python -m api.accessi_demo --ripara
if errorlevel 1 goto :errore

echo.
echo Fatto. Torna al browser e riprova ad accedere.
echo Se il browser compila la password da solo, cancellala e riscrivila a mano.
goto :fine

:manca_cartella
echo.
echo [ERRORE] Non trovo la cartella %API%
goto :fine

:prima_il_file_1
echo.
echo [ERRORE] L'ambiente Python non e' pronto. Lancia prima avvia-1-api.bat.
goto :fine

:errore
echo.
echo [ERRORE] Non sono riuscito a sistemare gli accessi. Leggi il messaggio qui sopra:
echo se parla di connessione o password del database, Postgres non e' acceso o non
echo e' configurato (lancia crea-database.bat). Altrimenti incolla qui tutto il messaggio.

:fine
echo.
pause
