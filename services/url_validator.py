"""
url_validator.py - Validation et nettoyage des URLs de performers Stash
=======================================================================

Fonctionnement :
  1. Lit les URLs depuis la table `performer_urls` de la base SQLite Stash
  2. Teste chaque URL (HEAD puis GET fallback) avec timeout court
  3. Classifie : ✅ Active / ❌ Morte / ⚠️ Redirigée / ⏭️ Ignorée
  4. Propose la suppression des URLs mortes (avec confirmation ou mode auto)
  5. Écrit les suppressions dans la BDD ET met à jour Stash via GraphQL

Usage standalone :
    python url_validator.py --db "H:/Stash/stash-go.sqlite" [--auto-delete] [--dry-run]

Usage depuis StashMaster (import) :
    from url_validator import URLValidator
    validator = URLValidator(db_path="...", stash_url="http://localhost:9999")
    results = validator.validate_all(performer_id=42)
    validator.delete_dead_urls(results, confirm=True)
"""

import sqlite3
import requests
import threading
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH     = "H:/Stash/stash-go.sqlite"
DEFAULT_STASH_URL   = "http://localhost:9999"
DEFAULT_TIMEOUT     = 10       # secondes par requête
DEFAULT_MAX_WORKERS = 8        # requêtes parallèles
DEFAULT_RETRY       = 1        # nb de retry en cas d'échec réseau

# Domaines à ne jamais supprimer même si inaccessibles (VPN, abonnement, etc.)
WHITELIST_DOMAINS = {
    "onlyfans.com",
    "fansly.com",
    "manyvids.com",
    "loyalfans.com",
    "fancentro.com",
    "4based.com",
    "unlockd.com",
}

# Codes HTTP considérés comme "vivants" (l'URL existe)
ALIVE_CODES = {200, 201, 202, 203, 204, 206, 301, 302, 303, 307, 308}
# Codes considérés comme "mortes" (contenu supprimé/inexistant)
DEAD_CODES  = {404, 410, 451}
# Codes ambigus (accès refusé mais la page peut exister)
AMBIGUOUS_CODES = {401, 403, 429, 503}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
}


# ---------------------------------------------------------------------------
# Modèle de données
# ---------------------------------------------------------------------------

class URLStatus(Enum):
    ACTIVE    = "active"      # ✅ URL vivante
    DEAD      = "dead"        # ❌ URL morte (404/410 confirmé)
    REDIRECT  = "redirect"    # ⚠️ Redirigée (301/302)
    AMBIGUOUS = "ambiguous"   # ❓ Accès refusé / timeout (on garde)
    WHITELISTED = "whitelisted"  # ⏭️ Domaine whitelist (pas de test)
    ERROR     = "error"       # 💥 Erreur réseau inattendue


@dataclass
class URLCheckResult:
    performer_id: int
    performer_name: str
    position: int
    url: str
    status: URLStatus
    http_code: Optional[int] = None
    redirect_to: Optional[str] = None
    error_msg: Optional[str] = None
    check_duration_ms: int = 0
    domain: str = field(init=False)

    def __post_init__(self):
        self.domain = _extract_domain(self.url)

    @property
    def should_delete(self) -> bool:
        return self.status == URLStatus.DEAD

    @property
    def icon(self) -> str:
        icons = {
            URLStatus.ACTIVE:      "✅",
            URLStatus.DEAD:        "❌",
            URLStatus.REDIRECT:    "↪️ ",
            URLStatus.AMBIGUOUS:   "❓",
            URLStatus.WHITELISTED: "⏭️ ",
            URLStatus.ERROR:       "💥",
        }
        return icons.get(self.status, "?")

    def __str__(self) -> str:
        base = f"{self.icon} [{self.http_code or '---'}] {self.url}"
        if self.redirect_to:
            base += f"\n     → {self.redirect_to}"
        if self.error_msg:
            base += f"\n     ! {self.error_msg}"
        return base


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def _extract_domain(url: str) -> str:
    """Extrait le domaine d'une URL."""
    m = re.search(r'https?://(?:www\.)?([^/]+)', url)
    return m.group(1).lower() if m else ""


def _is_whitelisted(url: str) -> bool:
    """Retourne True si le domaine est dans la whitelist."""
    domain = _extract_domain(url)
    return any(w in domain for w in WHITELIST_DOMAINS)


def _check_single_url(url: str, timeout: int = DEFAULT_TIMEOUT,
                       retry: int = DEFAULT_RETRY) -> Tuple[Optional[int], Optional[str], str]:
    """
    Vérifie une URL. Retourne (http_code, redirect_url, error_msg).
    Essaie d'abord HEAD, puis GET si HEAD échoue ou donne un résultat suspect.
    """
    last_error = ""
    for attempt in range(retry + 1):
        try:
            # 1. Tentative HEAD (plus rapide, pas de body)
            resp = requests.head(
                url, headers=HEADERS, timeout=timeout,
                allow_redirects=True
            )
            code = resp.status_code
            redirect = str(resp.url) if resp.url and str(resp.url) != url else None

            # Certains serveurs renvoient 405 sur HEAD → fallback GET
            if code in (405, 501):
                raise requests.exceptions.InvalidSchema("HEAD not allowed")

            return code, redirect, ""

        except requests.exceptions.InvalidSchema:
            # Fallback GET
            try:
                resp = requests.get(
                    url, headers=HEADERS, timeout=timeout,
                    allow_redirects=True, stream=True
                )
                resp.close()
                code = resp.status_code
                redirect = str(resp.url) if resp.url and str(resp.url) != url else None
                return code, redirect, ""
            except Exception as e2:
                last_error = str(e2)

        except requests.exceptions.ConnectionError as e:
            last_error = f"ConnectionError: {e}"
        except requests.exceptions.Timeout:
            last_error = f"Timeout ({timeout}s)"
        except requests.exceptions.TooManyRedirects:
            return None, None, "TooManyRedirects"
        except Exception as e:
            last_error = str(e)

        if attempt < retry:
            time.sleep(1)

    return None, None, last_error


# ---------------------------------------------------------------------------
# Classe principale
# ---------------------------------------------------------------------------

class URLValidator:
    """
    Valide les URLs des performers stockées dans la BDD Stash.

    Paramètres
    ----------
    db_path   : chemin vers stash-go.sqlite
    stash_url : URL de l'API Stash (pour les suppressions GraphQL)
    api_key   : clé API Stash si authentification requise
    timeout   : timeout HTTP en secondes
    max_workers : nombre de threads parallèles
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        stash_url: str = DEFAULT_STASH_URL,
        api_key: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        max_workers: int = DEFAULT_MAX_WORKERS,
    ):
        self.db_path = db_path
        self.stash_url = stash_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_workers = max_workers
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lecture BDD
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_all_performer_urls(
        self, performer_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Retourne toutes les URLs de performers depuis performer_urls.
        Si performer_id est fourni, filtre sur ce performer.
        """
        conn = self._get_connection()
        try:
            if performer_id:
                rows = conn.execute(
                    """
                    SELECT pu.performer_id, p.name, pu.position, pu.url
                    FROM performer_urls pu
                    JOIN performers p ON p.id = pu.performer_id
                    WHERE pu.performer_id = ?
                    ORDER BY pu.performer_id, pu.position
                    """,
                    (performer_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT pu.performer_id, p.name, pu.position, pu.url
                    FROM performer_urls pu
                    JOIN performers p ON p.id = pu.performer_id
                    ORDER BY pu.performer_id, pu.position
                    """
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_performer_count(self) -> Tuple[int, int]:
        """Retourne (nb performers avec URLs, nb total d'URLs)."""
        conn = self._get_connection()
        try:
            nb_urls = conn.execute("SELECT COUNT(*) FROM performer_urls").fetchone()[0]
            nb_perf = conn.execute(
                "SELECT COUNT(DISTINCT performer_id) FROM performer_urls"
            ).fetchone()[0]
            return nb_perf, nb_urls
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Vérification HTTP
    # ------------------------------------------------------------------

    def _check_url_entry(self, entry: Dict) -> URLCheckResult:
        """Vérifie une entrée URL et retourne un URLCheckResult."""
        url = entry["url"]
        result_base = dict(
            performer_id=entry["performer_id"],
            performer_name=entry["name"],
            position=entry["position"],
            url=url,
        )

        # Whitelist
        if _is_whitelisted(url):
            return URLCheckResult(
                **result_base,
                status=URLStatus.WHITELISTED,
            )

        # Vérification HTTP
        t0 = time.monotonic()
        code, redirect, error = _check_single_url(url, self.timeout)
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        if error and code is None:
            # Timeout ou erreur réseau → ambiguïté, on ne supprime pas
            return URLCheckResult(
                **result_base,
                status=URLStatus.ERROR,
                error_msg=error,
                check_duration_ms=elapsed_ms,
            )

        if code in DEAD_CODES:
            status = URLStatus.DEAD
        elif code in AMBIGUOUS_CODES:
            status = URLStatus.AMBIGUOUS
        elif code in (301, 302, 303, 307, 308) and redirect and redirect != url:
            status = URLStatus.REDIRECT
        elif code and code < 400:
            status = URLStatus.ACTIVE
        else:
            status = URLStatus.AMBIGUOUS  # code inconnu → on garde

        return URLCheckResult(
            **result_base,
            status=status,
            http_code=code,
            redirect_to=redirect if redirect != url else None,
            check_duration_ms=elapsed_ms,
        )

    def validate_urls(
        self,
        urls: List[Dict],
        progress_callback=None,
    ) -> List[URLCheckResult]:
        """
        Valide une liste d'entrées URL en parallèle.
        progress_callback(current, total, result) est appelé après chaque check.
        """
        results = []
        total = len(urls)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._check_url_entry, entry): entry for entry in urls}
            done = 0
            for future in as_completed(futures):
                result = future.result()
                with self._lock:
                    results.append(result)
                    done += 1
                if progress_callback:
                    progress_callback(done, total, result)

        # Tri : performer_id puis position
        results.sort(key=lambda r: (r.performer_id, r.position))
        return results

    def validate_all(
        self,
        performer_id: Optional[int] = None,
        progress_callback=None,
    ) -> List[URLCheckResult]:
        """
        Valide toutes les URLs (ou celles d'un seul performer).
        """
        entries = self.get_all_performer_urls(performer_id)
        if not entries:
            return []
        return self.validate_urls(entries, progress_callback)

    # ------------------------------------------------------------------
    # Suppression des URLs mortes
    # ------------------------------------------------------------------

    def delete_dead_urls_from_db(self, results: List[URLCheckResult]) -> int:
        """
        Supprime les URLs mortes directement dans la BDD SQLite.
        Retourne le nombre de suppressions effectuées.
        """
        dead = [r for r in results if r.should_delete]
        if not dead:
            return 0

        conn = self._get_connection()
        count = 0
        try:
            for r in dead:
                conn.execute(
                    "DELETE FROM performer_urls WHERE performer_id = ? AND url = ?",
                    (r.performer_id, r.url)
                )
                # Réindexer les positions restantes pour ce performer
                conn.execute(
                    """
                    UPDATE performer_urls
                    SET position = (
                        SELECT COUNT(*) FROM performer_urls pu2
                        WHERE pu2.performer_id = performer_urls.performer_id
                          AND pu2.position < performer_urls.position
                    )
                    WHERE performer_id = ?
                    """,
                    (r.performer_id,)
                )
                count += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Erreur suppression BDD : {e}") from e
        finally:
            conn.close()

        return count

    def delete_dead_urls_via_graphql(self, results: List[URLCheckResult]) -> Dict:
        """
        Supprime les URLs mortes via l'API GraphQL de Stash.
        Cette méthode est préférée si Stash tourne (mise à jour propre).
        Retourne un dict {performer_id: success/error}.
        """
        # Grouper les URLs mortes par performer
        dead_by_performer: Dict[int, List[URLCheckResult]] = {}
        for r in results:
            if r.should_delete:
                dead_by_performer.setdefault(r.performer_id, []).append(r)

        if not dead_by_performer:
            return {}

        # Pour chaque performer, récupérer ses URLs actuelles et retirer les mortes
        report = {}
        for performer_id, dead_list in dead_by_performer.items():
            dead_urls_set = {r.url for r in dead_list}
            try:
                # 1. Récupérer les URLs actuelles via GraphQL
                current_urls = self._gql_get_performer_urls(performer_id)
                # 2. Filtrer les mortes
                new_urls = [u for u in current_urls if u not in dead_urls_set]
                # 3. Mettre à jour via mutation
                self._gql_update_performer_urls(performer_id, new_urls)
                report[performer_id] = {
                    "status": "ok",
                    "removed": list(dead_urls_set),
                    "remaining": new_urls,
                }
            except Exception as e:
                report[performer_id] = {"status": "error", "error": str(e)}

        return report

    def _gql_headers(self) -> Dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["ApiKey"] = self.api_key
        return h

    def _gql_get_performer_urls(self, performer_id: int) -> List[str]:
        """Récupère la liste des URLs d'un performer via GraphQL."""
        query = """
        query FindPerformer($id: ID!) {
          findPerformer(id: $id) {
            urls
          }
        }
        """
        resp = requests.post(
            f"{self.stash_url}/graphql",
            json={"query": query, "variables": {"id": str(performer_id)}},
            headers=self._gql_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("findPerformer", {}).get("urls", [])

    def _gql_update_performer_urls(self, performer_id: int, urls: List[str]) -> bool:
        """Met à jour les URLs d'un performer via GraphQL."""
        mutation = """
        mutation PerformerUpdate($input: PerformerUpdateInput!) {
          performerUpdate(input: $input) {
            id
            urls
          }
        }
        """
        resp = requests.post(
            f"{self.stash_url}/graphql",
            json={
                "query": mutation,
                "variables": {"input": {"id": str(performer_id), "urls": urls}},
            },
            headers=self._gql_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return True

    def delete_dead_urls(
        self,
        results: List[URLCheckResult],
        mode: str = "auto",  # "auto" | "db_only" | "graphql_only"
        dry_run: bool = False,
    ) -> Dict:
        """
        Supprime les URLs mortes.

        mode:
          "auto"         → essaie GraphQL, fallback sur SQLite direct
          "db_only"      → suppression directe SQLite
          "graphql_only" → suppression via GraphQL uniquement

        dry_run: si True, simule sans modifier la BDD.
        """
        dead = [r for r in results if r.should_delete]
        if not dead:
            return {"deleted": 0, "mode": "none", "dry_run": dry_run}

        if dry_run:
            return {
                "deleted": len(dead),
                "mode": "dry_run",
                "dry_run": True,
                "urls": [r.url for r in dead],
            }

        if mode == "db_only":
            count = self.delete_dead_urls_from_db(results)
            return {"deleted": count, "mode": "db_only", "dry_run": False}

        if mode == "graphql_only":
            report = self.delete_dead_urls_via_graphql(results)
            deleted = sum(1 for v in report.values() if v.get("status") == "ok")
            return {"deleted": deleted, "mode": "graphql", "report": report}

        # Auto : tente GraphQL, fallback SQLite
        try:
            report = self.delete_dead_urls_via_graphql(results)
            deleted = sum(1 for v in report.values() if v.get("status") == "ok")
            return {"deleted": deleted, "mode": "graphql", "report": report}
        except Exception as e:
            print(f"[URLValidator] GraphQL indisponible ({e}), fallback SQLite...")
            count = self.delete_dead_urls_from_db(results)
            return {"deleted": count, "mode": "db_fallback", "dry_run": False}

    # ------------------------------------------------------------------
    # Rapport
    # ------------------------------------------------------------------

    def build_report(self, results: List[URLCheckResult]) -> str:
        """Génère un rapport textuel lisible des résultats."""
        active      = [r for r in results if r.status == URLStatus.ACTIVE]
        dead        = [r for r in results if r.status == URLStatus.DEAD]
        redirect    = [r for r in results if r.status == URLStatus.REDIRECT]
        ambiguous   = [r for r in results if r.status == URLStatus.AMBIGUOUS]
        whitelisted = [r for r in results if r.status == URLStatus.WHITELISTED]
        error       = [r for r in results if r.status == URLStatus.ERROR]

        lines = [
            "=" * 70,
            "RAPPORT DE VALIDATION DES URLs",
            "=" * 70,
            f"  ✅ Actives      : {len(active)}",
            f"  ❌ Mortes       : {len(dead)}   → seront supprimées",
            f"  ↪️  Redirigées   : {len(redirect)}",
            f"  ❓ Ambiguës     : {len(ambiguous)}   (403/429/timeout — conservées)",
            f"  ⏭️  Whitelistées : {len(whitelisted)}  (non testées)",
            f"  💥 Erreurs      : {len(error)}   (réseau — conservées)",
            f"  TOTAL          : {len(results)}",
        ]

        if dead:
            lines += ["", "─" * 70, "❌ URLs MORTES (à supprimer) :"]
            for r in dead:
                lines.append(f"  [{r.performer_name}] {r.url}  [{r.http_code}]")

        if redirect:
            lines += ["", "─" * 70, "↪️  URLs REDIRIGÉES :"]
            for r in redirect:
                lines.append(f"  [{r.performer_name}] {r.url}")
                if r.redirect_to:
                    lines.append(f"    → {r.redirect_to}")

        if ambiguous:
            lines += ["", "─" * 70, "❓ URLs AMBIGUËS (conservées) :"]
            for r in ambiguous:
                lines.append(f"  [{r.performer_name}] {r.url}  [{r.http_code}]")

        if error:
            lines += ["", "─" * 70, "💥 ERREURS RÉSEAU (conservées) :"]
            for r in error:
                lines.append(f"  [{r.performer_name}] {r.url}  — {r.error_msg}")

        lines.append("=" * 70)
        return "\n".join(lines)

    def build_summary_by_performer(self, results: List[URLCheckResult]) -> str:
        """Rapport résumé groupé par performer."""
        by_performer: Dict[int, List[URLCheckResult]] = {}
        for r in results:
            by_performer.setdefault(r.performer_id, []).append(r)

        lines = ["=" * 70, "RÉSUMÉ PAR PERFORMER", "=" * 70]
        for pid, pr in sorted(by_performer.items(), key=lambda x: x[1][0].performer_name):
            name = pr[0].performer_name
            dead_count = sum(1 for r in pr if r.should_delete)
            flag = f"  ← {dead_count} à supprimer" if dead_count else ""
            lines.append(f"\n  [{pid}] {name}{flag}")
            for r in pr:
                lines.append(f"    {r}")
        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


# ===========================================================================
# Widget Tkinter intégrable dans StashMaster
# ===========================================================================

class URLValidatorWidget:
    """
    Widget Tkinter autonome pour valider les URLs depuis StashMaster.
    S'intègre comme fenêtre secondaire (Toplevel).

    Usage :
        from url_validator import URLValidatorWidget
        widget = URLValidatorWidget(parent, db_path="...", stash_url="...")
        widget.show()
    """

    def __init__(self, parent, db_path: str, stash_url: str = DEFAULT_STASH_URL,
                 api_key: str = "", performer_id: Optional[int] = None):
        try:
            import tkinter as tk
            from tkinter import ttk, messagebox, scrolledtext
            self.tk = tk
            self.ttk = ttk
            self.messagebox = messagebox
            self.scrolledtext = scrolledtext
        except ImportError:
            raise ImportError("Tkinter requis pour URLValidatorWidget")

        self.parent = parent
        self.db_path = db_path
        self.stash_url = stash_url
        self.api_key = api_key
        self.performer_id = performer_id
        self.validator = URLValidator(db_path, stash_url, api_key)
        self.results: List[URLCheckResult] = []

    def show(self):
        """Ouvre la fenêtre de validation."""
        tk = self.tk
        ttk = self.ttk

        self.win = tk.Toplevel(self.parent)
        self.win.title("🔗 Validation des URLs de Performers")
        self.win.geometry("900x650")
        self.win.grab_set()

        # ── Header ──
        hdr = tk.Frame(self.win, bg="#1a1a2e", pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔗 Validation des URLs", font=("Arial", 13, "bold"),
                 bg="#1a1a2e", fg="white").pack()

        # Infos BDD
        try:
            nb_perf, nb_urls = self.validator.get_performer_count()
            info_txt = f"{nb_perf} performers · {nb_urls} URLs dans la BDD"
        except Exception as e:
            info_txt = f"Erreur lecture BDD : {e}"
        tk.Label(hdr, text=info_txt, font=("Arial", 9), bg="#1a1a2e", fg="#aaa").pack()

        # ── Options ──
        opt_frame = tk.LabelFrame(self.win, text="Options", padx=8, pady=6)
        opt_frame.pack(fill="x", padx=10, pady=5)

        # Timeout
        tk.Label(opt_frame, text="Timeout (s):").grid(row=0, column=0, sticky="w")
        self.timeout_var = tk.IntVar(value=DEFAULT_TIMEOUT)
        ttk.Spinbox(opt_frame, from_=3, to=30, textvariable=self.timeout_var, width=5
                    ).grid(row=0, column=1, padx=4)

        # Workers
        tk.Label(opt_frame, text="Threads:").grid(row=0, column=2, padx=(12,0), sticky="w")
        self.workers_var = tk.IntVar(value=DEFAULT_MAX_WORKERS)
        ttk.Spinbox(opt_frame, from_=1, to=20, textvariable=self.workers_var, width=5
                    ).grid(row=0, column=3, padx=4)

        # Dry run
        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_frame, text="Dry run (simuler sans supprimer)",
                        variable=self.dry_run_var).grid(row=0, column=4, padx=12)

        # ── Barre de progression ──
        prog_frame = tk.Frame(self.win)
        prog_frame.pack(fill="x", padx=10, pady=3)
        self.progress_label = tk.Label(prog_frame, text="En attente...", anchor="w")
        self.progress_label.pack(side="left", fill="x", expand=True)
        self.progress_bar = ttk.Progressbar(self.win, mode="determinate")
        self.progress_bar.pack(fill="x", padx=10, pady=2)

        # ── Zone de résultats (tableau) ──
        cols_frame = tk.Frame(self.win)
        cols_frame.pack(fill="both", expand=True, padx=10, pady=4)

        columns = ("status", "performer", "url", "code", "ms")
        self.tree = ttk.Treeview(cols_frame, columns=columns, show="headings", height=18)
        self.tree.heading("status",    text="État")
        self.tree.heading("performer", text="Performer")
        self.tree.heading("url",       text="URL")
        self.tree.heading("code",      text="HTTP")
        self.tree.heading("ms",        text="ms")
        self.tree.column("status",    width=90,  anchor="center")
        self.tree.column("performer", width=140, anchor="w")
        self.tree.column("url",       width=440, anchor="w")
        self.tree.column("code",      width=55,  anchor="center")
        self.tree.column("ms",        width=55,  anchor="center")

        # Tags de couleurs
        self.tree.tag_configure("active",      foreground="#2e7d32")
        self.tree.tag_configure("dead",        foreground="#c62828", background="#fff3f3")
        self.tree.tag_configure("redirect",    foreground="#e65100")
        self.tree.tag_configure("ambiguous",   foreground="#5d4037")
        self.tree.tag_configure("whitelisted", foreground="#1565c0")
        self.tree.tag_configure("error",       foreground="#6a1b9a")

        scroll_y = ttk.Scrollbar(cols_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(self.win, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_x.pack(fill="x", padx=10)

        # ── Boutons ──
        btn_frame = tk.Frame(self.win, pady=6)
        btn_frame.pack(fill="x", padx=10)

        self.btn_validate = ttk.Button(btn_frame, text="▶ Lancer la validation",
                                       command=self._start_validation)
        self.btn_validate.pack(side="left", padx=4)

        self.btn_delete = ttk.Button(btn_frame, text="🗑 Supprimer les URLs mortes",
                                     command=self._delete_dead, state="disabled")
        self.btn_delete.pack(side="left", padx=4)

        self.btn_report = ttk.Button(btn_frame, text="📋 Rapport complet",
                                     command=self._show_report, state="disabled")
        self.btn_report.pack(side="left", padx=4)

        self.dead_label = tk.Label(btn_frame, text="", fg="#c62828", font=("Arial", 9, "bold"))
        self.dead_label.pack(side="right", padx=8)

    def _start_validation(self):
        """Lance la validation dans un thread séparé."""
        import threading

        self.btn_validate.config(state="disabled")
        self.btn_delete.config(state="disabled")
        self.btn_report.config(state="disabled")
        self.results = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.progress_bar["value"] = 0
        self.dead_label.config(text="")

        self.validator.timeout = self.timeout_var.get()
        self.validator.max_workers = self.workers_var.get()

        def run():
            try:
                entries = self.validator.get_all_performer_urls(self.performer_id)
                total = len(entries)
                self.progress_bar["maximum"] = max(total, 1)

                def on_progress(current, total, result):
                    self.results.append(result)
                    self.win.after(0, self._add_tree_row, result)
                    self.win.after(0, self._update_progress, current, total)

                self.validator.validate_urls(entries, progress_callback=on_progress)

            except Exception as e:
                self.win.after(0, lambda: self.messagebox.showerror(
                    "Erreur", f"Erreur de validation :\n{e}"))
            finally:
                self.win.after(0, self._validation_done)

        threading.Thread(target=run, daemon=True).start()

    def _add_tree_row(self, r: URLCheckResult):
        tag = r.status.value
        label = {
            URLStatus.ACTIVE:      "✅ Active",
            URLStatus.DEAD:        "❌ Morte",
            URLStatus.REDIRECT:    "↪️  Redirect",
            URLStatus.AMBIGUOUS:   "❓ Ambiguë",
            URLStatus.WHITELISTED: "⏭️  Whitelist",
            URLStatus.ERROR:       "💥 Erreur",
        }.get(r.status, "?")

        self.tree.insert("", "end",
                         values=(label, r.performer_name, r.url,
                                 r.http_code or "—", r.check_duration_ms),
                         tags=(tag,))

    def _update_progress(self, current, total):
        self.progress_bar["value"] = current
        self.progress_label.config(text=f"Vérification {current}/{total}…")

    def _validation_done(self):
        dead_count = sum(1 for r in self.results if r.should_delete)
        self.progress_label.config(text=f"✅ Terminé — {len(self.results)} URLs vérifiées")
        self.btn_validate.config(state="normal")
        self.btn_report.config(state="normal")
        if dead_count:
            self.btn_delete.config(state="normal")
            self.dead_label.config(text=f"{dead_count} URL(s) morte(s) à supprimer")

    def _delete_dead(self):
        dead = [r for r in self.results if r.should_delete]
        if not dead:
            self.messagebox.showinfo("Info", "Aucune URL morte à supprimer.")
            return

        dry = self.dry_run_var.get()
        msg = (
            f"{'[DRY RUN] ' if dry else ''}"
            f"Supprimer {len(dead)} URL(s) morte(s) ?\n\n"
            + "\n".join(f"  • [{r.performer_name}] {r.url}" for r in dead[:15])
            + (f"\n  ... et {len(dead)-15} autres" if len(dead) > 15 else "")
        )
        if not self.messagebox.askyesno("Confirmation", msg):
            return

        try:
            result = self.validator.delete_dead_urls(self.results, dry_run=dry)
            mode = "GraphQL" if "graphql" in result.get("mode","") else "SQLite"
            msg_ok = (
                f"{'[DRY RUN] ' if dry else ''}"
                f"{result['deleted']} URL(s) supprimée(s) via {mode}."
            )
            self.messagebox.showinfo("Succès", msg_ok)
            self.btn_delete.config(state="disabled")
            self.dead_label.config(text="")
        except Exception as e:
            self.messagebox.showerror("Erreur", f"Erreur lors de la suppression :\n{e}")

    def _show_report(self):
        """Affiche le rapport complet dans une fenêtre."""
        tk = self.tk
        report = self.validator.build_report(self.results)

        win = tk.Toplevel(self.win)
        win.title("📋 Rapport complet")
        win.geometry("800x550")

        txt = self.scrolledtext.ScrolledText(win, font=("Courier New", 9), wrap="none")
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", report)
        txt.config(state="disabled")

        ttk = self.ttk
        ttk.Button(win, text="Fermer", command=win.destroy).pack(pady=4)


# ===========================================================================
# CLI (lancement direct)
# ===========================================================================

def _cli():
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Valide les URLs de performers dans la BDD Stash"
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH,
                        help="Chemin vers stash-go.sqlite")
    parser.add_argument("--stash-url", default=DEFAULT_STASH_URL,
                        help="URL de l'API Stash")
    parser.add_argument("--api-key", default="",
                        help="Clé API Stash")
    parser.add_argument("--performer-id", type=int, default=None,
                        help="Valider seulement ce performer (ID)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="Timeout HTTP en secondes")
    parser.add_argument("--workers", type=int, default=DEFAULT_MAX_WORKERS,
                        help="Nombre de threads parallèles")
    parser.add_argument("--auto-delete", action="store_true",
                        help="Supprimer automatiquement sans confirmation")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simuler sans modifier la BDD")
    parser.add_argument("--mode", choices=["auto","db_only","graphql_only"],
                        default="auto", help="Mode de suppression")
    args = parser.parse_args()

    validator = URLValidator(
        db_path=args.db,
        stash_url=args.stash_url,
        api_key=args.api_key,
        timeout=args.timeout,
        max_workers=args.workers,
    )

    # Infos
    try:
        nb_perf, nb_urls = validator.get_performer_count()
        print(f"BDD : {args.db}")
        print(f"Performers avec URLs : {nb_perf} | Total URLs : {nb_urls}")
    except Exception as e:
        print(f"❌ Impossible d'ouvrir la BDD : {e}")
        sys.exit(1)

    # Validation
    done_count = [0]
    def progress(current, total, result):
        done_count[0] = current
        print(f"  [{current:>4}/{total}] {result}", flush=True)

    print(f"\n{'─'*70}")
    print(f"Validation en cours ({args.workers} threads, timeout={args.timeout}s)…")
    print(f"{'─'*70}")

    results = validator.validate_all(
        performer_id=args.performer_id,
        progress_callback=progress,
    )

    # Rapport
    print("\n")
    print(validator.build_report(results))

    # Suppression
    dead = [r for r in results if r.should_delete]
    if not dead:
        print("\n✅ Aucune URL morte — base de données propre !")
        return

    if args.auto_delete or args.dry_run:
        result = validator.delete_dead_urls(results, mode=args.mode, dry_run=args.dry_run)
        if args.dry_run:
            print(f"\n[DRY RUN] {result['deleted']} URL(s) auraient été supprimées.")
        else:
            print(f"\n✅ {result['deleted']} URL(s) supprimées (mode: {result['mode']}).")
    else:
        ans = input(f"\nSupprimer les {len(dead)} URLs mortes ? [o/N] ").strip().lower()
        if ans in ("o", "oui", "y", "yes"):
            result = validator.delete_dead_urls(results, mode=args.mode)
            print(f"✅ {result['deleted']} URL(s) supprimées (mode: {result['mode']}).")
        else:
            print("Annulé — aucune modification.")


if __name__ == "__main__":
    _cli()
