import struct
import threading
import time


class ACPIWmi:
    r"""
    ACPI-WMI Bridge for GT Control Center.
    Maps to the Windows \root\wmi ACPIMethod class.
    GUID: 3161C7C3-489F-4074-82AE-538101CCE1C2
    """
    def __init__(self):
        self._is_mock = True
        self._lock = threading.Lock()
        
    def _call_wmi_method(self, method_id: int, in_data: bytearray, retries=3) -> int:
        # Format bytearray to {0xXX, 0xXX, ...} string
        buf_str = "{" + ", ".join([f"0x{b:02X}" for b in in_data]) + "}"
        cmd = f"\\_SB.AMW0.WMBA 0 {method_id} {buf_str}"
        
        for attempt in range(retries):
            try:
                with self._lock:
                    with open("/proc/acpi/call", "w") as f:
                        f.write(cmd)
                    with open("/proc/acpi/call", "r") as f:
                        result = f.read().strip('\x00').strip()
                        
                if result == "Error: AE_NOT_FOUND" or "Error" in result:
                    if attempt < retries - 1:
                        time.sleep(0.1)
                        continue
                    return 0
                    
                if not result:
                    if attempt < retries - 1:
                        time.sleep(0.1)
                        continue
                    return 0
                    
                if result.startswith("0x"):
                    val = int(result, 16)
                else:
                    val = int(result)
                    
                if val > 0:
                    return val
                elif attempt < retries - 1:
                    time.sleep(0.1)
                    continue
                return val
                    
            except PermissionError:
                return 0
            except FileNotFoundError:
                return 0
            except ValueError:
                if attempt < retries - 1:
                    time.sleep(0.1)
                    continue
                return 0
                
        return 0

    def do_method(self, cmd: int) -> int:
        """
        Equivalent to Wmi.DoMethod
        """
        buf = bytearray(24)
        buf[0:4] = b"BYDL"
        buf[4] = cmd & 0xFF
        buf[5] = (cmd >> 8) & 0xFF
        buf[6] = (cmd >> 16) & 0xFF
        buf[7] = (cmd >> 24) & 0xFF
        return self._call_wmi_method(1, buf)

    def smi(self, cmd: int, rw: int, length: int = 0, data: int = 0) -> int:
        """
        Equivalent to Wmi.SMI
        """
        buf = bytearray(24)
        buf[0:4] = b"BYDL"
        buf[4] = cmd & 0xFF
        buf[5] = (cmd >> 8) & 0xFF
        buf[6] = (cmd >> 16) & 0xFF
        buf[7] = (cmd >> 24) & 0xFF
        buf[12] = rw
        buf[13] = length
        if rw == 1:
            buf[16] = data & 0xFF
            
        return self._call_wmi_method(3, buf)
        
    def mem_io(self, address: int, rw: int, index: int, data: int = 0) -> int:
        """
        Equivalent to Wmi.IO (MemIO)
        """
        buf = bytearray(24)
        buf[0:4] = b"BYDL"
        buf[4] = address & 0xFF
        buf[5] = (address >> 8) & 0xFF
        buf[12] = 1 # ?
        buf[13] = rw
        buf[14] = 8 # length?
        buf[15] = index
        buf[16] = data & 0xFF
        return self._call_wmi_method(2, buf)

    # Higher-level helpers
    def get_cpu_temp(self) -> int:
        return self.do_method(3)
        
    def get_gpu_temp(self) -> int:
        return self.do_method(4)

    def get_ec_status(self) -> int:
        return self.do_method(2)
        
    def ec_write_ram_cmd(self, address: int, data: int) -> int:
        self.mem_io(768, 1, 148, 0)
        self.mem_io(768, 1, 145, 0)
        self.mem_io(768, 1, 146, 0)
        self.mem_io(768, 1, 146, 1)
        self.mem_io(768, 1, 144, 0)
        self.mem_io(768, 1, 145, address)
        self.mem_io(768, 1, 160, data)
        self.mem_io(768, 1, 147, 161)
        return 80
        
    def ec_read_ram_cmd(self, address: int) -> int:
        self.mem_io(768, 1, 148, 0)
        self.mem_io(768, 1, 146, 1)
        self.mem_io(768, 1, 144, 0)
        self.mem_io(768, 1, 145, address)
        self.mem_io(768, 1, 147, 160)
        return self.mem_io(768, 0, 160, 0)

    def set_gpu_mode(self, mode: int) -> int:
        """
        Switches the GPU mode: 1 = dGPU Only, 2 = Dynamic, 3 = iGPU Only
        """
        return self.ec_write_ram_cmd(192, mode)

    def get_gpu_mode(self) -> int:
        return self.ec_read_ram_cmd(192)

    def set_fan_full_mode(self, flag: bool) -> int:
        """
        Equivalent to Wmi.SetFanFullMode
        """
        return self.ec_write_ram_cmd(65, 1 if flag else 0)

