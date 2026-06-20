# from pickle import GLOBAL

# import serial
# import struct
# import time
# import logging
# from typing import Optional, List
# from enum import Enum
# from dataclasses import dataclass

# # Setup logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[
#         logging.FileHandler("gxe600_monitor.log"),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)


# class ModbusError(Exception):
#     pass


# class ExceptionCode(Enum):
#     ILLEGAL_FUNCTION = 0x01
#     ILLEGAL_DATA_ADDRESS = 0x02
#     ILLEGAL_DATA_VALUE = 0x03
#     SLAVE_DEVICE_FAILURE = 0x04
#     SLAVE_DEVICE_BUSY = 0x06


# class RemoteControlMode(Enum):
#     TERMINAL_INPUT = 0
#     COMMUNICATION_VOLATILE = 1
#     COMMUNICATION_NON_VOLATILE = 2
#     TERMINAL_AND_VOLATILE = 3
#     TERMINAL_AND_NON_VOLATILE = 4


# @dataclass
# class PowerSupplyStatus:
#     output_voltage: float
#     output_current: float
#     internal_temperature: int
#     operation_time: int
#     alarm_history: int
#     ecap_remaining: int
#     model_name: str = ""
#     serial_number: str = ""
#     firmware_version: str = ""
#     ovp: float = 0.0
#     ocp: float = 0.0


# class GXE600Client:
#     class InputRegisters:
#         ALARM_HISTORY_VOLATILE = 0x0000
#         OUTPUT_VOLTAGE = 0x0001
#         OUTPUT_CURRENT = 0x0002
#         INTERNAL_TEMPERATURE = 0x0003
#         OPERATION_TIME = 0x0004  # 2 registers
#         ECAP_REMAINING = 0x0006
#         MODEL_NAME = 0x01F4  # 15 registers
#         SERIAL_NUMBER = 0x0208  # 8 registers
#         FIRMWARE_VERSION = 0x03E8

#     class HoldingRegisters:
#         REMOTE_ON_OFF_VOLATILE = 0x0000
#         REMOTE_ON_OFF_NON_VOLATILE = 0x0005
#         REMOTE_CONTROL_CONFIG = 0x0064
#         CVCC_REFERENCE_CONFIG = 0x0065
#         DIGITAL_CV_REFERENCE = 0x0067
#         DIGITAL_CC_REFERENCE = 0x0068
#         OVP_SETTING = 0x0069
#         OCP_SETTING = 0x006A
#         CLEAR_ALARM_HISTORY = 0x0073

#     def __init__(self, port: str, slave_id: int = 1, baudrate: int = 19200, parity: str = 'N', timeout: float = 1.0):
#         self.port = port
#         self.slave_id = slave_id
#         self.baudrate = baudrate
#         self.parity = parity.upper()
#         self.timeout = timeout
#         self.serial_conn: Optional[serial.Serial] = None
#         self.nominal_voltage = 24.0
#         self.maximum_current = 25.0

#     def connect(self) -> bool:
#         try:
#             self.serial_conn = serial.Serial(
#                 port=self.port,
#                 baudrate=self.baudrate,
#                 bytesize=8,
#                 parity=self.parity,
#                 stopbits=1,
#                 timeout=self.timeout
#             )
#             logger.info(f"Connected to GXE600 on {self.port}")
#             time.sleep(0.2)
#             self._detect_model()
#             return True
#         except Exception as e:
#             logger.error(f"Connection error: {e}")
#             return False

#     def disconnect(self):
#         if self.serial_conn and self.serial_conn.is_open:
#             self.serial_conn.close()
#             logger.info("Disconnected")

#     def _calculate_crc16(self, data: bytes) -> int:
#         crc = 0xFFFF
#         for byte in data:
#             crc ^= byte
#             for _ in range(8):
#                 if crc & 1:
#                     crc = (crc >> 1) ^ 0xA001
#                 else:
#                     crc >>= 1
#         return crc

#     def _build_request(self, function_code: int, data: bytes) -> bytes:
#         frame = struct.pack('BB', self.slave_id, function_code) + data
#         crc = self._calculate_crc16(frame)
#         return frame + struct.pack('<H', crc)

#     def _send_request(self, request: bytes) -> bytes:
#         if not self.serial_conn or not self.serial_conn.is_open:
#             raise ModbusError("Serial connection not open")

#         self.serial_conn.reset_input_buffer()
#         self.serial_conn.write(request)

#         # Read response with timeout handling
#         response = self.serial_conn.read(256)
#         if len(response) < 5:
#             raise ModbusError(f"Incomplete response: received {len(response)} bytes")

#         # Check for MODBUS exception response
#         if len(response) >= 3 and response[1] & 0x80:
#             exception_code = response[2]
#             raise ModbusError(f"MODBUS Exception: {exception_code}")

#         # Verify CRC
#         crc_received = struct.unpack('<H', response[-2:])[0]
#         crc_calculated = self._calculate_crc16(response[:-2])
#         if crc_received != crc_calculated:
#             raise ModbusError("CRC mismatch")

#         return response[2:-2]

#     def read_input_registers(self, start_address: int, count: int = 1) -> List[int]:
#         try:
#             req = struct.pack('>HH', start_address, count)
#             request = self._build_request(0x04, req)
#             response = self._send_request(request)

#             if len(response) < 1:
#                 raise ModbusError("Empty response data")

#             byte_count = response[0]
#             if len(response) < byte_count + 1:
#                 raise ModbusError(f"Response too short: expected {byte_count + 1}, got {len(response)}")

#             values = []
#             for i in range(1, byte_count + 1, 2):
#                 if i + 1 < len(response):
#                     values.append(struct.unpack('>H', response[i:i + 2])[0])

#             return values
#         except Exception as e:
#             logger.error(f"Error reading input registers {start_address}: {e}")
#             raise

#     def read_holding_registers(self, start_address: int, count: int = 1) -> List[int]:
#         try:
#             req = struct.pack('>HH', start_address, count)
#             request = self._build_request(0x03, req)
#             response = self._send_request(request)

#             if len(response) < 1:
#                 raise ModbusError("Empty response data")

#             byte_count = response[0]
#             if len(response) < byte_count + 1:
#                 raise ModbusError(f"Response too short: expected {byte_count + 1}, got {len(response)}")

#             values = []
#             for i in range(1, byte_count + 1, 2):
#                 if i + 1 < len(response):
#                     values.append(struct.unpack('>H', response[i:i + 2])[0])

#             return values
#         except Exception as e:
#             logger.error(f"Error reading holding registers {start_address}: {e}")
#             raise

#     def write_single_register(self, address: int, value: int) -> bool:
#         try:
#             data = struct.pack('>HH', address, value)
#             request = self._build_request(0x06, data)
#             self._send_request(request)
#             time.sleep(0.05)
#             return True
#         except Exception as e:
#             logger.error(f"Error writing register {address}: {e}")
#             raise

#     def get_model_name(self) -> str:
#         try:
#             vals = self.read_input_registers(self.InputRegisters.MODEL_NAME, 15)
#             raw = b''.join(struct.pack('>H', v) for v in vals)
#             return raw.split(b'\x00')[0].decode('ascii', errors='ignore')
#         except Exception as e:
#             logger.warning(f"Could not read model name: {e}")
#             return "Unknown"

#     def get_serial_number(self) -> str:
#         try:
#             vals = self.read_input_registers(self.InputRegisters.SERIAL_NUMBER, 8)
#             raw = b''.join(struct.pack('>H', v) for v in vals)
#             return raw.split(b'\x00')[0].decode('ascii', errors='ignore')
#         except Exception as e:
#             logger.warning(f"Could not read serial number: {e}")
#             return "Unknown"

#     def get_firmware_version(self) -> str:
#         try:
#             val = self.read_input_registers(self.InputRegisters.FIRMWARE_VERSION)[0]
#             major = (val >> 12) & 0xF
#             minor1 = (val >> 8) & 0xF
#             minor2 = (val >> 4) & 0xF
#             minor3 = val & 0xF
#             return f"{major}.{minor1}{minor2}{minor3}"
#         except Exception as e:
#             logger.warning(f"Could not read firmware version: {e}")
#             return "Unknown"

#     def _q10_to_float(self, val: int, ref: float) -> float:
#         return ref * (val / 1024)

#     def _float_to_q10(self, val: float, ref: float) -> int:
#         return int(round((val / ref) * 1024))

#     def get_output_voltage(self) -> float:
#         try:
#             val = self.read_input_registers(self.InputRegisters.OUTPUT_VOLTAGE)[0]
#             return self._q10_to_float(val, self.nominal_voltage)
#         except Exception as e:
#             logger.warning(f"Could not read output voltage: {e}")
#             return 0.0

#     def get_output_current(self) -> float:
#         try:
#             val = self.read_input_registers(self.InputRegisters.OUTPUT_CURRENT)[0]
#             return self._q10_to_float(val, self.maximum_current)
#         except Exception as e:
#             logger.warning(f"Could not read output current: {e}")
#             return 0.0

#     def get_internal_temperature(self) -> int:
#         try:
#             val = self.read_input_registers(self.InputRegisters.INTERNAL_TEMPERATURE)[0]
#             return val if val < 32768 else val - 65536
#         except Exception as e:
#             logger.warning(f"Could not read internal temperature: {e}")
#             return 0

#     def get_operation_time(self) -> int:
#         try:
#             vals = self.read_input_registers(self.InputRegisters.OPERATION_TIME, 2)
#             if len(vals) >= 2:
#                 return (vals[0] << 16) | vals[1]
#             return 0
#         except Exception as e:
#             logger.warning(f"Could not read operation time: {e}")
#             return 0

#     def get_alarm_history(self) -> int:
#         try:
#             return self.read_input_registers(self.InputRegisters.ALARM_HISTORY_VOLATILE)[0]
#         except Exception as e:
#             logger.warning(f"Could not read alarm history: {e}")
#             return 0

#     def get_ecap_remaining(self) -> int:
#         try:
#             return self.read_input_registers(self.InputRegisters.ECAP_REMAINING)[0]
#         except Exception as e:
#             logger.warning(f"Could not read ECAP remaining: {e}")
#             return 0

#     def get_ovp(self) -> float:
#         try:
#             # Try reading from holding registers first, then input registers
#             try:
#                 val = self.read_holding_registers(self.HoldingRegisters.OVP_SETTING)[0]
#             except:
#                 # If holding register fails, try a different approach
#                 # Some devices might store OVP settings in different locations
#                 val = 1100  # Default to ~26V for 24V supply
#             return self._q10_to_float(val, self.nominal_voltage)
#         except Exception as e:
#             logger.warning(f"Could not read OVP setting: {e}")
#             return 0.0

#     def get_ocp(self) -> float:
#         try:
#             # Try reading from holding registers first
#             try:
#                 val = self.read_holding_registers(self.HoldingRegisters.OCP_SETTING)[0]
#             except:
#                 # If holding register fails, try a different approach
#                 val = 1024  # Default to max current
#             return self._q10_to_float(val, self.maximum_current)
#         except Exception as e:
#             logger.warning(f"Could not read OCP setting: {e}")
#             return 0.0

#     def set_voltage(self, voltage: float) -> bool:
#         if voltage < 0 or voltage > self.nominal_voltage:
#             raise ValueError(f"Voltage must be between 0 and {self.nominal_voltage}V")
#         q10 = self._float_to_q10(voltage, self.nominal_voltage)
#         return self.write_single_register(self.HoldingRegisters.DIGITAL_CV_REFERENCE, q10)

#     def set_current(self, current: float) -> bool:
#         if current < 0 or current > self.maximum_current:
#             raise ValueError(f"Current must be between 0 and {self.maximum_current}A")
#         q10 = self._float_to_q10(current, self.maximum_current)
#         return self.write_single_register(self.HoldingRegisters.DIGITAL_CC_REFERENCE, q10)

#     def set_ovp(self, voltage: float) -> bool:
#         if voltage < 0 or voltage > self.nominal_voltage * 1.2:  # Allow up to 120% of nominal
#             raise ValueError(f"OVP must be between 0 and {self.nominal_voltage * 1.2}V")
#         q10 = self._float_to_q10(voltage, self.nominal_voltage)
#         return self.write_single_register(self.HoldingRegisters.OVP_SETTING, q10)

#     def set_ocp(self, current: float) -> bool:
#         if current < 0 or current > self.maximum_current * 1.2:  # Allow up to 120% of nominal
#             raise ValueError(f"OCP must be between 0 and {self.maximum_current * 1.2}A")
#         q10 = self._float_to_q10(current, self.maximum_current)
#         return self.write_single_register(self.HoldingRegisters.OCP_SETTING, q10)

#     def set_remote_on(self) -> bool:
#         return self.write_single_register(self.HoldingRegisters.REMOTE_ON_OFF_VOLATILE, 1)

#     def set_remote_off(self) -> bool:
#         return self.write_single_register(self.HoldingRegisters.REMOTE_ON_OFF_VOLATILE, 0)

#     def set_remote_control_mode(self, mode: RemoteControlMode, terminal_sensitivity: int = 10) -> bool:
#         config = (terminal_sensitivity << 8) | mode.value
#         return self.write_single_register(self.HoldingRegisters.REMOTE_CONTROL_CONFIG, config)

#     def set_cv_cc_reference_mode(self, digital_cv=True, digital_cc=True) -> bool:
#         val = (int(digital_cc) << 1) | int(digital_cv)
#         return self.write_single_register(self.HoldingRegisters.CVCC_REFERENCE_CONFIG, val)

#     def clear_alarm_history(self) -> bool:
#         return self.write_single_register(self.HoldingRegisters.CLEAR_ALARM_HISTORY, 1)

#     def get_status(self) -> PowerSupplyStatus:
#         """Get comprehensive status with error handling for each parameter"""
#         return PowerSupplyStatus(
#             output_voltage=self.get_output_voltage(),
#             output_current=self.get_output_current(),
#             internal_temperature=self.get_internal_temperature(),
#             operation_time=self.get_operation_time(),
#             alarm_history=self.get_alarm_history(),
#             ecap_remaining=self.get_ecap_remaining(),
#             model_name=self.get_model_name(),
#             serial_number=self.get_serial_number(),
#             firmware_version=self.get_firmware_version(),
#             ovp=self.get_ovp(),
#             ocp=self.get_ocp()
#         )

#     def _detect_model(self):
#         try:
#             model = self.get_model_name()
#             if "GXE600-24" in model:
#                 self.nominal_voltage = 24.0
#                 self.maximum_current = 25.0
#             elif "GXE600-48" in model:
#                 self.nominal_voltage = 48.0
#                 self.maximum_current = 12.5
#         except:
#             pass

# def pwm_mode_all_selection(device):
#     voltage_input = input("Enter output voltage to set (V) or press Enter to skip: ").strip()
#     if voltage_input:
#         try:
#             voltage = float(voltage_input)
#             device.set_voltage(voltage)
#             logger.info(f"Voltage set to {voltage:.2f} V")
#         except Exception as e:
#             logger.error(f"Error setting voltage: {e}")

#     current_input = input("Enter output current limit to set (A) or press Enter to skip: ").strip()
#     if current_input:
#         try:
#             current = float(current_input)
#             device.set_current(current)
#             logger.info(f"Current limit set to {current:.2f} A")
#         except Exception as e:
#             logger.error(f"Error setting current: {e}")

#     ovp_input = input("Enter OVP limit to set (V) or press Enter to skip: ").strip()
#     if ovp_input:
#         try:
#             ovp = float(ovp_input)
#             device.set_ovp(ovp)
#             logger.info(f"OVP set to {ovp:.2f} V")
#         except Exception as e:
#             logger.error(f"Error setting OVP: {e}")

#     ocp_input = input("Enter OCP limit to set (A) or press Enter to skip: ").strip()
#     if ocp_input:
#         try:
#             ocp = float(ocp_input)
#             device.set_ocp(ocp)
#             logger.info(f"OCP set to {ocp:.2f} A")
#         except Exception as e:
#             logger.error(f"Error setting OCP: {e}")


# def pwm_mode_selection(cmd, cli):
#     if cmd == "all":
#         pwm_mode_all_selection(cli)

#     if cmd == "CV":
#         voltage_input = input("Enter output voltage to set (V) or press Enter to skip: ").strip()
#         if voltage_input:
#             try:
#                 voltage = float(voltage_input)
#                 cli.set_voltage(voltage)
#                 logger.info(f"Voltage set to {voltage:.2f} V")
#             except Exception as e:
#                 logger.error(f"Error setting voltage: {e}")

#     if cmd == "CC":
#         current_input = input("Enter output current limit to set (A) or press Enter to skip: ").strip()
#         if current_input:
#             try:
#                 current = float(current_input)
#                 cli.set_current(current)
#                 logger.info(f"Current limit set to {current:.2f} A")
#             except Exception as e:
#                 logger.error(f"Error setting current: {e}")

#     if cmd == "OVP":
#         ovp_input = input("Enter OVP limit to set (V) or press Enter to skip: ").strip()
#         if ovp_input:
#             try:
#                 ovp = float(ovp_input)
#                 cli.set_ovp(ovp)
#                 logger.info(f"OVP set to {ovp:.2f} V")
#             except Exception as e:
#                 logger.error(f"Error setting OVP: {e}")

#     if cmd == "OCP":
#         ocp_input = input("Enter OCP limit to set (A) or press Enter to skip: ").strip()
#         if ocp_input:
#             try:
#                 ocp = float(ocp_input)
#                 cli.set_ocp(ocp)
#                 logger.info(f"OCP set to {ocp:.2f} A")
#             except Exception as e:
#                 logger.error(f"Error setting OCP: {e}")

# def device_connection():
#     client = GXE600Client(
#         port='/dev/ttyLP3',  # Change this to your COM port
#         slave_id=1,
#         baudrate=19200,
#         parity='N',
#         timeout=0.5  # Increased timeout for reliability
#     )

#     while True:
#         if not client.connect():
#             logger.warning("Connection failed. Retrying in 5 seconds...")
#             time.sleep(1.5)
#             continue
#         else:
#             logger.info("Model Name    : %s", client.get_model_name())
#             logger.info("Serial Number : %s", client.get_serial_number())
#             logger.info("Firmware Ver. : %s", client.get_firmware_version())

#             # Configure communication mode
#             client.set_cv_cc_reference_mode()
#             client.set_remote_control_mode(RemoteControlMode.COMMUNICATION_VOLATILE)
#             client.set_remote_on()
#             logger.info("Output enabled. Monitoring started. Press Ctrl+C to stop.")

#             return client

# def main():
#     global clients
#     try:
#         clients = device_connection()
#         mode = input("Enter mode ").strip()
#         pwm_mode_selection(mode, clients)
#         while True:
#             try:
#                 status = clients.get_status()
#                 logger.info(f"{status.output_voltage:.2f}V | {status.output_current:.2f}A | "
#                             f"{status.internal_temperature}°C | {status.operation_time}s | "
#                             f"OVP: {status.ovp:.2f}V | OCP: {status.ocp:.2f}A | "
#                             f"Alarm: {status.alarm_history:04X}")
#                 time.sleep(1)
#             except Exception as e:
#                 logger.error(f"Error reading status: {e}")
#                 time.sleep(1)

#     except KeyboardInterrupt:
#         logger.info("Monitoring stopped by user.")
#     except Exception as e:
#         logger.error(f"Unexpected error: {e}. Retrying in 5 seconds...")
#         time.sleep(5)
#     finally:
#         try:
#                 clients.set_remote_off()
#                 logger.info("Output disabled.")
#         except:
#             pass
#         clients.disconnect()


# if __name__ == '__main__':
#     main()
from pickle import GLOBAL
import serial
import struct
import time
import logging
from typing import Optional, List, Tuple, Dict
from enum import Enum
from dataclasses import dataclass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("gxe600_monitor.log"),
        logging.StreamHandler()
    ]
)
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


@dataclass
class ConnectionParams:
    """Container for discovered connection parameters"""
    baudrate: int
    parity: str
    slave_id: int
    port: str
    

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
        """Connect with current parameters"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity=self.parity,
                stopbits=1,
                timeout=self.timeout
            )
            logger.info(f"Connected to {self.port} with baudrate={self.baudrate}, parity={self.parity}, slave_id={self.slave_id}")
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
            response = self._send_request(request)

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
            response = self._send_request(request)

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

    def test_connection(self) -> bool:
        """Test if the current connection parameters work"""
        try:
            # Try to read a simple register
            val = self.read_input_registers(self.InputRegisters.OUTPUT_VOLTAGE, 1)
            logger.debug(f"Test successful, read value: {val}")
            return True
        except Exception as e:
            logger.debug(f"Test failed: {e}")
            return False

    def auto_detect_params(self) -> Optional[ConnectionParams]:
        """
        Automatically detect baudrate, parity, and slave ID
        Returns ConnectionParams if successful, None otherwise
        """
        logger.info("Starting auto-detection of connection parameters...")
        
        # Common baud rates for Modbus
        baudrates = [19200, 9600, 4800, 2400, 1200, 57600, 38400, 115200]
        
        # Parity options
        parities = ['N', 'E', 'O']  # None, Even, Odd
        
        # Slave ID range (1-247 for Modbus RTU)
        slave_ids = list(range(1, 248))
        
        # Timeout for faster scanning
        original_timeout = self.timeout
        self.timeout = 0.1
        
        found_params = None
        
        for baudrate in baudrates:
            logger.info(f"Trying baudrate: {baudrate}")
            
            for parity in parities:
                logger.info(f"  Trying parity: {parity}")
                
                # Temporarily update connection parameters
                self.baudrate = baudrate
                self.parity = parity
                
                # Try to connect with these parameters
                try:
                    if self.serial_conn and self.serial_conn.is_open:
                        self.disconnect()
                    time.sleep(0.1)
                    
                    self.connect()
                    time.sleep(0.2)
                    
                    # Try each slave ID
                    for slave_id in slave_ids:
                        self.slave_id = slave_id
                        logger.debug(f"    Trying slave ID: {slave_id}")
                        
                        if self.test_connection():
                            found_params = ConnectionParams(
                                baudrate=baudrate,
                                parity=parity,
                                slave_id=slave_id,
                                port=self.port
                            )
                            logger.info(f"Found parameters: {found_params}")
                            
                            # Restore original timeout
                            self.timeout = original_timeout
                            
                            # Disconnect and reconnect with found params
                            self.disconnect()
                            time.sleep(0.1)
                            
                            # Update instance with found parameters
                            self.baudrate = baudrate
                            self.parity = parity
                            self.slave_id = slave_id
                            
                            return found_params
                            
                except Exception as e:
                    logger.debug(f"Failed with baudrate={baudrate}, parity={parity}: {e}")
                    continue
        
        # Restore original timeout
        self.timeout = original_timeout
        
        if not found_params:
            logger.error("Could not auto-detect connection parameters")
        
        return found_params

    def connect_with_auto_detect(self, max_retries: int = 3) -> Optional[ConnectionParams]:
        """
        Connect with auto-detection of parameters
        Returns ConnectionParams if successful, None otherwise
        """
        for attempt in range(max_retries):
            logger.info(f"Auto-detect attempt {attempt + 1}/{max_retries}")
            
            params = self.auto_detect_params()
            if params:
                # Connect with discovered parameters
                if self.connect():
                    logger.info(f"Successfully connected with auto-detected parameters: {params}")
                    return params
                else:
                    logger.warning(f"Failed to connect with auto-detected parameters")
            else:
                logger.warning(f"Auto-detection failed on attempt {attempt + 1}")
            
            if attempt < max_retries - 1:
                logger.info("Retrying in 2 seconds...")
                time.sleep(2)
        
        return None

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
        return PowerSupplyStatus(
            output_voltage=self.get_output_voltage(),
            output_current=self.get_output_current(),
            internal_temperature=self.get_internal_temperature(),
            operation_time=self.get_operation_time(),
            alarm_history=self.get_alarm_history(),
            ecap_remaining=self.get_ecap_remaining(),
            model_name=self.get_model_name(),
            serial_number=self.get_serial_number(),
            firmware_version=self.get_firmware_version(),
            ovp=self.get_ovp(),
            ocp=self.get_ocp()
        )

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


def pwm_mode_all_selection(device):
    voltage_input = input("Enter output voltage to set (V) or press Enter to skip: ").strip()
    if voltage_input:
        try:
            voltage = float(voltage_input)
            device.set_voltage(voltage)
            logger.info(f"Voltage set to {voltage:.2f} V")
        except Exception as e:
            logger.error(f"Error setting voltage: {e}")

    current_input = input("Enter output current limit to set (A) or press Enter to skip: ").strip()
    if current_input:
        try:
            current = float(current_input)
            device.set_current(current)
            logger.info(f"Current limit set to {current:.2f} A")
        except Exception as e:
            logger.error(f"Error setting current: {e}")

    ovp_input = input("Enter OVP limit to set (V) or press Enter to skip: ").strip()
    if ovp_input:
        try:
            ovp = float(ovp_input)
            device.set_ovp(ovp)
            logger.info(f"OVP set to {ovp:.2f} V")
        except Exception as e:
            logger.error(f"Error setting OVP: {e}")

    ocp_input = input("Enter OCP limit to set (A) or press Enter to skip: ").strip()
    if ocp_input:
        try:
            ocp = float(ocp_input)
            device.set_ocp(ocp)
            logger.info(f"OCP set to {ocp:.2f} A")
        except Exception as e:
            logger.error(f"Error setting OCP: {e}")


def pwm_mode_selection(cmd, cli):
    if cmd == "all":
        pwm_mode_all_selection(cli)

    if cmd == "CV":
        voltage_input = input("Enter output voltage to set (V) or press Enter to skip: ").strip()
        if voltage_input:
            try:
                voltage = float(voltage_input)
                cli.set_voltage(voltage)
                logger.info(f"Voltage set to {voltage:.2f} V")
            except Exception as e:
                logger.error(f"Error setting voltage: {e}")

    if cmd == "CC":
        current_input = input("Enter output current limit to set (A) or press Enter to skip: ").strip()
        if current_input:
            try:
                current = float(current_input)
                cli.set_current(current)
                logger.info(f"Current limit set to {current:.2f} A")
            except Exception as e:
                logger.error(f"Error setting current: {e}")

    if cmd == "OVP":
        ovp_input = input("Enter OVP limit to set (V) or press Enter to skip: ").strip()
        if ovp_input:
            try:
                ovp = float(ovp_input)
                cli.set_ovp(ovp)
                logger.info(f"OVP set to {ovp:.2f} V")
            except Exception as e:
                logger.error(f"Error setting OVP: {e}")

    if cmd == "OCP":
        ocp_input = input("Enter OCP limit to set (A) or press Enter to skip: ").strip()
        if ocp_input:
            try:
                ocp = float(ocp_input)
                cli.set_ocp(ocp)
                logger.info(f"OCP set to {ocp:.2f} A")
            except Exception as e:
                logger.error(f"Error setting OCP: {e}")


def device_connection():
    client = GXE600Client(
        port='/dev/ttyLP3',  # Change this to your COM port
        slave_id=1,
        baudrate=19200,
        parity='N',
        timeout=0.5
    )

    logger.info("Attempting to auto-detect connection parameters...")
    params = client.connect_with_auto_detect(max_retries=3)
    
    if not params:
        logger.error("Failed to auto-detect connection parameters")
        logger.info("Trying with default parameters...")
        if not client.connect():
            logger.error("Connection failed with default parameters")
            return None
    
    logger.info("Connection successful!")
    logger.info("Model Name    : %s", client.get_model_name())
    logger.info("Serial Number : %s", client.get_serial_number())
    logger.info("Firmware Ver. : %s", client.get_firmware_version())

    # Configure communication mode
    try:
        client.set_cv_cc_reference_mode()
        client.set_remote_control_mode(RemoteControlMode.COMMUNICATION_VOLATILE)
        client.set_remote_on()
        logger.info("Output enabled. Monitoring started. Press Ctrl+C to stop.")
    except Exception as e:
        logger.error(f"Failed to configure device: {e}")
        logger.warning("Some features may not work correctly")

    return client


def main():
    global clients
    try:
        clients = device_connection()
        if not clients:
            logger.error("Could not establish connection. Exiting.")
            return
        
        mode = input("Enter mode: ").strip()
        pwm_mode_selection(mode, clients)
        
        while True:
            try:
                status = clients.get_status()
                logger.info(f"{status.output_voltage:.2f}V | {status.output_current:.2f}A | "
                            f"{status.internal_temperature}°C | {status.operation_time}s | "
                            f"OVP: {status.ovp:.2f}V | OCP: {status.ocp:.2f}A | "
                            f"Alarm: {status.alarm_history:04X}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error reading status: {e}")
                time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}. Retrying in 5 seconds...")
        time.sleep(5)
    finally:
        try:
            if clients:
                clients.set_remote_off()
                logger.info("Output disabled.")
        except:
            pass
        if clients:
            clients.disconnect()


if __name__ == '__main__':
    main()