#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test du nettoyage d'awards par Gemini"""

from services.bio_generator import BioGenerator

bio_gen = BioGenerator()

# Test avec awards mal formatés
test_awards = """2015 2016 AVN Award: Best Boy/Girl Sex Scene w/ Flash Brown (Black & White 4)
2015, and she has been nominated for multiple other awards, including Best Supporting Actress at the XBIZ Awards in
2016 AVN Award for Best Boy/Girl Sex Scene and Best Solo/Tease Performance for Black & White 4, the
AVN Awards2015 Nominee: All-Girl Performer of the Year Nominee: Best Girl/Girl Sex Scene, Masterpiece (2013)Nominee: Fan Award: Best Boobs2016 Nominee: Best All-Girl Group Sex Scene"""

print("=== TEST GEMINI AWARDS CLEANER ===")
print(f"Input (premiers 200 chars): {test_awards[:200]}...")
print()
print("Appel Gemini en cours...")

result = bio_gen.clean_awards_with_gemini(test_awards)

print("\n=== RÉSULTAT ===")
print(result)
print(f"\nNombre de lignes: {len([l for l in result.splitlines() if l.strip()])}")
