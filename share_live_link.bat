@echo off
title TEKGLIDE RANK CHECKER - LIVE PUBLIC LINK
cd /d "%~dp0"

echo ====================================================================
echo             TEKGLIDE RANK CHECKER - LIVE PUBLIC SHARING
echo ====================================================================
echo.
echo [1/3] Checking if local app is running on port 5000...
powershell -Command "$c = Test-NetConnection -ComputerName 127.0.0.1 -Port 5000 -InformationLevel Quiet; if (-not $c) { Write-Host 'WARNING: run_local_app.bat is NOT running! Please start run_local_app.bat first.' -ForegroundColor Yellow } else { Write-Host 'SUCCESS: App is running on port 5000!' -ForegroundColor Green }"
echo.

echo [2/3] Fetching your Tunnel Password...
for /f "tokens=*" %%i in ('powershell -Command "(Invoke-RestMethod -Uri 'https://loca.lt/mytunnelpassword').Trim()"') do set "TUNNEL_PWD=%%i"
echo --------------------------------------------------------------------
echo  TUNNEL PASSWORD (if asked on first open): %TUNNEL_PWD%
echo --------------------------------------------------------------------
echo.

echo [3/3] Starting your Live Public Link...
echo (Keep this window open while sharing. Press Ctrl+C to stop.)
echo.
npx localtunnel --port 5000
echo.
pause
