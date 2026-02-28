#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires pour StashMaster V2
"""

import unittest
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stashmaster_unified import TagRulesEngine, AwardsCleaner
from services.scrapers import DataMerger, ScraperOrchestrator


class TestTagRulesEngine(unittest.TestCase):
    """Tests pour le moteur de génération de tags"""
    
    def setUp(self):
        self.engine = TagRulesEngine()
    
    def test_ethnicity_tags(self):
        """Test des tags d'ethnicité"""
        # Test Caucasian
        metadata = {'ethnicity': 'Caucasian'}
        tags = self.engine.generate_tags(metadata)
        self.assertIn('Caucasian', tags)
        self.assertNotIn('Asian', tags)  # ne doit pas matcher partiellement
        
        # Test Latina
        metadata = {'ethnicity': 'Cuban'}
        tags = self.engine.generate_tags(metadata)
        self.assertIn('Latina', tags)
        
        # Test Asian
        metadata = {'ethnicity': 'Asian'}
        tags = self.engine.generate_tags(metadata)
        self.assertIn('Asian', tags)
    
    def test_hair_color_tags(self):
        """Test des tags de couleur de cheveux"""
        # Test Blonde
        metadata = {'hair_color': 'Blonde'}
        tags = self.engine.generate_tags(metadata)
        self.assertIn('Blonde', tags)
        
        # Test Brunette
        metadata = {'hair_color': 'Brown'}
        tags = self.engine.generate_tags(metadata)
        self.assertIn('Brunette', tags)
        
        # Test Redhead
        metadata = {'hair_color': 'Red'}
        tags = self.engine.generate_tags(metadata)
        self.assertIn('Redhead', tags)
    
    def test_measurements_tags(self):
        """Test des tags basés sur les mesures"""
        # Test Big Boobs
        metadata = {'measurements': '38DD-27-34'}
        tags = self.engine.generate_tags(metadata)
        self.assertIn('Big Boobs', tags)
        
        # Test Small Boobs
        metadata = {'measurements': '32A-24-32'}
        tags = self.engine.generate_tags(metadata)
        self.assertIn('Small Boobs', tags)
    
    def test_piercings_tags(self):
        """Test des tags de piercings"""
        metadata = {'piercings': 'Navel, Tongue'}
        tags = self.engine.generate_tags(metadata)
        self.assertIn('Pierced', tags)
        
        # Pas de tag si "none"
        metadata = {'piercings': 'none'}
        tags = self.engine.generate_tags(metadata)
        self.assertNotIn('Pierced', tags)
    
    def test_tattoos_tags(self):
        """Test des tags de tattoos"""
        metadata = {'tattoos': 'Lower back, Right shoulder'}
        tags = self.engine.generate_tags(metadata)
        self.assertIn('Tattooed', tags)
        
        # Pas de tag si "none"
        metadata = {'tattoos': 'none'}
        tags = self.engine.generate_tags(metadata)
        self.assertNotIn('Tattooed', tags)
    
    def test_combined_tags(self):
        """Test de la génération de tags combinés"""
        metadata = {
            'ethnicity': 'Latina',
            'hair_color': 'Blonde',
            'measurements': '36DD-25-36',
            'piercings': 'Navel',
            'tattoos': 'Lower back',
            'trivia': 'She has a big butt and is also a bimbo.'
        }
        tags = self.engine.generate_tags(metadata)
        
        self.assertIn('Latina', tags)
        self.assertIn('Blonde', tags)
        self.assertIn('Big Boobs', tags)
        self.assertIn('Pierced', tags)
        self.assertIn('Tattooed', tags)
        self.assertIn('BigButt', tags)
        self.assertIn('Bimbo', tags)
        
        # Vérifier qu'il n'y a pas de doublons
        self.assertEqual(len(tags), len(set(tags)))


class TestBioGenerator(unittest.TestCase):
    """Tests pour générateur de bio (Google)"""

    def setUp(self):
        from services.bio_generator import BioGenerator
        self.bg = BioGenerator()

    def test_career_start_from_length(self):
        metadata = {'career_length': '2007-2025'}
        bio = self.bg.generate_google_bio('Test', metadata)
        self.assertIn('2007', bio)  # should mention 2007 for début

    def test_template_loaded(self):
        # create a temporary template file with a known pattern
        import os
        tmp_path = os.path.join(os.getcwd(), 'BioGooglemodele_template.txt')
        with open(tmp_path, 'w', encoding='utf8') as f:
            f.write('### {performer_name}\nIntro {birthdate}')
        try:
            bio = self.bg.generate_google_bio('X', {'birthdate': '01/01/2000'})
            self.assertTrue(bio.startswith('### X'))
            self.assertIn('Intro 01/01/2000', bio)
        finally:
            os.remove(tmp_path)

class TestAwardsCleaner(unittest.TestCase):
    """Tests pour le nettoyeur d'awards"""
    
    def setUp(self):
        self.cleaner = AwardsCleaner()
    
    def test_clean_simple_awards(self):
        """Test du nettoyage d'awards simples"""
        raw = """
        2012
        Winner: Unsung Starlet of the Year
        2013
        Nominee: Best Boobs
        """
        
        cleaned = self.cleaner.clean_awards(raw)
        
        # Vérifier la présence des années
        self.assertIn('2012', cleaned)
        self.assertIn('2013', cleaned)
        
        # Vérifier la présence des awards
        self.assertIn('Winner', cleaned)
        self.assertIn('Nominee', cleaned)
    
    def test_clean_awards_with_ceremony(self):
        """Test du nettoyage avec type de cérémonie"""
        raw = """
        AVN AWARDS
        2012
        Winner: Unsung Starlet of the Year
        XBIZ AWARDS
        2013
        Nominee: Best Performer
        """
        
        cleaned = self.cleaner.clean_awards(raw)
        
        # Vérifier la présence des cérémonies
        self.assertIn('AVN AWARDS', cleaned)
        self.assertIn('XBIZ AWARDS', cleaned)
    
    def test_clean_empty_awards(self):
        """Test avec des awards vides"""
        raw = ""
        cleaned = self.cleaner.clean_awards(raw)
        self.assertEqual(cleaned, "")


class TestURLUtils(unittest.TestCase):
    """Tests pour les utilitaires de gestion des URLs"""

    def test_clean_urls_list(self):
        from utils.url_utils import clean_urls_list
        raw = ["http://a.com", "", "http://a.com", " http://b.com ", "http://c.com", "http://c.com"]
        cleaned = clean_urls_list(raw)
        # blanks removed, duplicates collapsed and whitespace trimmed
        self.assertEqual(cleaned, ["http://a.com", "http://b.com", "http://c.com"])

    def test_merge_urls_by_domain(self):
        from utils.url_utils import merge_urls_by_domain
        base = ["http://iafd.com/foo", "http://example.com/page"]
        new = ["http://freeones.com/bar", "http://iafd.com/other", "http://unique.com"]
        merged = merge_urls_by_domain(base, new)
        # iafd should only appear once, base urls preserved first
        self.assertIn("http://iafd.com/foo", merged)
        self.assertNotIn("http://iafd.com/other", merged)
        # freeones should be present and order should place core domains first
        self.assertTrue(merged.index("http://freeones.com/bar") < merged.index("http://example.com/page"))
        # unique domain appended
        self.assertIn("http://unique.com", merged)


class TestDataMerger(unittest.TestCase):
    """Tests pour le fusionneur de données"""
    
    def setUp(self):
        self.merger = DataMerger()
    
    def test_merge_identical_data(self):
        """Test de fusion de données identiques"""
        sources = [
            {
                'source': 'iafd',
                'name': 'Bridgette B',
                'ethnicity': 'Caucasian'
            },
            {
                'source': 'freeones',
                'name': 'Bridgette B',
                'ethnicity': 'Caucasian'
            }
        ]
        
        result = self.merger.merge(sources)
        confirmed = result['confirmed']
        conflicts = result['conflicts']
        # Les données identiques doivent être confirmées
        self.assertIn('name', confirmed)
        self.assertEqual(confirmed['name'], 'Bridgette B')
        # Pas de conflits
        self.assertEqual(len(conflicts), 0)
    
    def test_merge_conflicting_data(self):
        """Test de fusion de données conflictuelles"""
        sources = [
            {
                'source': 'iafd',
                'hair_color': 'Blonde'
            },
            {
                'source': 'freeones',
                'hair_color': 'Brown'
            }
        ]
        
        result = self.merger.merge(sources)
        conflicts = result['conflicts']
        
        # Doit y avoir un conflit
        self.assertIn('hair_color', conflicts)
        self.assertEqual(len(conflicts['hair_color']), 2)
    
    def test_merge_majority_data(self):
        """Test de fusion avec valeur majoritaire"""
        sources = [
            {'source': 'iafd', 'ethnicity': 'Caucasian'},
            {'source': 'freeones', 'ethnicity': 'Caucasian'},
            {'source': 'thenude', 'ethnicity': 'White'}
        ]
        
        result = self.merger.merge(sources)
        confirmed = result['confirmed']
        # Le champ doit être présent dans les conflits et la valeur retenue doit être prioritaire
        self.assertIn('ethnicity', result['conflicts'])
        self.assertEqual(result['merged']['ethnicity'], 'Caucasian')
    
    def test_merge_unique_data(self):
        """Test de fusion de données uniques"""
        sources = [
            {
                'source': 'iafd',
                'name': 'Bridgette B',
                'birthdate': 'October 15, 1983'
            },
            {
                'source': 'freeones',
                'name': 'Bridgette B'
            }
        ]
        
        result = self.merger.merge(sources)
        confirmed = result['confirmed']
        # Les données uniques doivent apparaître dans le résultat fusionné
        self.assertIn('birthdate', result['merged'])
        self.assertEqual(result['merged']['birthdate'], 'October 15, 1983')

    def test_alias_dedup_case_insensitive(self):
        """Aliases avec casse différente ne doivent pas produire de doublons"""
        sources = [
            {'source': 'iafd', 'aliases': ['Bridgette B', 'bridgette b']},
            {'source': 'freeones', 'aliases': ['BRIDGETTE B']}
        ]
        result = self.merger.merge(sources)
        merged_aliases = result['merged'].get('aliases', [])
        # should keep only one version
        self.assertEqual(len(merged_aliases), 1)
        self.assertIn('Bridgette B', merged_aliases)


class TestBabepediaScraper(unittest.TestCase):
    """Tests spécifiques au scraper Babepedia"""

    def test_tattoos_parsing(self):
        html = '''<div class="info-item"><span class="label">Tattoos:</span> Cage thoracique droite (La Jalousie Est Une Maladie),<br>Derriere le cou (Spanish Doll),<br>Sous le nombril</div>'''
        from services.scrapers import BabepediaScraper
        from bs4 import BeautifulSoup
        scraper = BabepediaScraper()
        soup = BeautifulSoup(html, 'html.parser')
        result = scraper._parse(soup, 'https://babepedia.com')
        self.assertIn('tattoos', result)
        self.assertIn('Cage thoracique droite', result['tattoos'])
        self.assertIn('Derriere le cou', result['tattoos'])
        self.assertIn('Sous le nombril', result['tattoos'])

class TestDatabase(unittest.TestCase):
    """Tests pour le service de base de données SQLite"""

    def setUp(self):
        import tempfile
        from services.database import StashDatabase
        # utiliser un fichier réel pour que os.path.exists() soit vrai
        tmp = tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False)
        tmp.close()
        self.tmpfile = tmp.name
        self.db = StashDatabase(self.tmpfile)
        conn = self.db._get_connection()
        cur = conn.cursor()
        # créer schéma minimal
        cur.execute('CREATE TABLE performers (id TEXT PRIMARY KEY, name TEXT)')
        cur.execute('CREATE TABLE performer_custom_fields (performer_id TEXT, field TEXT, value TEXT)')
        conn.commit()

    def tearDown(self):
        # supprimer fichier temporaire
        try:
            os.remove(self.tmpfile)
        except Exception:
            pass

    def test_save_performer_with_custom_fields(self):
        updates = {
            'name': 'Alice',
            'trivia_fr': 'Je suis une star',
            'tattoos_fr': 'Tatouage 1',
            'piercings_fr': 'Piercing 1',
        }
        # ajouter performer basic
        conn = self.db._get_connection()
        conn.cursor().execute("INSERT INTO performers (id,name) VALUES (?,?)", ('123','Alice'))
        conn.commit()
        # appeler méthode
        self.db.save_performer_metadata('123', updates)
        cur = conn.cursor()
        cur.execute("SELECT field,value FROM performer_custom_fields WHERE performer_id=?", ('123',))
        rows = {r['field']: r['value'] for r in cur.fetchall()}
        self.assertEqual(rows.get('Trivia FR'), 'Je suis une star')
        self.assertEqual(rows.get('Tattoos FR'), 'Tatouage 1')
        self.assertEqual(rows.get('Piercings FR'), 'Piercing 1')

    def test_thread_local_connection(self):
        """Chaque thread doit obtenir sa propre connexion, non fermée par les autres"""
        import threading
        conns = []
        def worker():
            c = self.db._get_connection()
            conns.append(c)
        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads: t.start()
        for t in threads: t.join()
        # les objets connexion doivent être distincts
        ids = [id(c) for c in conns]
        self.assertEqual(len(set(ids)), len(ids))

class TestScrapers(unittest.TestCase):
    """Tests pour les scrapers (nécessitent une connexion internet)"""
    
    def test_iafd_url_detection(self):
        """Test de détection d'URL IAFD"""
        from services.scrapers import ScraperOrchestrator
        
        orchestrator = ScraperOrchestrator()
        url = "https://www.iafd.com/person.rme/perfid=bridgetteb/gender=f/bridgette-b.htm"
        
        scraper = orchestrator.detect_source(url)
        self.assertIsNotNone(scraper)
        self.assertEqual(type(scraper).__name__, 'IAFDScraper')
    
    def test_freeones_url_detection(self):
        """Test de détection d'URL Freeones"""
        from services.scrapers import ScraperOrchestrator
        
        orchestrator = ScraperOrchestrator()
        url = "https://www.freeones.xxx/bridgette-b"
        
        scraper = orchestrator.detect_source(url)
        self.assertIsNotNone(scraper)
        self.assertEqual(type(scraper).__name__, 'FreeOnesScraper')


def run_tests():
    """Lance tous les tests"""
    # Créer une suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter tous les tests
    suite.addTests(loader.loadTestsFromTestCase(TestTagRulesEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestAwardsCleaner))
    suite.addTests(loader.loadTestsFromTestCase(TestDataMerger))
    suite.addTests(loader.loadTestsFromTestCase(TestScrapers))
    
    # Lancer les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Retourner le statut
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
