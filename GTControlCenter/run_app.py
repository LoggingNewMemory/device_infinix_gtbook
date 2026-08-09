import sys
import os

# PyInstaller creates a temp folder and stores path in _MEIPASS
if hasattr(sys, '_MEIPASS'):
    os.chdir(sys._MEIPASS)

if '--tray-process' in sys.argv:
    import pystray
    from PIL import Image
    import subprocess
    import signal
    
    icon_path = os.path.join('assets', 'icon.png')
    if not os.path.exists(icon_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, 'assets', 'icon.png')
        
    image = Image.open(icon_path)
    if getattr(sys, 'frozen', False):
        exec_cmd = [sys.executable]
    else:
        exec_cmd = [sys.executable, os.path.abspath(__file__)]
    
    def show_window(icon, item):
        subprocess.Popen(exec_cmd)
        
    def quit_app(icon, item):
        # Kill the parent GTK process
        try:
            os.kill(os.getppid(), signal.SIGTERM)
        except Exception:
            pass
        icon.stop()
        
    menu = pystray.Menu(
        pystray.MenuItem("Show GT Control Center", show_window),
        pystray.MenuItem("Quit", quit_app)
    )
    
    icon = pystray.Icon("GTControlCenter", image, "GT Control Center", menu)
    icon.run()
    sys.exit(0)

from controlcenter.app import main

if __name__ == '__main__':
    main()
