from pydantic import BaseModel

class BitrateRequest(BaseModel):
     bitrate: int
     dbitrate: int
