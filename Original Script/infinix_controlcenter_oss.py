#!/usr/bin/env python3
import hid
import sys
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser

# --- Hardware Constants ---
VENDOR_ID = 0x340E
PRODUCT_ID = 0x8002
INTERFACE_NUM = 1

# --- Definitions ---
KB_MODES = {
    0: "Off",
    1: "Static Color",
    2: "Breathing",
    3: "Neon Cycle",
    4: "Rainbow",
    5: "Flow",
    6: "Wave",
}

PRESET_COLORS = {
    "Infinix Orange": (255, 100, 0),
    "Red": (255, 0, 0),
    "Green": (0, 255, 0),
    "Blue": (0, 0, 255),
    "Cyan": (0, 255, 255),
    "Magenta": (255, 0, 255),
    "Yellow": (255, 255, 0),
    "White": (255, 255, 255),
}

POWER_MODES = {
    "Office": 0x40,
    "Balance": 0x41,
    "Gaming": 0x42
}

class InfinixHardware:
    def __init__(self):
        self.device_path = None

    def find_device(self):
        """Finds the correct HID interface."""
        for d in hid.enumerate(VENDOR_ID, PRODUCT_ID):
            if d['interface_number'] == INTERFACE_NUM:
                self.device_path = d['path']
                return True
        return False

    def _calculate_checksum(self, packet):
        # Sum of bytes at index 1 to 62
        return sum(packet[1:63]) & 0xFF

    def _send_packet(self, packet):
        if not self.find_device():
            return False, "Device not found"
        
        try:
            h = hid.device()
            h.open_path(self.device_path)
            h.write(packet)
            h.close()
            return True, "Success"
        except Exception as e:
            return False, str(e)

    def set_keyboard(self, mode_id, r, g, b, brightness):
        packet = [0] * 65
        packet[0] = 0x06            # Report ID
        packet[1] = 0x10 | mode_id  # Command + Mode
        packet[2] = 0x04            # Data Size
        packet[7] = r
        packet[8] = g
        packet[9] = b
        packet[10] = brightness
        
        packet[63] = self._calculate_checksum(packet)
        return self._send_packet(packet)

    def set_power_mode(self, mode_byte):
        packet = [0] * 65
        packet[0] = 0x06
        packet[1] = mode_byte
        packet[63] = self._calculate_checksum(packet)
        return self._send_packet(packet)

class GTControlCenterApp:
    def __init__(self, root):
        self.root = root
        self.hw = InfinixHardware()
        self.root.title("Infinix GT Control Center (OSS)")
        self.root.geometry("600x550")
        self.root.resizable(False, False)
        
        # --- State Variables ---
        self.current_color = (255, 100, 0) # Default Orange
        self.brightness_var = tk.IntVar(value=50)
        self.mode_var = tk.StringVar(value="Static Color")
        self.status_var = tk.StringVar(value="Ready")

        # --- Style Configuration (Dark/Gamer Theme) ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        BG_COLOR = "#1e1e1e"
        FG_COLOR = "#ffffff"
        ACCENT_COLOR = "#ff6600" # Infinix Orange
        PANEL_COLOR = "#2d2d2d"
        
        self.root.configure(bg=BG_COLOR)
        
        self.style.configure("TFrame", background=BG_COLOR)
        self.style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=ACCENT_COLOR)
        
        self.style.configure("TButton", background=PANEL_COLOR, foreground=FG_COLOR, borderwidth=1, focuscolor=ACCENT_COLOR)
        self.style.map("TButton", background=[('active', ACCENT_COLOR)])
        
        self.style.configure("Accent.TButton", background=ACCENT_COLOR, foreground="#000000", font=("Segoe UI", 10, "bold"))
        self.style.map("Accent.TButton", background=[('active', "#ff8533")])

        self.style.configure("TScale", background=BG_COLOR, troughcolor=PANEL_COLOR, sliderlength=20)
        
        self.style.configure("TLabelframe", background=BG_COLOR, foreground=FG_COLOR, bordercolor=PANEL_COLOR)
        self.style.configure("TLabelframe.Label", background=BG_COLOR, foreground=ACCENT_COLOR, font=("Segoe UI", 11, "bold"))

        # --- UI Layout ---
        self._build_header()
        self._build_keyboard_controls()
        self._build_power_controls()
        self._build_statusbar()

    def _build_header(self):
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", pady=15, padx=20)
        
        lbl = ttk.Label(header_frame, text="GT BOOK CONTROL", style="Header.TLabel")
        lbl.pack(side="left")
        
        # Device Status Indicator
        self.lbl_conn = ttk.Label(header_frame, text="Checking...", font=("Segoe UI", 9))
        self.lbl_conn.pack(side="right", anchor="center")
        self.check_connection()

    def _build_keyboard_controls(self):
        kb_frame = ttk.LabelFrame(self.root, text="Keyboard Lighting", padding=15)
        kb_frame.pack(fill="x", padx=20, pady=10)

        # Row 1: Mode Selection
        row1 = ttk.Frame(kb_frame)
        row1.pack(fill="x", pady=5)
        ttk.Label(row1, text="Effect Mode:").pack(side="left", padx=(0, 10))
        
        mode_cb = ttk.Combobox(row1, textvariable=self.mode_var, values=list(KB_MODES.values()), state="readonly")
        mode_cb.pack(side="left", fill="x", expand=True)
        mode_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_keyboard())

        # Row 2: Brightness
        row2 = ttk.Frame(kb_frame)
        row2.pack(fill="x", pady=15)
        ttk.Label(row2, text="Brightness:").pack(side="left", padx=(0, 10))
        scale = ttk.Scale(row2, from_=0, to=100, variable=self.brightness_var, orient="horizontal", command=lambda v: self.apply_keyboard())
        scale.pack(side="left", fill="x", expand=True, padx=5)
        
        # FIX: Moved width=4 inside ttk.Label constructor
        ttk.Label(row2, textvariable=self.brightness_var, width=4).pack(side="right")

        # Row 3: Colors
        ttk.Label(kb_frame, text="Quick Colors:").pack(anchor="w", pady=(10, 5))
        color_grid = ttk.Frame(kb_frame)
        color_grid.pack(fill="x")
        
        col_idx = 0
        for name, rgb in PRESET_COLORS.items():
            btn = tk.Button(color_grid, bg=self._rgb_to_hex(rgb), width=4, height=2, 
                            activebackground=self._rgb_to_hex(rgb), 
                            command=lambda c=rgb: self.set_color(c))
            btn.grid(row=0, column=col_idx, padx=5, pady=5)
            col_idx += 1
            
        # Custom Color Button
        custom_btn = ttk.Button(kb_frame, text="Pick Custom Color", command=self.pick_color)
        custom_btn.pack(fill="x", pady=(15, 0))

    def _build_power_controls(self):
        pwr_frame = ttk.LabelFrame(self.root, text="System Performance", padding=15)
        pwr_frame.pack(fill="x", padx=20, pady=10)
        
        info_lbl = ttk.Label(pwr_frame, text="Select performance profile (affects fan speed & TDP):", font=("Segoe UI", 9, "italic"))
        info_lbl.pack(anchor="w", pady=(0, 10))

        btn_grid = ttk.Frame(pwr_frame)
        btn_grid.pack(fill="x")
        
        # Spread buttons evenly
        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)
        btn_grid.columnconfigure(2, weight=1)

        ttk.Button(btn_grid, text="OFFICE", command=lambda: self.apply_power("Office")).grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(btn_grid, text="BALANCE", command=lambda: self.apply_power("Balance")).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(btn_grid, text="GAMING", command=lambda: self.apply_power("Gaming"), style="Accent.TButton").grid(row=0, column=2, padx=5, sticky="ew")

    def _build_statusbar(self):
        status_frame = ttk.Frame(self.root, style="TFrame")
        status_frame.pack(side="bottom", fill="x", pady=10, padx=20)
        
        lbl = ttk.Label(status_frame, textvariable=self.status_var, font=("Segoe UI", 9))
        lbl.pack(side="left")

    # --- Logic ---

    def _rgb_to_hex(self, rgb):
        return "#%02x%02x%02x" % rgb

    def check_connection(self):
        if self.hw.find_device():
            self.lbl_conn.config(text="● Connected", foreground="#00ff00")
        else:
            self.lbl_conn.config(text="○ Disconnected", foreground="#ff0000")
        self.root.after(5000, self.check_connection) # Recheck every 5s

    def pick_color(self):
        color = colorchooser.askcolor(title="Select Keyboard Color")
        if color[0]: # If color selected (r, g, b)
            self.set_color(tuple(map(int, color[0])))

    def set_color(self, rgb_tuple):
        self.current_color = rgb_tuple
        # Auto switch to Static if user picks a color
        if self.mode_var.get() not in ["Static Color", "Breathing"]:
            self.mode_var.set("Static Color")
        self.apply_keyboard()

    def get_mode_id(self):
        current_text = self.mode_var.get()
        for k, v in KB_MODES.items():
            if v == current_text:
                return k
        return 1

    def apply_keyboard(self):
        mode = self.get_mode_id()
        r, g, b = self.current_color
        bright = self.brightness_var.get()
        
        success, msg = self.hw.set_keyboard(mode, r, g, b, bright)
        if success:
            self.status_var.set(f"Applied: {KB_MODES[mode]} | Brightness: {bright}%")
        else:
            self.status_var.set(f"Error: {msg}")

    def apply_power(self, mode_name):
        mode_byte = POWER_MODES[mode_name]
        success, msg = self.hw.set_power_mode(mode_byte)
        if success:
            self.status_var.set(f"System Mode set to: {mode_name.upper()}")
            messagebox.showinfo("Success", f"Performance mode set to {mode_name}")
        else:
            self.status_var.set(f"Error: {msg}")
            messagebox.showerror("Error", f"Failed to set mode: {msg}")

if __name__ == "__main__":
    root = tk.Tk()
    app = GTControlCenterApp(root)
    root.mainloop()