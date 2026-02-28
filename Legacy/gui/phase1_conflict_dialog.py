"""
Phase1ConflictDialog — Dialogue de résolution des conflits Phase 1.
Affiche confirmations, nouveaux et conflits pour chaque champ coché.
"""
import tkinter as tk
from tkinter import ttk


# Code couleur par statut
STATUS_COLORS = {
    "confirmed": "#2ecc71",  # vert
    "new": "#3498db",        # bleu
    "conflict": "#e74c3c",   # rouge
    "empty": "#95a5a6",      # gris
}

STATUS_ICONS = {
    "confirmed": "✅",
    "new": "🆕",
    "conflict": "⚠️",
    "empty": "⬜",
}


class Phase1ConflictDialog(tk.Toplevel):
    """
    Dialogue modal montrant le résultat du scraping Phase 1.
    Pour chaque champ :
    - Confirmé (vert) → DB == source
    - Nouveau (bleu) → DB vide, suggestion disponible
    - Conflit (rouge) → DB ≠ sources → l'utilisateur choisit
    - Vide (gris) → rien trouvé
    """

    def __init__(self, parent, performer_name: str, merge_result: dict, db_mapping: dict):
        super().__init__(parent)
        self.performer_name = performer_name
        self.title(f"🔍 Résultat scraping Phase 1 pour {performer_name}")
        self.merge_result = merge_result
        self.db_mapping = db_mapping
        self.result = None  # Dict final si validé

        self.geometry("800x600")
        self.minsize(750, 500)
        self.transient(parent)
        self.grab_set()

        # Variables de sélection par champ
        self.selections = {}

        self._build_ui()
        self.wait_window()

    def _build_ui(self):
        # ── Compteurs en haut ───────────────────────────────────
        header = ttk.Frame(self, padding=10)
        header.pack(fill=tk.X)

        counts = {"confirmed": 0, "new": 0, "conflict": 0, "empty": 0}
        for info in self.merge_result.values():
            counts[info["status"]] = counts.get(info["status"], 0) + 1

        summary = (
            f"✅ Confirmés: {counts['confirmed']}  |  "
            f"🆕 Nouveaux: {counts['new']}  |  "
            f"⚠️ Conflits: {counts['conflict']}  |  "
            f"⬜ Vides: {counts['empty']}"
        )
        ttk.Label(header, text=summary, font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)

        # ── Zone scrollable ────────────────────────────────────
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        canvas = tk.Canvas(main, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main, orient=tk.VERTICAL, command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── Lignes par champ ───────────────────────────────────
        for field_name, info in self.merge_result.items():
            self._build_field_row(field_name, info)

        # ── Boutons ────────────────────────────────────────────
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="✅ Appliquer et continuer",
                   command=self._apply).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="❌ Annuler",
                   command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _build_field_row(self, field_name: str, info: dict):
        """Construire une ligne pour un champ."""
        status = info["status"]
        db_value = info.get("db_value") or ""
        scraped_values = info.get("scraped_values", {})
        suggestion = info.get("suggestion") or ""

        # Cadre principal du champ
        frame = ttk.Frame(self.scroll_frame, padding=(5, 3))
        frame.pack(fill=tk.X, padx=5, pady=2)

        # Icône + Nom du champ
        icon = STATUS_ICONS.get(status, "")
        ttk.Label(frame, text=f"{icon} {field_name}", width=20, anchor=tk.W,
                  font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        if status == "confirmed":
            # Tout va bien — afficher simplement la valeur
            ttk.Label(frame, text=f"✓ {db_value}",
                      font=("Segoe UI", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.selections[field_name] = tk.StringVar(value=db_value)
            
            # Afficher les sources qui confirment la valeur
            if scraped_values:
                sources = ", ".join(k.upper() for k in scraped_values.keys())
                ttk.Label(frame, text=f"[{sources}]", font=("Segoe UI", 8, "italic")).pack(side=tk.LEFT, padx=5)

        elif status == "empty":
            # Rien trouvé
            ttk.Label(frame, text="(aucune donnée)",
                      font=("Segoe UI", 10, "italic")).pack(side=tk.LEFT)
            self.selections[field_name] = tk.StringVar(value="")

        elif status == "new":
            # Nouvelle valeur — proposer la suggestion modifiable
            var = tk.StringVar(value=suggestion)
            self.selections[field_name] = var
            ttk.Label(frame, text="DB: (vide) →",
                      font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT, padx=(0, 5))
            entry = ttk.Entry(frame, textvariable=var, width=50)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            # Source info
            sources = ", ".join(scraped_values.keys())
            ttk.Label(frame, text=f"[{sources}]",
                      font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=5)

        elif status == "conflict":
            # Conflit — radio buttons pour choisir
            self._build_conflict_section(frame, field_name, db_value, scraped_values, suggestion)

    def _build_conflict_section(self, parent, field_name, db_value, scraped_values, suggestion):
        """Construire la section de résolution de conflit."""
        # Sous-frame pour les options
        conflict_frame = ttk.Frame(parent)
        conflict_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        var = tk.StringVar(value=suggestion)
        self.selections[field_name] = var

        # Option 1 : garder la valeur DB
        ttk.Radiobutton(
            conflict_frame,
            text=f"DB: {db_value}",
            variable=var,
            value=db_value
        ).pack(anchor=tk.W)

        # Options : valeurs scrapées
        for source, val in scraped_values.items():
            ttk.Radiobutton(
                conflict_frame,
                text=f"{source.upper()}: {val}",
                variable=var,
                value=val
            ).pack(anchor=tk.W)

    def _apply(self):
        """Collecter les sélections et fermer."""
        self.result = {}
        for field_name, var in self.selections.items():
            val = var.get().strip()
            if val:
                self.result[field_name] = val
        self.destroy()
