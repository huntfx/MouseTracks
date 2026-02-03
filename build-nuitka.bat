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
python -m pip install --upgrade pip
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade -r requirements-build-nuitka.txt
if errorlevel 1 (
    echo Failed to install or update modules. Exiting.
    exit /b 1
)

:: Retrieve the version
set PYTHON_COMMAND_TO_GET_VERSION="from mousetracks2 import __version__; print(__version__)"
for /f "delims=" %%V in ('python -c %PYTHON_COMMAND_TO_GET_VERSION% 2^>nul') do set VERSION=%%V

if not defined VERSION (
    echo Failed to detect version. Exiting.
    exit /b 1
)

:: Build the executable
::echo --- Building Application (MouseTracks-%VERSION%-windows-x64.exe) ---
::python -m nuitka ^
::  --standalone ^
::  --onefile ^
::  --prefer-source-code ^
::  --output-dir=dist ^
::  --output-filename=MouseTracks-%VERSION%-windows-x64.exe ^
::  --plugin-enable=pyside6 ^
::  --include-data-file=config/colours.txt=config/colours.txt ^
::  --include-data-file=config/AppList.txt=config/AppList.txt ^
::  --include-data-file=config/language/strings/en_GB.ini=config/language/strings/en_GB.ini ^
::  --include-data-file=config/language/keyboard/keys/en_GB.ini=config/language/keyboard/keys/en_GB.ini ^
::  --include-data-file=config/language/keyboard/layout/en_US.txt=config/language/keyboard/layout/en_US.txt ^
::  --include-data-file=resources/images/icon.png=resources/images/icon.png ^
::  --windows-icon-from-ico=resources/images/icon.ico ^
::  --product-name="Mouse Tracks %VERSION%" ^
::  --file-description="Mouse Tracks %VERSION%" ^
::  --product-version=%VERSION% ^
::  --file-version=%VERSION% ^
::  --copyright="Peter Hunt" ^
::  launch.py

if errorlevel 1 (
    echo Main application build failed.
    call deactivate
    exit /b 1
)

echo --- Building Launcher (MouseTracks.exe) ---
python -m nuitka ^
  --standalone ^
  --onefile ^
  --prefer-source-code ^
  --output-dir=dist ^
  --output-filename=MouseTracks.exe ^
  --windows-icon-from-ico=resources/images/icon.ico ^
  launcher.py

if errorlevel 1 (
    echo Launcher build failed.
    call deactivate
    exit /b 1
)

:: Exit the virtual environment
call deactivate
