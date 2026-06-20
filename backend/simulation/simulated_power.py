import time
import threading
import random



class PowerState:
    def __init__(self):
        self.voltage = 0.0
        self.current = 0.0
        self.temperature = 27.0
        self.target_voltage = 0.0
        self.target_current = 0.0
        self.ovp = 0.0
        self.ocp = 0.0
        self.start_time = time.time()
        self.lock = threading.Lock()

    def update(self, cv: float, ocp: float, ovp: float):
        with self.lock:
            self.target_voltage = round(cv, 2)
            self.target_current = 1599.98  # fixed like your sim
            self.ovp = round(ovp, 2)
            self.ocp = round(ocp, 2)

    def step_simulation(self):
        with self.lock:
            # Adjust voltage gradually toward target
            delta_v = round(self.target_voltage - self.voltage, 2)
            if abs(delta_v) > 0.05:
                step = 0.1 if delta_v > 0 else -0.1
                self.voltage = round(self.voltage + step, 2)
            else:
                self.voltage = self.target_voltage

            # Simulate current draw
            if self.voltage > 0:
                self.current = random.choice([0.00, self.target_current])
            else:
                self.current = 0.00

            # Keep temperature stable
            self.temperature = 27.0

    def get_status(self):
        uptime = int(time.time() - self.start_time)
        formatted_status = (
            f"{round(self.voltage, 2)}V | "
            f"{round(self.current, 2)}A | "
            f"{self.temperature}°C | "
            f"{uptime}s | "
            f"OVP: {round(self.ovp, 2)}V | "
            f"OCP: {round(self.ocp, 2)}A | "
            f"Alarm: 0000"
        )
        return {
           
            "data": [formatted_status]
        }


power_state = PowerState()

def power_sim_loop():
    while True:
        power_state.step_simulation()
        time.sleep(2)

# Start simulator thread when device_handler loads
threading.Thread(target=power_sim_loop, daemon=True).start()
