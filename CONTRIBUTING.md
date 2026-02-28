# Guide de Contribution

Merci de votre intérêt pour contribuer à StashMaster V2 ! 🎉

## 📋 Table des Matières

- [Code de Conduite](#code-de-conduite)
- [Comment Contribuer](#comment-contribuer)
- [Développement](#développement)
- [Standards de Code](#standards-de-code)
- [Tests](#tests)
- [Documentation](#documentation)

## 🤝 Code de Conduite

- Soyez respectueux envers tous les contributeurs
- Fournissez des critiques constructives
- Concentrez-vous sur ce qui est le mieux pour le projet
- Acceptez les feedbacks avec grâce

## 💡 Comment Contribuer

### Rapporter des Bugs

Avant de créer une issue :
1. Vérifiez si le bug n'a pas déjà été rapporté
2. Utilisez la dernière version du code
3. Testez avec une installation propre

Pour rapporter un bug, incluez :
- **Description claire** du problème
- **Étapes pour reproduire** le bug
- **Comportement attendu** vs. comportement observé
- **Screenshots** si applicable
- **Environnement** : OS, version Python, dépendances
- **Logs d'erreur** si disponibles

### Suggérer des Améliorations

Pour suggérer une nouvelle fonctionnalité :
1. Vérifiez si elle n'est pas déjà planifiée (voir CHANGELOG)
2. Créez une issue avec le label "enhancement"
3. Décrivez clairement :
   - Le problème que ça résout
   - Comment ça devrait fonctionner
   - Des exemples d'utilisation
   - Des alternatives considérées

### Soumettre des Pull Requests

1. **Fork** le projet
2. **Créez une branche** pour votre fonctionnalité
   ```bash
   git checkout -b feature/ma-super-feature
   ```
3. **Committez** vos changements
   ```bash
   git commit -m "feat: ajout de ma super feature"
   ```
4. **Pushez** vers la branche
   ```bash
   git push origin feature/ma-super-feature
   ```
5. **Ouvrez une Pull Request**

## 🛠️ Développement

### Configuration de l'Environnement

```bash
# Cloner le repository
git clone https://github.com/votre-username/stashmaster-v2.git
cd stashmaster-v2

# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Installer les dépendances de développement (si disponibles)
pip install -r requirements-dev.txt
```

### Structure du Projet

```
stashmaster-v2/
│
├── stashmaster_unified.py    # Application principale
│   ├── MainWindow            # GUI principale
│   ├── TriviaAwardsWindow    # Fenêtre Trivia/Awards
│   ├── BioGenerationWindow   # Fenêtre génération de bio
│   ├── TagRulesEngine        # Moteur de tags
│   ├── AwardsCleaner         # Nettoyeur d'awards
│   └── BioGenerator          # Générateur de bio
│
├── scrapers.py               # Modules de scraping
│   ├── ScraperBase           # Classe de base
│   ├── IAFDScraper           # Scraper IAFD
│   ├── FreeonesScraper       # Scraper Freeones
│   ├── BabepaediaScraper     # Scraper Babepedia
│   ├── TheNudeScraper        # Scraper TheNude
│   ├── DataMerger            # Fusionneur de données
│   └── ScraperOrchestrator   # Orchestrateur
│
├── test_stashmaster.py       # Tests unitaires
├── config.json               # Configuration
├── requirements.txt          # Dépendances
├── README.md                 # Documentation
├── CHANGELOG.md              # Historique des versions
└── CONTRIBUTING.md           # Ce fichier
```

### Lancer l'Application en Mode Développement

```bash
# Mode normal
python3 stashmaster_unified.py

# Avec logs de debug (à implémenter)
python3 stashmaster_unified.py --debug

# Avec un performer spécifique (à implémenter)
python3 stashmaster_unified.py --performer "Bridgette B"
```

## 📝 Standards de Code

### Style Python

Suivez [PEP 8](https://www.python.org/dev/peps/pep-0008/) :

```python
# Bonnes pratiques
class MyClass:
    """Docstring pour la classe"""
    
    def my_method(self, param1: str, param2: int) -> bool:
        """Docstring pour la méthode
        
        Args:
            param1: Description du paramètre 1
            param2: Description du paramètre 2
            
        Returns:
            Description du retour
        """
        # Code ici
        return True

# Imports groupés
import sys
import os
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

from scrapers import IAFDScraper
```

### Nommage

- **Classes** : PascalCase (`TagRulesEngine`)
- **Fonctions/Méthodes** : snake_case (`generate_tags`)
- **Constantes** : UPPER_CASE (`MAX_RETRIES`)
- **Variables privées** : préfixe `_` (`_internal_method`)

### Docstrings

Utilisez le format Google :

```python
def scrape_performer(self, url: str) -> Dict:
    """Scrape les données d'un performer.
    
    Args:
        url: L'URL de la page du performer
        
    Returns:
        Dictionnaire contenant les métadonnées du performer
        
    Raises:
        ValueError: Si l'URL est invalide
        RequestException: Si le scraping échoue
        
    Examples:
        >>> scraper.scrape_performer("https://example.com/performer")
        {'name': 'John Doe', 'birthdate': '1990-01-01'}
    """
    pass
```

### Type Hints

Utilisez les type hints pour améliorer la lisibilité :

```python
from typing import Dict, List, Optional, Tuple

def merge_data(self, sources: List[Dict]) -> Tuple[Dict, Dict]:
    """Fusionne les données de plusieurs sources"""
    pass

def get_performer(self, id: int) -> Optional[Dict]:
    """Récupère un performer par ID"""
    pass
```

## 🧪 Tests

### Lancer les Tests

```bash
# Tous les tests
python3 test_stashmaster.py

# Tests spécifiques
python3 -m unittest test_stashmaster.TestTagRulesEngine

# Avec couverture (si coverage installé)
coverage run test_stashmaster.py
coverage report
```

### Écrire des Tests

```python
import unittest

class TestMyFeature(unittest.TestCase):
    def setUp(self):
        """Préparation avant chaque test"""
        self.engine = TagRulesEngine()
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        pass
    
    def test_my_feature(self):
        """Test de ma fonctionnalité"""
        result = self.engine.generate_tags({})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
```

### Couverture de Tests

Visez au minimum :
- 80% de couverture pour le code principal
- 60% pour les scrapers (dépendent de sources externes)
- 100% pour les utilitaires critiques (TagRulesEngine, DataMerger)

## 📚 Documentation

### Documenter le Code

- **Classes** : Docstring avec description, attributs
- **Méthodes** : Docstring avec Args, Returns, Raises
- **Modules** : Docstring d'en-tête avec description générale

### Mettre à Jour la Documentation

Lors de l'ajout de fonctionnalités :
1. **README.md** : Ajouter dans la section correspondante
2. **CHANGELOG.md** : Documenter le changement
3. **Docstrings** : Commenter le code
4. **config.json** : Ajouter les nouvelles options

## 🔀 Workflow Git

### Branches

- `main` : Code stable, production
- `develop` : Développement en cours
- `feature/*` : Nouvelles fonctionnalités
- `bugfix/*` : Corrections de bugs
- `hotfix/*` : Corrections urgentes

### Messages de Commit

Utilisez [Conventional Commits](https://www.conventionalcommits.org/) :

```bash
# Format
<type>(<scope>): <description>

[corps optionnel]

[footer(s) optionnel(s)]

# Exemples
feat(tags): ajout de la règle MILF basée sur l'âge
fix(scraper): correction du parsing IAFD
docs(readme): mise à jour des instructions d'installation
test(tags): ajout de tests pour les tags d'ethnicité
refactor(bio): amélioration de la génération Google
style(ui): correction de l'alignement des boutons
```

Types :
- `feat` : Nouvelle fonctionnalité
- `fix` : Correction de bug
- `docs` : Documentation
- `style` : Formatage (pas de changement de code)
- `refactor` : Refactoring
- `test` : Ajout de tests
- `chore` : Maintenance

## 🎯 Priorités de Développement

Consultez le [CHANGELOG.md](CHANGELOG.md) pour voir les fonctionnalités planifiées.

### Court Terme (v2.1)
- Base de données SQLite
- Export vers Stash
- Import JSON
- Historique des modifications

### Moyen Terme (v2.2)
- Scraping d'images
- Détection de doublons
- API REST
- Plugin system

### Long Terme (v3.0)
- Interface web
- Multi-utilisateurs
- Synchronisation cloud
- Mobile app

## ❓ Questions ?

N'hésitez pas à :
- Ouvrir une issue pour discuter
- Rejoindre les discussions
- Contacter les mainteneurs

## 🙏 Remerciements

Merci à tous les contributeurs qui aident à améliorer StashMaster V2 !

---

**Happy Coding!** 🚀
