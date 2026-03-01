"""
BioWizard v2 — Interface unique de génération de biographies IA.

Architecture : tout-en-un (requête + résultat dans la même fenêtre)
┌─────────────────────────────────────────────────────────────────┐
│  HEADER : nom du performer + barre de progression               │
├────────────────────────┬────────────────────────────────────────┤
│  PANNEAU GAUCHE        │  PANNEAU DROIT                         │
│  Contexte / Prompt     │  Biographie générée (éditable)         │
│  (lecture seule)       │                                        │
│                        │                                        │
├────────────────────────┴────────────────────────────────────────┤
│  BARRE D'ACTIONS : [Gemini] [Ollama] [Copier] [Valider]         │
└─────────────────────────────────────────────────────────────────┘

Améliorations v2 :
- Plus de 3 tabs → interface unifiée visible d'un coup
- Aperçu du prompt envoyé à l'IA (panneau gauche)
- Résultat éditable directement (panneau droit)
- Boutons Gemini et Ollama toujours accessibles
- Statut inline (pas de popup de progression séparée)
- Compteur de caractères sur la bio
- Bouton "Copier" pour presse-papier
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading

from services.bio_generator import BioGenerator

# ── Couleurs & typo ────────────────────────────────────────────────────────────
FONT_MONO   = ("Consolas", 9)
FONT_BODY   = ("Segoe UI", 10)
FONT_TITLE  = ("Segoe UI", 13, "bold")
FONT_SMALL  = ("Segoe UI", 8, "italic")

CLR_BG      = "#1e1e2e"   # fond principal
CLR_SURFACE = "#2a2a3d"   # panneaux
CLR_BORDER  = "#3d3d5c"
CLR_ACCENT  = "#7c6af7"   # violet Stash
CLR_SUCCESS = "#4caf80"
CLR_TEXT    = "#e0e0f0"
CLR_MUTED   = "#888aaa"
CLR_PROMPT  = "#1a2a1a"   # fond panneau prompt (vert sombre)
CLR_RESULT  = "#1a1a2e"   # fond panneau résultat


class BioWizard(tk.Toplevel):
    def __init__(
        self,
        parent,
        db_data: dict,
        stash_ctx: dict,
        merged_data: dict,
        scraped_results: list,
        checked_fields: list,
    ):
        super().__init__(parent)
        self.title("🧙 Assistant Biographie IA")
        self.geometry("1280x820")
        self.minsize(900, 600)
        self.configure(bg=CLR_BG)

        self.transient(parent)
        self.grab_set()

        # Données
        self.db_data        = db_data
        self.stash_ctx      = stash_ctx
        self.merged_data    = merged_data
        self.scraped_results = scraped_results
        self.checked_fields = checked_fields
        self.final_bio      = None
        
        # Bio existante (si disponible)
        self.existing_bio = db_data.get("details", "").strip()

        # État interne
        self._bio_gen   = BioGenerator()
        self._ctx       = None          # contexte construit une fois
        self._is_busy   = False

        self._build_ui()
        self._load_context()            # Charge le contexte au démarrage
        self.wait_window()

    # ── Construction UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_main_panels()
        self._build_action_bar()
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=CLR_ACCENT, pady=8)
        hdr.pack(fill=tk.X)

        performer = self.db_data.get("name", "Performer inconnu")
        tk.Label(
            hdr,
            text=f"  🧙 Biographie IA — {performer}",
            font=FONT_TITLE,
            bg=CLR_ACCENT,
            fg="white",
        ).pack(side=tk.LEFT, padx=10)

        # Indicateur de progression (spin)
        self._status_var = tk.StringVar(value="Prêt")
        self._status_lbl = tk.Label(
            hdr,
            textvariable=self._status_var,
            font=FONT_SMALL,
            bg=CLR_ACCENT,
            fg="#ddd",
        )
        self._status_lbl.pack(side=tk.RIGHT, padx=15)

        self._progress = ttk.Progressbar(hdr, mode="indeterminate", length=140)
        self._progress.pack(side=tk.RIGHT, padx=5)

    def _build_main_panels(self):
        paned = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            bg=CLR_BORDER,
            sashwidth=5,
            sashrelief=tk.FLAT,
        )
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # ── Panneau gauche : Contexte / Prompt ───────────────────────────────
        left = tk.Frame(paned, bg=CLR_SURFACE, bd=1, relief=tk.FLAT)
        paned.add(left, minsize=360, width=440)

        tk.Label(
            left,
            text="📋 Contexte envoyé à l'IA",
            font=("Segoe UI", 10, "bold"),
            bg=CLR_SURFACE,
            fg=CLR_TEXT,
            anchor="w",
            padx=8,
            pady=4,
        ).pack(fill=tk.X)

        tk.Frame(left, bg=CLR_BORDER, height=1).pack(fill=tk.X)

        prompt_frame = tk.Frame(left, bg=CLR_PROMPT)
        prompt_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._txt_prompt = tk.Text(
            prompt_frame,
            wrap=tk.WORD,
            font=FONT_MONO,
            bg=CLR_PROMPT,
            fg="#a8d8a8",
            insertbackground=CLR_TEXT,
            selectbackground=CLR_ACCENT,
            relief=tk.FLAT,
            state=tk.DISABLED,
            padx=6,
            pady=6,
        )
        sb_prompt = ttk.Scrollbar(prompt_frame, command=self._txt_prompt.yview)
        self._txt_prompt.configure(yscrollcommand=sb_prompt.set)
        sb_prompt.pack(side=tk.RIGHT, fill=tk.Y)
        self._txt_prompt.pack(fill=tk.BOTH, expand=True)

        # ── Panneau droit : Bio générée ───────────────────────────────────────
        right = tk.Frame(paned, bg=CLR_SURFACE, bd=1, relief=tk.FLAT)
        paned.add(right, minsize=400)
        
        # ── Section bio existante (si disponible) ─────────────────────────────
        if self.existing_bio and len(self.existing_bio) > 50:
            existing_frame = tk.Frame(right, bg="#2a2a1a", bd=1, relief=tk.FLAT)
            existing_frame.pack(fill=tk.X, padx=4, pady=4)
            
            exist_header = tk.Frame(existing_frame, bg="#3a3a2a")
            exist_header.pack(fill=tk.X)
            
            tk.Label(
                exist_header,
                text="📝 Bio actuelle en base",
                font=("Segoe UI", 9, "bold"),
                bg="#3a3a2a",
                fg="#d0d0a0",
                anchor="w",
                padx=6,
                pady=3,
            ).pack(side=tk.LEFT)
            
            chars_existing = len(self.existing_bio)
            tk.Label(
                exist_header,
                text=f"{chars_existing} caractères",
                font=FONT_SMALL,
                bg="#3a3a2a",
                fg="#999977",
            ).pack(side=tk.RIGHT, padx=6)
            
            # Texte bio existante (max 3 lignes visible)
            bio_preview = self.existing_bio[:200] + ("..." if len(self.existing_bio) > 200 else "")
            tk.Label(
                existing_frame,
                text=bio_preview,
                font=("Segoe UI", 8),
                bg="#2a2a1a",
                fg="#b0b088",
                anchor="w",
                justify=tk.LEFT,
                wraplength=600,
                padx=8,
                pady=4,
            ).pack(fill=tk.X)
            
            # Boutons d'action pour la bio existante
            exist_btns = tk.Frame(existing_frame, bg="#2a2a1a")
            exist_btns.pack(fill=tk.X, padx=4, pady=4)
            
            btn_mini_style = {
                "font": ("Segoe UI", 8, "bold"),
                "relief": tk.FLAT,
                "cursor": "hand2",
                "padx": 8,
                "pady": 3,
            }
            
            tk.Button(
                exist_btns,
                text="✅ Conserver telle quelle",
                bg="#3a5a3a",
                fg="white",
                activebackground="#2a4a2a",
                command=self._keep_existing_bio,
                **btn_mini_style,
            ).pack(side=tk.LEFT, padx=3)
            
            tk.Button(
                exist_btns,
                text="🔧 Ajuster avec Ollama",
                bg="#3a4a5a",
                fg="white",
                activebackground="#2a3a4a",
                command=self._adjust_existing_bio,
                **btn_mini_style,
            ).pack(side=tk.LEFT, padx=3)
            
            tk.Button(
                exist_btns,
                text="🔀 Fusionner avec nouvelle",
                bg="#5a3a5a",
                fg="white",
                activebackground="#4a2a4a",
                command=self._merge_with_new_bio,
                **btn_mini_style,
            ).pack(side=tk.LEFT, padx=3)
            
            tk.Frame(right, bg=CLR_BORDER, height=1).pack(fill=tk.X, pady=2)

        top_right = tk.Frame(right, bg=CLR_SURFACE)
        top_right.pack(fill=tk.X)

        tk.Label(
            top_right,
            text="✍️ Biographie générée",
            font=("Segoe UI", 10, "bold"),
            bg=CLR_SURFACE,
            fg=CLR_TEXT,
            anchor="w",
            padx=8,
            pady=4,
        ).pack(side=tk.LEFT)

        self._char_var = tk.StringVar(value="0 caractères")
        tk.Label(
            top_right,
            textvariable=self._char_var,
            font=FONT_SMALL,
            bg=CLR_SURFACE,
            fg=CLR_MUTED,
        ).pack(side=tk.RIGHT, padx=8)

        tk.Frame(right, bg=CLR_BORDER, height=1).pack(fill=tk.X)

        result_frame = tk.Frame(right, bg=CLR_RESULT)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._txt_result = tk.Text(
            result_frame,
            wrap=tk.WORD,
            font=FONT_BODY,
            bg=CLR_RESULT,
            fg=CLR_TEXT,
            insertbackground=CLR_TEXT,
            selectbackground=CLR_ACCENT,
            relief=tk.FLAT,
            undo=True,
            padx=8,
            pady=8,
        )
        
        # Message initial selon disponibilité bio existante
        if self.existing_bio and len(self.existing_bio) > 50:
            initial_msg = (
                "💡 Une bio existe déjà en base. Vous pouvez:\n\n"
                "  • La conserver telle quelle (bouton vert ci-dessus)\n"
                "  • L'ajuster avec Ollama (bouton bleu ci-dessus)\n"
                "  • La fusionner avec une nouvelle bio (bouton violet ci-dessus)\n"
                "  • Générer une nouvelle bio complète (boutons en bas)\n\n"
                "Vous pouvez aussi modifier le texte directement dans cette zone après génération."
            )
        else:
            initial_msg = (
                "💡 Cliquez sur [Générer (Gemini)] ou [Générer (Ollama)] pour créer la biographie...\n\n"
                "Vous pouvez modifier le texte directement dans cette zone après la génération."
            )
        
        self._txt_result.insert("1.0", initial_msg)
        sb_result = ttk.Scrollbar(result_frame, command=self._txt_result.yview)
        self._txt_result.configure(yscrollcommand=sb_result.set)
        self._txt_result.bind("<KeyRelease>", self._update_char_count)
        sb_result.pack(side=tk.RIGHT, fill=tk.Y)
        self._txt_result.pack(fill=tk.BOTH, expand=True)

    def _build_action_bar(self):
        bar = tk.Frame(self, bg=CLR_SURFACE, pady=8)
        bar.pack(fill=tk.X, padx=6)

        # Séparateur
        tk.Frame(self, bg=CLR_BORDER, height=1).pack(fill=tk.X, padx=6)

        btn_style = {
            "font": ("Segoe UI", 10, "bold"),
            "relief": tk.FLAT,
            "cursor": "hand2",
            "padx": 14,
            "pady": 6,
        }

        self._btn_gemini = tk.Button(
            bar,
            text="🚀 Générer (Gemini)",
            bg=CLR_ACCENT,
            fg="white",
            activebackground="#6a5af0",
            activeforeground="white",
            command=self._run_gemini,
            **btn_style,
        )
        self._btn_gemini.pack(side=tk.LEFT, padx=6)

        self._btn_ollama = tk.Button(
            bar,
            text="⚙️ Affiner (Ollama)",
            bg="#3a5a7a",
            fg="white",
            activebackground="#2a4a6a",
            activeforeground="white",
            command=self._run_ollama,
            **btn_style,
        )
        self._btn_ollama.pack(side=tk.LEFT, padx=4)

        self._btn_retry = tk.Button(
            bar,
            text="🔄 Régénérer",
            bg="#4a4a6a",
            fg=CLR_TEXT,
            activebackground="#3a3a5a",
            activeforeground="white",
            command=self._run_gemini,
            **btn_style,
        )
        self._btn_retry.pack(side=tk.LEFT, padx=4)

        # Séparateur droite
        tk.Frame(bar, bg=CLR_BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        self._btn_copy = tk.Button(
            bar,
            text="📋 Copier",
            bg="#3a4a3a",
            fg=CLR_TEXT,
            activebackground="#2a3a2a",
            activeforeground="white",
            command=self._copy_to_clipboard,
            **btn_style,
        )
        self._btn_copy.pack(side=tk.LEFT, padx=4)

        self._btn_clear = tk.Button(
            bar,
            text="🗑 Effacer",
            bg="#3a2a2a",
            fg=CLR_TEXT,
            activebackground="#4a2a2a",
            activeforeground="white",
            command=self._clear_result,
            **btn_style,
        )
        self._btn_clear.pack(side=tk.LEFT, padx=4)

        # Valider à droite
        self._btn_validate = tk.Button(
            bar,
            text="✅ Valider & Utiliser",
            bg=CLR_SUCCESS,
            fg="white",
            activebackground="#3a9a6a",
            activeforeground="white",
            command=self._inject_bio,
            **btn_style,
        )
        self._btn_validate.pack(side=tk.RIGHT, padx=6)

        tk.Button(
            bar,
            text="✖ Annuler",
            bg="#5a2a2a",
            fg=CLR_TEXT,
            activebackground="#6a3a3a",
            activeforeground="white",
            command=self.destroy,
            **btn_style,
        ).pack(side=tk.RIGHT, padx=4)

    def _build_statusbar(self):
        sbar = tk.Frame(self, bg="#111120", pady=2)
        sbar.pack(fill=tk.X, side=tk.BOTTOM)

        self._status_detail_var = tk.StringVar(value="")
        tk.Label(
            sbar,
            textvariable=self._status_detail_var,
            font=FONT_SMALL,
            bg="#111120",
            fg=CLR_MUTED,
            anchor="w",
            padx=8,
        ).pack(side=tk.LEFT)

    # ── Chargement du contexte ────────────────────────────────────────────────

    def _load_context(self):
        """Construit le contexte et affiche le prompt dans le panneau gauche."""
        try:
            self._ctx = self._bio_gen.build_context_from_v2(
                self.db_data,
                self.stash_ctx,
                self.scraped_results,
                self.merged_data,
                self.checked_fields,
            )
            prompt_preview = self._bio_gen.preview_prompt(self._ctx)
            self._set_prompt_text(prompt_preview)
            self._set_status("Contexte chargé — prêt à générer")
        except Exception as e:
            self._set_prompt_text(f"Erreur lors du chargement du contexte :\n{e}")
            self._set_status(f"Erreur contexte : {e}", error=True)

    def _set_prompt_text(self, text: str):
        self._txt_prompt.config(state=tk.NORMAL)
        self._txt_prompt.delete("1.0", tk.END)
        self._txt_prompt.insert("1.0", text)
        self._txt_prompt.config(state=tk.DISABLED)

    # ── Génération Gemini ─────────────────────────────────────────────────────

    def _run_gemini(self):
        if self._is_busy:
            return
        if not self._bio_gen.gemini_key:
            messagebox.showerror(
                "Clé Gemini manquante",
                "Aucune clé API Gemini trouvée.\n"
                "Créez le fichier .gemini_key à la racine du projet V2.",
            )
            return

        self._set_busy(True, "Génération Gemini en cours…")

        def _worker():
            try:
                bio = self._bio_gen.generate_gemini_bio(self._ctx)
                self.after(0, self._on_generation_done, bio, "Gemini")
            except Exception as e:
                self.after(0, self._on_generation_error, str(e), "Gemini")

        threading.Thread(target=_worker, daemon=True).start()

    # ── Affinage Ollama ───────────────────────────────────────────────────────

    def _run_ollama(self):
        if self._is_busy:
            return

        current_bio = self._txt_result.get("1.0", tk.END).strip()
        has_content = len(current_bio) > 100

        # Si une bio existe déjà, affiner ; sinon générer de zéro
        base_bio = current_bio if has_content else None

        self._set_busy(True, "Ollama en cours…")

        def _worker():
            try:
                bio = self._bio_gen.generate_ollama_bio(self._ctx, base_bio=base_bio)
                mode = "Ollama (affinage)" if base_bio else "Ollama"
                self.after(0, self._on_generation_done, bio, mode)
            except Exception as e:
                self.after(0, self._on_generation_error, str(e), "Ollama")

        threading.Thread(target=_worker, daemon=True).start()
    
    # ── Actions sur bio existante ─────────────────────────────────────────────
    
    def _keep_existing_bio(self):
        """Copie directement la bio existante dans le panneau de résultat"""
        if not self.existing_bio:
            messagebox.showinfo("Info", "Aucune bio existante trouvée.")
            return
        
        self._set_result_text(self.existing_bio)
        self._set_status("Bio existante chargée — prête à utiliser")
        self._set_detail(f"Bio existante conservée ({len(self.existing_bio)} caractères)")
    
    def _adjust_existing_bio(self):
        """Envoie la bio existante à Ollama pour ajustement/amélioration"""
        if not self.existing_bio:
            messagebox.showinfo("Info", "Aucune bio existante à ajuster.")
            return
        
        if self._is_busy:
            return
        
        self._set_busy(True, "Ajustement Ollama en cours…")
        
        def _worker():
            try:
                # Utilise Ollama en mode affinage sur la bio existante
                bio = self._bio_gen.generate_ollama_bio(self._ctx, base_bio=self.existing_bio)
                self.after(0, self._on_generation_done, bio, "Ollama (ajustement)")
            except Exception as e:
                self.after(0, self._on_generation_error, str(e), "Ollama")
        
        threading.Thread(target=_worker, daemon=True).start()
    
    def _merge_with_new_bio(self):
        """Génère une nouvelle bio puis la fusionne avec l'existante"""
        if not self.existing_bio:
            messagebox.showinfo("Info", "Aucune bio existante à fusionner. Génération normale...")
            self._run_gemini()
            return
        
        if self._is_busy:
            return
        
        if not self._bio_gen.gemini_key:
            messagebox.showerror(
                "Clé Gemini manquante",
                "La fusion nécessite Gemini pour générer la nouvelle bio.\n"
                "Créez le fichier .gemini_key à la racine du projet.",
            )
            return
        
        self._set_busy(True, "Génération + fusion en cours…")
        
        def _worker():
            try:
                # Étape 1: Générer nouvelle bio avec Gemini
                new_bio = self._bio_gen.generate_gemini_bio(self._ctx)
                if not new_bio:
                    self.after(0, self._on_generation_error, "Échec génération nouvelle bio", "Gemini")
                    return
                
                # Étape 2: Créer prompt de fusion
                merge_prompt = f"""Voici deux biographies pour le même artiste. Fusionne-les intelligemment en une seule biographie complète et cohérente.

BIOGRAPHIE EXISTANTE (en base):
{self.existing_bio}

NOUVELLE BIOGRAPHIE (générée):
{new_bio}

Instructions:
1. Fusionne les informations sans redondance
2. Garde les faits les plus précis et récents
3. Conserve la structure en 7 sections avec émojis
4. Privilégie la nouvelle bio pour la structure, mais intègre les faits uniques de l'existante
5. Longueur cible: 2500-3500 caractères

Retourne UNIQUEMENT la biographie fusionnée finale."""
                
                # Étape 3: Envoyer à Gemini pour fusion intelligente
                merged_bio = self._bio_gen._call_gemini(merge_prompt)
                
                if merged_bio:
                    self.after(0, self._on_generation_done, merged_bio, "Gemini (fusion)")
                else:
                    self.after(0, self._on_generation_error, "Échec fusion", "Gemini")
                    
            except Exception as e:
                self.after(0, self._on_generation_error, str(e), "Fusion")
        
        threading.Thread(target=_worker, daemon=True).start()

    # ── Callbacks résultat ────────────────────────────────────────────────────

    def _on_generation_done(self, bio: str | None, source: str):
        self._set_busy(False)
        if bio:
            self._set_result_text(bio)
            nb_chars = len(bio)
            self._set_status(f"✓ Bio générée par {source} — {nb_chars} caractères")
            self._set_detail(f"Source : {source} | {nb_chars} chars | Éditable directement")
        else:
            self._set_status(f"Échec de la génération ({source})", error=True)
            self._set_detail(
                f"Vérifiez la console pour les détails. "
                f"Clé Gemini : {'OK' if self._bio_gen.gemini_key else 'manquante'}"
            )
            messagebox.showwarning(
                f"Échec {source}",
                f"La génération via {source} a échoué.\n"
                "Vérifiez la console pour les détails.",
            )

    def _on_generation_error(self, error: str, source: str):
        self._set_busy(False)
        self._set_status(f"Erreur {source} : {error}", error=True)
        messagebox.showerror(f"Erreur {source}", error)

    def _set_result_text(self, text: str):
        self._txt_result.delete("1.0", tk.END)
        self._txt_result.insert("1.0", text)
        self._update_char_count()

    def _update_char_count(self, event=None):
        content = self._txt_result.get("1.0", tk.END).strip()
        n = len(content)
        color = CLR_SUCCESS if 2500 <= n <= 4000 else CLR_MUTED
        self._char_var.set(f"{n} caractères")
        # Teinte dynamique
        try:
            self._txt_result.master.master.winfo_children()
        except Exception:
            pass

    # ── Actions boutons ───────────────────────────────────────────────────────

    def _copy_to_clipboard(self):
        content = self._txt_result.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self._set_detail("Bio copiée dans le presse-papier ✓")
        else:
            messagebox.showinfo("Presse-papier", "Aucun contenu à copier.")

    def _clear_result(self):
        if messagebox.askyesno("Effacer", "Effacer le contenu du panneau de résultat ?"):
            self._txt_result.delete("1.0", tk.END)
            self._char_var.set("0 caractères")
            self._set_status("Panneau effacé")

    def _inject_bio(self):
        """Stocke la bio finale et ferme le wizard."""
        content = self._txt_result.get("1.0", tk.END).strip()
        if not content or len(content) < 50:
            messagebox.showwarning(
                "Contenu insuffisant",
                "La biographie est vide ou trop courte.\n"
                "Générez d'abord une biographie avant de valider.",
            )
            return
        self.final_bio = content
        self.destroy()

    # ── Utilitaires état ──────────────────────────────────────────────────────

    def _set_busy(self, busy: bool, message: str = ""):
        self._is_busy = busy
        state = tk.DISABLED if busy else tk.NORMAL

        self._btn_gemini.config(state=state)
        self._btn_ollama.config(state=state)
        self._btn_retry.config(state=state)

        if busy:
            self._progress.start(10)
            self._status_var.set(message)
        else:
            self._progress.stop()
            self._status_var.set("Prêt")

    def _set_status(self, message: str, error: bool = False):
        self._status_var.set(message)
        fg = "#ff6060" if error else "#ddd"
        self._status_lbl.config(fg=fg)

    def _set_detail(self, message: str):
        self._status_detail_var.set(message)
