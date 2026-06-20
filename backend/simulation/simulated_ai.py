import json
import threading, time, json, random, base64, logging
from tcp_sender import *
from . import device_handler 

CONFIG_PATH = "board_info.json"

sequence_counter = {}

def load_hardware_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def get_adc_channel_count():
    config = load_hardware_config()
    # Correct path in JSON
    return config["subsystems_available"]["analog_input"]["channel_count"]


# simulated_ai.py
def adc_tcp_sender(channel_id, adc_threads_ref):
    logging.info(f"[SIMULATION ADC TCP] Channel {channel_id} sending started.")
    if channel_id not in sequence_counter:
        sequence_counter[channel_id] = 7000 + channel_id

    try:
        while adc_threads_ref.get(channel_id, {}).get("running", False):
            fake_bytes = bytearray(random.getrandbits(8) for _ in range(3200))
            b64_data = base64.b64encode(fake_bytes).decode()
            payload = {"type": "ain", "channel": channel_id, "data": b64_data}
            send_tcp_message(json.dumps(payload))
            sequence_counter[channel_id] += 1
            time.sleep(0.1)
    except Exception as e:
        logging.error(f"[SIMULATION ADC TCP ERROR] {e}")
    logging.info(f"[SIMULATION ADC TCP] Channel {channel_id} sending stopped.")



