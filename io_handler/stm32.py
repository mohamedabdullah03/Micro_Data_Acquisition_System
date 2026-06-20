import time
import logging
from datetime import datetime
import serial
import base64
import queue_handler   # <- your custom module

logger = logging.getLogger(__name__)

# Lookup tables
SID_MAP = {
    0: "Reserved(0)",
    1: "iMX (DAQ Master)",
    2: "STM32 (DAQ Slave)",
    3: "Reserved",
    4: "Reserved",
    5: "Reserved",
    6: "Reserved",
    7: "Data Processor (PC/Work Station)"
}

TID_MAP = {
    0: "all",
    1: "ain",
    2: "ao",
    3: "din",
    4: "do"
}

CH_TYPE_MAP = {
    0: "Invalid",
    1: "Single Channel",
    2: "Sequential Multi Channel (ADC/DAC)",
    3: "Reserved"
}

CONTROL_MAP = {
    0: "Reserved",
    1: "Data",
    2: "Control",
    3: "Configure"
}


def format_hex_data(data: bytes) -> str:
    return ' '.join(f'{b:02X}' for b in data)


def uart_open(port: str, baudrate: int = 1000000, timeout: float = 1.0) -> serial.Serial:
    return serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=timeout,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False
    )

def uart_close(ser: serial.Serial):
    """Close the UART serial port safely."""
    try:
        if ser and ser.is_open:            
            ser.close()
            logger.info(f"Serial port {ser.port} closed successfully.")
        else:
            logger.warning("Serial port is already closed or invalid.")
    except Exception as e:
        logger.error(f"Error closing serial port: {e}")

def uart_send_message(ser, message: bytes) -> int:
    if not ser.is_open:
        logger.error("Serial port is closed!")
        return 0
    try:        
        if ser.is_open:
            ser.reset_output_buffer()
            bytes_written = ser.write(message)    
            ser.flush()
            logger.debug(f'port={ser.is_open}, data={message.hex()}, bytes={bytes_written}')
            return bytes_written

    except Exception as e:
        logger.error(f"Write error: {e}")
        return 0



def uart_receive_loop(ser: serial.Serial):
    """ Continuously read, parse and forward UART frames """
    buffer = bytearray()
    logger.info("Listening for incoming messages (Ctrl+C to stop)\n")

    try:
        while True:
            try:
                if not ser or not ser.is_open:
                    logger.error("Serial port closed or invalid. Exiting receive loop.")
                    break
                if ser.in_waiting > 0:
                    buffer.extend(ser.read(ser.in_waiting))

                while True:
                    # search SOF
                    start_idx = buffer.find(b'\x7E')
                    if start_idx == -1:
                        buffer.clear()
                        break
                    if start_idx > 0:
                        buffer = buffer[start_idx:]

                    # Need at least SOF + ID + CTRL + DL(2) + EOF
                    if len(buffer) < 6:
                        break

                    datalen = int.from_bytes(buffer[3:5], byteorder="little")
                    expected_frame_length = 5 + datalen + 1

                    if len(buffer) < expected_frame_length:
                        break

                    eof_idx = expected_frame_length - 1
                    if buffer[eof_idx] != 0x7F:
                        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        logger.warning(
                            f"❌[{ts}] Invalid frame: "
                            f"EOF not found at {eof_idx}, found 0x{buffer[eof_idx]:02X}"
                        )
                        buffer.pop(0)
                        continue

                    # slice out frame
                    frame = buffer[:expected_frame_length]
                    data_portion = frame[5:5 + datalen]
                    buffer = buffer[expected_frame_length:]

                    # ---- decode header fields ----
                    id_byte = frame[1]
                    sid = id_byte & 0b111
                    tid = (id_byte >> 3) & 0b111
                    ch_type = (id_byte >> 6) & 0b11

                    ctrl_chid = frame[2]
                    control = (ctrl_chid >> 6) & 0b11
                    ch_id = ctrl_chid & 0x3F

                    if tid == 0:
                        logger.info("⏩ Skipping frame with TID=0")
                        continue

                    msg_type = TID_MAP.get(tid, "unknown")

                    if (len(data_portion) > 100):
                        base64_str = base64.b64encode(data_portion).decode("utf-8")
                    else:
                        base64_str = data_portion.hex()

                    input_payload = {
                        "type": msg_type,
                        "data": base64_str
                    }
                    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    logger.debug(f"[{msg_type.upper()}] {input_payload}")
                    
                    try:
                        queue_handler.tcp_queue.put(input_payload)
                    except Exception as qe:
                        logger.error(f"Queue handler error: {qe}")

                time.sleep(0.01)

            except serial.SerialException as e:
                logger.error(f"Serial error: {e}")
                time.sleep(1)
            except Exception as e:
                logger.exception(f"Unexpected error: {e}")
                time.sleep(1)

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
