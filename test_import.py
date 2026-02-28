print("Start imports...")
try:
    import tkinter as tk
    print("tkinter OK")
    import sqlite3
    print("sqlite3 OK")
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from gui.performer_frame import PerformerFrame
    print("PerformerFrame OK")
    from services.config_manager import ConfigManager
    print("ConfigManager OK")
except Exception as e:
    print(f"Import Error: {e}")
print("End imports")
