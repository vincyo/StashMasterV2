"""
Phase2FieldWizard — Dialogue pas-à-pas pour la résolution des champs Phase 2.
Présente un champ à la fois avec le contexte Stash.
"""
import tkinter as tk
from tkinter import ttk


# Ordre des pages du wizard
WIZARD_PAGES = [
    ("awards", "🏆 AWARDS"),
    ("trivia", "📝 TRIVIA"),
    ("tattoos", "🎨 TATTOOS"),
    ("piercings", "💉 PIERCINGS"),
    ("tags", "🏷️ TAGS"),
    ("urls", "🔗 URLs"),
    ("details", "📖 DETAILS (Bio)"),
]


class Phase2FieldWizard(tk.Toplevel):
    """
    Wizard pas-à-pas : une page par champ Phase 2.
    Chaque page affiche le contexte Stash + les données scrapées.
    """

    def __init__(self, parent, merged_data: dict, stash_context: dict,
                 db_data: dict, scraped_results: list[dict] = None, checked_fields: list[str] | None = None):
        super().__init__(parent)
        self.title("📋 Wizard Phase 2 — Résolution pas-à-pas")
        self.merged_data = merged_data
        self.stash_ctx = stash_context
        self.db_data = db_data
        self.scraped_results = scraped_results or []  # Stocker les résultats bruts
        self.checked_fields = checked_fields or []   # ← AJOUTER
        self.result = None
        self.generated_bio = None

        self.geometry("950x700")
        self.minsize(900, 600)
        self.transient(parent)
        self.grab_set()

        # État du wizard
        self.current_page = 0
        self.selections = {}

        # Construire les cadres
        self._build_shell()
        self._show_page(0)
        self.wait_window()

    # ══════════════════════════════════════════════════════════════
    # STRUCTURE PRINCIPALE
    # ══════════════════════════════════════════════════════════════

    def _build_shell(self):
        """Créer la coquille du wizard (header, zone contenu, boutons nav)."""
        # ── Header ──────────────────────────────────────────────
        self.header_frame = ttk.Frame(self, padding=10)
        self.header_frame.pack(fill=tk.X)

        self.page_title = ttk.Label(self.header_frame, text="",
                                     font=("Segoe UI", 14, "bold"))
        self.page_title.pack(side=tk.LEFT)

        self.page_counter = ttk.Label(self.header_frame, text="",
                                       font=("Segoe UI", 10))
        self.page_counter.pack(side=tk.RIGHT)

        # Progress bar
        self.progress = ttk.Progressbar(self, maximum=len(WIZARD_PAGES), length=400)
        self.progress.pack(fill=tk.X, padx=10, pady=(0, 5))

        # ── Zone contenu scrollable ─────────────────────────────
        content_wrapper = ttk.Frame(self)
        content_wrapper.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(content_wrapper, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_wrapper, orient=tk.VERTICAL, command=self.canvas.yview)
        self.content_frame = ttk.Frame(self.canvas)

        self.content_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # Resize canvas window width
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── Boutons navigation ──────────────────────────────────
        nav_frame = ttk.Frame(self, padding=10)
        nav_frame.pack(fill=tk.X)

        self.btn_prev = ttk.Button(nav_frame, text="◀ Précédent", command=self._prev_page)
        self.btn_prev.pack(side=tk.LEFT, padx=5)

        ttk.Button(nav_frame, text="❌ Annuler", command=self.destroy).pack(side=tk.LEFT, padx=5)

        self.btn_next = ttk.Button(nav_frame, text="Suivant ▶", command=self._next_page)
        self.btn_next.pack(side=tk.RIGHT, padx=5)

        self.btn_skip = ttk.Button(nav_frame, text="⏭ Passer", command=self._skip_page)
        self.btn_skip.pack(side=tk.RIGHT, padx=5)

    # ══════════════════════════════════════════════════════════════
    # NAVIGATION
    # ══════════════════════════════════════════════════════════════

    def _prev_page(self):
        if self.current_page > 0:
            self._save_current()
            self.current_page -= 1
            self._show_page(self.current_page)

    def _next_page(self):
        self._save_current()
        if self.current_page < len(WIZARD_PAGES) - 1:
            self.current_page += 1
            self._show_page(self.current_page)
        else:
            self._finish()

    def _skip_page(self):
        """Passer sans sauvegarder le champ courant."""
        if self.current_page < len(WIZARD_PAGES) - 1:
            self.current_page += 1
            self._show_page(self.current_page)
        else:
            self._finish()

    def _show_page(self, idx):
        """Afficher la page à l'index donné."""
        field_key, title = WIZARD_PAGES[idx]

        # MAJ header
        self.page_title.config(text=title)
        self.page_counter.config(text=f"Étape {idx + 1} / {len(WIZARD_PAGES)}")
        self.progress["value"] = idx + 1

        # MAJ boutons
        self.btn_prev.config(state=tk.NORMAL if idx > 0 else tk.DISABLED)
        self.btn_next.config(text="✅ Terminer" if idx == len(WIZARD_PAGES) - 1 else "Suivant ▶")

        # Vider le contenu
        for w in self.content_frame.winfo_children():
            w.destroy()

        # Construire la page selon le champ
        builder = {
            "details": self._page_details,
            "awards": self._page_awards,
            "trivia": self._page_trivia,
            "tattoos": self._page_body_art,
            "piercings": self._page_body_art,
            "tags": self._page_tags,
            "urls": self._page_urls,
        }
        builder_fn = builder.get(field_key, lambda k: None)
        builder_fn(field_key)

        # Scroll en haut
        self.canvas.yview_moveto(0)

    # ══════════════════════════════════════════════════════════════
    # CONTEXTE STASH (affiché sur chaque page)
    # ══════════════════════════════════════════════════════════════

    def _add_stash_context(self, parent):
        """Ajouter un panneau de contexte Stash."""
        ctx = self.stash_ctx
        if not ctx:
            return

        frame = ttk.LabelFrame(parent, text="📊 Contexte Stash", padding=8)
        frame.pack(fill=tk.X, padx=5, pady=5)

        info_parts = []
        if ctx.get("scene_count"):
            info_parts.append(f"🎬 {ctx['scene_count']} scènes")
        if ctx.get("studios"):
            studios_str = ", ".join(ctx["studios"][:10])
            if len(ctx["studios"]) > 10:
                studios_str += f" (+{len(ctx['studios']) - 10})"
            info_parts.append(f"🏢 Studios: {studios_str}")
        if ctx.get("groups"):
            groups_str = ", ".join(ctx["groups"][:8])
            if len(ctx["groups"]) > 8:
                groups_str += f" (+{len(ctx['groups']) - 8})"
            info_parts.append(f"📀 Groups: {groups_str}")
        if ctx.get("collaborators"):
            top5 = [f"{c['name']} ({c['count']})" for c in ctx["collaborators"][:5]]
            info_parts.append(f"👥 Top collabs: {', '.join(top5)}")

        for part in info_parts:
            ttk.Label(frame, text=part, font=("Segoe UI", 9), wraplength=800).pack(
                anchor=tk.W, pady=1)

    # ══════════════════════════════════════════════════════════════
    # PAGE: DETAILS (Bio)
    # ══════════════════════════════════════════════════════════════

    def _page_details(self, field_key):
        parent = self.content_frame
        data = self.merged_data.get("details", {})
        by_source = data.get("by_source", {})
        fused = data.get("fused")
        db_bio = self.db_data.get("details") or self.db_data.get("bio") or ""

        # Contexte Stash
        self._add_stash_context(parent)

        # Valeur Stash actuelle
        if db_bio:
            stash_frame = ttk.LabelFrame(parent, text="📋 Bio actuelle (Stash)", padding=8)
            stash_frame.pack(fill=tk.X, padx=5, pady=5)
            stash_text = tk.Text(stash_frame, height=4, width=80, font=("Segoe UI", 9),
                                 wrap=tk.WORD, state=tk.DISABLED)
            stash_text.pack(fill=tk.X)
            stash_text.config(state=tk.NORMAL)
            stash_text.insert("1.0", db_bio)
            stash_text.config(state=tk.DISABLED)

        # Choix de source
        self._details_choice_frame = ttk.LabelFrame(parent, text="🔄 Choisir la bio", padding=8)
        self._details_choice_frame.pack(fill=tk.X, padx=5, pady=5)

        options = {}
        if db_bio:
            options["stash"] = db_bio

        for source, text in by_source.items():
            options[source] = text

        if fused:
            options["_fused_"] = fused

        # Ajouter la bio IA si déjà générée (persistance)
        if self.generated_bio:
            options["_ia_"] = self.generated_bio

        if not options:
            ttk.Label(self._details_choice_frame, text="Aucune bio disponible",
                      font=("Segoe UI", 10, "italic")).pack(anchor=tk.W)
            return

        # Récupérer la sélection précédente ou défaut
        prev = self.selections.get("details", {}).get("_choice")
        
        # Sélection par défaut : IA si dispo, sinon Stash, sinon première source
        default = prev
        if not default:
            default = "_ia_" if self.generated_bio else ("stash" if db_bio else list(options.keys())[0])

        self._details_var = tk.StringVar(value=default)
        self._details_options = options

        for key, text in options.items():
            label = key.upper() if key != "_fused_" else "FUSION"
            length = len(text)
            ttk.Radiobutton(self._details_choice_frame, text=f"{label} ({length} car.)",
                           variable=self._details_var, value=key).pack(anchor=tk.W, padx=5, pady=2)

        # Preview
        self._details_preview = tk.Text(parent, height=8, width=80,
                                         font=("Segoe UI", 9), wrap=tk.WORD)
        self._details_preview.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        def update(*_):
            self._details_preview.delete("1.0", tk.END)
            self._details_preview.insert("1.0", options.get(self._details_var.get(), ""))

        self._details_var.trace_add("write", update)
        update()

        # NOUVEAU : Bouton génération IA
        gen_frame = ttk.LabelFrame(parent, text="✨ Génération IA", padding=8)
        gen_frame.pack(fill=tk.X, padx=5, pady=5)

        self._bio_status = ttk.Label(gen_frame, text="Prêt (Auto)", font=("Segoe UI", 9, "italic"))
        self._bio_status.pack(side=tk.LEFT, padx=10)

        ttk.Button(
            gen_frame,
            text="🔄 Régénérer (Gemini/Ollama)",
            command=self._run_bio_generation
        ).pack(side=tk.RIGHT, padx=5)

        # Lancement automatique si pas encore de bio IA
        if not self.generated_bio:
            self.after(500, self._run_bio_generation)
        else:
            self._bio_status.config(text="✅ Bio IA déjà disponible")

    def _run_bio_generation(self):
        """Lance la génération IA en thread."""
        import threading
        import copy
        self._bio_status.config(text="🚀 Génération auto en cours (Gemini > Ollama)...")

        def t():
            from services.bio_generator import BioGenerator
            gen = BioGenerator()

            # Utiliser les vrais champs cochés (Phase 1 + Phase 2 disponibles)
            all_checked = (
                self.checked_fields if self.checked_fields
                else list(self.merged_data.keys())
            )
            # Ajouter tous les champs Phase 1 potentiellement utiles.
            # Le générateur décidera d'utiliser les specs techniques (Taille/Poids...) uniquement si les infos sont limitées.
            all_checked.extend(["Name", "Birthdate", "Height", "Weight", "Measurements", "Fake Tits", "Hair Color", "Eye Color", "Ethnicity", "Country", "Aliases", "Career Length"])
            
            # S'assurer que Awards et URLs sont cochés s'ils existent dans les données fusionnées
            all_checked.extend(["Awards", "URLs"])
            
            # Utiliser les données fusionnées, mais mettre à jour avec les sélections utilisateur
            # faites dans les onglets précédents (puisque Details est maintenant à la fin)
            effective_merged = copy.deepcopy(self.merged_data)
            if "awards" in self.selections:
                effective_merged.setdefault("awards", {})["merged"] = self.selections["awards"]["value"]
            
            # AJOUT : Injecter les URLs validées (onglet 6) pour que l'IA connaisse les bons réseaux sociaux
            if "urls" in self.selections:
                effective_merged.setdefault("urls", {})["merged"] = self.selections["urls"]["value"]

            ctx = gen.build_context_from_v2(
                db_data=self.db_data,
                stash_ctx=self.stash_ctx,
                scraped_results=self.scraped_results,  # Passer les résultats bruts
                merged_data=effective_merged,
                checked_fields=all_checked,
            )
            bio = gen.generate(ctx)

            def update():
                if bio:
                    self.generated_bio = bio
                    # Mise à jour UI seulement si on est encore sur la page Details
                    current_key = WIZARD_PAGES[self.current_page][0]
                    if hasattr(self, "_details_options") and current_key == "details":
                        if "_ia_" not in self._details_options:
                            self._details_options["_ia_"] = bio
                            ttk.Radiobutton(
                                self._details_choice_frame,
                                text=f"🤖 IA GENERATED ({len(bio)} car.)",
                                variable=self._details_var,
                                value="_ia_"
                            ).pack(anchor=tk.W, padx=5, pady=2)
                        self._details_var.set("_ia_") # Sélectionne et met à jour la preview via trace
                    self._bio_status.config(text=f"✅ Bio générée ({len(bio)} car.)")
                else:
                    self._bio_status.config(
                        text="❌ Échec — Vérifier .gemini_key ou Ollama actif")

            self.after(0, update)

        threading.Thread(target=t, daemon=True).start()

    # ══════════════════════════════════════════════════════════════
    # PAGE: AWARDS
    # ══════════════════════════════════════════════════════════════

    def _page_awards(self, field_key):
        parent = self.content_frame
        data = self.merged_data.get("awards", {})
        merged = data.get("merged", [])
        sources = data.get("sources", {})

        self._add_stash_context(parent)

        if not merged:
            ttk.Label(parent, text="Aucun award trouvé",
                      font=("Segoe UI", 10, "italic")).pack(anchor=tk.W, padx=10, pady=10)
            return

        # Info sources
        info_frame = ttk.LabelFrame(parent, text="📊 Sources", padding=8)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        source_info = "  ".join(f"[{s}: {len(a)}]" for s, a in sources.items() if a)
        ttk.Label(info_frame, text=source_info, font=("Segoe UI", 9)).pack(anchor=tk.W)

        # Liste cochable
        list_frame = ttk.LabelFrame(parent, text=f"🏆 Awards trouvés ({len(merged)})", padding=8)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        prev = self.selections.get("awards", {}).get("_items")
        self._award_vars = []
        for i, award in enumerate(merged):
            checked = prev[i] if prev and i < len(prev) else True
            var = tk.BooleanVar(value=checked)
            self._award_vars.append((var, award))
            ttk.Checkbutton(list_frame, text=award, variable=var).pack(anchor=tk.W, padx=5)

        # Boutons tout cocher/décocher
        btn_row = ttk.Frame(list_frame)
        btn_row.pack(anchor=tk.W, pady=5)
        ttk.Button(btn_row, text="✓ Tout",
                   command=lambda: [v.set(True) for v, _ in self._award_vars]).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="✗ Rien",
                   command=lambda: [v.set(False) for v, _ in self._award_vars]).pack(side=tk.LEFT, padx=2)

    # ══════════════════════════════════════════════════════════════
    # PAGE: TRIVIA
    # ══════════════════════════════════════════════════════════════

    def _page_trivia(self, field_key):
        parent = self.content_frame
        data = self.merged_data.get("trivia", {})
        by_source = data.get("by_source", {})

        self._add_stash_context(parent)

        if not by_source:
            ttk.Label(parent, text="Aucun trivia trouvé",
                      font=("Segoe UI", 10, "italic")).pack(anchor=tk.W, padx=10, pady=10)
            return

        choice_frame = ttk.LabelFrame(parent, text="📝 Sources Trivia", padding=8)
        choice_frame.pack(fill=tk.X, padx=5, pady=5)

        prev = self.selections.get("trivia", {}).get("_choice")
        default = prev or list(by_source.keys())[0]
        self._trivia_var = tk.StringVar(value=default)
        self._trivia_sources = by_source

        for source, text in by_source.items():
            preview = text[:80] + "..." if len(text) > 80 else text
            ttk.Radiobutton(choice_frame, text=f"{source.upper()} — {preview}",
                           variable=self._trivia_var, value=source).pack(anchor=tk.W, padx=5, pady=2)

        self._trivia_preview = tk.Text(parent, height=6, width=80,
                                        font=("Segoe UI", 9), wrap=tk.WORD)
        self._trivia_preview.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        def update(*_):
            self._trivia_preview.delete("1.0", tk.END)
            self._trivia_preview.insert("1.0", by_source.get(self._trivia_var.get(), ""))

        self._trivia_var.trace_add("write", update)
        update()

    # ══════════════════════════════════════════════════════════════
    # PAGE: TATTOOS / PIERCINGS
    # ══════════════════════════════════════════════════════════════

    def _page_body_art(self, field_key):
        parent = self.content_frame
        data = self.merged_data.get(field_key, {})
        merged = data.get("merged", [])
        db_value = data.get("db_value", "")

        self._add_stash_context(parent)

        # Valeur actuelle Stash
        if db_value:
            stash_frame = ttk.LabelFrame(parent, text=f"📋 {field_key.title()} actuels (Stash)",
                                          padding=8)
            stash_frame.pack(fill=tk.X, padx=5, pady=5)
            ttk.Label(stash_frame, text=str(db_value), font=("Segoe UI", 9),
                      wraplength=800).pack(anchor=tk.W)

        if not merged:
            ttk.Label(parent, text=f"Aucun {field_key} trouvé",
                      font=("Segoe UI", 10, "italic")).pack(anchor=tk.W, padx=10, pady=10)
            return

        list_frame = ttk.LabelFrame(parent, text=f"Résultat ({len(merged)} entrées)", padding=8)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        prev = self.selections.get(field_key, {}).get("_items")
        var_attr = f"_{field_key}_vars"
        vars_list = []
        for i, item in enumerate(merged):
            pos = item.get("position", "?")
            desc = item.get("description", "")
            label = f"{pos}" + (f" ({desc})" if desc else "")
            checked = prev[i] if prev and i < len(prev) else True
            var = tk.BooleanVar(value=checked)
            vars_list.append((var, item))
            ttk.Checkbutton(list_frame, text=label, variable=var).pack(anchor=tk.W, padx=5)

        setattr(self, var_attr, vars_list)

        btn_row = ttk.Frame(list_frame)
        btn_row.pack(anchor=tk.W, pady=5)
        ttk.Button(btn_row, text="✓ Tout",
                   command=lambda vl=vars_list: [v.set(True) for v, _ in vl]).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="✗ Rien",
                   command=lambda vl=vars_list: [v.set(False) for v, _ in vl]).pack(side=tk.LEFT, padx=2)

    # ══════════════════════════════════════════════════════════════
    # PAGE: TAGS
    # ══════════════════════════════════════════════════════════════

    def _page_tags(self, field_key):
        parent = self.content_frame
        data = self.merged_data.get("tags", {})
        merged = data.get("merged", [])
        sources = data.get("sources", {})
        stash_tags = self.db_data.get("tags", [])

        self._add_stash_context(parent)

        # Tags actuels Stash
        if stash_tags:
            stash_frame = ttk.LabelFrame(parent, text=f"📋 Tags actuels Stash ({len(stash_tags)})",
                                          padding=8)
            stash_frame.pack(fill=tk.X, padx=5, pady=5)
            ttk.Label(stash_frame, text=", ".join(stash_tags[:30]),
                      font=("Segoe UI", 9), wraplength=800).pack(anchor=tk.W)

        if not merged:
            ttk.Label(parent, text="Aucun tag scrapé",
                      font=("Segoe UI", 10, "italic")).pack(anchor=tk.W, padx=10, pady=10)
            return

        # Info sources
        info = "  ".join(f"[{s}: {len(t)}]" for s, t in sources.items() if t)
        ttk.Label(parent, text=f"Union : {len(merged)} tags — {info}",
                  font=("Segoe UI", 9, "italic")).pack(anchor=tk.W, padx=10, pady=5)

        list_frame = ttk.LabelFrame(parent, text="🏷️ Tags scrapés", padding=8)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        prev = self.selections.get("tags", {}).get("_items")
        self._tag_vars = []
        for i, tag in enumerate(merged):
            # Marquer si déjà dans Stash
            in_stash = tag.lower() in [t.lower() for t in stash_tags]
            label = f"{'✓ ' if in_stash else ''}{tag}"
            checked = prev[i] if prev and i < len(prev) else True
            var = tk.BooleanVar(value=checked)
            self._tag_vars.append((var, tag))
            ttk.Checkbutton(list_frame, text=label, variable=var).pack(anchor=tk.W, padx=5)

        btn_row = ttk.Frame(list_frame)
        btn_row.pack(anchor=tk.W, pady=5)
        ttk.Button(btn_row, text="✓ Tout",
                   command=lambda: [v.set(True) for v, _ in self._tag_vars]).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="✗ Rien",
                   command=lambda: [v.set(False) for v, _ in self._tag_vars]).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Nouveaux seuls",
                   command=lambda: self._select_new_tags_only(stash_tags)).pack(side=tk.LEFT, padx=2)

    def _select_new_tags_only(self, stash_tags):
        """Cocher uniquement les tags qui ne sont PAS déjà dans Stash."""
        stash_lower = {t.lower() for t in stash_tags}
        for var, tag in self._tag_vars:
            var.set(tag.lower() not in stash_lower)

    # ══════════════════════════════════════════════════════════════
    # PAGE: URLs
    # ══════════════════════════════════════════════════════════════

    def _page_urls(self, field_key):
        parent = self.content_frame
        data = self.merged_data.get("urls", {})
        merged = data.get("merged", {})
        stash_urls = self.db_data.get("urls", [])

        self._add_stash_context(parent)

        # URLs actuelles Stash
        if stash_urls:
            stash_frame = ttk.LabelFrame(parent, text=f"📋 URLs actuelles Stash ({len(stash_urls)})",
                                          padding=8)
            stash_frame.pack(fill=tk.X, padx=5, pady=5)
            for url in stash_urls[:15]:
                ttk.Label(stash_frame, text=url, font=("Segoe UI", 9)).pack(anchor=tk.W)

        if not merged:
            ttk.Label(parent, text="Aucune URL scrapée",
                      font=("Segoe UI", 10, "italic")).pack(anchor=tk.W, padx=10, pady=10)
            return

        list_frame = ttk.LabelFrame(parent, text=f"🔗 URLs scrapées ({len(merged)})", padding=8)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        prev = self.selections.get("urls", {}).get("_items")
        self._url_vars = []
        for i, (key, url) in enumerate(sorted(merged.items())):
            checked = True
            if prev:
                checked = prev.get(key, True)
            var = tk.BooleanVar(value=checked)
            self._url_vars.append((var, key, url))
            row = ttk.Frame(list_frame)
            row.pack(fill=tk.X, padx=5, pady=1)
            ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
            ttk.Label(row, text=f"{key}:", width=12, anchor=tk.W,
                      font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
            ttk.Label(row, text=url, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X)

    # ══════════════════════════════════════════════════════════════
    # SAUVEGARDE / FINITION
    # ══════════════════════════════════════════════════════════════

    def _save_current(self):
        """Sauvegarder la sélection de la page courante."""
        field_key = WIZARD_PAGES[self.current_page][0]

        if field_key == "details":
            if hasattr(self, "_details_var"):
                choice = self._details_var.get()
                text = self._details_options.get(choice, "")
                self.selections["details"] = {"_choice": choice, "value": text}

        elif field_key == "awards":
            if hasattr(self, "_award_vars"):
                items = [v.get() for v, _ in self._award_vars]
                selected = [a for v, a in self._award_vars if v.get()]
                self.selections["awards"] = {"_items": items, "value": selected}

        elif field_key == "trivia":
            if hasattr(self, "_trivia_var"):
                choice = self._trivia_var.get()
                text = self._trivia_sources.get(choice, "")
                self.selections["trivia"] = {"_choice": choice, "value": text}

        elif field_key in ("tattoos", "piercings"):
            var_attr = f"_{field_key}_vars"
            if hasattr(self, var_attr):
                vars_list = getattr(self, var_attr)
                items = [v.get() for v, _ in vars_list]
                selected = [item for v, item in vars_list if v.get()]
                self.selections[field_key] = {"_items": items, "value": selected}

        elif field_key == "tags":
            if hasattr(self, "_tag_vars"):
                items = [v.get() for v, _ in self._tag_vars]
                selected = [t for v, t in self._tag_vars if v.get()]
                self.selections["tags"] = {"_items": items, "value": selected}

        elif field_key == "urls":
            if hasattr(self, "_url_vars"):
                items = {k: v.get() for v, k, _ in self._url_vars}
                selected = {k: u for v, k, u in self._url_vars if v.get()}
                self.selections["urls"] = {"_items": items, "value": selected}

    def _finish(self):
        """Collecter toutes les sélections et fermer."""
        self._save_current()

        self.result = {}

        # Details
        det = self.selections.get("details", {})
        self.result["details"] = det.get("value")

        # Awards
        aw = self.selections.get("awards", {})
        self.result["awards"] = aw.get("value", [])

        # Trivia
        tr = self.selections.get("trivia", {})
        self.result["trivia"] = tr.get("value")

        # Tattoos
        tt = self.selections.get("tattoos", {})
        self.result["tattoos"] = tt.get("value", [])

        # Piercings
        pi = self.selections.get("piercings", {})
        self.result["piercings"] = pi.get("value", [])

        # Tags
        tg = self.selections.get("tags", {})
        self.result["tags"] = tg.get("value", [])

        # URLs
        ur = self.selections.get("urls", {})
        self.result["urls"] = ur.get("value", {})

        self.destroy()
