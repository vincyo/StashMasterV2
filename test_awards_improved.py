"""Test des améliorations du nettoyage d'awards"""
import sys
sys.path.insert(0, 'f:\\StashMasterV2')

from utils.normalizer import clean_awards_field

# Exemples problématiques de la sortie utilisateur
test_cases = [
    "2016 AVN Award - for Best Boy/Girl Sex Scene and Best Solo/Tease Performance for Black & White 4, the",
    "2019 AVN Award - for Female Performer of the Year, and the",
    "Award - Everest The Workout Warrior [Winner]",
    "2017 Award - Most Talented Tongue (Best Girl/Girl Kisser of the Year)Snapchat Sweetheart of the Year [Nominee]",
    "2020 Award - Most Talented Tongue (Best Girl/Girl Kisser of the Year)Sage of 69Nominee: The Sexiest Woman Alive [Nominee]",
    "2016 Award - Nominee: Best All-Girl Group Sex Scene, Business of Women(2015)Nominee: Best All-Girl Group Sex Scene, Me and My Girlfriend 10(2015)Best Boy/Girl Sex Scene, Black and White 4(2015)",
]

print("=" * 80)
print("TEST DES AMÉLIORATIONS")
print("=" * 80)

for i, test_input in enumerate(test_cases, 1):
    print(f"\n[TEST {i}]")
    print(f"Entrée : {test_input[:100]}...")
    result = clean_awards_field(test_input)
    print(f"Sortie :")
    for line in result.split('\n'):
        print(f"  - {line}")
    print()
