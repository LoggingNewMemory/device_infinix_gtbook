#!/usr/bin/env python3
import hid
import os
import sys
import time

# --- Constants ---
VENDOR_ID = 0x340E
PRODUCT_ID = 0x8002
INTERFACE_NUM = 1

# --- Dictionaries ---
MODES = {
    0: "Off",
    1: "Static Color",
    2: "Breathing",
    3: "Neon Cycle",
    4: "Rainbow",
    5: "Flow",
    6: "Wave",
}

# Mapping: Zone ID -> (Command Nibble, Offset Nibble)
# derived from decompiled C# sources in 'Keyboard Zone Key.py'
ZONE_MAPPING = {
    0: (0x01, 0x00), # All / Global
    1: (0x06, 0x00), # Left (Zone 1)
    2: (0x06, 0x04), # Mid-Left (Zone 2) - Offset 4
    3: (0x07, 0x00), # Mid-Right (Zone 3)
    4: (0x07, 0x04)  # Right (Zone 4) - Offset 4
}

ZONES = {
    0: "All / Global",
    1: "Left (Zone 1)",
    2: "Mid-Left (Zone 2)",
    3: "Mid-Right (Zone 3)",
    4: "Right (Zone 4)"
}

COLORS = {
    "Red": (255, 0, 0),
    "Green": (0, 255, 0),
    "Blue": (0, 0, 255),
    "Cyan": (0, 255, 255),
    "Magenta": (255, 0, 255),
    "Yellow": (255, 255, 0),
    "White": (255, 255, 255),
    "Infinix Orange": (255, 100, 0)
}

# --- State Management ---
current_settings = {
    "zone": 0,       # 0=All, 1-4=Specific
    "mode": 1,       # Effect Mode
    "color": (0, 255, 0),
    "brightness": 100
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_device_path():
    devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    for d in devices:
        if d['interface_number'] == INTERFACE_NUM:
            return d['path']
    return None

def create_packet(zone_id, mode, r, g, b, brightness):
    packet = [0] * 65
    packet[0] = 0x06  # Report ID
    packet[2] = 0x04  # Data Size
    
    # Payload
    packet[7] = r
    packet[8] = g
    packet[9] = b
    packet[10] = brightness

    # Get Command and Offset from Mapping
    # Default to Global if unknown
    cmd_nibble, offset_nibble = ZONE_MAPPING.get(zone_id, (0x01, 0x00))

    # --- Byte 1 Calculation ---
    # Logic: (Command << 4) | (Offset | Mode)
    # The Offset (0 or 4) likely acts as a sub-zone selector bit.
    # The Mode (0-6) is the effect.
    # We combine them using bitwise OR.
    
    combined_mode = (offset_nibble | mode)
    packet[1] = ((cmd_nibble & 0xF) << 4) | (combined_mode & 0xF)

    # Checksum: Sum of bytes 1 to 62, masked to 8 bits
    packet[63] = sum(packet[1:63]) & 0xFF
    return packet

def apply_settings():
    path = get_device_path()
    if not path:
        print("\n[!] Device not found. Check USB connection or Permissions.")
        input("Press Enter to continue...")
        return

    try:
        h = hid.device()
        h.open_path(path)
        
        z = current_settings["zone"]
        m = current_settings["mode"]
        r, g, b = current_settings["color"]
        bri = current_settings["brightness"]
        
        # Construct and send
        packet = create_packet(z, m, r, g, b, bri)
        h.write(packet)
        h.close()
        
        z_name = ZONES.get(z, "Unknown")
        m_name = MODES.get(m, "Unknown")
            
        print(f"\n[+] Applied to {z_name}: {m_name} | Bri: {bri}%")
        # Debug info for the curious user
        cmd, off = ZONE_MAPPING.get(z, (0,0))
        byte1_debug = ((cmd & 0xF) << 4) | ((off | m) & 0xF)
        print(f"    (Debug: Sent Byte[1] = {hex(byte1_debug)})")
        
    except Exception as e:
        print(f"\n[!] Error sending command: {e}")
        input("Press Enter to continue...")

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def menu_color():
    print("\n--- Select Color ---")
    color_keys = list(COLORS.keys())
    for i, name in enumerate(color_keys):
        print(f"{i+1}. {name}")
    print("99. Custom Hex Code")
    
    try:
        choice = int(input("\nSelection: "))
        if choice == 99:
            hex_code = input("Enter Hex (e.g. FF00FF): ")
            current_settings["color"] = hex_to_rgb(hex_code)
        elif 1 <= choice <= len(color_keys):
            current_settings["color"] = COLORS[color_keys[choice-1]]
            
        apply_settings()
    except ValueError:
        pass

def menu_mode():
    print("\n--- Select Effect Mode ---")
    for k, v in MODES.items():
        print(f"{k}. {v}")
    
    try:
        choice = int(input("\nSelection: "))
        if choice in MODES:
            current_settings["mode"] = choice
            apply_settings()
    except ValueError:
        pass

def menu_zone():
    print("\n--- Select Keyboard Zone ---")
    for k, v in ZONES.items():
        print(f"{k}. {v}")
    
    try:
        choice = int(input("\nSelection: "))
        if choice in ZONES:
            current_settings["zone"] = choice
            apply_settings()
    except ValueError:
        pass

def menu_brightness():
    try:
        val = int(input("\nEnter Brightness (0-100): "))
        if 0 <= val <= 100:
            current_settings["brightness"] = val
            apply_settings()
    except ValueError:
        pass

def main():
    while True:
        clear_screen()
        
        # Status Line
        z_str = ZONES[current_settings['zone']]
        m_str = MODES[current_settings['mode']]
            
        print("╔══════════════════════════════════════╗")
        print("║   INFINIX GT BOOK KEYBOARD CONTROL   ║")
        print("╚══════════════════════════════════════╝")
        print(f" Zone: {z_str}")
        print(f" Mode: {m_str}")
        print(f" Brightness: {current_settings['brightness']}%")
        print("----------------------------------------")
        print("1. Change Color")
        print("2. Change Effect Mode (All Zones)")
        print("3. Set Brightness")
        print("4. Select Zone")
        print("5. Turn OFF")
        print("0. Exit")
        print("----------------------------------------")
        
        choice = input("Option: ")
        
        if choice == '1':
            menu_color()
        elif choice == '2':
            menu_mode()
        elif choice == '3':
            menu_brightness()
        elif choice == '4':
            menu_zone()
        elif choice == '5':
            current_settings["mode"] = 0
            apply_settings()
        elif choice == '0':
            sys.exit()
            
        if choice in ['1', '2', '3', '4', '5']:
            time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye!")