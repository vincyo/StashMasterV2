# Utilitaire pour injecter des customfields performer

def inject_customfields(db, performer_id, customfields):
    """
    Injecte une liste de customfields pour un performer.
    customfields = [
        {"type": "award", "value": "..."},
        {"type": "trivia", "value": "..."},
        {"type": "tattoo", "value": "..."},
        {"type": "piercing", "value": "..."},
    ]
    """
    cur = db.conn.cursor()
    for cf in customfields:
        cur.execute(
            "INSERT INTO performer_customfields (performer_id, type, value) VALUES (?, ?, ?)",
            (performer_id, cf["type"], cf["value"])
        )
    db.conn.commit()
