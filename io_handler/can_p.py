import can
import os
import signal
import sys
import logging
import subprocess
import queue_handler
import socket
import time

logger = logging.getLogger(__name__)

chl = None

def stop_can1_command():
    try:
        subprocess.run(f"ip link set can0 down", shell=True, check=True)
        logger.debug(f"{"can0"} is down.")
    except subprocess.CalledProcessError as e:
        logger.ERROR(f"Failed to bring down {"can0"}: {e}")

def stop_can2_command():
    try:
        subprocess.run(f"ip link set can1 down", shell=True, check=True)
        logger.debug(f"{"can1"} is down.")
    except subprocess.CalledProcessError as e:
        logger.ERROR(f"Failed to bring down {"can1"}: {e}")

def set_can_bitrate(interface: str, bitrate:int=500000, dbitrate=None) -> bool:
    """Set CAN bitrate for the given interface in a simple way."""
    try:
        subprocess.run(f"ip link set {interface} down", shell=True, check=True)
        time.sleep(1)

        if dbitrate is not None and isinstance(dbitrate, int) and dbitrate > 0:
            subprocess.run(f"ip link set {interface} type can bitrate {bitrate} dbitrate {dbitrate} fd on", shell=True, check=True)            
        else:
            subprocess.run(f"ip link set {interface} mtu 16", shell=True, check=True)
            time.sleep(1)
            subprocess.run(f"ip link set {interface} type can bitrate {bitrate}", shell=True, check=True)            
        
        time.sleep(1)
        subprocess.run(f"ip link set {interface} up", shell=True, check=True)
        
        logger.info(f"Successfully set {interface} bitrate to {bitrate} dbitrate to {dbitrate}")
        can_fd = can_status(interface)

        return can_fd

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to set CAN bitrate for {interface}: {e}")
        return False

def send_msg_can(bus, channel, can_data:list, can_aid, can_eid:bool, can_fd:bool):
    msg = can.Message(arbitration_id=can_aid, data=can_data, is_extended_id=can_eid, is_fd=can_fd)
    bus.send(msg)
    chl = 1 if channel == "can0" else 2
            
    input_payload = {
        "type": "can",
        "data": {
            "cid": chl,
            "dir": "tx",
            "ts": f"{time.time():.6f}",
            "aid": can_aid,
            "dl": len(can_data),
            "data": bytes(can_data).hex()
        }
    }

    logger.info(f"can Tx data: {input_payload}")
    queue_handler.tcp_queue.put(input_payload)

def start_bus(interface):
    if_fd = can_status(interface)
    bus = can.Bus(interface="socketcan", channel=interface, fd=if_fd)
    return bus

def log_active_can0_channels(bus1):
    try:      
        msg = bus1.recv()      
        if msg:
            if not msg.is_rx:  # ← filter echo TX frames
                return None
            data = {
                "cid": 1,
                "dir": "rx",
                "ts": f"{msg.timestamp:.6f}",
                "aid": format(msg.arbitration_id, "X"),
                "dl": msg.dlc,
                "data": msg.data.hex()
            }
            input_payload = {
                "type": "can",
                "data": data
            }
            return input_payload
                    
    except Exception as e:
        logger.debug(f"Error: {e}")
            
def log_active_can1_channels(bus2):
    try:      
        msg = bus2.recv()      
        if msg:
            if not msg.is_rx:
                return None
            data = {
                "cid": 2,
                "dir": "rx",
                "ts": f"{msg.timestamp:.6f}",
                "aid": format(msg.arbitration_id, "X"),
                "dl": msg.dlc,
                "data": msg.data.hex()
            }
            input_payload = {
                "type": "can",
                "data": data
            }
            return input_payload
                    
    except Exception as e:
        logger.debug(f"Error: {e}")

def can_status(interface:str):
    result = subprocess.run(
        ["ip", "link", "show", interface],
        capture_output=True,
        text=True
    )
    output = result.stdout.strip()
    if "mtu" in output:
        mtu = int(output.split("mtu")[1].split()[0])

    # Determine type based on MTU
    can_fd = "Unknown"
    if mtu == 16:
        can_fd = False
    elif mtu == 72:
        can_fd = True

    logger.info(f"{interface} is_fd: {can_fd}")
    return can_fd
