@echo off
REM ============================================
REM  BambuRFID — Deploy Script (Windows)
REM  Starts the backend server and shows status
REM ============================================

cd /d "%~dp0"

echo.
echo ============================================
echo   BambuRFID — Deploy
echo ============================================
echo.

REM 1. Check Python
echo [1/4] Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
)
python --version

REM 2. Install dependencies
echo [2/4] Installing Python dependencies...
python -m pip install -r backend\requirements.txt --quiet 2>nul

REM 3. Kill existing server on port 8000
echo [3/4] Checking port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo   Port 8000 in use ^(PID: %%a^). Stopping...
    taskkill /PID %%a /F >nul 2>&1
    timeout /t 2 /nobreak >nul
)

REM 4. Get local IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
    set LOCAL_IP=%%a
    goto :got_ip
)
set LOCAL_IP=localhost
:got_ip
set LOCAL_IP=%LOCAL_IP: =%

REM 5. Start server
echo [4/4] Starting BambuRFID server...
echo.
echo ============================================
echo   BambuRFID is running!
echo ============================================
echo.
echo   Web UI:       http://localhost:8000
echo   LAN access:   http://%LOCAL_IP%:8000
echo   NFC Bridge:   ws://%LOCAL_IP%:8000/ws/nfc
echo.
echo   Android App:
echo     Download APK from GitHub Actions:
echo     https://github.com/jbrucifer/BambuRFID/actions
echo     Or enter this in the app: %LOCAL_IP%:8000
echo.
echo   Press Ctrl+C to stop the server.
echo.

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

pause
