#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AwardsCleaner - Nettoyage et formatage des récompenses
"""

import re

class AwardsCleaner:
    """Nettoie et formate les awards pour avoir 1 par ligne"""
    
    @staticmethod
    def clean_awards(raw_awards: str) -> str:
        """Nettoie le texte brut des awards pour avoir un format lisible"""
        if not raw_awards:
            return ""

        # Utiliser le nettoyeur robuste partagé (fallback regex quand Gemini est off)
        try:
            from utils.normalizer import clean_awards_field
            return clean_awards_field(raw_awards)
        except Exception:
            # Fallback vers l'ancien comportement si import impossible
            pass
        
        # Pattern pour détecter les types d'awards
        award_types = ['AVN AWARDS', 'XBIZ AWARDS', 'NIGHTMOVES', 'XRCO AWARDS', 'TEASE AWARDS', 'VENUS AWARDS']
        
        text = raw_awards
        for award_type in award_types:
            # S'assurer qu'il y a un saut de ligne devant le type d'award
            text = re.sub(f'(?i){re.escape(award_type)}', f'\n{award_type}\n', text)
        
        lines = []
        current_year = None
        
        # Diviser en lignes et nettoyer
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Détecter si c'est une année isolée
            if re.match(r'^\d{4}$', line):
                current_year = line
                lines.append(f'\n{current_year}')
                continue
            
            # Détecter si c'est un type d'award (déjà formaté ci-dessus)
            if any(award_type in line.upper() for award_type in award_types):
                lines.append(f'\n{line}')
                continue
            
            # Détecter Winner ou Nominee
            if line.startswith('Winner:') or line.startswith('Nominee:'):
                lines.append(f'  {line}')
            elif current_year and not line.startswith(' '):
                lines.append(f'  {line}')
            else:
                lines.append(line)
        
        # Nettoyage final des doubles sauts de lignes
        result = '\n'.join(lines)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result.strip()
