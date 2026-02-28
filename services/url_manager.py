import re
import requests
import time
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

# Import des scrapers
from services.scrapers import (
    IAFDScraper, FreeOnesScraper, TheNudeScraper, 
    BabepediaScraper, BoobpediaScraper, XXXBiosScraper,
    _fetch, HEADERS, TIMEOUT
)

class URLManager:
    """
    Gère la vérification, le tri et l'acquisition des URLs prioritaires.
    
    Ordre de priorité :
    1. IAFD
    2. FreeOnes
    3. TheNude
    4. Babepedia
    5. Boobpedia
    6. XXXBios
    """
    
    PRIORITY_ORDER = [
        ("iafd.com", IAFDScraper),
        ("freeones.xxx", FreeOnesScraper),
        ("thenude.com", TheNudeScraper),
        ("babepedia.com", BabepediaScraper),
        ("boobpedia.com", BoobpediaScraper),
        ("xxxbios.com", XXXBiosScraper)
    ]

    def __init__(self):
        # Initialisation des scrapers
        self.scrapers = {
            "iafd.com": IAFDScraper(),
            "freeones.xxx": FreeOnesScraper(),
            "thenude.com": TheNudeScraper(),
            "babepedia.com": BabepediaScraper(),
            "boobpedia.com": BoobpediaScraper(),
            "xxxbios.com": XXXBiosScraper()
        }

    def process_performer_urls(self, existing_urls: List[str], performer_name: str, progress_callback=None) -> List[str]:
        """
        Processus complet :
        1. Identification des URLs prioritaires présentes
        2. Validation de ces URLs (ping)
        3. Recherche/Acquisition des URLs manquantes
        4. Nettoyage et validation des autres URLs
        5. Retourne la liste finale triée (Max 50)
        """
        if progress_callback:
            progress_callback(0, "Analyse des URLs existantes...")

        # 1. Structure pour stocker les URLs prioritaires (index 0 à 5)
        priority_slots: List[Optional[str]] = [None] * 6
        other_urls: List[str] = []
        
        # Mapping domain -> index
        domain_to_index = {
            "iafd.com": 0,
            "freeones.xxx": 1, 
            "thenude.com": 2,
            "babepedia.com": 3,
            "boobpedia.com": 4,
            "xxxbios.com": 5
        }

        # 2. Tri des URLs existantes
        for url in existing_urls:
            url = url.strip()
            if not url:
                continue
                
            domain = self.get_domain_key(url)
            
            # Vérifier si c'est un domaine prioritaire
            index = domain_to_index.get(domain)
            
            if index is not None:
                # Si le slot est vide, on prend. Si déjà pris, on garde le "meilleur" (à implémenter si besoin)
                # Ici on prend le premier trouvé qui semble être un profil
                if priority_slots[index] is None:
                     if self.is_profile_url(url, domain):
                         priority_slots[index] = url
                     else:
                         other_urls.append(url)
                else:
                    # Doublon pour ce domaine, on l'ajoute aux autres pour l'instant
                    other_urls.append(url)
            else:
                other_urls.append(url)

        # 3. Validation et Acquisition des manquants
        for i, (domain, scraper_class) in enumerate(self.PRIORITY_ORDER):
            if progress_callback:
                progress_callback(int((i / 6) * 50), f"Vérification {domain}...")

            current_url = priority_slots[i]
            
            # A. Validation si présent
            if current_url:
                if not self.is_url_reachable(current_url):
                    print(f"URL morte détectée : {current_url}")
                    priority_slots[i] = None # On le supprime pour forcer la recherche
                    # On ne l'ajoute pas à other_urls car morte
            
            # B. Acquisition si manquant (ou devenu manquant après validation)
            if priority_slots[i] is None:
                if progress_callback:
                    progress_callback(int((i / 6) * 50) + 5, f"Recherche {domain}...")
                
                found_url = self.search_url_for_domain(domain, performer_name)
                if found_url:
                    priority_slots[i] = found_url

        # 4. Nettoyage et validation des autres URLs
        if progress_callback:
            progress_callback(60, "Validation des autres URLs...")
            
        validated_others = []
        unique_seen = set()
        
        # Ajouter les prioritaires au set pour éviter doublons
        for purl in priority_slots:
            if purl:
                unique_seen.add(purl)

        for url in other_urls:
            if url in unique_seen:
                continue
            
            if self.is_url_reachable(url):
                validated_others.append(url)
                unique_seen.add(url)
        
        # 5. Construction liste finale
        final_list = []
        
        # Ajouter les prioritaires dans l'ordre (1 à 6)
        for url in priority_slots:
            if url:
                final_list.append(url)
                
        # Ajouter le reste
        final_list.extend(validated_others)
        
        # Limiter à 50
        return final_list[:50]

    def get_domain_key(self, url: str) -> str:
        """Normalise le domaine pour correspondre aux clés."""
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if "iafd.com" in netloc: return "iafd.com"
            if "freeones" in netloc: return "freeones.xxx" # Gère freeones.com, freeones.xxx
            if "thenude.com" in netloc: return "thenude.com"
            if "babepedia.com" in netloc: return "babepedia.com"
            if "boobpedia.com" in netloc: return "boobpedia.com"
            if "xxxbios.com" in netloc: return "xxxbios.com"
            return netloc
        except:
            return ""

    def is_profile_url(self, url: str, domain: str) -> bool:
        """Vérifie sommairement si l'URL ressemble à une page profil."""
        # Logique simplifiée, peut être affinée par scraper
        if domain == "iafd.com" and ("person.rme" in url or "person.rvm" in url):
            return True
        if domain == "freeones.xxx" and "/feed/" not in url: return True
        if domain == "thenude.com" and "_" in url: return True
        if domain == "babepedia.com" and "/babe/" in url: return True
        if domain == "boobpedia.com" and "/boobs/" in url: return True
        # XXXBios : doit avoir le pattern exact slug-biography (pas juste -biography)
        if domain == "xxxbios.com":
            # Pattern plus strict : xxxbios.com/[nom-artiste]-biography/
            # Rejette les pages comme xxxbios.com/category/biography
            import re
            # Accepte les slugs avec lettres, chiffres et tirets, se terminant par -biography
            if re.search(r'/[a-z0-9][a-z0-9-]*-biography/?$', url, re.I):
                return True
            return False
        return True 

    def is_url_reachable(self, url: str) -> bool:
        """Vérifie si l'URL répond (code 200)."""
        try:
            # Headers enrichis pour éviter les blocages
            headers = {
                **HEADERS,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
            
            domain_key = self.get_domain_key(url)
            
            # IAFD et Babepedia bloquent les bots (Cloudflare) → on accepte 403 si l'URL correspond au pattern
            if domain_key in ("iafd.com", "babepedia.com"):
                if self.is_profile_url(url, domain_key):
                    # URL valide par structure → on l'accepte même si 403
                    print(f"[URLManager] {domain_key} accepté par pattern : {url}")
                    return True
                # Si ce n'est pas un profil valide, on teste quand même
                resp = requests.get(url, headers=headers, timeout=10, stream=True, allow_redirects=True)
                resp.close()
                print(f"[URLManager] {domain_key} GET → {resp.status_code}")
                # Accepter 200 ou 403 (403 = Cloudflare mais page existe)
                return resp.status_code in (200, 403)
            
            # Pour les autres : HEAD puis GET en fallback
            resp = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            
            if resp.status_code == 200:
                return True
                
            # Si HEAD échoue (405, 403, 404), fallback sur GET
            if resp.status_code in (405, 403, 404):
                resp = requests.get(url, headers=headers, timeout=10, stream=True, allow_redirects=True)
                resp.close()
                return resp.status_code == 200
                
            return False
        except Exception as e:
            print(f"[URLManager] Erreur vérification {url}: {type(e).__name__}: {e}")
            return False

    def search_url_for_domain(self, domain: str, name: str) -> Optional[str]:
        """Tente de trouver l'URL manquante via le scraper associé."""
        scraper = self.scrapers.get(domain)
        if not scraper:
            return None
            
        try:
            # 1. Si le scraper a une méthode 'search' (implémentée pour XXXBios)
            if hasattr(scraper, "search"):
                found_url = scraper.search(name)
                # Valider que l'URL trouvée correspond bien au pattern de profil attendu
                if found_url:
                    if self.is_profile_url(found_url, domain):
                        return found_url
                    else:
                        print(f"[URLManager] URL rejetée pour {domain} (pattern invalide) : {found_url}")
                        return None
                return None
            
            # 2. Construction d'URL (Boobpedia, XXXBios fallback)
            # XXXBiosScraper a build_url, BoobpediaScraper a build_url aussi ?
            # Vérifions les scrapers un par un ou utilisons une logique générique
            
            if domain == "boobpedia.com":
                 slug = re.sub(r"\s+", "_", name.strip().title())
                 url = f"https://www.boobpedia.com/boobs/{slug}"
                 if self.is_url_reachable(url):
                     return url

            if domain == "xxxbios.com":
                 # Fallback si search n'a pas marché (mais search est appelé ci-dessus si dispo)
                 if hasattr(scraper, "build_url"):
                     url = scraper.build_url(name)
                     if self.is_url_reachable(url):
                         return url

            # 3. Pour IAFD, FreeOnes, TheNude, Babepedia
            # Idéalement on utiliserait une recherche Google ou interne
            # Pour l'instant on retourne None si pas de méthode de recherche explicite
            # TODO: Implémenter recherche IAFD/FreeOnes
            
            return None
            
        except Exception as e:
            print(f"Erreur recherche {domain} pour {name}: {e}")
            return None


class URLOptimizer:
    """
    Optimise et nettoie les listes d'URLs en supprimant les paramètres de tracking,
    les doublons et en appliquant un système de priorité.
    """
    
    # Liste de priorité des domaines (plus le score est bas, plus il est prioritaire)
    PRIORITY_MAP = {
        "iafd.com": 1,
        "babepedia.com": 2,
        "freeones.com": 3,
        "freeones.xxx": 3,
        "thenude.com": 4,
        "data18.com": 5,
        "adultfilmdatabase.com": 6,
        "theporndb.net": 7,
        "imdb.com": 8,
        "boobpedia.com": 9,
        "instagram.com": 10,
        "twitter.com": 11,
        "x.com": 12,
        "onlyfans.com": 15,
        "fansly.com": 16,
        "xxxbios.com": 17,
    }
    
    # Domaines à filtrer (publicité, tracking, redirections)
    BLACKLIST_DOMAINS = [
        "google.com",
        "sjv.io",
        "go.ad2up.com",
        "click.",
        "tracker.",
        "affiliate.",
        "redirect.",
    ]

    def clean_url(self, url: str) -> str:
        """Supprime les paramètres de tracking et normalise l'URL"""
        from urllib.parse import urlparse, urlunparse
        
        try:
            u = urlparse(url)
            # Normaliser le netloc en enlevant www.
            netloc = u.netloc.replace("www.", "")
            # On garde uniquement le schéma, le netloc normalisé et le path (pas les query params)
            # Cela supprime tous les utm_, nats, ref, etc.
            clean = urlunparse((u.scheme, netloc, u.path, '', '', ''))
            return clean.rstrip('/')  # Enlever le / final pour éviter les doublons
        except:
            return url

    def is_blacklisted(self, url: str) -> bool:
        """Vérifie si l'URL est dans la blacklist (pub/tracking)"""
        url_lower = url.lower()
        for pattern in self.BLACKLIST_DOMAINS:
            if pattern in url_lower:
                return True
        return False

    def is_valid_profile_url(self, url: str, domain: str, performer_name: str = "") -> bool:
        """Vérifie si l'URL correspond au pattern attendu pour un profil performer."""
        import re
        from urllib.parse import urlparse

        low_url = url.lower()
        path = urlparse(url).path.lower()
        
        # Validation stricte pour certains domaines
        if domain == "xxxbios.com":
            # Doit se terminer par -biography, pas des pages génériques
            if not re.search(r'/[a-z0-9][a-z0-9-]*-biography/?$', url, re.I):
                return False
        
        if domain == "iafd.com" and not ("person.rme" in url or "person.rvm" in url):
            return False
            
        if domain == "babepedia.com" and "/babe/" not in url:
            return False
            
        if domain == "boobpedia.com" and "/boobs/" not in url:
            return False

        # Rejeter les pages manifestement non-profil (scènes, galeries, tracking...)
        bad_path_tokens = [
            '/scene', '/scenes', '/video', '/videos', '/gallery', '/galleries',
            '/image', '/images', '/pics', '/photo', '/photos', '/track/', '/updates',
            '/category/', '/tag/', '/post/', '/episode/', '/clip/', '/clips/'
        ]
        if any(tok in path for tok in bad_path_tokens):
            return False

        # Pour les domaines non stricts, exiger un minimum de correspondance au nom performer
        # pour limiter les pages hors-sujet.
        strict_domains = {'iafd.com', 'thenude.com', 'babepedia.com', 'boobpedia.com', 'xxxbios.com', 'freeones.com', 'freeones.xxx'}
        if performer_name and domain not in strict_domains:
            name = performer_name.strip().lower()
            tokens = [t for t in re.split(r'\s+', name) if len(t) >= 3]
            slug = '-'.join(tokens)
            compact = ''.join(tokens)
            if tokens and not (
                (slug and slug in low_url) or
                (compact and compact in low_url) or
                all(t in low_url for t in tokens[:2])
            ):
                return False
        
        # Autres domaines : accepter par défaut
        return True

    def get_top_urls(self, url_list: List[str], limit: int = 50, performer_name: str = "") -> List[str]:
        """
        Nettoie, déduplique et trie les URLs par priorité.
        Retourne les top URLs jusqu'à la limite spécifiée.
        """
        cleaned_set = set()
        ranked_urls = []

        for raw_url in url_list:
            if not raw_url or not isinstance(raw_url, str):
                continue
                
            # Nettoyage
            url = self.clean_url(raw_url.strip())
            
            # Filtrage blacklist
            if self.is_blacklisted(url):
                continue
            
            # Extraction du domaine
            try:
                domain = urlparse(url).netloc.replace("www.", "").lower()
            except:
                continue
            
            # Validation du pattern de profil
            if not self.is_valid_profile_url(url, domain, performer_name=performer_name):
                print(f"[URLOptimizer] URL rejetée (pattern invalide) : {url}")
                continue
            
            # Éviter les doublons
            if url in cleaned_set:
                continue
            
            # Attribution de la priorité
            priority = self.PRIORITY_MAP.get(domain, 99)  # 99 pour les sites inconnus
            
            ranked_urls.append({
                "url": url,
                "priority": priority,
                "domain": domain
            })
            cleaned_set.add(url)

        # Tri alphabétique demandé
        ranked_urls.sort(key=lambda x: x['url'].lower())
        
        # Retourner uniquement les URLs (pas les métadonnées)
        return [item['url'] for item in ranked_urls[:limit]]
