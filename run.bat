@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PY_EXE="

if exist "%~dp0.python-core\python.exe" (
  set "PY_EXE=%~dp0.python-core\python.exe"
) else (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_EXE=python"
)

if "%PY_EXE%"=="" (
  echo Python was not found.
  echo Please install Python 3.10 or later, or run install.py first.
  pause
  exit /b 1
)

"%PY_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or later is required.
  echo Current Python executable: %PY_EXE%
  pause
  exit /b 1
)

"%PY_EXE%" -c "import streamlit" >nul 2>nul
if errorlevel 1 (
  echo Streamlit is not installed in the selected Python environment.
  echo Please run: "%PY_EXE%" -m pip install -r requirements.txt
  pause
  exit /b 1
)

echo Starting AI Ops Agent...
echo Using Python: %PY_EXE%
"%PY_EXE%" -m streamlit run app.py
pause
