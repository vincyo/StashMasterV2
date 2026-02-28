"""
BaseExtractorDVD — Base commune pour tous les extracteurs de groupes/DVD.
Similaire à BaseExtractor (performer) mais adapté aux métadonnées group.
"""
from abc import ABC, abstractmethod
import re
import subprocess
from lxml import html as lxml_html
from services.scrape_cache import ScrapeCache


class BaseExtractorDVD(ABC):
    SOURCE_NAME = "unknown"

    def __init__(self):
        self.cache = ScrapeCache()

    def _fetch_tree(self, url: str):
        """Fetch HTML avec cache. Retourne lxml tree ou None."""
        cached = self.cache.get(url)
        if cached:
            return lxml_html.fromstring(cached)
        try:
            result = subprocess.run(
                ["curl", "-sL", "--max-time", "15", url],
                capture_output=True, timeout=20
            )
            html = result.stdout.decode("utf-8", errors="replace")
            if html and len(html) > 500:
                self.cache.set(url, html)
                return lxml_html.fromstring(html)
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Fetch error: {e}")
        return None

    def _get_text(self, tree, xpath: str) -> str | None:
        nodes = tree.xpath(xpath)
        if nodes:
            text = nodes[0] if isinstance(nodes[0], str) else nodes[0].text_content()
            return text.strip() or None
        return None

    def _empty_result(self, url: str) -> dict:
        """Retourne un dict vide standard pour un group."""
        return {
            "_source": self.SOURCE_NAME,
            "_url": url,
            # Métadonnées group (Phase 1)
            "title": None,
            "aliases": None,
            "date": None,
            "studio": None,
            "director": None,
            "duration_raw": None,   # chaîne brute — conversion dans merger
            "description": None,
            "tags": [],
            "front_cover_url": None,
            "back_cover_url": None,
            # Scènes extraites du DVD (Phase 2)
            "scenes": [],   # list[dict] avec clés : index, title, url_source
        }

    @abstractmethod
    def extract_from_url(self, url: str) -> dict:
        """Scraper une URL de group et retourner le dict unifié."""
        ...

    def search_urls(self, title: str, studio: str = "") -> list[str]:
        """
        Recherche de l'URL du group sur la source.
        À implémenter dans chaque sous-classe.
        Retourne une liste d'URLs candidates (max 5).
        """
        return []
