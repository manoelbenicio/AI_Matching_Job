@echo off
REM ========================================================
REM AI Job Matcher — Bootstrap (Start All Services)
REM ========================================================
REM Services:
REM   1. PostgreSQL 16    (port 5432)
REM   2. FastAPI Backend  (port 8000)  — depends on PostgreSQL
REM   3. Next.js Frontend (port 3000)  — depends on Backend
REM
REM URLs:
REM   Frontend:    http://localhost:3000
REM   API Swagger: http://localhost:8000/docs
REM   API Health:  http://localhost:8000/api/health
REM   PostgreSQL:  localhost:5432
REM ========================================================

echo.
echo ========================================================
echo   AI Job Matcher — Starting All Services
echo ========================================================
echo.

REM --- Pre-flight: Check Docker ---
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop first.
    pause
    exit /b 1
)
echo [OK] Docker is running

REM --- Pre-flight: Check .env file ---
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo Copy .env.example to .env and fill in your values.
    pause
    exit /b 1
)
echo [OK] .env file found

REM --- Stop any existing containers first for clean start ---
echo.
echo [1/4] Stopping any existing containers...
docker compose down >nul 2>&1
echo      Done.

REM --- Build and start all services ---
echo.
echo [2/4] Building and starting all containers...
echo      Services: PostgreSQL + FastAPI + Next.js
docker compose up --build -d
if errorlevel 1 (
    echo [ERROR] docker compose up failed!
    echo.
    echo Troubleshooting:
    echo   - Check Docker Desktop is running
    echo   - Check ports 3000, 5432, 8000 are free
    echo   - Run: docker compose logs
    pause
    exit /b 1
)

REM --- Wait for health checks ---
echo.
echo [3/4] Waiting for services to be healthy...
echo      PostgreSQL...
timeout /t 10 /nobreak >nul

REM Check PostgreSQL
docker compose exec -T db pg_isready -U job_matcher >nul 2>&1
if errorlevel 1 (
    echo      [WAIT] PostgreSQL not ready, waiting 10 more seconds...
    timeout /t 10 /nobreak >nul
)
echo      [OK] PostgreSQL ready

REM Check Backend
echo      FastAPI Backend...
curl -s -o nul -w "%%{http_code}" http://localhost:8000/api/health >nul 2>&1
if errorlevel 1 (
    echo      [WAIT] Backend not ready, waiting 15 more seconds...
    timeout /t 15 /nobreak >nul
)
echo      [OK] Backend ready

REM Check Frontend
echo      Next.js Frontend...
timeout /t 5 /nobreak >nul
echo      [OK] Frontend ready

REM --- Open browser ---
echo.
echo [4/4] Opening in browser...
start http://localhost:3000
timeout /t 2 /nobreak >nul
start http://localhost:8000/docs

REM --- Summary ---
echo.
echo ========================================================
echo   ALL SERVICES STARTED SUCCESSFULLY!
echo ========================================================
echo.
echo   Services Running:
echo   ---------------------------------------------------------
echo   PostgreSQL 16       localhost:5432     [DB]
echo   FastAPI Backend     http://localhost:8000/docs  [API]
echo   Next.js Frontend    http://localhost:3000       [UI]
echo   ---------------------------------------------------------
echo.
echo   COMMANDS:
echo   ---------
echo   View logs:          docker compose logs -f
echo   View specific log:  docker compose logs -f backend
echo   Stop all:           stop.bat  (or: docker compose down)
echo   Rebuild all:        start.bat  (auto-rebuilds)
echo   Reset DB:           docker compose down -v
echo   Container status:   docker compose ps
echo.
echo ========================================================
echo.
pause
