#!/bin/sh
if [ ! -d ".myenv" ]; then
    echo "[INFO] Virtual environment not found. Creating..."
    ./install_venv.sh
else
    echo "[INFO] Activating existing virtual environment..."
    . .myenv/bin/activate
fi

which python3
export PYTHONPATH=$(pwd)
