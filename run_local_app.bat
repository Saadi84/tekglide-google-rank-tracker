@echo off
title TEKGLIDE LOCAL GOOGLE US RANK CHECKER
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 goto :python_error
  set "PYTHON=python"
) else (
  set "PYTHON=py"
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the local Python environment...
  %PYTHON% -m venv .venv
  if errorlevel 1 goto :venv_error
)

if not exist ".venv\Scripts\flask.exe" (
  echo Installing local requirements...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :install_error
)

start "Tekglide Rank Checker Browser" http://127.0.0.1:5000/
echo.
echo Starting the local app at http://127.0.0.1:5000/
echo Keep this window open while using the checker.
echo.
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto :app_error
exit /b 0

:python_error
echo Python was not found. Install Python 3 and enable Add Python to PATH.
pause
exit /b 1

:venv_error
echo The Python virtual environment could not be created.
pause
exit /b 1

:install_error
echo Local requirements could not be installed. Check your internet connection.
pause
exit /b 1

:app_error
echo The local Flask app stopped unexpectedly.
pause
exit /b 1
