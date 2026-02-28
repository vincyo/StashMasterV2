"""
DataReviewWindow — GUI 1/3 du flux Bio IA
==========================================
Affiche en plein écran toutes les données scrapées (sauf bio) pour révision :
Trivia · Awards · Tatouages · Piercings · Tags · URLs

Layout :
┌──────────────────────────────────────────────────────────────────────┐
│  HEADER : performer + scraping stats + breadcrumb 1/3                │
├───────────────────────────────────────────────────────────────────────┤
│  RÉSUMÉ PERFORMER (bandeau horizontal) : identité + apparence rapide  │
├──────────────────────────┬────────────────────────────────────────────┤
│  COL GAUCHE              │  COL DROITE                                │
│  ┌── 📝 Trivia ────────┐ │  ┌── 🏆 Awards ──────────────────────────┐ │
│  │  texte éditable     │ │  │  liste cochable                       │ │
│  └────────────────────┘ │  └────────────────────────────────────────┘ │
│  ┌── 🎨 Tatouages ─────┐ │  ┌── 💉 Piercings ──────────────────────┐ │
│  │  liste cochable     │ │  │  liste cochable                       │ │
│  └────────────────────┘ │  ┌── 🏷️ Tags ───────────────────────────┐ │
│  ┌── 🔗 URLs ──────────┐ │  │  grille de badges cochables           │ │
│  │  liste cochable     │ │  └────────────────────────────────────────┘ │
│  └────────────────────┘ │                                             │
├──────────────────────────┴────────────────────────────────────────────┤
│  [Annuler]   [Tout cocher]   [Sélect. vides]       [→ Générer Bio]   │
└──────────────────────────────────────────────────────────────────────┘
"""
import tkinter as tk
from tkinter import ttk, messagebox
import platform

# ── Palette ────────────────────────────────────────────────────────────────────
P = {
    "bg":        "#13131f",
    "surface":   "#1e1e30",
    "card":      "#22223a",
    "card_hdr":  "#2c2c4a",
    "border":    "#3a3a58",
    "accent":    "#7c6af7",
    "success":   "#4caf7d",
    "danger":    "#c05050",
    "text":      "#e8e8f5",
    "muted":     "#8888aa",
    "dim":       "#55557a",
    "trivia_bg": "#1a1a2e",
    "award_bg":  "#1e2a1e",
    "tattoo_bg": "#2a1e1e",
    "tag_sel":   "#2a3a4a",
    "tag_unsel": "#1e1e2a",
    "url_bg":    "#1e1e28",
}

FH1  = ("Segoe UI", 14, "bold")
FH2  = ("Segoe UI", 11, "bold")
FH3  = ("Segoe UI", 9,  "bold")
FB   = ("Segoe UI", 10)
FSM  = ("Segoe UI", 8)
FSMB = ("Segoe UI", 8, "bold")
FMON = ("Consolas", 9)


def _lbl(parent, text, font=FB, fg=None, bg=None, **kw):
    return tk.Label(parent, text=text, font=font,
                    fg=fg or P["text"], bg=bg or P["surface"], **kw)


def _sep(parent, bg=None):
    return tk.Frame(parent, bg=bg or P["border"], height=1)


class _Card(tk.Frame):
    """Carte à en-tête coloré avec zone de contenu."""
    def __init__(self, parent, title, icon="", accent=None, **kw):
        super().__init__(parent, bg=P["card"], bd=0, **kw)
        self._accent = accent or P["accent"]

        # Bande couleur latérale
        tk.Frame(self, bg=self._accent, width=3).pack(side=tk.LEFT, fill=tk.Y)

        inner = tk.Frame(self, bg=P["card"])
        inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # En-tête
        hdr = tk.Frame(inner, bg=P["card_hdr"], pady=5)
        hdr.pack(fill=tk.X)
        _lbl(hdr, f"  {icon}  {title}" if icon else f"  {title}",
             font=FH3, fg=P["text"], bg=P["card_hdr"],
             anchor="w").pack(side=tk.LEFT, padx=4)
        self._count_lbl = _lbl(hdr, "", font=FSM, fg=P["muted"],
                                bg=P["card_hdr"])
        self._count_lbl.pack(side=tk.RIGHT, padx=8)

        _sep(inner, P["border"]).pack(fill=tk.X)

        self._body = tk.Frame(inner, bg=P["card"], padx=6, pady=4)
        self._body.pack(fill=tk.BOTH, expand=True)

    def body(self):
        return self._body

    def set_count(self, n, label=""):
        self._count_lbl.config(text=f"{n} {label}" if n else "")


class DataReviewWindow(tk.Toplevel):
    """
    Fenêtre 1/3 : révision des données scrapées.
    Retourne `result` dict ou None si annulé.
    """
    def __init__(self, parent, db_data, stash_ctx, merged_data,
                 scraped_results, checked_fields):
        super().__init__(parent)
        self.title("📋 Révision des données — Étape 1/3")
        self.configure(bg=P["bg"])

        self.db_data         = db_data
        self.stash_ctx       = stash_ctx
        self.merged_data     = merged_data
        self.scraped_results = scraped_results
        self.checked_fields  = checked_fields

        self.result = None          # dict sélections ou None

        # Widgets de sélection
        self._trivia_text   = None
        self._award_vars    = []    # [(BooleanVar, str)]
        self._tattoo_vars   = []    # [(BooleanVar, dict)]
        self._piercing_vars = []    # [(BooleanVar, dict)]
        self._tag_vars      = []    # [(BooleanVar, str)]
        self._url_vars      = []    # [(BooleanVar, str, str)]  (key, url)

        _fullscreen(self)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.bind("<Escape>", lambda _: self._cancel())
        self.wait_window()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_performer_banner()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self, bg=P["accent"], pady=0)
        hdr.pack(fill=tk.X)
        tk.Frame(hdr, bg="#9a88ff", height=3).pack(fill=tk.X)

        row = tk.Frame(hdr, bg=P["accent"], pady=7)
        row.pack(fill=tk.X, padx=12)

        _lbl(row, "📋", font=("Segoe UI", 18), fg="white",
             bg=P["accent"]).pack(side=tk.LEFT, padx=(0, 8))

        name = self.db_data.get("name", "Performer inconnu")
        _lbl(row, f"Révision des données — {name}",
             font=FH1, fg="white", bg=P["accent"]).pack(side=tk.LEFT)

        # Breadcrumb
        bc = tk.Frame(row, bg=P["accent"])
        bc.pack(side=tk.RIGHT, padx=12)
        for i, (num, lbl, active) in enumerate([
            ("1", "Données", True),
            ("2", "Bio IA",  False),
            ("3", "Valider", False),
        ]):
            fg   = "white"  if active else "#9980cc"
            bgc  = "#5a48c8" if active else P["accent"]
            tk.Label(bc, text=f" {num} ", font=FSMB, fg=fg,
                     bg=bgc, padx=6, pady=3).pack(side=tk.LEFT, padx=1)
            tk.Label(bc, text=lbl, font=FSM, fg=fg,
                     bg=P["accent"]).pack(side=tk.LEFT, padx=(0, 8))

    def _build_performer_banner(self):
        """Bandeau horizontal résumant le performer."""
        banner = tk.Frame(self, bg=P["surface"], pady=6)
        banner.pack(fill=tk.X, padx=0)
        _sep(banner).pack(fill=tk.X)

        inner = tk.Frame(banner, bg=P["surface"])
        inner.pack(fill=tk.X, padx=14, pady=4)

        db = self.db_data
        ctx = self.stash_ctx or {}

        def pill(parent, label, value, accent=None):
            if not value:
                return
            f = tk.Frame(parent, bg=P["card_hdr"])
            f.pack(side=tk.LEFT, padx=4, pady=2)
            tk.Label(f, text=f" {label} ", font=FSMB,
                     fg=P["muted"], bg=P["card_hdr"]).pack(side=tk.LEFT)
            tk.Label(f, text=f" {value} ", font=FSM,
                     fg=accent or P["text"], bg=P["card"]).pack(side=tk.LEFT)

        pill(inner, "🎂", db.get("birthdate"))
        pill(inner, "🌍", db.get("country"))
        pill(inner, "👤", db.get("ethnicity"))
        pill(inner, "💇", db.get("hair_color"))
        pill(inner, "👁", db.get("eye_color"))
        pill(inner, "📐", db.get("measurements"))
        pill(inner, "🎬", str(ctx.get("scene_count", "")) + " scènes"
             if ctx.get("scene_count") else "", P["accent"])
        if ctx.get("studios"):
            pill(inner, "🏢", ", ".join(ctx["studios"][:3]))

        _sep(banner).pack(fill=tk.X)

    def _build_body(self):
        body = tk.Frame(self, bg=P["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=2)
        body.grid_rowconfigure(1, weight=1)
        body.grid_rowconfigure(2, weight=1)

        # ── Colonne gauche ─────────────────────────────────────────────────────
        # Ligne 0 : Trivia (haut)
        self._build_trivia(body, row=0, col=0)
        # Ligne 1 : Tatouages
        self._build_body_art(body, "tattoos",   "🎨", "Tatouages",
                             "#c05050", row=1, col=0)
        # Ligne 2 : URLs
        self._build_urls(body, row=2, col=0)

        # ── Colonne droite ─────────────────────────────────────────────────────
        # Ligne 0 : Awards
        self._build_awards(body, row=0, col=1)
        # Ligne 1 : Piercings
        self._build_body_art(body, "piercings", "💉", "Piercings",
                             "#5080c0", row=1, col=1)
        # Ligne 2 : Tags
        self._build_tags(body, row=2, col=1)

    # ── Sections ───────────────────────────────────────────────────────────────

    def _build_trivia(self, parent, row, col):
        card = _Card(parent, "Trivia / Informations", "📝",
                     accent="#8060d0")
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)

        by_source = self.merged_data.get("trivia", {}).get("by_source", {})
        PRIORITY  = ["freeones", "thenude", "babepedia"]

        if not by_source:
            _lbl(card.body(), "Aucun trivia trouvé.",
                 fg=P["muted"], bg=P["card"]).pack(anchor="w")
            return

        # Sélecteur de source
        top = tk.Frame(card.body(), bg=P["card"])
        top.pack(fill=tk.X, pady=(0, 4))

        _lbl(top, "Source :", font=FH3, fg=P["muted"],
             bg=P["card"]).pack(side=tk.LEFT, padx=4)

        best = next((s for s in PRIORITY if s in by_source), None) or \
               list(by_source.keys())[0]
        self._trivia_src_var = tk.StringVar(value=best)

        for src in by_source:
            n = len(by_source[src])
            rb = tk.Radiobutton(
                top, text=f"{src.upper()} ({n}c)",
                variable=self._trivia_src_var, value=src,
                font=FSM, fg=P["text"], bg=P["card"],
                selectcolor=P["card_hdr"],
                activebackground=P["card"], relief=tk.FLAT,
                command=self._update_trivia_preview,
            )
            rb.pack(side=tk.LEFT, padx=4)

        # Zone texte éditable
        txt_f = tk.Frame(card.body(), bg=P["card"])
        txt_f.pack(fill=tk.BOTH, expand=True)

        self._trivia_text = tk.Text(
            txt_f, wrap=tk.WORD, font=FB,
            bg=P["trivia_bg"], fg=P["text"],
            insertbackground=P["text"],
            relief=tk.FLAT, padx=6, pady=6,
        )
        sb = ttk.Scrollbar(txt_f, command=self._trivia_text.yview)
        self._trivia_text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._trivia_text.pack(fill=tk.BOTH, expand=True)

        self._trivia_sources = by_source
        self._update_trivia_preview()

        card.set_count(len(by_source), "sources")

    def _update_trivia_preview(self):
        if self._trivia_text is None:
            return
        src  = self._trivia_src_var.get()
        text = self._trivia_sources.get(src, "")
        self._trivia_text.delete("1.0", tk.END)
        self._trivia_text.insert("1.0", text)

    def _build_awards(self, parent, row, col):
        data   = self.merged_data.get("awards", {})
        merged = data.get("merged", [])
        srcs   = data.get("sources", {})

        card = _Card(parent, "Awards & Nominations", "🏆",
                     accent="#c0a020")
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        card.set_count(len(merged), "awards")

        if not merged:
            _lbl(card.body(), "Aucun award trouvé.",
                 fg=P["muted"], bg=P["card"]).pack(anchor="w")
            return

        # Infos sources
        src_txt = "  ".join(
            f"[{s.upper()}: {len(a)}]" for s, a in srcs.items() if a
        )
        _lbl(card.body(), src_txt, font=FSM, fg=P["muted"],
             bg=P["card"]).pack(anchor="w", pady=(0, 4))

        # Zone scrollable
        sf = _scrolled_frame(card.body(), bg=P["award_bg"])

        self._award_vars = []
        for award in merged:
            var = tk.BooleanVar(value=True)
            self._award_vars.append((var, award))
            _checkbutton(sf, award, var, bg=P["award_bg"])

        # Boutons tout/rien
        _check_buttons(card.body(), self._award_vars)

    def _build_body_art(self, parent, field, icon, title, accent,
                        row, col):
        data   = self.merged_data.get(field, {})
        merged = data.get("merged", [])
        db_val = data.get("db_value", "")

        card = _Card(parent, title, icon, accent=accent)
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        card.set_count(len(merged))

        if db_val:
            _lbl(card.body(),
                 f"Stash actuel : {str(db_val)[:80]}",
                 font=FSM, fg=P["muted"], bg=P["card"]).pack(anchor="w")

        if not merged:
            _lbl(card.body(), f"Aucun {title.lower()} trouvé.",
                 fg=P["muted"], bg=P["card"]).pack(anchor="w")
            var_attr = f"_{field}_vars"
            setattr(self, var_attr, [])
            return

        sf = _scrolled_frame(card.body(), bg=P["tattoo_bg"])

        vars_list = []
        for item in merged:
            pos  = item.get("position", "?")
            desc = item.get("description", "")
            lbl  = f"{pos}" + (f"  ({desc})" if desc else "")
            var  = tk.BooleanVar(value=True)
            vars_list.append((var, item))
            _checkbutton(sf, lbl, var, bg=P["tattoo_bg"])

        var_attr = f"_{field}_vars"
        setattr(self, var_attr, vars_list)
        _check_buttons(card.body(), vars_list)

    def _build_tags(self, parent, row, col):
        data       = self.merged_data.get("tags", {})
        merged     = data.get("merged", [])
        stash_tags = {t.lower() for t in (self.db_data.get("tags") or [])}

        card = _Card(parent, "Tags", "🏷️", accent="#3a7a9a")
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        card.set_count(len(merged))

        if not merged:
            _lbl(card.body(), "Aucun tag trouvé.",
                 fg=P["muted"], bg=P["card"]).pack(anchor="w")
            return

        # Grille de badges cliquables
        grid = tk.Frame(card.body(), bg=P["card"])
        grid.pack(fill=tk.BOTH, expand=True)

        self._tag_vars = []
        for tag in merged:
            already = tag.lower() in stash_tags
            var = tk.BooleanVar(value=True)
            self._tag_vars.append((var, tag))

            btn_frame = tk.Frame(grid, bg=P["card"])
            btn_frame.pack(side=tk.LEFT, padx=2, pady=2)

            def _toggle(v=var, bf=btn_frame, t=tag, al=already):
                v.set(not v.get())
                _refresh_tag_btn(bf, t, v.get(), al)

            _refresh_tag_btn(btn_frame, tag, True, already)
            btn_frame.bind("<Button-1>", lambda e, fn=_toggle: fn())
            for child in btn_frame.winfo_children():
                child.bind("<Button-1>", lambda e, fn=_toggle: fn())

        # Boutons
        btn_row = tk.Frame(card.body(), bg=P["card"])
        btn_row.pack(fill=tk.X, pady=4)
        _small_btn(btn_row, "✓ Tous",
                   lambda: [v.set(True) or _refresh_all_tags(self._tag_vars)
                             for v, _ in self._tag_vars])
        _small_btn(btn_row, "✗ Aucun",
                   lambda: [v.set(False) or _refresh_all_tags(self._tag_vars)
                             for v, _ in self._tag_vars])
        _small_btn(btn_row, "Nouveaux",
                   lambda: self._select_new_tags(stash_tags))

    def _select_new_tags(self, stash_tags):
        for var, tag in self._tag_vars:
            var.set(tag.lower() not in stash_tags)

    def _build_urls(self, parent, row, col):
        data       = self.merged_data.get("urls", {})
        merged     = data.get("merged", {})
        stash_urls = set(self.db_data.get("urls") or [])

        card = _Card(parent, "URLs & Réseaux sociaux", "🔗",
                     accent="#3a6a9a")
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        card.set_count(len(merged))

        if not merged:
            _lbl(card.body(), "Aucune URL trouvée.",
                 fg=P["muted"], bg=P["card"]).pack(anchor="w")
            return

        sf = _scrolled_frame(card.body(), bg=P["url_bg"])

        ICONS = {
            "iafd": "🎬", "freeones": "🌐", "babepedia": "📚",
            "thenude": "📷", "twitter": "🐦", "instagram": "📸",
            "onlyfans": "💎", "facebook": "👍", "tiktok": "🎵",
        }

        self._url_vars = []
        for key in sorted(merged):
            url  = merged[key]
            icon = ICONS.get(key.lower(), "🔗")
            var  = tk.BooleanVar(value=True)
            self._url_vars.append((var, key, url))

            row_f = tk.Frame(sf, bg=P["url_bg"])
            row_f.pack(fill=tk.X, pady=1)

            cb = tk.Checkbutton(row_f, variable=var, bg=P["url_bg"],
                                fg=P["text"], selectcolor=P["card"],
                                activebackground=P["url_bg"], relief=tk.FLAT)
            cb.pack(side=tk.LEFT)

            tk.Label(row_f, text=f"{icon} {key:<14}",
                     font=FSMB, fg=P["text"], bg=P["url_bg"]).pack(side=tk.LEFT)
            tk.Label(row_f, text=url, font=FSM,
                     fg=P["muted"], bg=P["url_bg"]).pack(side=tk.LEFT)

    # ── Footer ─────────────────────────────────────────────────────────────────

    def _build_footer(self):
        _sep(self, P["border"]).pack(fill=tk.X)
        bar = tk.Frame(self, bg=P["surface"], pady=10)
        bar.pack(fill=tk.X, padx=12)

        _action_btn(bar, "✖ Annuler", P["danger"],
                    self._cancel, side=tk.LEFT)

        tk.Frame(bar, bg=P["surface"], width=12).pack(side=tk.LEFT)

        _action_btn(bar, "✓ Tout cocher", P["dim"],
                    self._check_all, side=tk.LEFT)
        _action_btn(bar, "⭕ Tout décocher", P["dim"],
                    self._uncheck_all, side=tk.LEFT, padx=4)

        _action_btn(bar, "→ Générer la Bio IA", P["success"],
                    self._proceed, side=tk.RIGHT)

    # ── Actions ────────────────────────────────────────────────────────────────

    def _check_all(self):
        for v, _ in self._award_vars:
            v.set(True)
        for v, _ in self._tattoo_vars:
            v.set(True)
        for v, _ in self._piercing_vars:
            v.set(True)
        for v, _ in self._tag_vars:
            v.set(True)
        for v, *_ in self._url_vars:
            v.set(True)

    def _uncheck_all(self):
        for v, _ in self._award_vars:
            v.set(False)
        for v, _ in self._tattoo_vars:
            v.set(False)
        for v, _ in self._piercing_vars:
            v.set(False)
        for v, _ in self._tag_vars:
            v.set(False)
        for v, *_ in self._url_vars:
            v.set(False)

    def _proceed(self):
        """Collecte les sélections et ferme."""
        self.result = {
            "trivia":   self._trivia_text.get("1.0", tk.END).strip()
                        if self._trivia_text else "",
            "awards":   [a  for v, a in self._award_vars    if v.get()],
            "tattoos":  [i  for v, i in self._tattoo_vars   if v.get()],
            "piercings":[i  for v, i in self._piercing_vars if v.get()],
            "tags":     [t  for v, t in self._tag_vars      if v.get()],
            "urls":     {k: u for v, k, u in self._url_vars if v.get()},
        }
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# ── Helpers UI ─────────────────────────────────────────────────────────────────

def _fullscreen(win):
    if platform.system() == "Windows":
        win.state("zoomed")
    elif platform.system() == "Linux":
        try:
            win.attributes("-zoomed", True)
        except Exception:
            win.geometry(f"{win.winfo_screenwidth()}x{win.winfo_screenheight()}+0+0")
    else:
        win.attributes("-fullscreen", True)


def _scrolled_frame(parent, bg=None):
    """Frame scrollable verticalement."""
    bg = bg or P["card"]
    wrapper = tk.Frame(parent, bg=bg)
    wrapper.pack(fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(wrapper, bg=bg, highlightthickness=0)
    sb     = ttk.Scrollbar(wrapper, orient=tk.VERTICAL, command=canvas.yview)
    inner  = tk.Frame(canvas, bg=bg)

    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.bind("<Configure>",
                lambda e: canvas.itemconfig(win_id, width=e.width))
    canvas.bind_all("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    sb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    return inner


def _checkbutton(parent, text, var, bg=None):
    bg = bg or P["card"]
    cb = tk.Checkbutton(
        parent, text=text, variable=var,
        font=FSM, fg=P["text"], bg=bg,
        selectcolor=P["card_hdr"],
        activebackground=bg, relief=tk.FLAT,
        wraplength=360, justify="left", anchor="w",
    )
    cb.pack(anchor="w", padx=4, pady=1)


def _check_buttons(parent, vars_list, extra_btns=None):
    row = tk.Frame(parent, bg=P["card"])
    row.pack(fill=tk.X, pady=4)
    _small_btn(row, "✓ Tous",
               lambda: [v.set(True) for v, _ in vars_list])
    _small_btn(row, "✗ Aucun",
               lambda: [v.set(False) for v, _ in vars_list])
    if extra_btns:
        for txt, cmd in extra_btns:
            _small_btn(row, txt, cmd)


def _small_btn(parent, text, cmd, **kw):
    b = tk.Button(
        parent, text=text, command=cmd,
        font=FSM, bg=P["card_hdr"], fg=P["text"],
        relief=tk.FLAT, padx=8, pady=3, cursor="hand2",
        activebackground=P["border"], activeforeground=P["text"],
    )
    b.pack(side=tk.LEFT, padx=3, **kw)


def _action_btn(parent, text, bg, cmd, side=tk.RIGHT, padx=6):
    b = tk.Button(
        parent, text=text, command=cmd,
        font=FH3, bg=bg, fg="white",
        relief=tk.FLAT, padx=16, pady=8, cursor="hand2",
        activebackground=bg, activeforeground="white",
    )
    b.pack(side=side, padx=padx)


def _refresh_tag_btn(frame, tag, selected, already):
    for w in frame.winfo_children():
        w.destroy()
    bg = P["tag_sel"] if selected else P["tag_unsel"]
    fg = P["text"]    if selected else P["muted"]
    pfx = "✓ " if already else ("+ " if selected else "")
    lbl = tk.Label(frame, text=f"{pfx}{tag}", font=FSMB,
                   fg=fg, bg=bg, padx=8, pady=4, cursor="hand2")
    lbl.pack()


def _refresh_all_tags(tag_vars):
    pass  # Simplification : badges se rafraîchissent au prochain clic
