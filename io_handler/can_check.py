import socket
import can
import os
import signal
import sys
import threading
import time

# Configuration
CAN_CHANNELS = {
    "can0": {"id": 1, "active": True},
    "can1": {"id": 2, "active": True}
}
UDP_IPS = ["192.168.1.135", "192.168.1.87", "192.168.1.128"]
UDP_PORT = 50000
BITRATE = 500000
LOG_FILE = "can_log.txt"

running = True

def setup_can_interface(interface):
    os.system(f"ip link set {interface} up type can bitrate {BITRATE}")
    print(f"[INFO] {interface} (Channel {CAN_CHANNELS[interface]['id']}) is up with bitrate {BITRATE}")

def cleanup_can_interface(interface):
    os.system(f"ip link set {interface} down")
    print(f"[INFO] {interface} (Channel {CAN_CHANNELS[interface]['id']}) is down")

def signal_handler(sig, frame):
    global running
    print("\n[SHUTDOWN] Stopping all CAN communication...")
    running = False
    for iface in CAN_CHANNELS:
        if CAN_CHANNELS[iface]["active"]:
            cleanup_can_interface(iface)
            CAN_CHANNELS[iface]["active"] = False
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def can_udp_bridge(interface):
    chan_id = CAN_CHANNELS[interface]["id"]
    try:
        setup_can_interface(interface)
        bus = can.Bus(interface="socketcan", channel=interface, bitrate=BITRATE)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"[STARTED] Channel {chan_id} bridge running, forwarding to {len(UDP_IPS)} UDP targets")

        with open(LOG_FILE, "a") as log_file:
            while running:
                if not CAN_CHANNELS[interface]["active"]:
                    time.sleep(1)
                    continue

                message = bus.recv(1)
                if message:
                    data_str = f"{ message.timestamp:.6f}#Channel {chan_id}#{message.arbitration_id:X}#{message.dlc}#{message.data.hex()}"
                    print(f"[Channel {chan_id}] 📡 {data_str}")
                    log_file.write(f"[Channel {chan_id}] {data_str}\n")
                    log_file.flush()

                    for ip in UDP_IPS:
                        try:
                            sock.sendto(data_str.encode('utf-8'), (ip, UDP_PORT))
                            print(f"[Channel {chan_id}]  Sent to {ip}")
                        except Exception as e:
                            print(f"[Channel {chan_id}]  Error sending to {ip}: {e}")
    except Exception as e:
        print(f"[Channel {chan_id}]  Error: {e}")
    finally:
        if CAN_CHANNELS[interface]["active"]:
            cleanup_can_interface(interface)
            CAN_CHANNELS[interface]["active"] = False

# Input monitor for runtime control
def monitor_input():
    global running
    while True:
        cmd = input("[COMMAND] Type 1 to stop Channel 1, 2 to stop Channel 2, q to quit: ").strip()
        if cmd == "1":
            iface = "can0"
            if CAN_CHANNELS[iface]["active"]:
                CAN_CHANNELS[iface]["active"] = False
                cleanup_can_interface(iface)
                print("[INPUT] Channel 1 stopped.")
                break
            else:
                print("[INPUT] Channel 1 already stopped.")
                break
        elif cmd == "2":
            iface = "can1"
            if CAN_CHANNELS[iface]["active"]:
                CAN_CHANNELS[iface]["active"] = False
                cleanup_can_interface(iface)
                print("[INPUT] Channel 2 stopped.")
                break
            else:
                print("[INPUT] Channel 2 already stopped.")
                break
        elif cmd.lower() == "q":
            print("[INPUT] Quitting all...")
            signal_handler(None, None)
            break
        else:
            print("[INPUT] Invalid command.")
            continue
# Start threads
threads = []
for iface in CAN_CHANNELS:
    t = threading.Thread(target=can_udp_bridge, args=(iface,))
    t.start()
    threads.append(t)

# Start command monitor
input_thread = threading.Thread(target=monitor_input, daemon=True)
input_thread.start()

# Wait for CAN threads
for t in threads:
    t.join()

