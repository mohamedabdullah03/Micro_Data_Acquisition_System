import logging
import queue_handler
import threading
import queue
import time
import protocol_frame
import can_p
import stm32
import ipc_handler
import json
import subprocess
import os
import socket_tx

logger = logging.getLogger(__name__)
can_process = None
uart_serial = None
can1_fd = None
can2_fd = None
dout_data = 0x0000
AO_VOLT_MIN = -10
AO_VOLT_MAX = 10
AO_DIGITAL_VAL_MAX = 0xFFFF

def can_set_config(bitrate:int, dbitrate: int):
    global can1_fd, can2_fd
    logger.info(f"[debug] can_set_config() called with bitrate: {bitrate}")
    if bitrate > 1000000:
        return "Invalid Bitrate"
    can1_fd = can_p.set_can_bitrate("can0", bitrate, dbitrate)
    can2_fd = can_p.set_can_bitrate("can1", bitrate, dbitrate)
    return "Bitrate update requested"

def can_start_stop_ch(cmd, channel):
    channel_id = channel.upper()
    logger.debug(f"[debug] can_start_ch() called with cmd: {cmd}, ch_id: {channel_id}")
    if cmd == "START":
        if channel_id == "CAN1":
            queue_handler.can1_input_queue.put(("START", "CAN1"))
        else:
            queue_handler.can2_input_queue.put(("START", "CAN2"))

        socket_tx.fifo_write(f"START_{channel_id}")
    elif cmd == "STOP":
        # subprocess.run(f"ip link set can1 down", shell=True, check=True)
        socket_tx.fifo_write(f"STOP_{channel_id}")
        if channel_id == "CAN1":
            # can_p.stop_can1_command()
            queue_handler.can1_input_queue.put(("STOP", "CAN1"))
        elif channel_id == "CAN2":
            # can_p.stop_can2_command()
            queue_handler.can2_input_queue.put(("STOP", "CAN2"))

def can_send_data(msg_id:int, flag:str, channel:str, data:list=None, arb_id:int=None, ext_id:bool=None, can_del:float=None):
    try:
        channel_id = channel.upper()
        logger.debug(f"{flag}, {msg_id}, {channel}")

        if can_del < 0.002:
            can_del = 0

        ext_id = True if arb_id > 2047 else ext_id
        ch_id = "can0" if channel_id == "CAN1" else "can1"
        fd_state = can_p.can_status(ch_id)
        payload = {
            "can_playload": {
                "cid": channel_id, "flag": flag, "msg_id": msg_id, "aid": arb_id,
                "data": data, "ext_id": ext_id, "can_delay": can_del, "can_fd": fd_state
            }
        }
        time.sleep(1)
        socket_tx.fifo_write(json.dumps(payload))
        time.sleep(1)
        # if channel_id == "CAN1":
        #     queue_handler.can_send_queue.put(("can0", data, arb_id, ext_id, can_del, msg_id, flag, can1_fd))
        # elif channel_id == "CAN2":
        #     queue_handler.can_send_queue.put(("can1", data, arb_id, ext_id, can_del, msg_id, flag, can2_fd))

    except Exception as e:
        logger.error(f'[CAN] can_send_data() {e}')
        raise e

def ain_start_config():
    ain_data = [0x7e, 0x49, 0x02, 0x01, 0x00, 0x01,0x7f]
    byte_data = bytes(ain_data)
    logger.debug("[debug] Called ain_start_config")
    stm32.uart_send_message(uart_serial, byte_data)

def dout_start_config(ch_type:str='single',channel:int=None, pin_value:int=None):
    global dout_data
    logger.debug(f"[DOUT] ch_type={ch_type}, channel={channel}, pin_value={pin_value}")
    s_id = 1       
    t_id = 4       
    ch_type_id = 0 
    control = 1   
    ch_id = 0     

    if ch_type== "all_high":
        dout_data = 0xFFFF
    elif ch_type== "all_low":
        dout_data = 0x0000

    elif ch_type== "single":
        if 1 <= channel <= 16:
            channel -= 1  #zero-based
            if pin_value:
                dout_data |= (1 << channel)
            else:
                dout_data &= ~(1 << channel)
        else:
            logger.error(f"[DOUT] Invalid channel number: {channel+1}")
            return
    else:
        logger.error(f"[DOUT] Invalid ch_type: {ch_type}")
        return

    logger.debug(f"[DOUT] Bitmask: {dout_data:016b}")

    data_bytes = []
    for ch in range(16):
        if dout_data & (1 << ch):
            data_bytes += [0xFD, 0x07, 0x00, 0x00]  
        else:
            data_bytes += [0x01, 0x00, 0x00, 0x00] 

    frame = protocol_frame.create_frame(
        ch_type_id, t_id, s_id, control, ch_id,
        len(data_bytes), data_bytes
    )

    config_data = bytes(frame)
    stm32.uart_send_message(uart_serial, config_data)
    logger.debug(f"[DOUT] Frame: {' '.join(f'{b:02X}' for b in frame)}")  

def ain_stop_config():
    ain_data = [0x7e, 0x09, 0x02, 0x01, 0x00, 0x00, 0x7f]
    byte_data = bytes(ain_data)
    logger.debug("[debug] Called ain_stop_config")
    stm32.uart_send_message(uart_serial, byte_data)

def aout_set_config(voltage, channel):
    logger.debug(f"voltage:{voltage},channel:{channel}")

    if voltage > AO_VOLT_MAX:
        voltage = AO_VOLT_MAX

    if voltage < AO_VOLT_MIN:
        voltage = AO_VOLT_MIN

    data = int(((voltage - AO_VOLT_MIN) / (AO_VOLT_MAX - AO_VOLT_MIN)) * AO_DIGITAL_VAL_MAX)
    ch_type_id = 1
    t_id = 2   
    s_id = 1   
    control = 3  

    data_bytes = [
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00             
    ]

    byte1 = data & 0xFF 
    byte2 = (data >> 8) & 0xFF

    data_bytes[-2] = byte1
    data_bytes[-1] = byte2
    data_bytes[-6] = 0x01

    frame = protocol_frame.create_frame(ch_type_id, t_id, s_id, control, channel, len(data_bytes), data_bytes)

    config_data = bytes(frame)
    stm32.uart_send_message(uart_serial, config_data)
    time.sleep(1)
    aout_set_enable(channel=channel)

def aout_set_enable(channel):
    ch_type_id = 1
    t_id = 2   
    s_id = 1   
    control = 2 

    data_bytes = [
        0x01            
    ]

    frame = protocol_frame.create_frame(ch_type_id, t_id, s_id, control, channel, len(data_bytes), data_bytes)

    byte_data = bytes(frame)
    stm32.uart_send_message(uart_serial, byte_data)
   
def aout_set_disable(channel):
    ch_type_id = 1
    t_id = 2   
    s_id = 1   
    control = 2 

    data_bytes = [
        0x00            
    ]

    frame = protocol_frame.create_frame(ch_type_id, t_id, s_id, control, channel, len(data_bytes), data_bytes)
    
    byte_data = bytes(frame)
    stm32.uart_send_message(uart_serial, byte_data)

def aout_all_disable():
    frame = [0x7E, 0x11, 0x02, 0x01, 0x00, 0x00, 0x7F]    
    byte_data = bytes(frame)
    stm32.uart_send_message(uart_serial, byte_data)

def pps_get_config():
    try:
        queue_handler.pps_input_queue.put("GET")
        data = queue_handler.pps_queue.get()
        logger.debug(f"[debug] Received from queue: {data}")
        return {"data": data}
    except queue.Empty:
        logger.debug("[debug] No new data available in PPS queue.")
        return None
    except Exception as e:
        logger.error(f"error:{e}")
        raise Exception(f"error:{e}")
    
def pps_clear_alarm():
    try:
        queue_handler.pps_input_queue.put("CLEAR")
        data = queue_handler.pps_queue.get()
        logger.debug(f"[debug] Received from queue: {data}")
        return {"data": data}
    except queue.Empty:
        logger.debug("[debug] No new data available in PPS queue.")
        return None
    
def pps_get_info():
    try:
        queue_handler.pps_input_queue.put("INFO")
        data = queue_handler.pps_queue.get(timeout=2)
        logger.debug(f"[debug] Received from queue: {data}")
        return data
    except queue.Empty:
        logger.debug("[debug] No new data available in PPS queue.")
        return None
    except Exception as e:
        logger.error(f"error:{e}")
        raise Exception(f"error:{e}")
    
def pps_set_config(cv, ocp, ovp):
    logger.debug(f"[debug] Called pps_set_config with CV={cv}, OCP={ocp}, OVP={ovp}")
    queue_handler.pps_input_queue.put((cv, ocp, ovp, "SEND"))
    data = queue_handler.pps_queue.get(timeout=5)
    if data and isinstance(data, str) and "error" in data.lower():
        raise Exception(data)

def deinit():
    global uart_serial
    try:

        can_start_stop_ch("STOP", "CAN1")
        time.sleep(0.5)
        can_start_stop_ch("STOP", "CAN2")
        time.sleep(0.5)
        dout_start_config(ch_type ='all_low')
        time.sleep(0.5)
        ain_stop_config()
        time.sleep(0.5)
        aout_all_disable()
        time.sleep(0.5)

        stm32.uart_close(uart_serial)
        queue_handler.stm32_worker("STOP")
        uart_serial = None
        logger.info("[debug] UART port closed.")

        time.sleep(0.5)
        queue_handler.pps_input_queue.put("STOP")

        logger.info("[debug] PPS stop command sent.")
        logger.info("[debug] Deinitialization completed successfully.")
        
        logger.info("[debug] Deinitializing all interfaces...")
        stop_can_handler(can_process)

        return "success"

    except Exception as e:
        logger.error(f"[Error] Deinitialization failed: {e}")
        return "fail"

def init_can_handler():
    can_path = "/root/udaq/io_handler/can"
    
    if not os.path.exists(can_path):
        logger.error(f"Error: {can_path} not found")
        return None
    
    try:
        # Use Popen instead of run to get process control
        process = subprocess.Popen(
            can_path,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return process
        
    except Exception as e:
        logger.error(f"Error starting CAN handler: {e}")
        return None

def stop_can_handler(process):
    if process and process.poll() is None:  # Check if still running
        process.terminate()  # Graceful shutdown
        try:
            process.wait(timeout=5)  # Wait for clean exit
        except subprocess.TimeoutExpired:
            process.kill()  # Force kill if needed
            logger.warning("CAN handler force killed")
        logger.info("CAN handler stopped")

def init():
    global uart_serial, can_process
    logger.info("[debug] Starting worker threads...")
    #.c file ..
    can_process = init_can_handler() 
        
    can1_receive_thread = threading.Thread(target=queue_handler.can1_receive_worker, daemon=True)
    can2_receive_thread = threading.Thread(target=queue_handler.can2_receive_worker, daemon=True)
    
    # can_send_thread = threading.Thread(target=queue_handler.can_send_worker, daemon=True)
    stm32_thread = threading.Thread(target=queue_handler.datain_worker, daemon=True)
    ipc_rec_thread = threading.Thread(target=queue_handler.ipc_read_worker, daemon=True)
    pps_thread = threading.Thread(target=queue_handler.pps_worker, daemon=True)
    tcp_sender_thread = threading.Thread(target=queue_handler.tcp_sender_worker, daemon=True)

    queue_handler.ip_set_config()
    queue_handler.init_config()

    uart_serial = stm32.uart_open(port="/dev/ttyLP2", baudrate=1000000)

    can1_receive_thread.start()
    can2_receive_thread.start()
    stm32_thread.start()
    ipc_rec_thread.start()
    # can_send_thread.start()
    pps_thread.start()
    tcp_sender_thread.start()
    
    logger.debug("[debug] All worker threads started")
    
def main():
    init()

    time.sleep(1)
    # data = pps_get_info()
    # print("data:",data)
    # time.sleep(2)
    # pps_set_config(4, 10, 21)
    # time.sleep(1)
    # count = 0
    # while True:
    #     data = pps_get_config()
    #     print(data)

    # can_p.can_shutdown("can1", 500000)
    # time.sleep(1)
    # can_p.can_shutdown("can0", 500000
    # time.sleep(1)
    # can_set_config(500000)
    # time.sleep(1)
    # can_start_stop_ch("START", "CAN2")
    # time.sleep(10)
    # can_start_stop_ch("START", "CAN1")
    # time.sleep(1)

    can_send_data(msg_id=1, flag="add", channel="CAN2", data=[1,2,3,4,5,6,7,8,0,0,0,0,0,0,0,0], arb_id=300, ext_id=False, can_del=0.2)
    time.sleep(1)
    can_send_data(msg_id=1, flag="start", channel="CAN2")
    # time.sleep(5)
    # can_send_data(msg_id=2, flag="add", channel="CAN1", data=[3,0,0,0,0,0,0,0], arb_id=0x300, ext_id=False, can_del=0.2)
    # time.sleep(1)
    # can_send_data(msg_id=2, flag="start", channel="CAN1")
    # time.sleep(10)
    # can_send_data(msg_id=1, flag="stop", channel="CAN2")
    # can_send_data(msg_id=2, flag="stop", channel="CAN2")
    # can_send_data(msg_id=3, flag="stop", channel="CAN1")
    # can_send_data("CAN1", [0,0,3,4,5,6,7,8], 0x100, False, 5, 2, "add")
    # time.sleep(10)
    # can_send_data("CAN1", msg_id=2, flag="start")
    # time.sleep(15)
    # can_send_data("CAN1", [0,2,3,4,5,6,7,8], 0xc0ffee, True, 1, 1, "modify")
    # time.sleep(20)
    # can_send_data("CAN1", msg_id=1, flag="stop")
    # time.sleep(20)
    # can_send_data("CAN1", msg_id=1, flag="start")
    # time.sleep(10)
    # can_send_data("CAN1", msg_id=1, flag="remove")
    # time.sleep(10)
    # can_send_data("CAN1", msg_id=1, flag="start")
    # time.sleep(1)
    # can_start_stop_ch("GET", "CAN1")
    # time.sleep(15)
    # can_start_stop_ch("GET", "CAN2")
    # time.sleep(15)
    # can_start_stop_ch("STOP", "CAN1")

    dout_start_config(channel=2, pin_value=1)
    time.sleep(1)
    # dout_start_config(0, 0, "all")
    # time.sleep(1)
    # dout_start_config(channel=3, pin_value=1)    
    # time.sleep(1)
    # dout_start_config(3, 0, "single")
    # aout_set_config(-9, 5)
    # time.sleep(2)
    # aout_set_enable(5)
    # ain_start_config()

    try:
        logger.debug("Workers running. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.debug("\nShutting down workers...")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    main()
