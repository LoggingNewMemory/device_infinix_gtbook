#!/usr/bin/env python3
import sys
import os
import struct
import time

# --- Configuration ---
# EC Index/Data Ports (corresponds to 768u in C# code)
EC_INDEX_PORT = 0x300
EC_DATA_PORT  = 0x301

# Address 64 (0x40) confirmed in SetPerformanceMode.cs
PERF_MODE_ADDR = 0x40

# Address 65 (0x41) confirmed in SetFanFullMode.cs
FAN_BOOST_ADDR = 0x41 

# Trigger Value 161 (0xA1) confirmed in ECWriteRamCMD
CMD_TRIGGER_WRITE = 0xA1 

# Performance Modes from SetPerformanceMode.cs
MODE_OFFICE  = 0x00
MODE_BALANCE = 0x01
MODE_GAMING  = 0x02

def check_root():
    if os.geteuid() != 0:
        print("[-] Error: Root privileges required. Run with sudo.")
        sys.exit(1)

def ec_write_byte(port_fd, index, value):
    """
    Writes a byte to the EC.
    Replicates IO(768u, 1, index, value) from C#.
    """
    try:
        # Write Index to 0x300
        port_fd.seek(EC_INDEX_PORT)
        port_fd.write(struct.pack('B', index))
        
        # Write Value to 0x301
        port_fd.seek(EC_DATA_PORT)
        port_fd.write(struct.pack('B', value))
        
        # Necessary delay for hardware processing
        time.sleep(0.005)
    except OSError as e:
        print(f"[-] I/O Error on index {hex(index)}: {e}")
        sys.exit(1)

def send_ec_ram_cmd(port, address, value):
    """
    Generic function to write to EC RAM using the initialization sequence
    found in ECWriteRamCMD.cs.
    """
    # 1. Initialization Sequence
    ec_write_byte(port, 0x94, 0x00) # Index 148
    ec_write_byte(port, 0x91, 0x00) # Index 145
    ec_write_byte(port, 0x92, 0x00) # Index 146
    ec_write_byte(port, 0x92, 0x01) # Index 146 (Value 1)
    ec_write_byte(port, 0x90, 0x00) # Index 144
    
    # 2. Set Address (e.g., 0x40 for Mode, 0x41 for Fan)
    ec_write_byte(port, 0x91, address)
    
    # 3. Set Value
    ec_write_byte(port, 0xA0, value) # Index 160
    
    # 4. Trigger Write
    ec_write_byte(port, 0x93, CMD_TRIGGER_WRITE) # Index 147

def set_fan_max(enable: bool):
    try:
        with open("/dev/port", "rb+", buffering=0) as port:
            if enable:
                print("[*] Switching to Gaming Mode (Instant Response)...")
                # Set Performance Mode to GAMING (2) first to remove smoothing
                send_ec_ram_cmd(port, PERF_MODE_ADDR, MODE_GAMING)
                
                print("[*] Engaging Max Fan Boost...")
                # Set Fan Boost to ON (1)
                send_ec_ram_cmd(port, FAN_BOOST_ADDR, 1)
                print("[+] Success: Fan set to MAX (Gaming Mode).")
                
            else:
                print("[*] Disabling Max Fan Boost...")
                # Set Fan Boost to OFF (0)
                send_ec_ram_cmd(port, FAN_BOOST_ADDR, 0)
                
                print("[*] Reverting to Balance Mode...")
                # Revert Performance Mode to BALANCE (1) for normal usage
                send_ec_ram_cmd(port, PERF_MODE_ADDR, MODE_BALANCE)
                print("[+] Success: Fan returned to Normal (Balance Mode).")
            
    except FileNotFoundError:
        print("[-] Error: /dev/port not found. Ensure kernel module 'port' is loaded.")
    except Exception as e:
        print(f"[-] An error occurred: {e}")

if __name__ == "__main__":
    check_root()
    
    if len(sys.argv) < 2:
        print("Usage: sudo python3 maxfan.py [on|off]")
        sys.exit(1)
        
    mode = sys.argv[1].lower()
    
    if mode == "on":
        set_fan_max(True)
    elif mode == "off":
        set_fan_max(False)
    else:
        print("Invalid argument. Use 'on' or 'off'.")