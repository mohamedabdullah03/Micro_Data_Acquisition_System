import subprocess
import sys
import logging

logger = logging.getLogger(__name__)

# --- User Config ---
target_ip = "192.168.1.161"
netmask   = "255.255.255.0"
interface = "end0"   # change if needed (e.g., enp1s0, wlan0)

# --- Convert netmask to CIDR ---
def netmask_to_cidr(netmask):
    return sum(bin(int(x)).count("1") for x in netmask.split("."))

cidr = netmask_to_cidr(netmask)
ip_cidr = f"{target_ip}/{cidr}"



def ip_config_set():
    try:
        # Remove old IPs on interface
        subprocess.run(["ip", "addr", "flush", "dev", interface], check=True)

        # Assign new IP
        subprocess.run(["ip", "addr", "add", ip_cidr, "dev", interface], check=True)

        # Bring interface up
        subprocess.run(["ip", "link", "set", interface, "up"], check=True)

        logger.info(f"[INFO] Successfully set {ip_cidr} on {interface}")

    except subprocess.CalledProcessError as e:
        logger.ERROR(f"[ERROR] Failed: {e}")
        # sys.exit(1)

if __name__ == "__main__":
    ip_config_set()
