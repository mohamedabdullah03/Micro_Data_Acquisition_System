

import json
import os
import platform

# Decide config path based on OS
if platform.system().lower().startswith("win"):
    CONFIG_FILE = os.path.join(os.getcwd(), "config.json")   # local project folder
else:
    CONFIG_FILE = "/root/udaq/config/config.json"            # target board path


def save_latest_connection(entry: dict):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(entry, f, indent=2)


def update_config_field(field: str, value):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    # Load existing config or start new
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}

    # Update specific field
    config[field] = value

    # Save updated config
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


