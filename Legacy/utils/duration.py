"""
Utilitaire de conversion de durées pour les DVDs.
Gère tous les formats rencontrés dans les sources DVD.
"""
import re
from typing import Optional


def parse_duration_to_seconds(raw: str) -> Optional[int]:
    """
    Convertit n'importe quelle représentation de durée en secondes (INTEGER).

    Formats supportés :
        '[01:55:32]'  → data18
        '01:55:00'    → adultdvdempire (après conversion interne)
        '115'         → iafd (minutes brutes)
        '240 minutes' → jeedoo
        '1 hrs. 55 mins.' → adultdvdempire brut
    """
    if not raw:
        return None
    raw = str(raw).strip().strip("[]")

    # HH:MM:SS
    m = re.match(r'^(\d+):(\d{2}):(\d{2})$', raw)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))

    # MM:SS
    m = re.match(r'^(\d+):(\d{2})$', raw)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))

    # "1 hrs. 55 mins." ou "1 hr 55 min"
    m = re.search(r'(\d+)\s*hr', raw, re.I)
    if m:
        hours = int(m.group(1))
        mins_m = re.search(r'(\d+)\s*min', raw, re.I)
        mins = int(mins_m.group(1)) if mins_m else 0
        return hours * 3600 + mins * 60

    # "240 minutes" ou "240 mins"
    m = re.search(r'(\d+)\s*min', raw, re.I)
    if m:
        return int(m.group(1)) * 60

    # Nombre seul → considéré comme minutes (iafd)
    m = re.match(r'^(\d+)$', raw)
    if m:
        return int(m.group(1)) * 60

    return None


def format_duration(seconds: int) -> str:
    """Formate des secondes en HH:MM:SS pour affichage."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
