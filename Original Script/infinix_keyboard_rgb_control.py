#!/usr/bin/env python3
import hid
import os
import sys

VENDOR_ID = 0x340E
PRODUCT_ID = 0x8002
INTERFACE_NUM = 1

MODES = {
    0: "Off",
    1: "Static Color",
    2: "Breathing",
    3: "Neon Cycle",
    4: "Rainbow",
    5: "Flow",
    6: "Wave",
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

current_settings = {
    "mode": 1,
    "color": (0, 255, 0),
    "brightness": 100
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_device_path():
    for d in hid.enumerate(VENDOR_ID, PRODUCT_ID):
        if d['interface_number'] == INTERFACE_NUM:
            return d['path']
    return None

def create_packet(mode, r, g, b, brightness):
    packet = [0] * 65
    packet[0] = 0x06
    packet[1] = 0x10 | mode
    packet[2] = 0x04
    packet[7] = r
    packet[8] = g
    packet[9] = b
    packet[10] = brightness
    
    checksum = sum(packet[1:63])
    packet[63] = checksum & 0xFF
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
        
        mode = current_settings["mode"]
        r, g, b = current_settings["color"]
        bright = current_settings["brightness"]
        
        packet = create_packet(mode, r, g, b, bright)
        h.write(packet)
        h.close()
        print(f"\n[+] Applied: {MODES.get(mode, 'Unknown')} | Brightness: {bright}%")
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
        
        if current_settings["mode"] not in [1, 2]:
            current_settings["mode"] = 1
            
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
        print("╔══════════════════════════════════════╗")
        print("║   INFINIX GT BOOK KEYBOARD CONTROL   ║")
        print("╚══════════════════════════════════════╝")
        print(f" Status: {MODES[current_settings['mode']]} | Brightness: {current_settings['brightness']}%")
        print("----------------------------------------")
        print("1. Change Color (Solid/Breath)")
        print("2. Change Effect Mode")
        print("3. Set Brightness")
        print("4. Turn OFF")
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
            current_settings["mode"] = 0
            apply_settings()
        elif choice == '0':
            sys.exit()
            
        if choice in ['1', '2', '3', '4']:
            import time
            time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye!")