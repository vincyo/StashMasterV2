import tkinter as tk
from tkinter import ttk
from gui.performer_frame import PerformerFrame

def test_load_performer():
    root = tk.Tk()
    root.title("Test PerformerFrame Load")
    root.geometry("1024x768")
    
    # Dummy Performer Data
    performer_data = {
        "name": "Riley Reid",
        "birthdate": "1991-07-09",
        "country": "United States",
        "urls": [
            "https://twitter.com/RileyReidx3", # Non-priority
            "https://www.iafd.com/person.rme/perfid=RileyReid/gender=f", # Priority 1 (Valid?)
            # Missing FreeOnes
            # Missing TheNude
            # Missing Babepedia
            # Missing Boobpedia
            # Missing XXXBios
        ]
    }
    
    frame = PerformerFrame(root)
    frame.pack(fill="both", expand=True)
    
    # Button to trigger load
    btn = ttk.Button(root, text="Load Performer", command=lambda: frame.load_performer(performer_data))
    btn.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    test_load_performer()
