"""
BioStudioWindow — GUI 2/3 du flux Bio IA
=========================================
Génération de biographie en plein écran.
Gemini (gauche) et Ollama (droite) côte à côte.

Layout :
┌──────────────────────────────────────────────────────────────────────┐
│  HEADER : performer + breadcrumb 2/3                                 │
├──────────────────────────────────────────────────────────────────────┤
│  CONTEXTE PERFORMER (bandeau compact 2 lignes)                       │
├──────────────────────────────────────────────────────────────────────┤
│  ┌── 🤖 Google Gemini ────────┐  ┌── ⚙️ Ollama (local) ────────────┐ │
│  │  [🚀 Générer]  [🔄 Retry] │  │  [⚙️ Affiner]  [⚡ Générer]    │ │
│  │  ─────────────────────── │  │  ─────────────────────────────  │ │
│  │                           │  │                                 │ │
│  │  Zone texte éditable      │  │  Zone texte éditable            │ │
│  │  (résultat Gemini)        │  │  (résultat Ollama)              │ │
│  │                           │  │                                 │ │
│  │  [📋 Copier] [Utiliser →] │  │  [📋 Copier] [Utiliser →]      │ │
│  └───────────────────────────┘  └─────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│  [← Retour]  [Annuler]    Compteurs chars       [→ Valider →]       │
└──────────────────────────────────────────────────────────────────────┘
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import platform

from services.bio_generator import BioGenerator

# ── Palette ────────────────────────────────────────────────────────────────────
P = {
    "bg":         "#13131f",
    "surface":    "#1e1e30",
    "card":       "#22223a",
    "card_hdr":   "#2c2c4a",
    "border":     "#3a3a58",
    "accent":     "#7c6af7",
    "gemini_bg":  "#0d1a2e",
    "gemini_hdr": "#1a2a4a",
    "gemini_acc": "#4a8af0",
    "ollama_bg":  "#1e1204",
    "ollama_hdr": "#2e2010",
    "ollama_acc": "#e8954a",
    "success":    "#4caf7d",
    "danger":     "#c05050",
    "text":       "#e8e8f5",
    "muted":      "#8888aa",
    "dim":        "#55557a",
}

FH1  = ("Segoe UI", 14, "bold")
FH2  = ("Segoe UI", 11, "bold")
FH3  = ("Segoe UI", 9,  "bold")
FB   = ("Segoe UI", 10)
FSM  = ("Segoe UI", 8)
FSMB = ("Segoe UI", 8,  "bold")
FMONO= ("Consolas", 9)


class BioStudioWindow(tk.Toplevel):
    """
    Fenêtre 2/3 : génération de bio via Gemini et/ou Ollama.
    Retourne `result` dict avec 'bio' str, ou None si annulé.
    """
    def __init__(self, parent, db_data, stash_ctx, merged_data,
                 scraped_results, checked_fields, review_result):
        super().__init__(parent)
        self.title("🎨 Studio Bio IA — Étape 2/3")
        self.configure(bg=P["bg"])

        self.db_data         = db_data
        self.stash_ctx       = stash_ctx
        self.merged_data     = merged_data
        self.scraped_results = scraped_results
        self.checked_fields  = checked_fields
        self.review_result   = review_result   # résultat GUI 1
        self.result          = None            # {'bio': str}

        self._bio_gen  = BioGenerator()
        self._ctx      = None
        self._busy_g   = False   # Gemini en cours
        self._busy_o   = False   # Ollama en cours

        _fullscreen(self)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._prepare_context()

        self.bind("<Escape>", lambda _: self._cancel())
        self.wait_window()

    # ── Contexte IA ────────────────────────────────────────────────────────────

    def _prepare_context(self):
        """Construit le contexte IA depuis les données fusionnées + sélections GUI 1."""
        try:
            # Injecter les sélections de la GUI 1 dans merged_data
            md = dict(self.merged_data)
            rv = self.review_result or {}

            if rv.get("awards"):
                md.setdefault("awards", {})["merged"] = rv["awards"]
            if rv.get("tattoos") is not None:
                md.setdefault("tattoos", {})["merged"] = rv["tattoos"]
            if rv.get("piercings") is not None:
                md.setdefault("piercings", {})["merged"] = rv["piercings"]
            if rv.get("urls"):
                md.setdefault("urls", {})["merged"] = rv["urls"]
            if rv.get("trivia"):
                md.setdefault("trivia", {})["suggestion"] = rv["trivia"]
                md["trivia"]["by_source"] = md["trivia"].get("by_source", {})
                md["trivia"]["by_source"]["_user_"] = rv["trivia"]

            all_fields = list(set(self.checked_fields + [
                "Name", "Birthdate", "Country", "Ethnicity",
                "Hair Color", "Eye Color", "Measurements", "Height",
                "Weight", "Fake Tits", "Aliases", "Career Length",
                "Tattoos", "Piercings", "Awards", "URLs", "Details",
            ]))

            self._ctx = self._bio_gen.build_context_from_v2(
                db_data=self.db_data,
                stash_ctx=self.stash_ctx,
                scraped_results=self.scraped_results,
                merged_data=md,
                checked_fields=all_fields,
            )
            self._set_context_banner()
        except Exception as e:
            print(f"[BioStudio] Erreur contexte : {e}")

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_context_banner()
        self._build_studio()
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self, bg=P["accent"])
        hdr.pack(fill=tk.X)
        tk.Frame(hdr, bg="#9a88ff", height=3).pack(fill=tk.X)

        row = tk.Frame(hdr, bg=P["accent"], pady=7)
        row.pack(fill=tk.X, padx=12)

        tk.Label(row, text="🎨", font=("Segoe UI", 18),
                 fg="white", bg=P["accent"]).pack(side=tk.LEFT, padx=(0, 8))

        name = self.db_data.get("name", "Performer inconnu")
        tk.Label(row, text=f"Studio Bio IA — {name}",
                 font=FH1, fg="white", bg=P["accent"]).pack(side=tk.LEFT)

        # Breadcrumb
        bc = tk.Frame(row, bg=P["accent"])
        bc.pack(side=tk.RIGHT, padx=12)
        for num, lbl, active in [("1","Données",False),("2","Bio IA",True),("3","Valider",False)]:
            bg = "#5a48c8" if active else P["accent"]
            fg = "white"   if active else "#9980cc"
            tk.Label(bc, text=f" {num} ", font=FSMB, fg=fg,
                     bg=bg, padx=6, pady=3).pack(side=tk.LEFT, padx=1)
            tk.Label(bc, text=lbl, font=FSM, fg=fg,
                     bg=P["accent"]).pack(side=tk.LEFT, padx=(0,8))

    def _build_context_banner(self):
        """Bandeau compact montrant le contexte performer."""
        self._banner_frame = tk.Frame(self, bg=P["surface"], pady=4)
        self._banner_frame.pack(fill=tk.X)
        tk.Frame(self, bg=P["border"], height=1).pack(fill=tk.X)

        self._banner_inner = tk.Frame(self._banner_frame, bg=P["surface"])
        self._banner_inner.pack(fill=tk.X, padx=12)

    def _set_context_banner(self):
        """Remplit le bandeau contexte une fois le contexte chargé."""
        for w in self._banner_inner.winfo_children():
            w.destroy()
        if not self._ctx:
            return

        db  = self.db_data
        ctx = self._ctx

        def pill(label, value, color=None):
            if not value:
                return
            f = tk.Frame(self._banner_inner, bg=P["card_hdr"])
            f.pack(side=tk.LEFT, padx=3, pady=2)
            tk.Label(f, text=f" {label} ", font=FSMB,
                     fg=P["muted"], bg=P["card_hdr"]).pack(side=tk.LEFT)
            tk.Label(f, text=f" {str(value)[:40]} ", font=FSM,
                     fg=color or P["text"], bg=P["card"]).pack(side=tk.LEFT)

        pill("👤", ctx.get("name"))
        pill("🎂", ctx.get("birthdate"))
        pill("🌍", ctx.get("country"))
        pill("👤", ctx.get("ethnicity"))
        pill("💇", ctx.get("hair_color"))
        pill("👁",  ctx.get("eye_color"))
        pill("📐", ctx.get("measurements"))
        pill("🎬", f"{ctx.get('scene_count',0)} scènes", P["gemini_acc"])
        pill("🏢", ", ".join(ctx.get("studios",[])[:3]))
        pill("🏆", f"{len(ctx.get('awards_fr',[]))} awards",
             P["ollama_acc"] if ctx.get("awards_fr") else None)

        tk.Frame(self, bg=P["border"], height=1).pack(fill=tk.X)

    def _build_studio(self):
        """Zone centrale : deux panneaux côte à côte."""
        studio = tk.Frame(self, bg=P["bg"])
        studio.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        studio.grid_columnconfigure(0, weight=1)
        studio.grid_columnconfigure(1, weight=1)
        studio.grid_rowconfigure(0, weight=1)

        self._build_gemini_panel(studio)
        self._build_ollama_panel(studio)

    # ── Panneau Gemini ─────────────────────────────────────────────────────────

    def _build_gemini_panel(self, parent):
        panel = tk.Frame(parent, bg=P["gemini_hdr"], bd=0)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # En-tête Gemini
        ghdr = tk.Frame(panel, bg=P["gemini_acc"], pady=8)
        ghdr.pack(fill=tk.X)
        tk.Label(ghdr, text="  🤖  Google Gemini",
                 font=FH2, fg="white", bg=P["gemini_acc"]).pack(side=tk.LEFT, padx=8)
        self._gemini_status = tk.Label(ghdr, text="Prêt",
                                        font=FSM, fg="#cce", bg=P["gemini_acc"])
        self._gemini_status.pack(side=tk.RIGHT, padx=8)
        self._gemini_progress = ttk.Progressbar(ghdr, mode="indeterminate", length=100)
        self._gemini_progress.pack(side=tk.RIGHT, padx=4)

        # Boutons
        gbtn = tk.Frame(panel, bg=P["gemini_hdr"], pady=6)
        gbtn.pack(fill=tk.X, padx=8)

        self._btn_gemini_gen = _studio_btn(
            gbtn, "🚀 Générer", P["gemini_acc"],
            self._run_gemini
        )
        self._btn_gemini_retry = _studio_btn(
            gbtn, "🔄 Régénérer", P["card_hdr"],
            self._run_gemini, state=tk.DISABLED
        )
        self._gemini_char_lbl = tk.Label(
            gbtn, text="", font=FSM, fg=P["muted"], bg=P["gemini_hdr"]
        )
        self._gemini_char_lbl.pack(side=tk.RIGHT, padx=8)

        tk.Frame(panel, bg=P["gemini_acc"], height=2).pack(fill=tk.X)

        # Zone texte
        txt_f = tk.Frame(panel, bg=P["gemini_bg"])
        txt_f.pack(fill=tk.BOTH, expand=True)

        self._txt_gemini = tk.Text(
            txt_f, wrap=tk.WORD, font=FB,
            bg=P["gemini_bg"], fg=P["text"],
            insertbackground=P["text"],
            relief=tk.FLAT, padx=12, pady=10,
            undo=True,
        )
        sb = ttk.Scrollbar(txt_f, command=self._txt_gemini.yview)
        self._txt_gemini.configure(yscrollcommand=sb.set)
        self._txt_gemini.bind("<KeyRelease>",
                              lambda e: self._update_char(self._txt_gemini,
                                                          self._gemini_char_lbl))
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._txt_gemini.pack(fill=tk.BOTH, expand=True)
        self._txt_gemini.insert("1.0",
            "💡 Cliquez sur [🚀 Générer] pour créer une biographie via Google Gemini.\n\n"
            "Le résultat sera directement éditable ici.")

        # Footer panneau
        gfoot = tk.Frame(panel, bg=P["gemini_hdr"], pady=6)
        gfoot.pack(fill=tk.X, padx=8)
        _studio_btn(gfoot, "📋 Copier",
                    P["card_hdr"], lambda: self._copy(self._txt_gemini))
        _studio_btn(gfoot, "→ Utiliser cette bio",
                    P["success"],  lambda: self._use_bio(self._txt_gemini))

    # ── Panneau Ollama ─────────────────────────────────────────────────────────

    def _build_ollama_panel(self, parent):
        panel = tk.Frame(parent, bg=P["ollama_hdr"], bd=0)
        panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # En-tête Ollama
        ohdr = tk.Frame(panel, bg=P["ollama_acc"], pady=8)
        ohdr.pack(fill=tk.X)
        tk.Label(ohdr, text="  ⚙️  Ollama (local)",
                 font=FH2, fg="white", bg=P["ollama_acc"]).pack(side=tk.LEFT, padx=8)
        self._ollama_status = tk.Label(ohdr, text="Prêt",
                                        font=FSM, fg="#ffe", bg=P["ollama_acc"])
        self._ollama_status.pack(side=tk.RIGHT, padx=8)
        self._ollama_progress = ttk.Progressbar(ohdr, mode="indeterminate", length=100)
        self._ollama_progress.pack(side=tk.RIGHT, padx=4)

        # Boutons
        obtn = tk.Frame(panel, bg=P["ollama_hdr"], pady=6)
        obtn.pack(fill=tk.X, padx=8)

        self._btn_ollama_refine = _studio_btn(
            obtn, "⚙️ Affiner Gemini", P["ollama_acc"],
            self._run_ollama_refine
        )
        self._btn_ollama_gen = _studio_btn(
            obtn, "⚡ Générer seul", P["card_hdr"],
            self._run_ollama_gen
        )
        self._ollama_char_lbl = tk.Label(
            obtn, text="", font=FSM, fg=P["muted"], bg=P["ollama_hdr"]
        )
        self._ollama_char_lbl.pack(side=tk.RIGHT, padx=8)

        tk.Frame(panel, bg=P["ollama_acc"], height=2).pack(fill=tk.X)

        # Zone texte
        txt_f = tk.Frame(panel, bg=P["ollama_bg"])
        txt_f.pack(fill=tk.BOTH, expand=True)

        self._txt_ollama = tk.Text(
            txt_f, wrap=tk.WORD, font=FB,
            bg=P["ollama_bg"], fg=P["text"],
            insertbackground=P["text"],
            relief=tk.FLAT, padx=12, pady=10,
            undo=True,
        )
        sb = ttk.Scrollbar(txt_f, command=self._txt_ollama.yview)
        self._txt_ollama.configure(yscrollcommand=sb.set)
        self._txt_ollama.bind("<KeyRelease>",
                              lambda e: self._update_char(self._txt_ollama,
                                                          self._ollama_char_lbl))
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._txt_ollama.pack(fill=tk.BOTH, expand=True)
        self._txt_ollama.insert("1.0",
            "💡 [⚙️ Affiner Gemini] : prend la bio Gemini et la corrige.\n"
            "[⚡ Générer seul] : génère une bio indépendante via Ollama.\n\n"
            "Générez d'abord avec Gemini (gauche) pour obtenir la meilleure qualité.")

        # Footer panneau
        ofoot = tk.Frame(panel, bg=P["ollama_hdr"], pady=6)
        ofoot.pack(fill=tk.X, padx=8)
        _studio_btn(ofoot, "📋 Copier",
                    P["card_hdr"], lambda: self._copy(self._txt_ollama))
        _studio_btn(ofoot, "→ Utiliser cette bio",
                    P["success"],  lambda: self._use_bio(self._txt_ollama))

    # ── Footer principal ───────────────────────────────────────────────────────

    def _build_footer(self):
        tk.Frame(self, bg=P["border"], height=1).pack(fill=tk.X)
        bar = tk.Frame(self, bg=P["surface"], pady=10)
        bar.pack(fill=tk.X, padx=12)

        _action_btn(bar, "← Retour",  P["dim"],     self._go_back, side=tk.LEFT)
        _action_btn(bar, "✖ Annuler", P["danger"],  self._cancel,  side=tk.LEFT, padx=6)

        _action_btn(bar, "→ Valider sans bio",
                    P["card_hdr"], self._proceed_no_bio, side=tk.RIGHT)
        _action_btn(bar, "→ Continuer vers Validation",
                    P["success"], self._proceed_with_best, side=tk.RIGHT, padx=8)

    # ── Génération Gemini ──────────────────────────────────────────────────────

    def _run_gemini(self):
        if self._busy_g:
            return
        if not self._bio_gen.gemini_key:
            messagebox.showerror(
                "Clé Gemini manquante",
                "Fichier .gemini_key introuvable à la racine du projet V2."
            )
            return
        self._set_gemini_busy(True, "Génération en cours…")

        def _worker():
            try:
                bio = self._bio_gen.generate_gemini_bio(self._ctx)
                self.after(0, self._on_gemini_done, bio)
            except Exception as e:
                self.after(0, self._on_gemini_done, None, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_gemini_done(self, bio, error=None):
        self._set_gemini_busy(False)
        if bio:
            self._set_text(self._txt_gemini, bio)
            self._update_char(self._txt_gemini, self._gemini_char_lbl)
            self._gemini_status.config(text=f"✓ {len(bio)} chars")
            self._btn_gemini_retry.config(state=tk.NORMAL)
        else:
            self._gemini_status.config(text="✗ Échec")
            msg = f"Génération Gemini échouée.\n{error or ''}"
            messagebox.showwarning("Gemini", msg)

    def _set_gemini_busy(self, busy, msg=""):
        self._busy_g = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self._btn_gemini_gen.config(state=state)
        if busy:
            self._gemini_progress.start(10)
            self._gemini_status.config(text=msg)
        else:
            self._gemini_progress.stop()

    # ── Génération Ollama ──────────────────────────────────────────────────────

    def _run_ollama_refine(self):
        """Affine la bio Gemini."""
        base = self._txt_gemini.get("1.0", tk.END).strip()
        if len(base) < 100:
            messagebox.showinfo("Ollama", "Générez d'abord une bio avec Gemini.")
            return
        self._run_ollama(base_bio=base)

    def _run_ollama_gen(self):
        """Génère indépendamment."""
        self._run_ollama(base_bio=None)

    def _run_ollama(self, base_bio=None):
        if self._busy_o:
            return
        self._set_ollama_busy(True, "Ollama en cours…")

        def _worker():
            try:
                bio = self._bio_gen.generate_ollama_bio(
                    self._ctx, base_bio=base_bio
                )
                self.after(0, self._on_ollama_done, bio)
            except Exception as e:
                self.after(0, self._on_ollama_done, None, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_ollama_done(self, bio, error=None):
        self._set_ollama_busy(False)
        if bio:
            self._set_text(self._txt_ollama, bio)
            self._update_char(self._txt_ollama, self._ollama_char_lbl)
            self._ollama_status.config(text=f"✓ {len(bio)} chars")
        else:
            self._ollama_status.config(text="✗ Échec")
            messagebox.showwarning(
                "Ollama",
                "Génération Ollama échouée.\n"
                "Vérifiez que le serveur Ollama est lancé (ollama serve).\n"
                f"{error or ''}"
            )

    def _set_ollama_busy(self, busy, msg=""):
        self._busy_o = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self._btn_ollama_refine.config(state=state)
        self._btn_ollama_gen.config(state=state)
        if busy:
            self._ollama_progress.start(10)
            self._ollama_status.config(text=msg)
        else:
            self._ollama_progress.stop()

    # ── Actions ────────────────────────────────────────────────────────────────

    def _set_text(self, widget, text):
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)

    def _update_char(self, widget, lbl):
        n = len(widget.get("1.0", tk.END).strip())
        color = P["success"] if 2500 <= n <= 4000 else P["muted"]
        lbl.config(text=f"{n} chars", fg=color)

    def _copy(self, widget):
        text = widget.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _use_bio(self, widget):
        """Sélectionne cette bio et passe à la validation."""
        bio = widget.get("1.0", tk.END).strip()
        if len(bio) < 100:
            messagebox.showwarning("Bio trop courte",
                                   "La biographie est vide ou trop courte.")
            return
        self.result = {"bio": bio}
        self.destroy()

    def _proceed_with_best(self):
        """Choisit la bio la plus longue disponible."""
        gemini = self._txt_gemini.get("1.0", tk.END).strip()
        ollama = self._txt_ollama.get("1.0", tk.END).strip()

        best = ""
        if len(gemini) > 200:
            best = gemini
        if len(ollama) > 200:
            # Prendre la plus longue (souvent Ollama affine mieux)
            if len(ollama) > len(best):
                best = ollama

        if not best:
            messagebox.showwarning("Aucune bio",
                                   "Générez d'abord une biographie.")
            return
        self.result = {"bio": best}
        self.destroy()

    def _proceed_no_bio(self):
        self.result = {"bio": ""}
        self.destroy()

    def _go_back(self):
        """Retourne à GUI 1 sans résultat."""
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


def _studio_btn(parent, text, bg, cmd, state=tk.NORMAL):
    b = tk.Button(
        parent, text=text, command=cmd, state=state,
        font=FH3, bg=bg, fg="white",
        relief=tk.FLAT, padx=10, pady=5, cursor="hand2",
        activebackground=bg, activeforeground="white",
    )
    b.pack(side=tk.LEFT, padx=4)
    return b


def _action_btn(parent, text, bg, cmd, side=tk.RIGHT, padx=6):
    b = tk.Button(
        parent, text=text, command=cmd,
        font=FH3, bg=bg, fg="white",
        relief=tk.FLAT, padx=16, pady=8, cursor="hand2",
        activebackground=bg, activeforeground="white",
    )
    b.pack(side=side, padx=padx)
