import sqlite3

DB_PATH = r"H:\Stash\stash-go.sqlite"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=== NETTOYAGE CIBLÉ DES MARQUEURS ===\n")

    # 1. Identifier les marqueurs "69" (via Tag ou Titre)
    cur.execute("""
        SELECT DISTINCT m.id 
        FROM scene_markers m
        LEFT JOIN scene_markers_tags mt ON m.id = mt.scene_marker_id
        LEFT JOIN tags t ON mt.tag_id = t.id
        WHERE m.title = '69' OR t.name = '69'
    """)
    ids_69 = [r[0] for r in cur.fetchall()]

    # 2. Identifier les marqueurs "Anal" <= 60s (via Tag ou Titre)
    cur.execute("""
        SELECT DISTINCT m.id 
        FROM scene_markers m
        LEFT JOIN scene_markers_tags mt ON m.id = mt.scene_marker_id
        LEFT JOIN tags t ON mt.tag_id = t.id
        WHERE (m.title = 'Anal' OR t.name = 'Anal')
          AND ((m.end_seconds - m.seconds) <= 60 
               OR m.end_seconds IS NULL 
               OR m.end_seconds = 0)
    """)
    ids_anal_short = [r[0] for r in cur.fetchall()]

    total_ids = set(ids_69) | set(ids_anal_short)

    print(f"Bilan avant suppression :")
    print(f"  - Marqueurs '69' trouvés : {len(ids_69)}")
    print(f"  - Marqueurs 'Anal' (<= 60s) trouvés : {len(ids_anal_short)}")
    print(f"  - Total unique à supprimer : {len(total_ids)}")

    if not total_ids:
        print("\n[!] Aucun marqueur ne correspond aux critères. Fin du script.")
        conn.close()
        return

    confirm = input("\nÊtes-vous sûr de vouloir SUPPRIMER ces marqueurs définitivement ? (OUI/non) : ")
    
    if confirm == "OUI":
        try:
            ids_tuple = [(int(mid),) for mid in total_ids]
            
            # Supprimer les liens tags
            cur.executemany("DELETE FROM scene_markers_tags WHERE scene_marker_id = ?", ids_tuple)
            # Supprimer les marqueurs
            cur.executemany("DELETE FROM scene_markers WHERE id = ?", ids_tuple)
            
            conn.commit()
            print(f"\n[OK] {len(total_ids)} marqueurs ont été supprimés avec succès.")
        except Exception as e:
            print(f"\n[ERREUR] Échec de la suppression : {e}")
            conn.rollback()
    else:
        print("\n[INFO] Opération annulée.")

    conn.close()

if __name__ == "__main__":
    main()
