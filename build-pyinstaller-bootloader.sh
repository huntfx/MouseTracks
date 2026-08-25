#!/bin/bash

# Exit immediately if any command fails
set -e

# This should match the version requirements-build-pyinstaller.txt
PYINSTALLER_VERSION="v6.11.1"

# Check the virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual Environment does not exist."
    echo "Please create it first with 'python3 -m venv .venv' using Python 3.11 or later."
    exit 1
fi

# Enter the virtual environment
echo "--- Activating virtual environment ---"
source .venv/bin/activate

# Create a clean build directory
echo "--- Preparing build directory ---"
rm -rf build
mkdir build

# Clone the specified version of PyInstaller
echo "--- Cloning PyInstaller ${PYINSTALLER_VERSION} ---"
git clone --branch ${PYINSTALLER_VERSION} --depth 1 https://github.com/pyinstaller/pyinstaller.git build/pyinstaller

# Build the bootloader
echo "--- Building PyInstaller Bootloader ---"
cd build/pyinstaller/bootloader
python ./waf distclean all
cd ..

# Install the new package
echo "--- Installing custom PyInstaller from build directory ---"
pip install wheel --upgrade
pip install .
cd ../..

# Exit the virtual environment
deactivate
echo "--- Virtual environment deactivated ---"
echo "--- PyInstaller bootloader build and installation complete! ---"
