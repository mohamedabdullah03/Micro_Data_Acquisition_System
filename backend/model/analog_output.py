from pydantic import BaseModel
from typing import Optional

class AnalogOutputBody(BaseModel):
    output_type: str
    amplitude: str
    frequency: Optional[str] = None

class AnalogOutputStatusBody(BaseModel):
    status: bool
