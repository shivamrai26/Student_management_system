@echo off
REM One click: starts the SRMS server, waits for it, then opens Chrome.
cd /d "%~dp0"

set "BACKEND=%~dp0srms-backend"
set "URL=http://127.0.0.1:8000"

if not exist "%BACKEND%\.venv\Scripts\python.exe" (
    echo Installing for the first time, this takes a minute...
    python -m venv "%BACKEND%\.venv"
    "%BACKEND%\.venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
    "%BACKEND%\.venv\Scripts\python.exe" -m pip install --quiet -r "%BACKEND%\requirements.txt"
)

if not exist "%~dp0srms-frontend\index.html" (
    echo ERROR: the srms-frontend folder is missing at "%~dp0srms-frontend"
    echo The page cannot load without it. Press any key to close.
    pause >nul
    exit /b 1
)

REM Already running? Then just open the browser.
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8000 -State Listen -EA SilentlyContinue) { exit 0 } else { exit 1 }" 2>nul
if %errorlevel%==0 (
    echo Server is already running.
    start "" "%URL%"
    exit /b 0
)

echo Starting the server in a separate window... keep it open.
start "SRMS server" cmd /k "cd /d "%BACKEND%" && .venv\Scripts\python.exe -m uvicorn main:app --port 8000"

REM Wait for it to answer before launching the browser.
echo Waiting for the server...
powershell -NoProfile -Command ^
  "$ok=$false; foreach($i in 1..40){ try { $r=Invoke-WebRequest -Uri '%URL%/api/health' -TimeoutSec 2 -UseBasicParsing; if($r.StatusCode -eq 200){$ok=$true; break} } catch { Start-Sleep -Milliseconds 500 } } ; if(-not $ok){ Write-Host 'Server did not start. See the SRMS server window for the error.'; exit 1 }"

if errorlevel 1 (
    echo.
    echo Could not reach the server. Press any key to close.
    pause >nul
    exit /b 1
)

echo Opening %URL% in your default browser...
start "" "%URL%"
echo.
echo All set. Close the "SRMS server" window to stop the app.
timeout /t 5 >nul
