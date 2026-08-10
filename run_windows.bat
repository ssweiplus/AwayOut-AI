@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul

if not exist ".venv\Scripts\python.exe" goto :first_setup
goto :run

:first_setup
echo [INFO] First run detected. Starting setup...
call setup_windows.bat
set "SETUP_RC=!errorlevel!"
if not "!SETUP_RC!"=="0" exit /b !SETUP_RC!

:run
set "VENV_PY=.venv\Scripts\python.exe"

"!VENV_PY!" doctor.py
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
"!VENV_PY!" interactive_pair.py
set "RC=!errorlevel!"

echo.
if not "!RC!"=="0" echo AwayOut-AI exited with code !RC!.
pause
exit /b !RC!
