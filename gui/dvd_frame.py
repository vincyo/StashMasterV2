#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DVDFrame - Interface de gestion des DVDs / Groupes
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from typing import Dict, List, Optional

class DVDFrame(ttk.Frame):
    def __init__(self, parent, dvd_id: Optional[str] = None, on_exit_to_selector=None):
        super().__init__(parent)
        self.dvd_id = dvd_id
        self.on_exit_to_selector = on_exit_to_selector
        
        # Services
        from services.config_manager import ConfigManager
        from services.database import StashDatabase
        from services.scrapers import ScraperOrchestrator
        
        config = ConfigManager()
        self.db = StashDatabase(config.get('database_path'))
        self.scraper = ScraperOrchestrator()
        
        # UI Attributes for linting
        self.notebook: Optional[ttk.Notebook] = None
        self.tab_metadata: Optional[ttk.Frame] = None
        self.urls_text: Optional[scrolledtext.ScrolledText] = None
        
        self.stash_data: Dict = {}
        self.field_vars: Dict[str, Dict[str, tk.Variable]] = {}
        self.fields = [
            ('name', 'Titre'),
            ('date', 'Date'),
            ('studio', 'Studio'),
            ('director', 'Réalisateur'),
            ('duration', 'Durée'),
            ('rating', 'Note'),
            ('tags', 'Tags'),
        ]
        
        self._setup_ttk_styles()
        self._create_widgets()
        if dvd_id:
            self._load_from_stash()

    def _setup_ttk_styles(self):
        style = ttk.Style()
        style.map('Valid.TCombobox', fieldbackground=[('readonly', '#d4edda'), ('!disabled', '#d4edda')])
        style.map('Invalid.TCombobox', fieldbackground=[('readonly', '#f8d7da'), ('!disabled', '#f8d7da')])
        style.map('Empty.TCombobox', fieldbackground=[('readonly', '#fff3cd'), ('!disabled', '#fff3cd')])
        style.map('Normal.TCombobox', fieldbackground=[('readonly', 'white'), ('!disabled', 'white')])

    def _create_widgets(self):
        # Initialiser les variables de champ
        for field, label in self.fields:
            self.field_vars[field] = {
                'check': tk.BooleanVar(value=True),
                'stash': tk.StringVar(),
                'main': tk.StringVar(),
                'source': tk.StringVar()
            }

        # Onglets
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tab_metadata = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_metadata, text="📀 Métadonnées")
        
        self._setup_metadata_tab()
        
        # Toolbar
        toolbar = ttk.Frame(self, padding=10)
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(toolbar, text="💾 Sauvegarder dans Stash", command=self._save_to_stash).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="🔍 Tout Scraper", command=self._scrape_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="← Retour sélection", command=self._exit_to_selector).pack(side=tk.LEFT, padx=5)

    def _setup_metadata_tab(self):
        if not self.tab_metadata: return
        container = ttk.Frame(self.tab_metadata, padding=10)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Headers
        headers = ["", "Champ", "Valeur Stash", "Modification", "Résultat Scrapers"]
        for i, h in enumerate(headers):
            lbl = ttk.Label(container, text=h, font=('Segoe UI', 9, 'bold'))
            lbl.grid(row=0, column=i, padx=5, pady=5, sticky="w")
        
        # Lignes de champs
        for i, (field, label) in enumerate(self.fields, start=1):
            # Checkbox
            ttk.Checkbutton(container, variable=self.field_vars[field]['check']).grid(row=i, column=0, padx=5)
            # Label
            ttk.Label(container, text=label).grid(row=i, column=1, padx=5, sticky="w")
            # Stash Value (Read-only)
            ent_stash = ttk.Entry(container, textvariable=self.field_vars[field]['stash'], state='readonly', width=30)
            ent_stash.grid(row=i, column=2, padx=5, pady=2, sticky="w")
            # Main Input (Validation)
            ent_main = ttk.Combobox(container, textvariable=self.field_vars[field]['main'], width=40)
            ent_main.grid(row=i, column=3, padx=5, pady=2, sticky="we")
            # Source Result (Read-only)
            ent_source = ttk.Entry(container, textvariable=self.field_vars[field]['source'], state='readonly', width=30)
            ent_source.grid(row=i, column=4, padx=5, pady=2, sticky="we")
            
            self.field_vars[field]['widget'] = ent_main
            
            # Monitoring de changement pour validation visuelle
            self.field_vars[field]['main'].trace_add("write", lambda *args, f=field: self._validate_field(f))

        # URL Area
        url_frame = ttk.LabelFrame(container, text="URLs Sources (IAFD, AdultEmpire, Data18...)", padding=10)
        url_frame.grid(row=len(self.fields)+1, column=0, columnspan=5, sticky="we", pady=15)
        self.urls_text = scrolledtext.ScrolledText(url_frame, height=4, wrap=tk.WORD)
        self.urls_text.pack(fill=tk.X, expand=True)

        container.columnconfigure(3, weight=10)
        container.columnconfigure(2, weight=5)
        container.columnconfigure(4, weight=5)

    def _load_from_stash(self):
        if not self.dvd_id: return
        data = self.db.get_group_metadata(self.dvd_id)
        if data:
            self.stash_data = data
            for field, _ in self.fields:
                val = str(data.get(field, '')) if data.get(field) is not None else ''
                self.field_vars[field]['stash'].set(val)
                self.field_vars[field]['main'].set(val)
                self._validate_field(field)

    def _validate_field(self, field):
        f = self.field_vars[field]
        main_val = f['main'].get().strip()
        stash_val = f['stash'].get().strip()
        is_checked = f['check'].get()
        combo = f.get('widget')
        
        if not is_checked:
            color = "white"
        elif not main_val:
            color = "#fff3cd"
        elif main_val.lower() == stash_val.lower():
            color = "#d4edda"
        else:
            color = "#f8d7da"

        if isinstance(combo, ttk.Combobox):
            style_map = {
                "white": "Normal.TCombobox",
                "#fff3cd": "Empty.TCombobox",
                "#d4edda": "Valid.TCombobox",
                "#f8d7da": "Invalid.TCombobox"
            }
            combo.configure(style=style_map.get(color, "Normal.TCombobox"))

    def _scrape_all(self):
        if not self.urls_text: return
        urls = self.urls_text.get('1.0', tk.END).strip().split('\n')
        urls = [u.strip() for u in urls if u.strip()]
        if not urls:
            messagebox.showwarning("Scraping", "Veuillez entrer au moins une URL.")
            return

        def run_scrape():
            results = self.scraper.scrape_dvd_multi(urls)
            if not results:
                self.after(0, lambda: messagebox.showinfo("Scraping", "Aucun résultat trouvé."))
                return
            
            from services.scrapers import DataMerger
            confirmed, _ = DataMerger.merge_data(results)
            
            merged_data = {k: v['value'] for k, v in confirmed.items()}
            self.after(0, lambda: self._apply_results(merged_data))

        threading.Thread(target=run_scrape, daemon=True).start()

    def _apply_results(self, data):
        for field, _ in self.fields:
            if field in data and data[field]:
                val = str(data[field])
                self.field_vars[field]['source'].set(val)
                # Utiliser .get() sur BooleanVar pour vérifier si coché
                if self.field_vars[field]['check'].get():
                    self.field_vars[field]['main'].set(val)
                
                # Update Combobox values
                stash_val = self.field_vars[field]['stash'].get().strip()
                all_vals = sorted(list(set([v for v in [stash_val, val] if v])))
                widget = self.field_vars[field].get('widget')
                if isinstance(widget, ttk.Combobox):
                    widget['values'] = all_vals
        
        # Injection des URLs de scènes (Spécifique Data18)
        if 'scenes' in data and data['scenes'] and self.dvd_id:
            self._inject_scene_urls(data['scenes'])

    def _inject_scene_urls(self, scraped_scenes: List[Dict]):
        """Associe les URLs Data18 aux scènes Stash du DVD"""
        stash_scenes = self.db.get_scenes_for_group(self.dvd_id)
        if not stash_scenes: return
        
        count: int = 0
        for s_scene in scraped_scenes:
            scraped_title = s_scene.get('title', '').lower()
            scraped_url = s_scene.get('url')
            if not scraped_url: continue
            
            # Recherche de match par titre (très basique pour l'instant)
            for db_scene in stash_scenes:
                db_title = db_scene.get('title', '').lower()
                # Match si le titre est contenu l'un dans l'autre (grossier mais souvent efficace sur Data18)
                if db_title and scraped_title and (db_title in scraped_title or scraped_title in db_title):
                    if self.db.add_scene_url(db_scene['id'], scraped_url):
                        count += 1
                    break
        
        if count > 0:
            print(f"Injecté {count} URLs de scènes depuis Data18.")
            # Optionnel: Notification discrète

    def _exit_to_selector(self):
        if self.on_exit_to_selector:
            self.on_exit_to_selector()

    def _save_to_stash(self):
        if not self.dvd_id: return
        updates = {f: var_dict['main'].get() for f, var_dict in self.field_vars.items()}
        if self.db.save_group_metadata(self.dvd_id, updates):
            messagebox.showinfo("Sauvegarde", "DVD mis à jour avec succès.")
            self._load_from_stash()
        else:
            messagebox.showerror("Sauvegarde", "Erreur lors de la sauvegarde.")
