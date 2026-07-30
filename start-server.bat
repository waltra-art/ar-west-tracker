@echo off
echo ==========================================
echo AR West Tracker - Shared Server
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Install dependencies if needed
echo Checking dependencies...
pip install -q flask flask-cors

echo.
echo Starting server...
echo Server will be available at: http://localhost:5000
echo.
echo Share this address with your team!
echo (Replace 'localhost' with your computer's IP for network access)
echo.
echo Press Ctrl+C to stop the server
echo ==========================================
echo.

python server.py

pause
