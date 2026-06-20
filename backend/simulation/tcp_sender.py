import json, socket, logging, threading, os
import platform


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

_connections = {}
_lock = threading.Lock()


if platform.system() == "Windows":
    CONFIG_PATH = os.path.join(os.getcwd(), "config.json")
else:
    CONFIG_PATH = "/root/udaq/config/config.json"


def load_tcp_config():
    """Load IP and port from JSON config file"""
    try:
        logging.info(f"[TCP CONFIG] Loading config from: {CONFIG_PATH}")
        
        if not os.path.exists(CONFIG_PATH):
            logging.error(f"[TCP CONFIG] Config file not found: {CONFIG_PATH}")
            return "127.0.0.1", 6000
        
        with open(CONFIG_PATH, 'r') as f:
            data = json.load(f)
            
        
            
            # Get the connection section - this is the correct way!
            connection_config = data.get("connection", {})
            
            # Extract IP and port from connection section
            ip = connection_config.get("data_processor_ip", "127.0.0.1")
            port = connection_config.get("data_port", 6000)
            
            # Convert port to integer
            try:
                port = int(port)
            except (ValueError, TypeError):
                logging.error(f"[TCP CONFIG] Invalid port value: {port}, using default 6000")
                port = 6000
            
            logging.info(f"[TCP CONFIG] Loaded: {ip}:{port}")
            return ip, port
            
    except Exception as e:
        logging.error(f"[TCP CONFIG] Failed to load {CONFIG_PATH}: {e}")
        return "127.0.0.1", 6000

def send_tcp_message(raw_data):
    global _connections, _lock

    try:
        if isinstance(raw_data, str):
            raw_data = (raw_data + "\n").encode()
        elif not isinstance(raw_data, (bytes, bytearray)):
            logging.error(f"[TCP] Invalid data type: {type(raw_data)}")
            return

        ip, tcp_port = load_tcp_config()
        key = f"{ip}:{tcp_port}"

        with _lock:
            if key not in _connections:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    s.connect((ip, tcp_port))
                    _connections[key] = s
                    logging.info(f"[TCP] Connected to {ip}:{tcp_port}")
                except Exception as e:
                    logging.error(f"[TCP] Connection failed to {ip}:{tcp_port} - {e}")
                    return

            try:
                _connections[key].sendall(raw_data)
                logging.info(f"[TCP SEND] {raw_data.decode().strip()}") 
                logging.debug(f"[TCP] Sent {len(raw_data)} bytes to {ip}:{tcp_port}")
            except Exception as e:
                logging.error(f"[TCP] Send failed: {e}")
                try:
                    _connections[key].close()
                except:
                    pass
                del _connections[key]

    except Exception as e:
        logging.error(f"[TCP SEND ERROR] {e}")