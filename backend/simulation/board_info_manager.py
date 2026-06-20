# board_info_manager.py
import json
import os
import platform

if platform.system() == "Windows":
    BOARD_INFO_PATH = os.path.join(os.getcwd(), "board_info.json")
else:
    BOARD_INFO_PATH = os.path.join(os.getcwd(), "board_info.json")

def load_board_info() -> dict:
    if not os.path.exists(BOARD_INFO_PATH):
        return {}
    with open(BOARD_INFO_PATH, "r") as f:
        return json.load(f)

def get_ai_channel_count() -> int:
    info = load_board_info()
    return info.get("subsystems_available", {}).get("analog_input", {}).get("channel_count", 4)

def get_ao_channel_count() -> int:
    info = load_board_info()
    return info.get("subsystems_available", {}).get("analog_output", {}).get("channel_count", 4)

def get_ai_channel_names() -> dict:
    info = load_board_info()
    channels = info.get("subsystems_available", {}).get("analog_input", {}).get("physical_channels", [])
    return {i+1: name for i, name in enumerate(channels)}

def get_ao_channel_names() -> dict:
    info = load_board_info()
    channel_count = info.get("subsystems_available", {}).get("analog_output", {}).get("channel_count", 4)
    return {i+1: f"Ch-{i+1}" for i in range(channel_count)}


# -------- Digital helpers (new) -------- #
def get_di_channel_count() -> int:
    info = load_board_info()
    return info.get("subsystems_available", {}).get("digital_input", {}).get("channel_count", 4)

def get_do_channel_count() -> int:
    info = load_board_info()
    return info.get("subsystems_available", {}).get("digital_output", {}).get("channel_count", 4)

def get_di_channels() -> dict:
    count = get_di_channel_count()
    return {i+1: f"Ch-{i+1}" for i in range(count)}

def get_do_channels() -> dict:
    count = get_do_channel_count()
    return {i+1: f"Ch-{i+1}" for i in range(count)}



