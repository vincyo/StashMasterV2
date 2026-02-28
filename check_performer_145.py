import sqlite3
import json

DB_PATH = "H:/Stash/stash-go.sqlite" # Assuming this is the path based on inspect_db.py
# If not found, try config
import os
if not os.path.exists(DB_PATH):
    # Try to load config
    try:
        from services.config_manager import ConfigManager
        config = ConfigManager()
        DB_PATH = config.get("database_path")
    except:
        DB_PATH = "data/database.sqlite"

print(f"Using DB: {DB_PATH}")

def get_performer(id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Check if table exists
    try:
        cur.execute("SELECT * FROM performers WHERE id = ?", (id,))
        row = cur.fetchone()
        if row:
            print(f"--- Performer {id} ---")
            for key in row.keys():
                print(f"{key}: {row[key]}")
        else:
            print(f"Performer {id} not found.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    get_performer(145)
