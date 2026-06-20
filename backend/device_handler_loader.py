import os
import platform
import importlib.util
import sys


print("Operating System Name:", platform.system())

# Determine which device_handler to use
if platform.system() == "Windows":
    module_path = os.path.join(os.path.dirname(__file__), "simulation", "device_handler.py")
else:
    module_path = "/root/udaq/io_handler/device_handler.py"

module_dir = os.path.dirname(module_path)
if module_dir not in sys.path:
    sys.path.append(module_dir)

spec = importlib.util.spec_from_file_location("device_handler", module_path)
device_handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(device_handler)
