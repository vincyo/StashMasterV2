"""
Extracteur IAFD — source primaire pour les awards.
"""
import re

from services.extractors.base import BaseExtractor
from utils.body_art_parser import parse_body_art


# Lignes parasites à ignorer dans les awards
AWARD_SKIP = re.compile(r'^([-–—]+|nomin[ée]e?d?|winner|won|year|award)$', re.I)

# Regex étendue multi-ceremonies pour fallback texte
AWARD_PATTERN = re.compile(
    r'(\d{4}\s+)?(AVN|XBIZ|XRCO|NightMoves|XCritic|AEBN|AdultFilmDatabase'
    r'|Fans of Adult Media|TEA|GayVN|Grabby|Urban X|CAVR|Inked)[^.\n]*',
    re.I
)


class IafdExtractor(BaseExtractor):
    SOURCE_NAME = "iafd"

    def build_url(self, performer_name: str) -> str | None:
        """Construire l'URL IAFD depuis le nom."""
        slug = self._normalize_name(performer_name)
        return f"https://www.iafd.com/person.rme/perfid={slug}/gender=f/{slug}.htm"

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

        data["birthdate"] = self._get_stat(tree, "Birthday") or self._get_stat(tree, "Date of Birth")
        data["death_date"] = self._get_stat(tree, "Death")
        data["ethnicity"] = self._get_stat(tree, "Ethnicity") or self._get_stat(tree, "Race")
        data["country"] = self._get_stat(tree, "Birthplace") or self._get_stat(tree, "Nationality")
        data["hair_color"] = self._get_stat(tree, "Hair Color")
        data["eye_color"] = self._get_stat(tree, "Eye Color")
        
        height_text = self._get_stat(tree, "Height")
        if height_text:
            data["height"] = height_text
        
        weight_text = self._get_stat(tree, "Weight")
        if weight_text:
            data["weight"] = weight_text
            
        data["measurements"] = self._get_stat(tree, "Measurements")
        data["fake_tits"] = self._get_stat(tree, "Boobs") or self._get_stat(tree, "Breast")
        
        career_years = self._get_stat(tree, "Years Active")
        if career_years:
            data["career_length"] = career_years
        else:
            start = self._get_stat(tree, "Start") or self._get_stat(tree, "Career Start")
            end = self._get_stat(tree, "End") or self._get_stat(tree, "Career End") or "Present"
            if start:
                data["career_length"] = f"{start} - {end}"

        # ── Phase 2 — Awards ────────────────────────────────────
        data["awards"] = self._extract_awards(tree)

        # ── Bio / Details ───────────────────────────────────────
        bio_text = self._get_text(tree, '//div[@id="bio"]')
        if not bio_text:
            bio_text = self._get_text(tree, '//div[contains(@class,"biodata")]')
        data["details"] = bio_text

        # ── Tattoos ─────────────────────────────────────────────
        tattoo_text = self._get_stat(tree, "Tattoos")
        data["tattoos"] = parse_body_art(tattoo_text) if tattoo_text else []

        # ── Piercings ───────────────────────────────────────────
        piercing_text = self._get_stat(tree, "Piercings")
        data["piercings"] = parse_body_art(piercing_text) if piercing_text else []

        # ── URLs ────────────────────────────────────────────────
        data["urls"]["iafd"] = url

        # Extraire les liens vers d'autres databases
        db_links = tree.xpath('//a[contains(@href, "http")]/@href')
        for link in db_links:
            link = link.strip()
            if "freeones.com" in link:
                data["urls"]["freeones"] = link
            elif "babepedia.com" in link:
                data["urls"]["babepedia"] = link
            elif "thenude.com" in link or "thenude.eu" in link:
                data["urls"]["thenude"] = link

        return data

    def _extract_awards(self, tree) -> list[str]:
        """Parser les awards depuis div#awards de IAFD."""
        awards_divs = tree.xpath("//div[@id='awards']")
        if not awards_divs:
            # Essayer un sélecteur alternatif
            awards_divs = tree.xpath("//div[contains(@class,'award')]")
        
        if not awards_divs:
            return []

        div = awards_divs[0]
        # Insérer des sauts de ligne avant chaque <br>
        for br in div.xpath(".//br"):
            br.tail = "\n" + (br.tail or "")

        awards_text = div.text_content()
        raw_lines = [line.strip() for line in awards_text.splitlines() if line.strip()]
        
        # Filtrer les lignes parasites
        result = []
        current_year = ""

        for line in raw_lines:
            # Détection de l'année (ex: 2012) pour l'associer à l'award
            if re.match(r'^\d{4}$', line):
                current_year = line
                continue

            if AWARD_SKIP.match(line):
                continue
            if len(line) < 4:
                continue
            
            # Ajouter l'année devant la ligne si elle n'y est pas déjà
            if current_year and not line.startswith(current_year):
                result.append(f"{current_year} {line}")
            else:
                result.append(line)

        return result

    def _get_stat(self, tree, label: str) -> str | None:
        """Extraire une stat depuis le tableau IAFD (label → valeur)."""
        # Essayer plusieurs formats de tableau bio IAFD
        xpaths = [
            f'//p[contains(text(), "{label}")]/following-sibling::p[1]',
            f'//td[contains(text(), "{label}")]/following-sibling::td[1]',
            f'//b[contains(text(), "{label}")]/parent::*/following-sibling::*[1]',
            f'//span[contains(text(), "{label}")]/following-sibling::span[1]',
        ]
        for xpath in xpaths:
            val = self._get_text(tree, xpath)
            if val:
                return val
        return None
