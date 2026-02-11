@echo off
REM ========================================================
REM AI Job Matcher - Stop All Services
REM ========================================================

echo.
echo ========================================================
echo   AI Job Matcher - Stopping All Services
echo ========================================================
echo.

echo [1/4] Stopping Streamlit Dashboard...
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Streamlit Dashboard" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

echo [2/4] Stopping batch scoring processes...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO TABLE ^| findstr python') do (
    wmic process where "processid=%%a and commandline like '%%run_batch_score%%'" delete >nul 2>&1
)

echo [3/4] Stopping Docker containers...
docker-compose -f docker-compose.postgres.yml down 2>nul

echo [4/4] Cleaning up temporary files...
del /Q generated_cvs\*.tmp 2>nul

echo.
echo ========================================================
echo   All Services Stopped!
echo ========================================================
echo.
echo   To restart all services, run: start.bat
echo.
pause
