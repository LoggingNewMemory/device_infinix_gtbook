from typing import Tuple

from controlcenter.models.tx_buf import FanCtrlMode, get_fan_control_packet
from controlcenter.services.usb_service import USBService
from controlcenter.services.acpi_wmi import ACPIWmi


class FanService:
    def __init__(self, usb_service: USBService, acpi_wmi: ACPIWmi):
        self.usb = usb_service
        self.wmi = acpi_wmi

    def set_fan_mode(self, mode: FanCtrlMode) -> bool:
        """
        Set fan mode via USB command (equivalent to Page1/Page2 behavior).
        """
        packet = get_fan_control_packet(mode.value)
        if self.usb.send_data(packet):
            return True
        else:
            return False

    def set_performance_mode(self, mode: int) -> bool:
        """
        Set performance mode via EC RAM (WMI).
        mode: 0 = Office, 1 = Balance, 2 = Gaming
        """
        try:
            # Address 64 (0x40) is used for Performance mode
            self.wmi.ec_write_ram_cmd(64, mode)
            return True
        except Exception as e:
            return False

    def get_performance_mode(self) -> int:
        """
        Get current performance mode.
        """
        try:
            return self.wmi.ec_read_ram_cmd(64)
        except Exception as e:
            return 0
            
    def set_fan_full_mode(self, flag: bool) -> bool:
        """
        Set max fan mode via WMI EC RAM.
        """
        try:
            self.wmi.set_fan_full_mode(flag)
            return True
        except Exception as e:
            return False
