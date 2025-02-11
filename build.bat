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
python -m pip install --upgrade -r requirements-build.txt
if errorlevel 1 (
    echo Failed to install or update modules. Exiting.
    exit /b 1
)

:: Retrieve the version from the latest Git tag
for /f "delims=" %%V in ('git describe --tags --abbrev=0 2^>nul') do set VERSION=%%V

:: If no tag is found, default to 0.0
if not defined VERSION set VERSION=0.0

:: Write out the executable version info
mkdir build
pyivf-make_version --outfile "build/version.rc" --version %VERSION% --file-description "MouseTracks %VERSION%" --internal-name "MouseTracks"  --original-filename "MouseTracks.exe" --product-name "MouseTracks %VERSION%" --legal-copyright "Peter Hunt" --company-name "Peter Hunt"

:: Build the executable
pyinstaller MouseTracks.spec

:: Exit the virtual environment
call deactivate
