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

:: Retrieve the version from the Python module
for /f "delims=" %%V in ('python -c "from mousetracks2 import __version__; print(__version__)"') do set VERSION=%%V

:: Check if the version was retrieved successfully
if not defined VERSION (
    echo Failed to retrieve version. Exiting.
    exit /b 1
)

:: Write out the executable version info
pyivf-make_version --outfile "build/version.rc" --version %VERSION% --file-description "MouseTracks %VERSION%" --internal-name "MouseTracks" --legal-copyright "Peter Hunt" --original-filename "MouseTracks.exe" --product-name "MouseTracks %VERSION%" --language 0x0809

:: Build the executable
pyinstaller MouseTracks.spec

:: Exit the virtual environment
call deactivate
