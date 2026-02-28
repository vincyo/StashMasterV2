"""
scrapers.py - Modules de scraping pour StashMaster V2
Sources supportées : IAFD, FreeOnes, TheNude, Babepedia

Chaque scraper retourne un dict avec les clés normalisées :
    name, aliases, birthdate, birthplace, country, ethnicity,
    hair, eyes, height_cm, weight_kg, measurements, fake_boobs,
    career_start, career_end, tattoos, piercings, awards
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 15  # secondes


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Nettoie une chaîne : supprime les espaces superflus."""
    return re.sub(r'\s+', ' ', text).strip()


def _clean_career(val: str) -> str:
    """Supprime tout texte entre parenthèses dans une période de carrière.
    Exemple : "2007-2025 (Started around 2007)" → "2007-2025".
    """
    if not val:
        return val
    return re.sub(r"\s*\(.*?\)", "", val).strip()


def _fetch_with_curl(url: str) -> Optional[str]:
    """Fallback utilisant curl pour contourner les blocages 403."""
    import subprocess
    try:
        # On utilise curl avec des headers standards et un timeout
        cmd = [
            "curl", "-s", "-L",
            "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", "Accept-Language: en-US,en;q=0.9",
            "--connect-timeout", str(TIMEOUT),
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except Exception as e:
        print(f"[SCRAPER] Échec fallback curl : {e}")
    return None


def _fetch(url: str) -> Optional[BeautifulSoup]:
    """Télécharge une page et retourne un objet BeautifulSoup, ou None."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        # Fallback pour les erreurs 403 (Forbidden) fréquentes sur IAFD/Babepedia
        resp_obj = getattr(e, 'response', None)
        status_code = getattr(resp_obj, 'status_code', 0)
        is_forbidden = status_code == 403
        
        if is_forbidden or "403" in str(e):
            print(f"[SCRAPER] 403 détecté sur {url}, tentative fallback curl...")
            html = _fetch_with_curl(url)
            if html:
                print(f"[SCRAPER] Succès fallback curl pour {url}")
                return BeautifulSoup(html, "html.parser")
        
        print(f"[SCRAPER] Erreur fetch {url} : {e}")
        return None


def _parse_html(html_content: str) -> BeautifulSoup:
    """Parse du HTML brut (pour les tests avec fichiers locaux)."""
    return BeautifulSoup(html_content, "html.parser")


def _extract_cm(text: str) -> str:
    """Extrait les cm d'une chaîne comme '5 feet, 8 inches (173 cm)', '172 cm' ou '1.63m'."""
    # Cas '1.63m' ou '1.63 m'
    m_meter = re.search(r'(\d\.\d{2})\s*m', text, re.IGNORECASE)
    if m_meter:
        return str(int(float(m_meter.group(1)) * 100))

    m = re.search(r'(\d{2,3})\s*cm', text, re.IGNORECASE)
    return m.group(1) if m else ""


def _extract_kg(text: str) -> str:
    """Extrait les kg d'une chaîne comme '129 lbs (59 kg)' ou '59 kg'."""
    m = re.search(r'(\d{2,3})\s*kg', text, re.IGNORECASE)
    return m.group(1) if m else ""


def _extract_year(text: str) -> str:
    """Extrait la première année sur 4 chiffres trouvée."""
    m = re.search(r'(\d{4})', text)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Scraper de base
# ---------------------------------------------------------------------------

class ScraperBase:
    """Classe de base pour tous les scrapers."""

    SOURCE_NAME = "unknown"

    def scrape(self, url: str) -> Dict[str, Any]:
        """Scrape une URL et retourne un dict normalisé."""
        soup = _fetch(url)
        if soup is None:
            return {}
        data = self._parse(soup, url)
        data['url'] = url
        data['source'] = self.SOURCE_NAME
        return data

    def scrape_from_html(self, html_content: str, url: str = "") -> Dict[str, Any]:
        """Scrape depuis du HTML brut (pour les tests locaux)."""
        soup = _parse_html(html_content)
        return self._parse(soup, url)

    def _parse(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def _detect_url(url: str) -> bool:
        """Retourne True si l'URL correspond à cette source."""
        raise NotImplementedError


# ===========================================================================
# SCRAPER IAFD
# ===========================================================================

class IAFDScraper(ScraperBase):
    """
    Scrape iafd.com
    URL type : https://www.iafd.com/person.rme/perfid=bridgetteb/gender=f/bridgette-b.htm

    Structure HTML :
    - <p class="bioheading"> contient le nom du champ
    - <p class="biodata"> ou <div class="biodata"> contient la valeur
    - Onglet awards : <div id="awards"> avec p.bioheading (cérémonie),
      div.showyear (année), div.biodata (mention + catégorie)
    """

    SOURCE_NAME = "IAFD"

    @staticmethod
    def _detect_url(url: str) -> bool:
        return "iafd.com" in url

    def _parse(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {"source": self.SOURCE_NAME, "url": url}

        # --- Nom principal ---
        h1 = soup.find("h1")
        if h1:
            data["name"] = _clean(h1.get_text())

        # --- Champs bioheading / biodata ---
        headings = soup.find_all("p", class_="bioheading")
        for heading in headings:
            key = _clean(heading.get_text())
            # La valeur est dans le prochain élément frère (p ou div .biodata)
            sib = heading.find_next_sibling()
            if sib is None:
                continue
            val = _clean(sib.get_text(separator=" "))

            if key in ("Performer AKA", "AKA"):
                # IAFD : alias séparés par des <br/> dans un div.biodata
                # On remplace les <br> par des séparateurs avant de parser
                for br in sib.find_all("br"):
                    br.replace_with("|")
                aliases = [_clean(a) for a in sib.get_text().split("|") if _clean(a)]
                # Filtrer les entrées inutiles type "No known aliases"
                aliases = [a for a in aliases if a.lower() not in {"no known aliases", "none", "unknown", "n/a"}]
                if aliases:
                    data["aliases"] = aliases

            elif key == "Birthday":
                # "October 15, 1983 (42 years old)"
                m = re.match(r"(.+?)\s*\(\d+", val)
                data["birthdate"] = _clean(m.group(1)) if m else val

            elif key == "Birthplace":
                data["birthplace"] = val

            elif key == "Ethnicity":
                data["ethnicity"] = val

            elif key == "Hair Colors":
                data["hair_color"] = val

            elif key == "Eye Color":
                data["eye_color"] = val

            elif key == "Height":
                data["height"] = _extract_cm(val)

            elif key == "Weight":
                data["weight"] = _extract_kg(val)

            elif key == "Measurements":
                data["measurements"] = val

            elif key == "Years Active":
                # nettoyer les parenthèses éventuelles
                data["career_length"] = _clean_career(val)

            elif key == "Tattoos":
                data["tattoos"] = val

            elif key == "Nationality":
                data["country"] = val

            elif key in ("Breast implants", "Implant", "Boobs"):
                # IAFD affiche souvent "Yes" ou "No"
                data["fake_tits"] = val

        # --- Awards (onglet dédié) ---
        awards_div = soup.find("div", id="awards")
        if awards_div:
            # Essayer de récupérer tous les awards depuis la page dédiée
            m = re.search(r'id=([a-f0-9-]+)', url)
            if m:
                awards_url = f"https://www.iafd.com/awards.asp?id={m.group(1)}"
                awards_soup = _fetch(awards_url)
                if awards_soup:
                    full_awards_div = awards_soup.find("div", id="awards")
                    if full_awards_div:
                        data["awards"] = self._parse_awards(full_awards_div)
                    else:
                        data["awards"] = self._parse_awards(awards_div)
                else:
                    data["awards"] = self._parse_awards(awards_div)
            else:
                data["awards"] = self._parse_awards(awards_div)

        # --- Liens Sociaux / Externes ---
        ext_links = []
        
        # 1. Liens dans bioheading "External Sites"
        ext_heading = soup.find("p", class_="bioheading", string=re.compile(r"External Sites", re.I))
        if ext_heading:
            sib = ext_heading.find_next_sibling()
            if sib:
                ext_links.extend([a["href"] for a in sib.find_all("a", href=True)])
        
        # 2. Liens dans bioheading "Social Network" (nouveau format IAFD)
        social_heading = soup.find("p", class_="bioheading", string=re.compile(r"Social Network", re.I))
        if social_heading:
            sib = social_heading.find_next_sibling()
            if sib:
                ext_links.extend([a["href"] for a in sib.find_all("a", href=True)])
        
        data["discovered_urls"] = list(set(ext_links))

        return data

    def _parse_awards(self, awards_div) -> str:
        """
        Parse le bloc awards IAFD et retourne une liste d'awards nettoyés :
            YEAR ORG - Category (Movie) [Status]
        """
        from utils.normalizer import clean_award_text
        
        lines = []
        current_ceremony = ""
        current_year = ""

        for child in awards_div.children:
            if not hasattr(child, "name") or child.name is None:
                continue

            tag_name = child.name
            tag_class = child.get("class", [])
            text = _clean(child.get_text(separator=" "))

            if tag_name == "p" and "bioheading" in tag_class:
                # Nouvelle cérémonie
                current_ceremony = text
                current_year = ""

            elif tag_name == "div" and "showyear" in tag_class:
                current_year = text

            elif tag_name == "div" and "biodata" in tag_class:
                if text:
                    # Inclure cérémonie + année + texte pour nettoyage complet
                    raw_award = f"{current_ceremony} {current_year} {text}"
                    cleaned_award = clean_award_text(raw_award)
                    lines.append(cleaned_award)

        return "\n".join(lines).strip()


# ===========================================================================
# SCRAPER FREEONES
# ===========================================================================

class FreeOnesScraper(ScraperBase):
    """
    Scrape freeones.xxx
    URL type : https://www.freeones.xxx/bridgette-b/bio

    Structure HTML :
    - <li class="hide-on-edit"> contenant :
        <span> (clé) + <span class="font-size-xs"> (valeur)
      Parfois la valeur est dans des liens <a>
    """

    SOURCE_NAME = "FreeOnes"

    @staticmethod
    def _detect_url(url: str) -> bool:
        return "freeones" in url

    def _parse(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {"source": self.SOURCE_NAME, "url": url}

        for li in soup.find_all("li", class_="hide-on-edit"):
            spans = li.find_all("span", recursive=False)
            if not spans:
                # Essayer tous les spans
                spans = li.find_all("span")
            if len(spans) < 1:
                continue

            key = _clean(spans[0].get_text()).rstrip(":")

            # Valeur : liens <a> ou dernier span
            links = [_clean(a.get_text()) for a in li.find_all("a") if _clean(a.get_text())]
            if links:
                val = links[0]
                all_links = links
            elif len(spans) > 1:
                val = _clean(spans[-1].get_text())
                all_links = [val]
            else:
                continue

            if not val or val.lower() in ("unknown", "n/a", "no"):
                # On garde quand même certains champs négatifs
                if key not in ("Piercings", "Tattoos", "Feature dancer"):
                    continue

            # Mapping des clés FreeOnes → clés normalisées
            if key == "Name":
                data["name"] = val

            elif key == "Aliases":
                data["aliases"] = all_links

            elif key == "Date of birth":
                data["birthdate"] = val

            elif key == "Place of birth":
                # "Barcelona Spain" ou links = ['Barcelona', 'Spain']
                data["birthplace"] = ", ".join(all_links) if len(all_links) > 1 else val

            elif key == "Nationality":
                data["country"] = val

            elif key == "Ethnicity":
                data["ethnicity"] = val

            elif key == "Hair Color":
                data["hair_color"] = val

            elif key == "Eye Color":
                data["eye_color"] = val

            elif key == "Height":
                data["height"] = _extract_cm(val)

            elif key == "Weight":
                data["weight"] = _extract_kg(val)

            elif key in ("Measurements", "Bust", "Waist", "Hip"):
                # On stocke les mesures brutes disponibles
                if key == "Measurements":
                    data["measurements"] = val
                else:
                    data[f"freeones_{key.lower()}"] = val

            elif key == "Boobs":
                data["fake_tits"] = val  # "Fake" ou "Natural"

            elif key == "Tattoos":
                # val = "Yes" ou description
                tattoo_loc = li.find("span", class_="font-size-xs")
                tattoo_val = _clean(tattoo_loc.get_text()) if tattoo_loc else val
                data["tattoos"] = tattoo_val if tattoo_val.lower() not in ("no",) else ""

            elif key == "Tattoo locations":
                data["tattoos"] = val  # Description complète

            elif key == "Piercings":
                piercing_val = val
                data["piercings"] = piercing_val if piercing_val.lower() not in ("no",) else ""

            elif key == "Piercing locations":
                if val and val.lower() not in ("no",):
                    data["piercings"] = val

            elif key == "Career start":
                val2 = _clean_career(val)
                data["career_length"] = val2 if "career_length" not in data else f"{val2} - {data['career_length']}"

            elif key == "Career end":
                val2 = _clean_career(val)
                data["career_length"] = f"{data.get('career_length', '???')} - {val2}"

        # --- Liens Sociaux / Externes ---
        ext_links = []
        social_box = soup.find("div", class_="social-links") or soup.find("ul", class_="social-links")
        if social_box:
            ext_links.extend([a["href"] for a in social_box.find_all("a", href=True)])
        
        # On peut aussi chercher dans les liens de la bio qui ne sont pas internes
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "freeones.xxx" not in href and href.startswith("http"):
                # Éviter les liens de navigation communs
                if not any(x in href for x in ["twitter.com/intent", "facebook.com/sharer"]):
                    ext_links.append(href)

        data["discovered_urls"] = list(set(ext_links))

        return data


# ===========================================================================
# SCRAPER THENUDE
# ===========================================================================

class TheNudeScraper(ScraperBase):
    """
    Scrape thenude.com
    URL type : https://www.thenude.com/bridgette-b-51339.htm

    Structure HTML :
    - <li> contenant <span class="list-quest">Clé:</span> suivi du texte de valeur
    """

    SOURCE_NAME = "TheNude"

    @staticmethod
    def _detect_url(url: str) -> bool:
        return "thenude.com" in url

    def _parse(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {"source": self.SOURCE_NAME, "url": url}

        for li in soup.find_all("li"):
            quest = li.find("span", class_="list-quest")
            if not quest:
                continue
            key = _clean(quest.get_text()).rstrip(":")
            # Valeur = texte du li sans le span
            full_text = _clean(li.get_text(separator=" "))
            key_text = _clean(quest.get_text())
            val = _clean(full_text.replace(key_text, "", 1))

            if not val:
                continue

            if key == "AKA":
                aliases = [a.strip() for a in val.split(",") if a.strip()]
                data["aliases"] = aliases

            elif key == "Born":
                data["birthdate"] = val  # "October 1983" (pas de jour)

            elif key == "Birthplace":
                data["birthplace"] = val

            elif key == "Measurements":
                # Format: "38F-27-36 / ~97-69-92"
                parts = val.split("/")
                data["measurements"] = _clean(parts[0])  # format US
                data["measurements_metric"] = _clean(parts[1].lstrip("~")) if len(parts) > 1 else ""

            elif key == "Height":
                data["height_cm"] = _extract_cm(val)

            elif key == "Weight":
                data["weight"] = _extract_kg(val)

            elif key in ("Hair Colour", "Hair Color"):
                data["hair_color"] = val

            elif key == "Ethnicity":
                data["ethnicity"] = val

            elif key == "Breasts":
                # "Large (Fake)" → fake_tits
                data["breast_size"] = val
                data["fake_tits"] = "Fake" if "fake" in val.lower() else "Natural"

            elif key == "Piercings":
                data["piercings"] = val if val.lower() not in ("none", "no") else ""

            elif key == "Tattoos":
                data["tattoos"] = val

            elif key == "Activities":
                data["activities"] = val

            elif key in ("First Seen", "Last Seen"):
                year = _extract_year(val)
                if "career_length" not in data:
                    data["career_length"] = year
                else:
                    if key == "First Seen":
                        data["career_length"] = f"{year} - {data['career_length']}"
                    else:
                        data["career_length"] = f"{data['career_length']} - {year}"

            elif key == "Tags":
                data["thenude_tags"] = [t.strip() for t in val.split(",")]

            elif key == "Agencies":
                data["agency"] = val

        # --- Liens Externes ---
        ext_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "thenude.com" not in href and href.startswith("http"):
                ext_links.append(href)
        
        data["discovered_urls"] = list(set(ext_links))

        return data


# ===========================================================================
# SCRAPER BABEPEDIA
# ===========================================================================

class BabepediaScraper(ScraperBase):
    """
    Scrape babepedia.com
    URL type : https://www.babepedia.com/babe/Bridgette_B

    Structure HTML :
    - <div class="info-item"> contenant :
        <span class="label">Clé:</span> + texte/liens pour la valeur
    - Aliases dans <div class="aliases"> ou section "Also known as:"
    """

    SOURCE_NAME = "Babepedia"

    @staticmethod
    def _detect_url(url: str) -> bool:
        return "babepedia.com" in url

    def _parse(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {"source": self.SOURCE_NAME, "url": url}

        # --- Nom principal ---
        h1 = soup.find("h1")
        if h1:
            data["name"] = _clean(h1.get_text())

        # --- Aliases ---
        aliases = []
        # Chercher "Also known as:" ou section alias
        for tag in soup.find_all(string=re.compile(r"Also known as", re.I)):
            parent = tag.parent
            # Chercher les liens dans le parent ou ses frères
            container = parent.parent if parent else None
            if container:
                alias_links = [_clean(a.get_text()) for a in container.find_all("a") if _clean(a.get_text())]
                aliases.extend(alias_links)
        if aliases:
            data["aliases"] = list(set(aliases))

        # --- Champs info-item ---
        for div in soup.find_all("div", class_="info-item"):
            label = div.find("span", class_="label")
            if not label:
                continue
            key = _clean(label.get_text()).rstrip(":")

            # Valeur : tout le texte du div moins le label
            # On utilise \n pour préserver la structure (ex: Tattoos 1 par ligne)
            full_text = _clean(div.get_text(separator="\n"))
            label_text = _clean(label.get_text())
            val = _clean(full_text.replace(label_text, "", 1))

            if not val:
                continue

            # Mapping Babepedia → normalisé
            if key == "Age":
                pass  # On ignore, on préfère la date de naissance

            elif key == "Born":
                # "Saturday 15th of October 1983"
                m = re.search(r'(\d+)(?:st|nd|rd|th)?\s+of\s+(\w+)\s+(\d{4})', val, re.I)
                if m:
                    data["birthdate"] = f"{m.group(3)}-{_month_to_num(m.group(2)):02d}-{int(m.group(1)):02d}"
                else:
                    data["birthdate"] = val

            elif key == "Years active":
                data["career_length"] = val

            elif key == "Birthplace":
                data["birthplace"] = val

            elif key == "Nationality":
                # Enlever les parenthèses éventuelles
                data["country"] = val.strip("()")

            elif key == "Ethnicity":
                data["ethnicity"] = val

            elif key == "Hair color":
                data["hair_color"] = val

            elif key == "Eye color":
                data["eye_color"] = val

            elif key == "Height":
                data["height"] = _extract_cm(val)

            elif key == "Weight":
                data["weight"] = _extract_kg(val)

            elif key == "Measurements":
                data["measurements"] = val

            elif key in ("Boobs", "Breast"):
                data["fake_tits"] = val  # "Fake/Enhanced" ou "Natural"

            elif key == "Instagram follower count":
                data["instagram_followers"] = val

            elif key == "Tattoos":
                # Babepedia : parfois une liste multi‑ligne ou séparée par des virgules
                # extraire chaque élément et conserver localisation si fournie
                items = [l.strip() for l in re.split(r"[\n,]", val) if l.strip()]
                formatted = []
                for line in items:
                    if line.lower() in ("none", "n/a"):
                        continue
                    m = re.search(r"\((.+?)\)", line)
                    pos = m.group(1) if m else None
                    desc = re.sub(r"\(.+?\)", "", line).strip()
                    if pos:
                        formatted.append(f"{pos} — {desc}")
                    else:
                        formatted.append(desc)
                data["tattoos"] = "\n".join(formatted)

        # --- Section TRIVIA ---
        # (déjà extrait plus haut) ; la traduction se fait en aval du scraping
        # Souvent une liste <ul> après un <h2>Trivia</h2>
        trivia_list = []
        trivia_h2 = soup.find("h2", string=re.compile(r"Trivia", re.I))
        if trivia_h2:
            container = trivia_h2.find_next_sibling(["ul", "ol"])
            if container:
                trivia_list = [_clean(li.get_text()) for li in container.find_all("li") if _clean(li.get_text())]
        if trivia_list:
            data["trivia"] = "\n".join(trivia_list)

        # --- Section ABOUT / BIO RAW ---
        about_div = soup.find("div", id="about") or soup.find("div", class_="about")
        if not about_div:
            # Essayer de trouver le texte après "About [Name]"
            about_h2 = soup.find("h2", string=re.compile(r"About", re.I))
            if about_h2:
                about_div = about_h2.find_next_sibling("p")
        if about_div:
            data["bio_raw"] = _clean(about_div.get_text(separator="\n"))  # mini-bio Babepedia/IAFD

        # --- Liens Sociaux / Externes ---
        ext_links = []
        socials = {}
        
        # Mapping Socials
        social_map = {
            "instagram.com": "instagram",
            "twitter.com": "x",
            "x.com": "x",
            "onlyfans.com": "onlyfans",
            "tiktok.com": "tiktok",
            "youtube.com": "youtube",
            "twitch.tv": "twitch",
            "imdb.com": "imdb",
            "facebook.com": "facebook"
        }

        # Babepedia a souvent une section "Links"
        link_container = soup.find("div", class_="links") or soup.find("ul", class_="links")
        # official website
        if not data.get('official_website'):
            off_tag = soup.find('a', class_=re.compile(r'official', re.I))
            if not off_tag:
                off_tag = soup.find('a', string=re.compile(r'Official', re.I))
            if off_tag and off_tag.get('href'):
                data['official_website'] = off_tag['href']
        if not link_container:
            # Chercher dans la barre de réseaux sociaux sous l'image
            link_container = soup.find("div", class_="social-icons")
            
        if link_container:
            for a in link_container.find_all("a", href=True):
                href = a["href"]
                if href.startswith("//"): href = "https:" + href
                if not href.startswith("http"): continue
                if url in href: continue # Ignorer le lien vers la page elle-même
                
                ext_links.append(href)
                for domain, key in social_map.items():
                    if domain in href.lower():
                        socials[key] = href
                        break
        
        # Fallback : tous les liens sortants
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("//"): href = "https:" + href
            if not href.startswith("http"): continue
            
            if "babepedia.com" not in href:
                if url in href: continue
                ext_links.append(href)
                for domain, key in social_map.items():
                    if domain in href.lower() and key not in socials:
                        socials[key] = href

        # --- Raffinement final des URLs ---
        final_urls = []
        seen_domains = set()
        
        # On trie pour donner la priorité aux sociaux déjà identifiés
        # Mais on va surtout assurer l'unicité par domaine
        for link in ext_links:
            if link == url: continue
            
            # Extraire le domaine de base
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', link.lower())
            if domain_match:
                domain = domain_match.group(1)
                if domain not in seen_domains:
                    final_urls.append(link)
                    seen_domains.add(domain)
            else:
                # Cas rare où le regex échoue
                if link not in final_urls:
                    final_urls.append(link)

        data["discovered_urls"] = final_urls
        data["socials"] = socials

        return data


def _month_to_num(month_name: str) -> int:
    """Convertit un nom de mois anglais en numéro."""
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }
    return months.get(month_name.lower(), 1)


# ===========================================================================
# SCRAPER BOOBPEDIA
# ===========================================================================

class BoobpediaScraper(ScraperBase):
    """
    Scrape boobpedia.com
    URL type : https://www.boobpedia.com/boobs/Abella_Anderson
    """

    SOURCE_NAME = "Boobpedia"

    @staticmethod
    def _detect_url(url: str) -> bool:
        return "boobpedia.com" in url

    def _parse(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {"source": self.SOURCE_NAME, "url": url}
        socials: Dict[str, str] = {}
        ext_links: List[str] = []

        # --- Nom ---
        h1 = soup.find("h1", id="firstHeading") or soup.find("h1")
        if h1:
            data["name"] = _clean(h1.get_text())

        # --- Infobox (table de données biographiques) ---
        infobox = soup.find("table", class_=re.compile(r"infobox|wikitable", re.I))
        if infobox:
            for row in infobox.find_all("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) < 2:
                    continue
                key = _clean(cells[0].get_text()).rstrip(":")
                val_cell = cells[1]
                # Extraire les liens
                links_in_cell = [a["href"] for a in val_cell.find_all("a", href=True) if a["href"].startswith("http")]
                val = _clean(val_cell.get_text(separator=" "))

                if not val:
                    continue

                if key in ("Born", "Date of Birth", "Birthday"):
                    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', val)
                    if m:
                        data["birthdate"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                    else:
                        data["birthdate"] = val
                elif key == "Birthplace":
                    data["birthplace"] = val
                elif key in ("Height",):
                    data["height"] = _extract_cm(val)
                elif key in ("Weight",):
                    data["weight"] = _extract_kg(val)
                elif key in ("Measurements", "Bust", "Bra size"):
                    data["measurements"] = val
                elif key in ("Hair color", "Hair"):
                    data["hair_color"] = val
                elif key in ("Eye color", "Eyes"):
                    data["eye_color"] = val
                elif key in ("Boobs", "Breast", "Breast type"):
                    data["fake_tits"] = val
                elif key in ("Ethnicity",):
                    data["ethnicity"] = val
                elif key in ("Nationality", "Country"):
                    data["country"] = val
                elif key in ("Years active", "Career"):
                    data["career_length"] = val
                elif key in ("Tattoos",):
                    data["tattoos"] = val
                elif key in ("Also known as", "AKA", "Aliases"):
                    aliases = [a.strip() for a in re.split(r"[,\n|]", val) if a.strip()]
                    data["aliases"] = aliases

                # Réseaux sociaux dans les liens de l'infobox
                for lnk in links_in_cell:
                    lnk_l = lnk.lower()
                    if "instagram.com" in lnk_l:
                        socials["instagram"] = lnk
                    elif "twitter.com" in lnk_l or "x.com" in lnk_l:
                        socials["twitter"] = lnk
                    elif "onlyfans.com" in lnk_l:
                        socials["onlyfans"] = lnk
                    elif "facebook.com" in lnk_l:
                        socials["facebook"] = lnk
                    ext_links.append(lnk)

        # --- Bio / intro paragraphe ---
        content_div = soup.find("div", id="mw-content-text") or soup.find("div", class_="mw-parser-output")
        if content_div:
            paragraphs = []
            for p in content_div.find_all("p", recursive=False):
                text = _clean(p.get_text())
                if text and len(text) > 40:
                    paragraphs.append(text)
                if len(paragraphs) >= 4:
                    break
            if paragraphs:
                data["bio_raw"] = "\n\n".join(paragraphs)

            # Awards dans les listes
            award_lines = []
            for ul in content_div.find_all(["ul", "ol"]):
                header = ul.find_previous_sibling(re.compile(r"h[2-4]"))
                if header and re.search(r"award|nominat|accolad", header.get_text(), re.I):
                    for li in ul.find_all("li"):
                        award_lines.append("- " + _clean(li.get_text()))
            if award_lines:
                data["awards"] = "\n".join(award_lines)

            # Liens externes
            ext_section = content_div.find("span", id=re.compile(r"External|Links", re.I))
            if ext_section:
                parent = ext_section.find_parent()
                if parent:
                    sib = parent.find_next_sibling()
                    if sib:
                        for a in sib.find_all("a", href=True):
                            href = a["href"]
                            if href.startswith("http"):
                                lnk_l = href.lower()
                                if "instagram.com" in lnk_l:
                                    socials["instagram"] = href
                                elif "twitter.com" in lnk_l or "x.com" in lnk_l:
                                    socials["twitter"] = href
                                elif "onlyfans.com" in lnk_l:
                                    socials["onlyfans"] = href
                                ext_links.append(href)

        data["discovered_urls"] = list(dict.fromkeys(ext_links))
        data["socials"] = socials
        return data


# ===========================================================================
# SCRAPER XXXBIOS
# ===========================================================================

class XXXBiosScraper(ScraperBase):
    """
    Scrape xxxbios.com
    URL type : https://xxxbios.com/abella-anderson-biography/

    Construction automatique de l'URL à partir du nom :
        "Abella Anderson" → "abella-anderson-biography"
    """

    SOURCE_NAME = "XXXBios"

    @staticmethod
    def _detect_url(url: str) -> bool:
        return "xxxbios.com" in url

    @staticmethod
    def build_url(performer_name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9\s]", "", performer_name.lower().strip())
        slug = re.sub(r"\s+", "-", slug)
        return f"https://xxxbios.com/{slug}-biography/"

    def search(self, performer_name: str) -> Optional[str]:
        """Recherche l'URL de la fiche sur XXXBios via le moteur de recherche."""
        if not performer_name:
            return None

        # Nettoyage nom
        query = performer_name.replace(" ", "+")
        search_url = f"https://xxxbios.com/?s={query}"
        
        # On utilise _fetch pour récupérer la page de résultats
        soup = _fetch(search_url)
        if not soup:
            return None

        # Les résultats sont généralement dans des titres h2, h3 ou h4 avec class="entry-title"
        # Exemple : <h2 class="entry-title"><a href="...">Performer Name Biography</a></h2>
        candidates = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4"], class_=re.compile(r"entry-title|post-title", re.I)):
            link = tag.find("a", href=True)
            if link:
                candidates.append((link.get_text().strip(), link["href"]))

        # Fallback : liens génériques dans le contenu principal si pas de balises titres standards
        if not candidates:
            main_content = soup.find("main") or soup.find("div", id="content") or soup.find("div", class_="site-content")
            if main_content:
                for link in main_content.find_all("a", href=True):
                    candidates.append((link.get_text().strip(), link["href"]))

        performer_lower = performer_name.lower()
        
        # Stratégie de sélection
        for text, href in candidates:
            t_lower = text.lower()
            # 1. Correspondance forte : contient le nom ET "biography"
            if performer_lower in t_lower and "biography" in t_lower:
                return href
            # 2. Correspondance exacte du nom (ex: "Riley Reid")
            if t_lower == performer_lower:
                return href

        # 3. Essai de correspondance partielle si lien contient "biography"
        for text, href in candidates:
            if performer_lower in text.lower() and "biography" in href:
                return href

        return None

    def _parse(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {"source": self.SOURCE_NAME, "url": url}
        socials: Dict[str, str] = {}
        ext_links: List[str] = []

        # --- Nom ---
        h1 = soup.find("h1")
        if h1:
            raw_name = _clean(h1.get_text())
            # Enlever le suffixe " Biography" s'il est présent
            data["name"] = re.sub(r" Biography$", "", raw_name, flags=re.IGNORECASE).strip()

        # --- Infos personnelles (tableau ou liste .personal-info) ---
        info_section = (
            soup.find("div", class_=re.compile(r"personal.?info|bio.?info|profile.?info", re.I))
            or soup.find("table", class_=re.compile(r"personal|bio|profile", re.I))
        )

        def _process_kv(k, v):
            if not v: return
            if k in ("Born", "Date of Birth", "Birthday"):
                data["birthdate"] = v
            elif k in ("Birthplace", "Place of Birth"):
                data["birthplace"] = v
            elif k in ("Height",):
                data["height"] = _extract_cm(v)
            elif k in ("Weight",):
                data["weight"] = _extract_kg(v)
            elif k in ("Measurements",):
                data["measurements"] = v
            elif k in ("Hair Color", "Hair"):
                data["hair_color"] = v
            elif k in ("Eye Color", "Eyes"):
                data["eye_color"] = v
            elif k in ("Boobs", "Breast Size", "Breasts"):
                data["fake_tits"] = v
            elif k in ("Ethnicity",):
                data["ethnicity"] = v
            elif k in ("Nationality", "Country"):
                data["country"] = v
            elif k in ("Years Active", "Career"):
                data["career_length"] = v
            elif k in ("Also Known As", "AKA", "Aliases"):
                aliases = [a.strip() for a in re.split(r"[,\n|]", v) if a.strip()]
                data["aliases"] = aliases

        if info_section:
            rows = info_section.find_all("tr") or info_section.find_all("li")
            for row in rows:
                cells = row.find_all(["th", "td", "span"])
                if len(cells) >= 2:
                    key = _clean(cells[0].get_text()).rstrip(":")
                    val = _clean(cells[1].get_text())
                elif row.find("strong") or row.find("b"):
                    lbl = row.find("strong") or row.find("b")
                    key = _clean(lbl.get_text()).rstrip(":")
                    val = _clean(row.get_text().replace(lbl.get_text(), "", 1))
                else:
                    continue
                _process_kv(key, val)
        else:
            # Fallback : Recherche d'un titre "Personal Info" et parsing des paragraphes suivants
            header = soup.find(["h2", "h3", "h4"], string=re.compile(r"Personal Info", re.I))
            if header:
                for sibling in header.find_next_siblings():
                    if sibling.name in ("h2", "h3", "h4", "div", "section"):
                        break
                    text = _clean(sibling.get_text())
                    if ":" in text:
                        parts = text.split(":", 1)
                        key = _clean(parts[0])
                        val = _clean(parts[1])
                        _process_kv(key, val)

        # --- Biographie (corps texte) ---
        # Chercher les grandes sections de contenu
        main_content = (
            soup.find("div", class_=re.compile(r"entry-content|post-content|article-content", re.I))
            or soup.find("article")
            or soup.find("div", id=re.compile(r"content", re.I))
        )
        if main_content:
            bio_paragraphs = []
            trivia_lines = []
            award_lines = []
            current_section = "bio"

            for tag in main_content.find_all(["h2", "h3", "h4", "p", "ul", "li"], recursive=True):
                text = _clean(tag.get_text())
                if not text:
                    continue

                if tag.name in ("h2", "h3", "h4"):
                    tl = text.lower()
                    if any(w in tl for w in ("award", "nominat", "accolad", "recognition")):
                        current_section = "awards"
                    elif any(w in tl for w in ("trivia", "fact", "did you know", "interesting")):
                        current_section = "trivia"
                    elif any(w in tl for w in ("career", "early life", "personal", "biography", "about", "social")):
                        current_section = "bio"
                    continue

                if tag.name in ("p",) and len(text) > 50:
                    if current_section == "bio":
                        bio_paragraphs.append(text)
                    elif current_section == "trivia":
                        trivia_lines.append("- " + text)
                    elif current_section == "awards":
                        award_lines.append(text)

                if tag.name == "li":
                    if current_section == "trivia":
                        trivia_lines.append("- " + text)
                    elif current_section == "awards":
                        award_lines.append("- " + text)

            if bio_paragraphs:
                data["bio_raw"] = "\n\n".join(bio_paragraphs[:8])
            if trivia_lines:
                data["trivia"] = "\n".join(trivia_lines[:20])
            if award_lines:
                data["awards"] = "\n".join(award_lines[:50])

            # Réseaux sociaux (liens dans le contenu)
            for a in main_content.find_all("a", href=True):
                href = a["href"]
                if not href.startswith("http"):
                    continue
                lnk_l = href.lower()
                if "instagram.com" in lnk_l:
                    socials["instagram"] = href
                elif "twitter.com" in lnk_l or "x.com" in lnk_l:
                    socials["twitter"] = href
                elif "onlyfans.com" in lnk_l:
                    socials["onlyfans"] = href
                elif "facebook.com" in lnk_l:
                    socials["facebook"] = href
                elif "brazzers.com" in lnk_l or "naughtyamerica.com" in lnk_l or "digitalplayground.com" in lnk_l:
                    ext_links.append(href)
                elif href.startswith("http") and "xxxbios.com" not in lnk_l:
                    ext_links.append(href)

        # Awards depuis section dédiée (tables)
        if not data.get("awards"):
            award_tables = soup.find_all("table")
            award_rows = []
            for tbl in award_tables:
                caption = tbl.find("caption")
                if caption and re.search(r"award|nominat", caption.get_text(), re.I):
                    for tr in tbl.find_all("tr")[1:]:
                        cells = [_clean(td.get_text()) for td in tr.find_all("td")]
                        if cells:
                            award_rows.append(" - ".join(c for c in cells if c))
            if award_rows:
                data["awards"] = "\n".join(award_rows)

        data["discovered_urls"] = list(dict.fromkeys(ext_links))
        data["socials"] = socials
        return data


# ===========================================================================
# ORCHESTRATEUR
# ===========================================================================

class ScraperOrchestrator:
    """
    Orchestre le scraping depuis plusieurs URLs.
    Détecte automatiquement la source selon l'URL.
    """

    def __init__(self):
        self.scrapers = {
            "iafd": IAFDScraper(),
            "freeones": FreeOnesScraper(),
            "thenude": TheNudeScraper(),
            "babepedia": BabepediaScraper(),
            "boobpedia": BoobpediaScraper(),
            "xxxbios": XXXBiosScraper(),
        }

    def detect_source(self, url: str) -> Optional[ScraperBase]:
        """Retourne le scraper approprié pour une URL."""
        for scraper in self.scrapers.values():
            if scraper._detect_url(url):
                return scraper
        return None

    def scrape_all(self, urls: List[str], progress_callback=None, performer_name: str = "") -> List[Dict[str, Any]]:
        """
        Scrape toutes les URLs fournies.
        Si performer_name est fourni, auto-construit les URLs Boobpedia et XXXBios
        si elles ne sont pas déjà dans la liste.
        Retourne une liste de dicts (un par source).
        """
        # Auto-découverte Boobpedia / XXXBios si performer_name fourni
        urls_lower = [u.lower() for u in urls]
        extra_urls = []

        if performer_name:
            # Boobpedia : https://www.boobpedia.com/boobs/Firstname_Lastname
            if not any("boobpedia.com" in u for u in urls_lower):
                slug = re.sub(r"\s+", "_", performer_name.strip().title())
                extra_urls.append(f"https://www.boobpedia.com/boobs/{slug}")
            # XXXBios : recherche via le moteur du site
            if not any("xxxbios.com" in u for u in urls_lower):
                found_url = self.scrapers["xxxbios"].search(performer_name)
                if found_url:
                    extra_urls.append(found_url)
                else:
                    # Fallback sur la méthode générative si la recherche échoue
                    # (Utile si le site de recherche est down ou change)
                    extra_urls.append(XXXBiosScraper.build_url(performer_name))

        all_urls = list(urls) + extra_urls

        results = []
        total = len(all_urls)
        for i, url in enumerate(all_urls):
            url = url.strip()
            if not url:
                continue
            scraper = self.detect_source(url)
            if scraper is None:
                continue
            
            if progress_callback:
                progress_callback(i, total, scraper.SOURCE_NAME)
                
            print(f"[ORCHESTRATOR] Scraping {scraper.SOURCE_NAME} : {url}")
            result = scraper.scrape(url)
            if result:
                results.append(result)
        
        if progress_callback:
            progress_callback(total, total, "Terminé")
            
        return results


# ===========================================================================
# DATA MERGER
# ===========================================================================

class DataMerger:
    """
    Fusionne intelligemment les données provenant de plusieurs sources.

    Catégories de résultats :
    - confirmed  : même valeur dans ≥2 sources
    - new        : valeur présente dans une seule source
    - conflict   : valeurs différentes entre sources
    """

    # Champs pour lesquels on accepte des listes (fusion au lieu de conflit)
    LIST_FIELDS = {"aliases", "thenude_tags", "activities", "trivia"}

    # Priorité des sources (index bas = priorité haute)
    SOURCE_PRIORITY = ["IAFD", "FreeOnes", "Babepedia", "TheNude"]

    # Pour certains champs, on préfère d'autres sources qu'IAFD
    FIELD_PRIORITY_OVERRIDE = {
        "ethnicity": ["FreeOnes", "Babepedia", "TheNude", "IAFD"],
        "hair":      ["FreeOnes", "Babepedia", "IAFD", "TheNude"],
        "tattoos":   ["Babepedia", "FreeOnes", "IAFD", "TheNude"],
        "trivia":    ["Babepedia", "TheNude", "IAFD", "FreeOnes"],
        "bio_raw":   ["Babepedia", "IAFD", "FreeOnes", "TheNude"]
    }

    def merge(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fusionne les sources et retourne un dict avec :
        {
            "merged": {...},          # Valeurs fusionnées (meilleure source)
            "confirmed": {...},       # Champs confirmés par ≥2 sources
            "conflicts": {...},       # Champs en conflit {champ: {source: val}}
            "new_fields": {...},      # Champs apparus dans 1 seule source
            "awards": "...",          # Awards bruts depuis IAFD
        }
        """
        if not sources:
            return {}

        # Collecter toutes les valeurs par champ
        field_values: Dict[str, Dict[str, Any]] = {}  # {field: {source_name: value}}

        for src in sources:
            src_name = src.get("source", "unknown")
            for key, val in src.items():
                if key in ("source", "url"):
                    continue
                if key not in field_values:
                    field_values[key] = {}
                field_values[key][src_name] = val

        merged = {}
        confirmed = {}
        conflicts = {}
        new_fields = {}
        awards_text = ""

        for field, source_vals in field_values.items():
            # Awards : champ spécial, on garde la valeur IAFD brute
            if field == "awards":
                awards_text = source_vals.get("IAFD", "")
                continue

            # Champs list : union
            if field in self.LIST_FIELDS:
                all_vals = []
                for v in source_vals.values():
                    if isinstance(v, list):
                        all_vals.extend(v)
                    else:
                        all_vals.append(v)
                # déduplication normale mais on veut normaliser les aliases par casse
                if field == 'aliases':
                    normalized = {}
                    for a in all_vals:
                        if not a:
                            continue
                        key = a.strip().lower()
                        if key not in normalized:
                            normalized[key] = a.strip()
                    merged[field] = list(normalized.values())
                else:
                    merged[field] = list(dict.fromkeys(all_vals))  # dédupliqué, ordre préservé
                confirmed[field] = merged[field]
                continue

            unique_vals = list(set(str(v).strip() for v in source_vals.values() if v))
            n_sources = len(source_vals)

            if n_sources == 1:
                # Valeur unique → nouvelle donnée
                val = list(source_vals.values())[0]
                merged[field] = val
                new_fields[field] = {list(source_vals.keys())[0]: val}

            elif len(unique_vals) == 1:
                # Valeur identique dans plusieurs sources → confirmée
                merged[field] = unique_vals[0]
                confirmed[field] = unique_vals[0]

            else:
                chosen_val = self._pick_by_priority(source_vals, field=field)
                merged[field] = chosen_val
                conflicts[field] = source_vals

        return {
            "merged": merged,
            "confirmed": confirmed,
            "conflicts": conflicts,
            "new_fields": new_fields,
            "awards": awards_text,
            "socials": self._merge_socials(sources),
            "discovered_urls": self._merge_discovered_urls(sources)
        }

    def _merge_socials(self, sources: List[Dict]) -> Dict[str, str]:
        """Fusionne les réseaux sociaux trouvés."""
        merged_socials = {}
        for src in sources:
            socials = src.get("socials", {})
            if isinstance(socials, dict):
                for k, v in socials.items():
                    if k not in merged_socials or not merged_socials[k]:
                        merged_socials[k] = v
        return merged_socials

    def _merge_discovered_urls(self, sources: List[Dict]) -> List[str]:
        """Agrège et déduplique toutes les URLs découvertes."""
        all_urls = []
        for src in sources:
            urls = src.get("discovered_urls", [])
            if isinstance(urls, list):
                all_urls.extend(urls)
        # Dédupliquer tout en gardant l'ordre
        return list(dict.fromkeys(all_urls))

    def _pick_by_priority(self, source_vals: Dict[str, Any], field: str = "") -> Any:
        """Choisit la valeur selon la priorité des sources (avec override par champ)."""
        priority = self.FIELD_PRIORITY_OVERRIDE.get(field, self.SOURCE_PRIORITY)
        for preferred_source in priority:
            if preferred_source in source_vals and source_vals[preferred_source]:
                return source_vals[preferred_source]
        # Fallback : première valeur non vide
        for val in source_vals.values():
            if val:
                return val
        return ""

    def format_report(self, merge_result: Dict[str, Any]) -> str:
        """
        Génère un rapport lisible du résultat de la fusion.
        """
        lines = []
        merged = merge_result.get("merged", {})
        confirmed = merge_result.get("confirmed", {})
        conflicts = merge_result.get("conflicts", {})
        new_fields = merge_result.get("new_fields", {})

        lines.append("=" * 60)
        lines.append("RÉSULTAT DE LA FUSION")
        lines.append("=" * 60)

        lines.append("\n✅ DONNÉES CONFIRMÉES (≥2 sources concordantes) :")
        for field, val in confirmed.items():
            lines.append(f"  {field}: {val}")

        if conflicts:
            lines.append("\n⚠️  CONFLITS (valeurs différentes entre sources) :")
            for field, src_vals in conflicts.items():
                lines.append(f"  {field}:")
                for src, val in src_vals.items():
                    lines.append(f"    [{src}] {val}")
                lines.append(f"    → Retenu: {merged.get(field)}")

        if new_fields:
            lines.append("\n🆕 NOUVELLES DONNÉES (source unique) :")
            for field, src_val in new_fields.items():
                src, val = list(src_val.items())[0]
                lines.append(f"  {field}: {val}  (source: {src})")

        if merge_result.get("awards"):
            lines.append("\n🏆 AWARDS (depuis IAFD) :")
            lines.append(merge_result["awards"])

        return "\n".join(lines)


# ===========================================================================
# AWARDS CLEANER
# ===========================================================================

class AwardsCleaner:
    """
    Nettoie et formate les awards bruts en format standardisé :
        CEREMONIE
        ANNEE - Winner/Nominee: Catégorie
    """

    def clean(self, raw_awards: str) -> str:
        """Nettoie le texte brut des awards."""
        if not raw_awards:
            return ""
        lines = [_clean(l) for l in raw_awards.split("\n") if _clean(l)]
        return "\n".join(lines)

    def to_structured_list(self, raw_awards: str) -> List[Dict]:
        """
        Convertit les awards en liste de dicts :
        [{"ceremony": "AVN", "year": "2012", "type": "Winner", "category": "..."}]
        """
        result = []
        current_ceremony = ""
        current_year = ""

        for line in raw_awards.split("\n"):
            line = _clean(line)
            if not line:
                continue
            # Cérémonie (ligne sans tiret ni année isolée)
            if re.match(r'^[A-Z][^-\n]+$', line) and not re.match(r'^\d{4}', line) and "-" not in line:
                current_ceremony = line
            # Ligne avec année et mention
            elif re.match(r'^\d{4}\s*-\s*(Winner|Nominee):', line):
                m = re.match(r'^(\d{4})\s*-\s*(Winner|Nominee):\s*(.+)', line)
                if m:
                    result.append({
                        "ceremony": current_ceremony,
                        "year": m.group(1),
                        "type": m.group(2),
                        "category": m.group(3),
                    })

        return result


# ===========================================================================
# TEST / DÉMO (exécution directe)
# ===========================================================================

if __name__ == "__main__":
    import sys
    import os

    print("=== TEST SCRAPERS DEPUIS FICHIERS LOCAUX ===\n")

    # Chemins vers les fichiers HTML de test
    test_files = {
        "IAFD":      "/tmp/urlscraping/bridgette b - iafd.com.html",
        "FreeOnes":  "/tmp/urlscraping/Bridgette B bio _ Read about her profile at FreeOnes.html",
        "TheNude":   "/tmp/urlscraping/Bridgette B nude from Scoreland and Twistys at theNude.com.html",
        "Babepedia": "/mnt/user-data/uploads/Bridgette_B_-_Free_nude_pics__galleries___more_at_Babepedia.html",
    }

    scrapers_map = {
        "IAFD":      IAFDScraper(),
        "FreeOnes":  FreeOnesScraper(),
        "TheNude":   TheNudeScraper(),
        "Babepedia": BabepediaScraper(),
    }

    results = []
    for source_name, filepath in test_files.items():
        if not os.path.exists(filepath):
            print(f"[SKIP] Fichier manquant : {filepath}")
            continue
        scraper = scrapers_map[source_name]
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        result = scraper.scrape_from_html(html, url=f"file://{filepath}")
        results.append(result)
        print(f"\n{'='*50}")
        print(f"SOURCE : {source_name}")
        print(f"{'='*50}")
        for k, v in result.items():
            if k in ("source", "url"):
                continue
            if k == "awards":
                print(f"  awards: [voir section dédiée]")
            elif isinstance(v, list):
                print(f"  {k}: {', '.join(str(x) for x in v)}")
            else:
                print(f"  {k}: {v}")

    # Fusion
    if results:
        print("\n\n" + "="*60)
        print("FUSION DES SOURCES")
        print("="*60)
        merger = DataMerger()
        merged = merger.merge(results)
        print(merger.format_report(merged))

        # Nettoyage awards
        if merged.get("awards"):
            print("\n\n" + "="*60)
            print("AWARDS STRUCTURÉS")
            print("="*60)
            cleaner = AwardsCleaner()
            structured = cleaner.to_structured_list(merged["awards"])
            for award in structured[:10]:
                status = "🏆" if award["type"] == "Winner" else "  "
                print(f"  {status} [{award['ceremony']}] {award['year']} - {award['type']}: {award['category']}")
            if len(structured) > 10:
                print(f"  ... et {len(structured)-10} awards supplémentaires")
