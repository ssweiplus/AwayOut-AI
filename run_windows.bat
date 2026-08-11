@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul

set "PY_CMD="
set "ENV_MODE="

if defined CONDA_PREFIX (
  if exist "%CONDA_PREFIX%\python.exe" (
    set "PY_CMD="%CONDA_PREFIX%\python.exe""
    set "ENV_MODE=conda"
    echo [OK] Using active Conda environment: %CONDA_PREFIX%
  )
)

if not defined PY_CMD (
  if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=".venv\Scripts\python.exe""
    set "ENV_MODE=venv"
  )
)

if not defined PY_CMD goto :first_setup
goto :run

:first_setup
echo [INFO] No active Conda environment or project .venv found. Starting setup...
call setup_windows.bat
set "SETUP_RC=!errorlevel!"
if not "!SETUP_RC!"=="0" exit /b !SETUP_RC!

if defined CONDA_PREFIX (
  if exist "%CONDA_PREFIX%\python.exe" (
    set "PY_CMD="%CONDA_PREFIX%\python.exe""
    set "ENV_MODE=conda"
  )
)
if not defined PY_CMD if exist ".venv\Scripts\python.exe" (
  set "PY_CMD=".venv\Scripts\python.exe""
  set "ENV_MODE=venv"
)
if not defined PY_CMD (
  echo [ERROR] No usable Python environment was found after setup.
  pause
  exit /b 1
)

:run
%PY_CMD% doctor.py
if errorlevel 1 (
  echo.
  echo Environment is not ready. Run setup_windows.bat after fixing the item above.
  echo.
  pause
  exit /b 1
)

echo.
if /I "!ENV_MODE!"=="conda" (
  echo Starting AwayOut-AI with active Conda environment...
) else (
  echo Starting AwayOut-AI with project .venv...
)
echo.
%PY_CMD% interactive_pair.py
set "RC=!errorlevel!"

echo.
if not "!RC!"=="0" echo AwayOut-AI exited with code !RC!.
pause
exit /b !RC!
