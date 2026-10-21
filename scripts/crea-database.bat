@echo off
rem ============================================================================
rem  CREA IL DATABASE DI SVILUPPO (una volta sola)
rem  Crea (o sistema) nel Postgres che hai sul PC l'utente "esposti" con password
rem  "esposti" e il database "esposti", cioe' quello che si aspettano le prove manuali.
rem  Non tocca gli altri database. Ripetibile senza danni.
rem  Ti chiede la password del superutente di Postgres (di solito "postgres").
rem ============================================================================
title Esposti - crea il database di sviluppo
setlocal
set "SUPERUTENTE=postgres"
set "PORTA=5432"

set "PSQL="
where psql >nul 2>&1 && set "PSQL=psql"
if defined PSQL goto :trovato
for /d %%d in ("%ProgramFiles%\PostgreSQL\*") do if exist "%%d\bin\psql.exe" set "PSQL=%%d\bin\psql.exe"
if not defined PSQL goto :no_psql

:trovato
echo.
echo Programma usato: "%PSQL%"
echo.
echo Sto per creare (o sistemare) l'utente "esposti" con password "esposti" e il database
echo "esposti". Gli altri database non vengono toccati.
echo.
echo Ora ti chiedo la password dell'utente "%SUPERUTENTE%" di Postgres, cioe' quella scelta
echo quando hai installato Postgres. Mentre la scrivi non si vede nulla: e' normale.
echo Se compare un errore "database esposti already exists" o "esiste gia'", va bene.
echo.
"%PSQL%" -U %SUPERUTENTE% -h localhost -p %PORTA% -c "DO $$ BEGIN IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'esposti') THEN ALTER ROLE esposti WITH LOGIN PASSWORD 'esposti'; ELSE CREATE ROLE esposti WITH LOGIN PASSWORD 'esposti'; END IF; END $$;" -c "CREATE DATABASE esposti OWNER esposti;" -c "ALTER DATABASE esposti OWNER TO esposti;"
if errorlevel 2 goto :errore_accesso

echo.
echo Verifico che l'accesso con utente esposti e password esposti funzioni...
set "PGPASSWORD=esposti"
"%PSQL%" -U esposti -h localhost -p %PORTA% -d esposti -tAc "SELECT 'Connessione riuscita'"
if errorlevel 1 goto :verifica_ko
echo.
echo [OK] Tutto a posto. Ora rilancia avvia-1-api.bat.
goto :fine

:no_psql
echo.
echo [ERRORE] Non trovo "psql" (il programma da riga di comando di Postgres).
echo Se Postgres e' installato, apri pgAdmin, scegli il server, apri lo "Strumento di query"
echo ed esegui queste istruzioni una alla volta:
echo     CREATE ROLE esposti LOGIN PASSWORD 'esposti';
echo     CREATE DATABASE esposti OWNER esposti;
echo Se la prima da' errore perche' l'utente esiste gia', usa invece:
echo     ALTER ROLE esposti LOGIN PASSWORD 'esposti';
echo Poi rilancia avvia-1-api.bat.
goto :fine

:errore_accesso
echo.
echo [ERRORE] Non sono riuscito ad accedere a Postgres come "%SUPERUTENTE%".
echo Controlla la password e rilancia questo file. Se il superutente ha un altro nome,
echo apri questo file con il Blocco note e cambia la riga:  set "SUPERUTENTE=postgres"
echo Se non ricordi la password, scrivimelo: ci sono altre strade.
goto :fine

:verifica_ko
echo.
echo [ERRORE] Il database e' stato creato ma l'accesso con esposti/esposti non riesce.
echo Leggi il messaggio qui sopra e incollalo.

:fine
echo.
pause
