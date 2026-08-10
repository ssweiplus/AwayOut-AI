@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================================
echo AwayOut-AI - Windows first-time setup
echo ============================================================

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if not defined PY_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
  echo.
  echo [ERROR] Python was not found.
  echo Install Python 3.10 or newer from https://www.python.org/downloads/windows/
  echo During installation, enable "Add python.exe to PATH" if offered.
  echo.
  pause
  exit /b 1
)

%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERROR] Python 3.10 or newer is required.
  %PY_CMD% --version
  echo Download: https://www.python.org/downloads/windows/
  echo.
  pause
  exit /b 1
)

for /f "delims=" %%V in ('%PY_CMD% --version 2^>^&1') do echo [OK] %%V

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating local virtual environment: .venv
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto :fail
) else (
  echo [OK] Existing virtual environment found.
)

set "VENV_PY=.venv\Scripts\python.exe"
echo [INFO] Updating pip...
"!VENV_PY!" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [INFO] Installing Python dependencies...
"!VENV_PY!" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo [INFO] Model provider is selected when AwayOut-AI starts.
echo        Supported: Ollama, CodeAgent/OpenAI-compatible HTTP, CodeAgent CLI.

echo.
"!VENV_PY!" doctor.py
set "DOCTOR_RC=!errorlevel!"
if "!DOCTOR_RC!"=="0" (
  echo.
  echo ============================================================
  echo Setup complete. Next time, double-click run_windows.bat
  echo ============================================================
) else (
  echo.
  echo Setup finished, but the base environment check failed above.
)

echo.
pause
exit /b !DOCTOR_RC!

:fail
echo.
echo [ERROR] Setup failed. Review the message above and retry.
echo.
pause
exit /b 1
