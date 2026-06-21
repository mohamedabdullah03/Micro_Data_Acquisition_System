Micro Data Acquisition System (Micro DAQ)
Overview
The Micro Data Acquisition System (Micro DAQ) is an Industrial IoT (IIoT) gateway and data acquisition platform designed to collect, monitor, configure, and transfer data from multiple industrial interfaces.

The system provides a graphical user interface (GUI) for configuring communication protocols, managing I/O channels, and monitoring gateway status in real time.

Features
Multi-protocol communication support
Modbus RTU / TCP
MQTT
RS485
CAN Bus
UART
I/O Configuration
Digital Inputs (DI)
Digital Outputs (DO)
Analog Inputs (AI)
Analog Outputs (AO)
Gateway Management
Device configuration
Network settings
Diagnostics and health monitoring
Firmware update support
User-friendly GUI
JSON-based configuration
Real-time monitoring and logging
Architecture
GUI (PyQt)
    |
    ├── Configuration Manager
    ├── Communication Manager
    │      ├── MQTT
    │      ├── Modbus RTU/TCP
    │      ├── CAN Bus
    │      └── Serial Communication
    |
    ├── JSON Configuration Files
    |
    └── Industrial Gateway Hardware
            ├── Sensors
            ├── PLC
            ├── Actuators
            └── Edge Devices
Technology Stack
Category Technologies

Language Python GUI PyQt Communication MQTT, Modbus RTU/TCP, CAN, UART Data Format JSON Industrial Protocols RS485, Modbus Version Control Git, GitHub

Project Structure
project/
│
├── main.py
├── functions.py
├── modbus_panel.py
├── mqtt_panel.py
├── config/
│   └── *.json
├── assets/
├── logs/
└── README.md
Workflow
Start the application.
Load gateway configuration from JSON.
Configure communication protocols.
Connect to the gateway device.
Acquire sensor and industrial device data.
Publish or store collected data.
Monitor diagnostics and logs.
Future Enhancements
AI-based anomaly detection
Predictive maintenance
Edge AI integration
Dashboard analytics
Cloud connectivity
OTA firmware updates
Author
Mohamed Abdullah S
Embedded & AI Engineer
Electrical and Electronics Engineering (2025)
Industrial IoT | STM32 | Python | MQTT | Modbus | Edge AI

If you find this project useful, consider giving it a ⭐ on GitHub.
