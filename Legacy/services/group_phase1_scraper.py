"""
GroupPhase1ScraperService — Orchestre le scraping des métadonnées DVD/Group.
"""
from services.extractors.dvd.data18_dvd import Data18DVDExtractor
from services.extractors.dvd.adultempire_dvd import AdultEmpireDVDExtractor
from services.extractors.dvd.iafd_dvd import IafdDVDExtractor
from services.extractors.dvd.jeedoo_dvd import JedeeDVDExtractor

class GroupPhase1ScraperService:
    def __init__(self):
        self.extractors = {
            "data18": Data18DVDExtractor(),
            "adultdvdempire": AdultEmpireDVDExtractor(),
            "iafd_dvd": IafdDVDExtractor(),
            "jeedoo": JedeeDVDExtractor(),
        }

    def scrape(self, title: str, year: str = None, known_urls: list = None, progress_callback=None) -> list[dict]:
        results = []
        known_urls = known_urls or []

        # 1. Utiliser les URLs connues
        for url in known_urls:
            extractor = self._find_extractor_for_url(url)
            if extractor:
                if progress_callback:
                    progress_callback(extractor.SOURCE_NAME, "Fetching from known URL...")
                res = extractor.extract_from_url(url)
                if res and res.get("title"):
                    results.append(res)

        # 2. Si Data18 n'est pas trouvé dans les URLs connues, essayer de deviner l'URL
        has_data18 = any(r.get("_source") == "data18" for r in results)
        if not has_data18:
            data18 = self.extractors["data18"]
            candidates = data18.search_urls(title)
            # Pas de boucle ici si search_urls ne fait que des guesses simples qui ont peu de chance de marcher
            # Mais on essaie quand même les guesses simples
            for url in candidates:
                if progress_callback:
                    progress_callback("data18", f"Trying candidate: {url}...")
                res = data18.extract_from_url(url)
                if res and res.get("title"):
                    results.append(res)
                    break # Found one valid Data18 page

        # 3. Si pas de résultat ou pour compléter, essayer IAFD par titre
        has_iafd = any(r.get("_source") == "iafd_dvd" for r in results)
        if not has_iafd:
            # Essayer IAFD par titre
            iafd = self.extractors["iafd_dvd"]
            url = iafd.build_url_from_title(title, year)
            if progress_callback:
                progress_callback("iafd_dvd", f"Searching for {title}...")
            res = iafd.extract_from_url(url)
            if res and res.get("title"):
                results.append(res)

        return results

    def _find_extractor_for_url(self, url: str):
        if "data18.com" in url: return self.extractors["data18"]
        if "adultdvdempire.com" in url: return self.extractors["adultdvdempire"]
        if "iafd.com" in url: return self.extractors["iafd_dvd"]
        if "jeedoo.com" in url: return self.extractors["jeedoo"]
        return None
