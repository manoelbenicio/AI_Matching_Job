@echo off
REM ========================================================
REM AI Job Matcher — Stop All Services
REM ========================================================
REM Stops: PostgreSQL + FastAPI Backend + Next.js Frontend
REM ========================================================

echo.
echo ========================================================
echo   AI Job Matcher — Stopping All Services
echo ========================================================
echo.

REM --- Show what's running before stopping ---
echo [1/3] Current container status:
docker compose ps 2>nul
echo.

REM --- Stop all containers ---
echo [2/3] Stopping all containers...
docker compose down
if errorlevel 1 (
    echo [WARNING] docker compose down had issues.
    echo Trying to force-stop all project containers...
    docker compose down --remove-orphans 2>nul
)

REM --- Verify everything is stopped ---
echo.
echo [3/3] Verifying all containers stopped...
docker compose ps 2>nul
echo.

echo ========================================================
echo   All Services Stopped!
echo ========================================================
echo.
echo   To restart:           start.bat
echo   To reset DB:          docker compose down -v
echo   To remove all data:   docker compose down -v --rmi all
echo.
echo ========================================================
echo.
pause
