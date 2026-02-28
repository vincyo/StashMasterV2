import sqlite3
import os

db_path = "H:/Stash/stash-go.sqlite"
if not os.path.exists(db_path):
    db_path = "data/database.sqlite"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print(f"Tables: {', '.join(tables)}")

# Check performers columns
cur.execute("PRAGMA table_info(performers)")
p_cols = [c[1] for c in cur.fetchall()]
print(f"Performer columns: {', '.join(p_cols)}")

# check for any table with 'custom' in it
custom_tables = [t for t in tables if 'custom' in t.lower()]
print(f"Custom field tables: {', '.join(custom_tables)}")

for t in custom_tables:
    print(f"\n--- {t} ---")
    cur.execute(f"PRAGMA table_info({t})")
    for c in cur.fetchall(): print(c)
    cur.execute(f"SELECT * FROM {t} LIMIT 10")
    for r in cur.fetchall(): print(r)

conn.close()
