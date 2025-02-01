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

:: Ensure pyinstaller is installed
python -m pip install --upgrade pip pyinstaller
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo Failed to install or update modules. Exiting.
    exit /b 1
)

:: Buiild the executable
pyinstaller MouseTracks.spec

:: Exit the virtual environment
call deactivate
