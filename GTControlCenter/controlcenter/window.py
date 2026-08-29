import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Pango

import os
import sys
import threading

from controlcenter.models.tx_buf import KeyboardLightMode, KeyboardLight12Mode, BackLightCmd, FanCtrlMode
from controlcenter.services.acpi_wmi import ACPIWmi
from controlcenter.services.usb_service import USBService
from controlcenter.services.serial_service import SerialService
from controlcenter.services.lighting import LightingService
from controlcenter.services.fan_service import FanService
from controlcenter.services.monitor import MonitorService
from controlcenter.services.config import ConfigManager
import ctypes

def load_custom_font(font_path):
    try:
        fontconfig = ctypes.CDLL('libfontconfig.so.1')
        fontconfig.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        fontconfig.FcConfigAppFontAddFile.restype = ctypes.c_int
        return fontconfig.FcConfigAppFontAddFile(None, font_path.encode('utf-8')) != 0
    except Exception:
        return False

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app, backend=None):
        super().__init__(application=app, title="INFINIX - GT BOOK")
        self.set_default_size(1280, 720)
        self.set_resizable(False)
        
        if hasattr(sys, '_MEIPASS'):
            self.assets_dir = os.path.join(sys._MEIPASS, 'assets')
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.assets_dir = os.path.join(base_dir, 'assets')
            
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        theme.add_search_path(self.assets_dir)
        self.set_icon_name("icon")
        
        load_custom_font(os.path.join(self.assets_dir, "InfinixDisplay-Regular.ttf"))
        load_custom_font(os.path.join(self.assets_dir, "HarmonyOS_Sans_Regular.ttf"))
        load_custom_font(os.path.join(self.assets_dir, "HarmonyOS_Sans_Light.ttf"))
        
        self.setup_css()
        
        self.backend = backend
        if self.backend:
            self.wmi = self.backend.wmi
            self.usb = self.backend.usb
            self.serial = self.backend.serial
            self.lighting = self.backend.lighting
            self.fan = self.backend.fan
            self.config_mgr = self.backend.config_mgr
        else:
            self.wmi = ACPIWmi()
            self.usb = USBService()
            self.usb.connect()
            self.serial = SerialService()
            self.lighting = LightingService(self.usb, self.serial)
            self.fan = FanService(self.usb, self.wmi)
            self.config_mgr = ConfigManager()

        self.monitor = MonitorService(self.wmi)
        
        self.setup_ui()
        self.load_settings()
        self.apply_all_settings()
        
        self.connect('close-request', self.on_close_request)
        
        # Populate data immediately before window is shown
        self.update_monitors()
        GLib.timeout_add(2000, self.update_monitors)

    def on_close_request(self, *args):
        self.set_visible(False)
        return True

    def present(self):
        if hasattr(self.get_application(), 'is_background') and self.get_application().is_background and getattr(self.get_application(), 'first_activate_done', False) == False:
            self.get_application().first_activate_done = True
            return
        super().present()

    def setup_css(self):
        css_provider = Gtk.CssProvider()
        css = '''
        window, window.background, window.csd, decoration {
            border-radius: 0px;
        }
        window {
            background-color: #272727;
            color: #ffffff;
            font-family: "HarmonyOS Sans", sans-serif;
        }
        headerbar {
            background-color: #272727;
            background-image: none;
            border: none;
            box-shadow: none;
            border-radius: 0px;
        }
        headerbar windowhandle {
            background-color: transparent;
        }
        .header-title {
            font-family: "Infinix Display", sans-serif;
            font-size: 24px;
            font-weight: bold;
            color: white;
            letter-spacing: 2px;
        }
        .nav-link {
            font-size: 22px;
            color: #ffffff;
            background: transparent;
            border: none;
            box-shadow: none;
            padding: 0 10px;
        }
        .nav-link:hover {
            color: #d1d1d1;
            background: transparent;
        }
        .nav-link.active {
            color: #29b6f6;
        }
        .nav-dot {
            font-size: 22px;
            color: #ffffff;
            margin: 0 5px;
        }
        
        .mode-btn {
            background-color: #3b3b3b;
            color: #ffffff;
            font-size: 26px;
            border-radius: 4px;
            padding: 12px 20px;
            margin-bottom: 15px;
            border: none;
        }
        .mode-btn:hover {
            background-color: #4a4a4a;
        }
        .mode-btn.active {
            background-color: #e53935;
        }
        .mode-btn.active:hover {
            background-color: #ff474c;
        }
        
        .bar-container {
            background-color: transparent;
            margin-top: 5px;
            margin-bottom: 5px;
        }
        .bar-cyan {
            background-color: #29b6f6;
            min-height: 15px;
            transition: min-width 0.6s cubic-bezier(0.25, 1, 0.5, 1);
        }
        .bar-green {
            background-color: #66bb6a;
            min-height: 15px;
            transition: min-width 0.6s cubic-bezier(0.25, 1, 0.5, 1);
        }
        .stat-label {
            font-size: 28px;
            font-weight: bold;
        }
        .stat-sub {
            font-size: 14px;
            color: #a0a0a0;
        }
        .stat-val {
            font-size: 20px;
        }
        .vert-sep {
            background-color: #ffffff;
            min-width: 2px;
            margin-left: 30px;
            margin-right: 30px;
        }
        
        .control-label {
            font-size: 22px;
        }
        .custom-dropdown > button {
            background-color: #444444;
            color: white;
            font-size: 20px;
            border-radius: 8px;
            min-height: 40px;
            border: none;
        }
        .custom-scale contents trough {
            background-color: #555555;
            min-height: 4px;
        }
        .custom-scale contents trough slider {
            background-color: #ffffff;
            min-width: 24px;
            min-height: 24px;
            border-radius: 12px;
        }
        .color-btn {
            border-radius: 8px;
            border: none;
        }
        .action-btn {
            background-color: #e53935;
            color: white;
            font-size: 22px;
            border-radius: 8px;
            padding: 10px;
            border: none;
        }
        '''
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def setup_ui(self):
        self.header = Adw.HeaderBar()
        self.header.set_show_title(False)
        self.header.set_show_start_title_buttons(False)
        self.header.set_decoration_layout(":close")
        
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        img_icon = Gtk.Image.new_from_file(os.path.join(self.assets_dir, "icon.png"))
        img_icon.set_pixel_size(24)
        self.lbl_title = Gtk.Label(label="INFINIX - GT BOOK")
        self.lbl_title.add_css_class("header-title")
        title_box.append(img_icon)
        title_box.append(self.lbl_title)
        
        self.header.pack_start(title_box)
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.append(self.header)
        
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_vexpand(True)
        self.stack.set_margin_start(40)
        self.stack.set_margin_end(40)
        self.stack.set_margin_top(20)
        self.stack.set_margin_bottom(20)
        
        self.setup_overview_page()
        self.setup_keyboard_page()
        self.setup_back_zone_page()
        self.setup_misc_page()
        
        self.main_box.append(self.stack)
        
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        nav_box.set_halign(Gtk.Align.CENTER)
        nav_box.set_margin_bottom(20)
        
        self.nav_btns = {}
        pages = [("overview", "Overview"), ("keyboard", "Keyboard Light"), ("backzone", "Back Zone Light"), ("misc", "Misc")]
        
        for i, (page_id, label) in enumerate(pages):
            btn = Gtk.Button(label=label)
            btn.add_css_class("nav-link")
            if i == 0:
                btn.add_css_class("active")
            btn.connect("clicked", self.on_nav_clicked, page_id)
            self.nav_btns[page_id] = btn
            nav_box.append(btn)
            
            if i < len(pages) - 1:
                dot = Gtk.Label(label="•")
                dot.add_css_class("nav-dot")
                nav_box.append(dot)
                
        self.main_box.append(nav_box)
        self.set_content(self.main_box)

    def on_nav_clicked(self, btn, page_id):
        for b in self.nav_btns.values():
            b.remove_css_class("active")
        btn.add_css_class("active")
        self.stack.set_visible_child_name(page_id)
        
        if page_id == "keyboard":
            self.lbl_title.set_label("INFINIX - KEYBOARD")
        elif page_id == "backzone":
            self.lbl_title.set_label("INFINIX - BACKZONE")
        else:
            self.lbl_title.set_label("INFINIX - GT BOOK")

    def setup_overview_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=30)
        left_box.set_size_request(720, -1)
        left_box.set_hexpand(False)
        left_box.set_valign(Gtk.Align.CENTER)
        
        def create_stat_row(title, sub, val1_id, val2_id, has_double_bar=True):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
            
            title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            lbl_title = Gtk.Label(label=title)
            lbl_title.add_css_class("stat-label")
            lbl_title.set_halign(Gtk.Align.START)
            title_box.append(lbl_title)
            
            lbl_sub = None
            if sub:
                lbl_sub = Gtk.Label(label=sub)
                lbl_sub.add_css_class("stat-sub")
                lbl_sub.set_halign(Gtk.Align.START)
                title_box.append(lbl_sub)
                
            title_box.set_size_request(200, -1)
            row.append(title_box)
            
            bar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            bar_box.set_hexpand(True)
            bar_box.set_valign(Gtk.Align.CENTER)
            bar_box.set_size_request(400, -1)
            
            bar1 = Gtk.Box()
            bar1.add_css_class("bar-cyan")
            bar1.set_halign(Gtk.Align.START)
            bar_box.append(bar1)
            
            if has_double_bar:
                bar2 = Gtk.Box()
                bar2.add_css_class("bar-green")
                bar2.set_halign(Gtk.Align.START)
                bar_box.append(bar2)
            else:
                bar2 = None
                
            row.append(bar_box)
            
            val_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            lbl_v1 = Gtk.Label(label="--")
            lbl_v1.add_css_class("stat-val")
            lbl_v1.set_halign(Gtk.Align.END)
            val_box.append(lbl_v1)
            setattr(self, val1_id, lbl_v1)
            
            if val2_id:
                lbl_v2 = Gtk.Label(label="--")
                lbl_v2.add_css_class("stat-val")
                lbl_v2.set_halign(Gtk.Align.END)
                val_box.append(lbl_v2)
                setattr(self, val2_id, lbl_v2)
                
            val_box.set_size_request(80, -1)
            row.append(val_box)
            
            return row, bar1, bar2, lbl_sub
            
        cpu_row, self.cpu_bar1, self.cpu_bar2, self.lbl_cpu_name = create_stat_row("CPU", "Loading...", "lbl_cpu_freq", "lbl_cpu_temp", True)
        gpu_row, self.gpu_bar1, self.gpu_bar2, self.lbl_gpu_name = create_stat_row("GPU", "Loading...", "lbl_gpu_freq", "lbl_gpu_temp", True)
        bat_row, self.bat_bar1, _, self.lbl_bat_name = create_stat_row("Battery", "Loading...", "lbl_bat_pct", None, False)
        disk_row, self.disk_bar1, _, self.lbl_disk_name = create_stat_row("Disk", "Loading...", "lbl_disk_pct", None, False)

        def fetch_hw_names():
            bat_name = "Internal Battery"
            try:
                import os
                for bat in os.listdir("/sys/class/power_supply"):
                    if bat.startswith("BAT"):
                        try:
                            with open(f"/sys/class/power_supply/{bat}/model_name", "r") as f:
                                bat_name = f.read().strip()
                            with open(f"/sys/class/power_supply/{bat}/manufacturer", "r") as f:
                                bat_man = f.read().strip()
                            if bat_man:
                                bat_name = f"{bat_man} {bat_name}"
                        except Exception:
                            pass
                        break
            except Exception:
                pass

            disk_name = "Primary SSD"
            try:
                import os, re
                with open("/proc/mounts", "r") as f:
                    for line in f:
                        if " / " in line:
                            dev = line.split(" ")[0]
                            if dev.startswith("/dev/"):
                                dev_name = os.path.basename(dev)
                                if dev_name.startswith("nvme"):
                                    dev_name = re.sub(r"p\d+$", "", dev_name)
                                else:
                                    dev_name = re.sub(r"\d+$", "", dev_name)
                                if os.path.exists(f"/sys/block/{dev_name}/device/model"):
                                    with open(f"/sys/block/{dev_name}/device/model", "r") as f:
                                        disk_name = f.read().strip()
                            break
            except Exception:
                pass

            cpu_name = "Unknown CPU"
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.startswith("model name"):
                            cpu_name = line.split(":", 1)[1].strip()
                            break
            except Exception:
                pass
                
            gpu_name = "Unknown GPU"
            try:
                import pynvml
                pynvml.nvmlInit()
                h = pynvml.nvmlDeviceGetHandleByIndex(0)
                name_val = pynvml.nvmlDeviceGetName(h)
                if isinstance(name_val, bytes):
                    gpu_name = name_val.decode('utf-8')
                else:
                    gpu_name = name_val
            except Exception:
                pass

            def update_ui():
                if self.lbl_cpu_name: self.lbl_cpu_name.set_label(cpu_name)
                if self.lbl_gpu_name: self.lbl_gpu_name.set_label(gpu_name)
                if self.lbl_bat_name: self.lbl_bat_name.set_label(bat_name)
                if self.lbl_disk_name: self.lbl_disk_name.set_label(disk_name)
                return False
            
            GLib.idle_add(update_ui)

        threading.Thread(target=fetch_hw_names, daemon=True).start()
        
        left_box.append(cpu_row)
        left_box.append(gpu_row)
        left_box.append(bat_row)
        left_box.append(disk_row)
        
        page.append(left_box)
        
        sep = Gtk.Box()
        sep.add_css_class("vert-sep")
        page.append(sep)
        
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right_box.set_valign(Gtk.Align.START)
        right_box.set_hexpand(True)
        right_box.set_size_request(300, -1)
        right_box.set_margin_top(0)
        
        self.mode_img = Gtk.Picture.new_for_filename(os.path.join(self.assets_dir, "office.png"))
        self.mode_img.set_can_shrink(True)
        self.mode_img.set_size_request(200, 200)
        self.mode_img.set_margin_bottom(20)
        self.mode_img.set_halign(Gtk.Align.CENTER)
        right_box.append(self.mode_img)
        
        self.btn_office = Gtk.Button(label="Office")
        self.btn_office.add_css_class("mode-btn")
        self.btn_office.connect("clicked", lambda x: self.set_performance_mode(0))
        
        self.btn_balance = Gtk.Button(label="Balanced")
        self.btn_balance.add_css_class("mode-btn")
        self.btn_balance.connect("clicked", lambda x: self.set_performance_mode(1))
        
        self.btn_gaming = Gtk.Button(label="Gaming")
        self.btn_gaming.add_css_class("mode-btn")
        self.btn_gaming.connect("clicked", lambda x: self.set_performance_mode(2))
        
        right_box.append(self.btn_office)
        right_box.append(self.btn_balance)
        right_box.append(self.btn_gaming)
        
        fan_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        fan_box.set_margin_top(40)
        lbl_fan = Gtk.Label(label="Max Fan")
        lbl_fan.add_css_class("control-label")
        lbl_fan.set_hexpand(True)
        lbl_fan.set_halign(Gtk.Align.START)
        
        self.max_fan_switch = Gtk.Switch()
        self.max_fan_switch.set_valign(Gtk.Align.CENTER)
        self.max_fan_switch.connect("state-set", self.on_max_fan_toggled)
        
        fan_box.append(lbl_fan)
        fan_box.append(self.max_fan_switch)
        right_box.append(fan_box)
        
        gpu_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        gpu_box.set_margin_top(40)
        lbl_gpu = Gtk.Label(label="GPU Profile")
        lbl_gpu.add_css_class("control-label")
        lbl_gpu.set_hexpand(True)
        lbl_gpu.set_halign(Gtk.Align.START)
        
        self.gpu_mode_dropdown = Gtk.DropDown.new_from_strings(["dGPU Only", "Dynamic", "iGPU Only"])
        self.gpu_mode_dropdown.add_css_class("custom-dropdown")
        self.gpu_mode_dropdown.set_valign(Gtk.Align.CENTER)
        
        try:
            current_gpu_mode = self.config_mgr.config.get("performance", {}).get("gpu_mode")
            if not current_gpu_mode:
                current_gpu_mode = self.wmi.get_gpu_mode()
            if current_gpu_mode in (1, 2, 3):
                self.gpu_mode_dropdown.set_selected(current_gpu_mode - 1)
        except Exception:
            pass

        self.gpu_mode_dropdown.connect("notify::selected", self.on_gpu_mode_changed)
        gpu_box.append(lbl_gpu)
        gpu_box.append(self.gpu_mode_dropdown)
        right_box.append(gpu_box)
        
        page.append(right_box)
        self.stack.add_named(page, "overview")

    def on_gpu_mode_changed(self, dropdown, pspec):
        if getattr(self, '_ignore_gpu_change', False):
            return

        idx = dropdown.get_selected()
        mode = idx + 1
        
        try:
            current_mode = self.config_mgr.config.get("performance", {}).get("gpu_mode")
            if not current_mode:
                current_mode = self.wmi.get_gpu_mode()
            if current_mode == mode:
                return
        except Exception:
            current_mode = 2
            
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Reboot Required",
            body="Changing the GPU profile requires a system reboot. Do you want to reboot now?"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("reboot", "Reboot")
        dialog.set_response_appearance("reboot", Adw.ResponseAppearance.DESTRUCTIVE)
        
        def on_response(dlg, response):
            if response == "reboot":
                if "performance" not in self.config_mgr.config:
                    self.config_mgr.config["performance"] = {}
                self.config_mgr.config["performance"]["gpu_mode"] = mode
                self.config_mgr.save()
                self.wmi.set_gpu_mode(mode)
                os.system("systemctl reboot")
            else:
                self._ignore_gpu_change = True
                if current_mode in (1, 2, 3):
                    self.gpu_mode_dropdown.set_selected(current_mode - 1)
                self._ignore_gpu_change = False

        dialog.connect("response", on_response)
        dialog.present()

    def _create_control_row(self, label_text, widget):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        row.set_margin_bottom(30)
        lbl = Gtk.Label(label=label_text)
        lbl.add_css_class("control-label")
        lbl.set_size_request(140, -1)
        lbl.set_halign(Gtk.Align.START)
        lbl.set_xalign(0.0)
        row.append(lbl)
        widget.set_hexpand(True)
        widget.set_valign(Gtk.Align.CENTER)
        row.append(widget)
        return row

    def setup_keyboard_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        
        img_box = Gtk.Box()
        img_box.set_size_request(400, 300)
        img_box.set_hexpand(False)
        img_box.set_valign(Gtk.Align.CENTER)
        self.kb_preview_img = Gtk.Picture.new_for_filename(os.path.join(self.assets_dir, "keyboard_all.png"))
        self.kb_preview_img.set_can_shrink(False)
        self.kb_preview_img.set_size_request(400, 300)
        self.kb_preview_img.set_halign(Gtk.Align.CENTER)
        img_box.append(self.kb_preview_img)
        page.append(img_box)
        
        sep = Gtk.Box()
        sep.add_css_class("vert-sep")
        page.append(sep)
        
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ctrl_box.set_valign(Gtk.Align.CENTER)
        ctrl_box.set_hexpand(True)
        ctrl_box.set_size_request(450, 500)
        
        self.kb_zone_dropdown = Gtk.DropDown.new_from_strings([
            "Main Keyboard (All)", "Keyboard Zone 1 (Left)", "Keyboard Zone 2 (Mid-Left)", 
            "Keyboard Zone 3 (Mid-Right)", "Keyboard Zone 4 (Right)"
        ])
        self.kb_zone_dropdown.set_size_request(260, -1)
        self.kb_zone_dropdown.add_css_class("custom-dropdown")
        self.kb_zone_dropdown.connect("notify::selected", self.on_kb_zone_changed)
        ctrl_box.append(self._create_control_row("Zone", self.kb_zone_dropdown))
        
        self.kb_color_button = Gtk.Button()
        self.kb_current_rgba = Gdk.RGBA()
        self.kb_current_rgba.parse("#FF0000")
        self.kb_color_popover = Gtk.Popover()
        self.kb_color_widget = Gtk.ColorChooserWidget()
        self.kb_color_widget.set_size_request(400, 300)
        self.kb_color_widget.set_rgba(self.kb_current_rgba)
        self.kb_color_popover.set_child(self.kb_color_widget)
        self.kb_color_popover.set_parent(self.kb_color_button)
        
        def on_popover_closed(p):
            self.kb_current_rgba = self.kb_color_widget.get_rgba()
            self._update_color_button_ui(self.kb_color_button, self.kb_current_rgba)
            
        self.kb_color_popover.connect("closed", on_popover_closed)
        
        def on_button_clicked(btn):
            self.kb_color_widget.set_rgba(self.kb_current_rgba)
            self.kb_color_popover.popup()
            
        self.kb_color_button.connect("clicked", on_button_clicked)
        self.kb_color_button.add_css_class("color-btn")
        self.kb_color_button.set_size_request(-1, 40)
        self._update_color_button_ui(self.kb_color_button, self.kb_current_rgba)
        ctrl_box.append(self._create_control_row("Color", self.kb_color_button))
        
        self.kb_mode_dropdown = Gtk.DropDown.new_from_strings([
            "Off", "Static Color", "Breathing", "Neon Cycle", "Ocean Waves", "Rainbow", "Flow", "Wave", "Rhythm Normal", "Rhythm Dance"
        ])
        self.kb_mode_dropdown.set_size_request(260, -1)
        self.kb_mode_dropdown.add_css_class("custom-dropdown")
        ctrl_box.append(self._create_control_row("Effects", self.kb_mode_dropdown))
        
        self.kb_brightness_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.kb_brightness_scale.set_value(100)
        self.kb_brightness_scale.add_css_class("custom-scale")
        ctrl_box.append(self._create_control_row("Brightness", self.kb_brightness_scale))
        
        # Audio controls for rhythm mode
        self.kb_audio_names = ["Auto (Speaker Output)"]
        self.kb_audio_device_ids = ["auto_speaker"]
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    self.kb_audio_device_ids.append(i)
                    self.kb_audio_names.append(dev['name'])
        except Exception:
            pass
            
        self.kb_device_dropdown = Gtk.DropDown.new_from_strings(self.kb_audio_names)
        self.kb_sens_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.kb_sens_scale.set_value(75)
        self.kb_smooth_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.kb_smooth_scale.set_value(0)
        
        apply_btn = Gtk.Button(label="Apply Keyboard Lighting")
        apply_btn.add_css_class("action-btn")
        apply_btn.connect("clicked", self.apply_keyboard_lighting)
        ctrl_box.append(apply_btn)
        
        page.append(ctrl_box)
        self.stack.add_named(page, "keyboard")

    def setup_back_zone_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=50)
        page.set_valign(Gtk.Align.CENTER)
        
        img = Gtk.Picture.new_for_filename(os.path.join(self.assets_dir, "backzone.png"))
        img.set_can_shrink(True)
        img.set_halign(Gtk.Align.CENTER)
        page.append(img)
        
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ctrl_box.set_halign(Gtk.Align.CENTER)
        ctrl_box.set_size_request(700, -1)
        
        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        row1.set_margin_bottom(30)
        
        lbl_c = Gtk.Label(label="Color")
        lbl_c.add_css_class("control-label")
        row1.append(lbl_c)
        
        self.bz_color_button = Gtk.Button()
        self.bz_current_rgba = Gdk.RGBA()
        self.bz_current_rgba.parse("#FF0000")
        self.bz_color_popover = Gtk.Popover()
        self.bz_color_widget = Gtk.ColorChooserWidget()
        self.bz_color_widget.set_size_request(400, 300)
        self.bz_color_widget.set_rgba(self.bz_current_rgba)
        self.bz_color_popover.set_child(self.bz_color_widget)
        self.bz_color_popover.set_parent(self.bz_color_button)
        
        def on_popover_closed(p):
            self.bz_current_rgba = self.bz_color_widget.get_rgba()
            self._update_color_button_ui(self.bz_color_button, self.bz_current_rgba)
            
        self.bz_color_popover.connect("closed", on_popover_closed)
        
        def on_button_clicked(btn):
            self.bz_color_widget.set_rgba(self.bz_current_rgba)
            self.bz_color_popover.popup()
            
        self.bz_color_button.connect("clicked", on_button_clicked)
        self.bz_color_button.add_css_class("color-btn")
        self.bz_color_button.set_size_request(150, 40)
        self._update_color_button_ui(self.bz_color_button, self.bz_current_rgba)
        row1.append(self.bz_color_button)
        
        lbl_e = Gtk.Label(label="Effects")
        lbl_e.add_css_class("control-label")
        lbl_e.set_margin_start(40)
        row1.append(lbl_e)
        
        self.bz_mode_dropdown = Gtk.DropDown.new_from_strings([
            "Default", "Off", "Static Color", "Breathing", "Rhythm", "Rainbow Rhythm", "Jump", "Rainbow Jump", "Round", "Cover"
        ])
        self.bz_mode_dropdown.add_css_class("custom-dropdown")
        self.bz_mode_dropdown.set_hexpand(True)
        row1.append(self.bz_mode_dropdown)
        ctrl_box.append(row1)
        
        self.bz_brightness_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.bz_brightness_scale.set_value(100)
        self.bz_brightness_scale.add_css_class("custom-scale")
        ctrl_box.append(self._create_control_row("Brightness", self.bz_brightness_scale))
        
        self.bz_audio_names = ["Auto (Speaker Output)"]
        self.bz_audio_device_ids = ["auto_speaker"]
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    self.bz_audio_device_ids.append(i)
                    self.bz_audio_names.append(dev['name'])
        except Exception:
            pass
            
        self.bz_device_dropdown = Gtk.DropDown.new_from_strings(self.bz_audio_names)
        self.bz_sens_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.bz_sens_scale.set_value(75)
        self.bz_smooth_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.bz_smooth_scale.set_value(0)
        
        apply_btn = Gtk.Button(label="Apply Back Zone Lighting")
        apply_btn.add_css_class("action-btn")
        apply_btn.connect("clicked", self.apply_back_zone_lighting)
        ctrl_box.append(apply_btn)
        
        page.append(ctrl_box)
        self.stack.add_named(page, "backzone")

    def setup_misc_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        
        img_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        img_box.set_hexpand(True)
        img_box.set_valign(Gtk.Align.CENTER)
        img_box.set_halign(Gtk.Align.CENTER)
        img = Gtk.Picture.new_for_filename(os.path.join(self.assets_dir, "GTBook.png"))
        img.set_can_shrink(True)
        img_box.append(img)
        
        lbl_credit = Gtk.Label(label="GT Control Center - By: Kanagawa Yamada")
        lbl_credit.add_css_class("stat-sub")
        lbl_credit.set_margin_top(20)
        img_box.append(lbl_credit)
        
        page.append(img_box)
        
        sep = Gtk.Box()
        sep.add_css_class("vert-sep")
        page.append(sep)
        
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ctrl_box.set_valign(Gtk.Align.CENTER)
        ctrl_box.set_size_request(450, -1)
        
        lbl_title = Gtk.Label(label="Audio Monitoring Devices")
        lbl_title.add_css_class("header-title")
        lbl_title.set_margin_bottom(20)
        ctrl_box.append(lbl_title)
        
        self.audio_dropdown = Gtk.DropDown.new_from_strings(self.kb_audio_names)
        self.audio_dropdown.add_css_class("custom-dropdown")
        self.audio_dropdown.set_margin_bottom(30)
        self.audio_dropdown.connect("notify::selected", self.on_global_audio_changed)
        ctrl_box.append(self.audio_dropdown)
        
        self.global_sens_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.global_sens_scale.set_value(75)
        self.global_sens_scale.add_css_class("custom-scale")
        self.global_sens_scale.connect("value-changed", self.on_global_sens_changed)
        ctrl_box.append(self._create_control_row("Sensitivity", self.global_sens_scale))
        
        self.global_smooth_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.global_smooth_scale.set_value(0)
        self.global_smooth_scale.add_css_class("custom-scale")
        self.global_smooth_scale.connect("value-changed", self.on_global_smooth_changed)
        ctrl_box.append(self._create_control_row("Smoothness", self.global_smooth_scale))
        
        self.autostart_switch = Gtk.Switch()
        self.autostart_switch.set_valign(Gtk.Align.CENTER)
        self.autostart_switch.set_halign(Gtk.Align.END)
        self.autostart_switch.connect("state-set", self.on_autostart_toggled)
        self.autostart_switch.set_active(self.is_autostart_enabled())
        ctrl_box.append(self._create_control_row("Run on Startup", self.autostart_switch))
        
        reset_btn = Gtk.Button(label="Reset Configurations")
        reset_btn.add_css_class("action-btn")
        reset_btn.set_margin_top(20)
        reset_btn.connect("clicked", self.on_reset_settings)
        ctrl_box.append(reset_btn)
        
        page.append(ctrl_box)
        self.stack.add_named(page, "misc")

    def get_autostart_path(self):
        return os.path.expanduser("~/.config/autostart/com.byd.controlcenter.desktop")

    def is_autostart_enabled(self):
        return os.path.exists(self.get_autostart_path())

    def on_autostart_toggled(self, switch, state):
        autostart_path = self.get_autostart_path()
        autostart_dir = os.path.dirname(autostart_path)
        if not os.path.exists(autostart_dir):
            os.makedirs(autostart_dir)
            
        if state:
            if getattr(sys, 'frozen', False):
                exec_cmd = os.path.abspath(sys.executable)
            else:
                exec_cmd = f"{os.path.abspath(sys.executable)} {os.path.abspath(sys.argv[0])}"
            
            desktop_content = f"""[Desktop Entry]
Type=Application
Exec={exec_cmd} --background
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=GT Control Center
Comment=Run GT Control Center in background
"""
            with open(autostart_path, "w") as f:
                f.write(desktop_content)
        else:
            if os.path.exists(autostart_path):
                os.remove(autostart_path)
                
        return False

    def on_global_audio_changed(self, dropdown, pspec):
        val = dropdown.get_selected()
        self.kb_device_dropdown.set_selected(val)
        self.bz_device_dropdown.set_selected(val)

    def on_global_sens_changed(self, scale):
        val = scale.get_value()
        self.kb_sens_scale.set_value(val)
        self.bz_sens_scale.set_value(val)
        if self.lighting.kb_anim:
            self.lighting.kb_anim["sens"] = val
        if self.lighting.bz_anim:
            self.lighting.bz_anim["sens"] = val
        if "keyboard" in self.config_mgr.config:
            self.config_mgr.config["keyboard"]["sens"] = val
        if "backzone" in self.config_mgr.config:
            self.config_mgr.config["backzone"]["sens"] = val
        self.config_mgr.save()

    def on_global_smooth_changed(self, scale):
        val = scale.get_value()
        self.kb_smooth_scale.set_value(val)
        self.bz_smooth_scale.set_value(val)
        if self.lighting.kb_anim:
            self.lighting.kb_anim["smooth"] = val
        if self.lighting.bz_anim:
            self.lighting.bz_anim["smooth"] = val
        if "keyboard" in self.config_mgr.config:
            self.config_mgr.config["keyboard"]["smooth"] = val
        if "backzone" in self.config_mgr.config:
            self.config_mgr.config["backzone"]["smooth"] = val
        self.config_mgr.save()


    def _update_color_button_ui(self, button, rgba):
        css_provider = Gtk.CssProvider()
        css = f"* {{ background-color: {rgba.to_string()}; background-image: none; border-radius: 6px; }}"
        css_provider.load_from_data(css.encode())
        context = button.get_style_context()
        context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def on_kb_zone_changed(self, dropdown, pspec):
        zone = dropdown.get_selected()
        
        if zone == 0:
            self.kb_mode_dropdown.set_model(Gtk.StringList.new([
                "Off", "Static Color", "Breathing", "Neon Cycle", "Ocean Waves", "Rainbow", "Flow", "Wave", "Rhythm Normal", "Rhythm Dance"
            ]))
        else:
            self.kb_mode_dropdown.set_model(Gtk.StringList.new([
                "Off", "Static Color", "Breathing", "Neon Cycle", "Rainbow"
            ]))
            
        # Update preview image
        images = [
            "keyboard_all.png",
            "keyboard_left.png",
            "keyboard_mid_left.png",
            "keyboard_mid_right.png",
            "keyboard_right.png"
        ]
        if hasattr(self, 'kb_preview_img') and zone < len(images):
            self.kb_preview_img.set_filename(os.path.join(self.assets_dir, images[zone]))
            
        zone_str = str(zone)
        zones_config = self.config_mgr.config.get("keyboard_zones", {})
        
        if zone_str in zones_config:
            kb = zones_config[zone_str]
            self.kb_mode_dropdown.set_selected(kb.get("mode", 1))
            self.kb_current_rgba.parse(kb.get("color", "#FF0000"))
            self._update_color_button_ui(self.kb_color_button, self.kb_current_rgba)
            self.kb_brightness_scale.set_value(kb.get("brightness", 100))
            if hasattr(self, 'kb_device_dropdown') and hasattr(self, 'kb_audio_device_ids'):
                device_idx = kb.get("audio_device", 0)
                if device_idx < len(self.kb_audio_device_ids):
                    self.kb_device_dropdown.set_selected(device_idx)
            if hasattr(self, 'kb_sens_scale'):
                self.kb_sens_scale.set_value(kb.get("sens", 75))
            if hasattr(self, 'kb_smooth_scale'):
                self.kb_smooth_scale.set_value(kb.get("smooth", 0))


    def _restore_back_zone_if_needed(self):
        if hasattr(self, 'bz_mode_dropdown'):
            def reapply():
                self.apply_back_zone_lighting(None)
                return False
            GLib.timeout_add(150, reapply)

    def set_performance_mode(self, mode: int, save=True):
        self.btn_office.remove_css_class("active")
        self.btn_balance.remove_css_class("active")
        self.btn_gaming.remove_css_class("active")
        
        if mode == 0:
            self.btn_office.add_css_class("active")
            target_fan_mode = FanCtrlMode.OfficeMode
            if hasattr(self, 'mode_img'):
                self.mode_img.set_filename(os.path.join(self.assets_dir, "office.png"))
        elif mode == 1:
            self.btn_balance.add_css_class("active")
            target_fan_mode = FanCtrlMode.PerformanceMode
            if hasattr(self, 'mode_img'):
                self.mode_img.set_filename(os.path.join(self.assets_dir, "balanced.png"))
        else:
            self.btn_gaming.add_css_class("active")
            target_fan_mode = FanCtrlMode.GamingMode
            if hasattr(self, 'mode_img'):
                self.mode_img.set_filename(os.path.join(self.assets_dir, "gaming.png"))
            
        self.fan.set_performance_mode(mode)
        
        self.fan.set_fan_mode(target_fan_mode)
        
        if hasattr(self, 'max_fan_switch') and self.max_fan_switch.get_active():
            self.fan.set_fan_full_mode(True)
            self.fan.set_fan_mode(FanCtrlMode.FullSpeed)
        else:
            self.fan.set_fan_full_mode(False)
            
        self._restore_back_zone_if_needed()
            
        if save:
            self.config_mgr.config["performance"]["mode"] = mode
            self.config_mgr.save()

    def on_max_fan_toggled(self, switch, state):
        self.fan.set_fan_full_mode(state)
        if state:
            self.fan.set_fan_mode(FanCtrlMode.FullSpeed)
        else:
            self.fan.set_fan_mode(FanCtrlMode.FullSpeedOff)
            if self.btn_office.has_css_class("active"):
                self.fan.set_fan_mode(FanCtrlMode.OfficeMode)
            elif self.btn_balance.has_css_class("active"):
                self.fan.set_fan_mode(FanCtrlMode.PerformanceMode)
            elif self.btn_gaming.has_css_class("active"):
                self.fan.set_fan_mode(FanCtrlMode.GamingMode)
                
        self._restore_back_zone_if_needed()
                
        self.config_mgr.config["performance"]["max_fan"] = state
        self.config_mgr.save()
        return False

    def apply_keyboard_lighting(self, btn):
        color = self.kb_current_rgba
        hex_color = f"#{int(color.red*255):02x}{int(color.green*255):02x}{int(color.blue*255):02x}"
        
        idx = self.kb_mode_dropdown.get_selected()
        zone = self.kb_zone_dropdown.get_selected()
        
        brightness_pct = self.kb_brightness_scale.get_value()
        brightness = int((brightness_pct / 100.0) * 255)
        
        sens = int(self.kb_sens_scale.get_value())
        smooth = int(self.kb_smooth_scale.get_value())
        
        device_idx = self.kb_device_dropdown.get_selected()
        audio_device = self.kb_audio_device_ids[device_idx] if hasattr(self, 'kb_audio_device_ids') and device_idx < len(self.kb_audio_device_ids) else None
        
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

            # Sync the effect to all individual zones so they don't revert if a specific zone is later configured
            # (Only sync static colors and Off to avoid animation timer glitches like 'Color Jump')
            if idx <= 2 or idx == 4:
                cmd_map = {1: 6, 2: 6, 3: 7, 4: 7}
                offset_map = {1: 0, 2: 4, 3: 0, 4: 4}
                zone_mode_map = {0: 0, 1: 0, 2: 1, 3: 2, 4: 2, 5: 3}
                zone_mode = zone_mode_map.get(idx, 0)
                sync_color = hex_color
                for z in range(1, 5):
                    self.lighting.set_zone_mode(cmd_map[z], offset_map[z] | zone_mode, sync_color, brightness=brightness)
            
            if idx != 4:
                self.lighting.set_keyboard_mode(mapped_mode, hex_color, brightness=brightness, sens=sens, smooth=smooth, audio_device=audio_device)

        elif 1 <= zone <= 4:
            cmd_map = {1: 6, 2: 6, 3: 7, 4: 7}
            offset_map = {1: 0, 2: 4, 3: 0, 4: 4}
            cmd = cmd_map[zone]
            offset = offset_map[zone]
            
            zone_mode_map = {
                0: 0, # Off -> Always (black)
                1: 0, # Static Color -> Always
                2: 1, # Breathing -> Breath
                3: 2, # Neon Cycle -> GradualChange
                4: 3  # Rainbow -> RainBow
            }
            zone_mode = zone_mode_map.get(idx, 0)
            
            param = offset | zone_mode
            if idx == 0:
                hex_color = "#000000"
            elif idx in (3, 4):
                hex_color = "#FFFFFF"  # Hardware requires white color for full-spectrum animations
            self.lighting.set_zone_mode(cmd, param, hex_color, brightness=brightness)
            
        if "keyboard_zones" not in self.config_mgr.config:
            self.config_mgr.config["keyboard_zones"] = {}
            
        zone_str = str(zone)
        zone_settings = {
            "mode": idx,
            "color": hex_color if idx != 0 else f"#{int(color.red*255):02x}{int(color.green*255):02x}{int(color.blue*255):02x}",
            "brightness": brightness_pct,
            "audio_device": device_idx,
            "sens": sens,
            "smooth": smooth
        }
        self.config_mgr.config["keyboard_zones"][zone_str] = zone_settings
        
        if zone == 0:
            for z in range(1, 5):
                self.config_mgr.config["keyboard_zones"][str(z)] = zone_settings.copy()

        self.config_mgr.config["keyboard"].update(zone_settings)
        self.config_mgr.config["keyboard"]["zone"] = zone
        self.config_mgr.save()

    def apply_back_zone_lighting(self, btn):
        color = self.bz_current_rgba
        hex_color = f"#{int(color.red*255):02x}{int(color.green*255):02x}{int(color.blue*255):02x}"
        
        idx = self.bz_mode_dropdown.get_selected()
        
        brightness_pct = self.bz_brightness_scale.get_value()
        brightness = int((brightness_pct / 100.0) * 255)
        
        sens = int(self.bz_sens_scale.get_value())
        smooth = int(self.bz_smooth_scale.get_value())
        
        device_idx = self.bz_device_dropdown.get_selected()
        audio_device = self.bz_audio_device_ids[device_idx] if hasattr(self, 'bz_audio_device_ids') and device_idx < len(self.bz_audio_device_ids) else None
        
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
            
            if hasattr(self, 'max_fan_switch') and self.max_fan_switch.get_active():
                self.fan.set_fan_full_mode(True)
                self.fan.set_fan_mode(FanCtrlMode.FullSpeed)
            else:
                self.fan.set_fan_full_mode(False)
                
            self.lighting.set_serial_back_zone_mode(bz_cmd, "#000000", brightness=100)
            hex_color = "#000000"
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

        self.config_mgr.config["backzone"].update({
            "mode": idx,
            "color": hex_color if idx not in (0, 1) else f"#{int(color.red*255):02x}{int(color.green*255):02x}{int(color.blue*255):02x}",
            "brightness": brightness_pct,
            "audio_device": device_idx,
            "sens": sens,
            "smooth": smooth
        })
        self.config_mgr.save()

    def update_monitors(self):
        def fetch_data():
            cpu_temp = self.monitor.get_cpu_temp()
            gpu_temp = self.monitor.get_gpu_temp()
            
            try:
                import psutil
                cpu_freq = psutil.cpu_freq().current / 1000.0 if psutil.cpu_freq() else 2.6
                bat = psutil.sensors_battery()
                bat_pct = int(bat.percent) if bat else 100
                disk = psutil.disk_usage('/')
                disk_pct = int(disk.percent)
            except Exception:
                cpu_freq = 0.0
                bat_pct = 0
                disk_pct = 0
                
            gpu_usage = self.monitor.get_gpu_usage()
            
            def update_ui():
                self.lbl_cpu_temp.set_label(f"{cpu_temp} °C" if cpu_temp > 0 else "N/A")
                self.lbl_gpu_temp.set_label(f"{gpu_temp} °C" if gpu_temp > 0 else "Sleep")
                self.lbl_cpu_freq.set_label(f"{cpu_freq:.1f} GHz" if cpu_temp > 0 else "0.0 GHz")
                self.lbl_gpu_freq.set_label(f"{gpu_usage}%" if gpu_temp > 0 else "0%")
                
                self.lbl_bat_pct.set_label(f"{bat_pct}%")
                self.lbl_disk_pct.set_label(f"{disk_pct}%")
                
                self.animate_bar(self.cpu_bar1, int(min(1.0, cpu_freq / 5.0) * 400))
                self.animate_bar(self.cpu_bar2, int(min(1.0, cpu_temp / 100.0) * 400))
                self.animate_bar(self.gpu_bar1, int((gpu_usage / 100.0) * 400))
                self.animate_bar(self.gpu_bar2, int(min(1.0, gpu_temp / 100.0) * 400))
                
                self.animate_bar(self.bat_bar1, int((bat_pct / 100.0) * 400))
                self.animate_bar(self.disk_bar1, int((disk_pct / 100.0) * 400))
                return False

            GLib.idle_add(update_ui)

        threading.Thread(target=fetch_data, daemon=True).start()
        return True # Continue timer

    def animate_bar(self, bar, new_width):
        if not hasattr(bar, '_anim_target_width'):
            bar._anim_target_width = 0
            
        old_width = float(bar._anim_target_width)
        bar._anim_target_width = float(new_width)
        
        def on_anim_tick(val, *args):
            bar.set_size_request(int(val), -1)
            
        target = Adw.CallbackAnimationTarget.new(on_anim_tick)
        anim = Adw.TimedAnimation.new(bar, old_width, float(new_width), 800, target)
        anim.set_easing(Adw.Easing.EASE_OUT_CUBIC)
        anim.play()
        # Keep a reference to prevent garbage collection stopping the animation early
        bar._current_anim = anim

    def load_settings(self):
        conf = self.config_mgr.config
        
        # Performance
        perf = conf.get("performance", {})
        self.max_fan_switch.set_active(perf.get("max_fan", False))

        # Keyboard
        kb = conf.get("keyboard", {})
        if hasattr(self, 'kb_zone_dropdown'):
            self.kb_zone_dropdown.set_selected(kb.get("zone", 0))
            self.kb_mode_dropdown.set_selected(kb.get("mode", 1))
            self.kb_current_rgba.parse(kb.get("color", "#FF0000"))
            self._update_color_button_ui(self.kb_color_button, self.kb_current_rgba)
            self.kb_brightness_scale.set_value(kb.get("brightness", 100))
            if hasattr(self, 'kb_device_dropdown') and hasattr(self, 'kb_audio_device_ids'):
                device_idx = kb.get("audio_device", 0)
                if device_idx < len(self.kb_audio_device_ids):
                    self.kb_device_dropdown.set_selected(device_idx)
            if hasattr(self, 'kb_sens_scale'):
                sens_val = kb.get("sens", 75)
                self.kb_sens_scale.set_value(sens_val)
                if hasattr(self, 'global_sens_scale'):
                    self.global_sens_scale.set_value(sens_val)
            if hasattr(self, 'kb_smooth_scale'):
                smooth_val = kb.get("smooth", 0)
                self.kb_smooth_scale.set_value(smooth_val)
                if hasattr(self, 'global_smooth_scale'):
                    self.global_smooth_scale.set_value(smooth_val)

        # Back Zone
        bz = conf.get("backzone", {})
        if hasattr(self, 'bz_mode_dropdown'):
            self.bz_mode_dropdown.set_selected(bz.get("mode", 0))
            self.bz_current_rgba.parse(bz.get("color", "#FF0000"))
            self._update_color_button_ui(self.bz_color_button, self.bz_current_rgba)
            self.bz_brightness_scale.set_value(bz.get("brightness", 100))
            if hasattr(self, 'bz_device_dropdown') and hasattr(self, 'bz_audio_device_ids'):
                device_idx = bz.get("audio_device", 0)
                if device_idx < len(self.bz_audio_device_ids):
                    self.bz_device_dropdown.set_selected(device_idx)
            if hasattr(self, 'bz_sens_scale'):
                self.bz_sens_scale.set_value(bz.get("sens", 75))
            if hasattr(self, 'bz_smooth_scale'):
                self.bz_smooth_scale.set_value(bz.get("smooth", 0))

    def apply_all_settings(self):
        conf = self.config_mgr.config
        perf = conf.get("performance", {})
        self.set_performance_mode(perf.get("mode", 1), save=False)
        self.apply_keyboard_lighting(None)
        self.apply_back_zone_lighting(None)

    def on_reset_settings(self, btn):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Reset Settings",
            body="Are you sure you want to reset all settings to their default values? This cannot be undone."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("reset", "Reset")
        dialog.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)
        
        def on_response(dlg, response):
            if response == "reset":
                self.config_mgr.reset()
                self.load_settings()
                self.apply_all_settings()
                
        dialog.connect("response", on_response)
        dialog.present()

