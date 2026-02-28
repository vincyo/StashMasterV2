import tkinter as tk
from tkinter import ttk, messagebox
import threading

from services.db import GroupDB
from services.group_phase2_scraper import GroupPhase2ScraperService
from services.group_phase2_merger import GroupPhase2Merger

STATUS_ICONS = {
    "new":         "🟢",
    "partial":     "🟠",
    "already_present": "🔵",
    "no_match":    "⚪",
}

class GroupPhase2Frame(ttk.Frame):
    def __init__(self, parent, controller, group_id, group_data, scenes_data):
        super().__init__(parent)
        self.controller = controller
        self.group_id = group_id
        self._group_data = group_data # Données Group déjà scrapées/fusionnées Phase 1
        self._scenes_data = scenes_data # Liste des scènes Stash du Group
        self._merged_scene_urls = [] # Résultat de la fusion Phase 2

        self.scene_checkboxes = [] # Pour cocher les URLs à injecter

        self.create_ui()
        self._run_phase2()

    def create_ui(self):
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(header_frame, text=f"Group ID: {self.group_id} — Phase 2: URLs Scènes",
                  font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(header_frame, text="Retour Phase 1",
                   command=lambda: self.controller.goto_phase1()).pack(side=tk.RIGHT)

        # Progress bar (similaire à Performer Phase 2)
        self.progress_frame = ttk.Frame(self)
        self.progress_label = ttk.Label(self.progress_frame, text="", 
                                        font=("Segoe UI", 9, "italic"))
        self.progress_label.pack(side=tk.LEFT, padx=10)
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="indeterminate", length=200)
        self.progress_bar.pack(side=tk.LEFT, padx=5)

        # Zone principale scrollable pour les scènes
        self.main_canvas = tk.Canvas(self, highlightthickness=0)
        self.main_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.main_canvas.yview)
        self.main_scrollable_frame = ttk.Frame(self.main_canvas)

        self.main_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(
                scrollregion=self.main_canvas.bbox("all")
            )
        )
        self.main_canvas_window = self.main_canvas.create_window((0, 0), window=self.main_scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        
        # Mousewheel scrolling
        self.main_canvas.bind_all("<MouseWheel>",
                             lambda e: self.main_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        
        # Resize canvas window width to match canvas width
        self.main_canvas.bind("<Configure>",
                         lambda e: self.main_canvas.itemconfig(self.main_canvas_window, width=e.width))


        self.main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.main_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Boutons d'action
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(action_frame, text="✔ Injecter sélectionnées", command=self._inject).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Tout sélectionner", command=self._select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Désélectionner tout", command=self._deselect_all).pack(side=tk.LEFT, padx=5)

    def _run_phase2(self):
        self._show_progress("Scraping URLs de scènes...")

        def _do_scraping_and_merge():
            try:
                scraper = GroupPhase2ScraperService()
                
                def update_prog(src, st):
                    self.after(0, lambda: self._update_progress(f"[{src}] {st}"))

                scraped_urls_by_index = scraper.scrape(
                    group_data=self._group_data,
                    progress_callback=update_prog
                )

                merger = GroupPhase2Merger()
                self._merged_scene_urls = merger.merge(
                    self._scenes_data, scraped_urls_by_index)

                self.after(0, self._display_results)

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erreur Phase 2", str(e)))
            finally:
                self.after(0, self._hide_progress)

        threading.Thread(target=_do_scraping_and_merge, daemon=True).start()

    def _display_results(self):
        for widget in self.main_scrollable_frame.winfo_children():
            widget.destroy()

        if not self._merged_scene_urls:
            ttk.Label(self.main_scrollable_frame, text="Aucune URL de scène trouvée ou fusionnée.",
                      font=("Segoe UI", 10, "italic")).pack(padx=10, pady=10)
            return

        # Headers du tableau
        header_frame = ttk.Frame(self.main_scrollable_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(header_frame, text="", width=4).pack(side=tk.LEFT) # Checkbox
        ttk.Label(header_frame, text="Statut", width=8, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Index", width=6, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Titre Stash", width=40, anchor=tk.W, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Nouvelles URLs", anchor=tk.W, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.scene_checkboxes = []
        for scene_data in self._merged_scene_urls:
            self._build_scene_row(self.main_scrollable_frame, scene_data)

    def _build_scene_row(self, parent_frame, scene_data):
        row_frame = ttk.Frame(parent_frame, padding=2)
        row_frame.pack(fill=tk.X, padx=5, pady=1)

        status_icon = STATUS_ICONS.get(scene_data["status"], "")

        # Cocher par défaut si nouvelles URLs (statut 'new' ou 'partial')
        has_new = bool(scene_data.get("new_urls"))
        var = tk.BooleanVar(value=has_new) 
        self.scene_checkboxes.append((var, scene_data)) # Stocker tuple (var, data)
        
        chk = ttk.Checkbutton(row_frame, variable=var)
        chk.pack(side=tk.LEFT)
        if not has_new:
            chk.config(state=tk.DISABLED)

        ttk.Label(row_frame, text=status_icon, width=4).pack(side=tk.LEFT)
        ttk.Label(row_frame, text=str(scene_data.get("scene_index", "?")), width=6).pack(side=tk.LEFT)
        ttk.Label(row_frame, text=scene_data.get("scene_title", "Sans titre"), width=40, anchor=tk.W).pack(side=tk.LEFT)

        urls_frame = ttk.Frame(row_frame)
        urls_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)

        new_urls = scene_data.get("new_urls", {})
        existing = scene_data.get("existing_urls", [])

        if new_urls:
            for src, url in new_urls.items():
                ttk.Label(urls_frame, text=f"➕ {src.upper()}: {url}", anchor=tk.W, font=("Segoe UI", 8, "bold"), foreground="green").pack(fill=tk.X)
        
        if existing:
            count = len(existing)
            ttk.Label(urls_frame, text=f"Existing: {count} URLs", anchor=tk.W, foreground="gray", font=("Segoe UI", 8)).pack(fill=tk.X)
        
        if not new_urls and not existing:
             ttk.Label(urls_frame, text="—", anchor=tk.W, foreground="gray", font=("Segoe UI", 8)).pack(fill=tk.X)

    def _inject(self):
        selected_urls_to_inject = []
        for var, scene_data in self.scene_checkboxes:
            if var.get():
                for url_src, url_val in scene_data["new_urls"].items():
                    selected_urls_to_inject.append({
                        "scene_id": scene_data["scene_id"],
                        "url": url_val,
                        "source": url_src,
                    })
        
        if not selected_urls_to_inject:
            messagebox.showwarning("Attention", "Aucune URL sélectionnée à injecter.")
            return

        try:
            db = GroupDB()
            # appel à la méthode inject_scene_urls que j'ai ajoutée dans db.py
            db.inject_scene_urls(selected_urls_to_inject) 
            db.close()
            
            messagebox.showinfo("✅ Injection Phase 2", f"{len(selected_urls_to_inject)} URLs de scènes injectées.")

            # Optionnel : Recharger ou fermer
            # self._run_phase2() 

        except Exception as e:
            messagebox.showerror("Erreur injection", str(e))

    def _select_all(self):
        for var, _ in self.scene_checkboxes:
            if str(var['state']) != tk.DISABLED:
                var.set(True)

    def _deselect_all(self):
        for var, _ in self.scene_checkboxes:
            var.set(False)

    def _show_progress(self, message):
        self.progress_frame.pack(fill=tk.X, padx=10, pady=2, before=self.main_canvas)
        self.progress_bar.start(10)
        self.progress_label.config(text=message)

    def _update_progress(self, message):
        self.progress_label.config(text=message)

    def _hide_progress(self):
        self.progress_bar.stop()
        self.progress_frame.pack_forget()
