"""
Extracteur FreeOnes — source primaire pour trivia et bio.
Sépare details / trivia / awards contrairement au V1.
"""
import re
import html as html_std

from services.extractors.base import BaseExtractor
from utils.body_art_parser import parse_body_art


# Regex multi-ceremonies pour extraire les awards du texte
AWARD_PATTERN = re.compile(
    r'((?:\d{4}\s+)?(?:AVN|XBIZ|XRCO|NightMoves|XCritic|AEBN|AdultFilmDatabase'
    r'|Fans of Adult|TEA|GayVN|Grabby|Urban X|CAVR|Inked)[^\n.;]*)',
    re.I
)


class FreeonesExtractor(BaseExtractor):
    SOURCE_NAME = "freeones"

    def build_url(self, performer_name: str) -> str | None:
        """Construire l'URL FreeOnes depuis le nom."""
        slug = self._normalize_name(performer_name)
        return f"https://www.freeones.com/{slug}/bio"

    def extract_from_url(self, url: str) -> dict:
        data = self._empty_result(url)

        tree = self._fetch_tree(url)
        if tree is None:
            return data

        # ── Phase 1 — Métadonnées ───────────────────────────────
        data["name"] = self._get_text(tree, '//h1/text()') or self._get_text(tree, '//h1//text()')
        
        aliases_el = self._get_stat(tree, "Aliases") or self._get_stat(tree, "Also Known As")
        if aliases_el:
            data["aliases"] = [a.strip() for a in aliases_el.split(',') if a.strip()]

        data["birthdate"] = self._get_stat(tree, "Date of Birth") or self._get_stat(tree, "Birthday")
        data["country"] = self._get_stat(tree, "Place of Birth") or self._get_stat(tree, "Birthplace")
        data["ethnicity"] = self._get_stat(tree, "Ethnicity")
        data["hair_color"] = self._get_stat(tree, "Hair Color") or self._get_stat(tree, "Hair")
        data["eye_color"] = self._get_stat(tree, "Eye Color") or self._get_stat(tree, "Eyes")
        data["height"] = self._get_stat(tree, "Height")
        data["weight"] = self._get_stat(tree, "Weight")

        # Ethnie : Essayer de récupérer via les liens si le texte simple échoue
        if not data["ethnicity"]:
            eth_links = tree.xpath('//a[contains(@href, "/ethnicity/")]/text()')
            if eth_links:
                data["ethnicity"] = eth_links[0].strip()

        data["measurements"] = self._get_stat(tree, "Measurements")
        
        # Si pas de measurements, essayer de construire depuis Bust/Waist/Hip
        if not data["measurements"]:
            bust = self._get_stat(tree, "Bust")
            waist = self._get_stat(tree, "Waist")
            hip = self._get_stat(tree, "Hip")
            if bust and waist and hip:
                data["measurements"] = f"{bust}-{waist}-{hip}"
        
        # Normalisation Mensurations (Conversion CM -> Pouces si nécessaire)
        if data["measurements"]:
            try:
                # Si les valeurs semblent être en cm (toutes > 50), on convertit
                parts = re.findall(r'\d+', data["measurements"])
                if len(parts) == 3 and all(int(x) > 50 for x in parts):
                    imperial = [str(round(int(x) / 2.54)) for x in parts]
                    data["measurements"] = "-".join(imperial)
            except Exception:
                pass

        data["fake_tits"] = self._get_stat(tree, "Boobs") or self._get_stat(tree, "Enhanced")
        
        # Career Length : Combiner Start/End si Years Active est vide
        data["career_length"] = self._get_stat(tree, "Career Start") or self._get_stat(tree, "Years Active")
        if not data["career_length"]:
            start = self._get_stat(tree, "Career Start") or self._get_stat(tree, "Started")
            end = self._get_stat(tree, "Career End") or self._get_stat(tree, "Ended") or "Present"
            if start:
                data["career_length"] = f"{start}-{end}"

        # ── Bio / Details ───────────────────────────────────────
        bio_xpaths = [
            '//div[@data-test="biography"]//text()[normalize-space()]',
            '//div[contains(@class,"biography")]//text()[normalize-space()]',
            '//div[@class="bio"]//text()[normalize-space()]',
        ]
        for xpath in bio_xpaths:
            bio_texts = tree.xpath(xpath)
            if bio_texts:
                bio = " ".join(t.strip() for t in bio_texts if t.strip())
                if len(bio) > 20:
                    data["details"] = bio
                    break

        # ── Trivia / Additional Information ─────────────────────
        trivia_xpaths = [
            (
                "//p[normalize-space(text())='Additional Information']"
                "/following-sibling::div[contains(@class,'hide-on-edit')]"
                "//text()[normalize-space()]"
            ),
            (
                "//h3[contains(text(),'Additional')]"
                "/following-sibling::div//text()[normalize-space()]"
            ),
            (
                "//div[contains(@class,'additional')]"
                "//text()[normalize-space()]"
            ),
        ]
        for xpath in trivia_xpaths:
            trivia_texts = tree.xpath(xpath)
            if trivia_texts:
                raw = " ".join(t.strip() for t in trivia_texts if t.strip())
                if len(raw) > 10:
                    data["trivia"] = html_std.unescape(raw)
                    break

        # ── Awards (regex depuis texte bio + trivia) ────────────
        combined = (data.get("details") or "") + " " + (data.get("trivia") or "")
        if combined.strip():
            matches = AWARD_PATTERN.findall(combined)
            data["awards"] = [m.strip() for m in matches if m.strip()]

        # ── Tattoos ─────────────────────────────────────────────
        tattoo_text = self._get_stat(tree, "Tattoos")
        data["tattoos"] = parse_body_art(tattoo_text) if tattoo_text else []

        # ── Piercings ───────────────────────────────────────────
        piercing_text = self._get_stat(tree, "Piercings")
        data["piercings"] = parse_body_art(piercing_text) if piercing_text else []

        # ── Tags (catégories) ───────────────────────────────────
        tag_xpaths = [
            "//a[contains(@href,'/category/')]//text()",
            "//a[contains(@href,'/tag/')]//text()",
            "//div[contains(@class,'tag')]//a/text()",
        ]
        for xpath in tag_xpaths:
            tags_raw = self._get_texts(tree, xpath)
            if tags_raw:
                data["tags"] = [t.strip() for t in tags_raw if t.strip() and len(t.strip()) > 1]
                break

        # ── URLs ────────────────────────────────────────────────
        data["urls"]["freeones"] = url

        # Extraire les liens vers databases extérieures
        links = tree.xpath('//a[contains(@class,"link") or contains(@class,"database")]/@href')
        for link in links:
            link = link.strip()
            if "iafd.com" in link:
                data["urls"]["iafd"] = link
            elif "babepedia.com" in link:
                data["urls"]["babepedia"] = link
            elif "thenude" in link:
                data["urls"]["thenude"] = link
            elif "twitter.com" in link or "x.com" in link:
                data["urls"]["twitter"] = link
            elif "instagram.com" in link:
                data["urls"]["instagram"] = link

        return data

    def _get_stat(self, tree, label: str) -> str | None:
        """Extraire une stat depuis la page FreeOnes."""
        label_slug = label.lower().replace(" ", "-")
        xpaths = [
            f'//span[contains(text(), "{label}")]/following-sibling::span[1]',
            f'//p[contains(@data-test, "{label.lower()}")]',
            f'//p[contains(@data-test, "{label_slug}")]',
            f'//div[contains(@data-test, "{label.lower()}")]',
            f'//div[contains(@data-test, "{label_slug}")]',
            f'//a[contains(@data-test, "{label_slug}")]',
            f'//td[contains(text(), "{label}")]/following-sibling::td[1]',
            f'//*[contains(text(), "{label}")]/following-sibling::*[1]',
        ]
        for xpath in xpaths:
            val = self._get_text(tree, xpath)
            if val:
                return val
        return None
