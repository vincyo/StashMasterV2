# Utilitaires pour la normalisation et la propagation des tags de métadonnées

COLORED_HAIR_TAGS = {
    "Blue": "BlueHair",
    "Green": "GreenHair",
    "Grey": "GreyHair",
    "Pink": "PinkHair",
    "Purple": "PurpleHair",
    "Red": "RedHair",
    "White": "WhiteHair"
}
NATURAL_HAIR_TAGS = {
    "Black": "BlackHair",
    "Blond": "BlondHair",
    "Brown": "BrownHair",
    "Redhead": "RedHead"
}
HAIR_TAGS = {**COLORED_HAIR_TAGS, **NATURAL_HAIR_TAGS}

NATIONALITY_TAGS = {
    "Cubaine": "Cuban",
    "Dominicaine": "Dominican",
    "Colombienne": "Colombian",
    "Thai": "Thai",
    "Vénézuélienne": "Venezuelan",
    "Brasilian": "Brazilian",
    "Mexicaine": "Mexican"
}

ETHNY_TAGS = {
    "Asian": "Asian",
    "Ebony": "Ebony",
    "Latina": "Latina"
}


def normalize_tag(value):
    """Normalise une valeur de métadonnée pour correspondre à un tag."""
    v = value.strip().capitalize()
    return v


def meta_to_tags(meta):
    """Transforme les métadonnées en tags selon les règles."""
    tags = []
    # Couleur de cheveux
    hair = meta.get("Hair Color", "")
    for color in [c.strip() for c in hair.split(",") if c.strip()]:
        tag = HAIR_TAGS.get(normalize_tag(color))
        if tag:
            tags.append(tag)
    # Nationalité
    nat = meta.get("Country", "")
    tag = NATIONALITY_TAGS.get(normalize_tag(nat))
    if tag:
        tags.append(tag)
    # Ethnie
    ethny = meta.get("Ethnicity", "")
    tag = ETHNY_TAGS.get(normalize_tag(ethny))
    if tag:
        tags.append(tag)
    # MILF
    import datetime
    birthdate = meta.get("Birthdate", "")
    if birthdate:
        try:
            birth = datetime.datetime.strptime(birthdate, "%Y-%m-%d")
            age = (datetime.datetime.now() - birth).days // 365
            if age >= 35:
                tags.append("MILF")
        except Exception:
            pass
    # BigTits
    measurements = meta.get("Measurements", "")
    bust = None
    hips = None
    if measurements:
        # Format attendu: 36-24-38
        parts = [p.strip() for p in measurements.split("-")]
        if len(parts) == 3:
            try:
                bust = int(parts[0])
            except Exception:
                pass
            try:
                hips = int(parts[2])
            except Exception:
                pass
    # BigTits
    if bust is not None and bust >= 36:
        tags.append("BigTits")
    # BigButt
    if hips is not None and hips >= 38:
        tags.append("BigButt")
    # Bimbo
    if "BigTits" in tags and "BigButt" in tags:
        tags.append("Bimbo")
    return tags


def propagate_tags_to_scenes(db, performer_id, tags):
    """Ajoute/supprime les tags de couleur de cheveux, nationalité, ethnie sur toutes les scènes de l'artiste."""
    # Récupérer toutes les scènes de l'artiste
    cur = db.conn.cursor()
    cur.execute("SELECT scene_id FROM performers_scenes WHERE performer_id=?", (performer_id,))
    scene_ids = [r[0] for r in cur.fetchall()]
    for scene_id in scene_ids:
        # Récupérer les tags actuels
        cur.execute("SELECT t.name FROM tags t JOIN scenes_tags st ON st.tag_id = t.id WHERE st.scene_id=?", (scene_id,))
        scene_tags = [r[0] for r in cur.fetchall()]
        # Ajouter les tags manquants
        for tag in tags:
            if tag not in scene_tags:
                # Ajout du tag à la scène
                cur.execute("SELECT id FROM tags WHERE name=?", (tag,))
                row = cur.fetchone()
                if row:
                    tag_id = row[0]
                    cur.execute("INSERT INTO scenes_tags (scene_id, tag_id) VALUES (?,?)", (scene_id, tag_id))
        # Supprimer les tags erronés
        valid_tags = set(HAIR_TAGS.values()) | set(NATIONALITY_TAGS.values()) | set(ETHNY_TAGS.values()) | {"MILF", "BigTits", "BigButt", "Bimbo"}
        for tag in scene_tags:
            if tag in valid_tags and tag not in tags:
                cur.execute("SELECT id FROM tags WHERE name=?", (tag,))
                row = cur.fetchone()
                if row:
                    tag_id = row[0]
                    cur.execute("DELETE FROM scenes_tags WHERE scene_id=? AND tag_id=?", (scene_id, tag_id))
    db.conn.commit()
