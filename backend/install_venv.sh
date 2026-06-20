#!/bin/sh
echo "[INFO] Creating virtual environment..."

# Ensure venv is installed
python3 -m pip install --upgrade pip
python3 -m pip install virtualenv

# Create venv
python3 -m venv .myenv

if [ $? -eq 0 ]; then
    echo "[INFO] Virtual environment created successfully."
    . .myenv/bin/activate
    echo "[INFO] Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "[ERROR] Failed to create virtual environment."
    exit 1
fi
