import threading
import queue
import time
import can_p
import can
from pps import pps_device_connection, pps_get_info, pps_get_output, pps_set_config, pps_stop_alarm, pps_device_disconnect
import stm32
import socket
import time
import logging
from pathlib import Path
import json
import ip_config
import subprocess
import ctypes
import ipc_handler
import socket_tx

libc = ctypes.CDLL('libc.so.6')

logger = logging.getLogger(__name__)

UART_PORT = '/dev/ttyLP2'
BAUD_RATE = 1000000

ser = None
client = None
ip = None
port = None
bitrate = None
can_bus0 = None
can_bus1 = None
can0_stop = None
can1_stop = None

# 1 milli sencond
CAN_SEND_MIN_INTERVAL = 0.001

# Create command queues
can1_input_queue = queue.Queue()
can2_input_queue = queue.Queue()
can_send_queue = queue.Queue()
stm32_input_queue = queue.Queue()
pps_input_queue = queue.Queue()
pps_queue = queue.Queue()
tcp_queue = queue.Queue()

def ip_set_config():
    ip_config.ip_config_set()
def init_config():
    global ip, port, bitrate, ser, can_bus0, can_bus1, client
    try:
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        config_path = project_root / "udaq" / "config" / "config.json"

        logger.debug(f"Looking for config at: {config_path}")

        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                connection_data = config_data.get('connection')
                # This will always get the latest IP from config file
                new_ip = connection_data.get('data_processor_ip')
                
                # Update global IP if it changed
                if new_ip != ip:
                    ip = new_ip
                    logger.debug(f"IP updated to: {ip}")
                else:
                    ip = new_ip
                    
                port = connection_data.get('data_port')
                bitrate = config_data.get('bitrate')
                dbitrate = config_data.get('dbitrate')

                logger.debug("Config loaded successfully.")
                logger.debug(f"ip_address: {ip}")
                logger.debug(f"ip_port: {port}")
                logger.debug(f"bitrate: {bitrate}")
                logger.debug(f"dbitrate: {dbitrate}")

                # Only initialize hardware once
                if 'ser' not in globals() or ser is None:
                    ser = stm32.uart_open(UART_PORT, BAUD_RATE)

                if 'client' not in globals() or client is None:
                    client = pps_device_connection() 

                if bitrate is not None:
                    can_p.set_can_bitrate("can0", bitrate, dbitrate)
                    can_p.set_can_bitrate("can1", bitrate, dbitrate)
                else:
                    can_p.set_can_bitrate("can0", 500000, None)
                    can_p.set_can_bitrate("can1", 500000, None)                   

                logger.debug(f"[CAN] Bitrate set to: {bitrate}")
        else:
            logger.debug(f"Config file not found: {config_path}")
            return None

    except Exception as e:
        logger.debug("Failed to load config.")
        return None 

    except Exception as e:
        logger.debug("Failed to load config.")
        return None

def tcp_sender_worker():
    logger.info("[TCP] TCP Sender started.")
    
    while True:
        try:
            # Get the latest IP and port from config before connecting
            init_config()  # This will update ip and port variables
            ip_port = int(port)
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((ip, ip_port))
                logger.info(f"[TCP] Connected to {ip}:{ip_port}")
                
                while True:
                    try:
                        message = tcp_queue.get_nowait() 
                        
                        if message is None:
                            logger.debug("[TCP] Received stop signal")
                            return
                        
                        msg = json.dumps(message).encode('utf-8')
                        s.sendall(msg)
                        logger.info(f"[TCP] Sent: {msg}")
                        
                    except queue.Empty:
                        continue 
                    except (socket.timeout, socket.error, ConnectionError) as e:
                        logger.error(f"[TCP] Connection error: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"[TCP] Connection failed to {ip}:{port}: {e}")
            time.sleep(2)
            
def can1_receive_worker():
    global can_bus0, can0_stop
    logger.info("[CAN] CAN Worker started for both CAN1 and CAN2.")    
    can0_stop = False
    
    while True:
        try:
            try:
                command = can1_input_queue.get_nowait()
                logger.debug(f"[CAN] Received command: {command}")
                
                if isinstance(command, tuple):
                    cmd, mode = command
                    
                    if cmd == "STOP":
                        if mode == "CAN1":
                            can0_stop = True
                            if can_bus0 is not None:
                                can_bus0.shutdown()
                                can_p.stop_can1_command()
                    
                    elif cmd == "START":
                        if mode == "CAN1":
                            can0_stop = False
                            subprocess.run(f"ip link set can0 up", shell=True, check=True)
                            can_bus0 = can_p.start_bus("can0")
                
                can1_input_queue.task_done()
                
            except queue.Empty:
                pass
            
            # Read from CAN0 (CAN1)
            if not can0_stop and can_bus0 is not None:
                try:
                    can0_data = can_p.log_active_can0_channels(can_bus0)
                    if can0_data is not None:
                        logger.debug(f"[CAN] RAW DATA: {can0_data}")
                        tcp_queue.put_nowait(can0_data)
                except Exception as e:
                    logger.error(f"[CAN] Error reading from CAN0: {e}")
             
        except Exception as e:
            logger.error(f"[CAN] Rx Worker error: {e}")
            time.sleep(0.1)

def can2_receive_worker():
    global can_bus1, can1_stop
    logger.info("[CAN] CAN Worker started for both CAN1 and CAN2.")    
    can1_stop = False
    
    while True:
        try:
            try:
                command = can2_input_queue.get_nowait()
                logger.debug(f"[CAN] Received command: {command}")
                
                if isinstance(command, tuple):
                    cmd, mode = command
                    
                    if cmd == "STOP":
                        if mode == "CAN2":
                            can1_stop = True
                            if can_bus1 is not None:
                                can_bus1.shutdown()
                                can_p.stop_can2_command()
                    
                    elif cmd == "START":
                        if mode == "CAN2":
                            can1_stop = False
                            subprocess.run(f"ip link set can1 up", shell=True, check=True)
                            can_bus1 = can_p.start_bus("can1")
                
                can2_input_queue.task_done()
                
            except queue.Empty:
                pass
            
            # Read from CAN1 (CAN2)
            if not can1_stop and can_bus1 is not None:
                try:
                    can1_data = can_p.log_active_can1_channels(can_bus1)
                    if can1_data is not None:
                        logger.debug(f"[CAN] RAW DATA: {can1_data}")
                        tcp_queue.put_nowait(can1_data)
                except Exception as e:
                    logger.error(f"[CAN] Error reading from CAN1: {e}")            
            
        except Exception as e:
            logger.error(f"[CAN] Rx Worker error: {e}")
            time.sleep(0.1)

def can_send_worker():
    global can_bus0, can_bus1, can0_stop, can1_stop

    logger.info("[CAN] CAN Send Worker started.")
    commands_db = {}
    active_commands = {}
    
    while True:
        entry_time = time.monotonic_ns()
        try:
            try:
                queue_item = can_send_queue.get_nowait()
                if queue_item is not None:
                    channel, data, aid, eid, can_del, msg_id, flag, fd = queue_item
                    logger.debug(f"{flag}, {msg_id}, {channel}")
                    
                    if flag == "add":
                        commands_db[msg_id] = {
                            'channel': channel, 'data': data, 'aid': aid, 
                            'eid': eid, 'can_del': can_del, 'is_active': False, 'fd': fd,
                            'last_send_time': 0
                        }
                            
                    elif flag in ["modify", "start", "stop", "remove"]:
                        if msg_id not in commands_db:
                            commands_db[msg_id] = {
                                'channel': channel, 'data': data, 'aid': aid, 
                                'eid': eid, 'can_del': can_del, 'is_active': False, 'fd': fd,
                                'last_send_time': 0
                            }
                            
                        if flag == "modify":
                            commands_db[msg_id].update({
                                'channel': channel, 'data': data, 'aid': aid,
                                'eid': eid, 'can_del': can_del, 'fd':fd
                            })
                            if msg_id in active_commands:
                                active_commands[msg_id] = commands_db[msg_id]
                                
                        elif flag == "start":
                            commands_db[msg_id]['is_active'] = True
                            commands_db[msg_id]['last_send_time'] = 0
                            active_commands[msg_id] = commands_db[msg_id]

                            
                        elif flag == "stop":
                            commands_db[msg_id]['is_active'] = False
                            if msg_id in active_commands:
                                del active_commands[msg_id]
                                
                        elif flag == "remove":
                            if msg_id in active_commands:
                                del active_commands[msg_id]
                            del commands_db[msg_id]
                                
                    else:
                        raise Exception(f"Unknown flag: {flag} for message ID {msg_id}")
            except:
                pass
            
            current_time = time.monotonic()
            
            # Find the next message that needs to be sent
            next_send_time = float('inf')
            
            for msg_id, cmd in list(active_commands.items()):
                try:
                    time_since_last_send = current_time - cmd['last_send_time']
                    
                    if cmd['can_del'] == 0 and not cmd['last_send_time']:
                        # Send message once and then stop
                        can_p.send_msg_can(
                            bus=can_bus0 if cmd['channel'] == "can0" else can_bus1,
                            channel=cmd['channel'],
                            can_data=cmd['data'],
                            can_aid=cmd['aid'],
                            can_eid=cmd['eid'],
                            can_fd=cmd['fd']
                        )
                        cmd['last_send_time'] = current_time
                        cmd['is_active'] = False  # Stop further sends
                        if msg_id in active_commands:
                            del active_commands[msg_id]
                        logger.debug(f"[CAN] One-time message sent and stopped: {msg_id}")

                    elif cmd['can_del'] > 0 and time_since_last_send >= cmd['can_del']:
                        # Regular periodic message
                        can_p.send_msg_can(
                            bus=can_bus0 if cmd['channel'] == "can0" else can_bus1,
                            channel=cmd['channel'],
                            can_data=cmd['data'],
                            can_aid=cmd['aid'],
                            can_eid=cmd['eid'],
                            can_fd=cmd['fd']
                        )
                        cmd['last_send_time'] = current_time
                        next_send_time = min(next_send_time, cmd['can_del'])
                    else:
                        # Calculate when this message will be ready
                        time_until_next_send = cmd['can_del'] - time_since_last_send
                        next_send_time = min(next_send_time, time_until_next_send)
                        
                except Exception as e:
                    logger.error(f"[CAN] Send error msg_id {msg_id}: {e}")
            
            # Sleep until the next message needs to be sent, but max 10ms
            if next_send_time == float('inf'):
                # No active commands or all delays are long
                sleep_time = CAN_SEND_MIN_INTERVAL
            else:
                sleep_time = min(next_send_time, CAN_SEND_MIN_INTERVAL)

            process_time = (time.monotonic_ns() - entry_time) / 1e9

            if process_time < sleep_time:
                libc.usleep(100)
                # time.sleep((sleep_time - process_time)-0.001)
                
        except Exception as e:
            logger.error(f"[CAN] Tx Worker error: {e}")
            time.sleep(1)
                   
def pps_worker():
    global client
    logger.debug("[PPS] PPS Worker started.")   
    client = pps_device_connection() 

    while True:
        try:
            try:
                command = pps_input_queue.get(timeout=0.1)
            except queue.Empty:
                time.sleep(0.1)
                continue

            if isinstance(command, tuple) and len(command) == 4:
                CV, OCP, OVP, cmd = command
            else:
                cmd = command

            if cmd == "STOP":
                pps_device_disconnect(client)

            if cmd == "SEND":
                logger.debug("[PPS] Starting PPS process.")                
                try:
                    if client:
                        pps_set_config(CV, OCP, OVP, client)
                        pps_queue.put("success")
                    else:
                        raise Exception("error: Failed to connect to device")
                        
                except Exception as e:
                    logger.debug(f"[PPS] Error in SEND command: {e}")
                    raise Exception(f"error: {e}")
                    
            elif cmd == "GET":
                if client is None:
                    pps_queue.put("error: No device connection")
                else:
                    try:
                        data = pps_get_output(client)
                        if data is not None:
                            pps_queue.put(data)
                    except Exception as e:
                        logger.debug(f"[PPS] Error in GET command: {e}")
                        raise Exception(f"error:{e}")

            elif cmd == "INFO":
                if client is None:
                    pps_queue.put("error: No device connection")
                else:
                    try:
                        data = pps_get_info(client)
                        if data is not None:
                            pps_queue.put(data)
                    except Exception as e:
                        logger.debug(f"[PPS] Error in INFO command: {e}")
                        raise Exception(f"error:{e}")
            elif cmd == "CLEAR":
                if client is None:
                    pps_queue.put("error: No device connection")
                else:
                    try:
                        pps_stop_alarm(client)
                        pps_queue.put("pps alarm cleared")
                    except Exception as e:
                        logger.debug(f"[PPS] Error in INFO command: {e}")
                        raise Exception(f"error:{e}")
            else:
                logger.debug(f"[PPS] Unknown command: {cmd}")
                pps_queue.put("error: Unknown command")

        except Exception as e:
            logger.debug(f"[PPS] Worker error: {e}")
            time.sleep(0.1)
 
def stm32_worker(data):
    global ser

    if data == "STOP":
        stm32.uart_close(ser)
        ser = None

def datain_worker():
    global ser
    logger.info("starting datain_worker")

    if ser is not None:
        stm32.uart_receive_loop(ser)

def ipc_read_worker():
    logger.info("Starting ipc_read_worker")
    while True:
        try:
            msg = ipc_handler.ipc_read()            
            if msg:                
                try:
                    parsed_msg = json.loads(msg)
                    can_data = parsed_msg.get("can_data")
                    input_payload = {
                        "type": "can",
                        "data": can_data
                    }
                    tcp_queue.put_nowait(input_payload)
                    time.sleep(0.002)

                except queue.Full:
                    logger.warning("tcp_queue is full, dropping message")

        except Exception as e:
            logger.error(f"Error in ipc_read_worker: {e}")
            time.sleep(0.1) 

def set_can_config(channel:str):
    result = socket_tx.fifo_write(channel)
    logger.info(result)
