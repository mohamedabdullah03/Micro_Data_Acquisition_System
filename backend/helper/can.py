def is_valid_can_channel(channel: str) -> bool:
    """
    Validate if the channel name is a valid CAN channel
    Accepts: CAN1, CAN2, can1, can2 (case-insensitive)
    """
    valid_channels = {"CAN1", "CAN2"}
    return channel.upper() in valid_channels
 