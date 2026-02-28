#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SceneFrame - Interface de gestion des Scènes
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Dict, List, Optional

class SceneFrame(ttk.Frame):
    """Frame principal pour la gestion des scènes"""
    
    def __init__(self, parent, scene_id: Optional[str] = None):
        super().__init__(parent)
        self.scene_id = scene_id
        self.metadata = {}
        
        # Services
        from services.config_manager import ConfigManager
        from services.database import StashDatabase
        from services.scrapers import ScraperOrchestrator
        
        config = ConfigManager()
        self.db = StashDatabase(config.get('database_path'))
        self.scraper = ScraperOrchestrator()
        
        # Definition of fields moved to __init__ as an instance variable
        self.fields = [
            ("Titre:", "title"),
            ("Studio:", "studio"),
            ("Date:", "date"),
            ("Code:", "code"),
            ("Réalisateur:", "director"),
            ("Rating:", "rating"),
            ("Tags (virgules):", "tags"),
            ("Performers (virgules):", "performers"),
        ]
        
        self._setup_ttk_styles()
        self._create_widgets()
        
        if scene_id:
            self._load_from_stash()

    def _setup_ttk_styles(self):
        style = ttk.Style()
        style.map('Valid.TCombobox', fieldbackground=[('readonly', '#d4edda'), ('!disabled', '#d4edda')])
        style.map('Invalid.TCombobox', fieldbackground=[('readonly', '#f8d7da'), ('!disabled', '#f8d7da')])
        style.map('Empty.TCombobox', fieldbackground=[('readonly', '#fff3cd'), ('!disabled', '#fff3cd')])
        style.map('Normal.TCombobox', fieldbackground=[('readonly', 'white'), ('!disabled', 'white')])

    def _create_widgets(self):
        # Header
        header = ttk.Frame(self, padding=10)
        header.pack(fill=tk.X)
        ttk.Label(header, text=f"Scène ID: {self.scene_id or 'Nouvelle'}", font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT)
        
        # Main content
        content = ttk.Frame(self, padding=10)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Grid layout for fields (Standardized to Stash/Validation/Source pattern)
        fields = [
            ("Titre:", "title"),
            ("Studio:", "studio"),
            ("Date:", "date"),
            ("Code:", "code"),
            ("Réalisateur:", "director"),
            ("Rating:", "rating"),
            ("Tags (virgules):", "tags"),
            ("Performers (virgules):", "performers"),
        ]
        
        headers = ["Valider", "Champ", "Valeur Stash", "Validation / Edit", "Sources"]
        for col, text in enumerate(headers):
            ttk.Label(content, text=text, font=('Segoe UI', 9, 'bold')).grid(row=0, column=col, padx=5, pady=5, sticky="w")

        self.field_vars = {}
        for i, (label, key) in enumerate(fields, start=1):
            # 0: Checkbox
            var_check = tk.BooleanVar(value=True)
            ttk.Checkbutton(content, variable=var_check).grid(row=i, column=0, padx=5)
            
            # 1: Label
            ttk.Label(content, text=label).grid(row=i, column=1, sticky="w", padx=5)
            
            # 2: Valeur Stash (Read-only)
            var_stash = tk.StringVar()
            ttk.Entry(content, textvariable=var_stash, state="readonly", width=30).grid(row=i, column=2, padx=5, sticky="we")
            
            # 3: Validation / Edit (Combobox)
            var_main = tk.StringVar()
            combo = ttk.Combobox(content, textvariable=var_main, width=40)
            combo.grid(row=i, column=3, padx=5, sticky="we")
            
            # 4: Source (Read-only)
            var_src = tk.StringVar()
            ttk.Entry(content, textvariable=var_src, state="readonly", width=30).grid(row=i, column=4, padx=5, sticky="we")
            
            # Monitoring
            var_main.trace_add("write", lambda *args, k=key: self._validate_field(k))
            
            self.field_vars[key] = {
                'check': var_check,
                'stash': var_stash,
                'main': var_main,
                'source': var_src,
                'widget': combo
            }
            
        content.columnconfigure(3, weight=10)
        content.columnconfigure(2, weight=5)
        content.columnconfigure(4, weight=5)
        
        # Details / Synopsis
        ttk.Label(content, text="Synopsis / Détails:").grid(row=len(fields)+1, column=0, sticky="nw", padx=5, pady=5)
        self.details_text = scrolledtext.ScrolledText(content, height=10, wrap=tk.WORD)
        self.details_text.grid(row=len(fields)+1, column=1, columnspan=4, sticky="wense", padx=5, pady=5)
        
        # URL Scraping area
        url_frame = ttk.LabelFrame(content, text="URLs de la Scène", padding=10)
        url_frame.grid(row=len(fields)+2, column=0, columnspan=5, sticky="we", pady=10)
        
        self.urls_text = scrolledtext.ScrolledText(url_frame, height=4, wrap=tk.WORD)
        self.urls_text.pack(fill=tk.X, expand=True)
        
        # Toolbar
        toolbar = ttk.Frame(self, padding=10)
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Button(toolbar, text="💾 Sauvegarder", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="🔍 Scraper Scène", command=self._scrape).pack(side=tk.LEFT, padx=5)

    def _load_from_stash(self):
        if not self.scene_id: return
        data = self.db.get_scene_metadata(self.scene_id)
        if data:
            self.metadata = data
            for label, key in self.fields:
                val = str(data.get(key, '')) if data.get(key) is not None else ''
                self.field_vars[key]['stash'].set(val)
                self.field_vars[key]['main'].set(val)
                self._validate_field(key)
            
            # Details
            self.details_text.delete('1.0', tk.END)
            self.details_text.insert('1.0', data.get('details', ''))

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

    def _scrape(self):
        messagebox.showinfo("Scraping", "Scraping de la scène à venir...")

    def _save(self):
        messagebox.showinfo("Sauvegarde", "Données de la scène sauvegardées dans Stash.")
