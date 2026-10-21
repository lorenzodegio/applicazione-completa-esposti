@echo off
rem ============================================================================
rem  TERMINALE 1 di 3 - API per le prove manuali nel browser
rem  Migrazioni del database + dati demo SINTETICI + server su http://localhost:8000
rem  Requisiti: backend\api\.venv con le dipendenze installate, un Postgres acceso.
rem  Da lanciare per PRIMO. Fermare con Ctrl+C.
rem ============================================================================
title Esposti - 1 API
setlocal
set "API=%~dp0..\backend\api"

if not exist "%API%\.venv\Scripts\activate.bat" goto :manca_venv

cd /d "%API%"
call ".venv\Scripts\activate.bat"
set "PYTHONPATH=.."
set "ESPOSTI_COOKIE_SECURE=false"
set "ESPOSTI_AMBIENTE=sviluppo"

rem Se il Postgres e' il container Docker "esposti-pg" lo avvia; senza Docker non succede nulla.
docker start esposti-pg >nul 2>&1 && timeout /t 4 /nobreak >nul

echo.
echo [1/3] Migrazioni del database...
alembic upgrade head
if errorlevel 1 goto :errore_db

echo.
echo [2/3] Dati demo sintetici (se ci sono gia' non rifa nulla)...
python -m api.demo
if errorlevel 1 goto :errore

echo.
echo [3/3] Server API su http://localhost:8000   Documentazione: http://localhost:8000/docs
echo Quando vedi "Application startup complete" puoi avviare gli altri due file.
echo.
uvicorn api.main:app --port 8000
goto :fine

:manca_venv
echo.
echo [ERRORE] Manca l'ambiente virtuale: %API%\.venv
echo Crealo una volta sola da backend\api con questi comandi:
echo     python -m venv .venv
echo     .venv\Scripts\activate
echo     pip install -e ".[dev]"
goto :fine

:errore_db
echo.
echo [ERRORE] Il database non risponde. Controlla che Postgres sia acceso.
echo Con Docker, la prima volta (tutto su una riga):
echo     docker run --name esposti-pg -e POSTGRES_USER=esposti -e POSTGRES_PASSWORD=esposti -e POSTGRES_DB=esposti -p 5432:5432 -d postgres:16
goto :fine

:errore
echo.
echo [ERRORE] Qualcosa non e' andato a buon fine: leggi il messaggio qui sopra.

:fine
echo.
pause
