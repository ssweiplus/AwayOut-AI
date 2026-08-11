@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================================
echo AwayOut-AI - Windows first-time setup
echo ============================================================

set "PY_CMD="
set "ENV_MODE="

if defined CONDA_PREFIX (
  if exist "%CONDA_PREFIX%\python.exe" (
    set "PY_CMD="%CONDA_PREFIX%\python.exe""
    set "ENV_MODE=conda"
    echo [OK] Active Conda environment detected: %CONDA_PREFIX%
  )
)

if not defined PY_CMD (
  if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=".venv\Scripts\python.exe""
    set "ENV_MODE=venv"
    echo [OK] Existing project virtual environment found: .venv
  )
)

if not defined PY_CMD (
  set "BASE_PY="
  where py >nul 2>nul
  if not errorlevel 1 set "BASE_PY=py -3"
  if not defined BASE_PY (
    where python >nul 2>nul
    if not errorlevel 1 set "BASE_PY=python"
  )

  if not defined BASE_PY (
    echo.
    echo [ERROR] Python was not found.
    echo Install Python 3.10+ or activate a Conda environment with Python 3.10+.
    echo.
    pause
    exit /b 1
  )

  %BASE_PY% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
  if errorlevel 1 (
    echo.
    echo [ERROR] Python 3.10 or newer is required.
    %BASE_PY% --version
    echo.
    pause
    exit /b 1
  )

  echo [INFO] No active Conda environment found. Creating project .venv...
  %BASE_PY% -m venv .venv
  if errorlevel 1 goto :fail
  set "PY_CMD=".venv\Scripts\python.exe""
  set "ENV_MODE=venv"
)

%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERROR] Selected Python environment must be Python 3.10 or newer.
  %PY_CMD% --version
  echo.
  pause
  exit /b 1
)

for /f "delims=" %%V in ('%PY_CMD% --version 2^>^&1') do echo [OK] %%V
if /I "!ENV_MODE!"=="conda" (
  echo [INFO] Dependencies will be installed into the currently active Conda environment.
) else (
  echo [INFO] Dependencies will be installed into the project-local .venv environment.
)

echo [INFO] Checking pip...
%PY_CMD% -m pip --version >nul 2>nul
if errorlevel 1 (
  echo [WARN] pip is missing in the selected Python environment.
  echo [INFO] Trying to repair pip with ensurepip...
  %PY_CMD% -m ensurepip --upgrade
  if errorlevel 1 (
    echo.
    echo [ERROR] pip could not be repaired automatically.
    if /I "!ENV_MODE!"=="venv" (
      echo Delete the broken .venv folder and run setup_windows.bat again:
      echo   rmdir /s /q .venv
      echo   setup_windows.bat
    ) else (
      echo Repair pip in the active Conda environment, for example:
      echo   conda install pip
    )
    echo.
    pause
    exit /b 1
  )
)

%PY_CMD% -m pip --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] pip is still unavailable after repair.
  pause
  exit /b 1
)

echo [OK] pip is available.
echo [INFO] Updating pip...
%PY_CMD% -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [INFO] Installing Python dependencies...
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo [INFO] Model provider is selected when AwayOut-AI starts.
echo        Recommended: CodeAgent Python Connector ^(edit codeagent_connector.py^).
echo        Also supported: Ollama, CodeAgent/OpenAI-compatible HTTP, CodeAgent CLI.

echo.
%PY_CMD% doctor.py
set "DOCTOR_RC=!errorlevel!"
if "!DOCTOR_RC!"=="0" (
  echo.
  echo ============================================================
  if /I "!ENV_MODE!"=="conda" (
    echo Setup complete using active Conda environment.
    echo Keep this Conda environment activated when using run_windows.bat.
  ) else (
    echo Setup complete. Next time, double-click run_windows.bat
  )
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
