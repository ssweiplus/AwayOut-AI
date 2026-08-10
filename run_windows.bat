@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] First run detected. Starting setup...
  call setup_windows.bat
  if errorlevel 1 exit /b %errorlevel%
)

set "VENV_PY=.venv\Scripts\python.exe"

"%VENV_PY%" doctor.py
if errorlevel 1 (
  echo.
  echo Environment is not ready. Run setup_windows.bat after fixing the item above.
  echo.
  pause
  exit /b 1
)

echo.
echo Starting AwayOut-AI...
echo.
"%VENV_PY%" interactive_pair.py
set "RC=%errorlevel%"

echo.
if not "%RC%"=="0" echo AwayOut-AI exited with code %RC%.
pause
exit /b %RC%
