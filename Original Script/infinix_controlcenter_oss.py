#!/usr/bin/env python3
import hid
import sys
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser

VENDOR_ID = 0x340E
PRODUCT_ID = 0x8002
INTERFACE_NUM = 1

COLOR_BG = "#121212"
COLOR_PANEL = "#1E1E1E"
COLOR_ACCENT = "#FF6600"
COLOR_TEXT = "#FFFFFF"
COLOR_TEXT_DIM = "#AAAAAA"
COLOR_SUCCESS = "#00E676"
COLOR_ERROR = "#FF5252"

KB_MODES = {
    0: "Lights Off",
    1: "Static Color",
    2: "Breathing",
    3: "Neon Cycle",
    4: "Rainbow",
    5: "Flow",
    6: "Wave",
}

PRESET_COLORS = {
    "GT Orange": (255, 100, 0),
    "Cyber Blue": (0, 255, 255),
    "Neon Green": (0, 255, 0),
    "Crimson": (255, 0, 0),
    "Deep Blue": (0, 0, 255),
    "Magenta": (255, 0, 255),
    "Yellow": (255, 255, 0),
    "White": (255, 255, 255),
}

PERFORMANCE_MODES = {
    "OFFICE": 0x40,
    "BALANCE": 0x41,
    "GAMING": 0x42
}

class InfinixHID:
    def __init__(self):
        self.device_path = None

    def find_device(self):
        try:
            for d in hid.enumerate(VENDOR_ID, PRODUCT_ID):
                if d['interface_number'] == INTERFACE_NUM:
                    self.device_path = d['path']
                    return True
        except Exception:
            return False
        return False

    def _checksum(self, packet):
        return sum(packet[1:63]) & 0xFF

    def _send(self, packet):
        if not self.find_device():
            return False, "Device not connected"
        try:
            h = hid.device()
            h.open_path(self.device_path)
            h.write(packet)
            h.close()
            return True, "Success"
        except Exception as e:
            return False, str(e)

    def set_rgb(self, mode_id, r, g, b, brightness):
        packet = [0] * 65
        packet[0] = 0x06
        packet[1] = 0x10 | mode_id
        packet[2] = 0x04
        packet[7] = r
        packet[8] = g
        packet[9] = b
        packet[10] = brightness
        packet[63] = self._checksum(packet)
        return self._send(packet)

    def set_performance(self, mode_byte):
        packet = [0] * 65
        packet[0] = 0x06
        packet[1] = mode_byte
        packet[63] = self._checksum(packet)
        return self._send(packet)

class GTControlCenter:
    def __init__(self, root):
        self.root = root
        self.hw = InfinixHID()
        
        self.root.title("GT CONTROL CENTER")
        self.root.geometry("700x500")
        self.root.configure(bg=COLOR_BG)
        self.root.resizable(False, False)

        self.var_mode = tk.StringVar(value="Static Color")
        self.var_bright = tk.IntVar(value=100)
        self.var_status = tk.StringVar(value="Initializing...")
        self.current_color = (255, 100, 0)

        self._setup_styles()
        self._build_ui()
        self._start_connection_monitor()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TFrame", background=COLOR_BG)
        style.configure("Panel.TFrame", background=COLOR_PANEL, relief="flat")
        
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=COLOR_PANEL, foreground=COLOR_TEXT, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=COLOR_BG, foreground=COLOR_ACCENT, font=("Segoe UI", 18, "bold"))
        style.configure("SubHeader.TLabel", background=COLOR_PANEL, foreground=COLOR_ACCENT, font=("Segoe UI", 12, "bold"))
        
        style.configure("TButton", 
            background="#333333", 
            foreground=COLOR_TEXT, 
            borderwidth=0, 
            font=("Segoe UI", 10, "bold")
        )
        style.map("TButton", 
            background=[('active', COLOR_ACCENT), ('pressed', '#CC5200')],
            foreground=[('active', '#000000')]
        )

        style.configure("Accent.TButton", 
            background=COLOR_ACCENT, 
            foreground="#000000", 
            font=("Segoe UI", 11, "bold")
        )
        style.map("Accent.TButton", background=[('active', '#FF8533')])

    def _build_ui(self):
        header = ttk.Frame(self.root)
        header.pack(fill="x", pady=20, padx=25)
        
        title = ttk.Label(header, text="GT CONTROL CENTER", style="Header.TLabel")
        title.pack(side="left")

        self.conn_lbl = ttk.Label(header, text="● Disconnected", foreground=COLOR_ERROR, font=("Segoe UI", 10))
        self.conn_lbl.pack(side="right")

        content = ttk.Frame(self.root)
        content.pack(fill="both", expand=True, padx=25, pady=10)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        kb_panel = ttk.Frame(content, style="Panel.TFrame", padding=20)
        kb_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        ttk.Label(kb_panel, text="KEYBOARD LIGHTING", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))

        ttk.Label(kb_panel, text="Effect Mode", style="Panel.TLabel", foreground=COLOR_TEXT_DIM).pack(anchor="w")
        mode_cb = ttk.Combobox(kb_panel, textvariable=self.var_mode, values=list(KB_MODES.values()), state="readonly")
        mode_cb.pack(fill="x", pady=(5, 15))
        mode_cb.bind("<<ComboboxSelected>>", self.apply_rgb)

        ttk.Label(kb_panel, text="Brightness", style="Panel.TLabel", foreground=COLOR_TEXT_DIM).pack(anchor="w")
        
        bright_frame = ttk.Frame(kb_panel, style="Panel.TFrame")
        bright_frame.pack(fill="x", pady=(5, 15))
        
        b_scale = ttk.Scale(bright_frame, from_=0, to=100, variable=self.var_bright, orient="horizontal", command=self.on_bright_slide)
        b_scale.pack(side="left", fill="x", expand=True)
        
        self.bright_lbl = ttk.Label(bright_frame, textvariable=self.var_bright, style="Panel.TLabel", width=4)
        self.bright_lbl.pack(side="right", padx=(10, 0))

        ttk.Label(kb_panel, text="Quick Colors", style="Panel.TLabel", foreground=COLOR_TEXT_DIM).pack(anchor="w", pady=(0, 5))
        
        color_grid = ttk.Frame(kb_panel, style="Panel.TFrame")
        color_grid.pack(fill="x")
        
        col_idx = 0
        row_idx = 0
        for name, rgb in PRESET_COLORS.items():
            hex_c = "#%02x%02x%02x" % rgb
            btn = tk.Button(color_grid, bg=hex_c, activebackground=hex_c, 
                            relief="flat", width=4, height=1, 
                            command=lambda c=rgb: self.set_color(c))
            btn.grid(row=row_idx, column=col_idx, padx=4, pady=4)
            col_idx += 1
            if col_idx > 3:
                col_idx = 0
                row_idx += 1

        ttk.Button(kb_panel, text="PICK CUSTOM COLOR", command=self.pick_custom_color).pack(fill="x", pady=(20, 0))

        perf_panel = ttk.Frame(content, style="Panel.TFrame", padding=20)
        perf_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        ttk.Label(perf_panel, text="SYSTEM MODE", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 5))
        ttk.Label(perf_panel, text="(Performance & Back Zone)", style="Panel.TLabel", font=("Segoe UI", 9, "italic"), foreground=COLOR_TEXT_DIM).pack(anchor="w", pady=(0, 20))

        btn_off = ttk.Button(perf_panel, text="OFFICE MODE", command=lambda: self.apply_perf("OFFICE"))
        btn_off.pack(fill="x", pady=10, ipady=5)
        
        btn_bal = ttk.Button(perf_panel, text="BALANCE MODE", command=lambda: self.apply_perf("BALANCE"))
        btn_bal.pack(fill="x", pady=10, ipady=5)

        btn_gam = ttk.Button(perf_panel, text="GAMING MODE", style="Accent.TButton", command=lambda: self.apply_perf("GAMING"))
        btn_gam.pack(fill="x", pady=10, ipady=8)

        self.status_bar = ttk.Label(self.root, textvariable=self.var_status, foreground=COLOR_TEXT_DIM, font=("Segoe UI", 8))
        self.status_bar.pack(side="bottom", fill="x", padx=25, pady=10)

    def _start_connection_monitor(self):
        found = self.hw.find_device()
        if found:
            self.conn_lbl.config(text="● CONNECTED", foreground=COLOR_SUCCESS)
        else:
            self.conn_lbl.config(text="● DISCONNECTED", foreground=COLOR_ERROR)
        self.root.after(3000, self._start_connection_monitor)

    def on_bright_slide(self, val):
        self.apply_rgb()

    def set_color(self, rgb):
        self.current_color = rgb
        if self.var_mode.get() not in ["Static Color", "Breathing"]:
            self.var_mode.set("Static Color")
        self.apply_rgb()

    def pick_custom_color(self):
        color = colorchooser.askcolor(title="Select LED Color")
        if color[0]:
            self.set_color(tuple(map(int, color[0])))

    def apply_rgb(self, event=None):
        mode_str = self.var_mode.get()
        mode_id = next((k for k, v in KB_MODES.items() if v == mode_str), 1)
        
        r, g, b = self.current_color
        bright = self.var_bright.get()

        success, msg = self.hw.set_rgb(mode_id, r, g, b, bright)
        if success:
            self.var_status.set(f"Lighting Applied: {mode_str} | {bright}%")
        else:
            self.var_status.set(f"Error: {msg}")

    def apply_perf(self, mode_name):
        byte_val = PERFORMANCE_MODES[mode_name]
        success, msg = self.hw.set_performance(byte_val)
        
        if success:
            self.var_status.set(f"System Mode Set: {mode_name}")
            messagebox.showinfo("System Mode", f"Switched to {mode_name} Mode")
        else:
            self.var_status.set(f"Error: {msg}")
            messagebox.showerror("Error", f"Failed to set mode: {msg}")

if __name__ == "__main__":
    app_root = tk.Tk()
    
    app = GTControlCenter(app_root)
    app_root.mainloop()