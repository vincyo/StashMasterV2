"""
GroupPhase2ScraperService — Scraping des URLs de scènes individuelles pour un Group.
"""
from services.extractors.dvd.data18_dvd import Data18DVDExtractor
from services.extractors.dvd.adultempire_dvd import AdultEmpireDVDExtractor

class GroupPhase2ScraperService:
    def __init__(self):
        self.extractors = {
            "data18": Data18DVDExtractor(),
            "adultdvdempire": AdultEmpireDVDExtractor(),
        }

    def scrape(self, group_data: dict, progress_callback=None) -> dict[int, dict[str, str]]:
        """
        Retourne : { scene_index: { "source": "url" } }
        """
        all_scene_urls = {} # {index: {source: url}}

        urls = group_data.get("urls", [])
        for url in urls:
            extractor = None
            if "data18.com" in url: extractor = self.extractors["data18"]
            elif "adultdvdempire.com" in url: extractor = self.extractors["adultdvdempire"]
            
            if extractor:
                if progress_callback:
                    progress_callback(extractor.SOURCE_NAME, f"Scraping scene URLs...")
                
                res = extractor.extract_from_url(url)
                scenes = res.get("scenes", [])
                for s in scenes:
                    idx = s.get("index")
                    s_url = s.get("url")
                    if idx and s_url:
                        if idx not in all_scene_urls:
                            all_scene_urls[idx] = {}
                        all_scene_urls[idx][extractor.SOURCE_NAME] = s_url

        return all_scene_urls
