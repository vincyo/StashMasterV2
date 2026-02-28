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
from scrapers import DataMerger


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
            'tattoos': 'Lower back'
        }
        tags = self.engine.generate_tags(metadata)
        
        self.assertIn('Latina', tags)
        self.assertIn('Blonde', tags)
        self.assertIn('Big Boobs', tags)
        self.assertIn('Pierced', tags)
        self.assertIn('Tattooed', tags)
        
        # Vérifier qu'il n'y a pas de doublons
        self.assertEqual(len(tags), len(set(tags)))


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
        
        confirmed, conflicts = self.merger.merge_data(sources)
        
        # Les données identiques doivent être confirmées
        self.assertIn('name', confirmed)
        self.assertEqual(confirmed['name']['value'], 'Bridgette B')
        self.assertEqual(confirmed['name']['count'], 2)
        
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
        
        confirmed, conflicts = self.merger.merge_data(sources)
        
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
        
        confirmed, conflicts = self.merger.merge_data(sources)
        
        # La valeur majoritaire doit être confirmée
        self.assertIn('ethnicity', confirmed)
        self.assertEqual(confirmed['ethnicity']['count'], 2)
    
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
        
        confirmed, conflicts = self.merger.merge_data(sources)
        
        # Les données uniques doivent être confirmées
        self.assertIn('birthdate', confirmed)
        self.assertEqual(confirmed['birthdate']['count'], 1)


class TestScrapers(unittest.TestCase):
    """Tests pour les scrapers (nécessitent une connexion internet)"""
    
    def test_iafd_url_detection(self):
        """Test de détection d'URL IAFD"""
        from scrapers import ScraperOrchestrator
        
        orchestrator = ScraperOrchestrator()
        url = "https://www.iafd.com/person.rme/perfid=bridgetteb/gender=f/bridgette-b.htm"
        
        scraper = orchestrator._get_scraper_for_url(url)
        self.assertIsNotNone(scraper)
        self.assertEqual(type(scraper).__name__, 'IAFDScraper')
    
    def test_freeones_url_detection(self):
        """Test de détection d'URL Freeones"""
        from scrapers import ScraperOrchestrator
        
        orchestrator = ScraperOrchestrator()
        url = "https://www.freeones.xxx/bridgette-b"
        
        scraper = orchestrator._get_scraper_for_url(url)
        self.assertIsNotNone(scraper)
        self.assertEqual(type(scraper).__name__, 'FreeonesScraper')


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
