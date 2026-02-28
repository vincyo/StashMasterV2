#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TagRulesEngine - Moteur de règles pour la génération de tags
"""

import re
from datetime import datetime
from typing import Dict, List

class TagRulesEngine:
    """Moteur de règles pour générer des tags basés sur les métadonnées"""
    
    # Tags AUTORISÉS (Whitelist)
    WHITELIST = [
        'Colombian', 'Dominican', 'Thai', 'Venezuelan', 'Mexican', 'Bresilian', 
        'Latina', 'Asian', 'Ebony', 'BigBoobs', 'MILF', 'BigButt', 'Bimbo'
    ]
    # Les Hair Color (all) sont également autorisés
    
    # Tags INTERDITS (Blacklist)
    BLACKLIST = ['Small Boobs', 'Pierced', 'Tattooed', 'Caucasian']

    @staticmethod
    def generate_tags(metadata: Dict) -> List[str]:
        """Génère des tags basés sur les métadonnées collectées"""
        tags = []
        
        # 1. Ethnicité & Nationalité
        ethnicity = metadata.get('ethnicity', '').lower()
        country = metadata.get('country', '').lower()
        
        # Nationalités spécifiques
        if 'colomb' in country or 'colomb' in ethnicity: tags.append('Colombian')
        if 'dominic' in country or 'dominic' in ethnicity: tags.append('Dominican')
        if 'thai' in country or 'thai' in ethnicity: tags.append('Thai')
        if 'venezue' in country or 'venezue' in ethnicity: tags.append('Venezuelan')
        if 'mexic' in country or 'mexic' in ethnicity: tags.append('Mexican')
        if 'brazil' in country or 'bresil' in country or 'brazil' in ethnicity or 'bresil' in ethnicity: 
            tags.append('Bresilian')
            
        # Groupes ethniques
        # on utilise des frontières de mots pour éviter les faux-positifs
        if re.search(r'\b(?:latin(?:a)?|cuban)\b', ethnicity):
            tags.append('Latina')
        if re.search(r'\basian\b', ethnicity):
            tags.append('Asian')
        if re.search(r'\b(?:ebony|african)\b', ethnicity):
            tags.append('Ebony')
        
        # 2. Cheveux (Tous autorisés par défaut)
        hair_color_raw = metadata.get('hair_color', '').lower()
        if 'blonde' in hair_color_raw or 'blond' in hair_color_raw: tags.append('BlondHair')
        elif 'brown' in hair_color_raw or 'brunette' in hair_color_raw: tags.append('BrownHair')
        elif 'black' in hair_color_raw: tags.append('BlackHair')
        elif 'red' in hair_color_raw: tags.append('RedHead')
        elif 'blue' in hair_color_raw: tags.append('BlueHair')
        elif 'green' in hair_color_raw: tags.append('GreenHair')
        elif 'grey' in hair_color_raw or 'gray' in hair_color_raw: tags.append('GreyHair')
        elif 'pink' in hair_color_raw: tags.append('PinkHair')
        elif 'purple' in hair_color_raw: tags.append('PurpleHair')
        elif 'white' in hair_color_raw: tags.append('WhiteHair')
        
        # 3. Mesures (Seins & Fesses)
        measurements = metadata.get('measurements', '')
        if measurements:
            match = re.search(r'(\d+)', measurements)
            if match:
                size = int(match.group(1))
                if size >= 36:
                    tags.append('BigBoobs')
                # 'Small Boobs' est dans la blacklist, on ne l'ajoute plus
        
        # BigButt & Bimbo (Heuristique basée sur Trivia ou Measurements si possible)
        trivia = str(metadata.get('trivia', '')).lower()
        if 'big butt' in trivia or 'bubble butt' in trivia:
            tags.append('BigButt')
        if 'bimbo' in trivia:
            tags.append('Bimbo')
        
        # 5. Âge de carrière
        career_start = metadata.get('career_start', '')
        if career_start:
            try:
                year_str = career_start.split('-')[0]
                year = int(year_str)
                if datetime.now().year - year > 10:
                    tags.append('MILF')
            except:
                pass
        
        # --- FILTRAGE STRICT ---
        # Garder uniquement ce qui est dans la WHITELIST ou qui se termine par 'Hair'
        final_tags = []
        for t in tags:
            if t in TagRulesEngine.WHITELIST or t.endswith('Hair') or t == 'RedHead':
                if t not in TagRulesEngine.BLACKLIST:
                    final_tags.append(t)
        
        return sorted(list(set(final_tags)))
