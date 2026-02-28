#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug clean_awards_field"""

import re

test = "AVN Awards2015 Nominee: All-Girl Performer of the Year Nominee: Best Girl/Girl Sex Scene"

# Simulation de clean_awards_field
text = test

print(f"Input: {text}")
print()

# Compter les status
status_count = len(re.findall(r'\b(Winner|Nominee):', text, re.I))
print(f"Nombre de Nominee/Winner: {status_count}")
print()

if status_count > 1:
    # Extraire préfixe
    prefix_match = re.match(r'^(.*?(?:AVN|XBIZ|XRCO|NightMoves|Spank Bank|PornHub)\s*Awards?\s*\d{4})', text, re.I)
    prefix = prefix_match.group(1).strip() if prefix_match else ""
    print(f"Préfixe détecté: '{prefix}'")
    print()
    
    # Split
    parts = re.split(r'\s+(Winner|Nominee):\s*', text)
    print(f"Parts après split: {parts}")
    print()
    
    if not prefix:
        prefix = parts[0].strip()
        print(f"Préfixe = parts[0]: '{prefix}'")
        print()
    
    # Traiter chaque award
    for i in range(1, len(parts), 2):
        if i+1 < len(parts):
            status_word = parts[i]
            category = parts[i+1].strip()
            reconstructed = f"{prefix} {status_word}: {category}"
            print(f"Award {i//2 + 1}:")
            print(f"  Statut: {status_word}")
            print(f"  Catégorie: {category}")
            print(f"  Reconstruit: {reconstructed}")
            print()
