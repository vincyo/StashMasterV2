"""
source_finder.py - Recherche des URLs manquantes pour les 4 sources
====================================================================

Pour un performer donné, détecte quelles sources manquent parmi :
    IAFD, FreeOnes, TheNude, Babepedia

Puis effectue une recherche sur chaque site manquant et propose
les meilleurs candidats à valider.

Usage standalone :
    python source_finder.py --name "Bridgette B" [--aliases "Spanish Doll"]

Usage depuis StashMaster (import) :
    from source_finder import SourceFinder
    finder = SourceFinder()
    missing  = finder.detect_missing(existing_urls)
    results  = finder.find_missing(name="Bridgette B", missing_sources=missing)
    best     = finder.best_candidates(results)
"""

import re
import time
import unicodedata
import requests
from urllib.parse import quote_plus, urlparse
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT         = 12
DELAY           = 1.0
SCORE_THRESHOLD = 40
ALL_SOURCES     = ["IAFD", "FreeOnes", "TheNude", "Babepedia"]

SOURCE_DOMAINS = {
    "IAFD":      ["iafd.com"],
    "FreeOnes":  ["freeones.com", "freeones.xxx"],
    "TheNude":   ["thenude.com"],
    "Babepedia": ["babepedia.com"],
}

SEARCH_URLS = {
    "IAFD":      "https://www.iafd.com/results.asp?pagetype=person&searchtype=name&sex=f&q={query}",
    "FreeOnes":  "https://www.freeones.com/search?q={query}&t=person",
    "TheNude":   "https://www.thenude.com/srch.php?q={query}&type=model",
    "Babepedia": "https://www.babepedia.com/search/{query}",
}

SEARCH_URLS_ALT = {
    "IAFD":      "https://www.iafd.com/results.asp?pagetype=person&searchtype=name&q={query}",
    "FreeOnes":  "https://www.freeones.com/search?q={query}",
    "TheNude":   "https://www.thenude.com/srch.php?q={query}",
    "Babepedia": "https://www.babepedia.com/search.php?q={query}",
}


# ---------------------------------------------------------------------------
# Modèle de données
# ---------------------------------------------------------------------------

@dataclass
class SearchCandidate:
    source:     str
    url:        str
    found_name: str
    score:      int = 0
    extra:      Dict = field(default_factory=dict)

    @property
    def is_good_match(self):
        return self.score >= SCORE_THRESHOLD

    def __str__(self):
        stars = "★" * (self.score // 20)
        return f"[{self.source}] {stars} ({self.score}/100) {self.found_name}\n  → {self.url}"


@dataclass
class FinderResult:
    source:     str
    searched:   bool = False
    candidates: List = field(default_factory=list)
    error:      str = ""

    @property
    def best(self):
        valid = [c for c in self.candidates if c.is_good_match]
        return max(valid, key=lambda c: c.score) if valid else None

    @property
    def has_match(self):
        return self.best is not None


# ---------------------------------------------------------------------------
# Utilitaires de scoring
# ---------------------------------------------------------------------------

def _normalize(text):
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _score_name_match(target, found, aliases=None):
    aliases = aliases or []
    t_norm  = _normalize(target)
    f_norm  = _normalize(found)

    if t_norm == f_norm:
        return 100
    for alias in aliases:
        if _normalize(alias) == f_norm:
            return 95
    if t_norm in f_norm or f_norm in t_norm:
        return 80
    for alias in aliases:
        a_norm = _normalize(alias)
        if a_norm in f_norm or f_norm in a_norm:
            return 70
    t_words = set(t_norm.split())
    f_words = set(f_norm.split())
    if t_words and t_words.issubset(f_words):
        return 60
    common = t_words & f_words
    if common:
        return int(30 + (len(common) / max(len(t_words), 1)) * 20)
    return 0


def _extract_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "").lower()
    except Exception:
        return ""


def _fetch(url, timeout=TIMEOUT):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "html.parser")
        return None
    except Exception:
        return None


def _build_search_url(template, query):
    return template.format(query=quote_plus(query))


def _deduplicate(candidates):
    seen = {}
    for c in candidates:
        url = c.url.rstrip("/")
        if url not in seen or c.score > seen[url].score:
            seen[url] = c
    return sorted(seen.values(), key=lambda c: c.score, reverse=True)


# ---------------------------------------------------------------------------
# Parseurs de résultats de recherche
# ---------------------------------------------------------------------------

def _parse_iafd_results(soup, name, aliases):
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "person.rme" not in href:
            continue
        if href.startswith("/"):
            href = "https://www.iafd.com" + href
        href = href.rstrip("#")
        found_name = a.get_text(strip=True)
        if not found_name:
            p = a.find_parent()
            found_name = p.get_text(strip=True) if p else ""
        extra = {}
        row = a.find_parent("tr") or a.find_parent("div")
        if row:
            m = re.search(r"\b(\w+ \d+, \d{4}|\d{4}-\d{2}-\d{2})\b",
                          row.get_text(separator="|", strip=True))
            if m:
                extra["birthdate"] = m.group(1)
        score = _score_name_match(name, found_name, aliases)
        if score > 0:
            candidates.append(SearchCandidate(
                source="IAFD", url=href, found_name=found_name,
                score=score, extra=extra))
    return _deduplicate(candidates)


def _parse_freeones_results(soup, name, aliases):
    candidates = []
    excluded = {"performers", "search", "login", "register", "videos",
                "photos", "clips", "blog", "contact", "terms", "privacy"}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Pattern : /slug ou /slug/bio (freeones.com)
        if not re.search(r"freeones\.(?:com|xxx)/[a-z0-9-]+(?:/bio)?$", href):
            if not re.match(r"^/[a-z0-9][a-z0-9-]+(?:/bio)?$", href):
                continue
        if href.startswith("/"):
            href = "https://www.freeones.com" + href
        if not href.endswith("/bio"):
            href = href.rstrip("/") + "/bio"
        slug = href.replace("/bio", "").rstrip("/").split("/")[-1]
        if slug in excluded or len(slug) < 3:
            continue
        found_name = a.get_text(strip=True)
        if not found_name:
            img = a.find("img")
            found_name = img.get("alt", "") if img else ""
        if not found_name:
            found_name = slug.replace("-", " ").title()
        score = _score_name_match(name, found_name, aliases)
        if score > 0:
            candidates.append(SearchCandidate(
                source="FreeOnes", url=href, found_name=found_name, score=score))
    return _deduplicate(candidates)


def _parse_thenude_results(soup, name, aliases):
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.search(r"thenude\.com/[^/]+_\d+\.htm", href):
            if not re.match(r"^/[^/]+_\d+\.htm$", href):
                continue
        # Ignorer liens de pagination (contiennent des query params)
        if "?" in href or "page_nr" in href or "filter_" in href:
            continue
        if href.startswith("/"):
            href = "https://www.thenude.com" + href
        found_name = a.get_text(strip=True)
        if not found_name:
            m = re.search(r"/([^/]+)_\d+\.htm$", href)
            if m:
                found_name = m.group(1).replace("%20", " ").replace("_", " ").strip()
        # Ignorer noms trop courts (icônes, chiffres de pagination)
        if len(found_name.strip()) < 3:
            continue
        score = _score_name_match(name, found_name, aliases)
        if score > 0:
            candidates.append(SearchCandidate(
                source="TheNude", url=href, found_name=found_name, score=score))
    return _deduplicate(candidates)


def _parse_babepedia_results(soup, name, aliases):
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.search(r"babepedia\.com/babe/[^/\s#]+$", href):
            if not re.match(r"^/babe/[^/\s#]+$", href):
                continue
        # Ignorer ancres (#menu, #info, etc.)
        if "#" in href:
            continue
        if href.startswith("/"):
            href = "https://www.babepedia.com" + href
        found_name = a.get_text(strip=True)
        if not found_name:
            m = re.search(r"/babe/([^/\s]+)$", href)
            if m:
                found_name = m.group(1).replace("_", " ").strip()
        extra = {}
        card = a.find_parent(["div", "li", "tr"])
        if card:
            m = re.search(r"\b(\d{4})\b", card.get_text(separator=" ", strip=True))
            if m:
                extra["year"] = m.group(1)
        # Ignorer noms trop courts (icônes)
        if len(found_name.strip()) < 3:
            continue
        score = _score_name_match(name, found_name, aliases)
        if score > 0:
            candidates.append(SearchCandidate(
                source="Babepedia", url=href, found_name=found_name,
                score=score, extra=extra))
    return _deduplicate(candidates)


PARSERS = {
    "IAFD":      _parse_iafd_results,
    "FreeOnes":  _parse_freeones_results,
    "TheNude":   _parse_thenude_results,
    "Babepedia": _parse_babepedia_results,
}


# ---------------------------------------------------------------------------
# Construction d'URLs directes + vérification
# ---------------------------------------------------------------------------

def _build_direct_urls(name, aliases):
    all_names = [name] + (aliases or [])
    result = {s: [] for s in ALL_SOURCES}
    for n in all_names:
        n = n.strip()
        perfid = re.sub(r"[^a-z0-9]", "", n.lower())
        slug   = re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
        result["IAFD"].append(
            f"https://www.iafd.com/person.rme/perfid={perfid}/gender=f/{slug}.htm")
        result["FreeOnes"].append(
            f"https://www.freeones.com/{slug}/bio")
        result["Babepedia"].append(
            f"https://www.babepedia.com/babe/{n.replace(' ', '_').replace('.', '')}")
        # TheNude nécessite un ID numérique → pas de construction directe fiable
    return result


def _verify_direct_url(url, source, name, aliases, timeout=TIMEOUT):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        h1 = soup.find("h1")
        found_name = h1.get_text(strip=True) if h1 else ""
        if not found_name:
            title = soup.find("title")
            if title:
                found_name = title.get_text(strip=True).split("-")[0].split("|")[0].strip()
        score = _score_name_match(name, found_name, aliases)
        if score >= SCORE_THRESHOLD:
            return SearchCandidate(
                source=source, url=str(resp.url), found_name=found_name,
                score=score, extra={"method": "direct"})
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Classe principale
# ---------------------------------------------------------------------------

class SourceFinder:

    def __init__(self, timeout=TIMEOUT, delay=DELAY):
        self.timeout = timeout
        self.delay   = delay

    # ── Détection ──────────────────────────────────────────────────────

    def detect_missing(self, existing_urls):
        """Retourne la liste des sources absentes dans les URLs existantes."""
        present = set()
        for url in existing_urls:
            domain = _extract_domain(url)
            for source, domains in SOURCE_DOMAINS.items():
                if any(d in domain for d in domains):
                    present.add(source)
        return [s for s in ALL_SOURCES if s not in present]

    def sources_status(self, existing_urls):
        """Retourne { source: texte_statut } pour affichage."""
        present_map = {}
        for url in existing_urls:
            domain = _extract_domain(url)
            for source, domains in SOURCE_DOMAINS.items():
                if any(d in domain for d in domains):
                    present_map[source] = url
        status = {}
        for source in ALL_SOURCES:
            if source in present_map:
                status[source] = f"✅  {present_map[source]}"
            else:
                status[source] = "❌  manquante"
        return status

    # ── Recherche pour une source ───────────────────────────────────────

    def find_for_source(self, source, name, aliases=None):
        aliases = aliases or []
        result  = FinderResult(source=source, searched=True)

        # Étape 1 : URL directe (rapide, sans recherche)
        for url in _build_direct_urls(name, aliases).get(source, []):
            candidate = _verify_direct_url(url, source, name, aliases, self.timeout)
            if candidate:
                result.candidates.append(candidate)
        if result.candidates:
            return result

        time.sleep(self.delay)

        # Étape 2 : Page de recherche du site
        candidates = self._search_on_site(source, name, aliases)
        # Essayer avec un alias si peu de résultats
        if len(candidates) < 2 and aliases:
            for alias in aliases[:2]:
                candidates += self._search_on_site(source, alias, aliases)
        result.candidates = _deduplicate(candidates)
        return result

    def _search_on_site(self, source, query, aliases):
        parser = PARSERS.get(source)
        if not parser:
            return []
        soup = _fetch(_build_search_url(SEARCH_URLS[source], query), self.timeout)
        if soup is None and source in SEARCH_URLS_ALT:
            soup = _fetch(_build_search_url(SEARCH_URLS_ALT[source], query), self.timeout)
        if soup is None:
            return []
        return parser(soup, query, aliases)

    # ── Recherche toutes sources manquantes ─────────────────────────────

    def find_missing(self, name, existing_urls=None, aliases=None,
                     missing_sources=None, progress_callback=None):
        existing_urls   = existing_urls or []
        aliases         = aliases or []
        missing_sources = missing_sources or self.detect_missing(existing_urls)
        results         = {}

        for i, source in enumerate(missing_sources):
            if progress_callback:
                progress_callback(source, None)
            result = self.find_for_source(source, name, aliases)
            results[source] = result
            if progress_callback:
                progress_callback(source, result)
            if i < len(missing_sources) - 1:
                time.sleep(self.delay)

        return results

    # ── Sélection ───────────────────────────────────────────────────────

    def best_candidates(self, results):
        return {source: result.best for source, result in results.items()}

    def auto_select_urls(self, results, min_score=80):
        """URLs sélectionnées automatiquement si score >= min_score."""
        return {
            source: result.best.url
            for source, result in results.items()
            if result.best and result.best.score >= min_score
        }

    # ── Rapport ─────────────────────────────────────────────────────────

    def build_report(self, name, existing_urls, results):
        lines = [
            "=" * 70,
            f"RECHERCHE DE SOURCES MANQUANTES — {name}",
            "=" * 70,
            "\n📋 STATUT DES SOURCES :",
        ]
        for source, st in self.sources_status(existing_urls).items():
            lines.append(f"  {source:12} {st}")

        lines.append("\n🔍 RÉSULTATS DE RECHERCHE :")
        for source, result in results.items():
            lines.append(f"\n  ── {source} ──")
            if result.error:
                lines.append(f"  💥 Erreur : {result.error}")
            elif not result.candidates:
                lines.append("  ❌ Aucun candidat trouvé")
            else:
                for c in result.candidates[:5]:
                    flag = "⭐" if c.score >= 80 else ("👍" if c.score >= 50 else "❓")
                    lines.append(f"  {flag} [{c.score:3d}/100] {c.found_name}")
                    lines.append(f"       {c.url}")
                    if c.extra.get("birthdate"):
                        lines.append(f"       Naissance : {c.extra['birthdate']}")
                    if c.extra.get("method") == "direct":
                        lines.append(f"       (trouvé par URL directe)")

        auto = self.auto_select_urls(results)
        if auto:
            lines.append("\n✅ SÉLECTION AUTOMATIQUE (score ≥ 80) :")
            for source, url in auto.items():
                lines.append(f"  {source:12} {url}")

        no_match = [s for s, r in results.items() if not r.has_match]
        if no_match:
            lines.append(f"\n⚠️  Non trouvées : {', '.join(no_match)}")
            lines.append("   → Vérification manuelle recommandée")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


# ===========================================================================
# Intégration ScraperOrchestrator
# ===========================================================================

def patch_orchestrator_with_finder(orchestrator_class):
    """
    Ajoute find_and_scrape_missing à ScraperOrchestrator.
    Usage :
        from source_finder import patch_orchestrator_with_finder
        from scrapers import ScraperOrchestrator
        patch_orchestrator_with_finder(ScraperOrchestrator)
        orchestrator = ScraperOrchestrator()
        result = orchestrator.find_and_scrape_missing("Bridgette B", existing_urls)
    """
    def find_and_scrape_missing(self, name, existing_urls,
                                 aliases=None, auto_threshold=80):
        finder  = SourceFinder()
        missing = finder.detect_missing(existing_urls)
        if not missing:
            print("[FINDER] Toutes les sources sont déjà présentes.")
            return {"missing": [], "found": {}, "new_data": []}

        print(f"[FINDER] Sources manquantes : {', '.join(missing)}")
        search_results = finder.find_missing(
            name=name, existing_urls=existing_urls, aliases=aliases or [])
        auto_urls = finder.auto_select_urls(search_results, min_score=auto_threshold)

        new_data = []
        for source, url in auto_urls.items():
            scraper = self.detect_source(url)
            if scraper:
                print(f"[FINDER] Scraping {source} : {url}")
                data = scraper.scrape(url)
                if data:
                    new_data.append(data)

        return {
            "missing":        missing,
            "found":          auto_urls,
            "new_data":       new_data,
            "search_results": search_results,
        }

    orchestrator_class.find_and_scrape_missing = find_and_scrape_missing
    return orchestrator_class


# ===========================================================================
# Widget Tkinter
# ===========================================================================

class SourceFinderWidget:
    """
    Fenêtre Tkinter secondaire pour rechercher et sélectionner
    les URLs manquantes, intégrable dans StashMaster.

    Usage :
        widget = SourceFinderWidget(
            parent, name="Bridgette B",
            existing_urls=[...], aliases=[...],
            on_urls_selected=lambda selected_dict: ...
        )
        widget.show()
    """

    def __init__(self, parent, name, existing_urls=None,
                 aliases=None, on_urls_selected=None):
        import tkinter as tk
        from tkinter import ttk, messagebox
        self.tk  = tk
        self.ttk = ttk
        self.messagebox = messagebox

        self.parent           = parent
        self.name             = name
        self.existing_urls    = existing_urls or []
        self.aliases          = aliases or []
        self.on_urls_selected = on_urls_selected
        self.finder           = SourceFinder()
        self.results          = {}
        self._selected_vars   = {}
        self._missing         = []

    def show(self):
        tk  = self.tk
        ttk = self.ttk

        self.win = tk.Toplevel(self.parent)
        self.win.title(f"🔍 Sources manquantes — {self.name}")
        self.win.geometry("880x600")
        self.win.grab_set()

        # ── Header ──
        hdr = tk.Frame(self.win, bg="#0d3349", pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔍 Recherche de sources manquantes",
                 font=("Arial", 12, "bold"), bg="#0d3349", fg="white").pack()
        tk.Label(hdr, text=f"Performer : {self.name}  |  Aliases : {', '.join(self.aliases) or '—'}",
                 font=("Arial", 9), bg="#0d3349", fg="#aad4f5").pack()

        # ── Statut des 4 sources ──
        stat_frame = tk.LabelFrame(self.win, text="Statut des sources", padx=8, pady=4)
        stat_frame.pack(fill="x", padx=10, pady=5)

        status = self.finder.sources_status(self.existing_urls)
        self._missing = self.finder.detect_missing(self.existing_urls)
        self._status_labels = {}
        for col, source in enumerate(ALL_SOURCES):
            frm = tk.Frame(stat_frame)
            frm.grid(row=0, column=col, padx=16, pady=2, sticky="w")
            tk.Label(frm, text=source, font=("Arial", 9, "bold")).pack(anchor="w")
            is_present = "✅" in status[source]
            short = status[source] if is_present else "❌  manquante"
            lbl = tk.Label(frm, text=short[:42], font=("Arial", 8),
                           fg="#2e7d32" if is_present else "#c62828")
            lbl.pack(anchor="w")
            self._status_labels[source] = lbl

        # ── Progression ──
        self.prog_label = tk.Label(self.win, text="En attente…",
                                   anchor="w", font=("Arial", 9))
        self.prog_label.pack(fill="x", padx=10, pady=(4, 0))
        self.prog_bar = ttk.Progressbar(self.win, mode="determinate")
        self.prog_bar.pack(fill="x", padx=10, pady=(0, 4))

        # ── Notebook (onglet par source manquante) ──
        nb_frame = tk.LabelFrame(self.win, text="Candidats", padx=6, pady=4)
        nb_frame.pack(fill="both", expand=True, padx=10, pady=2)

        if not self._missing:
            tk.Label(nb_frame,
                     text="✅ Toutes les sources sont déjà présentes !",
                     font=("Arial", 11), fg="#2e7d32").pack(pady=30)
        else:
            self.notebook = ttk.Notebook(nb_frame)
            self.notebook.pack(fill="both", expand=True)
            self._tabs = {}
            for source in self._missing:
                tab = tk.Frame(self.notebook)
                self.notebook.add(tab, text=f"  {source}  ")
                self._tabs[source] = tab
                tk.Label(tab, text="⏳ En attente…",
                         font=("Arial", 9), fg="gray").pack(pady=20)

        # ── Boutons ──
        btn_frame = tk.Frame(self.win, pady=6)
        btn_frame.pack(fill="x", padx=10)

        self.btn_search = ttk.Button(
            btn_frame, text="🔍 Lancer la recherche",
            command=self._start_search,
            state="normal" if self._missing else "disabled")
        self.btn_search.pack(side="left", padx=4)

        self.btn_apply = ttk.Button(
            btn_frame, text="✅ Ajouter les URLs sélectionnées",
            command=self._apply, state="disabled")
        self.btn_apply.pack(side="left", padx=4)

        self.result_count_lbl = tk.Label(btn_frame, text="", fg="#1565c0",
                                          font=("Arial", 9, "bold"))
        self.result_count_lbl.pack(side="left", padx=10)

        ttk.Button(btn_frame, text="Fermer",
                   command=self.win.destroy).pack(side="right", padx=4)

    # ── Logique de recherche ─────────────────────────────────────────

    def _start_search(self):
        import threading
        self.btn_search.config(state="disabled")
        self.btn_apply.config(state="disabled")
        self.prog_bar.config(maximum=max(len(self._missing), 1), value=0)
        self._done = 0
        self.results = {}

        def run():
            for source in self._missing:
                self.win.after(0, self.prog_label.config,
                               {"text": f"🔄 Recherche {source}…"})
                result = self.finder.find_for_source(
                    source, self.name, self.aliases)
                self.results[source] = result
                self._done += 1
                self.win.after(0, self._on_source_done, source, result, self._done)
            self.win.after(0, self._search_done)

        threading.Thread(target=run, daemon=True).start()

    def _on_source_done(self, source, result, done):
        self.prog_bar["value"] = done
        self._render_tab(source, result)

    def _render_tab(self, source, result):
        tk  = self.tk
        ttk = self.ttk
        tab = self._tabs.get(source)
        if not tab:
            return
        for w in tab.winfo_children():
            w.destroy()

        if not result.candidates:
            tk.Label(tab, text="❌ Aucun résultat — recherche manuelle requise",
                     font=("Arial", 9), fg="#c62828").pack(pady=15)
            return

        # Variable radio pour sélection
        var = tk.StringVar(value=result.best.url if result.best else "")
        self._selected_vars[source] = var

        # En-tête colonnes
        hdr = tk.Frame(tab, bg="#e3f2fd")
        hdr.pack(fill="x", padx=4, pady=(4, 0))
        for txt, w in [("✔", 4), ("Score", 7), ("Nom trouvé", 22), ("URL", 0)]:
            tk.Label(hdr, text=txt, width=w, bg="#e3f2fd",
                     font=("Arial", 8, "bold"), anchor="w").pack(side="left")

        # Scroll area
        canvas = tk.Canvas(tab, height=210, highlightthickness=0)
        sb = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=4)

        for c in result.candidates[:12]:
            color = "#1b5e20" if c.score >= 80 else (
                    "#e65100" if c.score >= 50 else "#757575")
            method_tag = " 📎direct" if c.extra.get("method") == "direct" else ""
            row = tk.Frame(inner, bd=0)
            row.pack(fill="x", pady=1)
            ttk.Radiobutton(row, variable=var, value=c.url).pack(side="left")
            tk.Label(row, text=f"{c.score}/100", width=7,
                     fg=color, font=("Arial", 8, "bold")).pack(side="left")
            tk.Label(row, text=(c.found_name[:22] + method_tag)[:26], width=26,
                     anchor="w", font=("Arial", 8)).pack(side="left")
            tk.Label(row, text=c.url[:68], anchor="w",
                     font=("Arial", 8), fg="#0d47a1",
                     cursor="hand2").pack(side="left", fill="x")

        # Note si aucun bon score
        if not result.has_match:
            tk.Label(tab,
                     text="⚠️  Aucun résultat fiable — sélectionner manuellement ou ignorer",
                     font=("Arial", 8), fg="#e65100").pack(pady=3)

    def _search_done(self):
        found = sum(1 for r in self.results.values() if r.has_match)
        self.prog_label.config(
            text=f"✅ Terminé — {found}/{len(self._missing)} source(s) trouvée(s)")
        self.btn_search.config(state="normal")
        self.result_count_lbl.config(
            text=f"{found} nouvelle(s) source(s) trouvée(s)" if found else "")
        if found:
            self.btn_apply.config(state="normal")

    def _apply(self):
        selected = {s: v.get() for s, v in self._selected_vars.items() if v.get()}
        if not selected:
            self.messagebox.showwarning("Aucune sélection",
                                        "Sélectionnez au moins une URL.")
            return
        msg = "Ajouter ces URLs ?\n\n" + "\n".join(
            f"  [{s}]  {u}" for s, u in selected.items())
        if not self.messagebox.askyesno("Confirmer", msg):
            return
        if self.on_urls_selected:
            self.on_urls_selected(selected)
        self.messagebox.showinfo("Succès",
                                  f"{len(selected)} URL(s) ajoutée(s).")
        self.win.destroy()


# ===========================================================================
# CLI
# ===========================================================================

def _cli():
    import argparse, sys

    parser = argparse.ArgumentParser(
        description="Recherche les URLs manquantes pour un performer Stash")
    parser.add_argument("--name",          required=True)
    parser.add_argument("--aliases",       nargs="*", default=[])
    parser.add_argument("--existing-urls", nargs="*", default=[])
    parser.add_argument("--sources",       nargs="*", choices=ALL_SOURCES)
    parser.add_argument("--timeout",       type=int, default=TIMEOUT)
    parser.add_argument("--min-score",     type=int, default=SCORE_THRESHOLD)
    args = parser.parse_args()

    finder = SourceFinder(timeout=args.timeout)

    print(f"\nPerformer : {args.name}")
    if args.aliases:
        print(f"Aliases   : {', '.join(args.aliases)}")
    print()
    for s, st in finder.sources_status(args.existing_urls).items():
        print(f"  {s:12} {st}")

    missing = args.sources or finder.detect_missing(args.existing_urls)
    if not missing:
        print("\n✅ Toutes les sources sont déjà présentes !")
        sys.exit(0)

    print(f"\nRecherche pour : {', '.join(missing)}")
    print("─" * 60)

    def progress(source, result):
        if result is None:
            print(f"  🔄 {source}…", flush=True)
        elif result.has_match:
            print(f"  ✅ {source} : {len(result.candidates)} candidat(s)")
        else:
            print(f"  ❌ {source} : aucun résultat")

    results = finder.find_missing(
        name=args.name, existing_urls=args.existing_urls,
        aliases=args.aliases, missing_sources=missing,
        progress_callback=progress)

    print()
    print(finder.build_report(args.name, args.existing_urls, results))


if __name__ == "__main__":
    _cli()
