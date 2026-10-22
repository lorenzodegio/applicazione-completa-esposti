@echo off
rem ============================================================================
rem  TERMINALE 3 di 3 - Interfaccia (frontend) su http://localhost:5173
rem  La prima volta installa le dipendenze (qualche minuto). Fermare con Ctrl+C.
rem  Le chiamate /api vengono inoltrate al server del file 1 (porta 8000).
rem ============================================================================
title Esposti - 3 Frontend - accessi demo: op.vet, smistatore, admin - password-sintetica-1
setlocal
set "FE=%~dp0..\frontend\backoffice"

if not exist "%FE%\package.json" goto :manca

cd /d "%FE%"
if exist node_modules goto :avvio
echo.
echo Prima volta: installo le dipendenze, attendi...
call npm install
if errorlevel 1 goto :errore

:avvio
echo.
echo Apri http://localhost:5173 nel browser.
echo Accessi demo: smistatore, op.vet, op.igp, admin   Password: password-sintetica-1
echo.
call npm run dev -- --clearScreen false
goto :fine

:manca
echo.
echo [ERRORE] Non trovo il frontend: %FE%
goto :fine

:errore
echo.
echo [ERRORE] npm install non e' riuscito: leggi il messaggio qui sopra. Serve Node 22 o piu' recente.

:fine
echo.
pause
