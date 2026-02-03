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

:: Retrieve the version
set PYTHON_COMMAND_TO_GET_VERSION="from mousetracks2 import __version__; print(__version__)"
for /f "delims=" %%V in ('python -c %PYTHON_COMMAND_TO_GET_VERSION% 2^>nul') do set VERSION=%%V

if not defined VERSION (
    echo Failed to detect version. Exiting.
    exit /b 1
)

:: Check if ISCC is already on the PATH
where ISCC >nul 2>nul
if %errorlevel% equ 0 set "ISCC_PATH=ISCC"
:: Search Program Files (x86)
if not defined ISCC_PATH (
    for /d %%D in ("%ProgramFiles(x86)%\Inno Setup*") do (
        if exist "%%D\ISCC.exe" set "ISCC_PATH=%%D\ISCC.exe"
    )
)
:: Search Program Files
if not defined ISCC_PATH (
    for /d %%D in ("%ProgramFiles%\Inno Setup*") do (
        if exist "%%D\ISCC.exe" set "ISCC_PATH=%%D\ISCC.exe"
    )
)

:: Set environment variables (to match build-executable.yml)
set "EXE_BASENAME=MouseTracks-%VERSION%-windows-x64"
set "FULL_EXE_NAME=%EXE_BASENAME%.exe"
set "INSTALLER_BASENAME=%EXE_BASENAME%-setup"
set "FULL_INSTALLER_NAME=%INSTALLER_BASENAME%.exe"

set "SOURCE_BASE_NAME=dist\%EXE_BASENAME%"
set "DEST_BASE_NAME=dist\%INSTALLER_BASENAME%"

:: Check if the source file actually exists in dist
if not exist "dist\%SOURCE_EXE_NAME%" (
    echo Error: Source file not found: dist\%SOURCE_EXE_NAME%
    echo Did you run build-pyinstaller.bat / build-nuitka.bat first?
    exit /b 1
)

:: Run or warn if not found
if defined ISCC_PATH (
    echo --- Building Installer using "%ISCC_PATH%" ---
    echo Source: %SOURCE_EXE_NAME%
    "%ISCC_PATH%" /DMyAppVersion="%VERSION%" /DMySourceBaseName="%SOURCE_BASE_NAME%" /DMyDestinationBaseName="%DEST_BASE_NAME%" "MouseTracks.iss"
    if errorlevel 1 (
        echo Warning: Installer creation failed.
    ) else (
        echo Installer created successfully: %DEST_BASE_NAME%.exe
    )
) else (
    echo -------------------------------------------------------------------
    echo WARNING: Inno Setup Compiler ^(ISCC.exe^) was not found.
    echo.
    echo Please ensure Inno Setup is installed or added to your system PATH.
    echo https://jrsoftware.org/isdl.php
    echo -------------------------------------------------------------------
)

:: Exit the virtual environment
call deactivate
