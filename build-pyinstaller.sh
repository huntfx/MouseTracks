#!/bin/bash

# Exit immediately if any command fails
set -e

# Check if the virtual environment directory exists
if [ ! -d ".venv" ]; then
    echo "Virtual Environment does not exist."
    echo "Please create it first with 'python3 -m venv .venv' using Python 3.11 or later."
    exit 1
fi

# Enter the virtual environment
source .venv/bin/activate

# Ensure all modules are installed/updated
python -m pip install --upgrade pip
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade -r requirements-build-pyinstaller.txt

# Build the executable
pyinstaller MouseTracks.spec

# Exit the virtual environment
deactivate
