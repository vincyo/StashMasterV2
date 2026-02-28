#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test du nettoyage des awards"""

from utils.normalizer import clean_awards_field, clean_award_text

# Test 1: Awards IAFD collés
test1 = "AVN Awards2015 Nominee: All-Girl Performer of the Year Nominee: Best Girl/Girl Sex Scene, Masterpiece (2013)"
print("=== TEST 1: Awards collés ===")
print(f"INPUT: {test1}")
print(f"OUTPUT:\n{clean_awards_field(test1)}")
print()

# Test 2: Award simple
test2 = "AVN Awards 2015 Nominee: All-Girl Performer of the Year"
print("=== TEST 2: Award simple ===")
print(f"INPUT: {test2}")
print(f"OUTPUT: {clean_award_text(test2)}")
print()

# Test 3: Texte mixte avec prose
test3 = """2015 2016 AVN Award: Best Boy/Girl Sex Scene w/ Flash Brown (Black & White 4)
2015, and she has been nominated for multiple other awards, including Best Supporting Actress at the XBIZ Awards in
2016 AVN Award for Best Solo/Tease Performance for Black & White 4, the
AVN Awards2015 Nominee: All-Girl Performer of the Year Nominee: Best Girl/Girl Sex Scene"""
print("=== TEST 3: Texte mixte ===")
print(f"INPUT: {test3[:100]}...")
result3 = clean_awards_field(test3)
print(f"OUTPUT ({len(result3.splitlines())} lignes):\n{result3}")
