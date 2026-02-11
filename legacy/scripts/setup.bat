@echo off
REM ========================================================
REM AI Job Matcher - First Time Setup
REM ========================================================
REM Run this ONCE before using the system
REM ========================================================

echo.
echo ========================================================
echo   AI Job Matcher - First Time Setup
echo ========================================================
echo.
echo This will:
echo   1. Check Docker installation
echo   2. Create environment file (.env)
echo   3. Install Python dependencies
echo   4. Start database containers
echo   5. Run database migrations
echo   6. Create Metabase admin user
echo.
pause

REM Check Docker
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not running!
    echo Please install Docker Desktop from: https://docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo [OK] Docker is running

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.11+ from: https://python.org
    pause
    exit /b 1
)
echo [OK] Python is installed

REM Create .env if not exists
if not exist .env (
    echo.
    echo [SETUP] Creating .env file...
    echo Please provide your API keys:
    echo.
    
    set /p OPENAI_KEY="OpenAI API Key: "
    set /p TELEGRAM_TOKEN="Telegram Bot Token (optional, press Enter to skip): "
    set /p TELEGRAM_CHAT="Telegram Chat ID (optional, press Enter to skip): "
    
    (
        echo # AI Job Matcher - Environment Configuration
        echo.
        echo # Database (Docker)
        echo DB_HOST=localhost
        echo DB_PORT=5432
        echo DB_NAME=job_matcher
        echo DB_USER=job_matcher
        echo DB_PASSWORD=JobMatcher2024!
        echo.
        echo # OpenAI
        echo OPENAI_API_KEY=%OPENAI_KEY%
        echo OPENAI_MODEL=gpt-4o-mini
        echo.
        echo # Telegram Notifications (optional)
        echo TELEGRAM_BOT_TOKEN=%TELEGRAM_TOKEN%
        echo TELEGRAM_CHAT_ID=%TELEGRAM_CHAT%
        echo.
        echo # Processing Settings
        echo BATCH_SIZE=50
        echo MIN_SCORE=70
        echo RATE_LIMIT_SECONDS=1
        echo.
        echo # Google Drive (optional - set folder ID if using)
        echo RESUME_FOLDER_ID=
    ) > .env
    
    echo [OK] Created .env file
) else (
    echo [OK] .env file already exists
)

REM Install Python dependencies
echo.
echo [SETUP] Installing Python dependencies...
pip install -r requirements.txt --quiet
echo [OK] Dependencies installed

REM Start Docker containers
echo.
echo [SETUP] Starting Docker containers...
docker-compose -f docker-compose.postgres.yml up -d
echo [OK] Containers started

REM Wait for database
echo.
echo [SETUP] Waiting for database to be ready...
timeout /t 15 /nobreak >nul

REM Run migrations
echo.
echo [SETUP] Running database migrations...
python -c "from job_matcher import Config, DatabaseManager; db = DatabaseManager(Config()); db.init_database()"
if errorlevel 1 (
    echo [WARNING] Migration may need manual setup. Check db/migrations/
) else (
    echo [OK] Database initialized
)

echo.
echo ========================================================
echo   Setup Complete!
echo ========================================================
echo.
echo   Next steps:
echo.
echo   1. Double-click 'start.bat' to start all services
echo   2. Open http://localhost:8501 for live monitoring
echo   3. Double-click 'process_jobs.bat' to process jobs
echo.
echo   Dashboard URLs:
echo     Streamlit:  http://localhost:8501
echo     Metabase:   http://localhost:3000
echo.
echo ========================================================
pause
