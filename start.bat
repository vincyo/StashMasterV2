@echo off
REM StashMaster V2 Launcher: checks venv, installs dependencies, and runs main.py

REM Set venv directory name
set VENV_DIR=.venv

REM Check if venv exists and is valid
if not exist %VENV_DIR%\Scripts\activate.bat (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment. Please ensure Python is installed and in your PATH.
        pause
        exit /b 1
    )
)

REM Activate venv
call %VENV_DIR%\Scripts\activate.bat

REM Add Ollama to PATH if installed at E:\Ollama
if exist E:\Ollama\ollama.exe set PATH=E:\Ollama;%PATH%

REM Check and install dependencies if needed
echo Installing/updating dependencies...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1
echo Dependencies ready.
echo.

REM --- Launching Application ---
echo Starting the main application...
python main.py

pause
