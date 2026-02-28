import sys
import os

# Ajouter le dossier courant au path pour les imports
sys.path.append(os.getcwd())

try:
    from utils.tag_engine import TagRulesEngine
    from services.bio_generator import BioGenerator
    from services.database import StashDatabase
    print("✅ Imports réussis.")
except ImportError as e:
    print(f"❌ Erreur d'import : {e}")
    sys.exit(1)

def test_tags():
    print("\n--- Test Moteur de Tags ---")
    # Test Cas 1: Performer Colombienne avec gros seins
    meta1 = {
        'ethnicity': 'Colombian Latina',
        'country': 'Colombia',
        'measurements': '36DDD',
        'hair_color': 'Blonde',
        'career_start': '2010-01-01',
        'trivia': 'She has a big butt.'
    }
    tags1 = TagRulesEngine.generate_tags(meta1)
    print(f"Meta 1 (Colombian/36DDD/Blond/2010) -> {tags1}")
    
    # Vérifications attendues: Colombian, Latina, BigBoobs, BlondHair, MILF, BigButt
    # Interdits: Caucasian, Small Boobs, Pierced, Tattooed
    
    # Test Cas 2: Caucasian (devrait être filtré)
    meta2 = {
        'ethnicity': 'Caucasian',
        'piercings': 'Yes',
        'tattoos': 'Yes',
        'measurements': '32A'
    }
    tags2 = TagRulesEngine.generate_tags(meta2)
    print(f"Meta 2 (Caucasian/Pierced/Tattooed/32A) -> {tags2}")
    # Devrait être vide ou ne contenir que des tags autorisés s'il y en avait d'autres.

def test_translation():
    print("\n--- Test Traduction Hybride ---")
    bg = BioGenerator()
    
    # Test simple (Google devrait suffire)
    text = "She is a very popular actress from Medellin."
    translated = bg.translate_hybrid(text, "Trivia")
    print(f"Original: {text}")
    print(f"Traduit: {translated}")

def main():
    test_tags()
    test_translation()

if __name__ == "__main__":
    main()
