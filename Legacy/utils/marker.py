from __future__ import annotations
import sqlite3
import csv
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional, Any

DB_PATH = r"H:\Stash\stash-go.sqlite"
CSV_REPORT = "audit_markers.csv"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("=== AUDIT AVANCE DES MARKERS ===\n")

# Récupérer toutes scènes
cur.execute("""
    SELECT s.id, s.title, v.duration 
    FROM scenes s
    LEFT JOIN scenes_files sf ON s.id = sf.scene_id
    LEFT JOIN video_files v ON sf.file_id = v.file_id
    WHERE sf."primary" = 1 OR sf."primary" IS NULL
    GROUP BY s.id
""")
scenes: List[Any] = cur.fetchall()

tag_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
    "total": 0,
    "overlaps": 0,
    "short": 0,
    "long": 0,
    "exact_dupes": 0
})

scene_results: List[Dict[str, Any]] = []
scene_scores: List[Tuple[Optional[str], int]] = []
markers_to_delete: Set[int] = set()
markers_to_update: Dict[int, float] = {}

for scene_row in scenes:
    scene_id: int = int(scene_row[0])
    title: Optional[str] = str(scene_row[1]) if scene_row[1] else None
    duration: float = float(scene_row[2]) if scene_row[2] else 0.0

    cur.execute("""
    SELECT m.id, m.title, m.seconds, m.end_seconds,
           GROUP_CONCAT(t.name)
    FROM scene_markers m
    LEFT JOIN scene_markers_tags mt ON m.id = mt.scene_marker_id
    LEFT JOIN tags t ON mt.tag_id = t.id
    WHERE m.scene_id = ?
    GROUP BY m.id
    """, (scene_id,))

    markers: List[Any] = cur.fetchall()
    if not markers:
        continue

    # Stats par scène
    markers_count: int = len(markers)
    unique_tags: Set[str] = set()
    scene_overlaps: int = 0
    scene_short: int = 0
    scene_long: int = 0
    scene_exact_dupes: int = 0
    scene_points: int = 0

    overlaps_list: List[Any] = []
    seen_ranges: Dict[Tuple[float, float], List[Set[str]]] = {}

    markers_sorted: List[Any] = sorted(markers, key=lambda x: x[2])

    for i in range(len(markers_sorted)):
        _row1 = markers_sorted[i]
        id1: int = int(_row1[0])
        m_title1: str = str(_row1[1]) if _row1[1] else ""
        start1: float = float(_row1[2])
        end1: float = float(_row1[3]) if _row1[3] else 0.0
        tags1_str: str = str(_row1[4]) if _row1[4] else ""

        tags1: Set[str] = set(tags1_str.split(",")) if tags1_str else set()
        if m_title1:
            tags1.add(m_title1)

        unique_tags.update(tags1)
        duration_marker: float = end1 - start1 if end1 else 0.0

        # Detection points sans durée
        if not end1 or end1 <= start1:
            scene_points += 1

        # Detection doublons exacts (même plage)
        time_range: Tuple[float, float] = (round(start1, 2), round(end1, 2) if end1 else 0.0)
        if time_range in seen_ranges:
            for prev_tags in seen_ranges[time_range]:
                common: Set[str] = tags1.intersection(prev_tags)
                if common:
                    scene_exact_dupes += len(common)
                    for t in common:
                        tag_stats[t]["exact_dupes"] += 1

        if time_range not in seen_ranges:
            seen_ranges[time_range] = []
        seen_ranges[time_range].append(tags1)

        # Stats tags
        for tag in tags1:
            tag_stats[tag]["total"] += 1
            if duration_marker > 0 and duration_marker < 3:
                tag_stats[tag]["short"] += 1
                scene_short += 1
            if duration and duration_marker > duration * 0.2:
                tag_stats[tag]["long"] += 1
                scene_long += 1

        # Check overlaps / Fusion / Redondance
        for j in range(i + 1, len(markers_sorted)):
            _row2 = markers_sorted[j]
            id2: int = int(_row2[0])
            m_title2: str = str(_row2[1]) if _row2[1] else ""
            start2: float = float(_row2[2])
            end2: float = float(_row2[3]) if _row2[3] else 0.0
            tags2_str: str = str(_row2[4]) if _row2[4] else ""

            tags2: Set[str] = set(tags2_str.split(",")) if tags2_str else set()
            if m_title2:
                tags2.add(m_title2)

            # --- LOGIQUE DE FUSION (GAP < 10s) ---
            if tags1 == tags2 and len(tags1) == 1:
                gap: float = start2 - (end1 if end1 else start1)
                if gap < 10:
                    new_end: float = max(end1 if end1 else start1, end2 if end2 else start2)
                    markers_to_update[id1] = new_end
                    markers_to_delete.add(id2)
                    end1 = new_end

            # Arrêt de la boucle j si on dépasse la zone de collision
            if start2 >= (end1 if end1 else start1):
                break

            # --- LOGIQUE DE CHEVAUCHEMENT / OVERLAP ---
            if start1 < (end2 if end2 else start2) and start2 < (end1 if end1 else start1):
                common2: Set[str] = tags1.intersection(tags2)
                if common2:
                    scene_overlaps += len(common2)
                    overlaps_list.append((id1, id2, start1, end1, start2, end2, list(common2)))
                    for tag in common2:
                        tag_stats[tag]["overlaps"] += 1

                    # --- LOGIQUE DE SUPPRESSION (CONTENU DANS) ---
                    if tags1 == tags2 and len(tags1) == 1:
                        # B est dans A
                        if start1 <= start2 and (end1 >= end2 if end1 and end2 else False):
                            markers_to_delete.add(id2)
                        # A est dans B
                        elif start2 <= start1 and (end2 >= end1 if end1 and end2 else False):
                            markers_to_delete.add(id1)

    scene_penalty: int = (scene_overlaps * 2) + scene_short + scene_long + (scene_exact_dupes * 5) + scene_points

    res: Dict[str, Any] = {
        "id": scene_id,
        "title": title,
        "duration": duration,
        "markers": markers_count,
        "points": scene_points,
        "tags": len(unique_tags),
        "overlaps": scene_overlaps,
        "short": scene_short,
        "long": scene_long,
        "exact_dupes": scene_exact_dupes,
        "penalty": scene_penalty
    }
    scene_results.append(res)
    scene_scores.append((title, scene_penalty))

    if scene_penalty > 0:
        display_title: str = title[:60] if title else "Sans titre"
        print(f"SCENE: {display_title}...")
        print(f"  - Durée: {duration}s | Marqueurs: {markers_count} (Points: {scene_points}) | Tags: {len(unique_tags)}")
        print(f"  - Problèmes: Overlaps={scene_overlaps}, Courts={scene_short}, Longs={scene_long}, Doublons Plage={scene_exact_dupes}")
        print(f"  - Score Pénalité: {scene_penalty}")
        print("-" * 30)

# Export CSV
with open(CSV_REPORT, mode='w', newline='', encoding='utf-8-sig') as f:
    if scene_results:
        writer = csv.DictWriter(f, fieldnames=list(scene_results[0].keys()))
        writer.writeheader()
        writer.writerows(scene_results)

print(f"\n[OK] Rapport détaillé exporté dans: {CSV_REPORT}")

# Classement scènes
print("\n=== TOP 20 SCENES PROBLEMATIQUES ===\n")
scene_scores.sort(key=lambda x: x[1], reverse=True)
top20: List[Tuple[Optional[str], int]] = scene_scores[:20]
for s in top20:
    if s[1] > 0:
        print(f"{s[1]:>4} pts | {s[0]}")

# Audit Tags
print("\n=== SCORE DE COHERENCE PAR TAG ===\n")
tag_audit: List[Tuple[str, int, Dict[str, int]]] = []
for tag, data in tag_stats.items():
    score: int = max(0, 100 - (data["overlaps"] * 3) - data["short"] - data["long"] - (data["exact_dupes"] * 10))
    tag_audit.append((tag, score, data))

tag_audit.sort(key=lambda x: x[1])
top_tags: List[Tuple[str, int, Dict[str, int]]] = tag_audit[:15]
for tag, score, data in top_tags:
    print(f"{tag[:20]:<20} | Score: {score:>3}/100 | {data['total']} total, {data['overlaps']} over, {data['exact_dupes']} dupes")

# --- SUPPRESSION / MISE A JOUR DES DOUBLONS ET FUSIONS ---
if markers_to_delete or markers_to_update:
    print(f"\n[!] ALERT: Travail de nettoyage identifié :")
    if markers_to_delete:
        print(f"  - {len(markers_to_delete)} marqueurs à SUPPRIMER (doublons/fusions)")
    if markers_to_update:
        print(f"  - {len(markers_to_update)} marqueurs à METTRE À JOUR (fusions de durée)")

    confirm: str = input(f"\nVoulez-vous appliquer ces changements à la base de données ? (oui/non) : ")

    if confirm.lower() in ['oui', 'y', 'yes', 'o']:
        try:
            # 1. Mises à jour (Fusions)
            for mid, new_end in markers_to_update.items():
                cur.execute("UPDATE scene_markers SET end_seconds = ? WHERE id = ?", (new_end, mid))

            # 2. Suppressions
            ids_to_del: List[Tuple[int]] = [(mid,) for mid in markers_to_delete]
            cur.executemany("DELETE FROM scene_markers WHERE id = ?", ids_to_del)
            cur.executemany("DELETE FROM scene_markers_tags WHERE scene_marker_id = ?", ids_to_del)

            conn.commit()
            print(f"[OK] Modifications appliquées avec succès.")
        except Exception as e:
            print(f"[ERREUR] Échec des modifications : {e}")
            conn.rollback()
    else:
        print("[INFO] Nettoyage annulé.")

conn.close()