import logging
from simulation.simulated_can import *
from simulation.simulated_ai import *
from simulation.simulated_di import *
from simulated_power import *
from model.can_request import *

logger = logging.getLogger("SimDeviceHandler")

def start_thread():
    logger.debug("Test")
    pass

# ----  CAN Functions ----
def can_start_stop_ch(action, channel_id):
    channel_id = channel_id.lower().strip()
    messages = []

    real_channel = ALIAS_TO_REAL_CAN.get(channel_id, channel_id)
    target_channels = AVAILABLE_CHANNELS if real_channel == "0" else [real_channel]

    for ch in target_channels:
        if action.upper() == "START":
            if channel_threads[ch]["running"]:
                messages.append(f"{ch} already running.")
            else:
                alias_num = ALIAS_NUM.get(REAL_TO_ALIAS.get(ch), "0")
                channel_threads[ch]["running"] = True
                threading.Thread(target=can_tcp_sender, args=(ch, alias_num), daemon=True).start()
                messages.append(f"{ch} started with alias_num {alias_num}.")
        elif action.upper() == "STOP":
            if channel_threads[ch]["running"]:
                channel_threads[ch]["running"] = False
                messages.append(f"{ch} stopped.")
            else:
                messages.append(f"{ch} was not running.")
    return messages


#--------(CAN Bitrate)--------->
def can_set_config(bitrate):
    import logging
    logging.info(f"[SIM] CAN config set to bitrate={bitrate}")
    return {"status": "success", "bitrate": bitrate}


# --------(AI FUnction)--------->


adc_threads = {}
sequence_counter = {}

def ain_start_config():
    """Start all ADC channels."""
    adc_channels = range(1, get_adc_channel_count() + 1)
    for ch_id in adc_channels:
        if ch_id not in adc_threads or not adc_threads[ch_id].get("running", False):
            adc_threads[ch_id] = {"running": True}
            threading.Thread(
                target=adc_tcp_sender, 
                args=(ch_id, adc_threads),   # pass adc_threads explicitly
                daemon=True
            ).start()
    logging.info(f"[TARGET] ADC channels started: {list(adc_channels)}")


def ain_stop_config():
    """Stop all ADC channels."""
    stopped = []
    for ch_id, val in adc_threads.items():
        if val.get("running", False):
            val["running"] = False
            stopped.append(ch_id)
    logging.info(f"[TARGET] ADC channels stopped: {stopped}")


#----------(DI Function)---------->
din_running = False
din_thread = None

def din_start_config():
    global din_thread, din_running
    if din_running:
        logging.info("[DIN] Already running")
        return
    din_running = True
    din_thread = threading.Thread(
        target=din_tcp_sender,
        args=(lambda: din_running,),   # pass getter
        daemon=True
    )
    din_thread.start()
    logging.info("[DIN] Simulation thread started")

def din_stop_config():
    global din_running, din_thread
    if not din_running:
        logging.info("[DIN] Was not running")
        return
    din_running = False
    if din_thread and din_thread.is_alive():
        din_thread.join(timeout=2)
    din_thread = None
    logging.info("[DIN] Simulation stopped")


#--------(Power supply)----------->
def pps_set_config(cv: float, ocp: float, ovp: float):
    logging.info(f"[SIM-PSS] Setting CV={cv}, OCP={ocp}, OVP={ovp}")
    power_state.update(cv, ocp, ovp)

def pps_get_config():
    status = power_state.get_status()
    logging.debug(f"[SIM-PSS] Reporting status: {status}")
    return status


def aout_all_disenable():
    """Simulate disabling all analog output channels"""
    # Create the frame as per your original function
    frame = [0x7E, 0x11, 0x02, 0x01, 0x00, 0x00, 0x7F]    
    byte_data = bytes(frame)
    
    # Call the stop function for all channels
    queue_handler.aout_stop(byte_data)
    
    # Disable all channels in the state tracking
    for channel in list(queue_handler.aout_states.keys()):
        queue_handler.aout_states[channel] = False
        queue_handler.aout_voltages[channel] = 0.0
    
    print(f"[SIMULATION] All analog output channels disabled")
    return byte_data


simulation_state = {
    "CAN1": {"active": False, "messages_sent": 0, "last_message": None},
    "CAN2": {"active": False, "messages_sent": 0, "last_message": None}
}

def can_send_data(channel, data: List[int], aid, eid: bool):
    """
    Simulation version of can_send_data function
    """
    channel_id = channel.upper()
    
    if channel_id not in simulation_state:
        logging.error(f"[SIMULATION] Invalid channel: {channel_id}")
        return False
    
    if not simulation_state[channel_id]["active"]:
        logging.warning(f"[SIMULATION] Channel {channel_id} is not active. Cannot send data.")
        return False
    
    # Convert data to hex string for better readability
    hex_data = " ".join([f"{byte:02X}" for byte in data])
    arbitration_id_hex = f"{aid:06X}" if isinstance(aid, int) else aid
    
    # Update simulation state
    simulation_state[channel_id]["messages_sent"] += 1
    simulation_state[channel_id]["last_message"] = {
        "data": data,
        "hex_data": hex_data,
        "arbitration_id": f"0x{arbitration_id_hex}",
        "extended_id": eid,
        "length": 64 if eid else 8,  # Convert back to numeric length
        "timestamp": logging.getLogger().handlers[0].formatter.formatTime(logging.makeLogRecord({}), "%Y-%m-%d %H:%M:%S") if logging.getLogger().handlers else "N/A"
    }
    
    logging.info(f"[SIMULATION] CAN SEND - Channel: {channel_id}, "
                f"AID: 0x{arbitration_id_hex}, Extended ID: {eid}, "
                f"Data: {hex_data}, Length: {64 if eid else 8} bytes")
    
    return True

def can_start_stop_ch(action: str, channel_id: str):
    """
    Simulation version of can_start_stop_ch function
    """
    channel = channel_id.upper()
    
    if channel not in simulation_state:
        logging.error(f"[SIMULATION] Invalid channel: {channel}")
        return {"error": f"Invalid channel: {channel}"}
    
    if action.upper() == "GET":
        # Return current status
        return {
            "channel": channel,
            "active": simulation_state[channel]["active"],
            "messages_sent": simulation_state[channel]["messages_sent"],
            "last_message": simulation_state[channel]["last_message"]
        }
    elif action.upper() == "START":
        simulation_state[channel]["active"] = True
        logging.info(f"[SIMULATION] CAN channel {channel} started")
        return {"message": f"CAN channel {channel} started successfully"}
    elif action.upper() == "STOP":
        simulation_state[channel]["active"] = False
        logging.info(f"[SIMULATION] CAN channel {channel} stopped")
        return {"message": f"CAN channel {channel} stopped successfully"}
    else:
        logging.error(f"[SIMULATION] Invalid action: {action}")
        return {"error": f"Invalid action: {action}"}

def get_simulation_status():
    """
    Get current simulation status for all channels
    """
    return simulation_state

def reset_simulation():
    """
    Reset simulation state
    """
    global simulation_state
    simulation_state = {
        "CAN1": {"active": False, "messages_sent": 0, "last_message": None},
        "CAN2": {"active": False, "messages_sent": 0, "last_message": None}
    }
    logging.info("[SIMULATION] Simulation state reset")
    return {"message": "Simulation reset successfully"}





