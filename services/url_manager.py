import re
import requests
import time
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, quote_plus, parse_qs, unquote

# Import des scrapers
from services.scrapers import (
    IAFDScraper, FreeOnesScraper, TheNudeScraper, 
    BabepediaScraper, BoobpediaScraper, XXXBiosScraper,
    _fetch, HEADERS, TIMEOUT
)

class URLManager:
    """
    Gère la vérification, le tri et l'acquisition des URLs prioritaires.
    
    Stratégie 2-tier:
    - 4 sources 1ère passe (utilisées par défaut) : IAFD, FreeOnes, TheNude, XXXBios
    - 2 sources de secours (2ème passe si nécessaire) : Babepedia, Boobpedia
    """
    
    # 4 sources 1ère passe
    PRIMARY_SOURCES = [
        ("iafd.com", IAFDScraper),        # 75% - Métadonnées biographiques
        ("freeones.xxx", FreeOnesScraper), # 65% - Awards, trivia, tags
        ("thenude.com", TheNudeScraper),   # 70% - Bios studio, aliases
        ("xxxbios.com", XXXBiosScraper),   # Infos perso + bio + awards + réseaux sociaux
    ]
    
    # 2 sources de secours (utilisées en 2ème passe si nécessaire)
    FALLBACK_SOURCES = [
        ("babepedia.com", BabepediaScraper),
        ("boobpedia.com", BoobpediaScraper),
    ]
    
    # Liste complète (pour compatibilité)
    PRIORITY_ORDER = PRIMARY_SOURCES + FALLBACK_SOURCES

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

    def _lookup_known_url_from_db(self, domain: str, performer_name: str) -> Optional[str]:
        """Fallback générique: tente de récupérer une URL déjà connue en base pour ce performer+domain."""
        try:
            from services.config_manager import ConfigManager
            from services.database import StashDatabase

            cfg = ConfigManager()
            db = StashDatabase(cfg.get("database_path"))
            conn = db._get_connection()
            cur = conn.cursor()

            # Trouver le performer par nom (insensible à la casse)
            cur.execute("SELECT id FROM performers WHERE lower(name)=lower(?) LIMIT 1", (performer_name,))
            row = cur.fetchone()
            if not row:
                return None

            performer_id = str(row[0])
            cur.execute("SELECT url FROM performer_urls WHERE performer_id=?", (performer_id,))
            urls = [r[0] for r in cur.fetchall() if r and r[0]]

            # Garder les URLs du domaine demandé et valider le pattern profil
            candidates = []
            for u in urls:
                d = self.get_domain_key(u)
                if d != domain:
                    continue
                if self.is_profile_url(u, domain) and self.is_valid_profile_url(u, d, performer_name=performer_name):
                    candidates.append(u)

            if not candidates:
                return None

            # Préférer URL courte et "propre"
            candidates.sort(key=lambda x: (len(x), x.lower()))
            return candidates[0]
        except Exception:
            return None

    def process_performer_urls(self, existing_urls: List[str], performer_name: str, progress_callback=None, use_fallback_sources: bool = False) -> List[str]:
        """
        Processus complet :
        1. Identification des URLs prioritaires présentes
        2. Validation de ces URLs (ping)
        3. Recherche/Acquisition des URLs manquantes
        4. Nettoyage et validation des autres URLs
        5. Retourne la liste finale triée (Max 50)
        
        Args:
            use_fallback_sources: Si False (défaut), utilise seulement les 3 sources primaires.
                                  Si True, utilise les 6 sources (primaires + secours).
        """
        if progress_callback:
            progress_callback(0, "Analyse des URLs existantes...")

        # Déterminer quelles sources utiliser
        active_sources = self.PRIMARY_SOURCES + (self.FALLBACK_SOURCES if use_fallback_sources else [])
        num_sources = len(active_sources)
        
        # 1. Structure pour stocker les URLs prioritaires
        priority_slots: List[Optional[str]] = [None] * num_sources
        other_urls: List[str] = []
        
        # Mapping domain -> index (basé sur les sources actives)
        domain_to_index = {domain: i for i, (domain, _) in enumerate(active_sources)}

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
        for i, (domain, scraper_class) in enumerate(active_sources):
            if progress_callback:
                progress_callback(int((i / num_sources) * 50), f"Vérification {domain}...")

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
                    progress_callback(int((i / num_sources) * 50) + 5, f"Recherche {domain}...")
                
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
            if netloc == "freeones.com" or netloc.endswith(".freeones.com") or netloc == "freeones.xxx" or netloc.endswith(".freeones.xxx"):
                return "freeones.xxx"  # Gère freeones.com, freeones.xxx uniquement
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
        if domain == "freeones.xxx":
            netloc = (urlparse(url).netloc or "").lower()
            if not (netloc == "freeones.com" or netloc.endswith(".freeones.com") or netloc == "freeones.xxx" or netloc.endswith(".freeones.xxx")):
                return False
            return "/feed/" not in url
        if domain == "thenude.com" and "_" in url: return True
        if domain == "babepedia.com" and "/babe/" in url: return True
        if domain == "boobpedia.com":
            low = url.lower()
            if "/boobs/" in low and "/main_page" not in low:
                return True
            return False
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

        # 0) Fallback générique base locale (évite les régressions si recherche distante KO)
        known = self._lookup_known_url_from_db(domain, name)
        if known:
            return known
            
        try:
            # 1) Recherche native du scraper (ex: XXXBios)
            if hasattr(scraper, "search"):
                found_url = scraper.search(name)
                # Valider que l'URL trouvée correspond bien au pattern de profil attendu
                if found_url:
                    if self.is_profile_url(found_url, domain):
                        return found_url
                    else:
                        print(f"[URLManager] URL rejetée pour {domain} (pattern invalide) : {found_url}")
                        return None
                # continue vers autres stratégies si search() n'a rien donné

            # 2) SourceFinder (IAFD / FreeOnes / TheNude / Babepedia)
            sourcefinder_map = {
                "iafd.com": "IAFD",
                "freeones.xxx": "FreeOnes",
                "thenude.com": "TheNude",
                "babepedia.com": "Babepedia",
            }
            sf_source = sourcefinder_map.get(domain)
            if sf_source:
                try:
                    from services.source_finder import SourceFinder
                    finder = SourceFinder(timeout=10, delay=0)
                    result = finder.find_for_source(sf_source, name, aliases=[])
                    found_url = None
                    if result and result.best and result.best.url:
                        found_url = result.best.url
                    elif result and result.candidates:
                        found_url = result.candidates[0].url

                    if found_url:
                        if self.is_profile_url(found_url, domain):
                            return found_url
                        print(f"[URLManager] URL SourceFinder rejetée pour {domain}: {found_url}")
                except Exception as e:
                    print(f"[URLManager] SourceFinder erreur pour {domain}: {e}")

            # 2bis) Fallback direct IAFD via page de résultats
            if domain == "iafd.com":
                try:
                    query = re.sub(r"\s+", "+", name.strip())
                    search_url = (
                        "https://www.iafd.com/results.asp?pagetype=person"
                        f"&searchtype=name&sex=f&q={query}"
                    )
                    soup = _fetch(search_url)
                    if soup:
                        candidates = []
                        for a in soup.find_all("a", href=True):
                            href = a["href"]
                            if "person.rme" not in href and "person.rvm" not in href:
                                continue
                            if href.startswith("/"):
                                href = "https://www.iafd.com" + href
                            txt = (a.get_text() or "").strip().lower()
                            name_l = (name or "").strip().lower()
                            score = 0
                            if name_l and txt == name_l:
                                score += 100
                            elif name_l and name_l in txt:
                                score += 60
                            if "person.rme" in href:
                                score += 10
                            candidates.append((score, href))

                        if candidates:
                            candidates.sort(key=lambda x: x[0], reverse=True)
                            for _, candidate_url in candidates:
                                if self.is_profile_url(candidate_url, domain):
                                    return candidate_url
                except Exception as e:
                    print(f"[URLManager] Fallback IAFD erreur: {e}")
            
            # 3) Construction d'URL directe (Babepedia/Boobpedia + XXXBios fallback)
            if domain == "babepedia.com":
                 name_clean = name.strip()
                 variants = []
                 variants.append(re.sub(r"\s+", "_", name_clean.title()))
                 variants.append(re.sub(r"\s+", "-", name_clean.lower()))
                 variants.append(re.sub(r"\s+", "_", name_clean))

                 tried = set()
                 for slug in variants:
                     if slug in tried:
                         continue
                     tried.add(slug)
                     url = f"https://www.babepedia.com/babe/{slug}"
                     # Babepedia peut répondre 403 malgré une page valide, donc
                     # on s'appuie sur le pattern profil + reachability manager.
                     if self.is_profile_url(url, domain) and self.is_url_reachable(url):
                         return url

            if domain == "boobpedia.com":
                 # Essais de slugs courants
                 name_clean = name.strip()
                 variants = []
                 variants.append(re.sub(r"\s+", "_", name_clean.title()))
                 variants.append(re.sub(r"\s+", "_", name_clean))
                 variants.append(re.sub(r"\s+", "_", name_clean.lower().title()))

                 tried = set()
                 for slug in variants:
                     if slug in tried:
                         continue
                     tried.add(slug)
                     url = f"https://www.boobpedia.com/boobs/{slug}"
                     if self.is_profile_url(url, domain) and self.is_url_reachable(url):
                         return url

            if domain == "thenude.com":
                 # Fallback via barre de recherche principale TheNude (navbar-search)
                 try:
                     from urllib.parse import quote
                     
                     # Endpoint exact du formulaire navbar-search
                     search_url = "https://www.thenude.com/index.php"
                     params = {
                         "page": "search",
                         "action": "searchModels",
                         "__form_name": "navbar-search",
                         "m_aka": "on",
                         "m_name": name.strip()
                     }
                     
                     # Construire l'URL complète
                     param_str = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items())
                     full_url = f"{search_url}?{param_str}"
                     
                     soup = _fetch(full_url)
                     if not soup:
                         print(f"[URLManager] TheNude navbar-search: échec fetch")
                     else:
                         candidates = []
                         for a in soup.find_all("a", href=True):
                             href = a["href"]
                             # Pattern profil TheNude: nom_ID.htm ou _ID.htm
                             if not re.search(r'(?:^|/)_[0-9]+\.htm$|(?:^|/)[^/]+_[0-9]+\.htm$', href, re.I):
                                 continue
                             
                             # Construire URL complète
                             if href.startswith("/"):
                                 href = "https://www.thenude.com" + href
                             elif not href.startswith("http"):
                                 href = "https://www.thenude.com/" + href
                             
                             # Encoder les espaces dans l'URL
                             href = href.replace(" ", "%20")
                             
                             # Scoring basé sur le texte du lien
                             txt = (a.get_text() or "").strip().lower()
                             name_l = (name or "").strip().lower()
                             score = 0
                             if name_l and txt == name_l:
                                 score += 100
                             elif name_l and name_l in txt:
                                 score += 60
                             elif txt and txt in name_l:
                                 score += 40
                             
                             # Bonus si le slug correspond
                             href_lower = href.lower()
                             name_slug = name_l.replace(" ", "-")
                             if name_slug in href_lower:
                                 score += 50
                             
                             candidates.append((score, href))

                         if candidates:
                             candidates.sort(key=lambda x: x[0], reverse=True)
                             print(f"[URLManager] TheNude: {len(candidates)} candidats, meilleur score={candidates[0][0]}")
                             
                             # Prendre le premier avec score > 0 et profil valide
                             for score, candidate_url in candidates:
                                 if score > 0 and self.is_profile_url(candidate_url, domain):
                                     return candidate_url
                 except Exception as e:
                     print(f"[URLManager] Fallback TheNude erreur: {e}")

            if domain == "iafd.com":
                 # Fallback direct : slug IAFD classique perfid=prenom_nom
                 name_clean = name.strip()
                 slug_us = re.sub(r"\s+", "_", name_clean.lower())
                 slug_dash = re.sub(r"\s+", "-", name_clean.lower())
                 url = f"https://www.iafd.com/person.rme/perfid={slug_us}/gender=f/{slug_dash}.htm"
                 if self.is_profile_url(url, domain) and self.is_url_reachable(url):
                     return url

            if domain == "xxxbios.com":
                 # Fallback si search n'a pas marché
                 if hasattr(scraper, "build_url"):
                     url = scraper.build_url(name)
                     if self.is_profile_url(url, domain) and self.is_url_reachable(url):
                         return url
            
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

    SOCIAL_DOMAINS = {
        "instagram.com", "x.com", "twitter.com", "onlyfans.com", "fansly.com",
        "tiktok.com", "youtube.com", "twitch.tv", "allmylinks.com", "linktr.ee",
        "cash.app", "tumblr.com", "threads.net", "facebook.com"
    }

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
        
        # Réseaux sociaux: acceptés comme groupe séparé
        if any(domain == d or domain.endswith(f".{d}") for d in self.SOCIAL_DOMAINS):
            return True

        # Validation stricte pour certains domaines
        if domain == "xxxbios.com":
            # Doit se terminer par -biography, pas des pages génériques
            if not re.search(r'/[a-z0-9][a-z0-9-]*-biography/?$', url, re.I):
                return False
        
        if domain == "iafd.com" and not ("person.rme" in url or "person.rvm" in url):
            return False

        if domain == "thenude.com":
            # Profil TheNude attendu : /slug_12345.htm OU /_12345.htm
            if not re.search(r'/(?:[^/]*_)?\d+\.htm$', path, re.I):
                return False

        if domain in ("freeones.com", "freeones.xxx"):
            # Profil FreeOnes attendu : /slug ou /slug/bio
            if not re.search(r'^/[a-z0-9][a-z0-9-]+(?:/bio)?$', path, re.I):
                return False
            
        if domain == "babepedia.com" and "/babe/" not in url:
            return False
            
        if domain == "boobpedia.com" and "/boobs/" not in url:
            return False

        # Rejeter pages génériques sans profil
        if domain == "boobpedia.com" and "/main_page" in path:
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
        profile_candidates = []
        social_candidates = []

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
            
            item = {
                "url": url,
                "domain": domain
            }

            if any(domain == d or domain.endswith(f".{d}") for d in self.SOCIAL_DOMAINS):
                social_candidates.append(item)
            else:
                profile_candidates.append(item)

            cleaned_set.add(url)

        # 1 URL par domaine dans chaque groupe (profil / réseaux sociaux)
        def keep_one_per_domain(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
            best_by_domain: Dict[str, Dict[str, str]] = {}
            for item in items:
                dom = item["domain"]
                # garder la première vue (préserve les URLs prioritaires validées)
                if dom not in best_by_domain:
                    best_by_domain[dom] = item
            return list(best_by_domain.values())

        profile_unique = keep_one_per_domain(profile_candidates)
        social_unique = keep_one_per_domain(social_candidates)

        # Tri alphabétique demandé, avec groupe profils puis groupe réseaux sociaux
        profile_unique.sort(key=lambda x: x['url'].lower())
        social_unique.sort(key=lambda x: x['url'].lower())

        final_items = profile_unique + social_unique
        return [item['url'] for item in final_items[:limit]]
