@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================================
echo AwayOut-AI - Windows first-time setup
echo ============================================================

set "PY_CMD="
set "ENV_MODE="
set "HAS_UV="

where uv >nul 2>nul
if not errorlevel 1 set "HAS_UV=1"

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
  if defined HAS_UV (
    echo [INFO] No active environment found. Creating project .venv with uv...
    uv venv .venv
    if errorlevel 1 goto :fail
    set "PY_CMD=".venv\Scripts\python.exe""
    set "ENV_MODE=venv"
  ) else (
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
      echo Install Python 3.10+ or install uv, then retry.
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

if defined HAS_UV (
  echo [OK] uv detected. Installing dependencies with uv pip.
  uv pip install --python %PY_CMD% -r requirements.txt
  if errorlevel 1 goto :fail
) else (
  echo [INFO] uv not found. Falling back to pip.
  %PY_CMD% -m pip --version >nul 2>nul
  if errorlevel 1 (
    echo [WARN] pip is missing in the selected Python environment.
    echo [INFO] Trying to repair pip with ensurepip...
    %PY_CMD% -m ensurepip --upgrade
    if errorlevel 1 (
      echo.
      echo [ERROR] pip could not be repaired automatically.
      echo Install uv or recreate the environment with pip support.
      echo.
      pause
      exit /b 1
    )
  )

  echo [INFO] Updating pip...
  %PY_CMD% -m pip install --upgrade pip
  if errorlevel 1 goto :fail

  echo [INFO] Installing Python dependencies...
  %PY_CMD% -m pip install -r requirements.txt
  if errorlevel 1 goto :fail
)

echo.
echo [INFO] Model provider is selected when AwayOut-AI starts.
echo        CodeAgent uses Python Connector only ^(edit codeagent_connector.py^).
echo        Ollama is also supported as an independent provider.

echo.
%PY_CMD% doctor.py
set "DOCTOR_RC=!errorlevel!"
if "!DOCTOR_RC!"=="0" (
  echo.
  echo ============================================================
  if defined HAS_UV (
    echo Setup complete using uv-compatible dependency installation.
  ) else if /I "!ENV_MODE!"=="conda" (
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
