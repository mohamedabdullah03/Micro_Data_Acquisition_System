from pydantic import BaseModel
from typing import Optional, Literal

class DigitalOutputBody(BaseModel):
    output_type: Literal["Level", "Waveform"]
    level: Optional[Literal["High", "Low"]] = None
    frequency: Optional[str] = None
    duty_cycle: Optional[str] = None

class DigitalOutputStatusBody(BaseModel):
    status: bool
# class DigitalOutputLevelBody(BaseModel):
#     level: Literal["High", "Low"]