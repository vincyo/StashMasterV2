#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug complet clean_awards_field"""

import re

# Copie de clean_award_text depuis normalizer.py
def clean_award_text_copy(raw_text: str) -> str:
    if not raw_text or not isinstance(raw_text, str):
        return ""
    
    text = raw_text.strip()
    text = re.sub(r'([a-zA-Z])(\d{4})', r'\1 \2', text)
    text = re.sub(r'Ã[ƒÆâ€šÂ¢]+[^A-Za-z0-9\s]*', '', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'\s+', ' ', text).strip()
    
    year_match = re.search(r'\b(19|20)\d{2}\b', text)
    year = year_match.group(0) if year_match else ""
    
    org = None
    org_patterns = [
        (r'\b(AVN)\s*Awards?\b', 'AVN'),
        (r'\b(XBIZ)\s*Awards?\b', 'XBIZ'),
        (r'\b(XRCO)\s*Awards?\b', 'XRCO'),
        (r'\b(NightMoves|Nightmoves)\s*(?:Awards?|Fan Awards?)?\b', 'NightMoves'),
        (r'\b(Spank\s*Bank)\s*(?:Awards?|Technical Awards?)?\b', 'Spank Bank'),
        (r'\b(Porn\s*Hub|PornHub)\s*Awards?\b', 'PornHub'),
        (r'\b(FAME)\s*Awards?\b', 'FAME')
    ]
    
    for pattern, org_name in org_patterns:
        if re.search(pattern, text, re.I):
            org = org_name
            text = re.sub(pattern, '', text, flags=re.I)
            break
    
    if org:
        org = f"{org} Award"
    else:
        org = "Award"
    
    status = None
    if re.search(r'\bWinner\s*:', text, re.I):
        status = "Winner"
        text = re.sub(r'\bWinner\s*:\s*', '', text, flags=re.I)
    elif re.search(r'\bNominee\s*:', text, re.I):
        status = "Nominee"
        text = re.sub(r'\bNominee\s*:\s*', '', text, flags=re.I)
    
    if year:
        text = re.sub(r'\b' + re.escape(year) + r'\b', '', text)
    text = re.sub(r'\bAward\s*:\s*', '', text, flags=re.I)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.lstrip('- :').strip()
    
    if not text or len(text) < 5:
        return ""
    
    if status:
        result = f"{year} {org} - {text} [{status}]" if year else f"{org} - {text} [{status}]"
    else:
        result = f"{year} {org} - {text}" if year else f"{org} - {text}"
    
    return result.strip()


# Test avec input clean_awards_field
test_input = "AVN Awards2015 Nominee: All-Girl Performer of the Year Nominee: Best Girl/Girl Sex Scene"

# Simulation de clean_awards_field
text = test_input

# Pré-traitement (copié depuis le code actuel)
print("=== PRÉ-TRAITEMENT ===")
print(f"Input original: {text}")

# Pas de ponctuation forte dans test_input donc pas de split
status_count = len(re.findall(r'\b(Winner|Nominee):', text, re.I))
print(f"Status count: {status_count}")

if status_count > 1:
    # Extraire préfixe
    prefix_match = re.match(r'^(.*?(?:AVN|XBIZ|XRCO|NightMoves|Spank Bank|PornHub)\s*Awards?\s*\d{4})', text, re.I)
    prefix = prefix_match.group(1).strip() if prefix_match else ""
    print(f"Préfixe: '{prefix}'")
    
    parts = re.split(r'\s+(Winner|Nominee):\s*', text)
    print(f"Parts: {parts}")
    
    if not prefix:
        prefix = parts[0].strip()
    
    # Traiter chaque award
    for i in range(1, len(parts), 2):
        if i+1 < len(parts):
            status_word = parts[i]
            category = parts[i+1].strip()
            
            reconstructed = f"{prefix} {status_word}: {category}"
            print(f"\n=== AWARD {i//2 + 1} ===")
            print(f"Reconstructed: {reconstructed}")
            
            cleaned = clean_award_text_copy(reconstructed)
            print(f"Cleaned: {cleaned}")
