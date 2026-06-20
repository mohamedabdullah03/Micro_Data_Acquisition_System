import time
import can

interface = 'socketcan'
channel = 'can1'

def producer(id):
    
    bus = can.Bus(channel=channel, interface=interface, fd=True) 

    for i in range(10):
        data = [id, i, 0, 1, 3, 1, 4, 1, 5, 9, 7, 6, 5, 4, 3, 2, 1 ,2, 2, 3, 9, 7, 6, 5, 4, 3, 2]  
        msg = can.Message(
            arbitration_id=0x123,
            data=data,
            is_fd=True,              
            bitrate_switch=True,      
            is_extended_id=False
        )
        try:
            bus.send(msg)
            print(f"Sent FD frame {i+1}: {msg}")
        except can.CanError as e:
            print(f"Error sending CAN FD frame: {e}")

        time.sleep(0.1)

    bus.shutdown()

if __name__ == "__main__":
    producer(10)