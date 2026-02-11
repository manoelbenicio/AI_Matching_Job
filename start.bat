@echo off
REM ========================================================
REM AI Job Matcher - Complete Scoring Solution Bootstrap
REM ========================================================
REM This script starts ALL services with a single command:
REM   - PostgreSQL Database (Docker)
REM   - Metabase Analytics (Docker)  
REM   - Streamlit Dashboard
REM   - Batch Scoring Service (optional)
REM ========================================================

echo.
echo ========================================================
echo   AI Job Matcher - Complete Scoring Solution
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

echo [1/6] Starting Docker containers (PostgreSQL + Metabase)...
docker-compose -f docker-compose.postgres.yml up -d
if errorlevel 1 (
    echo [WARNING] Docker compose failed, trying to start postgres container directly...
    docker start job_matcher_postgres 2>nul || docker run -d --name job_matcher_postgres -e POSTGRES_USER=job_matcher -e POSTGRES_PASSWORD=JobMatcher2024! -e POSTGRES_DB=job_matcher -p 5432:5432 postgres:15
)

echo.
echo [2/6] Waiting for database to be ready...
timeout /t 10 /nobreak >nul

REM Test database connection
python -c "import psycopg2; psycopg2.connect('host=127.0.0.1 port=5432 dbname=job_matcher user=job_matcher password=JobMatcher2024!')" 2>nul
if errorlevel 1 (
    echo [WARNING] Database not ready yet, waiting 10 more seconds...
    timeout /t 10 /nobreak >nul
)

echo.
echo [3/6] Installing/Updating Python dependencies...
pip install -r requirements.txt --quiet 2>nul

echo.
echo [4/6] Starting Streamlit Dashboard...
start "Streamlit Dashboard" cmd /c "streamlit run dashboard.py --server.headless true --server.port 8501"

echo.
echo [5/6] Opening dashboards in browser...
timeout /t 5 /nobreak >nul
start http://localhost:8501

REM Check if Metabase is running
docker ps | findstr metabase >nul 2>&1
if not errorlevel 1 (
    start http://localhost:3000
)

echo.
echo ========================================================
echo   All Services Started Successfully!
echo ========================================================
echo.
echo   DASHBOARDS:
echo   -----------
echo   Streamlit Dashboard: http://localhost:8501
echo   Metabase Dashboard:  http://localhost:3000
echo.
echo   BATCH SCORING COMMANDS:
echo   -----------------------
echo   Start batch scoring:    python run_batch_score.py
echo   Import Excel jobs:      python import_jobs_smart.py jobs.xlsx
echo   Reprocess scored jobs:  python reprocess_scored_jobs.py
echo.
echo   DATA MANAGEMENT:
echo   ----------------
echo   Check database stats:   python -c "from database import Database; db=Database(); print(db.get_stats())"
echo   Export qualified jobs:  Use dashboard Export CSV feature
echo.
echo   TO STOP ALL SERVICES:
echo   ---------------------
echo   Run: stop.bat
echo.
echo ========================================================
echo.
echo [6/6] Ready! Press any key to start batch scoring, or close this window.
echo.
set /p choice="Start batch scoring now? (Y/N): "
if /i "%choice%"=="Y" (
    echo.
    echo Starting batch scoring...
    python run_batch_score.py
) else (
    echo.
    echo Batch scoring skipped. Run 'python run_batch_score.py' when ready.
)

pause
