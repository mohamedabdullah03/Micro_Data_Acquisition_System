from fastapi import HTTPException
from simulation.config_manager import *
from typing import Optional



# Update functions
def update_digital_output(channel_id: int, body: dict):
    config = load_config()
    section = config.get("digital_output", {})
    ch_str = str(channel_id)

    if ch_str not in section:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found")

    output_type = body["output_type"]
    if output_type not in section[ch_str]["option"]:
        raise HTTPException(status_code=400, detail=f"Invalid output_type '{output_type}'")

    section[ch_str]["output_type"] = output_type
    if output_type == "Level":
        section[ch_str]["level"] = body["level"]
        section[ch_str]["frequency"] = None
        section[ch_str]["duty_cycle"] = None
    elif output_type == "Waveform":
        section[ch_str]["level"] = None
        section[ch_str]["frequency"] = body["frequency"]
        section[ch_str]["duty_cycle"] = body["duty_cycle"]

    config["digital_output"] = section
    save_config(config)
    return section[ch_str]

def update_digital_output_status(channel_id: int, status: bool):
    config = load_config()
    section = config.get("digital_output", {})
    ch_str = str(channel_id)

    if ch_str not in section:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found")

    section[ch_str]["status"] = status
    config["digital_output"] = section
    save_config(config)
    return section[ch_str]

def update_digital_output_level(channel_id: int, level: str):
    logger.debug(f"Updating channel {channel_id} to level: {level}")
    
    config = load_config()
    section = config.get("digital_output", {})
    ch_str = str(channel_id)

    if ch_str not in section:
        logger.error(f"Channel {channel_id} not found in config")
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found")
    
    logger.debug(f"Current channel config: {section[ch_str]}")
    
    # Update the level
    section[ch_str]["level"] = level
    config["digital_output"] = section
    
    logger.debug(f"Updated config: {config['digital_output'][ch_str]}")
    
    save_config(config)
    
    # Verify the change was saved
    saved_config = load_config()
    saved_level = saved_config.get("digital_output", {}).get(ch_str, {}).get("level")
    logger.debug(f"Verified saved level: {saved_level}")
    
    return section[ch_str]
