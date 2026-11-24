@echo off
rem ---------------------------------------------------------------------------
rem  HozoorYar production server launcher (run by the "HozoorYar Server" task).
rem  Serves the API and the prebuilt admin panel on port 8000.
rem  Restarts uvicorn if it ever exits, so the service self-heals.
rem ---------------------------------------------------------------------------
setlocal
set "ROOT=C:\Users\HP\Documents\attendance-app"
cd /d "%ROOT%\backend"

if not exist "data" mkdir "data"

rem Persistent database: backend\data\attendance.db (survives reboots).
set "DATABASE_URL=sqlite:///./data/attendance.db"
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"

:loop
"%ROOT%\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers >> "%ROOT%\server.log" 2>&1
echo [%date% %time%] uvicorn exited, restarting in 5s >> "%ROOT%\server.log"
timeout /t 5 /nobreak >nul
goto loop
