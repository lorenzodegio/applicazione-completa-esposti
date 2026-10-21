@echo off
rem ============================================================================
rem  TERMINALE 1 di 3 - API per le prove manuali nel browser
rem  Prepara da solo l'ambiente Python (una volta), migra il database, crea i dati
rem  demo SINTETICI e avvia il server su http://localhost:8000
rem  Requisiti: Python 3.12 o piu' recente e un Postgres acceso.
rem  Da lanciare per PRIMO. Fermare con Ctrl+C.
rem ============================================================================
title Esposti - 1 API
setlocal
set "API=%~dp0..\backend\api"

cd /d "%API%"
if errorlevel 1 goto :manca_cartella

if exist ".venv\Scripts\activate.bat" goto :venv_ok
echo.
echo Creo l'ambiente virtuale, una volta sola...
python --version
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if errorlevel 1 goto :python_vecchio
python -m venv .venv
if errorlevel 1 goto :errore

:venv_ok
call ".venv\Scripts\activate.bat"
python --version
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if errorlevel 1 goto :python_vecchio_venv

python -c "import fastapi, uvicorn, sqlalchemy, alembic, psycopg, argon2, pydantic_settings, multipart, httpx" >nul 2>&1
if not errorlevel 1 goto :dipendenze_ok
echo.
echo Installo le dipendenze del backend, una volta sola: ci vuole circa un minuto...
python -m pip install -e .
if errorlevel 1 goto :errore_pip

:dipendenze_ok
set "PYTHONPATH=.."
set "ESPOSTI_COOKIE_SECURE=false"
set "ESPOSTI_AMBIENTE=sviluppo"

rem Se il Postgres e' il container Docker "esposti-pg" lo avvia; senza Docker non succede nulla.
docker start esposti-pg >nul 2>&1 && timeout /t 4 /nobreak >nul

echo.
echo [1/3] Migrazioni del database...
python -m alembic upgrade head
if errorlevel 1 goto :errore_migrazione

echo.
echo [3/3] Server API su http://localhost:8000   Documentazione: http://localhost:8000/docs
echo Quando vedi "Application startup complete" puoi avviare gli altri due file.
echo.
python -m uvicorn api.main:app --port 8000
goto :fine

:manca_cartella
echo.
echo [ERRORE] Non trovo la cartella %API%
echo Questo file deve stare in "scripts" nella radice del repository, accanto a backend e frontend.
goto :fine

:python_vecchio
echo.
echo [ERRORE] Serve Python 3.12 o piu' recente, e questo "python" e' piu' vecchio o non c'e'.
echo Installalo da https://www.python.org/downloads/ spuntando "Add python.exe to PATH",
echo oppure con:   winget install Python.Python.3.12
echo Poi chiudi e riapri questa finestra e rilancia il file.
goto :fine

:python_vecchio_venv
echo.
echo [ERRORE] L'ambiente virtuale in backend\api\.venv usa un Python troppo vecchio: serve la 3.12 o piu'.
echo Installa Python 3.12, CANCELLA la cartella backend\api\.venv e rilancia questo file: la ricrea lui.
goto :fine

:errore_pip
echo.
echo [ERRORE] L'installazione delle dipendenze non e' riuscita: leggi l'errore qui sopra.
goto :fine

:errore_migrazione
echo.
echo [ERRORE] La migrazione del database e' fallita. Guarda l'ULTIMA riga dell'errore qui sopra:
echo   - "autenticazione con password fallita" o "password authentication failed":
echo     Postgres e' acceso ma non conosce l'utente "esposti" con password "esposti".
echo     Soluzione: lancia crea-database.bat (e' nella stessa cartella), poi rilancia questo file.
echo   - "database esposti does not exist" o "non esiste": stessa soluzione, crea-database.bat.
echo   - "connessione rifiutata" o "connection refused": Postgres non e' acceso.
echo     Con Docker, la prima volta (tutto su una riga):
echo     docker run --name esposti-pg -e POSTGRES_USER=esposti -e POSTGRES_PASSWORD=esposti -e POSTGRES_DB=esposti -p 5432:5432 -d postgres:16
echo   - Se vuoi usare utente, password o database DIVERSI, crea il file backend\api\.env con una riga:
echo     ESPOSTI_DATABASE_URL=postgresql+psycopg://UTENTE:PASSWORD@localhost:5432/NOMEDATABASE
echo     Usa un database NUOVO e dedicato, mai uno con dati reali.
goto :fine

:errore
echo.
echo [ERRORE] Qualcosa non e' andato a buon fine: leggi il messaggio qui sopra.

:fine
echo.
pause