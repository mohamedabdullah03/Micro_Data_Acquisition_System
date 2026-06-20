from pydantic import BaseModel, Field, validator,field_validator
from typing import Union
import re

class CANRequest(BaseModel):
    arbitration_id: str = Field(..., description="CAN arbitration ID (e.g., '0xC0FFEE', '10E', '11A')")
    length: int = Field(..., description="Message length: 8 for standard frame, 64 for extended frame")
    data: str = Field(..., description="Comma-separated data bytes (e.g., '1,2,3,4,5,6,7,8')")
    
    @validator('arbitration_id')
    def validate_arbitration_id(cls, v):
        # Remove any whitespace and convert to uppercase
        v = v.strip().upper()
        
        # Remove 0x prefix if present for validation
        clean_v = v.replace('0X', '') if v.startswith('0X') else v
        
        # Validate hex format
        if not re.match(r'^[0-9A-F]+$', clean_v):
            raise ValueError('Arbitration ID must be a valid hexadecimal value')
        
        return v
    
    @field_validator('length')
    @classmethod
    def validate_length(cls, v):
        # Allow any positive integer, but warn about CAN standards
        if v <= 0:
            raise ValueError('Length must be a positive integer')
        # if v not in [8, 64]:
        #     # Just a warning, not an error - allows flexibility
        #     print(f"Warning: Non-standard CAN length: {v}. Standard lengths are 8 or 64 bytes.")
        return v