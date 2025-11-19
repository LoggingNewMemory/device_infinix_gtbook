import hid
import struct
import time

VENDOR_ID = 0x340e
PRODUCT_ID = 0x8002

def scan_for_tunnel():
    print("--- TUNNEL SCANNER ---")
    
    # The Serial Packet we want to send (Static RED)
    # H1(52) H2(14) Mode(1) R(255) ...
    serial_packet = struct.pack('<BBBB', 0x34, 0x0E, 0x01, 0xFF) + (b'\x00'*13)

    devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    target = None
    for d in devices:
        if d['interface_number'] == 1:
            target = d
            break

    if not target: return

    h = hid.device()
    h.open_path(target['path'])
    
    print("Scanning Command IDs 0-255...")
    for cmd_id in range(256):
        # Construct a packet where Byte 0 is the Command ID
        # and the rest is our Serial Packet
        
        payload = bytearray(63)
        payload[0] = cmd_id
        
        # Copy serial packet into the payload at offset 1
        # (Simulating: [CMD] [SERIAL_DATA...])
        for i, b in enumerate(serial_packet):
            payload[i+1] = b
            
        # Send Report 6
        h.write(b'\x06' + payload)
        
        # Visual feedback every 10 IDs
        if cmd_id % 10 == 0:
            print(f"Tested ID: {cmd_id}", end='\r')
        
        time.sleep(0.01)

    h.close()
    print("\nScan Complete.")

if __name__ == "__main__":
    scan_for_tunnel()