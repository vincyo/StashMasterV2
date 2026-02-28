# StashMaster V2 - Interface Unifiée

Application Python/Tkinter pour la gestion et le scraping de métadonnées de performers, avec génération automatique de biographies.

## 🎯 Caractéristiques Principales

### Interface Unifiée
- **Fusion Phase 1 & Phase 2** : Une seule GUI pour toutes les opérations
- **Organisation par onglets** : Métadonnées, Champs Avancés, Bio
- **Workflow intuitif** : Scraping → Validation → Génération Bio

### Système de Tags Intelligent
- ✅ **Génération automatique** basée sur des règles métadonnées
- ✅ **PAS de scraping de tags** depuis les sources
- ✅ **Règles intelligentes** : ethnicité, couleur de cheveux, mesures, piercings, tattoos, âge

### Champs Optimisés
- **Champs simple ligne** : Nom, Aliases, Dates, Pays, etc.
- **Champs multilignes** :
  - 📝 Piercings
  - 📝 Tattoos
  - 🔗 URLs (une par ligne)

### Trivia & Awards
- **Fenêtre dédiée** avec requête et résultats séparés
- **Scraping ciblé** depuis IAFD et autres sources
- **Nettoyage automatique** : 1 award par ligne
- **Format structuré** : Année → Cérémonie → Awards

### Génération de Bio Automatique
- **Bio Google** : 3000 caractères, format professionnel (basé sur modèle)
- **Bio Ollama** : Génération IA locale optionnelle
- **Prompt personnalisé** : Directives précises pour l'IA
- **Choix flexible** : Cases à cocher pour type de bio

## 📋 Installation

### Prérequis
```bash
# Python 3.8 ou supérieur
python --version

# Tkinter (normalement inclus avec Python)
# Sur Ubuntu/Debian si besoin :
sudo apt-get install python3-tk
```

### Installation des dépendances
```bash
# Installer les packages Python requis
pip install -r requirements.txt
```

### Installation d'Ollama (optionnel)
Si vous voulez utiliser la génération de bio avec IA locale :

```bash
# Télécharger et installer Ollama depuis https://ollama.ai
# Puis télécharger un modèle
ollama pull llama2
```

## 🚀 Utilisation

### Lancement
```bash
python stashmaster_unified.py
```

### Workflow Complet

#### 1. Saisie des URLs
- Ouvrir l'onglet **"Champs Avancés"**
- Coller les URLs des sources (une par ligne) :
  ```
  https://www.iafd.com/person.rme/perfid=...
  https://www.freeones.xxx/...
  https://www.babepedia.com/...
  ```

#### 2. Scraping
- Menu **"Actions" → "Scraper & Lancer le flux Bio IA"**
- L'application scrape automatiquement toutes les URLs
- Affiche les résultats avec :
  - ✅ Données confirmées (même valeur de plusieurs sources)
  - 🆕 Nouvelles données (une seule source)
  - ⚠️ Conflits (valeurs différentes entre sources)

#### 3. Validation des Métadonnées
- Vérifier et compléter les champs dans l'onglet **"Métadonnées"**
- Les valeurs confirmées sont pré-remplies
- Résoudre les conflits manuellement si nécessaire

#### 4. Génération des Tags
- Onglet **"Champs Avancés"**
- Cliquer sur **"🔄 Générer Tags"**
- Les tags sont créés automatiquement selon les règles :
  - Ethnicité → Caucasian, Latina, Asian, Ebony
  - Cheveux → Blonde, Brunette, Redhead, Black Hair
  - Mesures → Big Boobs, Small Boobs
  - Piercings → Pierced
  - Tattoos → Tattooed
  - Carrière → MILF (si > 10 ans)

#### 5. Trivia & Awards
- Menu **"Actions" → "Trivia & Awards..."**
- Fenêtre dédiée s'ouvre avec deux sections :
  
  **Trivia**
  - Cliquer **"Scraper Trivia"**
  - Les anecdotes sont récupérées et affichées
  
  **Awards**
  - Cliquer **"Scraper Awards"**
  - Tous les prix/nominations sont listés
  - Cliquer **"Nettoyer Awards"** pour formater (1 par ligne)
  
- **"Appliquer et continuer"** pour sauvegarder

#### 6. Génération de Bio
- Menu **"Actions" → "Générer Bio..."** ou onglet **"Bio"**
- Fenêtre de génération s'ouvre avec 3 options :

  **Option 1 : Bio Google (recommandé)**
  - ✅ Génération automatique instantanée
  - ✅ Format professionnel de 3000 caractères
  - ✅ Structure avec sections : Introduction, Origines, Carrière, Vie Personnelle, Apparence, Prix
  - ✅ Basé sur le modèle BioGooglemodele.txt
  
  **Option 2 : Bio Ollama**
  - Génération avec IA locale (Ollama doit être installé)
  - Prompt par défaut optimisé
  
  **Option 3 : Bio Ollama avec prompt personnalisé**
  - Écrire vos directives précises dans le champ
  - Contrôle total sur le style et le contenu
  
- Cliquer **"Générer la Bio"**
- Vérifier le compteur de caractères
- **"Appliquer"** pour insérer dans l'onglet Bio

#### 7. Sauvegarde
- Bouton **"💾 Sauvegarder"** en bas à droite
- Toutes les données sont sauvegardées

## 📊 Architecture

### Structure des Fichiers
```
stashmaster_unified/
│
├── stashmaster_unified.py    # Application principale
├── scrapers.py                # Modules de scraping
├── requirements.txt           # Dépendances Python
├── README.md                  # Ce fichier
│
└── data/                      # Données sauvegardées (à créer)
    ├── performers/            # JSON des performers
    └── database.sqlite        # Base de données (futur)
```

### Composants Principaux

#### `MainWindow`
Interface principale unifiée avec 3 onglets :
- 📋 Métadonnées : Champs de base
- ⚙️ Champs Avancés : Tags, Piercings, Tattoos, URLs
  - nouvelles actions disponibles :
    - 🧹 **Nettoyer URLs** (enleve vides/duplications)
    - 🔗 **Valider URLs** (verifie les liens et colore le texte)
    - l'analyse/validation est également lancée automatiquement lors du
      chargement d'un performer ou dès qu'on modifie les URLs
- 📝 Bio : Biographie finale

#### `TriviaAwardsWindow`
Fenêtre dédiée pour :
- Scraping et affichage des trivia
- Scraping et nettoyage des awards
- Format structuré : 1 award par ligne

#### `BioGenerationWindow`
Fenêtre de génération avec :
- Choix du type de bio (Google/Ollama)
- Champ pour prompt personnalisé
- Prévisualisation et compteur de caractères

#### `TagRulesEngine`
Moteur de règles pour générer les tags automatiquement selon :
- Les métadonnées collectées (ethnicité, cheveux, mesures)
- Les attributs physiques (piercings, tattoos)
- L'âge de carrière

#### `AwardsCleaner`
Nettoyeur d'awards pour :
- Formater les awards (1 par ligne)
- Organiser par année et cérémonie
- Distinguer Winner vs Nominee

#### `BioGenerator`
Générateur de biographies avec 2 modes :
- **Google Bio** : Template de 3000 caractères
- **Ollama Bio** : IA locale avec prompt personnalisé

#### `ScraperOrchestrator`
Orchestre le scraping de plusieurs sources :
- IAFD
- Freeones
- Babepedia
- TheNude

#### `DataMerger`
Fusionne intelligemment les données de plusieurs sources :
- Détecte les valeurs confirmées (consensus)
- Identifie les nouvelles données (source unique)
- Signale les conflits (valeurs différentes)

## 🎨 Règles de Tags

Les tags sont générés automatiquement selon ces règles :

### Ethnicité
| Métadonnée | Tag Généré |
|------------|------------|
| Caucasian  | Caucasian  |
| Cuban, Latin, Latina | Latina |
| Asian | Asian |
| Ebony, African | Ebony |

### Couleur de Cheveux
| Métadonnée | Tag Généré |
|------------|------------|
| Blonde, Blond | Blonde |
| Brown, Brunette | Brunette |
| Red, Auburn | Redhead |
| Black | Black Hair |

### Mesures
| Condition | Tag Généré |
|-----------|------------|
| Tour de poitrine ≥ 36" | Big Boobs |
| Tour de poitrine ≤ 32" | Small Boobs |

### Attributs
| Métadonnée | Tag Généré |
|------------|------------|
| Piercings (non vide) | Pierced |
| Tattoos (non vide) | Tattooed |
| Carrière > 10 ans | MILF |

## 📝 Format de Bio Google

La bio générée suit ce template de 3000 caractères :

```markdown
### [Nom] : L'étoile charismatique au parcours diversifié

**Introduction**
Contexte, début de carrière, pseudonymes...

**📅 Origines et Premiers Pas**
Lieu de naissance, origines, début de carrière...

**🏆 Carrière et Filmographie**
Évolution, studios, performances, apogée...

**💡 Faits Intéressants & Vie Personnelle**
Personnalité, trivia, vie privée...

**👗 Apparence et Style**
Description physique, mesures, tatouages, piercings...

**🏆 Prix et Distinctions**
Awards, nominations, reconnaissance...

**Conclusion rapide**
Résumé, impact, héritage...
```

## 🔧 Configuration Avancée

### Personnaliser les Règles de Tags
Modifier la classe `TagRulesEngine` dans `stashmaster_unified.py` :

```python
@staticmethod
def generate_tags(metadata: Dict) -> List[str]:
    tags = []
    
    # Ajouter vos règles personnalisées ici
    if condition:
        tags.append('YourTag')
    
    return list(set(tags))
```

### Ajouter un Nouveau Scraper
Créer une nouvelle classe dans `scrapers.py` :

```python
class NewSourceScraper(ScraperBase):
    def scrape_performer(self, url: str) -> Dict:
        # Votre code de scraping
        return data
```

Puis l'enregistrer dans `ScraperOrchestrator` :

```python
self.scrapers['newsource'] = NewSourceScraper()
```

### Personnaliser le Template de Bio
Modifier la méthode `generate_google_bio` dans la classe `BioGenerator`.

## ❓ FAQ

### Les tags ne se génèrent pas automatiquement ?
→ Vérifiez que vous avez bien rempli les champs de base (ethnicité, cheveux, mesures) et cliquez sur "🔄 Générer Tags"

### Ollama ne fonctionne pas ?
→ Vérifiez qu'Ollama est installé et en cours d'exécution :
```bash
ollama serve
```

### Les awards ne sont pas nettoyés correctement ?
→ Utilisez le bouton "Nettoyer Awards" après le scraping pour formater automatiquement

### Comment résoudre les conflits de données ?
→ Les conflits sont affichés lors du scraping. Choisissez manuellement la valeur correcte ou conservez celle de la source la plus fiable (généralement IAFD)

### La bio est trop longue/courte ?
→ Bio Google : ~3000 caractères (fixe)
→ Bio Ollama : Ajustez dans le prompt personnalisé : "Écris une bio de [X] caractères..."

## 📄 Licence

Ce projet est fourni tel quel pour usage personnel.

## 🤝 Contribution

Pour toute amélioration ou correction :
1. Créer une branche pour votre fonctionnalité
2. Commiter vos changements
3. Créer une Pull Request

## 📮 Support

Pour toute question ou problème, créer une issue sur le repository.

---

**Version** : 2.0  
**Date** : Février 2026  
**Statut** : Production
