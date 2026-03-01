#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TagRulesEngine - Moteur de règles pour la génération de tags
"""

import re
from datetime import datetime
from typing import Dict, List, Optional

class TagRulesEngine:
    """Moteur de règles pour générer des tags basés sur les métadonnées"""

    # Tags AUTORISÉS (Whitelist) — Hair*Hair et RedHead sont auto-acceptés
    WHITELIST = [
        # Nationalités/Ethnies spécifiques
        'Colombian', 'Dominican', 'Thai', 'Venezuelan', 'Mexican', 'Bresilian',
        'Latina', 'Asian', 'Ebony', 'Mixed',
        # Physique
        'BigBoobs', 'NaturalBoobs', 'FakeBoobs',
        'BigButt', 'Petite', 'Tall', 'Curvy',
        # Carrière
        'MILF', 'Bimbo',
    ]

    # Tags INTERDITS (Blacklist)
    BLACKLIST = ['Small Boobs', 'Pierced', 'Tattooed', 'Caucasian', 'White']

    # Bonnettes cups ≥ C = BigBoobs
    BIG_CUPS = set('CDEFGHJK')

    @staticmethod
    def _first_year(raw: str) -> Optional[int]:
        """Extrait la première année (4 chiffres) d'une chaîne."""
        m = re.search(r'\b(19\d{2}|20\d{2})\b', str(raw))
        return int(m.group(1)) if m else None

    @staticmethod
    def generate_tags(metadata: Dict) -> List[str]:
        """Génère des tags basés sur les métadonnées collectées."""
        tags: List[str] = []
        now_year = datetime.now().year

        # ── Champs bruts ────────────────────────────────────────────────────
        ethnicity    = str(metadata.get('ethnicity',    '') or '').lower().strip()
        country      = str(metadata.get('country',      '') or '').lower().strip()
        birthplace   = str(metadata.get('birthplace',   '') or '').lower().strip()
        hair_color   = str(metadata.get('hair_color',   '') or '').lower().strip()
        measurements = str(metadata.get('measurements', '') or '').strip()
        fake_tits    = str(metadata.get('fake_tits',    '') or '').lower().strip()
        career_raw   = str(metadata.get('career_length', '') or
                          metadata.get('career_start', '') or '').strip()
        birthdate    = str(metadata.get('birthdate',    '') or '').strip()
        trivia       = str(metadata.get('trivia',       '') or '').lower()
        bio_raw      = str(metadata.get('bio_raw',      '') or '').lower()

        # Texte combiné pour les lookups géographiques
        geo = ' '.join([ethnicity, country, birthplace])

        # ── 1. NATIONALITÉS & ETHNIES ───────────────────────────────────────
        nat_rules = [
            ('Colombian',  r'colomb'),
            ('Dominican',  r'dominic'),
            ('Thai',       r'th(ai|a[iï]land)'),
            ('Venezuelan', r'venezue'),
            ('Mexican',    r'mexic'),
            ('Bresilian',  r'br[ae]sil|brazil'),
        ]
        for tag, pattern in nat_rules:
            if re.search(pattern, geo):
                tags.append(tag)

        # Groupes ethniques généraux
        if re.search(r'\b(latin[ao]?|cuban|puerto\s*ric)\b', geo):
            tags.append('Latina')
        if re.search(r'\b(asian|asiatique)\b', geo):
            tags.append('Asian')
        if re.search(r'\b(ebony|african[\s-]american|black)\b', geo):
            tags.append('Ebony')
        if re.search(r'\bmixed\b|\bmultiracial\b|\bbiracial\b|\bm[eé]tisse?\b', geo):
            tags.append('Mixed')

        # ── 2. CHEVEUX ────────────────────────────────────────────────────
        if   re.search(r'blond|blonde', hair_color):             tags.append('BlondHair')
        elif re.search(r'brown|brunette|brunet|brun', hair_color): tags.append('BrownHair')
        elif re.search(r'black|noir', hair_color):               tags.append('BlackHair')
        elif re.search(r'red|auburn|roux|roux', hair_color):     tags.append('RedHead')
        elif re.search(r'blue|bleu', hair_color):                tags.append('BlueHair')
        elif re.search(r'green|vert', hair_color):               tags.append('GreenHair')
        elif re.search(r'gr[ae]y|gris', hair_color):             tags.append('GreyHair')
        elif re.search(r'pink|rose', hair_color):                tags.append('PinkHair')
        elif re.search(r'purple|violet', hair_color):            tags.append('PurpleHair')
        elif re.search(r'white|blanc', hair_color):              tags.append('WhiteHair')

        # ── 3. MENSURATIONS ───────────────────────────────────────────────
        # Format : "34C-27-39" ou "34C – 27 – 39" ou "34DD-25-36" ou "34D/27/38"
        big_boobs = False
        if measurements:
            # Cherche bonnette (lettre après le premier nombre) ex: "34C", "32DD", "36DDD"
            cup_match = re.search(r'\d+\s*([A-Z]{1,3})', measurements.upper())
            if cup_match:
                cup = cup_match.group(1).upper()
                # Premier caractère C ou plus = BigBoobs
                if cup[0] in TagRulesEngine.BIG_CUPS:
                    big_boobs = True
            else:
                # Fallback : premier nombre ≥ 36 (tour de poitrine)
                num_match = re.search(r'(\d+)', measurements)
                if num_match and int(num_match.group(1)) >= 36:
                    big_boobs = True

            # Hanches ≥ 39 (3ème mesure) = BigButt
            hip_m = re.findall(r'(\d+)', measurements)
            if len(hip_m) >= 3:
                try:
                    hips = int(hip_m[2])
                    if hips >= 39:
                        tags.append('BigButt')
                except Exception:
                    pass

        # fake_tits : Stash stocke 'Fake' ou 'Natural'
        if fake_tits:
            if re.search(r'\bfake\b|enhanc|implant|augment|\byes\b|oui', fake_tits):
                big_boobs = True
                tags.append('FakeBoobs')
            elif re.search(r'\bnatural\b|natur|\bno\b|non\b', fake_tits) and measurements:
                tags.append('NaturalBoobs')

        if big_boobs:
            tags.append('BigBoobs')

        # ── 4. BigButt depuis texte (si pas déjà ajouté via mensurations) ───
        text_check = trivia + ' ' + bio_raw
        if re.search(r'big\s*(butt|ass)|bubble\s*butt|phat\s*ass|round\s*(ass|butt)', text_check):
            if 'BigButt' not in tags:
                tags.append('BigButt')

        # Bimbo = BigBoobs ET BigButt tous les deux présents
        if big_boobs and 'BigButt' in tags:
            tags.append('Bimbo')

        # ── 5. SILHOUETTE depuis taille ──────────────────────────────────
        height_raw = str(metadata.get('height', '') or '').strip()
        if height_raw:
            try:
                h_num = re.search(r'[\d.]+', height_raw)
                if h_num:
                    h = float(h_num.group())
                    if h < 10:   h *= 30.48  # pieds → cm
                    elif h < 100: h *= 2.54  # pouces → cm
                    if h <= 160:
                        tags.append('Petite')
                    elif h >= 175:
                        tags.append('Tall')
            except Exception:
                pass

        # ── 6. MILF ───────────────────────────────────────────────────────
        # MILF = âge ≥ 35 ans (birthdate uniquement)
        if birthdate:
            birth_yr = TagRulesEngine._first_year(birthdate)
            if birth_yr and birth_yr > 1900 and (now_year - birth_yr) >= 35:
                tags.append('MILF')

        # ── 7. FILTRAGE WHITELIST / BLACKLIST ────────────────────────────
        final_tags = []
        for t in tags:
            if t in TagRulesEngine.BLACKLIST:
                continue
            if (t in TagRulesEngine.WHITELIST
                    or t.endswith('Hair') or t == 'RedHead'):
                final_tags.append(t)

        result = sorted(list(set(final_tags)))

        # Debug console
        print(f"[TAGS] ethnicity='{ethnicity}' country='{country}' "
              f"measurements='{measurements}' fake_tits='{fake_tits}' "
              f"career='{career_raw}' hair='{hair_color}' dob='{birthdate[:7] if birthdate else ''}'")
        print(f"[TAGS] → {result}")
        return result
