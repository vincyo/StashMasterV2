#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test final avec force reload"""

import sys
# Force reload
if 'utils.normalizer' in sys.modules:
    del sys.modules['utils.normalizer']

from utils.normalizer import clean_awards_field, clean_award_text

test1 = "AVN Awards2015 Nominee: All-Girl Performer of the Year Nominee: Best Girl/Girl Sex Scene"
print("=== TEST clean_awards_field ===")
print(f"Input: {test1}")
result = clean_awards_field(test1)
print(f"Output:\n{result}")
print()

test2 = "AVN Awards2015 Nominee: All-Girl Performer of the Year"
print("=== TEST clean_award_text direct ===")
print(f"Input: {test2}")
result2 = clean_award_text(test2)
print(f"Output: {result2}")
