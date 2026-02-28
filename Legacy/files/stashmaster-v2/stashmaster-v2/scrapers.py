#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrapers pour différentes sources de données
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class ScraperBase:
    """Classe de base pour tous les scrapers"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_page(self, url: str, timeout: int = 10) -> Optional[BeautifulSoup]:
        """Récupère et parse une page web"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Erreur lors du scraping de {url}: {e}")
            return None


class IAFDScraper(ScraperBase):
    """Scraper pour IAFD.com"""
    
    def scrape_performer(self, url: str) -> Dict:
        """Scrape les données d'un performer depuis IAFD"""
        soup = self.get_page(url)
        if not soup:
            return {}
        
        data = {
            'source': 'iafd',
            'url': url
        }
        
        try:
            # Nom
            name_elem = soup.find('h1')
            if name_elem:
                data['name'] = name_elem.text.strip()
            
            # Informations de base
            info_box = soup.find('div', class_='biodata')
            if info_box:
                rows = info_box.find_all('p')
                for row in rows:
                    text = row.text.strip()
                    
                    # Date de naissance
                    if 'Born' in text or 'Birthday' in text:
                        date_match = re.search(r'(\w+ \d+, \d{4})', text)
                        if date_match:
                            data['birthdate'] = date_match.group(1)
                    
                    # Lieu de naissance
                    if 'Birthplace' in text:
                        place = text.split('Birthplace:')[-1].strip()
                        data['birthplace'] = place
                    
                    # Ethnicité
                    if 'Ethnicity' in text:
                        ethnicity = text.split('Ethnicity:')[-1].strip()
                        data['ethnicity'] = ethnicity
                    
                    # Cheveux
                    if 'Hair Color' in text:
                        hair = text.split('Hair Color:')[-1].strip()
                        data['hair_color'] = hair
                    
                    # Yeux
                    if 'Eye Color' in text:
                        eyes = text.split('Eye Color:')[-1].strip()
                        data['eye_color'] = eyes
                    
                    # Taille
                    if 'Height' in text:
                        height = text.split('Height:')[-1].strip()
                        data['height'] = height
                    
                    # Poids
                    if 'Weight' in text:
                        weight = text.split('Weight:')[-1].strip()
                        data['weight'] = weight
                    
                    # Mesures
                    if 'Measurements' in text:
                        measurements = text.split('Measurements:')[-1].strip()
                        data['measurements'] = measurements
                    
                    # Tatouages
                    if 'Tattoos' in text:
                        tattoos = text.split('Tattoos:')[-1].strip()
                        data['tattoos'] = tattoos
                    
                    # Piercings
                    if 'Piercings' in text:
                        piercings = text.split('Piercings:')[-1].strip()
                        data['piercings'] = piercings
                    
                    # Années actives
                    if 'Years Active' in text:
                        years = text.split('Years Active:')[-1].strip()
                        data['career_length'] = years
            
            # Aliases
            aliases_section = soup.find('p', string=re.compile('Also Known As', re.I))
            if aliases_section:
                aliases_text = aliases_section.text.replace('Also Known As:', '').strip()
                aliases = [a.strip() for a in aliases_text.split(',')]
                data['aliases'] = aliases
            
        except Exception as e:
            print(f"Erreur parsing IAFD: {e}")
        
        return data
    
    def scrape_awards(self, url: str) -> List[Dict]:
        """Scrape les awards depuis IAFD"""
        soup = self.get_page(url)
        if not soup:
            return []
        
        awards = []
        
        try:
            # Chercher la section awards
            awards_section = soup.find('div', {'id': 'awards'})
            if not awards_section:
                awards_section = soup.find('h2', string=re.compile('Awards', re.I))
                if awards_section:
                    awards_section = awards_section.find_next('div')
            
            if awards_section:
                # Parser les awards
                award_items = awards_section.find_all(['p', 'li'])
                current_year = None
                current_ceremony = None
                
                for item in award_items:
                    text = item.text.strip()
                    
                    # Détecter l'année
                    year_match = re.match(r'^(19\d{2}|20\d{2})$', text)
                    if year_match:
                        current_year = year_match.group(1)
                        continue
                    
                    # Détecter le type de cérémonie
                    if any(ceremony in text.upper() for ceremony in ['AVN', 'XBIZ', 'XRCO', 'NIGHTMOVES']):
                        current_ceremony = text
                        continue
                    
                    # C'est un award
                    if current_year and text:
                        award = {
                            'year': current_year,
                            'ceremony': current_ceremony or 'Unknown',
                            'award': text,
                            'winner': 'Winner' in text or 'Won' in text
                        }
                        awards.append(award)
        
        except Exception as e:
            print(f"Erreur scraping awards IAFD: {e}")
        
        return awards


class FreeonesScraper(ScraperBase):
    """Scraper pour Freeones.xxx"""
    
    def scrape_performer(self, url: str) -> Dict:
        """Scrape les données d'un performer depuis Freeones"""
        soup = self.get_page(url)
        if not soup:
            return {}
        
        data = {
            'source': 'freeones',
            'url': url
        }
        
        try:
            # Nom
            name_elem = soup.find('h1', class_='profile-header-name')
            if name_elem:
                data['name'] = name_elem.text.strip()
            
            # Bio section
            bio_section = soup.find('div', class_='profile-meta-list')
            if bio_section:
                items = bio_section.find_all('div', class_='profile-meta-item')
                for item in items:
                    label_elem = item.find('span', class_='profile-meta-label')
                    value_elem = item.find('span', class_='profile-meta-value')
                    
                    if label_elem and value_elem:
                        label = label_elem.text.strip().lower()
                        value = value_elem.text.strip()
                        
                        if 'born' in label or 'birth' in label:
                            data['birthdate'] = value
                        elif 'ethnicity' in label:
                            data['ethnicity'] = value
                        elif 'hair' in label:
                            data['hair_color'] = value
                        elif 'eye' in label:
                            data['eye_color'] = value
                        elif 'height' in label:
                            data['height'] = value
                        elif 'weight' in label:
                            data['weight'] = value
                        elif 'measure' in label:
                            data['measurements'] = value
                        elif 'tattoo' in label:
                            data['tattoos'] = value
                        elif 'piercing' in label:
                            data['piercings'] = value
            
            # Aliases
            aliases_elem = soup.find('div', class_='profile-aliases')
            if aliases_elem:
                aliases = [a.text.strip() for a in aliases_elem.find_all('a')]
                data['aliases'] = aliases
        
        except Exception as e:
            print(f"Erreur parsing Freeones: {e}")
        
        return data


class BabepaediaScraper(ScraperBase):
    """Scraper pour Babepedia.com"""
    
    def scrape_performer(self, url: str) -> Dict:
        """Scrape les données d'un performer depuis Babepedia"""
        soup = self.get_page(url)
        if not soup:
            return {}
        
        data = {
            'source': 'babepedia',
            'url': url
        }
        
        try:
            # Nom
            name_elem = soup.find('h1', class_='firstHeading')
            if name_elem:
                data['name'] = name_elem.text.strip()
            
            # Infobox (similaire à Wikipedia)
            infobox = soup.find('table', class_='infobox')
            if infobox:
                rows = infobox.find_all('tr')
                for row in rows:
                    th = row.find('th')
                    td = row.find('td')
                    
                    if th and td:
                        label = th.text.strip().lower()
                        value = td.text.strip()
                        
                        if 'born' in label:
                            data['birthdate'] = value
                        elif 'birth' in label and 'place' in label:
                            data['birthplace'] = value
                        elif 'ethnic' in label:
                            data['ethnicity'] = value
                        elif 'hair' in label:
                            data['hair_color'] = value
                        elif 'eye' in label:
                            data['eye_color'] = value
                        elif 'height' in label:
                            data['height'] = value
                        elif 'weight' in label:
                            data['weight'] = value
                        elif 'measure' in label:
                            data['measurements'] = value
        
        except Exception as e:
            print(f"Erreur parsing Babepedia: {e}")
        
        return data


class TheNudeScraper(ScraperBase):
    """Scraper pour TheNude.com"""
    
    def scrape_performer(self, url: str) -> Dict:
        """Scrape les données d'un performer depuis TheNude"""
        soup = self.get_page(url)
        if not soup:
            return {}
        
        data = {
            'source': 'thenude',
            'url': url
        }
        
        try:
            # Nom
            name_elem = soup.find('h1')
            if name_elem:
                data['name'] = name_elem.text.strip()
            
            # Données biographiques
            bio_divs = soup.find_all('div', class_='bio-item')
            for div in bio_divs:
                label_elem = div.find('strong')
                if label_elem:
                    label = label_elem.text.strip().lower()
                    value = div.text.replace(label_elem.text, '').strip()
                    
                    if 'born' in label or 'birth' in label:
                        data['birthdate'] = value
                    elif 'ethnic' in label:
                        data['ethnicity'] = value
                    elif 'hair' in label:
                        data['hair_color'] = value
                    elif 'eye' in label:
                        data['eye_color'] = value
                    elif 'height' in label:
                        data['height'] = value
                    elif 'weight' in label:
                        data['weight'] = value
                    elif 'measure' in label:
                        data['measurements'] = value
        
        except Exception as e:
            print(f"Erreur parsing TheNude: {e}")
        
        return data


class DataMerger:
    """Fusionne les données de plusieurs sources"""
    
    @staticmethod
    def merge_data(sources_data: List[Dict]) -> Tuple[Dict, Dict]:
        """
        Fusionne les données de plusieurs sources
        Retourne: (données confirmées, données en conflit)
        """
        confirmed = {}
        conflicts = {}
        
        # Compter les occurrences de chaque valeur pour chaque champ
        field_values = {}
        
        for source_data in sources_data:
            source_name = source_data.get('source', 'unknown')
            for field, value in source_data.items():
                if field in ['source', 'url']:
                    continue
                
                if not value:
                    continue
                
                if field not in field_values:
                    field_values[field] = {}
                
                value_str = str(value).strip().lower()
                if value_str not in field_values[field]:
                    field_values[field][value_str] = {
                        'count': 0,
                        'sources': [],
                        'original_value': value
                    }
                
                field_values[field][value_str]['count'] += 1
                field_values[field][value_str]['sources'].append(source_name)
        
        # Déterminer les valeurs confirmées et les conflits
        for field, values in field_values.items():
            if len(values) == 1:
                # Une seule valeur trouvée
                value_info = list(values.values())[0]
                confirmed[field] = {
                    'value': value_info['original_value'],
                    'count': value_info['count'],
                    'sources': value_info['sources']
                }
            else:
                # Plusieurs valeurs différentes = conflit
                sorted_values = sorted(values.items(), 
                                     key=lambda x: x[1]['count'], 
                                     reverse=True)
                
                if sorted_values[0][1]['count'] > sorted_values[1][1]['count']:
                    # Une valeur majoritaire
                    confirmed[field] = {
                        'value': sorted_values[0][1]['original_value'],
                        'count': sorted_values[0][1]['count'],
                        'sources': sorted_values[0][1]['sources'],
                        'note': 'Valeur majoritaire'
                    }
                    # Garder les autres valeurs dans les conflits
                    conflicts[field] = [
                        {
                            'value': v[1]['original_value'],
                            'count': v[1]['count'],
                            'sources': v[1]['sources']
                        }
                        for v in sorted_values[1:]
                    ]
                else:
                    # Égalité = vrai conflit
                    conflicts[field] = [
                        {
                            'value': v[1]['original_value'],
                            'count': v[1]['count'],
                            'sources': v[1]['sources']
                        }
                        for v in sorted_values
                    ]
        
        return confirmed, conflicts


class ScraperOrchestrator:
    """Orchestre le scraping depuis plusieurs sources"""
    
    def __init__(self):
        self.scrapers = {
            'iafd': IAFDScraper(),
            'freeones': FreeonesScraper(),
            'babepedia': BabepaediaScraper(),
            'thenude': TheNudeScraper()
        }
        self.merger = DataMerger()
    
    def scrape_urls(self, urls: List[str]) -> Tuple[Dict, Dict, int]:
        """
        Scrape plusieurs URLs et fusionne les résultats
        Retourne: (données confirmées, conflits, nombre de sources)
        """
        sources_data = []
        
        for url in urls:
            scraper = self._get_scraper_for_url(url)
            if scraper:
                data = scraper.scrape_performer(url)
                if data:
                    sources_data.append(data)
        
        if not sources_data:
            return {}, {}, 0
        
        confirmed, conflicts = self.merger.merge_data(sources_data)
        return confirmed, conflicts, len(sources_data)
    
    def _get_scraper_for_url(self, url: str) -> Optional[ScraperBase]:
        """Retourne le scraper approprié pour une URL"""
        url_lower = url.lower()
        
        if 'iafd.com' in url_lower:
            return self.scrapers['iafd']
        elif 'freeones' in url_lower:
            return self.scrapers['freeones']
        elif 'babepedia' in url_lower:
            return self.scrapers['babepedia']
        elif 'thenude' in url_lower:
            return self.scrapers['thenude']
        
        return None
    
    def scrape_awards(self, urls: List[str]) -> List[Dict]:
        """Scrape les awards de toutes les sources"""
        all_awards = []
        
        for url in urls:
            if 'iafd.com' in url.lower():
                awards = self.scrapers['iafd'].scrape_awards(url)
                all_awards.extend(awards)
        
        return all_awards


if __name__ == "__main__":
    # Test
    orchestrator = ScraperOrchestrator()
    
    # Exemple d'URLs
    test_urls = [
        "https://www.iafd.com/person.rme/perfid=bridgetteb/gender=f/bridgette-b.htm",
    ]
    
    confirmed, conflicts, num_sources = orchestrator.scrape_urls(test_urls)
    
    print(f"\n=== Données confirmées de {num_sources} source(s) ===")
    for field, info in confirmed.items():
        print(f"{field}: {info['value']} (sources: {', '.join(info['sources'])})")
    
    if conflicts:
        print(f"\n=== Conflits détectés ===")
        for field, values in conflicts.items():
            print(f"\n{field}:")
            for v in values:
                print(f"  - {v['value']} ({v['count']} source(s): {', '.join(v['sources'])})")
