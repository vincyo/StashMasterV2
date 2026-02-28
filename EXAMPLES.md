# Exemples d'Utilisation

Ce document contient des exemples pratiques pour utiliser StashMaster V2.

## 📋 Exemples Basiques

### Exemple 1 : Scraping Simple

```python
# Dans un script Python
from scrapers import ScraperOrchestrator

# Créer l'orchestrateur
orchestrator = ScraperOrchestrator()

# URLs à scraper
urls = [
    "https://www.iafd.com/person.rme/perfid=bridgetteb/gender=f/bridgette-b.htm",
    "https://www.freeones.xxx/bridgette-b"
]

# Scraper et fusionner
confirmed, conflicts, num_sources = orchestrator.scrape_urls(urls)

# Afficher les résultats
print(f"Données de {num_sources} source(s)")
print("\nConfirmées:")
for field, info in confirmed.items():
    print(f"  {field}: {info['value']}")

print("\nConflits:")
for field, values in conflicts.items():
    print(f"  {field}:")
    for v in values:
        print(f"    - {v['value']} ({', '.join(v['sources'])})")
```

### Exemple 2 : Génération de Tags

```python
from stashmaster_unified import TagRulesEngine

# Créer le moteur de règles
engine = TagRulesEngine()

# Métadonnées d'exemple
metadata = {
    'ethnicity': 'Latina',
    'hair_color': 'Blonde',
    'measurements': '36DD-25-36',
    'piercings': 'Navel',
    'tattoos': 'Lower back',
    'career_length': '2007-'
}

# Générer les tags
tags = engine.generate_tags(metadata)
print(f"Tags générés: {', '.join(tags)}")
# Output: Tags générés: Latina, Blonde, Big Boobs, Pierced, Tattooed, MILF
```

### Exemple 3 : Nettoyage d'Awards

```python
from stashmaster_unified import AwardsCleaner

cleaner = AwardsCleaner()

# Awards bruts
raw_awards = """
AVN AWARDS2012Winner: Unsung Starlet of the Year2014Nominee: Unsung Starlet of the Year
2015Nominee: Fan Award: Best Boobs
"""

# Nettoyer
cleaned = cleaner.clean_awards(raw_awards)
print(cleaned)
```

Output:
```
AVN AWARDS

2012
  Winner: Unsung Starlet of the Year

2014
  Nominee: Unsung Starlet of the Year

2015
  Nominee: Fan Award: Best Boobs
```

### Exemple 4 : Génération de Bio

```python
from stashmaster_unified import BioGenerator

generator = BioGenerator()

# Métadonnées du performer
metadata = {
    'name': 'Bridgette B',
    'birthdate': 'October 15, 1983',
    'birthplace': 'Barcelona, Spain',
    'ethnicity': 'Caucasian',
    'hair_color': 'Blonde',
    'measurements': '34DD-27-34',
    'height': '173 cm',
    'weight': '129 lbs',
    'career_start': '2007',
    'aliases': ['Bridget B', 'Bridgette', 'Spanish Doll']
}

# Générer bio Google
bio = generator.generate_google_bio('Bridgette B', metadata)
print(f"Bio générée ({len(bio)} caractères):\n{bio}")
```

## 🔧 Exemples Avancés

### Exemple 5 : Fusion de Données Complexes

```python
from scrapers import DataMerger

merger = DataMerger()

# Données de 3 sources différentes
sources = [
    {
        'source': 'iafd',
        'name': 'Bridgette B',
        'birthdate': 'October 15, 1983',
        'ethnicity': 'Caucasian',
        'hair_color': 'Blonde',
        'measurements': '34DD-27-34'
    },
    {
        'source': 'freeones',
        'name': 'Bridgette B',
        'birthdate': 'October 15, 1983',
        'ethnicity': 'Caucasian',
        'hair_color': 'Blonde',  # Conflit
        'height': '173 cm'
    },
    {
        'source': 'babepedia',
        'name': 'Bridgette B',
        'birthdate': 'October 15, 1983',
        'ethnicity': 'Caucasian',
        'hair_color': 'Brown',  # Conflit
        'weight': '129 lbs'
    }
]

# Fusionner
confirmed, conflicts = merger.merge_data(sources)

print("=== Données Confirmées ===")
for field, info in confirmed.items():
    sources_str = ', '.join(info['sources'])
    print(f"{field}: {info['value']} ({info['count']} sources: {sources_str})")

print("\n=== Conflits ===")
for field, values in conflicts.items():
    print(f"\n{field}:")
    for v in values:
        print(f"  - {v['value']} ({v['count']} sources: {', '.join(v['sources'])})")
```

### Exemple 6 : Scraping avec Gestion d'Erreurs

```python
from scrapers import IAFDScraper
import requests

scraper = IAFDScraper()

urls = [
    "https://www.iafd.com/person.rme/perfid=bridgetteb/gender=f/bridgette-b.htm",
    "https://www.iafd.com/person.rme/perfid=invalid/gender=f/invalid.htm"
]

for url in urls:
    print(f"\nScraping: {url}")
    try:
        data = scraper.scrape_performer(url)
        if data:
            print(f"  ✅ Succès: {data.get('name', 'Unknown')}")
            print(f"  Champs: {len(data)}")
        else:
            print("  ❌ Échec: Aucune donnée retournée")
    except requests.RequestException as e:
        print(f"  ❌ Erreur réseau: {e}")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
```

### Exemple 7 : Création d'un Scraper Personnalisé

```python
from scrapers import ScraperBase
from typing import Dict

class MonSiteScraper(ScraperBase):
    """Scraper pour mon site personnalisé"""
    
    def scrape_performer(self, url: str) -> Dict:
        """Scrape un performer depuis mon site"""
        soup = self.get_page(url)
        if not soup:
            return {}
        
        data = {
            'source': 'monsite',
            'url': url
        }
        
        try:
            # Extraire le nom
            name_elem = soup.find('h1', class_='performer-name')
            if name_elem:
                data['name'] = name_elem.text.strip()
            
            # Extraire la date de naissance
            birthday_elem = soup.find('span', class_='birthday')
            if birthday_elem:
                data['birthdate'] = birthday_elem.text.strip()
            
            # Ajouter d'autres extractions...
            
        except Exception as e:
            print(f"Erreur: {e}")
        
        return data

# Utilisation
scraper = MonSiteScraper()
data = scraper.scrape_performer("https://monsite.com/performer/123")
print(data)
```

### Exemple 8 : Intégration avec l'Interface

```python
# Dans votre propre script
from stashmaster_unified import MainWindow
import tkinter as tk

# Créer et configurer la fenêtre
app = MainWindow()

# Pré-remplir des données (exemple)
app.metadata_entries['name'].insert(0, "Bridgette B")
app.urls_text.insert('1.0', "https://www.iafd.com/person.rme/perfid=bridgetteb/gender=f/bridgette-b.htm")

# Lancer l'application
app.mainloop()
```

## 🎓 Cas d'Usage Réels

### Cas 1 : Workflow Complet Automatisé

```python
#!/usr/bin/env python3
"""
Workflow automatisé complet pour un performer
"""

from scrapers import ScraperOrchestrator
from stashmaster_unified import TagRulesEngine, BioGenerator
import json

def process_performer(name: str, urls: list) -> dict:
    """Traite complètement un performer"""
    print(f"\n{'='*50}")
    print(f"Traitement de: {name}")
    print('='*50)
    
    # 1. Scraping
    print("\n1. Scraping des sources...")
    orchestrator = ScraperOrchestrator()
    confirmed, conflicts, num_sources = orchestrator.scrape_urls(urls)
    print(f"   ✅ {num_sources} source(s) scrapée(s)")
    print(f"   ✅ {len(confirmed)} champ(s) confirmé(s)")
    print(f"   ⚠️  {len(conflicts)} conflit(s)")
    
    # 2. Préparer les métadonnées
    print("\n2. Préparation des métadonnées...")
    metadata = {key: info['value'] for key, info in confirmed.items()}
    metadata['name'] = name
    
    # 3. Générer les tags
    print("\n3. Génération des tags...")
    tag_engine = TagRulesEngine()
    tags = tag_engine.generate_tags(metadata)
    metadata['tags'] = tags
    print(f"   ✅ {len(tags)} tag(s) généré(s): {', '.join(tags)}")
    
    # 4. Générer la bio
    print("\n4. Génération de la bio...")
    bio_generator = BioGenerator()
    bio = bio_generator.generate_google_bio(name, metadata)
    metadata['bio'] = bio
    print(f"   ✅ Bio générée ({len(bio)} caractères)")
    
    # 5. Sauvegarder
    print("\n5. Sauvegarde...")
    filename = f"data/performers/{name.lower().replace(' ', '_')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Sauvegardé: {filename}")
    
    return metadata

# Exemple d'utilisation
if __name__ == "__main__":
    performer_data = process_performer(
        name="Bridgette B",
        urls=[
            "https://www.iafd.com/person.rme/perfid=bridgetteb/gender=f/bridgette-b.htm",
            "https://www.freeones.xxx/bridgette-b"
        ]
    )
    
    print("\n" + "="*50)
    print("✅ Traitement terminé avec succès!")
    print("="*50)
```

### Cas 2 : Batch Processing de Plusieurs Performers

```python
#!/usr/bin/env python3
"""
Traitement par lots de plusieurs performers
"""

import json
from pathlib import Path
from scrapers import ScraperOrchestrator
from stashmaster_unified import TagRulesEngine, BioGenerator

def batch_process(performers_file: str):
    """Traite plusieurs performers depuis un fichier JSON"""
    
    # Charger la liste
    with open(performers_file, 'r') as f:
        performers = json.load(f)
    
    print(f"Traitement de {len(performers)} performer(s)...\n")
    
    orchestrator = ScraperOrchestrator()
    tag_engine = TagRulesEngine()
    bio_generator = BioGenerator()
    
    results = {
        'success': [],
        'failed': [],
        'partial': []
    }
    
    for i, performer in enumerate(performers, 1):
        name = performer['name']
        urls = performer['urls']
        
        print(f"\n[{i}/{len(performers)}] {name}")
        print("-" * 40)
        
        try:
            # Scraping
            confirmed, conflicts, num_sources = orchestrator.scrape_urls(urls)
            
            if num_sources == 0:
                print("  ❌ Aucune source valide")
                results['failed'].append(name)
                continue
            
            # Métadonnées
            metadata = {key: info['value'] for key, info in confirmed.items()}
            metadata['name'] = name
            
            # Tags
            tags = tag_engine.generate_tags(metadata)
            metadata['tags'] = tags
            
            # Bio
            bio = bio_generator.generate_google_bio(name, metadata)
            metadata['bio'] = bio
            
            # Sauvegarder
            filename = f"data/performers/{name.lower().replace(' ', '_')}.json"
            Path("data/performers").mkdir(parents=True, exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            if len(conflicts) > 0:
                print(f"  ⚠️  Succès partiel ({len(conflicts)} conflits)")
                results['partial'].append(name)
            else:
                print("  ✅ Succès complet")
                results['success'].append(name)
        
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            results['failed'].append(name)
    
    # Résumé
    print("\n" + "="*50)
    print("RÉSUMÉ")
    print("="*50)
    print(f"✅ Succès complet: {len(results['success'])}")
    print(f"⚠️  Succès partiel: {len(results['partial'])}")
    print(f"❌ Échecs: {len(results['failed'])}")
    
    return results

# Exemple d'utilisation
if __name__ == "__main__":
    # Créer un fichier performers_list.json avec:
    # [
    #   {
    #     "name": "Performer 1",
    #     "urls": ["url1", "url2"]
    #   },
    #   ...
    # ]
    
    results = batch_process("performers_list.json")
```

### Cas 3 : Validation et Correction Semi-Automatique

```python
#!/usr/bin/env python3
"""
Validation et correction semi-automatique des données
"""

from scrapers import ScraperOrchestrator
from stashmaster_unified import TagRulesEngine

def validate_and_correct(urls: list) -> dict:
    """Valide et propose des corrections"""
    
    orchestrator = ScraperOrchestrator()
    confirmed, conflicts, num_sources = orchestrator.scrape_urls(urls)
    
    print("="*50)
    print("VALIDATION DES DONNÉES")
    print("="*50)
    
    # Données confirmées
    print("\n✅ Données confirmées:")
    for field, info in confirmed.items():
        print(f"  {field}: {info['value']}")
        print(f"    Sources: {', '.join(info['sources'])}")
    
    # Conflits à résoudre
    if conflicts:
        print("\n⚠️  CONFLITS À RÉSOUDRE:")
        corrections = {}
        
        for field, values in conflicts.items():
            print(f"\n  {field}:")
            for i, v in enumerate(values, 1):
                print(f"    [{i}] {v['value']} ({', '.join(v['sources'])})")
            
            # Demander à l'utilisateur de choisir
            while True:
                choice = input(f"  Choisir [1-{len(values)}] ou [s]kip: ")
                if choice.lower() == 's':
                    break
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(values):
                        corrections[field] = values[idx]['value']
                        print(f"    ✅ {field} = {values[idx]['value']}")
                        break
                except ValueError:
                    pass
                print("    ❌ Choix invalide")
        
        # Appliquer les corrections
        for field, value in corrections.items():
            confirmed[field] = {
                'value': value,
                'note': 'Corrigé manuellement'
            }
    
    # Résultat final
    final_data = {key: info['value'] for key, info in confirmed.items()}
    
    print("\n" + "="*50)
    print("DONNÉES FINALES")
    print("="*50)
    for field, value in final_data.items():
        print(f"  {field}: {value}")
    
    return final_data

# Exemple
if __name__ == "__main__":
    urls = [
        "https://www.iafd.com/person.rme/perfid=bridgetteb/gender=f/bridgette-b.htm",
        "https://www.freeones.xxx/bridgette-b"
    ]
    
    data = validate_and_correct(urls)
```

## 🔗 Intégrations

### Intégration avec Stash

```python
import requests
import json

class StashAPI:
    """Client pour l'API Stash"""
    
    def __init__(self, url="http://localhost:9999", api_key=None):
        self.url = url
        self.api_key = api_key
    
    def create_performer(self, performer_data: dict) -> dict:
        """Crée un performer dans Stash"""
        # GraphQL mutation
        mutation = """
        mutation PerformerCreate($input: PerformerCreateInput!) {
          performerCreate(input: $input) {
            id
            name
          }
        }
        """
        
        variables = {
            "input": {
                "name": performer_data.get('name'),
                "birthdate": performer_data.get('birthdate'),
                "ethnicity": performer_data.get('ethnicity'),
                "hair_color": performer_data.get('hair_color'),
                "height": performer_data.get('height'),
                "measurements": performer_data.get('measurements'),
                "tags": performer_data.get('tags', [])
            }
        }
        
        response = requests.post(
            f"{self.url}/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        return response.json()

# Utilisation
stash = StashAPI()
result = stash.create_performer(performer_data)
print(f"Performer créé: {result}")
```

---

Ces exemples couvrent les cas d'usage les plus courants. Pour plus d'informations, consultez le [README.md](README.md) et la documentation des modules.
