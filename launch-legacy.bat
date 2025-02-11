@echo off
:: Check the virtual environment exists
if not exist ".venv-legacy" (
    echo Virtual Environment does not exist.
    echo Please create it first with `python -m venv .venv-legacy` using Python 3,
    echo  or `python -m virtualenv .venv-legacy` with Python 2.
    pause
    exit /b 1
)

:: Enter the virtual environment
call .venv-legacy\Scripts\activate

:: Ensure all modules are installed
python -m pip install --upgrade pip
python -m pip install --upgrade -r requirements-legacy.txt
if errorlevel 1 (
    echo Failed to install or update modules. Exiting.
    exit /b 1
)

:: Run the application entry point
python launch-legacy.py %*

:: Exit the virtual environment
call deactivate
