import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import threading

from gui.performer_base import PerformerBaseFrame
from gui.phase1_conflict_dialog import Phase1ConflictDialog


class PerformerPhase1Frame(PerformerBaseFrame):
    def __init__(self, parent, controller, stash_id):
        super().__init__(parent, controller, stash_id)
        
        # Configuration des champs Phase 1
        self.fields_list = [
            "Name", "Aliases", "Birthdate", "Deathdate", "Country", "Ethnicity",
            "Hair Color", "Eye Color", "Height", "Weight", "Measurements", "Fake Tits", "Career Length"
        ]
        
        self.db_mapping = {
            "Name": "name",
            "Aliases": "aliases",
            "Birthdate": "birthdate",
            "Deathdate": "death_date",
            "Country": "country",
            "Ethnicity": "ethnicity",
            "Hair Color": "hair_color",
            "Eye Color": "eye_color",
            "Height": "height",
            "Weight": "weight",
            "Measurements": "measurements",
            "Fake Tits": "fake_tits",
            "Career Length": "career_length"
        }
        
        self.create_ui()
        self.load_data()

    def process_and_goto_phase2(self):
        """
        Workflow Phase 1 : Scrape, compare, et prépare les données pour la Phase 2.
        AUCUNE injection en base de données n'est faite ici.
        """
        checked_fields = [f for f, var in self.field_checkboxes.items() if var.get()]
        if not checked_fields:
            self.controller.goto_phase2({}) # Passe un dict vide si pas de scraping
            return
        
        try:
            from services.db import PerformerDB
            db = PerformerDB()
            db_data = db.get_performer_by_id(self.stash_id)
            db.close()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lire la DB: {e}")
            return

        if not db_data:
            messagebox.showerror("Erreur", "Performer non trouvé dans la base.")
            return

        performer_name = db_data["name"]
        known_urls = db_data.get("urls", [])

        self.progress_frame.pack(fill=tk.X, padx=10, pady=2, after=list(self.fields.values())[-1].master)
        self.progress_bar.start(10)
        self.progress_label.config(text=f"Scraping {len(checked_fields)} champs pour {performer_name}...")

        def _do_scraping():
            try:
                from services.phase2_scraper import Phase2ScraperService
                from services.phase1_merger import Phase1Merger

                scraper = Phase2ScraperService()
                results = scraper.scrape(performer_name, known_urls=known_urls,
                                         progress_callback=lambda s, m: self.after(0, self.progress_label.config, {'text': f"[{s}] {m}"}))
                
                # Nettoyage des données scrapées AVANT le merge
                for res in results:
                    if res.get("hair_color"):
                        # Déduplication et nettoyage (ex: "Blonde, Blonde" -> "Blonde")
                        parts = [p.strip() for p in res["hair_color"].replace('/', ',').split(',') if p.strip()]
                        seen = set()
                        unique = []
                        for p in parts:
                            p_cap = p.capitalize()
                            if p_cap not in seen:
                                seen.add(p_cap)
                                unique.append(p_cap)
                        res["hair_color"] = ", ".join(unique)

                merger = Phase1Merger()
                merge_results = merger.merge(db_data, results, checked_fields)
                
                # Construire l'affichage pour TOUS les champs cochés
                display_results = {}
                for field in checked_fields:
                    # Le merger renvoie les résultats indexés par le nom du champ (ex: "Name")
                    if field in merge_results:
                        display_results[field] = merge_results[field]
                    else:
                        # Si le merger n'a rien renvoyé, on force l'affichage en mode "empty"
                        # pour confirmer à l'utilisateur que le champ a été traité mais sans résultat.
                        db_key = self.db_mapping.get(field)
                        current_val = db_data.get(db_key) if db_key else None
                        display_results[field] = {'status': 'empty', 'db_value': current_val, 'scraped_values': {}, 'suggestion': None}

                self.after(0, self._hide_progress)

                phase1_updates = {}
                if display_results:
                    dialog = Phase1ConflictDialog(self.master, performer_name, display_results, self.db_mapping)
                    if dialog.result is not None:
                        # Le dialogue retourne les valeurs à mettre à jour
                        for field_name, resolved_value in dialog.result.items():
                            db_key = self.db_mapping.get(field_name)
                            if db_key:
                                # Spécial pour les alias, on veut une liste
                                if db_key == 'aliases' and isinstance(resolved_value, str):
                                     phase1_updates[db_key] = [a.strip() for a in resolved_value.split(',') if a.strip()]
                                elif db_key == 'hair_color' and isinstance(resolved_value, str):
                                     # Nettoyage et déduplication pour la couleur de cheveux
                                     parts = [p.strip() for p in resolved_value.replace('/', ',').split(',') if p.strip()]
                                     seen = set()
                                     unique_parts = []
                                     for p in parts:
                                         if p.lower() not in seen:
                                             seen.add(p.lower())
                                             unique_parts.append(p)
                                     phase1_updates[db_key] = ", ".join(unique_parts)
                                else:
                                     phase1_updates[db_key] = resolved_value
                        
                        messagebox.showinfo("Phase 1 Traitée", f"{len(phase1_updates)} modifications de la Phase 1 ont été préparées pour la validation finale.")
                    else:
                        # L'utilisateur a annulé, on ne passe aucune modification
                        messagebox.showinfo("Annulé", "Fusion des données annulée. Passage en phase 2 sans appliquer les changements de la phase 1.")
                else:
                    messagebox.showinfo("Phase 1 Complète", "Aucun conflit ou nouvelle donnée à traiter. Passage en Phase 2.")
                
                # Passer en Phase 2 avec les données résolues de la phase 1
                self.after(0, lambda: self.controller.goto_phase2(phase1_updates))

            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Erreur Phase 1", f"Une erreur est survenue : {err_msg}"))
            finally:
                self.after(0, self._hide_progress)

        threading.Thread(target=_do_scraping, daemon=True).start()

    def _hide_progress(self):
        self.progress_bar.stop()
        self.progress_frame.pack_forget()

    def create_ui(self):
        # Header + Boutons spécifiques
        buttons = [
            ("Tout sélectionner", self.select_all_fields),
            ("Sélectionner vides", self.select_empty_fields),
            ("Suivant / Traiter", self.process_and_goto_phase2),
            ("Retour", self.controller.return_to_menu),
        ]
        self.create_header("Phase 1 : Métadonnées usuelles", buttons)

        # Barre de progression (cachée par défaut)
        self.progress_frame = ttk.Frame(self)
        self.progress_label = ttk.Label(self.progress_frame, text="",
                                        font=("Segoe UI", 9, "italic"))
        self.progress_label.pack(side=tk.LEFT, padx=10)
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="indeterminate", length=200)
        self.progress_bar.pack(side=tk.LEFT, padx=5)

        # Zone des champs
        f = ttk.Frame(self)
        f.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Configuration de la grille pour l'extension horizontale
        f.grid_columnconfigure(0, weight=0)  # Checkbox
        f.grid_columnconfigure(1, weight=0)  # Label
        f.grid_columnconfigure(2, weight=1)  # Entry (prend tout l'espace restant)

        for i, field in enumerate(self.fields_list):
            row = i
            # Checkbox (décochée par défaut)
            var = tk.BooleanVar(value=False)
            self.field_checkboxes[field] = var
            checkbox = ttk.Checkbutton(f, variable=var, text="")
            checkbox.grid(row=row, column=0, sticky=tk.W, padx=(5, 0), pady=2)
            
            # Label
            ttk.Label(f, text=f"{field}:").grid(row=row, column=1, sticky=tk.NW, padx=5, pady=2)
            
            # Entry Widget
            entry = ttk.Entry(f, width=60)
            entry.grid(row=row, column=2, sticky=tk.EW, padx=5, pady=2)
            self.fields[field] = entry
