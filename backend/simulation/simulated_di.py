import json, time, random, logging
from tcp_sender import send_tcp_message




CONFIG_PATH = "board_info.json"

def load_hardware_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def get_di_channel_count():
    config = load_hardware_config()
    return config["subsystems_available"]["digital_input"]["channel_count"]

def get_di_channels():
    count = get_di_channel_count()
    return {i: f"in_digital{i - 1}_raw" for i in range(1, count + 1)}

din_running = False

def din_tcp_sender(running_flag_getter):
    logging.info("[SIMULATION] Starting DI simulation...")

    while running_flag_getter():
        try:
            sid = 6
            tid = 3
            ch_type = 1
            ch_ctrl = 1
            ch_id = random.randint(0, get_di_channel_count()-1)
            value = random.randint(0, 1)

            id_byte = ((sid & 0x07) << 5) | ((tid & 0x07) << 2) | (ch_type & 0x03)
            ch_byte = ((ch_ctrl & 0x03) << 6) | (ch_id & 0x3F)

            data_bytes = bytearray([value])
            frame = bytearray([
                0x7E, id_byte, ch_byte,
                0x00, len(data_bytes),
                *data_bytes,
                0x7F
            ])

            json_msg = {"type": "din", "data": frame.hex()}
            send_tcp_message(json.dumps(json_msg).encode("utf-8"))

            logging.debug(f"[SIM-DI] Sent: {json_msg}")
            time.sleep(0.1)

        except Exception as e:
            logging.error(f"[SIM-DI ERROR] {e}")
            break

    logging.info("[SIMULATION] DIN simulation stopped")
