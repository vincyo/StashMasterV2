import sqlite3
import os

db_path = "H:/Stash/stash-go.sqlite"
if not os.path.exists(db_path):
    db_path = "data/database.sqlite"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print(f"--- Schema for table 'performers' ({db_path}) ---")
cur.execute("PRAGMA table_info(performers)")
columns = cur.fetchall()
for col in columns:
    print(col)

print("\n--- List of all tables ---")
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
for table in tables:
    print(table[0])

# Check for custom fields related tables
for t in ["performer_custom_fields", "custom_fields"]:
    if any(t == table[0] for table in tables):
        print(f"\n--- Schema for table '{t}' ---")
        cur.execute(f"PRAGMA table_info({t})")
        cols = cur.fetchall()
        for c in cols:
            print(c)
        
        cur.execute(f"SELECT * FROM {t} LIMIT 5")
        rows = cur.fetchall()
        print(f"Sample data from {t}:")
        for r in rows:
            print(r)

conn.close()
