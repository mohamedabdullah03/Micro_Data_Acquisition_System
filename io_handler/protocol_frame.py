import struct

sof = 126
eof = 127

def create_frame(ch_type_id, t_id, s_id, control, ch_id, dl, data):
    ID = (ch_type_id << 6) | (t_id << 3) | s_id
    CH = (ch_id << 2) | control
    DL1 = dl & 0xFF         
    DL2 = (dl >> 8) & 0xFF 

    # Create frame with integer values (not hex strings)
    frame_bytes = [sof, ID, CH, DL1, DL2] + data + [eof]
    
    return frame_bytes

def main():
    voltage = 10
    channel = 10
    # Convert to integer for bitwise operations
    data = int((voltage / 10) * 65535)

    ch_type_id = 1
    t_id = 2   
    s_id = 1   
    control = 3  

    data_bytes = [
        0x00, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x00, 0x00,
        0x80, 0x80             
    ]

    byte1 = data & 0xFF 
    byte2 = (data >> 8) & 0xFF

    data_bytes[-2] = byte1
    data_bytes[-1] = byte2
    
    frame = create_frame(ch_type_id, t_id, s_id, control, channel, len(data_bytes), data_bytes)
    
    # Format the frame as hex values with 0x prefix
    formatted_frame = [hex(byte) for byte in frame]
    logger.DEBUG("Formatted frame:", formatted_frame)
    
    # Or if you want the actual integer values (this is what you see when you logger.DEBUG a list of hex literals)
    logger.DEBUG("Frame as integers:", frame)
    
    # To see it exactly like [0x7E, 0x21, 0x03, 0x01, 0x00, 0x00, 0x7F]
    # You can manually create the list with hex notation
    hex_frame = [f"0x{byte:02X}" for byte in frame]
    logger.DEBUG("Hex frame:", hex_frame)

if __name__ == "__main__":
    main()