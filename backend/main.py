import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import JSONResponse
import json
from fastapi import FastAPI, Query, HTTPException, Path,Body
from typing import Dict, Any
from config import *
import logging
from model.ip_port import *
from common.ip_Port_config import *
from datetime import datetime
import socket
from model.bitrate import *
from model.power import *
import logging
from contextlib import asynccontextmanager
import threading
from fastapi import FastAPI, Query
import importlib.util
import os
import sys
from model.can_channel import *
from simulation.analog_manager import ensure_analog_input, ensure_analog_output
from simulation.board_info_manager import *
from model.analog_output import *
from crud.analog_setting import *
from model.digital_output import *
from crud.digital_setting import *
from device_handler_loader import *
from model.can_request import *
from helper.can import *

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INFO] Starting queue_handler threads...")
    device_handler.init()
    yield  # This marks the end of startup and the beginning of shutdown
    # Add cleanup code here if needed

app = FastAPI(lifespan=lifespan)

#==================================================================(SYSTEM)=============================================>
@app.get("/api/pulse/",tags=["SYSTEM"])
async def get_pulse():
    return JSONResponse(content={"status": "ok"}, status_code=200)

@app.post("/board/base/connect/", tags=["SYSTEM"])
async def connect_device(payload: ConnectRequest):
    logging.info("Received connection request:")
    logging.info(f"Current IP: {payload.data_processor_ip}")
    logging.info(f"Data Port: {payload.data_port}")
    logging.info(f"API Port: {payload.api_port}")

    received_at = datetime.utcnow().isoformat()
    
    # Update only the "connection" section in config.json
    update_config_field("connection", {
        "data_processor_ip": payload.data_processor_ip,
        "data_port": payload.data_port,
        "api_port": payload.api_port,
        "received_at": received_at
    })

    return {
        "message": "Device connected successfully",
        "received_at": received_at
    }

@app.get("/board/status/",tags=["SYSTEM"])
def get_board_info():
    file_path = "board_info.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            data = json.load(file)
        return JSONResponse(content=data)
    return JSONResponse(content={"error": "File not found"}, status_code=404)

#==================================================================(CAN)===============================================>

@app.p0ost("/can/set/tx/{message_id}/{modes}/{channel}/{can_delay}", tags=["CAN"])
def send_can_data(
    message_id: int = Path(..., description="Unique id  (e.g., 1, 2, 3, 4)"),
    modes: str = Path(..., description="modes  (e.g., add, modify, remove, start, stop)"),
    channel: str = Path(..., description="CAN channel (e.g., can1, can2, CAN1, CAN2)"),
    can_delay: float = Path(..., description="can_delay  (e.g., 0.01, 0.02, 0.03, 0.04)"),
    payload: CANRequest = ...
):
    logger.debug(f"message_id:{message_id},modes:{modes},channel:{channel},can_delay:{can_delay}")
    
    # Validate channel name using your existing function
    channel_upper = channel.upper()
    if not is_valid_can_channel(channel_upper):
        raise HTTPException(
            status_code=404,
            detail=f"Invalid CAN channel: {channel}"
        )
    # FIXED: Handle both comma-separated and space-separated formats
    try:
        data_list = []
        # Remove any extra spaces and check the format
        clean_data = payload.data.strip()
        
        # Check if it's comma-separated or space-separated
        if ',' in clean_data:
            # Comma-separated format: "FF,FF,FF,FF,FF"
            items = clean_data.split(',')
        else:
            # Space-separated format: "FF FF FF FF FF"
            items = clean_data.split()
        
        for item in items:
            item = item.strip()
            if not item:  # Skip empty items
                continue
                
            # Handle hex values (with or without 0x prefix)
            if item.startswith('0x'):
                # Format: "0xFF"
                data_list.append(int(item, 16))
            else:
                # Format: "FF" or "255" - try hex first, then decimal
                try:
                    # Try as hex (FF, AA, 11, etc.)
                    data_list.append(int(item, 16))
                except ValueError:
                    try:
                        # Try as decimal
                        data_list.append(int(item))
                    except ValueError as e:
                        raise ValueError(f"Invalid number format: {item}")
                        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid data format: {str(e)}")
   
    is_extended_frame = (payload.length > 8)
    max_length = payload.length
   
    if len(data_list) > max_length:
        raise HTTPException(
            status_code=400, 
            detail=f"Data length exceeds maximum allowed ({max_length} bytes)"
        )
   
    try:
        if payload.arbitration_id.lower().startswith('0x'):
            arbitration_id = int(payload.arbitration_id[2:], 16)
        else:
            arbitration_id = int(payload.arbitration_id, 16)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid arbitration ID format: {str(e)}")
   
    try:
        device_handler.can_send_data(
            msg_id=message_id,
            flag=modes,
            channel=channel_upper,
            data=data_list,
            arb_id=arbitration_id,
            ext_id=is_extended_frame,
            can_del=can_delay
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send CAN data: {str(e)}")
   
    return {
        "message": "CAN data sent successfully"
    }


@app.post("/can/set/bitrate/", tags=["CAN"])
def set_can_bitrate(request: BitrateRequest ):
    result = device_handler.can_set_config(request.bitrate, request.dbitrate)

    if result == "Invalid Bitrate":
        raise HTTPException(status_code=400, detail=result)

    # ✅ Store in JSON config file
    update_config_field("bitrate", request.bitrate)
    update_config_field("dbitrate", request.dbitrate)

    return {"message": "bitrate & dbitrate update requested"}

@app.post("/can/start/", tags=["CAN"])
def start_can(channel_id: str = Query(..., description="CAN channel to start (e.g., can1, can2)")):
    logger.info(f"[API] CAN start requested for channel: {channel_id}")
    try:
        # Validate channel name
        channel_upper = channel_id.upper()
        if not is_valid_can_channel(channel_upper):
            raise HTTPException(
                status_code=404,
                detail=f"Invalid CAN channel: {channel_id}"
            )
        messages = device_handler.can_start_stop_ch("START", channel_upper)
        logger.info(f"[API] CAN start response: {messages}")
        return {"message": messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] CAN start failed: {e}")
        return {"error": str(e)}


@app.post("/can/stop/", tags=["CAN"])
def stop_can(channel_id: str = Query(..., description="CAN channel to stop (e.g., can1, can2)")):
    logger.info(f"[API] CAN stop requested for channel: {channel_id}")
    try:
        # Validate channel name
        channel_upper = channel_id.upper()
        if not is_valid_can_channel(channel_upper):
            raise HTTPException(
                status_code=404,
                detail=f"Invalid CAN channel: {channel_id}"
            )
        messages = device_handler.can_start_stop_ch("STOP", channel_upper)
        logger.info(f"[API] CAN stop response: {messages}")
        return {"message": messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] CAN stop failed: {e}")
        return {"error": str(e)}


#==================================================================(ANALOG INPUT)=====================================>
@app.post("/ai/start/", tags=["ANALOG"])
def start_adc():
    device_handler.ain_start_config()
    return {"message": "ADC start command sent"}


@app.post("/ai/stop/", tags=["ANALOG"])
def stop_adc():
    device_handler.ain_stop_config()
    return {"message": "ADC stop command sent"}

#=================================================================(Digital Input)==========================================>
@app.post("/di/start/", tags=["DIGITAL"])
def start_digital_input():
    # device_handler.din_start_config()
    return {"message": "DIN start command sent"}

@app.post("/di/stop/", tags=["DIGITAL"])
def stop_digital_input():
    # device_handler.din_stop_config()
    return {"message": "DIN stop command sent"}


#=================================================(POWER SUPPLY)=============================
# ==== Set pps Config ====
@app.post("/pps/set/",tags=["POWER SUPPLY"])
def set_pps_config(request: PSSConfigRequest):
    try:
        device_handler.pps_set_config(request.cv, request.ocp, request.ovp)
        return {"message": "pps config set successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==== Get pps Config Output ====
@app.get("/pps/status/",tags=["POWER SUPPLY"])
def get_pps_config():
    try:
        data = device_handler.pps_get_config()
        if data is None:
            return {"message": "No new data", "data": None}
        return {"message": "pps config fetched", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#----------------(ANALOG Setting)----------------->

class AmplitudeRequest(BaseModel):
    amplitude: float = Field(..., description="Amplitude/Voltage value (can be negative, max +10V)")
 
@app.post("/ao/set/amplitude/{channel_key}", tags=["ANALOG"])
def set_analog_output_amplitude(
    channel_key: str = Path(..., description="Analog output channel key (e.g., 1 , 2 ...16 )"),
    amplitude_request: AmplitudeRequest = Body(..., description="Amplitude/Voltage configuration")
):
    """
    Set analog output amplitude/voltage on specified channel
    """
    try:
        amplitude = amplitude_request.amplitude
       
        # Extract channel number from channel_key (e.g., "ao1" -> 1, "channel2" -> 2)
        try:
            # Try to extract numeric part from the channel key
            channel_id = int(''.join(filter(str.isdigit, channel_key)))
            if channel_id <= 0:
                raise ValueError("Channel ID must be positive")
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid channel key format: {channel_key}. Expected format like '1', '2', etc."
            )
       
        # Validate voltage range - allow negative values but cap at +10V
        if amplitude > 10:
            raise HTTPException(
                status_code=400,
                detail=f"Amplitude must be less than or equal to 10V, got {amplitude}V"
            )
        # Call the device handler function
        result = device_handler.aout_set_config(amplitude, channel_id)
       
        return {
            "status": "success",
            "message": f"Analog output channel {channel_key} (ID: {channel_id}) set to {amplitude}V",
            "channel_key": channel_key,
            "channel_id": channel_id,
            "amplitude": amplitude,
            "data": result.hex() if hasattr(result, 'hex') else str(result)
        }
       
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set analog output amplitude on channel {channel_key}: {str(e)}"
        )

@app.post("/ao/start/channel/", tags=["ANALOG"])
def start_analog_output(channel_id: int = Query(..., description="Analog output channel to start (e.g., 1, 2, 3)")):
    """
    Enable analog output on specified channel
    """
    try:
        result = device_handler.aout_set_enable(channel_id)
        return {
            "status": "success",
            "message": f"Analog output channel {channel_id} started successfully",
            "data": result.hex() if hasattr(result, 'hex') else str(result)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to start analog output channel {channel_id}",
            "error": str(e)
        }
    
@app.post("/ao/stop/channel/", tags=["ANALOG"])
def stop_analog_output(channel_id: int = Query(..., description="Analog output channel to stop (e.g., 1, 2, 3)")):
    """
    Disable analog output on specified channel
    """
    try:
        result = device_handler.aout_set_disable(channel_id)
        return {
            "status": "success",
            "message": f"Analog output channel {channel_id} stopped successfully",
            "data": result.hex() if hasattr(result, 'hex') else str(result)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to stop analog output channel {channel_id}",
            "error": str(e)
        }
@app.post("/ao/start/",tags=["ANALOG"])
async def start_analog_output():
    """
    Endpoint to start analog output - returns 200 OK for testing
    """
    logging.info(" Received start analog output request")
    return {"status": "success", "message": "Analog output started"}

@app.post("/ao/stop/", tags=["ANALOG"])
def disable_all_analog_outputs():
    """
    Disable all analog output channels simultaneously.
    """
    try:
        # Call the device handler function
        result = device_handler.aout_all_disable()
        
        return {
            "status": "success",
            "message": "All analog output channels disabled successfully",
            "data": result.hex() if hasattr(result, 'hex') else str(result)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disable all analog outputs: {str(e)}"
        )

@app.get("/ai/config/", tags=["ANALOG"])
def get_analog_input():
    config = ensure_analog_input()
    names = get_ai_channel_names()
    for ch_id, name in names.items():
        if str(ch_id) in config:
            config[str(ch_id)]["name"] = name
    return config


@app.get("/ao/config/", tags=["ANALOG"])
def get_analog_output():
    config = ensure_analog_output()  # will now take 6 channels
    names = get_ao_channel_names()
    for ch_id, name in names.items():
        if str(ch_id) in config:
            config[str(ch_id)]["name"] = name
    return config

@app.post("/ao/set/config/{channel_id}", tags=["ANALOG"])
def set_analog_output_params(channel_id: int = Path(...), body: AnalogOutputBody = ...):
    return update_analog_output_params(
        channel_id=channel_id,
        output_type=body.output_type,
        amplitude=body.amplitude,
        frequency=body.frequency
    )

@app.post("/ao/update/status/{channel_id}", tags=["ANALOG"])
def set_analog_output_status(channel_id: int = Path(...), body: AnalogOutputStatusBody = ...):
    return update_analog_output_status(channel_id, body.status)


#-------------------------(Digital Setting)---------------->
@app.get("/di/config/", tags=["DIGITAL"])
def get_digital_input():
    channel_count = get_di_channel_count()
    config = ensure_digitalinput_config(channel_count)
    for ch_id in config:
        config[ch_id]["name"] = get_di_channels().get(int(ch_id), "Unknown")
    return config

@app.get("/do/config/", tags=["DIGITAL"])
def get_digital_output():
    channel_count = get_do_channel_count()
    config = ensure_digitaloutput_config(channel_count)
    for ch_id in config:
        config[ch_id]["name"] = get_do_channels().get(int(ch_id), "Unknown")
    return config

# POST endpoints
@app.post("/do/set/config/{channel_id}", tags=["DIGITAL"])
def set_digital_output_params(channel_id: int = Path(...), body: DigitalOutputBody = ...):
    updated = update_digital_output(channel_id, body.dict())
    return {f"channel{channel_id}": updated}

@app.post("/do/update/status/{channel_id}", tags=["DIGITAL"])
def set_digital_output_status(channel_id: int = Path(...), body: DigitalOutputStatusBody = ...):
    updated = update_digital_output_status(channel_id, body.status)
    return {f"channel{channel_id}": updated}

class DigitalOutputLevelBody(BaseModel):
    level: Literal["High", "Low"] = Field(..., description="Digital output level (High or Low)")

@app.post("/do/update/level/{channel_id}", tags=["DIGITAL"])
def set_digital_output_level(
    channel_id: int = Path(..., ge=1, le=16, description="Digital output channel ID (1-16)"), 
    body: DigitalOutputLevelBody = Body(..., description="Digital output level configuration")
):
    """
    Set the level (High/Low) for a digital output channel.
    """
    try:
        # Convert "High"/"Low" to 1/0
        level_value = 1 if body.level.lower() == "high" else 0
        
        # Call the device handler function
        result = device_handler.dout_start_config(channel=channel_id, pin_value=level_value)
        # result = device_handler.dout_start_config(channel_id, level_value)

        
        return {
            "status": "success",
            "message": f"Digital output channel {channel_id} set to {body.level}",
            "channel_id": channel_id,
            "level": body.level,  # Return the original string
            "level_value": level_value,  # Return the numeric value
            "data": result.hex() if hasattr(result, 'hex') else str(result)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set digital output level on channel {channel_id}: {str(e)}"
        )
    
@app.get("/debug/tcp_config", tags=["DEBUG"])
def debug_tcp_config():
    """Debug endpoint to check TCP configuration loading"""
    from simulation.tcp_sender import load_tcp_config, CONFIG_PATH
    import os
    
    ip, port = load_tcp_config()
    
    response = {
        "config_path": CONFIG_PATH,
        "config_exists": os.path.exists(CONFIG_PATH),
        "loaded_ip": ip,
        "loaded_port": port,
        "target_connection": f"{ip}:{port}"
    }
    
    # Read and show the actual config content
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config_data = json.load(f)
                response["connection_config"] = config_data.get("connection", {})
        except Exception as e:
            response["config_read_error"] = str(e)
    
    return response


# Add this to your main.py for debugging
@app.get("/debug/threads",tags=["DEBUG"])
def debug_threads():
    import threading
    active_threads = [t.name for t in threading.enumerate()]
    return {"active_threads": active_threads}




@app.get("/debug/config_test", tags=["DEBUG"])
def debug_config_test():
    """Test if config file is being read correctly"""
    from simulation.tcp_sender import CONFIG_PATH
    import os, json
    
    result = {
        "config_path": CONFIG_PATH,
        "file_exists": os.path.exists(CONFIG_PATH),
        "file_size": os.path.getsize(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else 0
    }
    
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                result["config_keys"] = list(config.keys())
                result["connection_section"] = config.get("connection", {})
        except Exception as e:
            result["error"] = str(e)
    
    return result

@app.post("/stop_all/",tags=["ALL"])
def stop_all():
    try:
        result = device_handler.deinit()        
        return result
    except Exception as e:
        raise e
        logger.error(f"[Error] Deinitialization failed: {e}")
                    

if __name__ == "__main__":
    # Configure logging
    # logging.basicConfig(
    #     level=logging.DEBUG,
    #     format="%(asctime)s [%(levelname)s] %(message)s"
    # )
    # logger = logging.getLogger(__name__)

    try:
        uvicorn.run(app, host="0.0.0.0", port=9030)
    except KeyboardInterrupt:
        logging.info("\n[INFO] Server stopped by user")
