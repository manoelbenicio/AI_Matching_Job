@echo off
REM ========================================================
REM AI Job Matcher - Run Job Processing
REM ========================================================

echo.
echo ========================================================
echo   AI Job Matcher - Processing Jobs
echo ========================================================
echo.

set /p BATCH_SIZE="How many jobs to process? (default: 10): "
if "%BATCH_SIZE%"=="" set BATCH_SIZE=10

echo.
echo Processing %BATCH_SIZE% jobs...
echo.

python job_matcher.py --batch-size %BATCH_SIZE%

echo.
echo ========================================================
echo   Processing Complete!
echo ========================================================
echo.
echo View results at: http://localhost:8501
echo.
pause
