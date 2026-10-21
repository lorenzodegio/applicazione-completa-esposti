@echo off
rem ============================================================================
rem  CONTROLLO DEI REQUISITI per le prove manuali nel browser
rem  Non installa e non modifica nulla: guarda solo cosa c'e' sul PC e dice cosa manca.
rem  Si puo' lanciare quante volte si vuole (doppio clic).
rem ============================================================================
title Esposti - controllo requisiti
setlocal
set "RADICE=%~dp0.."
set "PROBLEMI=0"

echo.
echo === Controllo dei requisiti per le prove manuali ===

echo.
echo --- 1. Python (serve la 3.12 o piu' recente)
python --version >nul 2>&1
if errorlevel 1 goto :py_manca
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if errorlevel 1 goto :py_vecchio
for /f "delims=" %%v in ('python --version') do echo [OK]      %%v
goto :node
:py_manca
echo [MANCA]   Python non trovato. Installalo da https://www.python.org/downloads/
echo           spuntando "Add python.exe to PATH", oppure: winget install Python.Python.3.12
echo           Poi CHIUDI e riapri questa finestra. Se hai gia' installato Python, puo' essere
echo           bloccato dall'alias del Microsoft Store: Impostazioni, Alias di esecuzione app.
set /a PROBLEMI+=1
goto :node
:py_vecchio
for /f "delims=" %%v in ('python --version') do echo [VECCHIO] %%v: serve la 3.12 o piu' recente.
echo           Installa Python 3.12 (winget install Python.Python.3.12) e riapri la finestra.
set /a PROBLEMI+=1

:node
echo.
echo --- 2. Node.js e npm (serve Node 22 o piu' recente)
node --version >nul 2>&1
if errorlevel 1 goto :node_manca
node -e "process.exit(parseInt(process.versions.node) >= 22 ? 0 : 1)"
if errorlevel 1 goto :node_vecchio
for /f "delims=" %%v in ('node --version') do echo [OK]      Node %%v
call npm --version >nul 2>&1
if errorlevel 1 goto :npm_manca
for /f "delims=" %%v in ('npm --version') do echo [OK]      npm %%v
goto :postgres
:node_manca
echo [MANCA]   Node.js non trovato. Installalo da https://nodejs.org/ (versione LTS)
echo           oppure: winget install OpenJS.NodeJS.LTS   Poi riapri la finestra.
set /a PROBLEMI+=1
goto :postgres
:node_vecchio
for /f "delims=" %%v in ('node --version') do echo [VECCHIO] Node %%v: serve la 22 o piu' recente.
echo           Installa la versione LTS da https://nodejs.org/ e riapri la finestra.
set /a PROBLEMI+=1
goto :postgres
:npm_manca
echo [MANCA]   npm non trovato: reinstalla Node.js da https://nodejs.org/
set /a PROBLEMI+=1

:postgres
echo.
echo --- 3. Database PostgreSQL (porta 5432)
netstat -an | findstr /R /C:":5432 .*LISTENING" >nul
if not errorlevel 1 goto :pg_ok
echo [MANCA]   Nessun Postgres in ascolto sulla porta 5432.
docker --version >nul 2>&1
if errorlevel 1 goto :no_docker
docker info >nul 2>&1
if errorlevel 1 goto :docker_fermo
for /f "delims=" %%i in ('docker ps -q --filter "name=esposti-pg"') do set "IN_ESECUZIONE=%%i"
if defined IN_ESECUZIONE goto :pg_in_avvio
for /f "delims=" %%i in ('docker ps -aq --filter "name=esposti-pg"') do set "ESISTE=%%i"
if defined ESISTE goto :container_fermo
echo           Docker c'e' ma il contenitore non e' ancora stato creato. La prima volta, in un
echo           terminale (tutto su una riga):
echo           docker run --name esposti-pg -e POSTGRES_USER=esposti -e POSTGRES_PASSWORD=esposti -e POSTGRES_DB=esposti -p 5432:5432 -d postgres:16
set /a PROBLEMI+=1
goto :progetto
:pg_ok
echo [OK]      Un Postgres e' in ascolto sulla porta 5432.
echo           Deve avere utente "esposti", password "esposti" e database "esposti".
goto :progetto
:pg_in_avvio
echo [ATTENZIONE] Il contenitore esposti-pg e' acceso ma non ancora in ascolto: attendi 10 secondi e rilancia.
set /a PROBLEMI+=1
goto :progetto
:container_fermo
echo           Il contenitore esposti-pg esiste ma e' fermo. Avvialo con:  docker start esposti-pg
echo           (oppure lancia avvia-1-api.bat, che lo avvia da solo).
set /a PROBLEMI+=1
goto :progetto
:docker_fermo
echo           Docker e' installato ma non e' acceso: avvia "Docker Desktop" e attendi che sia pronto.
set /a PROBLEMI+=1
goto :progetto
:no_docker
echo           Docker non trovato. Scegli UNA di queste strade:
echo             a) Docker Desktop (consigliato): https://www.docker.com/products/docker-desktop/
echo             b) PostgreSQL installato a mano (https://www.postgresql.org/download/windows/):
echo                crea utente "esposti" con password "esposti" e database "esposti".
set /a PROBLEMI+=1

:progetto
echo.
echo --- 4. File del progetto
if exist "%RADICE%\backend\api\pyproject.toml" (echo [OK]      backend\api) else (echo [MANCA]   backend\api: hai estratto lo zip nella radice del repository? & set /a PROBLEMI+=1)
if exist "%RADICE%\frontend\backoffice\package.json" (echo [OK]      frontend\backoffice) else (echo [MANCA]   frontend\backoffice: hai estratto lo zip nella radice del repository? & set /a PROBLEMI+=1)
if exist "%RADICE%\scripts\avvia-1-api.bat" (echo [OK]      scripts\avvia-1-api.bat) else (echo [MANCA]   scripts\avvia-1-api.bat & set /a PROBLEMI+=1)
if exist "%RADICE%\backend\api\.venv\Scripts\python.exe" goto :venv_c
echo [INFO]    Ambiente Python non ancora creato: lo crea avvia-1-api.bat alla prima esecuzione.
goto :moduli
:venv_c
"%RADICE%\backend\api\.venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if errorlevel 1 goto :venv_vecchio
echo [OK]      Ambiente Python gia' creato (backend\api\.venv) con una versione adeguata.
goto :moduli
:venv_vecchio
echo [VECCHIO] backend\api\.venv usa un Python troppo vecchio. Dopo aver installato Python 3.12,
echo           CANCELLA la cartella backend\api\.venv: avvia-1-api.bat la ricrea.
set /a PROBLEMI+=1
:moduli
if exist "%RADICE%\frontend\backoffice\node_modules" (echo [OK]      Dipendenze del frontend gia' installate) else (echo [INFO]    Dipendenze del frontend non ancora installate: le installa avvia-3-frontend.bat.)

echo.
echo --- 5. Porte libere (8000 per le API, 5173 per l'interfaccia)
netstat -an | findstr /R /C:":8000 .*LISTENING" >nul
if not errorlevel 1 (echo [ATTENZIONE] La porta 8000 e' gia' occupata: forse hai gia' un server acceso da una prova precedente. & set /a PROBLEMI+=1) else (echo [OK]      porta 8000 libera)
netstat -an | findstr /R /C:":5173 .*LISTENING" >nul
if not errorlevel 1 (echo [ATTENZIONE] La porta 5173 e' gia' occupata: forse hai gia' l'interfaccia accesa. & set /a PROBLEMI+=1) else (echo [OK]      porta 5173 libera)

echo.
echo ============================================================================
if "%PROBLEMI%"=="0" goto :tutto_ok
echo  Ci sono %PROBLEMI% punti da sistemare (quelli con MANCA, VECCHIO o ATTENZIONE).
echo  Risolvili e rilancia questo file finche' non vedi "Tutto pronto".
goto :fine
:tutto_ok
echo  Tutto pronto. Ora lancia, in quest'ordine, un doppio clic ciascuno:
echo     1) avvia-1-api.bat   2) avvia-2-worker.bat   3) avvia-3-frontend.bat
echo  Poi apri http://localhost:5173 nel browser.
:fine
echo ============================================================================
echo.
pause
