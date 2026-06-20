from pickle import GLOBAL
import serial
import struct
import time
import logging
from typing import Optional, List
from enum import Enum
from dataclasses import dataclass

# Setup logging
logger = logging.getLogger(__name__)


class ModbusError(Exception):
    pass


class ExceptionCode(Enum):
    ILLEGAL_FUNCTION = 0x01
    ILLEGAL_DATA_ADDRESS = 0x02
    ILLEGAL_DATA_VALUE = 0x03
    SLAVE_DEVICE_FAILURE = 0x04
    SLAVE_DEVICE_BUSY = 0x06


class RemoteControlMode(Enum):
    TERMINAL_INPUT = 0
    COMMUNICATION_VOLATILE = 1
    COMMUNICATION_NON_VOLATILE = 2
    TERMINAL_AND_VOLATILE = 3
    TERMINAL_AND_NON_VOLATILE = 4


@dataclass
class PowerSupplyStatus:
    output_voltage: float
    output_current: float
    internal_temperature: int
    operation_time: int
    alarm_history: int
    ecap_remaining: int
    model_name: str = ""
    serial_number: str = ""
    firmware_version: str = ""
    ovp: float = 0.0
    ocp: float = 0.0


class GXE600Client:
    class InputRegisters:
        ALARM_HISTORY_VOLATILE = 0x0000
        OUTPUT_VOLTAGE = 0x0001
        OUTPUT_CURRENT = 0x0002
        INTERNAL_TEMPERATURE = 0x0003
        OPERATION_TIME = 0x0004  # 2 registers
        ECAP_REMAINING = 0x0006
        MODEL_NAME = 0x01F4  # 15 registers
        SERIAL_NUMBER = 0x0208  # 8 registers
        FIRMWARE_VERSION = 0x03E8

    class HoldingRegisters:
        REMOTE_ON_OFF_VOLATILE = 0x0000
        REMOTE_ON_OFF_NON_VOLATILE = 0x0005
        REMOTE_CONTROL_CONFIG = 0x0064
        CVCC_REFERENCE_CONFIG = 0x0065
        DIGITAL_CV_REFERENCE = 0x0067
        DIGITAL_CC_REFERENCE = 0x0068
        OVP_SETTING = 0x0069
        OCP_SETTING = 0x006A
        CV_RISING_TIME = 0x006B
        CC_RISING_TIME = 0x006C
        CV_TRANSITION_TIME = 0x006D
        CC_TRANSITION_TIME = 0x006E
        CLEAR_ALARM_HISTORY = 0x0073

    def __init__(self, port: str, slave_id: int = 1, baudrate: int = 19200, parity: str = 'N', timeout: float = 1.0):
        self.port = port
        self.slave_id = slave_id
        self.baudrate = baudrate
        self.parity = parity.upper()
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self.nominal_voltage = 24.0
        self.maximum_current = 25.0

    def connect(self) -> bool:
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity=self.parity,
                stopbits=1,
                timeout=self.timeout
            )
            logger.info(f"Connected to GXE600 on {self.port}")
            time.sleep(0.2)
            self._detect_model()
            return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def disconnect(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Disconnected")

    def _calculate_crc16(self, data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def _build_request(self, function_code: int, data: bytes) -> bytes:
        frame = struct.pack('BB', self.slave_id, function_code) + data
        crc = self._calculate_crc16(frame)
        return frame + struct.pack('<H', crc)

    def _send_request(self, request: bytes) -> bytes:
        if not self.serial_conn or not self.serial_conn.is_open:
            raise ModbusError("Serial connection not open")

        self.serial_conn.reset_input_buffer()
        self.serial_conn.write(request)

        # Read response with timeout handling
        response = self.serial_conn.read(256)
        if len(response) < 5:
            raise ModbusError(f"Incomplete response: received {len(response)} bytes")

        # Check for MODBUS exception response
        if len(response) >= 3 and response[1] & 0x80:
            exception_code = response[2]
            raise ModbusError(f"MODBUS Exception: {exception_code}")

        # Verify CRC
        crc_received = struct.unpack('<H', response[-2:])[0]
        crc_calculated = self._calculate_crc16(response[:-2])
        if crc_received != crc_calculated:
            raise ModbusError("CRC mismatch")

        return response[2:-2]

    def read_input_registers(self, start_address: int, count: int = 1) -> List[int]:
        try:
            req = struct.pack('>HH', start_address, count)
            request = self._build_request(0x04, req)
            logger.debug(request.hex())

            response = self._send_request(request)
            logger.debug(response.hex())

            if len(response) < 1:
                raise ModbusError("Empty response data")

            byte_count = response[0]
            if len(response) < byte_count + 1:
                raise ModbusError(f"Response too short: expected {byte_count + 1}, got {len(response)}")

            values = []
            for i in range(1, byte_count + 1, 2):
                if i + 1 < len(response):
                    values.append(struct.unpack('>H', response[i:i + 2])[0])

            return values
        except Exception as e:
            logger.error(f"Error reading input registers {start_address}: {e}")
            raise

    def read_holding_registers(self, start_address: int, count: int = 1) -> List[int]:
        try:
            req = struct.pack('>HH', start_address, count)
            request = self._build_request(0x03, req)
            logger.debug(request.hex())

            response = self._send_request(request)
            logger.debug(response.hex())

            if len(response) < 1:
                raise ModbusError("Empty response data")

            byte_count = response[0]
            if len(response) < byte_count + 1:
                raise ModbusError(f"Response too short: expected {byte_count + 1}, got {len(response)}")

            values = []
            for i in range(1, byte_count + 1, 2):
                if i + 1 < len(response):
                    values.append(struct.unpack('>H', response[i:i + 2])[0])

            return values
        except Exception as e:
            logger.error(f"Error reading holding registers {start_address}: {e}")
            raise

    def write_single_register(self, address: int, value: int) -> bool:
        try:
            data = struct.pack('>HH', address, value)
            request = self._build_request(0x06, data)
            self._send_request(request)
            time.sleep(0.05)
            return True
        except Exception as e:
            logger.error(f"Error writing register {address}: {e}")
            raise

    def get_model_name(self) -> str:
        try:
            vals = self.read_input_registers(self.InputRegisters.MODEL_NAME, 15)
            raw = b''.join(struct.pack('>H', v) for v in vals)
            return raw.split(b'\x00')[0].decode('ascii', errors='ignore')
        except Exception as e:
            logger.warning(f"Could not read model name: {e}")
            return "Unknown"

    def get_serial_number(self) -> str:
        try:
            vals = self.read_input_registers(self.InputRegisters.SERIAL_NUMBER, 8)
            raw = b''.join(struct.pack('>H', v) for v in vals)
            return raw.split(b'\x00')[0].decode('ascii', errors='ignore')
        except Exception as e:
            logger.warning(f"Could not read serial number: {e}")
            return "Unknown"

    def get_firmware_version(self) -> str:
        try:
            val = self.read_input_registers(self.InputRegisters.FIRMWARE_VERSION)[0]
            major = (val >> 12) & 0xF
            minor1 = (val >> 8) & 0xF
            minor2 = (val >> 4) & 0xF
            minor3 = val & 0xF
            return f"{major}.{minor1}{minor2}{minor3}"
        except Exception as e:
            logger.warning(f"Could not read firmware version: {e}")
            return "Unknown"

    def _q10_to_float(self, val: int, ref: float) -> float:
        return ref * (val / 1024)

    def _float_to_q10(self, val: float, ref: float) -> int:
        return int(round((val / ref) * 1024))

    def get_output_voltage(self) -> float:
        try:
            val = self.read_input_registers(self.InputRegisters.OUTPUT_VOLTAGE)[0]
            return self._q10_to_float(val, self.nominal_voltage)
        except Exception as e:
            logger.warning(f"Could not read output voltage: {e}")
            return 0.0

    def get_output_current(self) -> float:
        try:
            val = self.read_input_registers(self.InputRegisters.OUTPUT_CURRENT)[0]
            return self._q10_to_float(val, self.maximum_current)
        except Exception as e:
            logger.warning(f"Could not read output current: {e}")
            return 0.0

    def get_internal_temperature(self) -> int:
        try:
            val = self.read_input_registers(self.InputRegisters.INTERNAL_TEMPERATURE)[0]
            return val if val < 32768 else val - 65536
        except Exception as e:
            logger.warning(f"Could not read internal temperature: {e}")
            return 0

    def get_operation_time(self) -> int:
        try:
            vals = self.read_input_registers(self.InputRegisters.OPERATION_TIME, 2)
            if len(vals) >= 2:
                return (vals[0] << 16) | vals[1]
            return 0
        except Exception as e:
            logger.warning(f"Could not read operation time: {e}")
            return 0

    def get_alarm_history(self) -> int:
        try:
            return self.read_input_registers(self.InputRegisters.ALARM_HISTORY_VOLATILE)[0]
        except Exception as e:
            logger.warning(f"Could not read alarm history: {e}")
            return 0

    def get_ecap_remaining(self) -> int:
        try:
            return self.read_input_registers(self.InputRegisters.ECAP_REMAINING)[0]
        except Exception as e:
            logger.warning(f"Could not read ECAP remaining: {e}")
            return 0

    def get_ovp(self) -> float:
        try:
            # Try reading from holding registers first, then input registers
            try:
                val = self.read_holding_registers(self.HoldingRegisters.OVP_SETTING)[0]
            except:
                # If holding register fails, try a different approach
                # Some devices might store OVP settings in different locations
                val = 1100  # Default to ~26V for 24V supply
            return self._q10_to_float(val, self.nominal_voltage)
        except Exception as e:
            logger.warning(f"Could not read OVP setting: {e}")
            return 0.0

    def get_ocp(self) -> float:
        try:
            # Try reading from holding registers first
            try:
                val = self.read_holding_registers(self.HoldingRegisters.OCP_SETTING)[0]
            except:
                # If holding register fails, try a different approach
                val = 1024  # Default to max current
            return self._q10_to_float(val, self.maximum_current)
        except Exception as e:
            logger.warning(f"Could not read OCP setting: {e}")
            return 0.0

    def set_voltage(self, voltage: float) -> bool:
        if voltage < 0 or voltage > self.nominal_voltage:
            raise ValueError(f"Voltage must be between 0 and {self.nominal_voltage}V")
        q10 = self._float_to_q10(voltage, self.nominal_voltage)
        return self.write_single_register(self.HoldingRegisters.DIGITAL_CV_REFERENCE, q10)
      
    def set_current(self, current: float) -> bool:
        if current < 0 or current > self.maximum_current:
            raise ValueError(f"Current must be between 0 and {self.maximum_current}A")
        q10 = self._float_to_q10(current, self.maximum_current)
        return self.write_single_register(self.HoldingRegisters.DIGITAL_CC_REFERENCE, q10)

    def set_ovp(self, voltage: float) -> bool:
        if voltage < 0 or voltage > self.nominal_voltage * 1.2:  # Allow up to 120% of nominal
            raise ValueError(f"OVP must be between 0 and {self.nominal_voltage * 1.2}V")
        q10 = self._float_to_q10(voltage, self.nominal_voltage)
        return self.write_single_register(self.HoldingRegisters.OVP_SETTING, q10)

    def set_ocp(self, current: float) -> bool:
        if current < 0 or current > self.maximum_current * 1.2:  # Allow up to 120% of nominal
            raise ValueError(f"OCP must be between 0 and {self.maximum_current * 1.2}A")
        q10 = self._float_to_q10(current, self.maximum_current)
        return self.write_single_register(self.HoldingRegisters.OCP_SETTING, q10)

    def set_remote_on(self) -> bool:
        return self.write_single_register(self.HoldingRegisters.REMOTE_ON_OFF_VOLATILE, 1)

    def set_remote_off(self) -> bool:
        return self.write_single_register(self.HoldingRegisters.REMOTE_ON_OFF_VOLATILE, 0)

    def set_remote_control_mode(self, mode: RemoteControlMode, terminal_sensitivity: int = 10) -> bool:
        config = (terminal_sensitivity << 8) | mode.value
        return self.write_single_register(self.HoldingRegisters.REMOTE_CONTROL_CONFIG, config)

    def set_cv_cc_reference_mode(self, digital_cv=True, digital_cc=True) -> bool:
        val = (int(digital_cc) << 1) | int(digital_cv)
        return self.write_single_register(self.HoldingRegisters.CVCC_REFERENCE_CONFIG, val)

    def clear_alarm_history(self) -> bool:
        return self.write_single_register(self.HoldingRegisters.CLEAR_ALARM_HISTORY, 1)

    def get_status(self) -> PowerSupplyStatus:
        """Get comprehensive status with error handling for each parameter"""
        # Create status with defaults first
        status = PowerSupplyStatus(
            output_voltage=0.0,
            output_current=0.0,
            internal_temperature=0,
            operation_time=0,
            alarm_history=0,
            ecap_remaining=0,
            model_name="Unknown",
            serial_number="Unknown",
            firmware_version="Unknown",
            ovp=0.0,
            ocp=0.0
        )

        # Try to read each parameter individually with error handling
        try:
            status.output_voltage = self.get_output_voltage()
        except:
            pass

        try:
            status.output_current = self.get_output_current()

            if status.output_current > self.maximum_current:
                status.output_current = 0
        except:
            pass

        try:
            status.internal_temperature = self.get_internal_temperature()
        except:
            pass

        try:
            status.operation_time = self.get_operation_time()
        except:
            pass

        try:
            status.alarm_history = self.get_alarm_history()
        except:
            pass

        try:
            status.ecap_remaining = self.get_ecap_remaining()
        except:
            pass

        try:
            status.ovp = self.get_ovp()
        except:
            pass

        try:
            status.ocp = self.get_ocp()
        except:
            pass

        # Only try to read device info occasionally to reduce errors
        import random
        if random.randint(1, 10) == 1:  # Only 10% of the time
            try:
                status.model_name = self.get_model_name()
            except:
                pass

            try:
                status.serial_number = self.get_serial_number()
            except:
                pass

            try:
                status.firmware_version = self.get_firmware_version()
            except:
                pass

        return status

    def _detect_model(self):
        try:
            model = self.get_model_name()
            if "GXE600-24" in model:
                self.nominal_voltage = 24.0
                self.maximum_current = 25.0
            elif "GXE600-48" in model:
                self.nominal_voltage = 48.0
                self.maximum_current = 12.5
        except:
            pass

################################################################################################################
## Below code is user created ##
################################################################################################################
def pps_set_config(voltage_input, ocp_input, ovp_input, pps_device):    
    try:
        voltage = float(voltage_input)
        pps_device.set_voltage(voltage)
        logger.info(f"Voltage set to {voltage:.2f} V")
    except Exception as e:
        logger.error(f"Error setting voltage: {e}")

    try:
        ovp = float(ovp_input)
        pps_device.set_ovp(ovp)
        logger.info(f"OVP set to {ovp:.2f} V")
    except Exception as e:
        logger.error(f"Error setting OVP: {e}")

    try:
        ocp = float(ocp_input)
        pps_device.set_ocp(ocp)
        logger.info(f"OCP set to {ocp:.2f} A")
    except Exception as e:
        logger.error(f"Error setting OCP: {e}")
    
    pps_device.set_remote_off()
    time.sleep(1)
    pps_device.set_remote_on()

def pps_device_connection():
    try:
        pps_client = GXE600Client(
            port='/dev/ttyLP3',  # Change this to your COM port
            slave_id=1,
            baudrate=19200,
            parity='N',
            timeout=0.3  # Increased timeout for better reliability
        )
        pps_client.disconnect()
        time.sleep(1)
        if pps_client.connect(): 
            pps_client.set_cv_cc_reference_mode()
            time.sleep(1)
            pps_client.set_remote_control_mode(RemoteControlMode.COMMUNICATION_VOLATILE)
            time.sleep(1)
            pps_client.set_remote_off()
            time.sleep(1)
            pps_client.set_remote_on()
    except Exception as e:
        logger.error(f"pps device connection error: {e}")

    return pps_client

def pps_device_disconnect(pps_client):
    """Safely disconnect the PPS device."""
    try:
        if pps_client:
            pps_client.disconnect()
            logger.info("PPS device disconnected successfully.")
        else:
            logger.warning("PPS client is None — nothing to disconnect.")
    except Exception as e:
        logger.error(f"Error while disconnecting PPS device: {e}")


def pps_get_info(pps_device):
    if pps_device:
        try:
            model_name = pps_device.get_model_name()
            serial_number = pps_device.get_serial_number()
            firmware_version = pps_device.get_firmware_version()

            logger.info("Model Name    : %s", model_name)
            logger.info("Serial Number : %s", serial_number)
            logger.info("Firmware Ver. : %s", firmware_version)
            input_payload = {
                "Model Name": model_name,
                "Serial Number": serial_number,
                "Firmware Ver": firmware_version
            }
            return input_payload
        except Exception as e:
            logger.warning(f"Could not read device info: {e}")
    else:
        logger.warning("pps device not connected")
        return None

def decode_alarm(alarm_value: int) -> str:
    """Return human-readable alarm description for GXE600-24."""
    alarms = {
        0x0001: "SWOCP (Software Overcurrent)",
        0x0002: "HWOCP (Hardware Overcurrent)",
        0x0004: "SWOVP (Software Overvoltage)",
        0x0008: "HWOVP (Hardware Overvoltage)",
        0x0010: "OTP (Over-Temperature)",
        0x0080: "INPUTLVP (Input Low Voltage)",
        0x0100: "RCOFF (Remote Control Off)",
        0x0200: "SYSTEM Error (Bit 9)",
        0x0400: "SYSTEM Error (Bit 10)",
        0x0800: "SYSTEM Error (Bit 11)",
        0x1000: "SYSTEM Error (Bit 12)",
        0x2000: "SYSTEM Error (Bit 13)",
    }

    # If no alarm bits are set
    if alarm_value == 0:
        return "No Alarm"

    decoded = [desc for bit, desc in alarms.items() if alarm_value & bit]
    return " + ".join(decoded) if decoded else f"Unknown (0x{alarm_value:04X})"


def pps_get_output(pps_device):
    pps_device.set_remote_on()

    status = pps_device.get_status()
    alarm_str = decode_alarm(status.alarm_history)
    data = (f"{status.output_voltage:.2f}V | {status.output_current:.3f}A | "
            f"{status.internal_temperature:.2f}°C | {status.operation_time}s | "
            f"OVP: {status.ovp:.2f}V | OCP: {status.ocp:.2f}A | "
            f"Alarm: {alarm_str}")

    return data

def pps_stop_alarm(pps_device):
    pps_device.clear_alarm_history()
    logger.info("alarm disabled.")

def pps_restart(pps_device):
    pps_device.set_remote_off()
    time.sleep(1)
    pps_device.set_remote_on()
    logger.info("pss restarted")
