"""
Extracteur TheNude — source pour bios studio contextualisées.
"""
import re

from services.extractors.base import BaseExtractor
from utils.body_art_parser import parse_body_art


class ThenudeExtractor(BaseExtractor):
    SOURCE_NAME = "thenude"

    def build_url(self, performer_name: str) -> str | None:
        """Construire l'URL TheNude depuis le nom."""
        slug = self._normalize_name_underscore(performer_name)
        return f"https://www.thenude.com/models/{slug}.htm"

    def extract_from_url(self, url: str) -> dict:
        data = self._empty_result(url)

        tree = self._fetch_tree(url)
        if tree is None:
            return data

        # ── Phase 1 — Métadonnées ───────────────────────────────
        data["name"] = self._get_text(tree, '//h1/text()')
        
        aliases_text = self._get_stat(tree, "Aliases") or self._get_stat(tree, "AKA")
        if aliases_text:
            data["aliases"] = [a.strip() for a in aliases_text.split(',') if a.strip()]

        data["birthdate"] = self._get_stat(tree, "Born") or self._get_stat(tree, "Date of Birth")
        data["country"] = self._get_stat(tree, "Birthplace") or self._get_stat(tree, "Country")
        data["ethnicity"] = self._get_stat(tree, "Ethnicity")
        data["hair_color"] = self._get_stat(tree, "Hair")
        data["eye_color"] = self._get_stat(tree, "Eyes")
        data["height"] = self._get_stat(tree, "Height")
        data["weight"] = self._get_stat(tree, "Weight")
        data["measurements"] = self._get_stat(tree, "Measurements")
        data["fake_tits"] = self._get_stat(tree, "Boobs")

        # ── Bio principale ──────────────────────────────────────
        bio_xpaths = [
            '//p[@class="description"]/text()',
            '//div[@class="description"]//text()',
            '//div[contains(@class,"bio")]//text()',
        ]
        for xpath in bio_xpaths:
            texts = tree.xpath(xpath)
            if texts:
                bio = " ".join(t.strip() for t in texts if t.strip())
                if len(bio) > 20:
                    data["details"] = bio
                    break

        # ── Bios studio (trivia) ────────────────────────────────
        studio_bios = self._extract_studio_bios(tree)
        if studio_bios:
            data["trivia"] = "\n\n".join(studio_bios)

        # ── Tattoos ─────────────────────────────────────────────
        tattoo_text = self._get_stat(tree, "Tattoos")
        data["tattoos"] = parse_body_art(tattoo_text) if tattoo_text else []

        # ── Piercings ───────────────────────────────────────────
        piercing_text = self._get_stat(tree, "Piercings")
        data["piercings"] = parse_body_art(piercing_text) if piercing_text else []

        # ── Tags (keywords) ─────────────────────────────────────
        tag_xpaths = [
            '//div[@class="keywords"]//a/text()',
            '//meta[@name="keywords"]/@content',
            '//div[contains(@class,"tag")]//a/text()',
        ]
        for xpath in tag_xpaths:
            tags_raw = tree.xpath(xpath)
            if tags_raw:
                # Si c'est un meta keywords, splitter par virgule
                if len(tags_raw) == 1 and ',' in tags_raw[0]:
                    tags_raw = [t.strip() for t in tags_raw[0].split(',')]
                data["tags"] = [t.strip() for t in tags_raw 
                                if t.strip() and len(t.strip()) > 1]
                break

        # ── URLs ────────────────────────────────────────────────
        data["urls"]["thenude"] = url

        # Extraire les liens vers databases
        links = tree.xpath('//a[contains(@href, "http")]/@href')
        for link in links:
            link = link.strip()
            if "iafd.com" in link:
                data["urls"]["iafd"] = link
            elif "freeones.com" in link:
                data["urls"]["freeones"] = link
            elif "babepedia.com" in link:
                data["urls"]["babepedia"] = link

        return data

    def _extract_studio_bios(self, tree) -> list[str]:
        """Extraire les bios par studio (ex: 'BRAZZERS biography')."""
        studio_bios = []
        
        # Chercher les headers contenant "biography"
        bio_headers = tree.xpath(
            '//*[contains(translate(text(),"BIOGRAPHY","biography"), "biography")]'
        )
        
        for h in bio_headers:
            title = h.text_content().strip()
            if title.lower() == "biography":
                continue

            # Le contenu suit le header
            content_node = h.getnext()
            if content_node is not None:
                content = content_node.text_content().strip()
                if content and len(content) > 20:
                    studio_bios.append(f"[{title}]\n{content}")

        return studio_bios

    def _get_stat(self, tree, label: str) -> str | None:
        """Extraire une stat depuis la page TheNude."""
        xpaths = [
            f'//span[contains(text(), "{label}")]/following-sibling::span[1]',
            f'//td[contains(text(), "{label}")]/following-sibling::td[1]',
            f'//li[contains(., "{label}")]',
            f'//div[contains(@class,"stat")]//*[contains(text(), "{label}")]/..',
        ]
        for xpath in xpaths:
            val = self._get_text(tree, xpath)
            if val:
                # Nettoyer le label du texte si présent
                val = re.sub(rf'^{label}\s*[:]\s*', '', val, flags=re.I).strip()
                if val:
                    return val
        return None
