import usb.core
import usb.util
from typing import Optional, Tuple


VID = 0x340E  # 13326
PID = 0x8002  # 32770

class USBService:
    def __init__(self):
        self.dev = None
        self.interface = 1
        self.ep_out = 0x02
        self.ep_in = 0x82 # Assuming 0x82 for IN endpoint if out is 0x02
        
    def connect(self) -> bool:
        """
        Connect to the BYD USB controller.
        """
        try:
            self.dev = usb.core.find(idVendor=VID, idProduct=PID)
            if self.dev is None:
                return False
                
            # Detach kernel driver if necessary
            if self.dev.is_kernel_driver_active(self.interface):
                try:
                    self.dev.detach_kernel_driver(self.interface)
                except usb.core.USBError as e:
                    self.dev = None
                    return False
                    
            usb.util.claim_interface(self.dev, self.interface)
            return True
            
        except usb.core.USBError as e:
            self.dev = None
            return False

    def disconnect(self):
        if self.dev is not None:
            usb.util.dispose_resources(self.dev)
            self.dev = None

    def send_data(self, data: bytearray) -> bool:
        """
        Send a 64-byte report to the device.
        """
        if self.dev is None:
            if not self.connect():
                return False
                
        try:
            # Write to EP02 (Out)
            bytes_written = self.dev.write(self.ep_out, data, timeout=3000)
            return bytes_written == len(data)
        except usb.core.USBError as e:
            self.disconnect() # Force reconnect on next try
            return False

    def receive_data(self, timeout=3000) -> Optional[bytearray]:
        """
        Receive a 64-byte report from the device.
        """
        if self.dev is None:
            if not self.connect():
                return None
                
        try:
            # Read from EP82 (In)
            data = self.dev.read(self.ep_in, 64, timeout=timeout)
            return bytearray(data)
        except usb.core.USBError as e:
            self.disconnect()
            return None
