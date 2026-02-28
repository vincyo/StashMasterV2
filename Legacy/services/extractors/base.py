import re
import subprocess
from abc import ABC, abstractmethod

from lxml import html as lxml_html

from services.scrape_cache import ScrapeCache


class BaseExtractor(ABC):
    """
    Base commune à tous les extracteurs de données performer.
    Chaque sous-classe implémente extract_from_url() qui retourne
    un dict unifié Phase 2.
    """

    SOURCE_NAME: str = "base"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    TIMEOUT = 15

    # ── Méthode principale ─────────────────────────────────────

    @abstractmethod
    def extract_from_url(self, url: str) -> dict:
        """
        Extraire les données Phase 1 + Phase 2 depuis une URL.
        
        Retourne un dict unifié avec champs Phase 1 (métadonnées)
        et Phase 2 (awards, trivia, details, tattoos, piercings, tags, urls).
        """
        ...

    def build_url(self, performer_name: str) -> str | None:
        """
        Construire l'URL d'un performer à partir de son nom.
        À surcharger dans les sous-classes.
        Retourne None si pas de logique de construction disponible.
        """
        return None

    # ── Helpers ─────────────────────────────────────────────────

    def _empty_result(self, url: str) -> dict:
        """Retourner un résultat vide avec les métadonnées source."""
        return {
            "_source": self.SOURCE_NAME,
            "_url": url,
            # Phase 1 — métadonnées
            "name": None,
            "aliases": [],
            "birthdate": None,
            "death_date": None,
            "country": None,
            "ethnicity": None,
            "hair_color": None,
            "eye_color": None,
            "height": None,
            "weight": None,
            "measurements": None,
            "fake_tits": None,
            "career_length": None,
            # Phase 2 — champs avancés
            "awards": [],
            "trivia": None,
            "details": None,
            "tattoos": [],
            "piercings": [],
            "tags": [],
            "urls": {},
        }

    def _fetch_tree(self, url: str) -> lxml_html.HtmlElement | None:
        """
        Télécharger une page HTML et retourner l'arbre lxml.
        Utilise le ScrapeCache si disponible.
        """
        try:
            command = ['curl.exe', '-L', '-s', '-A', self.HEADERS['User-Agent'], url]
            # Exécuter curl et capturer la sortie binaire brute
            result = subprocess.run(command, capture_output=True, check=True, timeout=self.TIMEOUT)
            
            # Laisser lxml analyser le contenu binaire, il auto-détectera l'encodage
            return lxml_html.fromstring(result.stdout)
        except subprocess.CalledProcessError as e:
            # Décoder stderr pour l'impression, avec un fallback sûr
            error_message = e.stderr.decode('utf-8', errors='replace') if e.stderr else ''
            print(f"[{self.SOURCE_NAME}] Erreur fetch {url}: {error_message}")
            return None
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Erreur fetch {url}: {e}")
            return None

    def _get_text(self, tree: lxml_html.HtmlElement, xpath: str) -> str | None:
        """Extraire le texte d'un nœud via XPath."""
        nodes = tree.xpath(xpath)
        if nodes:
            if isinstance(nodes[0], str):
                return nodes[0].strip() or None
            text = nodes[0].text_content().strip()
            return text if text else None
        return None

    def _get_texts(self, tree: lxml_html.HtmlElement, xpath: str) -> list[str]:
        """Extraire une liste de textes via XPath."""
        nodes = tree.xpath(xpath)
        result = []
        for n in nodes:
            if isinstance(n, str):
                t = n.strip()
            else:
                t = n.text_content().strip()
            if t:
                result.append(t)
        return result

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normaliser un nom pour construction d'URL (espaces → tirets, lowercase)."""
        name = name.strip().lower()
        name = re.sub(r'[^a-z0-9\s-]', '', name)
        name = re.sub(r'\s+', '-', name)
        return name

    @staticmethod
    def _normalize_name_plus(name: str) -> str:
        """Normaliser un nom pour URL FreeOnes (espaces → +)."""
        return name.strip().replace(' ', '+')

    @staticmethod
    def _normalize_name_underscore(name: str) -> str:
        """Normaliser un nom pour URL (espaces → _)."""
        return name.strip().replace(' ', '_')
