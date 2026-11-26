@echo off
REM Starts the SRMS API on http://127.0.0.1:8000 and serves the front-end too.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
)

echo.
echo   Front-end + API : http://127.0.0.1:8000
echo   API docs        : http://127.0.0.1:8000/docs
echo   Demo logins     : admin/admin123   T1-T2/teach123   CS101-CS106/stud123
echo.
.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000