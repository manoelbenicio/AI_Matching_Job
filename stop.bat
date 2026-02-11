@echo off
REM ========================================================
REM AI Job Matcher — Stop (Docker Compose)
REM ========================================================

echo.
echo ========================================================
echo   AI Job Matcher — Stopping Docker Stack
echo ========================================================
echo.

echo [1/2] Stopping containers...
docker compose down
if errorlevel 1 (
    echo [WARNING] docker compose down failed, trying legacy compose file...
    docker-compose -f docker-compose.postgres.yml down 2>nul
)

echo [2/2] Done.

echo.
echo ========================================================
echo   All Services Stopped!
echo ========================================================
echo.
echo   To restart:  start.bat
echo   To remove volumes (reset DB):  docker compose down -v
echo.
pause
