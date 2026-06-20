import threading, time, random, socket, json, can
from simulation.tcp_sender import *

# ---- Simulated CAN state ----
AVAILABLE_CHANNELS = ["can0", "can1"]
ALIAS_TO_REAL_CAN = {"can1": "can0", "can2": "can1", "0": "0"}
REAL_TO_ALIAS = {"can0": "can1", "can1": "can2"}
ALIAS_NUM = {"can1": "1", "can2": "2"}
channel_threads = {"can0": {"running": False}, "can1": {"running": False}}


# ---- Fake CAN message sender ----
def generate_fake_can_message(arbitration_id_start=0x100):
    arb_id = arbitration_id_start + random.randint(0, 31)
    dlc = 8
    data = [random.randint(0, 255) for _ in range(dlc)]
    return can.Message(arbitration_id=arb_id, data=data, is_extended_id=False)



def can_tcp_sender(channel_id, alias_num):
    bus = can.interface.Bus(channel=channel_id, interface="virtual")
    try:
        while channel_threads[channel_id]["running"]:
            msg = generate_fake_can_message()
            msg.timestamp = time.time()
            json_msg = {
                "type": "can",
                "data": {
                    "cid": int(alias_num),
                    "ts": msg.timestamp,
                    "aid": msg.arbitration_id,
                    "dl": 8,
                    "data": msg.data.hex()
                }
            }
            send_tcp_message(json.dumps(json_msg))
            time.sleep(0.05)
    finally:
        bus.shutdown()
