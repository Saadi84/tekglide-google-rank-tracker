@echo off
title TEKGLIDE GOOGLE RANK TRACKER V10
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo First-time setup chal raha hai...
  py -m venv .venv 2>nul || python -m venv .venv
  if errorlevel 1 goto :python_error
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :install_error
)

echo.
echo USA VPN connected rehna chahiye.
echo Tracker start ho raha hai...
echo.
".venv\Scripts\python.exe" rank_tracker.py %*
echo.
pause
exit /b

:python_error
echo Python nahi mila. Python 3 install karke "Add Python to PATH" select karein.
pause
exit /b 1

:install_error
echo Selenium install nahi hua. Internet check karke dobara run karein.
pause
exit /b 1

