"""
PerformerPhase2Frame — Orchestre le flux 3-fenêtres Bio IA.

Flux :
  1. Scraping Phase 2 (background thread)
  2. GUI 1 : DataReviewWindow   — révision données (sauf bio)
  3. GUI 2 : BioStudioWindow    — génération bio Gemini / Ollama
  4. GUI 3 : ValidationWindow   — validation + injection Stash

Toutes les fenêtres s'ouvrent en plein écran.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import copy

from gui.performer_base import PerformerBaseFrame


class PerformerPhase2Frame(PerformerBaseFrame):
    def __init__(self, parent, controller, stash_id, phase1_data: dict):
        self.phase1_data  = phase1_data
        self.phase2_data  = {}

        super().__init__(parent, controller, stash_id)

        self.fields_list = [
            "Trivia", "Awards", "Tattoos", "Piercings", "Tags", "URLs", "Details"
        ]
        self.db_mapping = {
            "Trivia":    "trivia",
            "Awards":    "awards",
            "Tattoos":   "tattoos",
            "Piercings": "piercings",
            "Tags":      "tags",
            "URLs":      "urls",
            "Details":   "details",
        }

        self._scraped_results = None
        self._merged_data     = None
        self._db_data         = None
        self._stash_context   = None

        self.create_ui()
        self.load_data()

    # ── Chargement DB ──────────────────────────────────────────────────────────

    def load_data(self):
        super().load_data()
        if self.phase1_data:
            for db_key, value in self.phase1_data.items():
                field_name = next(
                    (n for n, k in self.db_mapping.items() if k == db_key), None
                )
                if field_name:
                    display = (", ".join(value) if isinstance(value, list)
                               else str(value) if value else "")
                    self._update_field_display(field_name, display)

    # ── UI ─────────────────────────────────────────────────────────────────────

    def create_ui(self):
        buttons = [
            ("🔎 Scraper & Lancer le flux Bio IA", self.run_full_flow),
            ("Tout sélectionner",  self.select_all_fields),
            ("Sélectionner vides", self.select_empty_fields),
            ("Retour Phase 1",     self.controller.goto_phase1),
        ]
        self.create_header("Phase 2 : Champs Avancés + Bio IA", buttons)

        # Barre de progression (scraping)
        self.progress_frame = ttk.Frame(self)
        self.progress_label = ttk.Label(
            self.progress_frame, text="", font=("Segoe UI", 9, "italic")
        )
        self.progress_label.pack(side=tk.LEFT, padx=10)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, mode="indeterminate", length=200
        )
        self.progress_bar.pack(side=tk.LEFT, padx=5)

        # Grille des champs (lecture seule — affichage des données actuelles)
        f = ttk.Frame(self)
        f.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        f.grid_columnconfigure(2, weight=1)

        for i, field in enumerate(self.fields_list):
            var = tk.BooleanVar(value=True)
            self.field_checkboxes[field] = var
            ttk.Checkbutton(f, variable=var, text="").grid(
                row=i, column=0, sticky=tk.W, padx=(5, 0), pady=5
            )
            ttk.Label(f, text=f"{field}:").grid(
                row=i, column=1, sticky=tk.NW, padx=5, pady=5
            )

            height = 3
            if field == "Details": height = 8
            if field in ("URLs", "Awards"): height = 5

            entry = tk.Text(f, width=60, height=height, font=("Segoe UI", 10))
            entry.grid(row=i, column=2, sticky=tk.EW, padx=5, pady=5)
            self.fields[field] = entry

    # ── Flux principal ─────────────────────────────────────────────────────────

    def run_full_flow(self):
        """
        Point d'entrée : scrape les sources puis ouvre les 3 GUIs en séquence.
        """
        # Charger DB
        try:
            from services.db import PerformerDB
            db = PerformerDB()
            self._db_data      = db.get_performer_by_id(self.stash_id)
            self._stash_context = db.get_performer_context(self.stash_id)
            db.close()
        except Exception as e:
            messagebox.showerror("Erreur DB", f"Impossible de lire la base : {e}")
            return

        if not self._db_data:
            messagebox.showerror("Erreur", "Performer introuvable dans la base.")
            return

        # Données à jour (DB + Phase 1)
        self._combined = copy.deepcopy(self._db_data)
        self._combined.update(self.phase1_data)

        performer_name = self._combined.get("name", "")
        known_urls     = self._combined.get("urls", [])

        # Afficher barre progression
        self._show_progress(f"Scraping en cours pour {performer_name}…")

        def _do_scraping():
            try:
                from services.phase2_scraper import Phase2ScraperService
                from services.phase2_merger  import Phase2Merger

                scraper = Phase2ScraperService()
                results = scraper.scrape(
                    performer_name,
                    known_urls=known_urls,
                    progress_callback=lambda s, m: self.after(
                        0, self.progress_label.config, {"text": f"[{s}] {m}"}
                    ),
                )
                self._scraped_results = results

                merger = Phase2Merger()
                self._merged_data = merger.merge(self._combined, results)

                self.after(0, self._on_scraping_done)

            except Exception as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror("Erreur scraping", err))
                self.after(0, self._hide_progress)

        threading.Thread(target=_do_scraping, daemon=True).start()

    def _on_scraping_done(self):
        self._hide_progress()
        checked_fields = [f for f, v in self.field_checkboxes.items() if v.get()]
        self._open_gui1(checked_fields)

    # ── GUI 1 : DataReviewWindow ───────────────────────────────────────────────

    def _open_gui1(self, checked_fields):
        from gui.data_review_window import DataReviewWindow

        win = DataReviewWindow(
            parent          = self.winfo_toplevel(),
            db_data         = self._combined,
            stash_ctx       = self._stash_context,
            merged_data     = self._merged_data,
            scraped_results = self._scraped_results or [],
            checked_fields  = checked_fields,
        )

        if win.result is None:
            # Annulé
            return

        # Appliquer les sélections dans les champs UI de phase 2
        self._apply_review_result(win.result)
        self._open_gui2(checked_fields, win.result)

    # ── GUI 2 : BioStudioWindow ────────────────────────────────────────────────

    def _open_gui2(self, checked_fields, review_result):
        from gui.bio_studio_window import BioStudioWindow

        win = BioStudioWindow(
            parent          = self.winfo_toplevel(),
            db_data         = self._combined,
            stash_ctx       = self._stash_context,
            merged_data     = self._merged_data,
            scraped_results = self._scraped_results or [],
            checked_fields  = checked_fields,
            review_result   = review_result,
        )

        if win.result is None:
            # Retour ou annuler : retourner à GUI 1
            self._open_gui1(checked_fields)
            return

        self._open_gui3(review_result, win.result)

    # ── GUI 3 : ValidationWindow ───────────────────────────────────────────────

    def _open_gui3(self, review_result, bio_result):
        from gui.validation_window import ValidationWindow

        win = ValidationWindow(
            parent        = self.winfo_toplevel(),
            db_data       = self._combined,
            stash_ctx     = self._stash_context,
            review_result = review_result,
            bio_result    = bio_result,
        )

        if win.result == "injected":
            messagebox.showinfo(
                "✅ Succès",
                "Les données ont été injectées dans Stash avec succès.\n"
                "Vous pouvez continuer ou retourner au menu.",
            )
            # Rafraîchir l'affichage Phase 2 avec les nouvelles données
            self._refresh_display(review_result, bio_result)

        elif win.result is None:
            # Retour à GUI 2 → GUI 1 est perdue (simplification)
            # On relance seulement GUI 2 avec le même review_result
            checked = [f for f, v in self.field_checkboxes.items() if v.get()]
            self._open_gui2(checked, review_result)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _apply_review_result(self, result: dict):
        """Met à jour les widgets de la phase 2 avec les sélections GUI 1."""
        if not result:
            return

        mapping = {
            "trivia":    ("Trivia",   lambda x: x),
            "awards":    ("Awards",   lambda x: "\n".join(x) if x else ""),
            "tattoos":   ("Tattoos",  self._fmt_body_art),
            "piercings": ("Piercings",self._fmt_body_art),
            "tags":      ("Tags",     lambda x: ", ".join(x) if x else ""),
            "urls":      ("URLs",     lambda x: "\n".join(x.values()) if x else ""),
        }
        for key, (field, fmt) in mapping.items():
            val = result.get(key)
            if val is not None:
                self._update_field_display(field, fmt(val))
                self.phase2_data[key] = val

    def _fmt_body_art(self, items):
        if not items:
            return ""
        def fmt(it):
            pos  = it.get("position", "")
            desc = it.get("description", "")
            return f"{pos} ({desc})" if desc else pos
        return "; ".join(fmt(i) for i in items)

    def _refresh_display(self, review_result: dict, bio_result: dict):
        """Rafraîchit les champs après injection réussie."""
        self._apply_review_result(review_result)
        bio = (bio_result or {}).get("bio", "")
        if bio:
            self._update_field_display("Details", bio)
            self.phase2_data["details"] = bio

    def _show_progress(self, message):
        self.progress_label.config(text=message)
        self.progress_frame.pack(fill=tk.X, padx=10, pady=2)
        self.progress_bar.start(10)

    def _hide_progress(self):
        self.progress_bar.stop()
        self.progress_frame.pack_forget()

    def _update_field_display(self, field_name: str, value: str):
        entry = self.fields.get(field_name)
        if entry and isinstance(entry, tk.Text):
            entry.config(state=tk.NORMAL)
            entry.delete("1.0", tk.END)
            if value:
                entry.insert("1.0", value)
            self.field_checkboxes.get(field_name, tk.BooleanVar()).set(bool(value))
