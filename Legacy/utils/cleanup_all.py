from __future__ import annotations
import sqlite3
from collections import defaultdict, OrderedDict
from typing import Dict, List, Set, Tuple, Optional, Any

DB_PATH = r"H:\Stash\stash-go.sqlite"

# ============================================================
# CONFIGURATION DU NETTOYAGE
# ============================================================

# Durée minimale globale : tout marqueur <= cette valeur (s) sera supprimé
# Mettre à 0.0 pour désactiver.
GLOBAL_MIN_DURATION: float = 60.0

# Règles ciblées par tag (indépendantes de la règle globale)
# Format : (tag, durée_max_ou_None_pour_tous)
TARGETED_DELETE_RULES: List[Tuple[str, Optional[float]]] = [
    ("69", None),  # Supprimer TOUS les marqueurs "69" (quelle que soit la durée)
]

# ============================================================
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("=== MÉNAGE COMPLET DES MARQUEURS ===\n")

# ---- 1. Chargement de tous les marqueurs ----
cur.execute("""
    SELECT m.id, m.seconds, m.end_seconds, GROUP_CONCAT(t.name), m.title
    FROM scene_markers m
    LEFT JOIN scene_markers_tags mt ON m.id = mt.scene_marker_id
    LEFT JOIN tags t ON mt.tag_id = t.id
    GROUP BY m.id
    ORDER BY m.scene_id, m.seconds
""")
all_markers: List[Any] = cur.fetchall()

# Construire un dict id -> marker data
marker_data: Dict[int, Dict[str, Any]] = {}
for row in all_markers:
    mid: int = int(row[0])
    start: float = float(row[1])
    end: float = float(row[2]) if row[2] else 0.0
    tags_str: str = str(row[3]) if row[3] else ""
    title: str = str(row[4]) if row[4] else ""
    tags: Set[str] = set(tags_str.split(",")) if tags_str else set()
    if title:
        tags.add(title)
    marker_data[mid] = {"start": start, "end": end, "tags": tags}

# ---- 2. Grouper les IDs par scène (ordonnés par seconds) ----
cur.execute("SELECT scene_id, id FROM scene_markers ORDER BY scene_id, seconds")
scene_groups: Dict[int, List[int]] = OrderedDict()
for row in cur.fetchall():
    sid: int = int(row[0])
    mid: int = int(row[1])
    if sid not in scene_groups:
        scene_groups[sid] = []
    scene_groups[sid].append(mid)

# ---- 3. Règles FUSION + CONTENANCE ----
markers_to_delete: Set[int] = set()
markers_to_update: Dict[int, float] = {}
fusions_count: int = 0
contained_count: int = 0

for sid, mids in scene_groups.items():
    for i in range(len(mids)):
        id1: int = mids[i]
        if id1 not in marker_data:
            continue
        d1 = marker_data[id1]
        start1: float = d1["start"]
        end1: float = d1["end"]
        tags1: Set[str] = d1["tags"]

        for j in range(i + 1, len(mids)):
            id2: int = mids[j]
            if id2 not in marker_data or id2 in markers_to_delete:
                continue
            d2 = marker_data[id2]
            start2: float = d2["start"]
            end2: float = d2["end"]
            tags2: Set[str] = d2["tags"]

            # Doit avoir le même tag unique
            if tags1 != tags2 or len(tags1) != 1:
                if start2 >= end1:
                    break
                continue

            gap: float = start2 - end1

            # Règle FUSION : gap < 10s
            if gap < 10:
                new_end: float = max(end1, end2 if end2 else start2)
                markers_to_update[id1] = new_end
                markers_to_delete.add(id2)
                end1 = new_end
                d1["end"] = new_end
                fusions_count += 1
                continue

            # Arrêt si hors zone
            if start2 >= end1:
                break

            # Règle CONTENANCE
            if start1 < end2 and start2 < end1:
                if start1 <= start2 and end1 >= end2 and end2 > 0:
                    markers_to_delete.add(id2)
                    contained_count += 1
                elif start2 <= start1 and end2 >= end1 and end1 > 0:
                    markers_to_delete.add(id1)
                    contained_count += 1

# ---- 4. Règle GLOBALE : durée minimale ----
global_short_count: int = 0
if GLOBAL_MIN_DURATION > 0:
    for mid, d in marker_data.items():
        if mid in markers_to_delete:
            continue
        m_dur: float = d["end"] - d["start"] if d["end"] > d["start"] else 0.0
        if m_dur <= GLOBAL_MIN_DURATION:
            markers_to_delete.add(mid)
            global_short_count += 1
            # Annuler la fusion si ce marqueur était source d'une mise à jour
            if mid in markers_to_update:
                del markers_to_update[mid]

# ---- 5. Règles CIBLÉES par tag ----
targeted_deletes: Dict[str, int] = {}
for mid, d in marker_data.items():
    if mid in markers_to_delete:
        continue
    m_dur = d["end"] - d["start"] if d["end"] > d["start"] else 0.0
    m_tags: Set[str] = d["tags"]
    for tag_rule, max_dur in TARGETED_DELETE_RULES:
        if tag_rule in m_tags:
            if max_dur is None or m_dur <= max_dur:
                markers_to_delete.add(mid)
                rule_key: str = f"{tag_rule} (<= {max_dur}s)" if max_dur else tag_rule
                targeted_deletes[rule_key] = targeted_deletes.get(rule_key, 0) + 1
                break

# ---- 6. Bilan ----
total_updates: int = len(markers_to_update)
total_deletes: int = len(markers_to_delete)

print(f"Bilan du nettoyage identifié :\n")
print(f"  [FUSION]     {fusions_count} marqueurs fusionnés")
print(f"  [CONTENANCE] {contained_count} marqueurs contenus dans un autre")
if GLOBAL_MIN_DURATION > 0:
    print(f"  [DURÉE ≤{int(GLOBAL_MIN_DURATION)}s] {global_short_count} marqueurs trop courts (toutes catégories)")
for rule, count in targeted_deletes.items():
    print(f"  [CIBLÉ]      {count} marqueurs '{rule}'")
print(f"\n  TOTAL : {total_updates} UPDATE(s), {total_deletes} DELETE(s)\n")

if not markers_to_delete and not markers_to_update:
    print("[OK] Aucune action nécessaire. Base déjà propre !")
    conn.close()
    exit()

confirm: str = input("Voulez-vous appliquer tous ces changements ? (OUI/non) : ")

if confirm == "OUI":
    try:
        for mid, new_end in markers_to_update.items():
            cur.execute("UPDATE scene_markers SET end_seconds = ? WHERE id = ?", (new_end, mid))

        ids_to_del: List[Tuple[int]] = [(mid,) for mid in markers_to_delete]
        cur.executemany("DELETE FROM scene_markers_tags WHERE scene_marker_id = ?", ids_to_del)
        cur.executemany("DELETE FROM scene_markers WHERE id = ?", ids_to_del)

        conn.commit()
        print(f"\n[OK] {total_updates} mise(s) à jour et {total_deletes} suppression(s) appliquées avec succès.")
    except Exception as e:
        print(f"\n[ERREUR] Échec : {e}")
        conn.rollback()
else:
    print("[INFO] Nettoyage annulé.")

conn.close()
