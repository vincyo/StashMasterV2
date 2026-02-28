"""
IafdDVDExtractor — Extracteur IAFD pour les titres DVDs/Groups.
Source P2 (prioritaire pour DVDs classiques US, cast fiable, dates précises).
"""
import re
from services.extractors.dvd.base_dvd import BaseExtractorDVD
from utils.duration import parse_duration_to_seconds


class IafdDVDExtractor(BaseExtractorDVD):
    SOURCE_NAME = "iafd_dvd"
    BASE_URL = "https://www.iafd.com/title.rme/title="

    def build_url_from_title(self, title: str, year: str | None = None) -> str:
        """Construire l'URL de recherche IAFD depuis un titre."""
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        url = f"{self.BASE_URL}{slug}"
        if year:
            url += f"/year={year}"
        return url

    def extract_from_url(self, url: str) -> dict:
        data = self._empty_result(url)

        tree = self._fetch_tree(url)
        if tree is None:
            return data

        # ── Titre ────────────────────────────────────────────────
        data["title"] = self._get_text(tree, '//h1[@itemprop="name"]/text()')
        if not data["title"]:
            data["title"] = self._get_text(tree, '//h1/text()')

        # ── Date / Année ─────────────────────────────────────────
        data["date"] = (self._get_stat(tree, "Release Date") or 
                       self._get_stat(tree, "Year"))

        # ── Studio ───────────────────────────────────────────────
        data["studio"] = (self._get_text(
            tree, '//p[@class="subheading"]/a[1]/text()'
        ) or self._get_stat(tree, "Studio"))

        # ── Réalisateur ──────────────────────────────────────────
        data["director"] = (self._get_text(
            tree, '//p[b[contains(text(),"Director")]]/a/text()'
        ) or self._get_stat(tree, "Director"))

        # ── Durée ────────────────────────────────────────────────
        raw_duration = (self._get_stat(tree, "Running Time") or 
                       self._get_stat(tree, "Duration"))
        if raw_duration:
            data["duration"] = raw_duration
            secs = parse_duration_to_seconds(raw_duration)
            if secs:
                data["_duration_seconds"] = secs

        # ── Description / Synopsis ───────────────────────────────
        data["description"] = (self._get_text(
            tree, '//div[@class="synopsis"]//text()'
        ) or self._get_text(
            tree, '//div[contains(@class,"description")]//text()'
        ))

        # ── Aliases / Titres alternatifs ─────────────────────────
        aliases_text = (self._get_stat(tree, "Alternate Titles") or 
                       self._get_stat(tree, "AKA"))
        if aliases_text:
            data["aliases"] = [a.strip() for a in aliases_text.split(',') if a.strip()]

        # ── Tags / Catégories ────────────────────────────────────
        tags = tree.xpath('//div[@id="genres"]//a/text()')
        if not tags:
            tags = tree.xpath('//a[contains(@href,"/genre/")]/text()')
        data["tags"] = [t.strip() for t in tags if t.strip()]

        # ── Scènes (liste indexée) ───────────────────────────────
        data["scenes"] = self._extract_scenes(tree)

        # ── URLs ─────────────────────────────────────────────────
        data["urls"] = {"iafd_dvd": url}

        return data

    def _extract_scenes(self, tree) -> list[dict]:
        """
        Extraire la liste des scènes du DVD depuis la page IAFD.
        Retourne : [{"index": int, "title": str | None, "performers": [str]}]
        """
        scenes = []

        # IAFD liste les scènes dans un tableau ou une liste ordonnée
        # Structure typique : <div id="sceneinfo"> ou <table class="w100">
        scene_rows = tree.xpath(
            '//div[contains(@id,"scene")] | //tr[contains(@class,"scene")]'
        )

        for i, row in enumerate(scene_rows, start=1):
            scene = {"index": i, "title": None, "performers": [], "url": None}

            # Titre de scène
            title_nodes = row.xpath('.//b/text() | .//strong/text()')
            if title_nodes:
                scene["title"] = title_nodes[0].strip()

            # Performers
            perf_links = row.xpath('.//a[contains(@href,"/person.rme/")]/text()')
            scene["performers"] = [p.strip() for p in perf_links if p.strip()]

            # URL directe de la scène (si disponible)
            scene_link = row.xpath('.//a[contains(@href,"/scene.rme/")]/@href')
            if scene_link:
                scene["url"] = "https://www.iafd.com" + scene_link[0]

            if scene["title"] or scene["performers"]:
                scenes.append(scene)

        return scenes

    def _get_stat(self, tree, label: str) -> str | None:
        """Extraire une valeur depuis les tableaux info IAFD."""
        xpaths = [
            f'//td[contains(text(),"{label}")]/following-sibling::td[1]',
            f'//b[contains(text(),"{label}")]/parent::*/following-sibling::*[1]',
            f'//p[contains(text(),"{label}")]/following-sibling::p[1]',
            f'//span[normalize-space(text())="{label}"]/following-sibling::span[1]',
        ]
        for xpath in xpaths:
            val = self._get_text(tree, xpath)
            if val:
                return val.strip()
        return None
