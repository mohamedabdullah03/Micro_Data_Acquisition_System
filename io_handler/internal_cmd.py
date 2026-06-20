import glob
import subprocess


def read_cpu_temperature():
    for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            with open(f"{hwmon}/name") as f:
                name = f.read().strip()

            if name in ("cpu0_thermal", "cpu1_thermal"):
                with open(f"{hwmon}/temp1_input") as f:
                    temp = int(f.read().strip())
                return temp / 1000.0

        except Exception:
            continue

    raise RuntimeError("CPU thermal sensor not found")


def reboot():
    try:
        subprocess.run(["systemctl", "reboot"], check=True)
    except Exception as e:
        raise Exception(f"error:{e}")

def shutdown():
    try:
        subprocess.run(["systemctl", "poweroff"], check=True)
    except Exception as e:
        raise Exception(f"error:{e}")
