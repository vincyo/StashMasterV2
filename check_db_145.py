import sqlite3
import os
import sys

# Try multiple paths
paths = [
    r"H:\Stash\stash-go.sqlite",
    r"F:\Nouveau dossier\data\database.sqlite",
    "stash-go.sqlite"
]

DB_PATH = None
for p in paths:
    if os.path.exists(p):
        DB_PATH = p
        break

if not DB_PATH:
    print(f"Database not found in: {paths}")
    # Force creation of result file to signal failure
    with open("performer_145_data.txt", "w") as f:
        f.write("DB NOT FOUND")
    sys.exit(1)

print(f"Using DB: {DB_PATH}")

try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM performers WHERE id = ?", (145,))
    row = cur.fetchone()
    
    with open("performer_145_data.txt", "w", encoding="utf-8") as f:
        if row:
            f.write(f"--- Performer 145 Found ---\n")
            f.write(f"Name: {row['name']}\n")
            f.write(f"URLs: {row['urls']}\n")
            # Dump all fields just in case
            f.write("Full Data:\n")
            for key in row.keys():
                f.write(f"{key}: {row[key]}\n")
            print(f"Data written to performer_145_data.txt")
        else:
            f.write("Performer 145 NOT FOUND\n")
            print("Performer 145 NOT FOUND")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    with open("performer_145_data.txt", "w") as f:
        f.write(f"Error: {e}")

