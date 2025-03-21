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

:: Delete build/pyinstaller if it exists
IF EXIST "build\pyinstaller" (
    rmdir "build\pyinstaller" /s /q
)

:: Clone the matching PyInstaller version
git clone --branch v6.11.1 --depth 1 https://github.com/pyinstaller/pyinstaller.git build/pyinstaller

:: Build the bootloader
cd build/pyinstaller/bootloader
python ./waf distclean all
cd ..

:: Install the new package
pip install wheel --upgrade
pip install .

:: Exit the virtual environment
cd ../..
call deactivate
