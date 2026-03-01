#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalizer - Utilitaires de normalisation des données (Pays, Dates, etc.)
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

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

    # Nettoyage rapide des tokens vides fréquents avant tout parsing
    # Exemple: "() [] []" ou "[ ]" collés dans certains scrapings
    text = re.sub(r'\[\s*\]', '', text)
    text = re.sub(r'\(\s*\)', '', text)
    
    # Détecter si déjà au format "YYYY [ORG] Award - Category [Status]"
    # Si oui, juste normaliser et retourner
    already_formatted = re.match(r'^\d{4}\s+(?:\w+\s+)?Award\s*-', text)
    if already_formatted:
        # Juste nettoyer les espaces et retourner
        text = re.sub(r'\s+', ' ', text).strip()
        # Enlever les doubles brackets vides "[]"
        text = re.sub(r'\[\s*\]', '', text).strip()
        text = re.sub(r'\(\s*\)', '', text).strip()
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
    
    # 6. Détecter statut (Winner/Nominee/Nomine/Nominé)
    status = None
    nominee_word_re = r"\bNomin(?:ee|e)?\b"  # couvre: Nominee / Nomine / Nomin (après stripping accents)

    # Cas ambigu: les deux statuts apparaissent (souvent un artefact HTML) -> ignorer le statut
    if (
        re.search(r"\bWinner\b", text, re.I)
        and re.search(nominee_word_re, text, re.I)
        and not re.search(r"\b(Winner|Nominee|Nomine|Nomin(?:ee|e)?)\s*:", text, re.I)
    ):
        text = re.sub(r'\bWinner\b', '', text, flags=re.I)
        text = re.sub(nominee_word_re, '', text, flags=re.I)
        status = None
    if re.search(r'\bWinner\s*:', text, re.I):
        status = "Winner"
        text = re.sub(r'\bWinner\s*:\s*', '', text, flags=re.I)
    elif re.search(rf'{nominee_word_re}\s*:', text, re.I):
        status = "Nominee"
        text = re.sub(rf'{nominee_word_re}\s*:\s*', '', text, flags=re.I)
    elif re.search(r'\b\*\*Winner\b', text, re.I):
        status = "Winner"
        text = re.sub(r'\b\*\*Winner\b', '', text, flags=re.I)
    elif re.search(r'\bWinner\b', text, re.I):
        status = "Winner"
        text = re.sub(r'\bWinner\b', '', text, flags=re.I)
    elif re.search(nominee_word_re, text, re.I):
        status = "Nominee"
        text = re.sub(nominee_word_re, '', text, flags=re.I)
    
    # 7. Nettoyer l'année du reste du texte et mots clés redondants
    if year:
        text = re.sub(r'\b' + re.escape(year) + r'\b', '', text)
    text = re.sub(r'\bAward\s*:\s*', '', text, flags=re.I)
    
    # Enlever "Award -" si présent (pour éviter double "Award - Award -")
    text = re.sub(r'^Award\s*-\s*', '', text, flags=re.I)
    
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.lstrip('- :').strip()

    # Enlever les restes de tokens vides et ponctuation parasite
    text = re.sub(r'\[\s*\]', '', text)
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    # Ne pas supprimer les ellipses en fin de ligne: elles peuvent indiquer
    # un intitulé tronqué (préférable à une perte d'info).
    
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

    # Si le texte est déjà groupé avec des entêtes (Winner/Nomine/Autres),
    # injecter le statut dans les lignes suivantes pour préserver l'info
    # même si les suffixes "[Winner]"/"[Nominee]" sont absents.
    try:
        raw_lines = [ln.rstrip() for ln in text.splitlines()]

        def _header_status(line: str) -> Optional[str]:
            l = (line or '').strip().casefold()
            if l == 'winner':
                return 'Winner'
            if l in ('nominee', 'nomine', 'nominé'):
                return 'Nominee'
            if l in ('autres', 'others', 'other'):
                return ''
            return None

        if any(_header_status(ln) is not None for ln in raw_lines):
            current_status: str = ''
            out_lines: List[str] = []
            for ln in raw_lines:
                stripped = (ln or '').strip()
                if not stripped:
                    continue

                hs = _header_status(stripped)
                if hs is not None:
                    current_status = hs
                    continue

                if current_status and not re.search(
                    r"\bWinner\b|\bNomin(?:ee|e)?\b|\[\s*(winner|nominee|nomine|nomin)\s*\]",
                    stripped,
                    re.I,
                ):
                    out_lines.append(f"{current_status}: {stripped}")
                else:
                    out_lines.append(stripped)
            text = "\n".join(out_lines)
    except Exception:
        pass
    
    # Séparer les phrases avec ponctuation forte
    text = re.sub(r'([.!])\s+([A-Z])', r'\1\n\2', text)
    
    # Séparer quand une nouvelle année + org apparaît (mais pas le premier)
    text = re.sub(r'(\d{4})\s+(?=\d{4}\s+(?:AVN|XBIZ))', r'\1\n', text, flags=re.I)
    
    # Séparer "Boobs2016" -> "Boobs\n2016"  
    text = re.sub(r'([a-z])(\d{4}\s+(?:Winner|Nomin(?:ee|e)?))', r'\1\n\2', text, flags=re.I)

    # Séparer les blocs collés où une année démarre un nouvel award en milieu de ligne
    # ex: "... Now!2016 ..." ou "...(2017)2018 Best ..."
    text = re.sub(r'([\w\)!\]])((?:19|20)\d{2})(?=\s)', r'\1\n\2', text)
    text = re.sub(
        r'\b((?:19|20)\d{2})\s+(?=(?:Best|Most|Winner|Nominee|Nomine|Nomin(?:ee|e)?|AVN|XBIZ|XRCO|NightMoves|PornHub|Spank|Female|Miss|Breakthrough|Girl|Cosplay|Fan|Special|America))',
        r'\n\1 ',
        text,
        flags=re.I,
    )
    
    lines = text.split('\n')
    cleaned_lines = []
    active_status = ""
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        # Propager le statut actif quand des lignes ont été découpées
        # (ex: "Winner: ...2016 ..." -> la 2e ligne garde Winner)
        status_prefix = re.match(r'^(Winner|Nominee|Nomine|Nomin(?:ee|e)?)\s*:\s*(.+)$', line, re.I)
        if status_prefix:
            st = (status_prefix.group(1) or "").strip().lower()
            active_status = "Winner" if st == "winner" else "Nominee"
            line = status_prefix.group(2).strip()
        elif active_status and re.match(r'^(19|20)\d{2}\b', line) and not re.search(r'\b(Winner|Nominee|Nomine|Nomin(?:ee|e)?)\b', line, re.I):
            line = f"{active_status}: {line}"
        
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
        status_count = len(re.findall(r'\b(Winner|Nominee|Nomine|Nomin(?:ee|e)?):', line, re.I))
        
        # Détecter aussi les awards sans status explicite mais avec patterns répétés
        # Exemple : "Best X, Title(year)Best Y, Title2(year)" 
        best_patterns = len(re.findall(r'\bBest\s+[A-Z]', line))
        
        # Détecter les collages après parenthèses : ")Word" sans espace
        parenthesis_collisions = len(re.findall(r'\)[A-Z][a-z]', line))
        
        # Si plusieurs "Best" ou collisions après parenthèses, séparer
        if best_patterns > 2 or parenthesis_collisions > 0:
            # Séparer aussi sur les enchaînements "... Best X Best Y ..." (souvent collés en une ligne)
            if best_patterns > 2:
                line = re.sub(r'\s+(?=Best\s+)', r'\n', line)

            # Séparer quand un mot title-case suit immédiatement une parenthèse fermante
            line = re.sub(r'\)([A-Z][a-z]+)', r')\n\1', line)
            # Séparer aussi sur les patterns ")Best" ou ")Nominee:" ou ")Winner:"
            line = re.sub(r'\)(Best|Winner|Nominee|Nomine|Nomin(?:ee|e)?)', r')\n\1', line, flags=re.I)
            
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
            if not prefix_match:
                prefix_match = re.match(r'^(\d{4})', line)
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
            line = re.sub(r'\)(Winner|Nominee|Nomine|Nomin(?:ee|e)?):', r')\n\1:', line, flags=re.I)
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
            parts = re.split(r'\s+(Winner|Nominee|Nomine|Nomin(?:ee|e)?):\s*', line)
            
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
    
    # Dédupliquer (clé canonique) en ignorant le statut pour éviter doublons
    # et en préférant la version avec statut si disponible.
    unique_lines: List[str] = []
    canonical_to_index: Dict[str, int] = {}

    def _canonical_key(s: str) -> str:
        low = s.lower()
        low = re.sub(r'\[(winner|nominee|nomine|nomin)\]', '', low)
        low = re.sub(r'\b(winner|nominee|nomine|nomin)\b', '', low)
        return re.sub(r'[^a-z0-9]+', '', low)

    def _status_rank(s: str) -> int:
        l = (s or '').lower()
        if '[winner]' in l or re.search(r'\bwinner\b', l):
            return 2
        if (
            '[nominee]' in l
            or '[nomine]' in l
            or '[nomin]' in l
            or re.search(r'\bnominee\b', l)
            or re.search(r'\bnomine\b', l)
            or re.search(r'\bnomin\b', l)
        ):
            return 1
        return 0

    for line in cleaned_lines:
        key = _canonical_key(line)
        if not key:
            continue
        if key not in canonical_to_index:
            canonical_to_index[key] = len(unique_lines)
            unique_lines.append(line)
            continue

        # Déjà vu: préférer Winner > Nominee > aucune info
        idx = canonical_to_index[key]
        if _status_rank(line) > _status_rank(unique_lines[idx]):
            unique_lines[idx] = line

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
        elif '[nominee]' in low or '[nomine]' in low or '[nomin]' in low:
            nominees.append(line)
        else:
            others.append(line)

    winners.sort(key=lambda l: (_extract_year(l), _extract_org_rank(l), l.lower()))
    nominees.sort(key=lambda l: (_extract_org_rank(l), _extract_year(l), l.lower()))
    others.sort(key=lambda l: (_extract_year(l), _extract_org_rank(l), l.lower()))

    # Sortie: uniquement des lignes d'awards, sans en-têtes "Winner/Nominee".
    final_lines = winners + nominees + others
    return "\n".join(final_lines).strip()


def format_awards_grouped(
    awards_text: str,
    *,
    require_year: bool = True,
    include_headers: bool = True,
    sort_alpha_within_group: bool = True,
) -> str:
    """Nettoie et regroupe les awards en sections Winner/Nominee.

    - Ajoute des entêtes (Winner/Nominee/Autres) si demandé.
    - Filtre les lignes sans année si require_year=True.
    - Trie alphabétiquement dans chaque groupe si demandé.
    """
    if not awards_text or not isinstance(awards_text, str):
        return ""

    cleaned = clean_awards_field(awards_text)
    if not cleaned:
        return ""

    lines = [l.strip() for l in cleaned.splitlines() if l.strip()]

    def _extract(line: str) -> Tuple[Optional[int], str, str, str]:
        # year, org, category, status
        m = re.match(
            r'^\s*(\d{4})\s+(.*?)\s*-\s*(.+?)(?:\s*\[(Winner|Nominee|Nomine|Nomin(?:ee|e)?)\])?\s*$',
            line,
            re.I,
        )
        if m:
            year = int(m.group(1))
            org = (m.group(2) or "").strip()
            category = (m.group(3) or "").strip()
            status = (m.group(4) or "").strip().title()
            if status and status.lower().startswith('nomin'):
                status = 'Nominee'
            return year, org, category, status
        m2 = re.match(r'^\s*(\d{4})\s*[-–]\s*(.+?)(?:\s*\[(Winner|Nominee|Nomine|Nomin(?:ee|e)?)\])?\s*$', line, re.I)
        if m2:
            year = int(m2.group(1))
            category = (m2.group(2) or "").strip()
            status = (m2.group(3) or "").strip().title()
            if status and status.lower().startswith('nomin'):
                status = 'Nominee'
            return year, "", category, status
        y = re.search(r'\b(19|20)\d{2}\b', line)
        year = int(y.group(0)) if y else None
        st = ""
        if re.search(r'\[\s*winner\s*\]', line, re.I):
            st = "Winner"
        elif re.search(r'\[\s*(nominee|nomine|nomin)\s*\]', line, re.I):
            st = "Nominee"
        return year, "", line.strip(), st

    winners: List[str] = []
    nominees: List[str] = []
    others: List[str] = []
    for l in lines:
        year, _org, _category, status = _extract(l)
        if require_year and year is None:
            continue
        sl = (status or "").lower()
        if sl == 'winner':
            winners.append(l)
        elif sl == 'nominee':
            nominees.append(l)
        else:
            others.append(l)

    def _chrono_key(line: str):
        year, org, category, _status = _extract(line)
        return (
            int(year or 9999),
            (org or '').lower(),
            re.sub(r'\s+', ' ', (category or '').lower()).strip(),
            line.lower(),
        )

    if sort_alpha_within_group:
        # Tri chronologique demandé (par année), puis org/catégorie
        winners.sort(key=_chrono_key)
        nominees.sort(key=_chrono_key)
        others.sort(key=_chrono_key)

    def _drop_inline_status_suffix(line: str) -> str:
        # Les entêtes de section portent déjà le statut.
        return re.sub(
            r"\s*\[\s*(Winner|Nominee|Nomine|Nomin(?:ee|e)?)\s*\]\s*$",
            "",
            (line or "").strip(),
            flags=re.I,
        ).strip()

    if not include_headers:
        return "\n".join(winners + nominees + others).strip()

    out: List[str] = []
    if winners:
        out.append("Winner")
        out.extend([_drop_inline_status_suffix(x) for x in winners])
        out.append("")
    if nominees:
        out.append("Nomine")
        out.extend([_drop_inline_status_suffix(x) for x in nominees])
        out.append("")
    if others:
        out.append("Autres")
        out.extend([_drop_inline_status_suffix(x) for x in others])
        out.append("")

    return "\n".join(out).strip()

