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
pip install --upgrade pip
pip install --upgrade -r requirements.txt

# Run the application entry point
python3 launch.py "$@"

# Exit the virtual environment
deactivate
