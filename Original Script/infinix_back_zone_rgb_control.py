import usb.core
import usb.util
import sys

# Device Constants from Usb.cs
VENDOR_ID = 0x340E  # 13326
PRODUCT_ID = 0x8002 # 32770
ENDPOINT_OUT = 0x02

def calculate_checksum(data):
    # C# Logic: Sum of bytes at index 1 to 62
    total = sum(data[1:63])
    return total & 0xFF

def create_packet(mode_byte):
    # Packet structure based on TxBuf.cs
    # Size is 64 bytes
    packet = [0] * 64
    
    # Byte 0: ID (Fixed 6)
    packet[0] = 0x06
    
    # Byte 1: Command + Mode (Fan_Ctrl + Mode)
    # Reversed logic from C# bit manipulation:
    # Office (0)  -> 0x40 (64)
    # Balance (1) -> 0x41 (65)
    # Gaming (2)  -> 0x42 (66)
    packet[1] = 0x40 + mode_byte
    
    # Byte 63: Checksum
    packet[63] = calculate_checksum(packet)
    
    return bytes(packet)

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
    packet = create_packet(modes[mode_name])
    
    # Find device
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if dev is None:
        print("Device not found! Is the Infinix GT Book connected?")
        return

    # Detach kernel driver if active (hid-generic often grabs this)
    if dev.is_kernel_driver_active(1):
        try:
            dev.detach_kernel_driver(1)
        except usb.core.USBError as e:
            sys.exit(f"Could not detach kernel driver: {str(e)}")

    # Write to Endpoint 0x02
    try:
        # Interface 1 is used in Usb.cs
        dev.write(ENDPOINT_OUT, packet, 1000)
        print("Command sent successfully.")
    except usb.core.USBError as e:
        print(f"Error sending command: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sudo python infinix_control.py [office|balance|gaming]")
    else:
        send_command(sys.argv[1].lower())