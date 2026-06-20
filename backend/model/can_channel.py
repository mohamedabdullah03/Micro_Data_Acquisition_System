from pydantic import BaseModel

# --- Dummy handler for illustration ---
class ChannelRequest(BaseModel):
    channel_id: str

# class DeviceHandler:
#     def can_start_ch(self, ch_id):
#         print(f"CAN Start called for {ch_id}")

#     def can_stop_ch(self, ch_id):
#         print(f"CAN Stop called for {ch_id}")

# device_handler = DeviceHandler()