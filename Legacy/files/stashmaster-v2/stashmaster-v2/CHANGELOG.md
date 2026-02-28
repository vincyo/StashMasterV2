# Changelog

Toutes les modifications notables du projet sont documentées dans ce fichier.

## [2.0.0] - 2026-02-25

### Ajouté
- ✨ **Interface unifiée** : Fusion complète des Phase 1 et Phase 2 en une seule GUI
- 🏷️ **Système de tags intelligent** : Génération automatique basée sur des règles métadonnées
  - Tags basés sur l'ethnicité (Caucasian, Latina, Asian, Ebony)
  - Tags basés sur la couleur de cheveux (Blonde, Brunette, Redhead, Black Hair)
  - Tags basés sur les mesures (Big Boobs, Small Boobs)
  - Tags pour piercings et tattoos
  - Tag MILF basé sur l'âge de carrière
- 📝 **Champs multilignes** pour Piercings, Tattoos et URLs
- 🪟 **Fenêtre Trivia & Awards dédiée** avec :
  - Scraping ciblé depuis IAFD
  - Affichage séparé des requêtes et résultats
  - Nettoyage automatique des awards (1 par ligne)
- 📄 **Génération de bio automatique** avec 2 modes :
  - Bio Google : Template de 3000 caractères professionnel
  - Bio Ollama : IA locale avec prompt personnalisé
- 🔄 **ScraperOrchestrator** : Scraping multi-sources avec fusion intelligente
- ✅ **DataMerger** : Détection automatique des données confirmées et conflits
- 🧹 **AwardsCleaner** : Formatage intelligent des awards
- 📊 **Onglets organisés** : Métadonnées, Champs Avancés, Bio

### Modifié
- 🔧 **Tags** : Ne sont plus scrapés, uniquement générés par règles
- 📋 **Interface** : Onglets au lieu de fenêtres séparées
- 🎯 **Workflow** : Simplifié et plus intuitif
- 💾 **Architecture** : Code modulaire avec séparation des responsabilités

### Supprimé
- ❌ Scraping de tags depuis les sources (remplacé par génération automatique)
- ❌ Fenêtres multiples (remplacé par onglets)

### Technique
- 🐍 Python 3.8+ requis
- 📦 Dépendances : requests, beautifulsoup4, lxml
- 🤖 Support optionnel d'Ollama pour génération IA
- 🏗️ Architecture MVC améliorée

### Documentation
- 📖 README complet avec guide d'utilisation
- 🎓 Documentation des règles de tags
- 💡 Exemples et FAQ
- 🛠️ Guide de configuration avancée

---

## [1.0.0] - Version Précédente

### Fonctionnalités
- Interface Phase 1 : Métadonnées usuelles avec scraping
- Interface Phase 2 : Champs avancés séparés
- Scraping basique depuis IAFD et autres sources
- Tags scrapés depuis les sources
- Bio manuelle

### Limitations
- Deux fenêtres séparées
- Tags scrapés pas toujours cohérents
- Pas de génération automatique de bio
- Awards bruts non formatés
- Workflow moins fluide

---

## À venir

### [2.1.0] - Planifié
- [ ] Base de données SQLite intégrée
- [ ] Export vers Stash
- [ ] Import depuis fichiers JSON
- [ ] Historique des modifications
- [ ] Undo/Redo
- [ ] Raccourcis clavier
- [ ] Thèmes dark/light
- [ ] Support multi-langues

### [2.2.0] - En réflexion
- [ ] Scraping d'images
- [ ] Détection automatique de doublons
- [ ] Suggestions intelligentes
- [ ] API REST pour intégrations
- [ ] Plugin system
- [ ] Scraping de scènes/films
- [ ] Statistiques et graphiques

---

**Format du Changelog** : [Keep a Changelog](https://keepachangelog.com/)  
**Versioning** : [Semantic Versioning](https://semver.org/)
