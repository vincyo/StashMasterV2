"""
Phase2MergeDialog — Fenêtre modale de résolution des résultats Phase 2.
Chaque champ a son propre mode d'affichage et de sélection.
"""
import tkinter as tk
from tkinter import ttk


class Phase2MergeDialog(tk.Toplevel):
    """
    Dialogue de fusion pour les champs Phase 2.
    Affiche les résultats fusionnés et permet à l'utilisateur
    de choisir/modifier avant application.
    """

    def __init__(self, parent, merged_data: dict):
        super().__init__(parent)
        self.title("📋 Résultats scraping Phase 2")
        self.merged_data = merged_data
        self.result = None  # Dict final si l'utilisateur valide

        # Configurer la fenêtre
        self.geometry("900x700")
        self.minsize(800, 600)
        self.transient(parent)
        self.grab_set()

        # Variables de sélection
        self.selections = {}

        self._build_ui()
        self.wait_window()

    def _build_ui(self):
        # ── Frame principal avec scroll ─────────────────────────
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Canvas + Scrollbar pour le contenu
        canvas = tk.Canvas(main, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main, orient=tk.VERTICAL, command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mousewheel scroll
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── Sections par champ ──────────────────────────────────
        self._build_awards_section()
        self._build_trivia_section()
        self._build_details_section()
        self._build_body_art_section("tattoos", "🎨 TATTOOS")
        self._build_body_art_section("piercings", "💉 PIERCINGS")
        self._build_tags_section()
        self._build_urls_section()

        # ── Boutons d'action ────────────────────────────────────
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="✅ Appliquer tout",
                   command=self._apply_all).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="❌ Annuler",
                   command=self.destroy).pack(side=tk.RIGHT, padx=5)

    # ══════════════════════════════════════════════════════════════
    # AWARDS — liste cochable
    # ══════════════════════════════════════════════════════════════

    def _build_awards_section(self):
        data = self.merged_data.get("awards", {})
        merged = data.get("merged", [])
        sources = data.get("sources", {})

        frame = self._section_frame("🏆 AWARDS")

        if not merged:
            ttk.Label(frame, text="Aucun award trouvé").pack(anchor=tk.W)
            self.selections["awards"] = []
            return

        # Compteur par source
        source_info = "  ".join(f"[{s}: {len(a)}]" for s, a in sources.items() if a)
        ttk.Label(frame, text=source_info, font=("Segoe UI", 9, "italic")).pack(anchor=tk.W, pady=(0, 5))

        # Liste cochable
        self.award_vars = []
        for award in merged:
            var = tk.BooleanVar(value=True)
            self.award_vars.append((var, award))
            ttk.Checkbutton(frame, text=award, variable=var).pack(anchor=tk.W, padx=10)

        # Boutons
        btn_row = ttk.Frame(frame)
        btn_row.pack(anchor=tk.W, pady=5)
        ttk.Button(btn_row, text="✓ Tout cocher",
                   command=lambda: [v.set(True) for v, _ in self.award_vars]).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="✗ Tout décocher",
                   command=lambda: [v.set(False) for v, _ in self.award_vars]).pack(side=tk.LEFT, padx=2)

    # ══════════════════════════════════════════════════════════════
    # TRIVIA — sélecteur de source
    # ══════════════════════════════════════════════════════════════

    def _build_trivia_section(self):
        data = self.merged_data.get("trivia", {})
        by_source = data.get("by_source", {})
        suggestion = data.get("suggestion")

        frame = self._section_frame("📝 TRIVIA")

        if not by_source:
            ttk.Label(frame, text="Aucun trivia trouvé").pack(anchor=tk.W)
            self.selections["trivia"] = None
            return

        # Radio buttons pour chaque source
        self.trivia_var = tk.StringVar(value=list(by_source.keys())[0] if suggestion is None else
                                       next((k for k, v in by_source.items() if v == suggestion), ""))
        
        for source, text in by_source.items():
            preview = text[:100] + "..." if len(text) > 100 else text
            ttk.Radiobutton(frame, text=f"{source.upper()} — {preview}",
                           variable=self.trivia_var, value=source).pack(anchor=tk.W, padx=10, pady=2)

        # Zone de prévisualisation
        self.trivia_preview = tk.Text(frame, height=4, width=80, font=("Segoe UI", 9), wrap=tk.WORD)
        self.trivia_preview.pack(fill=tk.X, padx=10, pady=5)
        
        # MAJ prévisualisation quand la sélection change
        def update_preview(*_):
            src = self.trivia_var.get()
            self.trivia_preview.delete("1.0", tk.END)
            self.trivia_preview.insert("1.0", by_source.get(src, ""))
        
        self.trivia_var.trace_add("write", update_preview)
        update_preview()

    # ══════════════════════════════════════════════════════════════
    # DETAILS (Bio) — radio source unique ou fusion
    # ══════════════════════════════════════════════════════════════

    def _build_details_section(self):
        data = self.merged_data.get("details", {})
        by_source = data.get("by_source", {})
        fused = data.get("fused")

        frame = self._section_frame("📖 DETAILS (Bio)")

        if not by_source:
            ttk.Label(frame, text="Aucune bio trouvée").pack(anchor=tk.W)
            self.selections["details"] = None
            return

        # Options
        self.details_var = tk.StringVar(value="freeones" if "freeones" in by_source else list(by_source.keys())[0])

        for source, text in by_source.items():
            length = len(text)
            ttk.Radiobutton(frame, text=f"{source.upper()} ({length} car.)",
                           variable=self.details_var, value=source).pack(anchor=tk.W, padx=10, pady=2)

        if fused:
            ttk.Radiobutton(frame, text=f"Fusion toutes sources ({len(fused)} car.)",
                           variable=self.details_var, value="_fused_").pack(anchor=tk.W, padx=10, pady=2)

        # Zone de prévisualisation
        self.details_preview = tk.Text(frame, height=6, width=80, font=("Segoe UI", 9), wrap=tk.WORD)
        self.details_preview.pack(fill=tk.X, padx=10, pady=5)

        def update_preview(*_):
            src = self.details_var.get()
            self.details_preview.delete("1.0", tk.END)
            if src == "_fused_":
                self.details_preview.insert("1.0", fused or "")
            else:
                self.details_preview.insert("1.0", by_source.get(src, ""))

        self.details_var.trace_add("write", update_preview)
        update_preview()

    # ══════════════════════════════════════════════════════════════
    # TATTOOS / PIERCINGS — liste éditable
    # ══════════════════════════════════════════════════════════════

    def _build_body_art_section(self, field: str, title: str):
        data = self.merged_data.get(field, {})
        merged = data.get("merged", [])

        frame = self._section_frame(title)

        if not merged:
            ttk.Label(frame, text=f"Aucun {field} trouvé").pack(anchor=tk.W)
            self.selections[field] = []
            return

        # Info stratégie
        ttk.Label(frame, text=f"Merge auto (structuré > flat) → {len(merged)} entrées uniques",
                  font=("Segoe UI", 9, "italic")).pack(anchor=tk.W, pady=(0, 5))

        # Liste cochable
        vars_list = []
        for item in merged:
            pos = item.get("position", "?")
            desc = item.get("description", "")
            label = f"{pos}" + (f" ({desc})" if desc else "")
            var = tk.BooleanVar(value=True)
            vars_list.append((var, item))
            ttk.Checkbutton(frame, text=label, variable=var).pack(anchor=tk.W, padx=10)

        setattr(self, f"{field}_vars", vars_list)

        # Boutons
        btn_row = ttk.Frame(frame)
        btn_row.pack(anchor=tk.W, pady=5)
        ttk.Button(btn_row, text="✓ Tout",
                   command=lambda vl=vars_list: [v.set(True) for v, _ in vl]).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="✗ Rien",
                   command=lambda vl=vars_list: [v.set(False) for v, _ in vl]).pack(side=tk.LEFT, padx=2)

    # ══════════════════════════════════════════════════════════════
    # TAGS — liste filtrable
    # ══════════════════════════════════════════════════════════════

    def _build_tags_section(self):
        data = self.merged_data.get("tags", {})
        merged = data.get("merged", [])
        sources = data.get("sources", {})

        frame = self._section_frame("🏷️ TAGS")

        if not merged:
            ttk.Label(frame, text="Aucun tag trouvé").pack(anchor=tk.W)
            self.selections["tags"] = []
            return

        # Compteur
        source_info = "  ".join(f"[{s}: {len(t)}]" for s, t in sources.items() if t)
        ttk.Label(frame, text=f"Union : {len(merged)} tags — {source_info}",
                  font=("Segoe UI", 9, "italic")).pack(anchor=tk.W, pady=(0, 5))

        # Filtre
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=2)
        ttk.Label(filter_frame, text="Filtrer:").pack(side=tk.LEFT)
        self.tag_filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_frame, textvariable=self.tag_filter_var, width=30)
        filter_entry.pack(side=tk.LEFT, padx=5)

        # Tags dans un frame scrollable
        tag_canvas = tk.Canvas(frame, height=150, highlightthickness=0)
        tag_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tag_canvas.yview)
        self.tag_inner = ttk.Frame(tag_canvas)

        self.tag_inner.bind("<Configure>",
                            lambda e: tag_canvas.configure(scrollregion=tag_canvas.bbox("all")))
        tag_canvas.create_window((0, 0), window=self.tag_inner, anchor="nw")
        tag_canvas.configure(yscrollcommand=tag_scroll.set)

        tag_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tag_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        self.tag_vars = []
        for tag in merged:
            var = tk.BooleanVar(value=True)
            self.tag_vars.append((var, tag))
            ttk.Checkbutton(self.tag_inner, text=tag, variable=var).pack(anchor=tk.W)

        # Boutons
        btn_row = ttk.Frame(frame)
        btn_row.pack(anchor=tk.W, pady=5)
        ttk.Button(btn_row, text="✓ Tout",
                   command=lambda: [v.set(True) for v, _ in self.tag_vars]).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="✗ Rien",
                   command=lambda: [v.set(False) for v, _ in self.tag_vars]).pack(side=tk.LEFT, padx=2)

    # ══════════════════════════════════════════════════════════════
    # URLs — tableau
    # ══════════════════════════════════════════════════════════════

    def _build_urls_section(self):
        data = self.merged_data.get("urls", {})
        merged = data.get("merged", {})

        frame = self._section_frame("🔗 URLs")

        if not merged:
            ttk.Label(frame, text="Aucune URL trouvée").pack(anchor=tk.W)
            self.selections["urls"] = {}
            return

        ttk.Label(frame, text=f"{len(merged)} URLs agrégées",
                  font=("Segoe UI", 9, "italic")).pack(anchor=tk.W, pady=(0, 5))

        self.url_vars = []
        for key, url in sorted(merged.items()):
            var = tk.BooleanVar(value=True)
            self.url_vars.append((var, key, url))
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, padx=10, pady=1)
            ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
            ttk.Label(row, text=f"{key}:", width=12, anchor=tk.W,
                      font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
            ttk.Label(row, text=url, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X)

    # ══════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════

    def _section_frame(self, title: str) -> ttk.Frame:
        """Créer un cadre de section avec titre."""
        sep = ttk.Separator(self.scroll_frame, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, padx=5, pady=(10, 5))

        lbl = ttk.Label(self.scroll_frame, text=title, 
                        font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor=tk.W, padx=10)

        frame = ttk.Frame(self.scroll_frame, padding=(10, 5))
        frame.pack(fill=tk.X, padx=5)
        return frame

    def _apply_all(self):
        """Collecter toutes les sélections et fermer."""
        self.result = {}

        # Awards
        if hasattr(self, 'award_vars'):
            self.result["awards"] = [a for v, a in self.award_vars if v.get()]
        else:
            self.result["awards"] = []

        # Trivia
        if hasattr(self, 'trivia_var'):
            src = self.trivia_var.get()
            by_source = self.merged_data.get("trivia", {}).get("by_source", {})
            self.result["trivia"] = by_source.get(src)
        else:
            self.result["trivia"] = None

        # Details
        if hasattr(self, 'details_var'):
            src = self.details_var.get()
            details_data = self.merged_data.get("details", {})
            if src == "_fused_":
                self.result["details"] = details_data.get("fused")
            else:
                self.result["details"] = details_data.get("by_source", {}).get(src)
        else:
            self.result["details"] = None

        # Tattoos
        if hasattr(self, 'tattoos_vars'):
            self.result["tattoos"] = [item for v, item in self.tattoos_vars if v.get()]
        else:
            self.result["tattoos"] = []

        # Piercings
        if hasattr(self, 'piercings_vars'):
            self.result["piercings"] = [item for v, item in self.piercings_vars if v.get()]
        else:
            self.result["piercings"] = []

        # Tags
        if hasattr(self, 'tag_vars'):
            self.result["tags"] = [t for v, t in self.tag_vars if v.get()]
        else:
            self.result["tags"] = []

        # URLs
        if hasattr(self, 'url_vars'):
            self.result["urls"] = {k: u for v, k, u in self.url_vars if v.get()}
        else:
            self.result["urls"] = {}

        self.destroy()
