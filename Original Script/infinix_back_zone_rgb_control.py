#!/usr/bin/env python3
import hid
import sys

# --- Hardware Constants ---
VENDOR_ID = 0x340E   # Infinix / ITE
PRODUCT_ID = 0x8002  # GT Book Controller
INTERFACE_NUM = 1    # Shared Interface

def get_device_path():
    """Finds the correct HID interface."""
    for d in hid.enumerate(VENDOR_ID, PRODUCT_ID):
        if d['interface_number'] == INTERFACE_NUM:
            return d['path']
    return None

def calculate_checksum(data):
    # Sum of bytes at index 1 to 62 (indices 1 up to 63 in Python slice)
    total = sum(data[1:63])
    return total & 0xFF

def create_packet(mode_byte):
    # Packet structure: 65 bytes for HIDAPI (First byte is Report ID 0)
    # The actual payload starts at index 1
    packet = [0] * 65
    
    # Report ID (Usually 0 for raw HID writes, or specific ID)
    # Based on your previous script, the first data byte is 0x06.
    # In hidapi, packet[0] is often the Report ID. 
    # If the device expects the first byte of transmission to be 0x06:
    packet[0] = 0x06 
    
    # Byte 1: Command + Mode
    # Office (0)  -> 0x40 
    # Balance (1) -> 0x41 
    # Gaming (2)  -> 0x42 
    packet[1] = 0x40 + mode_byte
    
    # Byte 63: Checksum
    # Note: checksum calculation is based on packet[1:63]
    packet[63] = calculate_checksum(packet)
    
    return packet

def send_command(mode_name):
    modes = {
        "office": 0,
        "balance": 1,
        "gaming": 2
    }
    
    if mode_name not in modes:
        print(f"Invalid mode. Available modes: {list(modes.keys())}")
        return

    print(f"Setting mode to: {mode_name}...")
    
    path = get_device_path()
    if not path:
        print("[!] Device not found. Ensure it is plugged in.")
        return

    try:
        h = hid.device()
        h.open_path(path)
        
        packet = create_packet(modes[mode_name])
        
        # Send the packet
        h.write(packet)
        h.close()
        print("Command sent successfully.")
        
    except Exception as e:
        print(f"Error sending command: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 infinix_back_zone_rgb_control.py [office|balance|gaming]")
    else:
        send_command(sys.argv[1].lower())