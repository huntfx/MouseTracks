@echo off
:: Check the virtual environment exists
if not exist ".venv" (
    echo Virtual Environment does not exist.
    echo Please create it first with `python -m venv .venv` using Python 3.11 or later.
    pause
    exit /b 1
)

:: Enter the virtual environment
call .venv\Scripts\activate

:: Ensure all modules are installed
python -m pip install --upgrade pip
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo Failed to install or update modules. Exiting.
    exit /b 1
)

:: Run the application entry point
python launch.py %*

:: Exit the virtual environment
call deactivate
