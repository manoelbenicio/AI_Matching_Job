@echo off
REM ========================================================
REM AI Job Matcher — Start (Docker Compose)
REM ========================================================
REM Starts:  PostgreSQL 16 + FastAPI Backend + Next.js Frontend
REM URLs:    http://localhost:3000  (Frontend)
REM          http://localhost:8000/docs  (API Swagger)
REM ========================================================

echo.
echo ========================================================
echo   AI Job Matcher — Starting Docker Stack
echo ========================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop first.
    pause
    exit /b 1
)
echo [OK] Docker is running

echo.
echo [1/3] Building and starting containers...
docker compose up --build -d
if errorlevel 1 (
    echo [ERROR] docker compose failed!
    pause
    exit /b 1
)

echo.
echo [2/3] Waiting for services to be healthy...
timeout /t 15 /nobreak >nul

REM Health check
echo.
echo Checking backend health...
curl -s http://localhost:8000/api/health >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Backend not ready yet, waiting 10 more seconds...
    timeout /t 10 /nobreak >nul
)

echo.
echo [3/3] Opening in browser...
start http://localhost:3000
timeout /t 2 /nobreak >nul
start http://localhost:8000/docs

echo.
echo ========================================================
echo   All Services Started!
echo ========================================================
echo.
echo   Frontend:       http://localhost:3000
echo   API Swagger:    http://localhost:8000/docs
echo   PostgreSQL:     localhost:5432
echo.
echo   COMMANDS:
echo   ---------
echo   View logs:      docker compose logs -f
echo   Stop:           stop.bat  (or: docker compose down)
echo   Rebuild:        docker compose up --build -d
echo.
echo ========================================================
echo.
pause
