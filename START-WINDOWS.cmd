@echo off
setlocal
cd /d "%~dp0"
title BD Workspace - keep this window open
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 (
    py -3 app.py
    goto :finished
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 (
    python app.py
    goto :finished
)
echo.
echo Python 3.10 or newer is needed to run BD Workspace.
echo Install Python from https://www.python.org/downloads/windows/
echo Then close this window and double-click START-WINDOWS.cmd again.
echo If Python is already installed, enable its launcher or add it to PATH.
echo.
:finished
pause
