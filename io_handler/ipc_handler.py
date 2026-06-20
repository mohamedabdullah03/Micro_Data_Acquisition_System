from multiprocessing import shared_memory
import time
import json
import struct
import logging

logger = logging.getLogger(__name__)

SHM_NAME = "my_shm"
SHM_SIZE = 4096

def ipc_write(json_str: str):
    """Write JSON string into shared memory with sequence number."""
    try:
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=False)
        logger.debug("Attached to existing shared memory.")
        
        current_seq_bytes = bytes(shm.buf[0:4])
        current_sequence = int.from_bytes(current_seq_bytes, byteorder='little')
        new_sequence = current_sequence + 1
        if new_sequence == 0:
            new_sequence = 1
    except FileNotFoundError:
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)
        logger.info("Created new shared memory segment.")
        new_sequence = 1

    sequence_bytes = new_sequence.to_bytes(4, byteorder='little')
    json_bytes = json_str.encode()

    total_size = len(sequence_bytes) + len(json_bytes) + 1 
    if total_size > SHM_SIZE:
        max_json_size = SHM_SIZE - len(sequence_bytes) - 1
        json_bytes = json_str.encode()[:max_json_size]
        logger.warning(f"Truncated JSON to {max_json_size} bytes (exceeded SHM_SIZE)")

    shm.buf[0:4] = sequence_bytes
    shm.buf[4:4+len(json_bytes)] = json_bytes
    shm.buf[4+len(json_bytes)] = 0  

    logger.info(f"Wrote sequence {new_sequence}: {json_str}")
    shm.close()

def ipc_read(clear_after=True) -> str:
    """Read JSON from shared memory, skip binary header, return only if contains CAN data."""
    shm = None
    try:
        shm = shared_memory.SharedMemory(name=SHM_NAME)
        raw_bytes = bytes(shm.buf[:SHM_SIZE])

        data_bytes = raw_bytes
        start = raw_bytes.find(b'{')
        if start > 0:
            data_bytes = raw_bytes[start:]

        null_pos = data_bytes.find(b'\x00')
        if null_pos == -1:
            null_pos = len(data_bytes)
        
        data = data_bytes[:null_pos].decode('utf-8', errors='ignore').strip()

        if any(k in data for k in ('"can_data"', '"can_playload"')):
            if clear_after:
                shm.buf[:SHM_SIZE] = b'\x00' * SHM_SIZE
            return data
        else:
            return ""

    except FileNotFoundError:
        return ""
    except Exception as e:
        return ""
    finally:
        if shm:
            shm.close()

def ipc_cleanup():
    shm = shared_memory.SharedMemory(name=SHM_NAME)
    shm.unlink()
    logger.info("Shared memory unlinked.")

# def main():
#     can_data = ["11", "22"]
#     can_data1 = ["11", "22", "33", "44"]

#     config_playload1 = {"config_playload": {"config": "CAN1"}}
#     config_playload2 = {"config_playload": {"config": "CAN2"}}

#     playload1 = {
#         "can_playload": {
#             "cid": "CAN1", "flag": "add", "msg_id": 3, "aid": 100,
#             "data": can_data, "ext_id": False, "can_delay": 0.002
#         }
#     }

#     playload2 = {
#         "can_playload": {
#             "cid": "CAN1", "flag": "start", "msg_id": 3, "aid": 100,
#             "data": can_data, "ext_id": False, "can_delay": 0.002
#         }
#     }

#     playload_can1 = {
#         "can_playload": {
#             "cid": "CAN2", "flag": "add", "msg_id": 9, "aid": 100,
#             "data": can_data1, "ext_id": False, "can_delay": 0.003
#         }
#     }

#     playload2_can1 = {
#         "can_playload": {
#             "cid": "CAN2", "flag": "start", "msg_id": 9, "aid": 100,
#             "data": can_data1, "ext_id": False, "can_delay": 0.003
#         }
#     }

#     time.sleep(1)
#     ipc_write(json.dumps(config_playload1))
#     time.sleep(0.5)
#     ipc_write(json.dumps(playload1))
#     time.sleep(0.5)
#     ipc_write(json.dumps(playload2))

#     time.sleep(10)
#     ipc_write(json.dumps(config_playload2))
#     time.sleep(0.5)
#     ipc_write(json.dumps(playload_can1))
#     time.sleep(0.5)
#     ipc_write(json.dumps(playload2_can1))

# if __name__ == "__main__":
#     main()
