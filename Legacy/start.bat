@echo off
REM Optimized launcher: checks venv, dependencies, installs if missing, generates a report, and then runs main.py

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

REM Check and install dependencies if needed
echo Upgrading pip and installing requirements from requirements.txt...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt

REM --- System Hardware and AI Report ---

REM Verify for NVIDIA GPU and Ollama, and generate a report
echo Generating system report...
for /f %%i in ('powershell -Command "Get-Date -format 'yyyyMMdd-HHmmss'"') do set TIMESTAMP=%%i
set REPORT_FILE=rapport_Ollama_%TIMESTAMP%.txt

(
    echo Report generated on %DATE% at %TIME%
    echo.
) > %REPORT_FILE%

REM Check for NVIDIA GPU
nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: NVIDIA GPU not found or nvidia-smi is not in your PATH.
    (
        echo === NVIDIA GPU Status ===
        echo NVIDIA GPU not found or nvidia-smi command failed.
    ) >> %REPORT_FILE%
) else (
    echo NVIDIA GPU detected.
    (
        echo === NVIDIA GPU Status ===
        nvidia-smi
    ) >> %REPORT_FILE%
)

REM Check for Ollama
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Ollama not found. Please ensure it is installed and in your PATH.
    (
        echo.
        echo === Ollama Status ===
        echo Ollama not found.
    ) >> %REPORT_FILE%
) else (
    echo Ollama detected.
    (
        echo.
        echo === Ollama Models List ===
        ollama list
    ) >> %REPORT_FILE%
)

echo Report saved to %REPORT_FILE%
echo.

REM --- Launching Application ---
echo Starting the main application...
python main.py

pause
