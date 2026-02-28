"""
Utilitaire partagé pour parser les tattoos/piercings depuis n'importe quelle source.
Gère les formats structurés ("wrist (tribal)") et flat ("multiple tattoos").
"""
import re


def parse_body_art(raw_text: str) -> list[dict]:
    """
    Parse un texte brut de tattoos/piercings en liste structurée.
    
    Retourne: [{"position": str, "description": str | None}]
    
    Exemples d'entrée:
        "left wrist (tribal); right arm (sleeve)" → 2 entrées structurées
        "Yes - multiple tattoos" → 1 entrée flat
        "None" → []
    """
    items = []
    if not raw_text or raw_text.strip().lower() in ('unknown', 'no', 'n/a', 'none', ''):
        return items

    # Retirer le préfixe "Yes - " ou "Yes," courant
    cleaned = re.sub(r'^Yes\s*[-,]?\s*', '', raw_text, flags=re.I).strip()
    if not cleaned:
        return items

    # Séparer par point-virgule d'abord (plus fiable), sinon virgule
    if ';' in cleaned:
        parts = cleaned.split(';')
    else:
        parts = cleaned.split(',')

    for part in parts:
        part = part.strip()
        if not part or part.lower() in ('unknown', 'no', 'n/a', 'none'):
            continue

        # Tenter de parser "position (description)"
        m = re.match(r'(.+?)\s*\((.+?)\)\s*$', part)
        if m:
            items.append({
                "position": m.group(1).strip(),
                "description": m.group(2).strip()
            })
        else:
            # Tenter "position - description" ou "position : description"
            m2 = re.match(r'(.+?)\s*[-–:]\s+(.+)', part)
            if m2 and len(m2.group(1)) < 30:
                items.append({
                    "position": m2.group(1).strip(),
                    "description": m2.group(2).strip()
                })
            else:
                items.append({
                    "position": part,
                    "description": None
                })

    return items
