#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PerformerFrame - Interface de gestion des performers
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import re
from typing import Dict, List, Optional, Tuple, Any, Callable

# Imports locaux
from utils.tag_engine import TagRulesEngine
from utils.awards_cleaner import AwardsCleaner
from services.bio_generator import BioGenerator
from services.database import StashDatabase
from services.config_manager import ConfigManager
from services.scrapers import ScraperOrchestrator
from services.source_finder import SourceFinderWidget
from services.url_manager import URLManager # Nouvelle importation
from services.url_manager import URLOptimizer # Nouvelle importation
from gui.url_verification_dialog import URLVerificationDialog # Nouvelle importation

# utilitaires pour URL (nettoyage / fusion)
from utils.url_utils import clean_urls_list, merge_urls_by_domain

class PerformerFrame(ttk.Frame):
    """Frame principal pour la gestion des performers"""
    
    def __init__(self, parent, performer_id: Optional[str] = None, on_exit_to_selector: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.performer_id = performer_id
        self.on_exit_to_selector = on_exit_to_selector
        
        # Initialisation des services
        self.config = ConfigManager()
        self.db = StashDatabase(self.config.get("database_path"))
        self.tag_rules = TagRulesEngine()
        self.bio_generator = BioGenerator()
        self.orchestrator = ScraperOrchestrator()
        self.url_manager = URLManager() # Initialisation URLManager
        self.url_optimizer = URLOptimizer() # Initialisation URLOptimizer
        
        # Données
        self.stash_data: Dict[str, Any] = {}
        self.field_vars: Dict[str, Dict[str, Any]] = {}
        
        # Widgets
        self.notebook: ttk.Notebook = None # type: ignore
        self.metadata_tab: ttk.Frame = None # type: ignore
        self.advanced_tab: ttk.Frame = None # type: ignore
        self.bio_tab: ttk.Frame = None # type: ignore
        self.bio_text: scrolledtext.ScrolledText = None # type: ignore
        self.char_label: ttk.Label = None # type: ignore
        self.progress_bar: ttk.Progressbar = None # type: ignore
        self.status_label: ttk.Label = None # type: ignore
        self.url_tree: ttk.Treeview = None # type: ignore
        self.btn_back: Optional[ttk.Button] = None
        self.btn_next: Optional[ttk.Button] = None
        self.btn_finish: Optional[ttk.Button] = None
        self.btn_exit: Optional[ttk.Button] = None
        self.fields = [
            ("Nom", "name"),
            ("Aliases", "aliases"),
            ("Date Naissance", "birthdate"),
            ("Lieu Naissance", "birthplace"),
            ("Date Décès", "deathdate"),
            ("Pays", "country"),
            ("Ethnicité", "ethnicity"),
            ("Cheveux", "hair_color"),
            ("Yeux", "eye_color"),
            ("Taille (cm)", "height"),
            ("Poids (kg)", "weight"),
            ("Mesures", "measurements"),
            ("Poitrine", "fake_tits"),
            ("Années activité", "career_length"),
        ]
        
        self.source_labels = {}
        self.bio_valid_var = tk.BooleanVar(value=True)

        # Bio UI (4 sous-onglets)
        self._bio_notebook: Optional[ttk.Notebook] = None
        self._bio_slots: List[str] = ["", "", "", "", ""]  # 0=bio_raw, 1=trivia, 2=google, 3=ollama, 4=stash_bio
        self._bio_merge_content: str = ""
        self._merge_vars: List[tk.BooleanVar] = []

        self._bio_raw_text: Optional[scrolledtext.ScrolledText] = None
        self._bio_trivia_disp: Optional[scrolledtext.ScrolledText] = None
        self._bio_google_text: Optional[scrolledtext.ScrolledText] = None
        self._bio_ollama_text: Optional[scrolledtext.ScrolledText] = None
        self._bio_merge_text: Optional[scrolledtext.ScrolledText] = None

        self._lbl_scrape_chars: Optional[ttk.Label] = None
        self._lbl_scrape_chars2: Optional[ttk.Label] = None
        self._lbl_google_chars: Optional[ttk.Label] = None
        self._lbl_ollama_chars: Optional[ttk.Label] = None
        self._lbl_merge_chars: Optional[ttk.Label] = None
        self._lbl_url_count: Optional[ttk.Label] = None
        self._lbl_award_count: Optional[ttk.Label] = None

        self._ollama_status: Optional[ttk.Label] = None
        self._merge_status: Optional[ttk.Label] = None
        
        self._setup_ttk_styles()
        self._create_widgets()

        if self.notebook:
            self.notebook.bind("<<NotebookTabChanged>>", self._on_notebook_tab_changed)
            self.after(200, self._update_wizard_buttons)
        
        # Différer le chargement pour que la mainloop soit démarrée
        if performer_id:
            self.after(100, self._load_from_stash)

    def _setup_ttk_styles(self):
        style = ttk.Style()
        # On définit des styles pour les Combobox basés sur la validation
        style.map('Valid.TCombobox', fieldbackground=[('readonly', '#d4edda'), ('!disabled', '#d4edda')])
        style.map('Invalid.TCombobox', fieldbackground=[('readonly', '#f8d7da'), ('!disabled', '#f8d7da')])
        style.map('Empty.TCombobox', fieldbackground=[('readonly', '#fff3cd'), ('!disabled', '#fff3cd')])
        style.map('Normal.TCombobox', fieldbackground=[('readonly', 'white'), ('!disabled', 'white')])

    def _create_widgets(self):
        """Crée l'interface de l'onglet Performer"""
        # Notebook pour les sous-onglets
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Onglets
        self.metadata_tab = self._create_metadata_tab()
        self.advanced_tab = self._create_advanced_tab()
        self.bio_tab = self._create_bio_tab()
        
        self.notebook.add(self.metadata_tab, text="📋 Métadonnées")
        self.notebook.add(self.advanced_tab, text="⚙️ Tags & Détails")
        self.notebook.add(self.bio_tab, text="📝 Biographie")
        
        # Barre d'outils
        self._create_toolbar()

    def _get_field_values(self) -> Dict[str, Any]:
        """Récupère toutes les valeurs de validation actuelles"""
        values = {}
        for k, v in self.field_vars.items():
            if v.get('is_multiline'):
                # Handle tk.Text widget
                val = v['entry'].get('1.0', tk.END).strip()
                if k == 'aliases':
                    values[k] = [a.strip() for a in re.split(r'[,\n\r]+', val) if a.strip()]
                elif k == 'discovered_urls' or k == 'urls':
                    values[k] = [u.strip() for u in re.split(r'[,\n\r\s]+', val) if u.strip()]
                else:
                    values[k] = val
            else:
                # Handle tk.StringVar
                values[k] = v['main'].get().strip()
        # Ajouter explicitement la biographie (details)
        values['details'] = self._get_best_bio_text()
            
        return values

    def _get_best_bio_text(self) -> str:
        merge_content = (getattr(self, '_bio_merge_content', '') or '').strip()
        if merge_content:
            return merge_content

        ollama = (self._bio_ollama_text.get('1.0', tk.END).strip()
                  if getattr(self, '_bio_ollama_text', None) else '').strip()
        if ollama:
            return ollama

        google = (self._bio_google_text.get('1.0', tk.END).strip()
                  if getattr(self, '_bio_google_text', None) else '').strip()
        if google:
            return google

        # fallback legacy
        if getattr(self, 'bio_text', None):
            try:
                return self.bio_text.get('1.0', tk.END).strip()
            except Exception:
                pass
        return ""

    def _refresh_bio_counters(self):
        try:
            urls_count = 0
            if 'urls' in self.field_vars and self.field_vars['urls'].get('is_multiline'):
                urls_raw = self.field_vars['urls']['entry'].get('1.0', tk.END).strip()
                urls = [u.strip() for u in re.split(r'[\,\n\r\s]+', urls_raw) if u.strip()]
                urls_count = len(clean_urls_list(urls))

            awards_count = 0
            if 'awards' in self.field_vars and self.field_vars['awards'].get('is_multiline'):
                awards_raw = self.field_vars['awards']['entry'].get('1.0', tk.END).strip()
                awards_count = len([l for l in awards_raw.splitlines() if l.strip()])

            if self._lbl_url_count:
                self._lbl_url_count.config(text=f"URLs : {urls_count}")
            if self._lbl_award_count:
                self._lbl_award_count.config(text=f"Awards : {awards_count}")
        except Exception:
            pass

    def _bio_update_chars(self, slot_idx: int, widget: scrolledtext.ScrolledText, label: ttk.Label):
        text = widget.get('1.0', tk.END).strip()
        self._bio_slots[slot_idx] = text
        label.config(text=f"Caractères : {len(text)}")

    def _bio_clear(self, slot_idx: int):
        mapping = {
            2: self._bio_google_text,
            3: self._bio_ollama_text,
        }
        widget = mapping.get(slot_idx)
        if not widget:
            return
        widget.delete('1.0', tk.END)
        self._bio_slots[slot_idx] = ""
        if slot_idx == 2 and self._lbl_google_chars:
            self._lbl_google_chars.config(text="Caractères : 0")
        if slot_idx == 3 and self._lbl_ollama_chars:
            self._lbl_ollama_chars.config(text="Caractères : 0")

    def _update_raw_content(self, bio_raw: Optional[str] = None, trivia: Optional[str] = None):
        # Update internal slot values
        if bio_raw is not None:
            self._bio_slots[0] = str(bio_raw).strip()
        if trivia is not None:
            self._bio_slots[1] = str(trivia).strip()

        if self._bio_raw_text:
            self._bio_raw_text.config(state='normal')
            self._bio_raw_text.delete('1.0', tk.END)
            self._bio_raw_text.insert('1.0', self._bio_slots[0])
            self._bio_raw_text.config(state='disabled')
            if self._lbl_scrape_chars:
                self._lbl_scrape_chars.config(text=f"Caractères : {len(self._bio_slots[0])}")

        if self._bio_trivia_disp:
            self._bio_trivia_disp.config(state='normal')
            self._bio_trivia_disp.delete('1.0', tk.END)
            self._bio_trivia_disp.insert('1.0', self._bio_slots[1])
            self._bio_trivia_disp.config(state='disabled')
            if self._lbl_scrape_chars2:
                self._lbl_scrape_chars2.config(text=f"Caractères : {len(self._bio_slots[1])}")

        self._refresh_bio_counters()

    def _create_metadata_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.notebook)
        
        # Style pour les entrées textuelles multi-lignes
        # Canvas pour le scroll
        canvas = tk.Canvas(frame, bg="#f5f5f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding=15)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Header de la grille
        
        # Header de la grille
        headers_labels = ["Scrap", "Champ", "Valeur Stash"]
        # Sources fixes (priorité DataMerger)
        source_names = ["IAFD", "FreeOnes", "TheNude", "Babepedia", "Boobpedia", "XXXBios"]
        
        header_fonts = ('Segoe UI', 10, 'bold')
        for col, text in enumerate(headers_labels):
            ttk.Label(scrollable_frame, text=text, font=header_fonts).grid(row=1, column=col, padx=10, pady=10, sticky="w")
        
        for i, name in enumerate(source_names):
            lbl = ttk.Label(scrollable_frame, text=name, font=header_fonts)
            lbl.grid(row=1, column=3 + i, padx=10, pady=10)
            self.source_labels[name] = lbl
        
        # Validation / Edit à la fin
        ttk.Label(scrollable_frame, text="Validation / Edit", font=header_fonts).grid(row=1, column=3 + len(source_names), padx=10, pady=10, sticky="w")

        for i, (label, key) in enumerate(self.fields, start=1):
            # 0: Checkbox
            var_check = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(scrollable_frame, variable=var_check)
            cb.grid(row=i+1, column=0, padx=5, pady=5)
            
            # 1: Label
            ttk.Label(scrollable_frame, text=label, font=('Segoe UI', 9)).grid(row=i+1, column=1, sticky="w", padx=10)
            
            # Determine widget type
            is_multiline = key in ['aliases', 'awards', 'discovered_urls', 'trivia', 'tattoos', 'details']
            if key == 'aliases':
                row_height = 10
            else:
                row_height = 3 if is_multiline else 1
            
            # 2: Stash Value
            var_stash = tk.StringVar()
            if is_multiline:
                entry_stash = tk.Text(scrollable_frame, width=30, height=row_height, font=('Segoe UI', 9), bg="#eeeeee", relief=tk.FLAT)
                entry_stash.grid(row=i+1, column=2, padx=2, pady=2, sticky="nsew")
                entry_stash.configure(state="disabled")
            else:
                entry_stash = ttk.Entry(scrollable_frame, textvariable=var_stash, width=30, state="readonly")
                entry_stash.grid(row=i+1, column=2, padx=2, pady=2, sticky="we")
            
            # 3-6: Sources (Décalé à col 3-6)
            vars_sources = []
            widgets_sources = []
            for col_offset, _ in enumerate(source_names):
                col = 3 + col_offset
                v_src = tk.StringVar()
                if is_multiline:
                    e_src = tk.Text(scrollable_frame, width=20, height=row_height, font=('Segoe UI', 9), bg="#f9f9f9", relief=tk.FLAT)
                    e_src.grid(row=i+1, column=col, padx=2, pady=2, sticky="nsew")
                    e_src.configure(state="disabled")
                else:
                    e_src = ttk.Entry(scrollable_frame, textvariable=v_src, width=20, state="readonly")
                    e_src.grid(row=i+1, column=col, padx=2, pady=2, sticky="we")
                vars_sources.append(v_src)
                widgets_sources.append(e_src)
            
            # 7: Main Input (Validation) - À LA FIN
            var_main = tk.StringVar()
            final_col = 3 + len(source_names)
            if is_multiline:
                entry_main = tk.Text(scrollable_frame, width=45, height=row_height, font=('Segoe UI', 9), relief=tk.FLAT, highlightthickness=1)
                entry_main.grid(row=i+1, column=final_col, padx=2, pady=2, sticky="nsew")
            else:
                entry_main = ttk.Combobox(scrollable_frame, textvariable=var_main, width=45)
                entry_main.grid(row=i+1, column=final_col, padx=2, pady=2, sticky="we")
            
            # Cache vars and widgets
            self.field_vars[key] = {
                'check': var_check,
                'stash': var_stash,
                'main': var_main,
                'entry': entry_main, # This is the widget
                'sources': vars_sources,
                'source_widgets': widgets_sources,
                'stash_widget': entry_stash,
                'is_multiline': is_multiline
            }
            
            # Traces for validation
            def make_callback(k):
                return lambda *args: self._update_validation(k)

            if is_multiline:
                # Text widgets need event binding
                entry_main.bind("<KeyRelease>", make_callback(key))
            else:
                var_check.trace_add("write", make_callback(key))
                var_main.trace_add("write", make_callback(key))
                var_stash.trace_add("write", make_callback(key))
            
            # Allow row to grow for multiline
            if is_multiline:
                scrollable_frame.rowconfigure(i+1, weight=1)
            
        # Configure grid expansion
        final_col = 3 + len(source_names)
        scrollable_frame.columnconfigure(final_col, weight=10) # Validation column takes most space
        scrollable_frame.columnconfigure(2, weight=5) # Stash column
        for c in range(3, final_col):
            scrollable_frame.columnconfigure(c, weight=4) # Source columns
        
        # Expand row for content
        scrollable_frame.rowconfigure(len(self.fields) + 1, weight=1)
        
        # S'assurer que le canvas occupe toute la largeur
        frame.columnconfigure(0, weight=1)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        frame.rowconfigure(0, weight=1)
        
        return frame

    def _create_advanced_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.notebook)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        canvas = tk.Canvas(frame, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding=20)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Disposition en 3 Colonnes
        # Col 1: Tags, Tatouages, Piercings
        col1 = ttk.Frame(scrollable_frame)
        col1.grid(row=0, column=0, sticky="nsew", padx=10)
        
        # Col 2: Awards
        col2 = ttk.Frame(scrollable_frame)
        col2.grid(row=0, column=1, sticky="nsew", padx=10)
        
        # Col 3: URLs
        col3 = ttk.Frame(scrollable_frame)
        col3.grid(row=0, column=2, sticky="nsew", padx=10)
        
        scrollable_frame.columnconfigure(0, weight=1)
        scrollable_frame.columnconfigure(1, weight=1)
        scrollable_frame.columnconfigure(2, weight=1)
        
        # --- Colonne 1 ---
        # Tags
        lf_tags = ttk.LabelFrame(col1, text=" Tags ", padding=10)
        lf_tags.pack(fill=tk.BOTH, expand=True, pady=5)
        self._setup_advanced_field(lf_tags, "tags", has_gen=True)
        
        # Tatouages (ex Tattoos)
        lf_tats = ttk.LabelFrame(col1, text=" Tatouages ", padding=10)
        lf_tats.pack(fill=tk.BOTH, expand=True, pady=5)
        self._setup_advanced_field(lf_tats, "tattoos")
        
        # Piercings
        lf_pierce = ttk.LabelFrame(col1, text=" Piercings ", padding=10)
        lf_pierce.pack(fill=tk.BOTH, expand=True, pady=5)
        self._setup_advanced_field(lf_pierce, "piercings")
        
        # --- Colonne 2 ---
        # Awards
        lf_awards = ttk.LabelFrame(col2, text=" Awards / Prix ", padding=10)
        lf_awards.pack(fill=tk.BOTH, expand=True, pady=5)
        self._setup_advanced_field(lf_awards, "awards")
        
        # --- Colonne 3 ---
        # URLs
        lf_urls = ttk.LabelFrame(col3, text=" URLs (Fusionnées & Uniques) ", padding=10)
        lf_urls.pack(fill=tk.BOTH, expand=True, pady=5)
        self._setup_advanced_field(lf_urls, "urls")
        
        # URLs Découvertes (caché ou secondaire ?) - On le garde pour la compatibilité
        self.field_vars['discovered_urls'] = {'is_multiline': True, 'entry': tk.Text(frame, height=1), 'check': tk.BooleanVar(), 'stash': tk.StringVar(), 'main': tk.StringVar(), 'stash_widget': tk.Text(frame)}

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        return frame

    def _setup_advanced_field(self, parent, key, has_gen=False):
        """Helper pour créer les blocs de l'onglet avancé"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X)
        
        var_check = tk.BooleanVar(value=True)
        ttk.Checkbutton(header_frame, text="Valider", variable=var_check).pack(side=tk.LEFT)
        
        if has_gen and key == "tags":
            ttk.Button(header_frame, text="✨ Générer Tags", command=self._refresh_tags).pack(side=tk.RIGHT)

        ttk.Label(parent, text="Actuel dans Stash:", font=('Segoe UI', 8, 'italic')).pack(anchor="w", pady=(5,0))
        entry_stash = tk.Text(parent, height=2, font=('Segoe UI', 9), bg="#eeeeee", relief=tk.FLAT)
        entry_stash.pack(fill=tk.X, pady=(0, 5))
        entry_stash.configure(state="disabled")

        ttk.Label(parent, text="Validation / Edit:", font=('Segoe UI', 8, 'italic')).pack(anchor="w")
        txt = tk.Text(parent, height=8, font=('Segoe UI', 9), relief=tk.FLAT, highlightthickness=1)
        txt.pack(fill=tk.BOTH, expand=True, pady=5)
        # when editing URLs, keep them clean/validated automatically
        if key == "urls":
            txt.bind('<KeyRelease>', self._on_urls_modified)
        
        var_stash = tk.StringVar()
        var_main = tk.StringVar()
        
        self.field_vars[key] = {
            'check': var_check,
            'stash': var_stash,
            'main': var_main,
            'entry': txt,
            'sources': [],
            'source_widgets': [],
            'stash_widget': entry_stash,
            'is_multiline': True
        }
        txt.bind("<KeyRelease>", lambda e, k=key: self._update_validation(k))

    def _create_bio_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.notebook, padding=10)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self._bio_notebook = ttk.Notebook(frame)
        self._bio_notebook.grid(row=0, column=0, sticky='nsew')

        # --- Tab 0: Scrappé ---
        tab_scrape = ttk.Frame(self._bio_notebook, padding=10)
        tab_scrape.columnconfigure(0, weight=1)
        tab_scrape.rowconfigure(1, weight=1)
        tab_scrape.rowconfigure(3, weight=1)

        header = ttk.Frame(tab_scrape)
        header.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        self._lbl_url_count = ttk.Label(header, text='URLs : 0')
        self._lbl_url_count.pack(side=tk.LEFT, padx=(0, 10))
        self._lbl_award_count = ttk.Label(header, text='Awards : 0')
        self._lbl_award_count.pack(side=tk.LEFT)

        lf_raw = ttk.LabelFrame(tab_scrape, text=' Bio scrappée ', padding=6)
        lf_raw.grid(row=1, column=0, sticky='nsew')
        lf_raw.columnconfigure(0, weight=1)
        lf_raw.rowconfigure(0, weight=1)
        self._bio_raw_text = scrolledtext.ScrolledText(lf_raw, wrap=tk.WORD, height=10)
        self._bio_raw_text.grid(row=0, column=0, sticky='nsew')
        self._bio_raw_text.config(state='disabled')
        self._lbl_scrape_chars = ttk.Label(tab_scrape, text='Caractères : 0')
        self._lbl_scrape_chars.grid(row=2, column=0, sticky=tk.E, pady=(2, 8))

        lf_trivia = ttk.LabelFrame(tab_scrape, text=' Trivia scrappée ', padding=6)
        lf_trivia.grid(row=3, column=0, sticky='nsew')
        lf_trivia.columnconfigure(0, weight=1)
        lf_trivia.rowconfigure(0, weight=1)
        self._bio_trivia_disp = scrolledtext.ScrolledText(lf_trivia, wrap=tk.WORD, height=8)
        self._bio_trivia_disp.grid(row=0, column=0, sticky='nsew')
        self._bio_trivia_disp.config(state='disabled')
        self._lbl_scrape_chars2 = ttk.Label(tab_scrape, text='Caractères : 0')
        self._lbl_scrape_chars2.grid(row=4, column=0, sticky=tk.E, pady=(2, 0))

        # --- Tab 1: Google ---
        tab_google = ttk.Frame(self._bio_notebook, padding=10)
        tab_google.columnconfigure(0, weight=1)
        tab_google.rowconfigure(1, weight=1)
        btns_g = ttk.Frame(tab_google)
        btns_g.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        ttk.Button(btns_g, text='📝 Générer Google', command=self._bio_generate_google).pack(side=tk.LEFT)
        ttk.Button(btns_g, text='🧽 Effacer', command=lambda: self._bio_clear(2)).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(btns_g, text='Valider la Bio', variable=self.bio_valid_var).pack(side=tk.RIGHT)

        self._bio_google_text = scrolledtext.ScrolledText(tab_google, wrap=tk.WORD)
        self._bio_google_text.grid(row=1, column=0, sticky='nsew')
        self._lbl_google_chars = ttk.Label(tab_google, text='Caractères : 0')
        self._lbl_google_chars.grid(row=2, column=0, sticky=tk.E)
        self._bio_google_text.bind(
            '<KeyRelease>',
            lambda e: self._bio_update_chars(2, self._bio_google_text, self._lbl_google_chars),
        )

        # --- Tab 2: Ollama ---
        tab_ollama = ttk.Frame(self._bio_notebook, padding=10)
        tab_ollama.columnconfigure(0, weight=1)
        tab_ollama.rowconfigure(2, weight=1)
        top_o = ttk.Frame(tab_ollama)
        top_o.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        ttk.Button(top_o, text='🤖 Générer Ollama', command=self._bio_generate_ollama).pack(side=tk.LEFT)
        ttk.Button(top_o, text='🧹 Clear Cache', command=self._clear_ollama_cache).pack(side=tk.LEFT, padx=6)
        ttk.Button(top_o, text='🧽 Effacer', command=lambda: self._bio_clear(3)).pack(side=tk.LEFT, padx=6)
        self._ollama_status = ttk.Label(top_o, text='')
        self._ollama_status.pack(side=tk.RIGHT)

        self._bio_ollama_text = scrolledtext.ScrolledText(tab_ollama, wrap=tk.WORD)
        self._bio_ollama_text.grid(row=2, column=0, sticky='nsew')
        self._lbl_ollama_chars = ttk.Label(tab_ollama, text='Caractères : 0')
        self._lbl_ollama_chars.grid(row=3, column=0, sticky=tk.E)
        self._bio_ollama_text.bind(
            '<KeyRelease>',
            lambda e: self._bio_update_chars(3, self._bio_ollama_text, self._lbl_ollama_chars),
        )

        # --- Tab 3: Raffiner/Fusionner ---
        tab_merge = ttk.Frame(self._bio_notebook, padding=10)
        tab_merge.columnconfigure(0, weight=1)
        tab_merge.rowconfigure(4, weight=1)

        src_box = ttk.LabelFrame(tab_merge, text=' Sources à fusionner ', padding=8)
        src_box.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        self._merge_vars = [
            tk.BooleanVar(value=True),
            tk.BooleanVar(value=True),
            tk.BooleanVar(value=True),
            tk.BooleanVar(value=True),
            tk.BooleanVar(value=False),
        ]
        ttk.Checkbutton(src_box, text='Scrappé (bio)', variable=self._merge_vars[0]).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(src_box, text='Scrappé (trivia)', variable=self._merge_vars[1]).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(src_box, text='Google', variable=self._merge_vars[2]).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(src_box, text='Ollama', variable=self._merge_vars[3]).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(src_box, text='Stash (bio existante)', variable=self._merge_vars[4]).pack(side=tk.LEFT, padx=6)

        prompt_lf = ttk.LabelFrame(tab_merge, text=' Directives IA (style, ton, taille, fusion...) ', padding=6)
        prompt_lf.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        self.bio_prompt_text = tk.Text(prompt_lf, height=4, font=('Segoe UI', 9))
        self.bio_prompt_text.pack(fill=tk.X, expand=True)
        self.bio_prompt_text.insert('1.0', 'Ton professionnel, français, environ 3000 caractères. ZÉRO liste à puces. Fusionner proprement les sources sélectionnées.')

        actions = ttk.Frame(tab_merge)
        actions.grid(row=2, column=0, sticky='ew', pady=(0, 6))
        ttk.Button(actions, text='🔀 Fusionner', command=self._bio_do_merge).pack(side=tk.LEFT)
        ttk.Button(actions, text='✨ Raffiner (Ollama)', command=self._bio_do_refine).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text='✅ Appliquer → Ollama', command=self._bio_apply_merge).pack(side=tk.LEFT)
        self._merge_status = ttk.Label(actions, text='')
        self._merge_status.pack(side=tk.RIGHT)

        self._bio_merge_text = scrolledtext.ScrolledText(tab_merge, wrap=tk.WORD)
        self._bio_merge_text.grid(row=4, column=0, sticky='nsew')
        self._lbl_merge_chars = ttk.Label(tab_merge, text='Caractères : 0')
        self._lbl_merge_chars.grid(row=5, column=0, sticky=tk.E)
        self._bio_merge_text.bind(
            '<KeyRelease>',
            lambda e: self._bio_update_merge_chars(),
        )

        # Add tabs
        self._bio_notebook.add(tab_scrape, text='📄 Scrappé')
        self._bio_notebook.add(tab_google, text='🔍 Google')
        self._bio_notebook.add(tab_ollama, text='🤖 Ollama')
        self._bio_notebook.add(tab_merge, text='🔀 Raffiner/Fusionner')

        # Legacy aliases for compatibility with existing methods
        self.bio_text = self._bio_google_text  # type: ignore
        self.char_label = self._lbl_google_chars  # type: ignore

        self._refresh_bio_counters()
        self._update_raw_content(self._bio_slots[0], self._bio_slots[1])

        return frame

    def load_performer(self, performer_data: Dict[str, Any]):
        """Charge les données d'un performer dans l'interface."""
        # 1. Pré-traitement URL Manager Interactif
        if performer_data.get("name"):
            # Récupération URLs existantes
            raw_urls = performer_data.get("urls", [])
            if isinstance(raw_urls, str):
                raw_urls = [u.strip() for u in raw_urls.splitlines() if u.strip()]
            elif raw_urls is None:
                raw_urls = []
            
            # Lancement de la fenêtre de vérification interactive
            # Utilisation de la classe URLVerificationDialog importée
            if isinstance(raw_urls, str):
                raw_urls = [u.strip() for u in raw_urls.splitlines() if u.strip()]
            
            dlg = URLVerificationDialog(self, self.url_manager, raw_urls, performer_data["name"])
            self.wait_window(dlg)
            
            if dlg.final_urls is not None:
                performer_data["urls"] = dlg.final_urls
            # Sinon, on garde les URLs d'origine (si l'utilisateur a fermé sans finir ?)

        self.stash_data = performer_data
        
        # Reset fields
        for key, field_info in self.field_vars.items():
            entry = field_info["entry"]
            if hasattr(entry, 'delete'):
                if isinstance(entry, (tk.Text, scrolledtext.ScrolledText)):
                    entry.delete('1.0', tk.END)
                else:
                    entry.delete(0, tk.END)
        
        # Populate fields
        for key, val in performer_data.items():
            if key in self.field_vars:
                field_info = self.field_vars[key]
                entry = field_info["entry"]
                
                display_val = val
                if isinstance(val, list):
                    display_val = "\n".join(str(v) for v in val if v)
                elif val is None:
                    display_val = ""
                
                if isinstance(entry, (tk.Text, scrolledtext.ScrolledText)):
                    entry.insert('1.0', str(display_val))
                elif isinstance(entry, (ttk.Entry, ttk.Combobox)):
                    entry.insert(0, str(display_val))
        
        self._refresh_bio_counters()
        self._update_raw_content(performer_data.get("bio_raw"), performer_data.get("trivia"))


    def _bio_update_merge_chars(self):
        if not self._bio_merge_text or not self._lbl_merge_chars:
            return
        text = self._bio_merge_text.get('1.0', tk.END).strip()
        self._bio_merge_content = text
        self._lbl_merge_chars.config(text=f"Caractères : {len(text)}")

    def _bio_generate_google(self):
        metadata = self._get_field_values()
        name = self.field_vars.get('name', {}).get('main').get() if 'name' in self.field_vars else ''
        # Injecter la bio Stash existante + bio scrapée + trivia dans les métadonnées
        metadata['bio_raw']   = self._bio_slots[0] or self.stash_data.get('details', '')
        metadata['trivia']    = metadata.get('trivia', '') or self._bio_slots[1]
        metadata['stash_bio'] = self.stash_data.get('details', '')
        bio = self.bio_generator.generate_google_bio(name, metadata)
        if self._bio_google_text and self._lbl_google_chars:
            self._bio_google_text.delete('1.0', tk.END)
            self._bio_google_text.insert('1.0', bio or '')
            self._bio_update_chars(2, self._bio_google_text, self._lbl_google_chars)
        if self._bio_notebook:
            self._bio_notebook.select(1)

    def _bio_generate_ollama(self):
        prompt = self.bio_prompt_text.get('1.0', tk.END).strip() if getattr(self, 'bio_prompt_text', None) else ''
        name = self.field_vars.get('name', {}).get('main').get() if 'name' in self.field_vars else ''

        def run():
            try:
                if self._ollama_status:
                    self.after(0, lambda: self._ollama_status.config(text='Génération...'))
                metadata = self._get_field_values()
                metadata['bio_raw'] = self._bio_slots[0]
                metadata['trivia'] = metadata.get('trivia', '') or self._bio_slots[1]
                bio = self.bio_generator.generate_ollama_bio(name, metadata, custom_prompt=prompt)
                if bio and self._bio_ollama_text and self._lbl_ollama_chars:
                    def apply():
                        self._bio_ollama_text.delete('1.0', tk.END)
                        self._bio_ollama_text.insert('1.0', bio)
                        self._bio_update_chars(3, self._bio_ollama_text, self._lbl_ollama_chars)
                        if self._ollama_status:
                            self._ollama_status.config(text='')
                        if self._bio_notebook:
                            self._bio_notebook.select(2)
                    self.after(0, apply)
                else:
                    self.after(0, lambda: (self._ollama_status.config(text='') if self._ollama_status else None,
                                           messagebox.showerror('Ollama', 'Erreur lors de la génération avec Ollama.')))
            except Exception:
                self.after(0, lambda: (self._ollama_status.config(text='') if self._ollama_status else None,
                                       messagebox.showerror('Ollama', 'Erreur lors de la génération avec Ollama.')))

        threading.Thread(target=run, daemon=True).start()

    def _clear_ollama_cache(self):
        """Nettoie les caches runtime (Python + modèle Ollama en mémoire)."""
        def run():
            try:
                if self._ollama_status:
                    self.after(0, lambda: self._ollama_status.config(text='Clear cache...'))
                ok = self.bio_generator.clear_runtime_caches()
                if self._ollama_status:
                    self.after(0, lambda: self._ollama_status.config(text='Cache OK' if ok else 'Cache partiel'))
            except Exception:
                if self._ollama_status:
                    self.after(0, lambda: self._ollama_status.config(text='Cache error'))

        threading.Thread(target=run, daemon=True).start()

    def _bio_do_merge(self):
        prompt = self.bio_prompt_text.get('1.0', tk.END).strip() if getattr(self, 'bio_prompt_text', None) else ''
        sources = []
        if self._merge_vars and self._merge_vars[0].get() and self._bio_slots[0].strip():
            sources.append('BIO SCRAPPÉE:\n' + self._bio_slots[0].strip())
        if self._merge_vars and self._merge_vars[1].get() and self._bio_slots[1].strip():
            sources.append('TRIVIA SCRAPPÉE:\n' + self._bio_slots[1].strip())
        if self._merge_vars and self._merge_vars[2].get() and self._bio_google_text:
            t = self._bio_google_text.get('1.0', tk.END).strip()
            if t:
                sources.append('BIO GOOGLE:\n' + t)
        if self._merge_vars and self._merge_vars[3].get() and self._bio_ollama_text:
            t = self._bio_ollama_text.get('1.0', tk.END).strip()
            if t:
                sources.append('BIO OLLAMA:\n' + t)
        if self._merge_vars and len(self._merge_vars) > 4 and self._merge_vars[4].get():
            stash_bio = str(self.stash_data.get('details', '') or '').strip()
            if stash_bio:
                sources.append('BIO STASH (EXISTANTE):\n' + stash_bio)

        current = "\n\n---\n\n".join(sources).strip()
        if not current:
            messagebox.showwarning('Fusion', 'Aucune source sélectionnée ou disponible.')
            return

        def run():
            try:
                if self._merge_status:
                    self.after(0, lambda: self._merge_status.config(text='Fusion...'))
                merged = self.bio_generator.refine_bio(current, prompt)
                if merged and self._bio_merge_text and self._lbl_merge_chars:
                    def apply():
                        self._bio_merge_text.delete('1.0', tk.END)
                        self._bio_merge_text.insert('1.0', merged)
                        self._bio_merge_content = merged
                        self._lbl_merge_chars.config(text=f"Caractères : {len(merged.strip())}")
                        if self._merge_status:
                            self._merge_status.config(text='')
                        if self._bio_notebook:
                            self._bio_notebook.select(3)
                    self.after(0, apply)
                else:
                    self.after(0, lambda: (self._merge_status.config(text='') if self._merge_status else None,
                                           messagebox.showerror('Fusion', 'Erreur lors de la fusion avec Ollama.')))
            except Exception:
                self.after(0, lambda: (self._merge_status.config(text='') if self._merge_status else None,
                                       messagebox.showerror('Fusion', 'Erreur lors de la fusion avec Ollama.')))

        threading.Thread(target=run, daemon=True).start()

    def _bio_do_refine(self):
        current = self._get_best_bio_text()
        prompt = self.bio_prompt_text.get('1.0', tk.END).strip() if getattr(self, 'bio_prompt_text', None) else ''
        if not current:
            messagebox.showwarning('IA', 'Aucune biographie à raffiner.')
            return

        def run():
            try:
                if self._merge_status:
                    self.after(0, lambda: self._merge_status.config(text='Raffinage...'))
                refined = self.bio_generator.refine_bio(current, prompt)
                if refined and self._bio_merge_text and self._lbl_merge_chars:
                    def apply():
                        self._bio_merge_text.delete('1.0', tk.END)
                        self._bio_merge_text.insert('1.0', refined)
                        self._bio_merge_content = refined
                        self._lbl_merge_chars.config(text=f"Caractères : {len(refined.strip())}")
                        if self._merge_status:
                            self._merge_status.config(text='')
                        if self._bio_notebook:
                            self._bio_notebook.select(3)
                    self.after(0, apply)
                else:
                    self.after(0, lambda: (self._merge_status.config(text='') if self._merge_status else None,
                                           messagebox.showerror('Ollama', 'Erreur lors du raffinage avec Ollama.')))
            except Exception:
                self.after(0, lambda: (self._merge_status.config(text='') if self._merge_status else None,
                                       messagebox.showerror('Ollama', 'Erreur lors du raffinage avec Ollama.')))

        threading.Thread(target=run, daemon=True).start()

    def _bio_apply_merge(self):
        merged = (getattr(self, '_bio_merge_content', '') or '').strip()
        if not merged or not self._bio_ollama_text or not self._lbl_ollama_chars:
            return
        self._bio_ollama_text.delete('1.0', tk.END)
        self._bio_ollama_text.insert('1.0', merged)
        self._bio_update_chars(3, self._bio_ollama_text, self._lbl_ollama_chars)
        if self._bio_notebook:
            self._bio_notebook.select(2)

    def _load_from_stash(self):
        """Charge les données du performer depuis la base Stash"""
        if not self.performer_id:
            return
            
        data = self.db.get_performer_metadata(self.performer_id)
        if not data:
            messagebox.showerror("Erreur", "Impossible de charger les données du performer.")
            return

        # 0. Vérification interactive des URLs AVANT de charger dans l'interface
        if data.get("name"):
            # Récupération URLs existantes
            raw_urls = data.get("urls", [])
            if isinstance(raw_urls, str):
                raw_urls = [u.strip() for u in raw_urls.splitlines() if u.strip()]
            elif raw_urls is None:
                raw_urls = []
            
            # Lancement de la fenêtre de vérification interactive
            dlg = URLVerificationDialog(self, self.url_manager, raw_urls, data["name"])
            self.wait_window(dlg)
            
            if dlg.final_urls is not None:
                data["urls"] = dlg.final_urls
            # Sinon, on garde les URLs d'origine (si l'utilisateur a fermé sans finir)

        self.stash_data = data
        
        # 1. Remplir les champs de métadonnées
        for key, vars in self.field_vars.items():
            val = data.get(key)
            if val is None: val = ""
            
            if not isinstance(val, str):
                if isinstance(val, list):
                    # Normalisation URLs (Doublons + Tri)
                    if key == 'urls':
                        val = self._sort_urls(list(dict.fromkeys(val)))
                    val = "\n".join(map(str, val))
                else:
                    val = str(val)

            # Nettoyage spécial des aliases : supprimer les placeholders
            if key == 'aliases' and val:
                alias_lines = [a.strip() for a in re.split(r'[\n\r,]+', val) if a.strip()]
                banned = {"no known aliases", "none", "unknown", "n/a"}
                alias_lines = [a for a in alias_lines if a.lower() not in banned]
                val = "\n".join(alias_lines)

            # Normalisation structurée body-art (tatouages/piercings)
            if key in ('tattoos', 'piercings') and val:
                val = self._normalize_body_art_value(key, val)

            # Normalisation unifiée pour tous les champs non-multiline
            if val and not vars.get('is_multiline'):
                val = self._normalize_field_value(key, val)
            elif key == 'awards' and val:
                # Awards : nettoyage spécial via Gemini (champ multiline)
                val = self.bio_generator.clean_awards_with_gemini(val)
                
            if vars.get('is_multiline'):
                st = vars['stash_widget']
                st.configure(state="normal")
                st.delete('1.0', tk.END)
                st.insert('1.0', val)
                st.configure(state="disabled")
                
                et = vars['entry']
                if not et.get('1.0', tk.END).strip():
                    et.delete('1.0', tk.END)
                    et.insert('1.0', val)
            else:
                # Normaliser la valeur avant de la mettre
                vars['stash'].set(val)
                if not vars['main'].get():
                    vars['main'].set(val)
                
                # Mettre à jour la combobox avec la valeur normalisée
                if isinstance(vars['entry'], ttk.Combobox):
                    vars['entry']['values'] = [val] if val else []
            
            self._update_validation(key)

        # 2. Bio / Détails
        details = data.get('details') or ""
        if self._bio_google_text and self._lbl_google_chars:
            self._bio_google_text.delete('1.0', tk.END)
            self._bio_google_text.insert('1.0', str(details))
            self._bio_update_chars(2, self._bio_google_text, self._lbl_google_chars)
        self._bio_merge_content = ""
        if self._bio_merge_text and self._lbl_merge_chars:
            self._bio_merge_text.delete('1.0', tk.END)
            self._lbl_merge_chars.config(text='Caractères : 0')
        self._refresh_bio_counters()

        # 3. URLs
        stash_urls = self.stash_data.get('urls', [])
        # clean duplicates & empties on load
        if isinstance(stash_urls, list):
            cleaned = clean_urls_list(stash_urls)
            # Optimisation et tri par priorité (Top 50)
            cleaned = self.url_optimizer.get_top_urls(cleaned, limit=50, performer_name=self.stash_data.get('name', ''))
            self.stash_data['urls'] = cleaned
            stash_urls = cleaned
        self._highlight_missing_sources(stash_urls)
        # update widget content if any (loop below handles this too but we
        # might want to ensure it's normalized)
        self._start_automatic_validation()

    def _create_toolbar(self):
        toolbar = ttk.Frame(self, padding=5)
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Conteneur pour centrer ou répartir si besoin
        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="💾 Sauvegarder dans Stash", command=self._save_to_stash).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="🔍 Scraper Tout", command=self._scrape_all).pack(side=tk.LEFT, padx=5)
        
        # Barre de progression
        self.status_label = ttk.Label(btn_frame, text="Prêt", font=('Segoe UI', 9))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        self.progress_bar = ttk.Progressbar(btn_frame, orient=tk.HORIZONTAL, length=150, mode='determinate')
        self.progress_bar.pack(side=tk.RIGHT, padx=10)

        # Nouveaux outils V2
        ttk.Button(btn_frame, text="🔎 Chercher Sources", command=self._open_source_finder).pack(side=tk.LEFT, padx=5)

        # Workflow wizard: Back / Next / Finish / Exit
        wizard_frame = ttk.Frame(toolbar)
        wizard_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))

        self.btn_back = ttk.Button(wizard_frame, text="⬅ Back", command=self._go_back_tab)
        self.btn_back.pack(side=tk.LEFT, padx=5)

        self.btn_next = ttk.Button(wizard_frame, text="➡ Next", command=self._go_next_tab)
        self.btn_next.pack(side=tk.LEFT, padx=5)

        self.btn_finish = ttk.Button(wizard_frame, text="✅ Finish", command=self._finish_workflow)
        self.btn_finish.pack(side=tk.LEFT, padx=5)

        self.btn_exit = ttk.Button(wizard_frame, text="❌ Exit", command=self._exit_to_selector)
        self.btn_exit.pack(side=tk.RIGHT, padx=5)

        self._update_wizard_buttons()

    def _current_tab_index(self) -> int:
        if not self.notebook:
            return 0
        try:
            return self.notebook.index(self.notebook.select())
        except Exception:
            return 0

    def _on_notebook_tab_changed(self, _event=None):
        self._update_wizard_buttons()
        # Onglet 3 (Bio) : génération Google auto si vide
        if self._current_tab_index() == 2:
            self._auto_generate_google_bio_if_needed()

    def _update_wizard_buttons(self):
        idx = self._current_tab_index()

        if self.btn_back:
            self.btn_back.configure(state=("normal" if idx > 0 else "disabled"))

        # Onglet 3: Finish visible, Next caché
        if self.btn_next and self.btn_finish:
            if idx >= 2:
                self.btn_next.pack_forget()
                if not self.btn_finish.winfo_manager():
                    self.btn_finish.pack(side=tk.LEFT, padx=5)
            else:
                self.btn_finish.pack_forget()
                if not self.btn_next.winfo_manager():
                    self.btn_next.pack(side=tk.LEFT, padx=5)

    def _go_back_tab(self):
        if not self.notebook:
            return
        idx = self._current_tab_index()
        if idx > 0:
            self.notebook.select(idx - 1)

    def _go_next_tab(self):
        if not self.notebook:
            return

        # Sauvegarde auto à chaque passage d'onglet
        saved = self._save_to_stash_internal(show_messages=False, reload_after_save=False)
        if not saved:
            messagebox.showerror("Sauvegarde", "Échec de sauvegarde automatique. Corrigez puis réessayez.")
            return

        idx = self._current_tab_index()
        if idx < 2:
            self.notebook.select(idx + 1)

    def _finish_workflow(self):
        # Dernier onglet : sauvegarde finale
        saved = self._save_to_stash_internal(show_messages=False, reload_after_save=False)
        if not saved:
            messagebox.showerror("Finish", "Échec de sauvegarde finale.")
            return
        messagebox.showinfo("Finish", "Workflow terminé et sauvegardé.")

    def _exit_to_selector(self):
        # Reset par fermeture de la fenêtre courante, retour sélecteur ID
        if self.on_exit_to_selector:
            self.on_exit_to_selector()
        else:
            root = self.winfo_toplevel()
            try:
                root.destroy()
            except Exception:
                pass

    def _auto_generate_google_bio_if_needed(self):
        try:
            current_google = self._bio_google_text.get('1.0', tk.END).strip() if self._bio_google_text else ""
        except Exception:
            current_google = ""

        if current_google:
            return

        # Génération automatique une seule fois quand on arrive sur l'onglet Bio
        self._bio_generate_google()

    def _open_source_finder(self):
        """Ouvre le chercheur de sources pour ce performer"""
        if not self.stash_data:
            messagebox.showwarning("Attention", "Veuillez d'abord charger les données du performer.")
            return

        name = self.stash_data.get("name", "")
        aliases = self.stash_data.get("aliases", [])
        urls = self.stash_data.get("urls", [])
        
        def on_selected(new_urls):
            if not new_urls:
                return
            # On ajoute les nouvelles URLs à la liste actuelle
            current_urls = list(self.stash_data.get("urls", []))
            # On attend un dict de SourceFinderWidget: {source: url}
            if isinstance(new_urls, dict):
                new_urls_list = list(new_urls.values())
            else:
                new_urls_list = list(new_urls)
            
            merged = merge_urls_by_domain(current_urls, new_urls_list)
            merged = clean_urls_list(merged)
            self.stash_data["urls"] = merged  # Dédupliquer
            messagebox.showinfo("Succès", f"URLs ajoutées localement. N'oubliez pas de sauvegarder.")

        widget = SourceFinderWidget(self, name=name, aliases=aliases, existing_urls=urls, on_urls_selected=on_selected)
        widget.show()

    def _update_validation(self, key: str):
        """Met à jour la couleur de fond de l'entry selon la validité"""
        if key not in self.field_vars:
            return
            
        f = self.field_vars[key]
        entry = f['entry']
        is_checked = f['check'].get()
        
        if f.get('is_multiline'):
            main_val = entry.get('1.0', tk.END).strip()
            stash_val = f['stash_widget'].get('1.0', tk.END).strip()
        else:
            main_val = f['main'].get().strip()
            stash_val = f['stash'].get().strip()
        
        if not is_checked:
            color = "white"
        elif not main_val:
            color = "#fff3cd" # Jaune (vide mais coché)
        elif main_val.lower() == stash_val.lower():
            color = "#d4edda" # Vert (identique)
        else:
            color = "#f8d7da" # Rouge (différent)
            
        # Application de la couleur sécurisée
        if isinstance(entry, tk.Text):
            entry.configure(bg=color)
        else:
            # Pour tous les widgets ttk (Combobox, Entry, etc.)
            style_map = {
                "white": "Normal.TCombobox",
                "#fff3cd": "Empty.TCombobox",
                "#d4edda": "Valid.TCombobox",
                "#f8d7da": "Invalid.TCombobox"
            }
            # Un mappage générique pour les styles ttk
            try:
                # Si c'est un Entry, on utilise Normal.TEntry etc (à définir si besoin)
                # Mais ici on cible principalement les Combobox
                if isinstance(entry, ttk.Combobox):
                    entry.configure(style=style_map.get(color, "Normal.TCombobox"))
                else:
                    # Fallback sécurisé pour éviter le crash -bg
                    pass
            except:
                pass

        # Keep Bio counters in sync
        if key in ("urls", "awards"):
            self._refresh_bio_counters()

    def _update_count(self, event=None):
        count = len(self.bio_text.get('1.0', tk.END).strip())
        self.char_label.config(text=f"Caractères : {count}")

    def _refresh_tags(self):
        metadata = self._get_field_values()
        tags = self.tag_rules.generate_tags(metadata)
        entry = self.field_vars['tags']['entry']
        entry.delete('1.0', tk.END)
        entry.insert('1.0', ', '.join(tags))
        self._update_validation('tags')

    def _gen_bio_google(self):
        self._bio_generate_google()

    def _gen_bio_ollama(self):
        self._bio_generate_ollama()

    def _refine_bio_ollama(self):
        self._bio_do_refine()

    def _apply_bio(self, bio):
        if self._bio_google_text and self._lbl_google_chars:
            self._bio_google_text.delete('1.0', tk.END)
            self._bio_google_text.insert('1.0', bio)
            self._bio_update_chars(2, self._bio_google_text, self._lbl_google_chars)

    def _save_to_stash(self):
        """Sauvegarde les modifications dans Stash"""
        self._save_to_stash_internal(show_messages=True, reload_after_save=True)

    def _save_to_stash_internal(self, show_messages: bool = True, reload_after_save: bool = True) -> bool:
        """Sauvegarde interne (silencieuse possible) utilisée par le workflow Next/Finish."""
        if not self.performer_id:
            if show_messages:
                messagebox.showerror("Sauvegarde", "Aucun performer n'est chargé.")
            return False

        updates = self._get_field_values()

        # Normaliser systématiquement les champs "simples" avant sauvegarde
        for key, meta in self.field_vars.items():
            if not meta.get('is_multiline') and key in updates:
                raw_val = str(updates.get(key) or "").strip()
                if raw_val:
                    updates[key] = self._normalize_field_value(key, raw_val)

        # Normaliser/structurer les champs body-art avant sauvegarde
        for key in ('tattoos', 'piercings'):
            if key in updates:
                updates[key] = self._normalize_body_art_value(key, str(updates.get(key) or ""))

        updates['details'] = self._get_best_bio_text()
        
        # S'assurer que les découvertes d'URL sont incluses si modifiées
        if 'urls' in updates:
            updates['discovered_urls'] = updates['urls']
        
        if self.db.save_performer_metadata(self.performer_id, updates):
            if show_messages:
                messagebox.showinfo("Sauvegarde", "Performer mis à jour avec succès dans Stash.")
            if reload_after_save:
                # Recharger pour rafraîchir les colonnes 'Stash'
                self._load_from_stash()
            return True

        if show_messages:
            messagebox.showerror("Sauvegarde", "Erreur lors de la sauvegarde dans la base de données.")
        return False

    def _scrape_all(self):
        """Orchestre le scraping multi-sources avec barre de progression"""
        urls = self.stash_data.get('urls', [])
        performer_name = self.stash_data.get('name', '')

        # On lance le scraping même sans URLs (Boobpedia + XXXBios seront auto-construits)
        if not urls and not performer_name:
            messagebox.showwarning("Scraping", "Aucune URL et aucun nom trouvé pour ce performer.")
            return

        def update_progress(current, total, source_name):
            self.after(0, lambda: self._update_ui_progress(current, total, source_name))

        def run():
            # Reset UI
            self.after(0, lambda: self.progress_bar.configure(value=0))
            self.after(0, lambda: self.status_label.configure(text="Initialisation..."))
            
            # Scraping avec auto-découverte Boobpedia/XXXBios
            results = self.orchestrator.scrape_all(urls, progress_callback=update_progress, performer_name=performer_name)
            
            if not results:
                self.after(0, lambda: self.status_label.configure(text="Échec"))
                self.after(0, lambda *_: messagebox.showinfo("Scraping", "Aucune donnée trouvée sur les sources."))
                return

            # Validation des URLs découvertes
            self.after(0, lambda: self.status_label.configure(text="Validation URLs..."))
            all_discovered = []
            for res in results:
                d_urls = res.get("discovered_urls", [])
                if isinstance(d_urls, list):
                    all_discovered.extend(d_urls)
            
            all_discovered = list(dict.fromkeys(all_discovered))
            
            if all_discovered:
                from services.url_validator import URLValidator, URLStatus
                validator = URLValidator(timeout=5)
                entries = [{"url": u, "performer_id": self.performer_id or 0, "name": "Discovered", "position": 0} for u in all_discovered]
                valid_results = validator.validate_urls(entries)
                alive_urls = [r.url for r in valid_results if r.status in (URLStatus.ACTIVE, URLStatus.AMBIGUOUS, URLStatus.REDIRECT, URLStatus.WHITELISTED)]
                
                for res in results:
                    res["discovered_urls"] = alive_urls

            self.after(0, lambda *_: self._apply_scrape_results(results))

        threading.Thread(target=run, daemon=True).start()

    def _update_ui_progress(self, current, total, source_name):
        """Met à jour les widgets de progression (appelé via .after)"""
        if self.progress_bar and self.status_label:
            val = (current / total) * 100 if total > 0 else 0
            self.progress_bar.configure(value=val)
            self.status_label.configure(text=f"Scraping {source_name}...")
            if current == total:
                self.status_label.configure(text="Terminé")


    def _apply_scrape_results(self, results: List[Dict]):
        """Affiche les résultats du scraping dans la grille et agrège les URLs"""
        # 1. Agrégation des URLs de toutes les sources + URLs Stash actuelles
        all_discovered = []
        for res in results:
            urls = res.get("discovered_urls", [])
            if isinstance(urls, list):
                all_discovered.extend(urls)
        
        # Ajouter l'existant pour dédoublonnage global
        stash_urls = self.stash_data.get('urls', [])
        
        # Déduplication et Tri Hiérarchique (Core sources first)
        all_discovered = merge_urls_by_domain(stash_urls, all_discovered)
        
        # Mettre à jour l'en-tête (rouge si une source manque)
        self._highlight_missing_sources(all_discovered)
        
        # Dispatcher les réseaux sociaux si présents dans les résultats
        for res in results:
            socials = res.get("socials", {})
            for s_key, s_val in socials.items():
                if s_key in res: continue # Déjà présent ?
                # Normaliser twitter -> x? Non, on garde twitter pour la clé interne
                if s_key == "x": s_key = "twitter"
                if s_val: res[s_key] = s_val
        
        # 2. Mise à jour de la grille (limité aux 6 sources principales configurées)
        source_order = ["IAFD", "FreeOnes", "TheNude", "Babepedia", "Boobpedia", "XXXBios"]
        # Réordonner les résultats selon source_order pour que chaque source tombe dans la bonne colonne
        ordered_results = []
        result_by_source = {r.get('source', ''): r for r in results}
        for sname in source_order:
            ordered_results.append(result_by_source.get(sname, {}))
        limit = len(source_order)
        for source_idx in range(limit):
            res = ordered_results[source_idx]
            source_name = res.get('source', source_order[source_idx])
            
            for key, fields in self.field_vars.items():
                if key == "discovered_urls":
                    continue
                    
                val = res.get(key, "")
                
                # Normalisation unifiée pour tous les champs non-multiline
                if val and not fields.get('is_multiline'):
                    val = self._normalize_field_value(key, str(val))
                elif key == 'awards' and val:
                    # Awards : nettoyage spécial via Gemini (champ multiline)
                    val = self.bio_generator.clean_awards_with_gemini(val)
                elif key in ('tattoos', 'piercings') and val:
                    val = self._normalize_body_art_value(key, str(val))
                
                # Cas spécial : pour la ligne URLs, on veut l'URL source
                if key == "urls" and res.get('url'):
                    val = res['url']
                if isinstance(val, list):
                    val = "\n".join(map(str, val)) if fields.get('is_multiline') else ", ".join(map(str, val))
                
                # Cas spécial : Socials si présents dans un dict
                if key == "socials":
                    # On dispatch les socials vers leurs champs respectifs
                    pass # Sera géré après la boucle key ou via key direct

                # Mettre à jour la colonne source correspondante
                if fields.get('is_multiline'):
                    widgets = fields.get('source_widgets', [])
                    if source_idx < len(widgets):
                        w = widgets[source_idx]
                        w.configure(state="normal")
                        w.delete('1.0', tk.END)
                        w.insert('1.0', str(val))
                        w.configure(state="disabled")
                else:
                    fields['sources'][source_idx].set(str(val))
                
                # Auto-remplissage si case cochée et vide
                is_empty = False
                if fields.get('is_multiline'):
                    is_empty = not fields['entry'].get('1.0', tk.END).strip()
                else:
                    is_empty = not fields['main'].get().strip()

                # Fusion automatique des aliases (ne pas écraser)
                if key == 'aliases' and fields['check'].get() and fields.get('is_multiline') and val:
                    try:
                        current_text = fields['entry'].get('1.0', tk.END).strip()
                        current_aliases = [a.strip() for a in re.split(r'[\n\r,]+', current_text) if a.strip()]
                        incoming_aliases = [a.strip() for a in re.split(r'[\n\r,]+', str(val)) if a.strip()]
                        banned = {"no known aliases", "none", "unknown", "n/a"}
                        current_aliases = [a for a in current_aliases if a.lower() not in banned]
                        incoming_aliases = [a for a in incoming_aliases if a.lower() not in banned]
                        merged = []
                        seen = set()
                        for a in (current_aliases + incoming_aliases):
                            k = a.casefold()
                            if k in seen:
                                continue
                            seen.add(k)
                            merged.append(a)
                        fields['entry'].delete('1.0', tk.END)
                        fields['entry'].insert('1.0', "\n".join(merged))
                        self._update_validation('aliases')
                        is_empty = False
                    except Exception:
                        pass

                if fields['check'].get() and is_empty and val:
                    if fields.get('is_multiline'):
                        fields['entry'].delete('1.0', tk.END)
                        fields['entry'].insert('1.0', str(val))
                    else:
                        fields['main'].set(str(val))
                
                # Mise à jour des valeurs de la liste déroulante (Combobox)
                if not fields.get('is_multiline') and isinstance(fields['entry'], ttk.Combobox):
                    stash_val = fields['stash'].get().strip()
                    source_vals = [s.get().strip() for s in fields['sources']]
                    
                    # Normaliser toutes les valeurs avant de les mettre dans la combobox
                    all_raw = [v for v in ([stash_val] + source_vals) if v]
                    all_normalized = []
                    for v in all_raw:
                        normalized_v = self._normalize_field_value(key, v)
                        if normalized_v:
                            all_normalized.append(normalized_v)
                    
                    # Dédupliquer et trier
                    all_vals = sorted(list(set(all_normalized)))
                    fields['entry']['values'] = all_vals

        # 3. Remplissage du champ global URLs avec les découvertes triées
        if "urls" in self.field_vars and all_discovered:
            fields = self.field_vars["urls"]
            # Fusion intelligente : on garde l'existant déjà édité + découvertes
            current_text = fields['entry'].get('1.0', tk.END).strip()
            current_urls = [u.strip() for u in re.split(r'[,\n\r\s]+', current_text) if u.strip()]
            
            # merge+clean sans doublons
            combined = merge_urls_by_domain(current_urls, all_discovered)
            combined = clean_urls_list(combined)
            
            # Optimisation et tri par priorité (Top 50)
            combined = self.url_optimizer.get_top_urls(combined, limit=50, performer_name=self.stash_data.get('name', ''))
            
            fields['entry'].delete('1.0', tk.END)
            fields['entry'].insert('1.0', "\n".join(combined))
            self._update_validation("urls")

        # 4. Relancer la validation automatique des URLs Stash
        self._start_automatic_validation()

        # 5. Traduction automatique (French/QC) pour les champs texte riches
        def run_translation():
            fields_to_translate = {
                'trivia': 'Trivia',
                'tattoos': 'Tatouages',
                'piercings': 'Piercings'
            }
            
            for key, label in fields_to_translate.items():
                if key not in self.field_vars: continue
                
                # Récupérer la valeur actuelle dans le widget Main
                v = self.field_vars[key]
                current_val = ""
                if v.get('is_multiline'):
                    current_val = v['entry'].get('1.0', tk.END).strip()
                else:
                    current_val = v['main'].get().strip()
                
                if current_val and current_val.lower() != 'none':
                    translated = self.bio_generator.translate_hybrid(current_val, label)
                    if translated and translated != current_val:
                        def update_ui(k=key, t=translated):
                            v_ui = self.field_vars[k]
                            if v_ui.get('is_multiline'):
                                v_ui['entry'].delete('1.0', tk.END)
                                v_ui['entry'].insert('1.0', t)
                            else:
                                v_ui['main'].set(t)
                            self._update_validation(k)
                        self.after(0, update_ui)

        threading.Thread(target=run_translation, daemon=True).start()

        # 6. Sync bio_raw / trivia scrappés dans l'onglet Bio (si présents)
        bio_raw = ""
        trivia = ""
        try:
            for res in results:
                if not bio_raw and res.get('bio_raw'):
                    bio_raw = str(res.get('bio_raw') or '').strip()
                if not trivia and res.get('trivia'):
                    trivia = str(res.get('trivia') or '').strip()
                if bio_raw and trivia:
                    break
        except Exception:
            pass
        if bio_raw or trivia:
            self._update_raw_content(bio_raw=bio_raw, trivia=trivia)

        messagebox.showinfo("Scraping", f"Scraping terminé ({len(results)} sources). {len(all_discovered)} URLs agrégées.")

    def _sort_urls(self, urls: List[str]) -> List[str]:
        """Trie les URLs : sources recherchées d'abord (IAFD, FreeOnes, etc.)"""
        # Cette méthode n'est plus utilisée par le Treeview, mais peut être utile ailleurs.
        # Si elle n'est plus utilisée du tout, elle peut être supprimée.
        core_dirs = ["iafd.com", "freeones.com", "thenude.com", "babepedia.com"]
        
        def sort_key(url):
            url_lower = url.lower()
            for i, domain in enumerate(core_dirs):
                if domain in url_lower:
                    return i
            return 99 # Autres sources après
            
        return sorted(list(set(urls)), key=sort_key)

    def _populate_url_tree(self, urls):
        pass # Ancien Treeview, méthode obsolète

    def _clean_urls(self):
        """Internal helper for the advanced tab that normalizes the list of
        URLs currently displayed: removes blank lines, trims and discards
        duplicates."""
        if 'urls' not in self.field_vars:
            return
        widget = self.field_vars['urls']['entry']
        raw = widget.get('1.0', tk.END)
        urls = [u for u in raw.splitlines()]
        cleaned = clean_urls_list(urls)
        widget.delete('1.0', tk.END)
        widget.insert('1.0', "\n".join(cleaned))

    def _on_urls_modified(self, event=None):
        # if the user is editing URLs manually, keep them tidy and revalidate
        self._clean_urls()
        self._refresh_bio_counters()
        self._start_automatic_validation()

    def _start_automatic_validation(self):
        """Lance la validation automatique des URLs Stash (champ texte)."""
        # make sure urls are cleaned first
        self._clean_urls()

        # On regarde si on a le champ 'urls' (onglet avancé)
        if 'urls' not in self.field_vars:
            return
            
        widget = self.field_vars['urls']['entry']
        text = widget.get('1.0', tk.END).strip()
        if not text:
            return
            
        urls_to_check = text.split('\n')
        
        def validate():
            from services.url_validator import URLStatus
            from services.url_validator import URLValidator
            validator = URLValidator(timeout=5)
            
            entries = [{"url": u, "performer_id": self.performer_id or 0, "name": "Stash", "position": 0} for u in urls_to_check]
            results = validator.validate_urls(entries)
            
            # Mettre à jour l'UI avec des tags de couleur
            for i, res in enumerate(results):
                status = res.status
                tag = "url_ok"
                if status in (URLStatus.DEAD, URLStatus.ERROR):
                    tag = "url_error"
                elif status == URLStatus.REDIRECT:
                    tag = "url_warning"
                
                # Appliquer le tag à la ligne correspondante
                line_start = f"{i+1}.0"
                line_end = f"{i+1}.end"
                self.after(0, lambda w=widget, t=tag, s=line_start, e=line_end: self._apply_url_tag(w, t, s, e))

            # remove dead/error URLs from the widget and re-clean
            from utils.url_utils import clean_urls_list, filter_live_urls
            live_urls = filter_live_urls(urls_to_check, results)
            live_urls = clean_urls_list(live_urls)
            if live_urls != urls_to_check:
                # rewrite the text on the main thread
                self.after(0, lambda: widget.delete('1.0', tk.END))
                self.after(0, lambda: widget.insert('1.0', "\n".join(live_urls)))
                # recolor lines if list shortened
        

        import threading
        threading.Thread(target=validate, daemon=True).start()

    def _apply_url_tag(self, widget, tag, start, end):
        """Applique un tag de couleur à une ligne du widget Text"""
        widget.tag_add(tag, start, end)
        # Configurer les couleurs des tags si pas encore fait
        widget.tag_configure("url_ok", foreground="green")
        widget.url_error_color = widget.tag_configure("url_error", foreground="red")
        widget.tag_configure("url_warning", foreground="orange")

    def _update_url_row(self, item_id, status, redirect, tag):
        current_values = list(self.url_tree.item(item_id)['values'])
        current_values[1] = status
        current_values[2] = redirect
        self.url_tree.item(item_id, values=current_values, tags=(tag,))
        
        # Configurer les couleurs des tags
        self.url_tree.tag_configure("ok", foreground="green")
        self.url_tree.tag_configure("error", foreground="red")
        self.url_tree.tag_configure("warning", foreground="orange")

    def _open_selected_url(self):
        """Ouvre l'URL sélectionnée dans le navigateur"""
        import webbrowser
        selected = self.url_tree.selection()
        if not selected:
            return
        url = self.url_tree.item(selected[0])['values'][0]
        webbrowser.open(url)

    def _normalize_field_value(self, field_key: str, value: str) -> str:
        """Normalise une valeur en fonction du champ"""
        if not value:
            return ""
        
        value = value.strip()
        
        # Dates : formats YYYY-MM-DD
        if field_key in ['birthdate', 'deathdate']:
            from datetime import datetime
            for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%Y"):
                try:
                    dt = datetime.strptime(value.split('T')[0], fmt)
                    return dt.strftime("%Y-%m-%d")
                except:
                    continue
            return value
        
        # Pays : code ISO 2 lettres
        if field_key == 'country':
            return self._normalize_country(value)
        
        # Lieu de naissance : format "City, State, Country" avec pays normalisé
        if field_key == 'birthplace':
            # Standardiser les séparateurs en virgules propres
            value = re.sub(r'\s*[,/]\s*', ', ', value)
            parts = [p.strip() for p in value.split(',') if p.strip()]
            if len(parts) >= 2:
                # Dernier élément = pays -> on le normalise comme pour le champ country
                last = parts[-1]
                parts[-1] = self._normalize_country(last)
                value = ', '.join(parts)
            return value
        
        # Ethnicité : normaliser vers une valeur canonique basée sur la BDD
        if field_key == 'ethnicity':
            v = value.strip().lower()
            ethnicity_map = {
                # Caucasian / White
                'white': 'Caucasian',
                'caucasian': 'Caucasian',
                'european': 'Caucasian',
                # Latin / Latina
                'latin': 'Latina',
                'latina': 'Latina',
                # Black / Ebony
                'black': 'Black',
                'ebony': 'Black',
                'african american': 'Black',
                # Asian
                'asian': 'Asian',
                # Mixed / Middle Eastern et autres cas mineurs
                'mixed': 'Métisse',
                'middle eastern': 'Middle Eastern',
            }
            if v in ethnicity_map:
                return ethnicity_map[v]
            return value.title()
        
        # Cheveux/Yeux : uniformiser
        if field_key in ['hair_color', 'eye_color']:
            # Supprimer espaces inutiles
            v = re.sub(r'\s+', ' ', value).strip()
            low = v.lower()
            if field_key == 'eye_color':
                # Mapping simple EN -> FR pour les yeux
                eye_map = {
                    'brown': 'Brun',
                    'light brown': 'Brun',
                    'dark brown': 'Brun',
                    'blue': 'Bleu',
                    'green': 'Vert',
                    'hazel': 'Noisette',
                    'grey': 'Gris',
                    'gray': 'Gris',
                }
                return eye_map.get(low, v.title())
            else:
                # Cheveux : mapping EN -> FR principal
                hair_map = {
                    'brown': 'Brunette',
                    'dark brown': 'Brunette',
                    'light brown': 'Brunette',
                    'black': 'Noir',
                    'blonde': 'Blonde',
                    'blond': 'Blonde',
                    'red': 'Rousse',
                    'redhead': 'Rousse',
                }
                return hair_map.get(low, v.title())
        
        # Années activité : uniformiser format "YYYY - Now"
        if field_key == 'career_length':
            # Unifier tous les tirets en " - "
            value = re.sub(r'\s*[-–—]\s*', ' - ', value)
            # Normaliser les mots finaux vers "Now"
            value = re.sub(r'\b(present|current|now)\b', 'Now', value, flags=re.I)
            value = re.sub(r'\s+', ' ', value).strip()
            # Si on a juste "YYYY -" → compléter en "YYYY - Now"
            m = re.match(r'^(\d{4})\s*-\s*$', value)
            if m:
                value = f"{m.group(1)} - Now"
            return value
        
        # Mesures : format XX-YY-ZZ
        if field_key == 'measurements':
            # Uniformiser séparateurs
            value = re.sub(r'\s*[-–—]\s*', '-', value)
            return value
        
        # Height/Weight : format avec unités
        if field_key in ['height', 'weight']:
            # Enlever espaces inutiles
            return re.sub(r'\s+', ' ', value).strip()
        
        # Par défaut: juste trim et normaliser espaces
        return re.sub(r'\s+', ' ', value).strip()

    def _normalize_body_art_value(self, field_key: str, value: str) -> str:
        """Nettoie et structure les champs tattoos/piercings en liste lisible."""
        if not value:
            return ""

        text = str(value).replace('\r', '\n').strip()
        text = re.sub(r'(?im)^\s*(tattoos?|tatouages?|piercings?)\s*[:;]\s*', '', text)

        raw_parts = re.split(r'[\n;]+', text)
        normalized_parts = []
        seen = set()

        for part in raw_parts:
            p = part.strip().strip('-').strip()
            if not p:
                continue

            low = p.lower()
            if 'nombres en francais' in low:
                continue

            if field_key == 'piercings':
                p = re.sub(r'\bnavel\b', 'Nombril', p, flags=re.I)
                p = re.sub(r'\bbelly\s*button\b', 'Nombril', p, flags=re.I)
                p = re.sub(r'\bnipples?\b', 'Tétons', p, flags=re.I)
                p = re.sub(r'\btit[s]?\b', 'Tétons', p, flags=re.I)

            p = re.sub(r'\s+', ' ', p).strip(' ,.')
            if len(p) < 2:
                continue

            key_norm = p.casefold()
            if key_norm in seen:
                continue
            seen.add(key_norm)
            normalized_parts.append(p)

        if not normalized_parts:
            return ""

        return "\n".join(f"- {p}" for p in normalized_parts)

    def _normalize_country(self, country: str) -> str:
        """Convertit un nom de pays en code ISO 2 lettres"""
        if not country or len(country) == 2:
            return country
            
        mapping = {
            "united states": "US", "usa": "US",
            "united kingdom": "UK", "uk": "UK",
            "france": "FR", "germany": "DE", "spain": "ES",
            "italy": "IT", "canada": "CA", "brazil": "BR",
            "russia": "RU", "japan": "JP", "australia": "AU",
            "hungary": "HU", "czech republic": "CZ", "poland": "PL",
            "netherlands": "NL", "belgium": "BE", "switzerland": "CH",
        }
        return mapping.get(country.lower().strip(), country)

    def _highlight_missing_sources(self, urls: List[str]):
        """Surligne en rouge le nom des sources manquantes dans les URLs Stash"""
        if not hasattr(self, 'source_labels'):
            return
            
        # Priorités
        core_dirs = {
            "IAFD": "iafd.com",
            "FreeOnes": "freeones.com",
            "TheNude": "thenude.com",
            "Babepedia": "babepedia.com",
            "Boobpedia": "boobpedia.com",
            "XXXBios": "xxxbios.com"
        }
        
        url_text = "\n".join(urls).lower()
        
        for name, domain in core_dirs.items():
            lbl = self.source_labels.get(name)
            if lbl:
                if domain in url_text:
                    lbl.configure(foreground="black")
                else:
                    lbl.configure(foreground="red")
    def _delete_selected_url(self):
        """Supprime l'URL sélectionnée de la liste locale"""
        selected = self.url_tree.selection()
        if not selected:
            return
        if messagebox.askyesno("Confirmation", "Supprimer cette URL de la liste locale ?"):
            self.url_tree.delete(selected[0])
            # Note: cela ne supprime pas de Stash tant qu'on n'a pas sauvegardé
