import tkinter as tk
from tkinter import ttk
import sqlite3
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.performer_frame import PerformerFrame
from services.config_manager import ConfigManager

def get_performer_data(performer_id):
    # Try to find DB
    paths = [
        r"H:\Stash\stash-go.sqlite",
        "data/database.sqlite",
        "stash-go.sqlite"
    ]
    
    db_path = None
    for p in paths:
        if os.path.exists(p):
            db_path = p
            break
            
    if not db_path:
        print("WARNING: Database not found. Using dummy data.")
        return {
            "name": "Test Performer 145",
            "urls": ["https://www.iafd.com/person.rme/perfid=test145/gender=f"]
        }
        
    print(f"Using DB: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM performers WHERE id = ?", (performer_id,))
        row = cur.fetchone()
        
        if row:
            data = dict(row)
            
            # Fetch URLs from performer_urls table
            cur.execute("SELECT url FROM performer_urls WHERE performer_id = ?", (performer_id,))
            url_rows = cur.fetchall()
            data['urls'] = [r['url'] for r in url_rows]

            conn.close()
            return data
        else:
            print(f"Performer {performer_id} not found in DB.")
            return None
    except Exception as e:
        print(f"DB Error: {e}")
        return None

def main():
    sys.stdout.reconfigure(line_buffering=True)
    print("Starting test_id145...", flush=True)
    performer_id = 145
    print(f"Fetching data for Performer ID: {performer_id}")
    
    data = get_performer_data(performer_id)
    
    if not data:
        print("No data available. Exiting.")
        return

    print(f"Loaded Data: {data.get('name', 'Unknown')}")
    
    root = tk.Tk()
    root.title(f"Test ID {performer_id}")
    root.geometry("1200x800")
    
    frame = PerformerFrame(root, performer_id=str(performer_id))
    frame.pack(fill="both", expand=True)
    
    # Trigger load after mainloop starts
    root.after(100, lambda: frame.load_performer(data))
    
    root.mainloop()

if __name__ == "__main__":
    main()
