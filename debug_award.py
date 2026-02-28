#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TestDebugAward simple"""

import re

def clean_award_text_debug(raw_text: str) -> str:
    """Version debug avec prints"""
    if not raw_text or not isinstance(raw_text, str):
        return ""
    
    text = raw_text.strip()
    print(f"STEP 0 - Input: {text}")
    
    # 1. Séparer les blocs collés
    text = re.sub(r'([a-zA-Z])(\d{4})', r'\1 \2', text)
    print(f"STEP 1 - Après séparation année: {text}")
    
    # 2. Nettoyage UTF-8
    text = re.sub(r'Ã[ƒÆâ€šÂ¢]+[^A-Za-z0-9\s]*', '', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # 3. Normalisation espaces
    text = re.sub(r'\s+', ' ', text).strip()
    print(f"STEP 3 - Après nettoyage: {text}")
    
    # 4. Extraction année
    year_match = re.search(r'\b(19|20)\d{2}\b', text)
    year = year_match.group(0) if year_match else ""
    print(f"STEP 4 - Année détectée: {year}")
    
    # 5. Extraction organisation
    org = None
    org_patterns = [
        (r'\b(AVN)\s*Awards?\b', 'AVN'),
        (r'\b(XBIZ)\s*Awards?\b', 'XBIZ'),
    ]
    
    for pattern, org_name in org_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            print(f"STEP 5 - Pattern {pattern} matché: {m.group(0)}")
            org = org_name
            text = re.sub(pattern, '', text, flags=re.I)
            break
    
    if org:
        org = f"{org} Award"
    else:
        org = "Award"
    print(f"STEP 5 - Organisation: {org}")
    print(f"STEP 5 - Texte après org: {text}")
    
    # 6. Détecter statut
    status = None
    if re.search(r'\bWinner\s*:', text, re.I):
        status = "Winner"
        text = re.sub(r'\bWinner\s*:\s*', '', text, flags=re.I)
    elif re.search(r'\bNominee\s*:', text, re.I):
        status = "Nominee"
        text = re.sub(r'\bNominee\s*:\s*', '', text, flags=re.I)
    print(f"STEP 6 - Statut: {status}")
    print(f"STEP 6 - Texte après statut: {text}")
    
    # 7. Nettoyer année du texte
    if year:
        text = re.sub(r'\b' + re.escape(year) + r'\b', '', text)
    text = re.sub(r'\bAward\s*:\s*', '', text, flags=re.I)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.lstrip('- :').strip()
    print(f"STEP 7 - Texte final catégorie: {text}")
    
    # 8. Validation
    if not text or len(text) < 5:
        print("STEP 8 - Catégorie trop courte, ignoré")
        return ""
    
    # 9. Résultat
    if status:
        result = f"{year} {org} - {text} [{status}]" if year else f"{org} - {text} [{status}]"
    else:
        result = f"{year} {org} - {text}" if year else f"{org} - {text}"
    
    print(f"STEP 9 - Résultat final: {result}")
    return result.strip()

# Test
test = "AVN Awards2015 Nominee: All-Girl Performer of the Year"
print("="*60)
result = clean_award_text_debug(test)
print("="*60)
print(f"Résultat: {result}")
