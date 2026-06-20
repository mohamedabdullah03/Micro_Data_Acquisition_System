import os

def detect_board():
    """Auto-detect if running on the board by reading system info."""
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read().strip().lower()
            return "Toradex" in model or "nvidia" in model or "tegra" in model
    except Exception:
        return False

# Read IS_BOARD from environment variable or auto-detect it
IS_BOARD = os.getenv("IS_BOARD", "false").lower() == "true" or detect_board()

# Adjust paths or settings based on the board type
if IS_BOARD:
    print("[INFO] Running on the board, using real CAN, ADC, DAC functionality.")
else:
    print("[INFO] Running locally, using simulated CAN, ADC, DAC.")
