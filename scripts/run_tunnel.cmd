@echo off
rem ---------------------------------------------------------------------------
rem  Public access for HozoorYar via ngrok (works behind CGNAT / 4G).
rem  Reads the token and the free static domain from scripts\tunnel.env:
rem      NGROK_AUTHTOKEN=...
rem      NGROK_DOMAIN=your-name.ngrok-free.app
rem  Until that file exists the task simply waits, so it is safe to run early.
rem ---------------------------------------------------------------------------
setlocal
set "ROOT=C:\Users\HP\Documents\attendance-app"

:loop
if not exist "%ROOT%\scripts\tunnel.env" (
  timeout /t 60 /nobreak >nul
  goto loop
)

set "NGROK_AUTHTOKEN="
set "NGROK_DOMAIN="
for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%\scripts\tunnel.env") do set "%%A=%%B"

if "%NGROK_AUTHTOKEN%"=="" (
  timeout /t 60 /nobreak >nul
  goto loop
)
if "%NGROK_DOMAIN%"=="" (
  echo [%date% %time%] tunnel.env has no NGROK_DOMAIN, waiting >> "%ROOT%\tunnel.log"
  timeout /t 60 /nobreak >nul
  goto loop
)

echo [%date% %time%] starting ngrok on https://%NGROK_DOMAIN% >> "%ROOT%\tunnel.log"
"%ROOT%\.tools\ngrok\ngrok.exe" http 8000 --url "https://%NGROK_DOMAIN%" --authtoken "%NGROK_AUTHTOKEN%" --log stdout --log-format logfmt >> "%ROOT%\tunnel.log" 2>&1
echo [%date% %time%] ngrok exited, retrying in 15s >> "%ROOT%\tunnel.log"
timeout /t 15 /nobreak >nul
goto loop
