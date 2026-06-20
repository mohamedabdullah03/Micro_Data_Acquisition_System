#!/bin/sh
echo "-----------------------------------------"
echo "Starting Backend Project"
echo "-----------------------------------------"
echo "Current Dir: $(dirname "$0")"

cd "$(dirname "$0")"

# Activate or create venv
./activate_venv.sh

# Run backend project
python3 main.py
