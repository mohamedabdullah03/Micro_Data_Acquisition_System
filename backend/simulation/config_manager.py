import os, json, platform, threading,logging
from fastapi import HTTPException


# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Use the SAME config path as your FastAPI application
if platform.system() == "Windows":
    # Point to config.json in your current backend directory
    CONFIG_PATH = os.path.join(os.getcwd(), "config.json")
else:
    CONFIG_PATH = "/root/udaq/config/config.json"

CONFIG_LOCK = threading.Lock()


def load_config():
    """Load full config.json, or return empty dict if not exists."""
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config: dict):
    """Save updated config.json atomically with lock."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with CONFIG_LOCK:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)


def update_section(section: str, section_config: dict):
    config = load_config()
    config[section] = section_config
    save_config(config)


def get_section(section: str) -> dict:
    config = load_config()
    return config.get(section, {})


def get_channel_config(section: str, channel_id: int):
    config = load_config()
    section_data = config.get(section, {})
    ch_id_str = str(channel_id)
    if ch_id_str not in section_data:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found in '{section}'")
    return config, section_data, ch_id_str




# -------- Digital Input -------- #
def get_default_digital_input_config(channel_id: int):
   
    return {"name": f"Ch-{channel_id}"}

def ensure_digitalinput_config(channel_count: int):
    config = get_section("digital_input")
    for ch_id in range(1, channel_count + 1):
        ch_str = str(ch_id)
        if ch_str not in config:
            # Pass the channel ID to get the correct name
            config[ch_str] = get_default_digital_input_config(ch_id)

    for ch_str in list(config.keys()):
        if int(ch_str) > channel_count:
            del config[ch_str]

    update_section("digital_input", config)
    return config

# -------- Digital Output -------- #
def get_default_digital_output_config():
    return {
        "output_type": "Level",
        "option": ["Level", "Waveform"],
        "level": "Low",
        "frequency": None,
        "duty_cycle": None,
        "status": False,
    }

def ensure_digitaloutput_config(channel_count: int):
    config = get_section("digital_output")
    updated = False

    for ch_id in range(1, channel_count + 1):
        ch_str = str(ch_id)
        if ch_str not in config:
            config[ch_str] = get_default_digital_output_config()
            updated = True

    for ch_str in list(config.keys()):
        if int(ch_str) > channel_count:
            del config[ch_str]
            updated = True

    if updated:
        update_section("digital_output", config)
    return config

