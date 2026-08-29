import time
from controlcenter.models.tx_buf import FanCtrlMode, KeyboardLightMode, BackLightCmd
from controlcenter.services.acpi_wmi import ACPIWmi
from controlcenter.services.usb_service import USBService
from controlcenter.services.serial_service import SerialService
from controlcenter.services.lighting import LightingService
from controlcenter.services.fan_service import FanService
from controlcenter.services.config import ConfigManager


class AppBackend:
    def __init__(self):
        self.wmi = ACPIWmi()
        self.usb = USBService()
        self.usb.connect()
        self.serial = SerialService()
        self.lighting = LightingService(self.usb, self.serial)
        self.fan = FanService(self.usb, self.wmi)
        self.config_mgr = ConfigManager()

    def _hex_to_rgb(self, hex_color: str):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (0, 0, 0)

    def apply_performance(self):
        perf = self.config_mgr.config.get("performance", {})
        mode = perf.get("mode", 1)
        max_fan = perf.get("max_fan", False)

        if mode == 0:
            target_fan_mode = FanCtrlMode.OfficeMode
        elif mode == 1:
            target_fan_mode = FanCtrlMode.PerformanceMode
        else:
            target_fan_mode = FanCtrlMode.GamingMode

        self.fan.set_performance_mode(mode)
        self.fan.set_fan_mode(target_fan_mode)

        if max_fan:
            self.fan.set_fan_full_mode(True)
            self.fan.set_fan_mode(FanCtrlMode.FullSpeed)
        else:
            self.fan.set_fan_full_mode(False)

    def apply_keyboard(self):
        kb = self.config_mgr.config.get("keyboard", {})
        idx = kb.get("mode", 1)
        zone = kb.get("zone", 0)
        hex_color = kb.get("color", "#FF0000")
        brightness_pct = kb.get("brightness", 100)
        brightness = int((brightness_pct / 100.0) * 255)
        sens = kb.get("sens", 75)
        smooth = kb.get("smooth", 0)
        
        audio_device = "auto_speaker" 

        if zone == 0:
            mode_map = {
                0: KeyboardLightMode.LightOFF,
                1: KeyboardLightMode.Always,
                2: KeyboardLightMode.Breath,
                3: KeyboardLightMode.GradualChange,
                4: KeyboardLightMode.GradualChange,
                5: KeyboardLightMode.RainBow,
                6: KeyboardLightMode.Flow,
                7: KeyboardLightMode.Wave,
                8: KeyboardLightMode.RhythmNormal,
                9: KeyboardLightMode.RhythmDance
            }
            mapped_mode = mode_map.get(idx, KeyboardLightMode.Always)
            if idx == 0:
                hex_color = "#000000"
            elif idx in (3, 4, 5):
                hex_color = "#FFFFFF"

            if idx <= 2 or idx == 4:
                cmd_map = {1: 6, 2: 6, 3: 7, 4: 7}
                offset_map = {1: 0, 2: 4, 3: 0, 4: 4}
                zone_mode_map = {0: 0, 1: 0, 2: 1, 3: 2, 4: 2, 5: 3}
                zone_mode = zone_mode_map.get(idx, 0)
                for z in range(1, 5):
                    self.lighting.set_zone_mode(cmd_map[z], offset_map[z] | zone_mode, hex_color, brightness=brightness)
            
            if idx != 4:
                self.lighting.set_keyboard_mode(mapped_mode, hex_color, brightness=brightness, sens=sens, smooth=smooth, audio_device=audio_device)

        elif 1 <= zone <= 4:
            cmd_map = {1: 6, 2: 6, 3: 7, 4: 7}
            offset_map = {1: 0, 2: 4, 3: 0, 4: 4}
            cmd = cmd_map[zone]
            offset = offset_map[zone]
            
            zone_mode_map = {
                0: 0, 1: 0, 2: 1, 3: 2, 4: 3
            }
            zone_mode = zone_mode_map.get(idx, 0)
            
            param = offset | zone_mode
            if idx == 0:
                hex_color = "#000000"
            elif idx in (3, 4):
                hex_color = "#FFFFFF"
            self.lighting.set_zone_mode(cmd, param, hex_color, brightness=brightness)

    def apply_backzone(self):
        bz = self.config_mgr.config.get("backzone", {})
        idx = bz.get("mode", 0)
        hex_color = bz.get("color", "#FF0000")
        brightness_pct = bz.get("brightness", 100)
        brightness = int((brightness_pct / 100.0) * 255)
        sens = bz.get("sens", 75)
        smooth = bz.get("smooth", 0)
        audio_device = "auto_speaker"

        if idx == 0:
            self.lighting.bz_anim = None
            self.lighting.update_animations()
            
            perf_mode = self.config_mgr.config.get("performance", {}).get("mode", 1)
            if perf_mode == 0:
                target_fan_mode = FanCtrlMode.OfficeMode
                bz_cmd = BackLightCmd.SliceMode
            elif perf_mode == 1:
                target_fan_mode = FanCtrlMode.PerformanceMode
                bz_cmd = BackLightCmd.BalanceMode
            else:
                target_fan_mode = FanCtrlMode.GamingMode
                bz_cmd = BackLightCmd.GameMode
            self.fan.set_fan_mode(target_fan_mode)
            
            perf = self.config_mgr.config.get("performance", {})
            if perf.get("max_fan", False):
                self.fan.set_fan_full_mode(True)
                self.fan.set_fan_mode(FanCtrlMode.FullSpeed)
            else:
                self.fan.set_fan_full_mode(False)
                
            self.lighting.set_serial_back_zone_mode(bz_cmd, "#000000", brightness=100)
        else:
            mode_map_back = {
                1: BackLightCmd.Light_Close,
                2: BackLightCmd.Light_AlwaysOn,
                3: BackLightCmd.Light_Breath,
                4: BackLightCmd.Light_Rythm,
                5: 99,
                6: BackLightCmd.Light_Jump,
                7: 98,
                8: BackLightCmd.Light_Round,
                9: BackLightCmd.Light_Cover
            }
            mapped_mode = mode_map_back.get(idx, BackLightCmd.Light_AlwaysOn)
            if idx == 1:
                hex_color = "#000000"
            self.lighting.set_serial_back_zone_mode(mapped_mode, hex_color, brightness=brightness, sens=sens, smooth=smooth, audio_device=audio_device)

    def apply_all(self):
        self.apply_performance()
        self.apply_keyboard()
        self.apply_backzone()

