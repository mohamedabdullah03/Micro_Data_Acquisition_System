from simulation.config_manager import *
from simulation.board_info_manager import *

def ensure_analog_input(channel_count: int = None):
    if channel_count is None:
        channel_count = get_ai_channel_count()
    config = get_section("analog_input") or {}
    for ch_id in range(1, channel_count + 1):
        if str(ch_id) not in config:
            config[str(ch_id)] = {
                "Vref-": -10,
                "Vref+": 10,
                "min": -32768,
                "max": 32767,
                "scale": 1,
                "unit": "V",
            }
    update_section("analog_input", config)
    return config

def ensure_analog_output(channel_count: int = None):
    if channel_count is None:
        channel_count = get_ao_channel_count()
    config = get_section("analog_output") or {}
    for ch_id in range(1, channel_count + 1):
        if str(ch_id) not in config:
            config[str(ch_id)] = {
                "output_type": "DC",
                "option": ["DC", "Square", "Triangle", "Sine"],
                "status": False,
                "amplitude": "0",
                "frequency": None,
            }
    update_section("analog_output", config)
    return config
