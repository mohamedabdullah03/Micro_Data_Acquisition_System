from pydantic import BaseModel

class ConnectRequest(BaseModel):
    data_processor_ip: str
    data_port: str
    api_port: str
 