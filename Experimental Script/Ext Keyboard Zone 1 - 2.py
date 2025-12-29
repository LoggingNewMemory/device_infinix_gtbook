# This is an accidential found where I found the diff zone of keyboard

#!/usr/bin/env python3
import hid
import sys
import argparse

# --- Constants ---
VENDOR_ID = 0x340E
PRODUCT_ID = 0x8002
INTERFACE_NUM = 1

# Command 6 matches 'KeyBoard_Light12' in the C# source
CMD_ZONE_1_2 = 0x06 

def get_device_path():
    """
    Locates the specific HID interface path for Interface 1.
    """
    # Enumerate all devices with matching VID/PID
    devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    for d in devices:
        if d['interface_number'] == INTERFACE_NUM:
            return d['path']
    return None

def create_packet(cmd_id, r, g, b):
    """
    Constructs the 65-byte packet.
    Byte 0: Report ID (0x06)
    Byte 1: (Command << 4) | Mode. Mode 1 is 'Always' (Static).
    Byte 2: Data Size (4 bytes for R,G,B,L)
    Byte 7-10: R, G, B, Brightness
    Byte 63: Checksum
    """
    packet = [0] * 65
    packet[0] = 0x06
    
    # 0x06 (Command) << 4 | 0x01 (Mode: Always) = 0x61
    packet[1] = ((cmd_id & 0xF) << 4) | 0x01 
    
    packet[2] = 0x04   # Data length
    
    # Color Payload
    packet[7] = r
    packet[8] = g
    packet[9] = b
    packet[10] = 200   # Brightness (Fixed at 200/255)

    # Checksum: Sum of bytes 1 to 62 masked to 8 bits
    checksum = sum(packet[1:63])
    packet[63] = checksum & 0xFF
    return packet

def set_zone_color(r, g, b):
    path = get_device_path()
    if path is None:
        print(f"[-] Device {hex(VENDOR_ID)}:{hex(PRODUCT_ID)} (Interface {INTERFACE_NUM}) not found.")
        print("    Ensure you are using 'sudo' or have proper udev rules.")
        return False

    packet = create_packet(CMD_ZONE_1_2, r, g, b)
    
    try:
        # Open the device using the specific path found
        h = hid.device()
        h.open_path(path)
        
        # Write the packet
        # Note: 'packet' is a list of integers. hidapi expects bytes or list of ints.
        h.write(packet)
        h.close()
        print(f"[+] Zone 1-2 set to RGB({r}, {g}, {b})")
        return True
    except Exception as e:
        print(f"[!] Error writing to HID device: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Infinix GT Book - Zone 1-2 Controller")
    parser.add_argument("--r", type=int, default=0, help="Red (0-255)")
    parser.add_argument("--g", type=int, default=255, help="Green (0-255) - Default")
    parser.add_argument("--b", type=int, default=0, help="Blue (0-255)")
    
    args = parser.parse_args()
    
    set_zone_color(args.r, args.g, args.b)