from fastapi import HTTPException
from simulation.config_manager import *
from typing import Optional

def update_analog_output_params(channel_id: int, output_type: str, amplitude: str, frequency: Optional[str]):
    config, section_data, ch_str = get_channel_config("analog_output", channel_id)

    valid_options = section_data[ch_str].get("option", [])
    if output_type not in valid_options:
        raise HTTPException(status_code=400, detail=f"Invalid output_type '{output_type}'. Valid options: {valid_options}")

    section_data[ch_str]["output_type"] = output_type
    section_data[ch_str]["amplitude"] = amplitude
    section_data[ch_str]["frequency"] = None if output_type == "DC" else frequency

    save_config(config)
    return {f"channel{channel_id}": section_data[ch_str]}

def update_analog_output_status(channel_id: int, status: bool):
    config, section_data, ch_str = get_channel_config("analog_output", channel_id)
    section_data[ch_str]["status"] = status
    save_config(config)
    return {"channel": channel_id, "status": status}
