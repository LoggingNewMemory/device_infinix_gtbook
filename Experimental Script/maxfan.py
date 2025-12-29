#!/usr/bin/env python3
import sys
import os
import struct
import time

# --- Configuration ---
EC_INDEX_PORT = 0x300
EC_DATA_PORT  = 0x301

# EC RAM Address for Fan Boost (from BYD WMI2.cs: ECWriteRamCMD(65, ...))
FAN_BOOST_ADDR = 0x41 

# Commands
CMD_TRIGGER_WRITE = 0xA1

def check_root():
    if os.geteuid() != 0:
        print("[-] Error: This script requires root privileges to access I/O ports.")
        print("    Usage: sudo python maxfan.py [on|off]")
        sys.exit(1)

def ec_write_byte(port_fd, index, value):
    """
    Writes a byte to a specific register index on the EC.
    Equivalent to outb(index, 0x300); outb(value, 0x301);
    """
    try:
        # Write Index
        port_fd.seek(EC_INDEX_PORT)
        port_fd.write(struct.pack('B', index))
        
        # Write Data
        port_fd.seek(EC_DATA_PORT)
        port_fd.write(struct.pack('B', value))
        
        # Small delay to ensure EC processes the write
        time.sleep(0.001)
    except OSError as e:
        print(f"[-] I/O Error writing index {hex(index)}: {e}")
        sys.exit(1)

def set_fan_max(enable: bool):
    """
    Replicates the ECWriteRamCMD sequence found in BYD WMI2.cs
    
    Source logic:
    IO(768u, 1, 148, 0);   -> Reg 0x94 = 0
    IO(768u, 1, 145, 0);   -> Reg 0x91 = 0
    IO(768u, 1, 146, 0);   -> Reg 0x92 = 0
    IO(768u, 1, 146, 1);   -> Reg 0x92 = 1
    IO(768u, 1, 144, 0);   -> Reg 0x90 = 0
    IO(768u, 1, 145, data); -> Reg 0x91 = Address (0x41)
    IO(768u, 1, 160, val);  -> Reg 0xA0 = Value (1 or 0)
    IO(768u, 1, 147, 161);  -> Reg 0x93 = 0xA1 (Trigger Write)
    """
    val = 1 if enable else 0
    status_str = "ON" if enable else "OFF"
    
    print(f"[*] Setting Fan Max Mode to: {status_str}...")

    try:
        with open("/dev/port", "rb+", buffering=0) as port:
            # 1. Reset/Init sequence
            ec_write_byte(port, 0x94, 0x00)
            ec_write_byte(port, 0x91, 0x00)
            ec_write_byte(port, 0x92, 0x00)
            ec_write_byte(port, 0x92, 0x01)
            ec_write_byte(port, 0x90, 0x00)
            
            # 2. Set Target Address (0x41)
            ec_write_byte(port, 0x91, FAN_BOOST_ADDR)
            
            # 3. Set Value (1 = Max, 0 = Normal)
            ec_write_byte(port, 0xA0, val)
            
            # 4. Trigger Write Command (0xA1)
            ec_write_byte(port, 0x93, CMD_TRIGGER_WRITE)
            
            print(f"[+] Successfully sent command to EC.")
            
    except FileNotFoundError:
        print("[-] Error: /dev/port not found. Ensure kernel module 'port' is loaded (usually built-in).")
        print("    If Secure Boot is on, direct I/O access might be blocked.")

if __name__ == "__main__":
    check_root()
    
    if len(sys.argv) < 2:
        print("Usage: sudo python maxfan.py [on|off]")
        sys.exit(1)
        
    mode = sys.argv[1].lower()
    
    if mode == "on":
        set_fan_max(True)
    elif mode == "off":
        set_fan_max(False)
    else:
        print("Invalid argument. Use 'on' or 'off'.")