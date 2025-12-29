#!/usr/bin/env python3
import hid
import argparse

# --- Constants ---
VENDOR_ID = 0x340E
PRODUCT_ID = 0x8002
INTERFACE_NUM = 1

# --- Command Mappings from C# Decompilation ---
# From BydCentral.Core.Models.TxBuf.COMMAND
# KeyBoard_Light (Main)   = 1 -> 0x01
# KeyBoard_Light12 (Z1/2) = 6 -> 0x06
# KeyBoard_Light34 (Z3/4) = 7 -> 0x07

# From BydCentral.Core.Models.TxBuf.PARAMS
# For Cmd 0x06 and 0x07:
# Always1 = 0  (Used for Zone 1 and Zone 3)
# Always2 = 4  (Used for Zone 2 and Zone 4)
# Note: User found 0x01 works for Z1. C# says 0x00. 
# We will use 0x00 as per source code, but keep 0x01 as fallback if 0x00 turns it off.

def get_device_path():
    """
    Locates the specific HID interface path for Interface 1.
    """
    devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    for d in devices:
        if d['interface_number'] == INTERFACE_NUM:
            return d['path']
    return None

def create_packet(cmd_byte, mode_byte, r, g, b, brightness=200):
    """
    Constructs the 65-byte packet based on TxBuf structure.
    Byte 0: Report ID (0x06 usually, or set by ID field)
    Byte 1: (Command << 4) | Mode/Param
    Byte 2: Data Size (0x04)
    Byte 7-10: R, G, B, L
    Byte 63: Checksum
    """
    packet = [0] * 65
    packet[0] = 0x06  # Report ID / Internal ID
    
    # Construct Byte 1: High nibble is CMD, Low nibble is MODE
    # Based on C# bit manipulation logic in TxBuf.cs
    packet[1] = ((cmd_byte & 0xF) << 4) | (mode_byte & 0xF)
    
    packet[2] = 0x04   # Data length (R,G,B,L)
    
    # Color Payload (Offset 7 based on unionData offset)
    packet[7] = r
    packet[8] = g
    packet[9] = b
    packet[10] = brightness

    # Checksum: Sum of bytes 1 to 62, masked to 8 bits
    checksum = sum(packet[1:63])
    packet[63] = checksum & 0xFF
    return packet

def set_zone_color(zone, r, g, b, brightness):
    path = get_device_path()
    if path is None:
        print(f"[-] Device {hex(VENDOR_ID)}:{hex(PRODUCT_ID)} (Interface {INTERFACE_NUM}) not found.")
        print("    Ensure you are using 'sudo' or have proper udev rules.")
        return False

    # Logic derived from BydContral.Page2.cs mapping
    cmd = 0x00
    mode = 0x00

    if zone == 0: # Main / All
        cmd = 0x01 # KeyBoard_Light
        mode = 0x01 # Always On (Enum value 1)
    elif zone == 1:
        cmd = 0x06 # KeyBoard_Light12
        mode = 0x00 # Always1 (Enum value 0)
    elif zone == 2:
        cmd = 0x06 # KeyBoard_Light12
        mode = 0x04 # Always2 (Enum value 4)
    elif zone == 3:
        cmd = 0x07 # KeyBoard_Light34
        mode = 0x00 # Always1 (Enum value 0)
    elif zone == 4:
        cmd = 0x07 # KeyBoard_Light34
        mode = 0x04 # Always2 (Enum value 4)
    else:
        print("[-] Invalid Zone. Use 0-4.")
        return False

    print(f"[*] Preparing Packet: Cmd={hex(cmd)}, Mode={hex(mode)}, Zone={zone}")
    packet = create_packet(cmd, mode, r, g, b, brightness)
    
    try:
        h = hid.device()
        h.open_path(path)
        h.write(packet)
        h.close()
        print(f"[+] Zone {zone} set to RGB({r}, {g}, {b})")
        return True
    except Exception as e:
        print(f"[!] Error writing to HID device: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Infinix GT Book - RGB Controller")
    parser.add_argument("--zone", type=int, default=0, help="Zone ID: 0=Main, 1=Left, 2=Mid-Left, 3=Mid-Right, 4=Right")
    parser.add_argument("--r", type=int, default=0, help="Red (0-255)")
    parser.add_argument("--g", type=int, default=255, help="Green (0-255)")
    parser.add_argument("--b", type=int, default=0, help="Blue (0-255)")
    parser.add_argument("--bri", type=int, default=200, help="Brightness (0-255)")
    
    args = parser.parse_args()
    
    set_zone_color(args.zone, args.r, args.g, args.b, args.bri)