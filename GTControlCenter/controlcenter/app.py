import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio

import subprocess

from controlcenter.window import MainWindow


class ControlCenterApp(Adw.Application):
    def __init__(self, is_background=False):
        super().__init__(application_id='com.byd.controlcenter',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.is_background = is_background
        self.first_activate = True
                         
        # Suppress Adwaita warning if user's environment has prefer-dark-theme set globally
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", False)
            
        self.win = None
        self.tray_proc = None

    def setup_tray(self):
        try:
            import os
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, '--tray-process']
            else:
                cmd = [sys.executable, os.path.abspath(sys.argv[0]), '--tray-process']
            self.tray_proc = subprocess.Popen(cmd)
        except Exception as e:
            print("Failed to start tray process:", e)

    def do_startup(self):
        Adw.Application.do_startup(self)
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        
        # Keep application running in background
        self.hold()
        self.setup_tray()

    def get_backend(self):
        if not hasattr(self, 'backend'):
            from controlcenter.backend import AppBackend
            self.backend = AppBackend()
        return self.backend

    def do_activate(self):
        if self.is_background and self.first_activate:
            self.first_activate = False
            # Completely avoid creating a GTK window for true headless start
            self.get_backend().apply_all()
        else:
            if not self.win:
                self.win = MainWindow(self, self.get_backend())
            self.win.present()
            self.first_activate = False

def main():
    is_bg = '--background' in sys.argv
    if is_bg:
        sys.argv.remove('--background')
        
    app = ControlCenterApp(is_background=is_bg)
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())

