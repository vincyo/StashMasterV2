import sqlite3
import csv

DB_PATH = r"H:\Stash\stash-go.sqlite"
OUTPUT_CSV = "short_markers.csv"

def main():
    print(f"Extraction des marqueurs <= 60s...")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    query = """
    SELECT 
        s.id as scene_id, 
        s.title as scene_title, 
        m.id as marker_id, 
        m.title as marker_title, 
        m.seconds as start, 
        m.end_seconds as end
    FROM scene_markers m
    JOIN scenes s ON m.scene_id = s.id
    WHERE (m.end_seconds - m.seconds) <= 60 
       OR m.end_seconds IS NULL 
       OR m.end_seconds = 0
    ORDER BY s.id, m.seconds
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    results = []
    for r in rows:
        scene_id, scene_title, m_id, m_title, start, end = r
        duration = (end - start) if (end and end > start) else 0
        results.append({
            "scene_id": scene_id,
            "scene_title": scene_title,
            "marker_id": m_id,
            "marker_title": m_title,
            "start": round(start, 2),
            "end": round(end, 2) if end else 0,
            "duration": round(duration, 2)
        })
    
    if results:
        with open(OUTPUT_CSV, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"[OK] {len(results)} marqueurs extraits dans {OUTPUT_CSV}")
    else:
        print("[!] Aucun marqueur de moins de 60s trouvé.")
        
    conn.close()

if __name__ == "__main__":
    main()
