#!/bin/bash
# Script de lancement de StashMaster V2

echo "================================================"
echo "  StashMaster V2 - Interface Unifiée"
echo "================================================"
echo ""

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    echo "Installez Python 3.8 ou supérieur"
    exit 1
fi

echo "✅ Python 3 détecté : $(python3 --version)"

# Vérifier les dépendances
echo ""
echo "Vérification des dépendances..."

if ! python3 -c "import requests" 2>/dev/null; then
    echo "⚠️  Module 'requests' manquant"
    echo "Installation des dépendances..."
    pip3 install -r requirements.txt
fi

if ! python3 -c "import bs4" 2>/dev/null; then
    echo "⚠️  Module 'beautifulsoup4' manquant"
    echo "Installation des dépendances..."
    pip3 install -r requirements.txt
fi

echo "✅ Toutes les dépendances sont installées"

# Créer les répertoires nécessaires
echo ""
echo "Création des répertoires..."
mkdir -p data/performers

echo "✅ Répertoires créés"

# Lancer l'application
echo ""
echo "================================================"
echo "  Lancement de l'application..."
echo "================================================"
echo ""

python3 stashmaster_unified.py

echo ""
echo "Application fermée."
