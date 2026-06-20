import os
import time
import json

FIFO_PATH = "/tmp/can_fifo"

def fifo_write(message: str):
    """Write message to FIFO."""
    if not os.path.exists(FIFO_PATH):
        os.mkfifo(FIFO_PATH)

    try:
        with open(FIFO_PATH, "w") as fifo:
            fifo.write(message + "\n")
            fifo.flush()
            return True
    except Exception as e:
        logger.error(f"[PYTHON] Write error: {e}")
        return False


if __name__ == "__main__":
    count = 0
    while True:
        msg = {"can_data": {"cid": str(count % 255), "data": "D0"}}
        fifo_write(json.dumps(msg))
        count += 1
        time.sleep(0.0001)  # 2 ms interval
