"""
JedeeDVDExtractor — Extracteur Jeedoo pour productions européennes.
Source P4 (priorité basse — spécialisé europe).
"""
from services.extractors.dvd.base_dvd import BaseExtractorDVD


class JedeeDVDExtractor(BaseExtractorDVD):
    SOURCE_NAME = "jeedoo"
    BASE_URL = "https://www.jeedoo.com/"

    def extract_from_url(self, url: str) -> dict:
        data = self._empty_result(url)
        tree = self._fetch_tree(url)
        if tree is None:
            return data

        data["title"] = self._get_text(tree, '//h1/text()')
        data["date"] = self._get_text(tree,
            '//span[contains(@class,"date")]/text() | '
            '//p[contains(text(),"Année")]/following-sibling::p[1]/text()')
        data["studio"] = self._get_text(tree,
            '//a[contains(@href,"/studio/")]/text()')
        data["director"] = self._get_text(tree,
            '//p[contains(text(),"Réalisateur")]/following-sibling::p[1]/text()')
        data["duration"] = self._get_text(tree,
            '//p[contains(text(),"Durée")]/following-sibling::p[1]/text()')
        data["description"] = self._get_text(tree,
            '//div[contains(@class,"description")]//text()')

        tags = tree.xpath('//a[contains(@href,"/categorie/")]/text()')
        data["tags"] = [t.strip() for t in tags if t.strip()]

        data["scenes"] = []  # Jeedoo ne liste pas les scènes individuellement
        data["urls"] = {"jeedoo": url}

        return data
