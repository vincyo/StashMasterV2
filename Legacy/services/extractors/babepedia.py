"""
Extracteur Babepedia — source pour bio courte, tattoos/piercings
avec parsing amélioré, et tags.
"""
import re

from services.extractors.base import BaseExtractor
from utils.body_art_parser import parse_body_art


class BabepediaExtractor(BaseExtractor):
    SOURCE_NAME = "babepedia"

    def build_url(self, performer_name: str) -> str | None:
        """Construire l'URL Babepedia depuis le nom."""
        # Babepedia utilise le nom with espaces → underscores
        slug = self._normalize_name_underscore(performer_name)
        return f"https://www.babepedia.com/babe/{slug}"

    def extract_from_url(self, url: str) -> dict:
        data = self._empty_result(url)

        tree = self._fetch_tree(url)
        if tree is None:
            return data

        # ── Phase 1 — Métadonnées ───────────────────────────────
        data["name"] = self._get_text(tree, '//h1/text()') or self._get_text(tree, '//h1//text()')
        
        aliases_text = self._get_stat(tree, "Aliases") or self._get_stat(tree, "Also known as")
        if aliases_text:
            data["aliases"] = [a.strip() for a in aliases_text.split(',') if a.strip()]

        data["birthdate"] = self._get_stat(tree, "Born") or self._get_stat(tree, "Birthday")
        data["country"] = self._get_stat(tree, "Birthplace")
        data["ethnicity"] = self._get_stat(tree, "Ethnicity")
        data["hair_color"] = self._get_stat(tree, "Hair color") or self._get_stat(tree, "Hair")
        data["eye_color"] = self._get_stat(tree, "Eye color") or self._get_stat(tree, "Eyes")
        data["height"] = self._get_stat(tree, "Height")
        data["weight"] = self._get_stat(tree, "Weight")
        data["measurements"] = self._get_stat(tree, "Measurements")
        data["fake_tits"] = self._get_stat(tree, "Boobs")

        # ── Bio / Details ───────────────────────────────────────
        bio_xpaths = [
            '//p[@id="biotext"]/text()',
            '//div[@id="bio"]//text()',
            '//div[contains(@class,"bio")]//text()',
        ]
        for xpath in bio_xpaths:
            texts = tree.xpath(xpath)
            if texts:
                bio = " ".join(t.strip() for t in texts if t.strip())
                if len(bio) > 20:
                    data["details"] = bio
                    break

        # ── Tattoos ─────────────────────────────────────────────
        tattoo_text = self._get_stat(tree, "Tattoos")
        data["tattoos"] = parse_body_art(tattoo_text) if tattoo_text else []

        # ── Piercings ───────────────────────────────────────────
        piercing_text = self._get_stat(tree, "Piercings")
        data["piercings"] = parse_body_art(piercing_text) if piercing_text else []

# ── Tags — stratégie multi-fallback ──────────────────────────────
        tags = []

        # Stratégie 1 : meta keywords (le plus fiable)
        meta_kw = tree.xpath('//meta[@name="keywords"]/@content')
        if meta_kw and meta_kw[0].strip():
            tags = [t.strip() for t in meta_kw[0].split(',')
                    if t.strip() and len(t.strip()) > 2]

        # Stratégie 2 : liens /tag/ ou /category/ dans la page
        if not tags:
            raw = tree.xpath(
                '//a[contains(@href,"/tag/") or contains(@href,"/category/")]/text()'
            )
            tags = [t.strip() for t in raw if t.strip() and len(t.strip()) > 2]

        # Stratégie 3 : balises spécifiques Babepedia
        if not tags:
            raw = tree.xpath('//span[@class="tag"]/text() | //div[@class="tags"]//text()')
            tags = [t.strip() for t in raw if t.strip() and len(t.strip()) > 2]

        data["tags"] = list(dict.fromkeys(tags))[:50]  # dédupliquer, limiter à 50

        # ── URLs ────────────────────────────────────────────────
        data["urls"]["babepedia"] = url

        # Extraire liens vers d'autres databases
        links = tree.xpath('//a[contains(@href, "http")]/@href')
        for link in links:
            link = link.strip()
            if "iafd.com" in link:
                data["urls"]["iafd"] = link
            elif "freeones.com" in link:
                data["urls"]["freeones"] = link
            elif "thenude" in link:
                data["urls"]["thenude"] = link
            elif "twitter.com" in link or "x.com" in link:
                data["urls"]["twitter"] = link
            elif "instagram.com" in link:
                data["urls"]["instagram"] = link

        return data

    def _get_stat(self, tree, label: str) -> str | None:
        """Extraire une stat de Babepedia (format tableau)."""
        xpaths = [
            f'//td[contains(text(), "{label}")]/following-sibling::td[1]',
            f'//span[contains(text(), "{label}")]/following-sibling::span[1]',
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
