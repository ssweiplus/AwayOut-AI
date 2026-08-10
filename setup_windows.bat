@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================================
echo AwayOut-AI - Windows first-time setup
echo ============================================================

set "PY_CMD="
where py >nul 2>nul
if %errorlevel%==0 set "PY_CMD=py -3"
if not defined PY_CMD (
  where python >nul 2>nul
  if %errorlevel%==0 set "PY_CMD=python"
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
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [INFO] Installing Python dependencies...
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

where ollama >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ACTION REQUIRED] Ollama is not installed or is not on PATH.
  echo AwayOut-AI uses Ollama only for the local Attacker and Judge models.
  echo Opening the official Windows download page...
  start "" "https://ollama.com/download/windows"
  echo After installing Ollama, run setup_windows.bat again.
  echo.
  pause
  exit /b 2
)

echo [OK] Ollama command found.

powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://127.0.0.1:11434/api/tags; exit 0 } catch { exit 1 }" >nul 2>nul
if errorlevel 1 (
  echo [INFO] Ollama API is not responding. Trying to start 'ollama serve'...
  start "AwayOut-AI Ollama" /min cmd /c "ollama serve"
  timeout /t 3 /nobreak >nul
)

powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 http://127.0.0.1:11434/api/tags; exit 0 } catch { exit 1 }" >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERROR] Ollama is installed but the API is not reachable at http://127.0.0.1:11434
  echo On normal Windows installs, launch Ollama from the Start menu and retry.
  echo.
  pause
  exit /b 3
)

echo [OK] Ollama API is reachable.

for /f %%C in ('powershell -NoProfile -Command "$j=Invoke-RestMethod http://127.0.0.1:11434/api/tags; @($j.models).Count"') do set "MODEL_COUNT=%%C"
if "%MODEL_COUNT%"=="0" (
  echo.
  echo [INFO] No Ollama model is installed.
  set /p "PULL_MODEL=Download the default 'mistral' model now? [Y/n]: "
  if /I not "%PULL_MODEL%"=="n" (
    echo [INFO] Running: ollama pull mistral
    ollama pull mistral
    if errorlevel 1 (
      echo [WARN] Model download failed. You can retry later with: ollama pull mistral
    )
  )
) else (
  echo [OK] At least one Ollama model is already installed.
)

echo.
"%VENV_PY%" doctor.py
set "DOCTOR_RC=%errorlevel%"
if "%DOCTOR_RC%"=="0" (
  echo.
  echo ============================================================
  echo Setup complete. Next time, double-click run_windows.bat
  echo ============================================================
) else (
  echo.
  echo Setup finished, but the environment check still reports an item above.
)

echo.
pause
exit /b %DOCTOR_RC%

:fail
echo.
echo [ERROR] Setup failed. Review the message above and retry.
echo.
pause
exit /b 1
