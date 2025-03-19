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

:: Retrieve the version from the latest Git tag
for /f "delims=" %%V in ('git describe --tags --abbrev=0 2^>nul') do set VERSION=%%V

:: If no tag is found, default to 0.0
if not defined VERSION set VERSION=1.0

:: Build the executable
python -m nuitka ^
  --standalone ^
  --onefile ^
  --prefer-source-code ^
  --output-dir=dist ^
  --output-filename=MouseTracks.exe ^
  --plugin-enable=pyside6 ^
  --include-data-file=config/colours.txt=config/colours.txt ^
  --include-data-file=config/AppList.txt=config/AppList.txt ^
  --include-data-file=config/language/strings/en_GB.ini=config/language/strings/en_GB.ini ^
  --include-data-file=config/language/keyboard/keys/en_GB.ini=config/language/keyboard/keys/en_GB.ini ^
  --include-data-file=config/language/keyboard/layout/en_US.txt=config/language/keyboard/layout/en_US.txt ^
  --include-data-file=resources/images/icon.png=resources/images/icon.png ^
  --windows-icon-from-ico=resources/images/icon.ico ^
  --product-name="Mouse Tracks %VERSION%" ^
  --file-description="Mouse Tracks %VERSION%" ^
  --product-version=%VERSION% ^
  --file-version=%VERSION% ^
  --copyright="Peter Hunt" ^
  launch.py

:: Exit the virtual environment
call deactivate
