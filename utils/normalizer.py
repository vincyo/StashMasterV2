#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalizer - Utilitaires de normalisation des données (Pays, Dates, etc.)
"""

import re
from datetime import datetime
from typing import Dict, Optional

# Mapping des codes pays ISO-2 vers les noms complets (Français/Anglais selon besoin)
# Ici on utilise les noms anglais car Stash et IAFD sont majoritairement en anglais
COUNTRY_MAP = {
    'AF': 'Afghanistan', 'AX': 'Åland Islands', 'AL': 'Albania', 'DZ': 'Algeria', 'AS': 'American Samoa',
    'AD': 'Andorra', 'AO': 'Angola', 'AI': 'Anguilla', 'AQ': 'Antarctica', 'AG': 'Antigua and Barbuda',
    'AR': 'Argentina', 'AM': 'Armenia', 'AW': 'Aruba', 'AU': 'Australia', 'AT': 'Austria', 'AZ': 'Azerbaijan',
    'BS': 'Bahamas', 'BH': 'Bahrain', 'BD': 'Bangladesh', 'BB': 'Barbados', 'BY': 'Belarus', 'BE': 'Belgium',
    'BZ': 'Belize', 'BJ': 'Benin', 'BM': 'Bermuda', 'BT': 'Bhutan', 'BO': 'Bolivia', 'BA': 'Bosnia and Herzegovina',
    'BW': 'Botswana', 'BV': 'Bouvet Island', 'BR': 'Brazil', 'IO': 'British Indian Ocean Territory',
    'BN': 'Brunei Darussalam', 'BG': 'Bulgaria', 'BF': 'Burkina Faso', 'BI': 'Burundi', 'KH': 'Cambodia',
    'CM': 'Cameroon', 'CA': 'Canada', 'CV': 'Cape Verde', 'KY': 'Cayman Islands', 'CF': 'Central African Republic',
    'TD': 'Chad', 'CL': 'Chile', 'CN': 'China', 'CX': 'Christmas Island', 'CC': 'Cocos (Keeling) Islands',
    'CO': 'Colombia', 'KM': 'Comoros', 'CG': 'Congo', 'CD': 'Congo, Democratic Republic', 'CK': 'Cook Islands',
    'CR': 'Costa Rica', 'CI': 'Côte d\'Ivoire', 'HR': 'Croatia', 'CU': 'Cuba', 'CY': 'Cyprus', 'CZ': 'Czech Republic',
    'DK': 'Denmark', 'DJ': 'Djibouti', 'DM': 'Dominica', 'DO': 'Dominican Republic', 'EC': 'Ecuador', 'EG': 'Egypt',
    'SV': 'El Salvador', 'GQ': 'Equatorial Guinea', 'ER': 'Eritrea', 'EE': 'Estonia', 'ET': 'Ethiopia',
    'FK': 'Falkland Islands (Malvinas)', 'FO': 'Faroe Islands', 'FJ': 'Fiji', 'FI': 'Finland', 'FR': 'France',
    'GF': 'French Guiana', 'PF': 'French Polynesia', 'TF': 'French Southern Territories', 'GA': 'Gabon',
    'GM': 'Gambia', 'GE': 'Georgia', 'DE': 'Germany', 'GH': 'Ghana', 'GI': 'Gibraltar', 'GR': 'Greece',
    'GL': 'Greenland', 'GD': 'Grenada', 'GP': 'Guadeloupe', 'GU': 'Guam', 'GT': 'Guatemala', 'GG': 'Guernsey',
    'GN': 'Guinea', 'GW': 'Guinea-Bissau', 'GY': 'Guyana', 'HT': 'Haiti', 'HM': 'Heard Island and McDonald Islands',
    'VA': 'Holy See (Vatican City State)', 'HN': 'Honduras', 'HK': 'Hong Kong', 'HU': 'Hungary', 'IS': 'Iceland',
    'IN': 'India', 'ID': 'Indonesia', 'IR': 'Iran', 'IQ': 'Iraq', 'IE': 'Ireland', 'IM': 'Isle of Man',
    'IL': 'Israel', 'IT': 'Italy', 'JM': 'Jamaica', 'JP': 'Japan', 'JE': 'Jersey', 'JO': 'Jordan', 'KZ': 'Kazakhstan',
    'KE': 'Kenya', 'KI': 'Kiribati', 'KP': 'Korea, Democratic People\'s Republic', 'KR': 'Korea, Republic',
    'KW': 'Kuwait', 'KG': 'Kyrgyzstan', 'LA': 'Lao People\'s Democratic Republic', 'LV': 'Latvia', 'LB': 'Lebanon',
    'LS': 'Lesotho', 'LR': 'Liberia', 'LY': 'Libyan Arab Jamahiriya', 'LI': 'Liechtenstein', 'LT': 'Lithuania',
    'LU': 'Luxembourg', 'MO': 'Macao', 'MK': 'Macedonia', 'MG': 'Madagascar', 'MW': 'Malawi', 'MY': 'Malaysia',
    'MV': 'Maldives', 'ML': 'Mali', 'MT': 'Malta', 'MH': 'Marshall Islands', 'MQ': 'Martinique', 'MR': 'Mauritania',
    'MU': 'Mauritius', 'YT': 'Mayotte', 'MX': 'Mexico', 'FM': 'Micronesia', 'MD': 'Moldova', 'MC': 'Monaco',
    'MN': 'Mongolia', 'ME': 'Montenegro', 'MS': 'Montserrat', 'MA': 'Morocco', 'MZ': 'Mozambique', 'MM': 'Myanmar',
    'NA': 'Namibia', 'NR': 'Nauru', 'NP': 'Nepal', 'NL': 'Netherlands', 'AN': 'Netherlands Antilles',
    'NC': 'New Caledonia', 'NZ': 'New Zealand', 'NI': 'Nicaragua', 'NE': 'Niger', 'NG': 'Nigeria', 'NU': 'Niue',
    'NF': 'Norfolk Island', 'MP': 'Northern Mariana Islands', 'NO': 'Norway', 'OM': 'Oman', 'PK': 'Pakistan',
    'PW': 'Palau', 'PS': 'Palestinian Territory', 'PA': 'Panama', 'PG': 'Papua New Guinea', 'PY': 'Paraguay',
    'PE': 'Peru', 'PH': 'Philippines', 'PN': 'Pitcairn', 'PL': 'Poland', 'PT': 'Portugal', 'PR': 'Puerto Rico',
    'QA': 'Qatar', 'RE': 'Réunion', 'RO': 'Romania', 'RU': 'Russian Federation', 'RW': 'Rwanda', 'SH': 'Saint Helena',
    'KN': 'Saint Kitts and Nevis', 'LC': 'Saint Lucia', 'PM': 'Saint Pierre and Miquelon',
    'VC': 'Saint Vincent and the Grenadines', 'WS': 'Samoa', 'SM': 'San Marino', 'ST': 'Sao Tome and Principe',
    'SA': 'Saudi Arabia', 'SN': 'Senegal', 'RS': 'Serbia', 'SC': 'Seychelles', 'SL': 'Sierra Leone', 'SG': 'Singapore',
    'SK': 'Slovakia', 'SI': 'Slovenia', 'SB': 'Solomon Islands', 'SO': 'Somalia', 'ZA': 'South Africa',
    'GS': 'South Georgia and the South Sandwich Islands', 'ES': 'Spain', 'LK': 'Sri Lanka', 'SD': 'Sudan',
    'SR': 'Suriname', 'SJ': 'Svalbard and Jan Mayen', 'SZ': 'Swaziland', 'SE': 'Sweden', 'CH': 'Switzerland',
    'SY': 'Syrian Arab Republic', 'TW': 'Taiwan', 'TJ': 'Tajikistan', 'TZ': 'Tanzania', 'TH': 'Thailand',
    'TL': 'Timor-Leste', 'TG': ' Togo', 'TK': 'Tokelay', 'TO': 'Tonga', 'TT': 'Trinidad and Tobago', 'TN': 'Tunisia',
    'TR': 'Turkey', 'TM': 'Turkmenistan', 'TC': 'Turks and Caicos Islands', 'TV': 'Tuvalu', 'UG': 'Uganda',
    'UA': 'Ukraine', 'AE': 'United Arab Emirates', 'GB': 'United Kingdom', 'US': 'USA',
    'UM': 'United States Minor Outlying Islands', 'UY': 'Uruguay', 'UZ': 'Uzbekistan', 'VU': 'Vanuatu', 'VE': 'Venezuela',
    'VN': 'Viet Nam', 'VG': 'Virgin Islands, British', 'VI': 'Virgin Islands, U.S.', 'WF': 'Wallis and Futuna',
    'EH': 'Western Sahara', 'YE': 'Yemen', 'ZM': 'Zambia', 'ZW': 'Zimbabwe'
}

def normalize_country(country: str) -> str:
    """Convertit un code pays ISO-2 en nom complet ou nettoie le nom"""
    if not country: return ""
    c = country.strip().upper()
    if c in COUNTRY_MAP:
        return COUNTRY_MAP[c]
    return country.strip()

def normalize_date(date_str: str) -> str:
    """Convertit divers formats de date en YYYY-MM-DD"""
    if not date_str or date_str == "": return ""
    
    # Formats courants: "October 15, 1983" ou "1983-10-15"
    try:
        # Essayer October 15, 1983
        dt = datetime.strptime(date_str, "%B %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except:
        pass
        
    try:
        # Essayer Oct 15, 1983
        dt = datetime.strptime(date_str, "%b %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except:
        pass
        
    # Déjà au bon format ou format inconnu
    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
        return date_str
        
    return date_str


def clean_award_text(raw_text: str) -> str:
    """
    Nettoie et structure le texte brut d'UN award.
    
    Entrées possibles:
    - "AVN Awards 2015 Nominee: All-Girl Performer of the Year"
    - "2016 Winner: Best Boy/Girl Sex Scene"
    - "AVN Awards2015 Nominee: Best Girl/Girl Sex Scene, Masterpiece (2013)"
    - "2017 Award - Most Talented Tongue [Nominee]" (déjà partiellement formaté)
    
    Sortie standard: "2015 AVN Award - All-Girl Performer of the Year [Nominee]"
    """
    if not raw_text or not isinstance(raw_text, str):
        return ""
    
    text = raw_text.strip()
    
    # Détecter si déjà au format "YYYY [ORG] Award - Category [Status]"
    # Si oui, juste normaliser et retourner
    already_formatted = re.match(r'^\d{4}\s+(?:\w+\s+)?Award\s*-', text)
    if already_formatted:
        # Juste nettoyer les espaces et retourner
        text = re.sub(r'\s+', ' ', text).strip()
        # Enlever les doubles brackets vides "[]"
        text = re.sub(r'\[\s*\]', '', text).strip()
        return text
    
    # 1. Séparer les blocs collés (ex: "Awards2015" -> "Awards 2015")
    text = re.sub(r'([a-zA-Z])(\d{4})', r'\1 \2', text)
    
    # 2. Nettoyage des caractères UTF-8 mal encodés (Ã‚â€, etc.)
    text = re.sub(r'Ã[ƒÆâ€šÂ¢]+[^A-Za-z0-9\s]*', '', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # 3. Normalisation espaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 4. Extraction année (première occurrence)
    year_match = re.search(r'\b(19|20)\d{2}\b', text)
    year = year_match.group(0) if year_match else ""
    
    # 5. Extraction organisation AVANT de nettoyer le texte
    # Pattern: "AVN Awards", "XBIZ Awards", etc. (peut avoir "Awards" au pluriel ou singulier)
    org = None
    org_patterns = [
        (r'\b(AVN)\s*Awards?\b', 'AVN'),
        (r'\b(XBIZ)\s*Awards?\b', 'XBIZ'),
        (r'\b(XRCO)\s*Awards?\b', 'XRCO'),
        (r'\b(NightMoves|Nightmoves)\s*(?:Awards?|Fan Awards?)?\b', 'NightMoves'),
        (r'\b(Spank\s*Bank)\s*(?:Awards?|Technical Awards?)?\b', 'Spank Bank'),
        (r'\b(Porn\s*Hub|PornHub)\s*Awards?\b', 'PornHub'),
        (r'\b(FAME)\s*Awards?\b', 'FAME')
    ]
    
    for pattern, org_name in org_patterns:
        if re.search(pattern, text, re.I):
            org = org_name
            # Retirer cette partie du texte pour ne garder que la catégorie
            text = re.sub(pattern, '', text, flags=re.I)
            break
    
    # Si aucune organisation détectée, on ne met pas "Award" par défaut
    # car cela crée des doublons "Award - Award -"
    if org:
        org = f"{org} Award"
    else:
        # Ne pas mettre de préfixe générique, on construira différemment
        org = ""
    
    # 6. Détecter statut (Winner/Nominee)
    status = None
    if re.search(r'\bWinner\s*:', text, re.I):
        status = "Winner"
        text = re.sub(r'\bWinner\s*:\s*', '', text, flags=re.I)
    elif re.search(r'\bNominee\s*:', text, re.I):
        status = "Nominee"
        text = re.sub(r'\bNominee\s*:\s*', '', text, flags=re.I)
    elif re.search(r'\b\*\*Winner\b', text, re.I):
        status = "Winner"
        text = re.sub(r'\b\*\*Winner\b', '', text, flags=re.I)
    elif re.search(r'\bWinner\b', text, re.I):
        status = "Winner"
        text = re.sub(r'\bWinner\b', '', text, flags=re.I)
    elif re.search(r'\bNominee\b', text, re.I):
        status = "Nominee"
        text = re.sub(r'\bNominee\b', '', text, flags=re.I)
    
    # 7. Nettoyer l'année du reste du texte et mots clés redondants
    if year:
        text = re.sub(r'\b' + re.escape(year) + r'\b', '', text)
    text = re.sub(r'\bAward\s*:\s*', '', text, flags=re.I)
    
    # Enlever "Award -" si présent (pour éviter double "Award - Award -")
    text = re.sub(r'^Award\s*-\s*', '', text, flags=re.I)
    
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.lstrip('- :').strip()
    
    # 8. Si aucune catégorie restante, ignorer
    if not text or len(text) < 5:
        return ""
    
    # 9. Construire le résultat final
    # Gérer le cas où org est vide (pas de préfixe "Award" générique)
    if org:
        # Avec organisation
        if status:
            result = f"{year} {org} - {text} [{status}]" if year else f"{org} - {text} [{status}]"
        else:
            result = f"{year} {org} - {text}" if year else f"{org} - {text}"
    else:
        # Sans organisation - juste année et catégorie
        if status:
            result = f"{year} - {text} [{status}]" if year else f"{text} [{status}]"
        else:
            result = f"{year} - {text}" if year else text
    
    return result.strip()



def clean_awards_field(awards_text: str) -> str:
    """
    Nettoie complètement un champ awards qui peut contenir :
    - Des awards bruts d'IAFD collés (avec Awards2015, etc.)
    - Des phrases de prose de bio
    - Des awards déjà partiellement formatés
    
    Retourne une liste propre d'awards formatés, un par ligne.
    """
    if not awards_text or not isinstance(awards_text, str):
        return ""
    
    # Étape 1: Pré-traitement global pour séparer les blocs
    text = awards_text
    
    # Séparer les phrases avec ponctuation forte
    text = re.sub(r'([.!])\s+([A-Z])', r'\1\n\2', text)
    
    # Séparer quand une nouvelle année + org apparaît (mais pas le premier)
    text = re.sub(r'(\d{4})\s+(?=\d{4}\s+(?:AVN|XBIZ))', r'\1\n', text, flags=re.I)
    
    # Séparer "Boobs2016" -> "Boobs\n2016"  
    text = re.sub(r'([a-z])(\d{4}\s+(?:Nominee|Winner))', r'\1\n\2', text, flags=re.I)
    
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        
        # Normaliser Awards2015 → Awards 2015 AVANT extraction du préfixe
        line = re.sub(r'([a-zA-Z])(\d{4})', r'\1 \2', line)
        
        # Filtrer les lignes de prose descriptive
        # Ces lignes ont souvent "for" suivi de "and" ou se terminent par ", the" ou ", and the"
        if re.search(r'\bfor\b.*\band\b', line, re.I) or re.search(r',\s*(and\s+)?the\s*$', line, re.I):
            continue
        
        # Filtrer les lignes commençant par "Award - " sans année (orphelines)
        if re.match(r'^Award\s*-\s*', line, re.I) and not re.search(r'\b\d{4}\b', line):
            continue
        
        # Filtrer les autres phrases de prose (bio générée)
        prose_keywords = [
            "she has been", "she was also", "she was named", 
            "including", "for her", " in a",
            "dramatic feature", "multiple avn", "multiple other",
            " at the "
        ]
        if any(phrase in line.lower() for phrase in prose_keywords):
            continue
        
        # Détecter s'il y a plusieurs awards dans cette ligne
        # Compter les "Nominee:" et "Winner:" mais aussi les patterns "Best X" répétés
        status_count = len(re.findall(r'\b(Winner|Nominee):', line, re.I))
        
        # Détecter aussi les awards sans status explicite mais avec patterns répétés
        # Exemple : "Best X, Title(year)Best Y, Title2(year)" 
        best_patterns = len(re.findall(r'\bBest\s+[A-Z]', line))
        
        # Détecter les collages après parenthèses : ")Word" sans espace
        parenthesis_collisions = len(re.findall(r'\)[A-Z][a-z]', line))
        
        # Si plusieurs "Best" ou collisions après parenthèses, séparer
        if best_patterns > 2 or parenthesis_collisions > 0:
            # Séparer quand un mot title-case suit immédiatement une parenthèse fermante
            line = re.sub(r'\)([A-Z][a-z]+)', r')\n\1', line)
            # Séparer aussi sur les patterns ")Best" ou ")Nominee:" ou ")Winner:"
            line = re.sub(r'\)(Best|Nominee|Winner)', r')\n\1', line, flags=re.I)
            
            # Re-split en sous-lignes
            sublines = line.split('\n')
            
            # Si la ligne originale est déjà formatée (YYYY Award -), juste séparer sans reformater
            already_formatted = re.match(r'^(\d{4}\s+(?:\w+\s+)?Award\s*-)', line)
            
            if already_formatted:
                # Extraire le préfixe strict (année + org si présente + Award)
                prefix = already_formatted.group(1).strip()
                
                for subline in sublines:
                    subline = subline.strip()
                    if len(subline) < 10:
                        continue
                    
                    # Si commence par le préfixe, c'est la première partie, la garder telle quelle
                    if subline.startswith(prefix):
                        # Juste normaliser les espaces
                        cleaned_lines.append(re.sub(r'\s+', ' ', subline).strip())
                    else:
                        # Ajouter le préfixe aux parties suivantes
                        cleaned_lines.append(f"{prefix} {subline}")
                continue
            
            # Sinon, extraire le préfixe de la ligne originale pour le propager
            prefix_match = re.match(r'^(.*?(?:AVN|XBIZ|XRCO|NightMoves|Spank Bank|PornHub|FAME)\s*Awards?\s*\d{4})', line, re.I)
            if not prefix_match:
                prefix_match = re.match(r'^(\d{4}(?:\s+\w+)?\s*Awards?)', line)
            prefix = prefix_match.group(1).strip() if prefix_match else ""
            
            for subline in sublines:
                subline = subline.strip()
                if len(subline) < 10:
                    continue
                
                # Si la sous-ligne n'a pas d'année, ajouter le préfixe
                if not re.search(r'\b\d{4}\b', subline) and prefix:
                    subline = f"{prefix} {subline}"
                
                cleaned = clean_award_text(subline)
                if cleaned and len(cleaned) > 15:
                    cleaned_lines.append(cleaned)
            continue  # Passer à la ligne suivante
        
        if status_count > 1:
            # Ligne avec plusieurs awards collés - extraire le préfixe commun
            # Séparer d'abord les awards collés après parenthèses : ")Nominee:" → ")\nNominee:"
            line = re.sub(r'\)(Nominee|Winner):', r')\n\1:', line, flags=re.I)
            line = re.sub(r'\)(Best\s+)', r')\n\1', line, flags=re.I)
            
            # Re-split si on a créé des nouvelles lignes
            if '\n' in line:
                sublines = line.split('\n')
                for subline in sublines:
                    subline = subline.strip()
                    if len(subline) < 10:
                        continue
                    cleaned = clean_award_text(subline)
                    if cleaned and len(cleaned) > 15:
                        cleaned_lines.append(cleaned)
                continue  # Passer à la ligne suivante
            
            # Important: normaliser AVANT d'extraire le préfixe
            normalized_line = re.sub(r'([a-zA-Z])(\d{4})', r'\1 \2', line)
            
            # Extraire "AVN Awards 2015" ou similaire au début
            prefix_match = re.match(r'^(.*?(?:AVN|XBIZ|XRCO|NightMoves|Spank Bank|PornHub)\s*Awards?\s*\d{4})', normalized_line, re.I)
            if not prefix_match:
                # Essayer juste année
                prefix_match = re.match(r'^(\d{4})', normalized_line)
            
            prefix = prefix_match.group(1).strip() if prefix_match else ""
            
            # Split sur la LIGNE ORIGINALE pour garder les positions correctes
            parts = re.split(r'\s+(Winner|Nominee):\s*', line)
            
            # parts[0] pourrait contenir le préfixe (ou être inclus dedans)
            # Si prefix est vide, utiliser parts[0]
            if not prefix:
                prefix = parts[0].strip()
            
            # Traiter chaque award (parts[1]=status, parts[2]=category, parts[3]=status, parts[4]=category, etc.)
            for i in range(1, len(parts), 2):
                if i+1 < len(parts):
                    status_word = parts[i]
                    category = parts[i+1].strip()
                    
                    # Reconstruire avec préfixe
                    reconstructed = f"{prefix} {status_word}: {category}"
                    cleaned = clean_award_text(reconstructed)
                    if cleaned and len(cleaned) > 15:
                        cleaned_lines.append(cleaned)
        else:
            # Un seul award (ou aucun)
            cleaned = clean_award_text(line)
            if cleaned and len(cleaned) > 15:
                cleaned_lines.append(cleaned)
    
    # Dédupliquer
    unique_lines = []
    seen = set()
    for line in cleaned_lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)

    # Regrouper et trier : Winners d'abord (chronologique), puis Nominees
    # (par prestige), puis autres lignes non classées.
    prestige_map = {
        'AVN': 1,
        'XBIZ': 2,
        'XRCO': 3,
        'NightMoves': 4,
        'PornHub': 5,
        'Spank Bank': 6,
        'FAME': 7,
    }

    def _extract_year(line: str) -> int:
        m = re.search(r'\b(19|20)\d{2}\b', line)
        return int(m.group(0)) if m else 9999

    def _extract_org_rank(line: str) -> int:
        for org, rank in prestige_map.items():
            if re.search(rf'\b{re.escape(org)}\b', line, re.I):
                return rank
        return 99

    winners, nominees, others = [], [], []
    for line in unique_lines:
        low = line.lower()
        if '[winner]' in low:
            winners.append(line)
        elif '[nominee]' in low:
            nominees.append(line)
        else:
            others.append(line)

    winners.sort(key=lambda l: (_extract_year(l), _extract_org_rank(l), l.lower()))
    nominees.sort(key=lambda l: (_extract_org_rank(l), _extract_year(l), l.lower()))
    others.sort(key=lambda l: (_extract_year(l), _extract_org_rank(l), l.lower()))

    final_lines = []
    if winners:
        final_lines.append("Winner")
        final_lines.extend(winners)
    if nominees:
        if final_lines:
            final_lines.append("")
        final_lines.append("Nominee")
        final_lines.extend(nominees)
    if others:
        if final_lines:
            final_lines.append("")
        final_lines.extend(others)

    return "\n".join(final_lines)

