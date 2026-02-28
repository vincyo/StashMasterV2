# check_db.py — vérification rapide DB
import sqlite3, sys

DB_PATH = r"F:\stash\stash-go.sqlite"  # adapter selon votre installation

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Vérifier un performer (remplacer 42 par un ID réel testé)
performer_id = 42

print(f"=== Performer {performer_id} ===")
cur.execute("SELECT name, details, tattoos, piercings FROM performers WHERE id=?",
            (performer_id,))
row = cur.fetchone()
if row:
    print(f"  Name: {row['name']}")
    print(f"  Details: {row['details'][:80] if row['details'] else 'VIDE'}...")
    print(f"  Tattoos: {row['tattoos']}")

cur.execute("SELECT url FROM performer_urls WHERE performer_id=?", (performer_id,))
urls = [r['url'] for r in cur.fetchall()]
print(f"  URLs: {urls}")

cur.execute("""
    SELECT t.name FROM tags t
    JOIN performers_tags pt ON pt.tag_id = t.id
    WHERE pt.performer_id=?
""", (performer_id,))
tags = [r['name'] for r in cur.fetchall()]
print(f"  Tags: {tags[:10]}")

# Vérifier un group (remplacer 5 par un ID réel testé)
group_id = 5
print(f"\n=== Group {group_id} ===")
cur.execute("SELECT name, director, description FROM groups WHERE id=?", (group_id,))
row = cur.fetchone()
if row:
    print(f"  Name: {row['name']}")
    print(f"  Director: {row['director']}")

# Scènes avec URLs
cur.execute("""
    SELECT s.title, su.url
    FROM groups_scenes gs
    JOIN scenes s ON s.id = gs.scene_id
    LEFT JOIN scene_urls su ON su.scene_id = s.id
    WHERE gs.group_id=?
    LIMIT 5
""", (group_id,))
for row in cur.fetchall():
    print(f"  Scène: {row['title']} → {row['url']}")

conn.close()