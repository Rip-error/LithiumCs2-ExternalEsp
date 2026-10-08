import os
# Kill Qt's DPI scaling BEFORE any Qt import — Windows gives us
# physical pixels, we render in physical pixels. no double-scaling.
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE_V2
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import sys
from PySide6 import QtWidgets
from Lithium.Overlay import ESPOverlay


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    overlay = ESPOverlay()
    overlay.show()
    sys.exit(app.exec())