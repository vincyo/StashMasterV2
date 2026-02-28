#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test rapide Gemini"""

from services.bio_generator import BioGenerator

bio_gen = BioGenerator()

# Test simple
test = "AVN Awards2015 Nominee: Best Scene Nominee: Best Actress"

print("Appel Gemini (timeout 30s)...")
try:
    result = bio_gen.clean_awards_with_gemini(test)
    print(f"Résultat:\n{result}")
except Exception as e:
    print(f"ERREUR: {e}")
    import traceback
    traceback.print_exc()
