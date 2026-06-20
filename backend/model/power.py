from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from threading import Lock


class PSSConfigRequest(BaseModel):
    cv: float
    ocp: float
    ovp: float