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
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install or update modules. Exiting.
    exit /b 1
)
:: Ensure type stubs are installed
python -m pip install -r requirements-typecheck.txt --upgrade
if errorlevel 1 (
    echo Failed to install or update modules. Exiting.
    exit /b 1
)

:: Run mypy on the entry point
python -m mypy mousetracks2 launch.py --disallow-untyped-defs --disallow-incomplete-defs

:: Exit the virtual environment
call deactivate
