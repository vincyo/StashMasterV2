"""
Phase2ScraperService — orchestre les 4 extracteurs et gère le cache.
"""
from services.scrape_cache import ScrapeCache
from services.extractors.iafd import IafdExtractor
from services.extractors.freeones import FreeonesExtractor
from services.extractors.thenude import ThenudeExtractor
from services.extractors.babepedia import BabepediaExtractor


class Phase2ScraperService:
    """
    Lance le scraping Phase 2 sur toutes les sources disponibles.
    
    Utilise le ScrapeCache pour éviter le double scraping.
    Construit les URLs automatiquement si non disponibles.
    """

    def __init__(self):
        self.extractors = [
            IafdExtractor(),
            FreeonesExtractor(),
            ThenudeExtractor(),
            BabepediaExtractor(),
        ]

    def scrape(
        self,
        performer_name: str,
        known_urls: list[str] | None = None,
        progress_callback=None,
    ) -> list[dict]:
        """
        Scraper toutes les sources pour un performer.
        
        Args:
            performer_name: Nom du performer
            known_urls: URLs déjà connues (depuis DB Stash)
            progress_callback: Callback(source_name, status) pour le progrès
            
        Returns:
            Liste de dicts Phase 2 (un par source réussie)
        """
        results = []
        known_urls = known_urls or []

        # Mapper les URLs connues par source
        url_map = self._map_urls_to_sources(known_urls)

        for i, extractor in enumerate(self.extractors):
            source = extractor.SOURCE_NAME
            
            if progress_callback:
                progress_callback(source, f"Scraping {source}...")

            # Déterminer l'URL à utiliser
            url = url_map.get(source)
            if not url:
                url = extractor.build_url(performer_name)
            
            if not url:
                print(f"[Phase2Scraper] Pas d'URL pour {source}, skip")
                continue

            try:
                # Vérifier le cache d'abord
                cached = ScrapeCache.get(url)
                if cached:
                    print(f"[Phase2Scraper] Cache hit pour {source}: {url}")
                    results.append(cached)
                    continue

                # Scraper
                print(f"[Phase2Scraper] Scraping {source}: {url}")
                data = extractor.extract_from_url(url)
                
                if data:
                    # Stocker en cache
                    ScrapeCache.set(url, data)
                    results.append(data)
                    print(f"[Phase2Scraper] {source} OK — "
                          f"awards:{len(data.get('awards',[]))}, "
                          f"tags:{len(data.get('tags',[]))}, "
                          f"tattoos:{len(data.get('tattoos',[]))}")
                          
            except Exception as e:
                print(f"[Phase2Scraper] Erreur {source}: {e}")
                if progress_callback:
                    progress_callback(source, f"Erreur: {e}")

        if progress_callback:
            progress_callback("done", f"Scraping terminé — {len(results)} sources")

        return results

    def _map_urls_to_sources(self, urls: list[str]) -> dict[str, str]:
        """Mapper les URLs connues aux noms de source."""
        url_map = {}
        for url in urls:
            url_lower = url.lower()
            if "iafd.com" in url_lower:
                url_map["iafd"] = url
            elif "freeones.com" in url_lower:
                url_map["freeones"] = url
            elif "thenude.com" in url_lower or "thenude.eu" in url_lower:
                url_map["thenude"] = url
            elif "babepedia.com" in url_lower:
                url_map["babepedia"] = url
        return url_map
