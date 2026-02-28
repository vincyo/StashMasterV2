"""
ValidationWindow — GUI 3/3 du flux Bio IA
==========================================
Récapitulatif final avant injection dans Stash.

Layout :
┌──────────────────────────────────────────────────────────────────────┐
│  HEADER : performer + breadcrumb 3/3                                 │
├─────────────────────────┬────────────────────────────────────────────┤
│  RÉCAPITULATIF 40%      │  BIO FINALE 60%                            │
│                         │                                            │
│  ┌── ✅ À injecter ───┐ │  ┌── ✍️ Biographie (éditable) ──────────┐ │
│  │  Trivia : ✓/✗      │ │  │                                       │ │
│  │  Awards : N        │ │  │  Grande zone de texte éditable        │ │
│  │  Tatouages : N     │ │  │  avec scroll                          │ │
│  │  Piercings : N     │ │  │                                       │ │
│  │  Tags : N          │ │  │                                       │ │
│  │  URLs : N          │ │  │                                       │ │
│  └────────────────────┘ │  └───────────────────────────────────────┘ │
│                         │  [📋 Copier] [🗑 Effacer] [N chars]        │
│  ┌── ⚠️ Champs DB ────┐ │                                            │
│  │  Mapping injection │ │                                            │
│  │  avant/après       │ │                                            │
│  └────────────────────┘ │                                            │
├─────────────────────────┴────────────────────────────────────────────┤
│  [← Retour]  [✖ Annuler]              [✅ INJECTER DANS STASH]       │
└──────────────────────────────────────────────────────────────────────┘
"""
import tkinter as tk
from tkinter import ttk, messagebox
import platform

# ── Palette ────────────────────────────────────────────────────────────────────
P = {
    "bg":         "#13131f",
    "surface":    "#1e1e30",
    "card":       "#22223a",
    "card_hdr":   "#2c2c4a",
    "border":     "#3a3a58",
    "accent":     "#7c6af7",
    "success":    "#4caf7d",
    "success_dk": "#2a6a4a",
    "danger":     "#c05050",
    "warn":       "#d4a940",
    "text":       "#e8e8f5",
    "muted":      "#8888aa",
    "dim":        "#55557a",
    "bio_bg":     "#0d0d1e",
    "added":      "#1a3a1a",   # fond items ajoutés
    "removed":    "#3a1a1a",   # fond items supprimés
}

FH1  = ("Segoe UI", 14, "bold")
FH2  = ("Segoe UI", 11, "bold")
FH3  = ("Segoe UI", 9,  "bold")
FB   = ("Segoe UI", 10)
FSM  = ("Segoe UI", 8)
FSMB = ("Segoe UI", 8,  "bold")


class ValidationWindow(tk.Toplevel):
    """
    Fenêtre 3/3 : validation finale et injection dans Stash.
    """
    def __init__(self, parent, db_data, stash_ctx,
                 review_result, bio_result):
        super().__init__(parent)
        self.title("✅ Validation & Injection — Étape 3/3")
        self.configure(bg=P["bg"])

        self.db_data       = db_data
        self.stash_ctx     = stash_ctx
        self.review_result = review_result   # dict depuis GUI 1
        self.bio_result    = bio_result      # dict {'bio': str} depuis GUI 2

        self.result        = None   # 'injected' | None

        _fullscreen(self)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._populate_summary()
        self._populate_bio()

        self.bind("<Escape>", lambda _: self._cancel())
        self.wait_window()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()

        body = tk.Frame(self, bg=P["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        body.grid_columnconfigure(0, weight=38)
        body.grid_columnconfigure(1, weight=62)
        body.grid_rowconfigure(0, weight=1)

        self._build_summary_panel(body)
        self._build_bio_panel(body)

        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self, bg=P["success"], pady=0)
        hdr.pack(fill=tk.X)
        tk.Frame(hdr, bg="#6adf9d", height=3).pack(fill=tk.X)

        row = tk.Frame(hdr, bg=P["success"], pady=7)
        row.pack(fill=tk.X, padx=12)

        tk.Label(row, text="✅", font=("Segoe UI", 18),
                 fg="white", bg=P["success"]).pack(side=tk.LEFT, padx=(0, 8))

        name = self.db_data.get("name", "Performer inconnu")
        tk.Label(row, text=f"Validation & Injection — {name}",
                 font=FH1, fg="white", bg=P["success"]).pack(side=tk.LEFT)

        # Breadcrumb
        bc = tk.Frame(row, bg=P["success"])
        bc.pack(side=tk.RIGHT, padx=12)
        for num, lbl, active in [("1","Données",False),("2","Bio IA",False),("3","Valider",True)]:
            bg = P["success_dk"] if active else P["success"]
            fg = "white"         if active else "#aaffcc"
            tk.Label(bc, text=f" {num} ", font=FSMB, fg=fg,
                     bg=bg, padx=6, pady=3).pack(side=tk.LEFT, padx=1)
            tk.Label(bc, text=lbl, font=FSM, fg=fg,
                     bg=P["success"]).pack(side=tk.LEFT, padx=(0, 8))

    # ── Panneau gauche : Récapitulatif ─────────────────────────────────────────

    def _build_summary_panel(self, parent):
        panel = tk.Frame(parent, bg=P["surface"])
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        _hdr(panel, "📊 Récapitulatif des modifications")

        # Scrollable
        canvas = tk.Canvas(panel, bg=P["surface"], highlightthickness=0)
        sb     = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=canvas.yview)
        self._summary_inner = tk.Frame(canvas, bg=P["surface"])

        self._summary_inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        ))
        win = canvas.create_window((0, 0), window=self._summary_inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _populate_summary(self):
        parent = self._summary_inner
        rv = self.review_result or {}
        db = self.db_data

        def section(title, icon, items_new, items_old=None, text_mode=False):
            """Carte récapitulatif pour un champ."""
            card = tk.Frame(parent, bg=P["card"], pady=0)
            card.pack(fill=tk.X, padx=6, pady=4)
            tk.Frame(card, bg=P["accent"], width=3).pack(side=tk.LEFT, fill=tk.Y)

            inner = tk.Frame(card, bg=P["card"])
            inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # En-tête
            hf = tk.Frame(inner, bg=P["card_hdr"], pady=4)
            hf.pack(fill=tk.X)
            tk.Label(hf, text=f"  {icon}  {title}", font=FH3,
                     fg=P["text"], bg=P["card_hdr"], anchor="w").pack(side=tk.LEFT, padx=4)

            if text_mode:
                # Champ texte court
                n = len(items_new) if items_new else 0
                status = f"✓ {n} chars" if n > 0 else "— vide"
                color  = P["success"] if n > 0 else P["muted"]
                tk.Label(hf, text=status, font=FSMB,
                         fg=color, bg=P["card_hdr"]).pack(side=tk.RIGHT, padx=8)
                if items_new:
                    preview = items_new[:120] + ("…" if len(items_new) > 120 else "")
                    tk.Label(inner, text=preview, font=FSM,
                             fg=P["muted"], bg=P["card"],
                             wraplength=320, justify="left",
                             anchor="w", padx=8, pady=4).pack(fill=tk.X)
            else:
                # Liste d'éléments
                n_new = len(items_new) if items_new else 0
                n_old = len(items_old) if items_old else 0
                added = n_new - n_old if n_new > n_old else 0
                status = f"+{added} · total {n_new}" if added else f"{n_new} éléments"
                color  = P["success"] if n_new > 0 else P["muted"]
                tk.Label(hf, text=status, font=FSMB,
                         fg=color, bg=P["card_hdr"]).pack(side=tk.RIGHT, padx=8)

                body = tk.Frame(inner, bg=P["card"], padx=8, pady=4)
                body.pack(fill=tk.X)

                display = items_new[:8] if items_new else []
                for it in display:
                    label = it if isinstance(it, str) else \
                            (f"{it.get('position','')} ({it.get('description','')})"
                             if it.get("description") else it.get("position", str(it)))
                    tk.Label(body, text=f"  ✓ {label}", font=FSM,
                             fg=P["text"], bg=P["card"], anchor="w").pack(fill=tk.X)
                if items_new and len(items_new) > 8:
                    tk.Label(body, text=f"  … +{len(items_new)-8} autres",
                             font=FSM, fg=P["muted"], bg=P["card"],
                             anchor="w").pack(fill=tk.X)
                if not items_new:
                    tk.Label(body, text="  — aucun élément", font=FSM,
                             fg=P["dim"], bg=P["card"], anchor="w").pack(fill=tk.X)

        # Sections
        section("Trivia",     "📝", rv.get("trivia", ""),
                text_mode=True)
        section("Awards",     "🏆", rv.get("awards", []),
                items_old=db.get("awards", []))
        section("Tatouages",  "🎨", rv.get("tattoos", []),
                items_old=[])
        section("Piercings",  "💉", rv.get("piercings", []),
                items_old=[])
        section("Tags",       "🏷️", rv.get("tags", []),
                items_old=db.get("tags", []))

        # URLs : dict → liste de strings
        urls_new = list((rv.get("urls") or {}).keys())
        urls_old = db.get("urls", [])
        section("URLs",       "🔗", urls_new, items_old=urls_old)

        # Bio
        bio = (self.bio_result or {}).get("bio", "")
        section("Biographie", "✍️", bio, text_mode=True)

        # Séparateur + info DB
        tk.Frame(parent, bg=P["border"], height=1).pack(fill=tk.X, padx=6, pady=8)

        info = tk.Frame(parent, bg=P["card"], padx=10, pady=8)
        info.pack(fill=tk.X, padx=6, pady=2)
        tk.Label(info, text="ℹ️  Champs qui seront mis à jour dans Stash :",
                 font=FH3, fg=P["muted"], bg=P["card"]).pack(anchor="w")
        fields = []
        if rv.get("trivia"):           fields.append("details (trivia)")
        if rv.get("awards"):           fields.append("custom_fields (awards)")
        if rv.get("tattoos"):          fields.append("tattoos")
        if rv.get("piercings"):        fields.append("piercings")
        if rv.get("tags"):             fields.append("tags")
        if rv.get("urls"):             fields.append("performer_urls")
        if (self.bio_result or {}).get("bio"): fields.append("details (bio)")
        for f in fields:
            tk.Label(info, text=f"  • {f}", font=FSM,
                     fg=P["text"], bg=P["card"]).pack(anchor="w")

    # ── Panneau droit : Bio finale ─────────────────────────────────────────────

    def _build_bio_panel(self, parent):
        panel = tk.Frame(parent, bg=P["surface"])
        panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        _hdr(panel, "✍️ Biographie finale (éditable)")

        # Zone texte
        txt_f = tk.Frame(panel, bg=P["bio_bg"])
        txt_f.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 0))

        self._txt_bio = tk.Text(
            txt_f, wrap=tk.WORD, font=("Segoe UI", 10),
            bg=P["bio_bg"], fg=P["text"],
            insertbackground=P["text"],
            relief=tk.FLAT, padx=14, pady=12,
            undo=True,
        )
        sb = ttk.Scrollbar(txt_f, command=self._txt_bio.yview)
        self._txt_bio.configure(yscrollcommand=sb.set)
        self._txt_bio.bind("<KeyRelease>", self._update_char)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._txt_bio.pack(fill=tk.BOTH, expand=True)

        # Barre sous l'éditeur
        bio_bar = tk.Frame(panel, bg=P["surface"], pady=5)
        bio_bar.pack(fill=tk.X, padx=4)

        self._char_lbl = tk.Label(bio_bar, text="0 chars",
                                   font=FSM, fg=P["muted"], bg=P["surface"])
        self._char_lbl.pack(side=tk.RIGHT, padx=8)

        _mini_btn(bio_bar, "📋 Copier", self._copy_bio)
        _mini_btn(bio_bar, "🗑 Effacer", self._clear_bio)
        _mini_btn(bio_bar, "↺ Restaurer", self._restore_bio)

    def _populate_bio(self):
        bio = (self.bio_result or {}).get("bio", "")
        self._original_bio = bio
        if bio:
            self._txt_bio.insert("1.0", bio)
        else:
            self._txt_bio.insert("1.0",
                "Aucune biographie générée.\n\n"
                "Vous pouvez en saisir une manuellement ici, ou retourner à l'étape 2.")
        self._update_char()

    def _update_char(self, event=None):
        n = len(self._txt_bio.get("1.0", tk.END).strip())
        color = P["success"] if 2500 <= n <= 4000 else \
                P["warn"]   if 100  <= n < 2500   else P["muted"]
        self._char_lbl.config(text=f"{n} chars", fg=color)

    def _copy_bio(self):
        text = self._txt_bio.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _clear_bio(self):
        if messagebox.askyesno("Effacer", "Effacer la biographie ?"):
            self._txt_bio.delete("1.0", tk.END)
            self._update_char()

    def _restore_bio(self):
        self._txt_bio.delete("1.0", tk.END)
        self._txt_bio.insert("1.0", self._original_bio or "")
        self._update_char()

    # ── Footer ─────────────────────────────────────────────────────────────────

    def _build_footer(self):
        tk.Frame(self, bg=P["border"], height=1).pack(fill=tk.X)
        bar = tk.Frame(self, bg=P["surface"], pady=10)
        bar.pack(fill=tk.X, padx=12)

        _action_btn(bar, "← Retour",  P["dim"],    self._go_back, side=tk.LEFT)
        _action_btn(bar, "✖ Annuler", P["danger"], self._cancel,  side=tk.LEFT, padx=6)

        # Avertissement
        tk.Label(
            bar,
            text="⚠️  L'injection modifie directement la base Stash — opération irréversible",
            font=FSM, fg=P["warn"], bg=P["surface"],
        ).pack(side=tk.LEFT, padx=20)

        _action_btn(bar, "✅  INJECTER DANS STASH",
                    P["success"], self._inject, side=tk.RIGHT, padx=8)

    # ── Injection ──────────────────────────────────────────────────────────────

    def _inject(self):
        bio = self._txt_bio.get("1.0", tk.END).strip()
        rv  = self.review_result or {}

        # Résumé de confirmation
        parts = []
        if rv.get("trivia"):  parts.append(f"Trivia ({len(rv['trivia'])} chars)")
        if rv.get("awards"):  parts.append(f"{len(rv['awards'])} awards")
        if rv.get("tattoos"): parts.append(f"{len(rv['tattoos'])} tatouages")
        if rv.get("piercings"):parts.append(f"{len(rv['piercings'])} piercings")
        if rv.get("tags"):    parts.append(f"{len(rv['tags'])} tags")
        if rv.get("urls"):    parts.append(f"{len(rv['urls'])} URLs")
        if bio:               parts.append(f"Bio ({len(bio)} chars)")

        if not parts:
            messagebox.showwarning("Rien à injecter",
                                   "Aucune donnée sélectionnée.")
            return

        confirm = messagebox.askyesno(
            "Confirmer l'injection",
            f"Vous allez injecter dans Stash :\n\n"
            + "\n".join(f"  • {p}" for p in parts)
            + f"\n\nPerformer : {self.db_data.get('name')}"
            + f"\nID : {self.db_data.get('id')}"
            + "\n\nCette action est irréversible. Continuer ?",
            icon="warning",
        )
        if not confirm:
            return

        try:
            self._do_injection(rv, bio)
            messagebox.showinfo(
                "✅ Injection réussie",
                f"Les données ont été injectées avec succès dans Stash.\n\n"
                + "\n".join(f"  ✓ {p}" for p in parts),
            )
            self.result = "injected"
            self.destroy()

        except Exception as e:
            messagebox.showerror(
                "Erreur d'injection",
                f"Une erreur est survenue lors de l'injection :\n\n{e}"
            )

    def _do_injection(self, rv: dict, bio: str):
        """Injecte les données dans la DB Stash."""
        from services.db import PerformerDB
        from utils.body_art_parser import parse_body_art

        performer_id = self.db_data.get("id")
        if not performer_id:
            raise ValueError("ID performer manquant")

        db = PerformerDB()
        try:
            updates = {}

            # ── Bio / Details ─────────────────────────────────────────────────
            if bio:
                updates["details"] = bio

            # ── Tatouages ─────────────────────────────────────────────────────
            tattoos = rv.get("tattoos", [])
            if tattoos:
                def _fmt_item(it):
                    pos  = it.get("position", "")
                    desc = it.get("description", "")
                    return f"{pos} ({desc})" if desc else pos
                updates["tattoos"] = "; ".join(_fmt_item(t) for t in tattoos)

            # ── Piercings ─────────────────────────────────────────────────────
            piercings = rv.get("piercings", [])
            if piercings:
                def _fmt_item(it):
                    pos  = it.get("position", "")
                    desc = it.get("description", "")
                    return f"{pos} ({desc})" if desc else pos
                updates["piercings"] = "; ".join(_fmt_item(p) for p in piercings)

            # ── Appliquer updates performer ────────────────────────────────────
            if updates:
                db.update_performer(performer_id, updates)

            # ── Tags ──────────────────────────────────────────────────────────
            tags = rv.get("tags", [])
            if tags:
                db.update_performer_tags(performer_id, tags)

            # ── URLs ──────────────────────────────────────────────────────────
            urls = rv.get("urls", {})
            if urls:
                url_list = list(urls.values())
                db.update_performer_urls(performer_id, url_list)

            # ── Awards & Trivia → custom fields ───────────────────────────────
            custom = []
            if rv.get("awards"):
                for a in rv["awards"]:
                    custom.append({"type": "award", "value": a})
            if rv.get("trivia"):
                custom.append({"type": "trivia", "value": rv["trivia"]})
            if custom:
                try:
                    from utils.customfield_utils import inject_custom_fields
                    inject_custom_fields(db, performer_id, custom)
                except Exception as e:
                    print(f"[Injection] Warning custom fields : {e}")

        finally:
            db.close()

    def _go_back(self):
        self.result = None
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# ── Helpers ────────────────────────────────────────────────────────────────────

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


def _hdr(parent, title):
    f = tk.Frame(parent, bg="#2c2c4a", pady=7)
    f.pack(fill=tk.X)
    tk.Label(f, text=f"  {title}", font=("Segoe UI", 11, "bold"),
             fg="#e8e8f5", bg="#2c2c4a", anchor="w").pack(side=tk.LEFT, padx=8)
    tk.Frame(parent, bg="#3a3a58", height=1).pack(fill=tk.X)


def _mini_btn(parent, text, cmd):
    b = tk.Button(parent, text=text, command=cmd,
                  font=("Segoe UI", 8), bg="#2c2c4a", fg="#e8e8f5",
                  relief=tk.FLAT, padx=8, pady=3, cursor="hand2",
                  activebackground="#3a3a58")
    b.pack(side=tk.LEFT, padx=3)


def _action_btn(parent, text, bg, cmd, side=tk.RIGHT, padx=6):
    b = tk.Button(parent, text=text, command=cmd,
                  font=("Segoe UI", 9, "bold"), bg=bg, fg="white",
                  relief=tk.FLAT, padx=16, pady=8, cursor="hand2",
                  activebackground=bg, activeforeground="white")
    b.pack(side=side, padx=padx)
