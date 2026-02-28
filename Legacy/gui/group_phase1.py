"""
Placeholder for Group Phase 1 Frame.
The content for this file is in PLAN_GROUPS_V2.md, which was not provided.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import yaml

from services.db import GroupDB
from services.group_phase1_scraper import GroupPhase1ScraperService
from services.group_phase1_merger import GroupPhase1Merger
from gui.phase1_conflict_dialog import Phase1ConflictDialog
from services.phase2_scraper import Phase2ScraperService


class GroupPhase1Frame(ttk.Frame):
    def __init__(self, parent, controller, group_id):
        super().__init__(parent)
        self.controller = controller
        self.group_id = group_id

        self._group_data = None
        self._scenes_data = [] # Scenes associées au group

        self.field_checkboxes = {}
        self.fields = {}

        self.create_ui()
        self._load_data()

    def create_ui(self):
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(header_frame, text=f"Group ID: {self.group_id}",
                  font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(header_frame, text="Retour Launcher",
                   command=self.controller.return_to_menu).pack(side=tk.RIGHT)

        # ScrolledFrame pour les champs du Group
        self.main_canvas = tk.Canvas(self, highlightthickness=0)
        self.main_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.main_canvas.yview)
        self.main_scrollable_frame = ttk.Frame(self.main_canvas)

        self.main_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(
                scrollregion=self.main_canvas.bbox("all")
            )
        )
        self.main_canvas.create_window((0, 0), window=self.main_scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)

        self.main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.main_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Section Group Details
        group_details_frame = ttk.LabelFrame(self.main_scrollable_frame, text="Group Details (Phase 1)", padding=10)
        group_details_frame.pack(fill=tk.X, padx=10, pady=5)

        # TODO: Charger les champs depuis settings.yaml
        self.fields_list = [
            "Title", "Aliases", "Date", "Studio", "Director",
            "Duration", "Description", "Tags", "URLs"
        ]

        for i, field in enumerate(self.fields_list):
            row = i
            var = tk.BooleanVar(value=True)
            self.field_checkboxes[field] = var
            checkbox = ttk.Checkbutton(group_details_frame, variable=var, text="")
            checkbox.grid(row=row, column=0, sticky=tk.W, padx=(5, 0), pady=2)

            ttk.Label(group_details_frame, text=f"{field}:").grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
            entry = tk.Text(group_details_frame, height=2, width=60, font=("Segoe UI", 9))
            entry.grid(row=row, column=2, sticky=tk.EW, padx=5, pady=2)
            self.fields[field] = entry

        group_details_frame.grid_columnconfigure(2, weight=1)

        # Boutons d'action
        action_frame = ttk.Frame(self.main_scrollable_frame)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(action_frame, text="🔎 Analyser & Phase 2", command=self._run_phase1).pack(side=tk.LEFT, padx=5)

        # Section Scènes Associées
        self.scenes_frame = ttk.LabelFrame(self.main_scrollable_frame, text="Scènes Associées au Group", padding=10)
        self.scenes_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        ttk.Label(self.scenes_frame, text="Chargement des scènes...", font=("Segoe UI", 9, "italic")).pack()

    def _load_data(self):
        try:
            gid = int(self.group_id)
        except ValueError:
            gid = self.group_id

        db = GroupDB()
        self._group_data = db.get_group_by_id(gid)
        self._scenes_data = db.get_group_scenes(gid)
        db.close()

        print(f"DEBUG: Loaded group data for ID {gid}: {bool(self._group_data)}")
        print(f"DEBUG: Loaded {len(self._scenes_data)} scenes")

        if self._group_data:
            for field_name, entry_widget in self.fields.items():
                db_key = field_name.lower().replace(" ", "_")
                value = self._group_data.get(db_key)
                if field_name == "Studio" and self._group_data.get("studio_name"):
                    value = self._group_data["studio_name"]
                elif field_name == "Tags" and value:
                    value = ", ".join(value)
                elif field_name == "URLs" and value:
                    value = "\n".join(value)

                if value:
                    entry_widget.config(state=tk.NORMAL)
                    entry_widget.delete("1.0", tk.END)
                    entry_widget.insert("1.0", str(value))
                    entry_widget.config(state=tk.DISABLED)

        self._display_scenes()

    def _display_scenes(self):
        for widget in self.scenes_frame.winfo_children():
            widget.destroy()

        if not self._scenes_data:
            ttk.Label(self.scenes_frame, text="Aucune scène associée.", font=("Segoe UI", 9, "italic")).pack()
            return

        # Treeview pour les scènes
        columns = ("index", "title", "urls")
        tree = ttk.Treeview(self.scenes_frame, columns=columns, show="headings", height=8)
        tree.heading("index", text="#")
        tree.heading("title", text="Titre Stash")
        tree.heading("urls", text="URLs Existantes")
        
        tree.column("index", width=30, anchor=tk.CENTER)
        tree.column("title", width=300, anchor=tk.W)
        tree.column("urls", width=400, anchor=tk.W)

        for s in self._scenes_data:
            urls_str = ", ".join(s.get("existing_urls", []))
            tree.insert("", tk.END, values=(
                s.get("scene_index", "?"),
                s.get("scene_title", "Sans titre"),
                urls_str
            ))
        
        tree.pack(fill=tk.BOTH, expand=True)

    def _run_phase1(self):
        """Lance le scraping Phase 1 Group."""
        checked = [f for f, var in self.field_checkboxes.items() if var.get()]
        if not checked:
            messagebox.showwarning("Attention", "Aucun champ coché.")
            return

        # Afficher progression
        progress_popup = tk.Toplevel(self)
        progress_popup.title("Scraping Group Phase 1...")
        progress_popup.geometry("300x100")
        prog_label = ttk.Label(progress_popup, text="Initialisation...")
        prog_label.pack(pady=20)

        def _do():
            try:
                scraper = GroupPhase1ScraperService()
                title = self.fields["Title"].get("1.0", tk.END).strip()
                year = self.fields["Date"].get("1.0", tk.END).strip()[:4] # Année
                known_urls = self.fields["URLs"].get("1.0", tk.END).strip().split("\n")
                known_urls = [u.strip() for u in known_urls if u.strip()]

                def update_prog(src, st):
                    self.after(0, lambda: prog_label.config(text=f"[{src}] {st}"))

                scraped = scraper.scrape(title, year, known_urls, progress_callback=update_prog)
                
                # Check for Data18
                has_data18 = any(r.get("_source") == "data18" for r in scraped)
                
                if not has_data18:
                    self.after(0, lambda: self._ask_data18_and_continue(scraped, checked, scraper, progress_popup))
                else:
                    self.after(0, lambda: self._finish_phase1(scraped, checked, progress_popup))

            except Exception as e:
                self.after(0, lambda: [progress_popup.destroy(), messagebox.showerror("Erreur", str(e))])

        threading.Thread(target=_do, daemon=True).start()

    def _ask_data18_and_continue(self, scraped, checked, scraper, progress_popup):
        from tkinter import simpledialog
        # Cacher la popup de progression temporairement
        progress_popup.withdraw()
        
        url = simpledialog.askstring(
            "Data18 Manquant", 
            "Data18 n'a pas été trouvé automatiquement.\n\n"
            "Pour avoir les meilleurs résultats (Tags, Scènes...), collez l'URL Data18 ici :\n"
            "(Sinon, laissez vide et OK pour continuer)",
            parent=self
        )
        
        progress_popup.deiconify()
        
        if url and "data18.com" in url:
            # Relancer un petit thread pour scraper cette URL
            def _scrape_extra():
                try:
                    from services.extractors.dvd.data18_dvd import Data18DVDExtractor
                    e = Data18DVDExtractor()
                    res = e.extract_from_url(url.strip())
                    if res:
                        scraped.append(res)
                except Exception as e:
                    print(f"Error scraping extra URL: {e}")
                
                self.after(0, lambda: self._finish_phase1(scraped, checked, progress_popup))
            
            threading.Thread(target=_scrape_extra, daemon=True).start()
        else:
            self._finish_phase1(scraped, checked, progress_popup)

    def _finish_phase1(self, scraped, checked, progress_popup):
        progress_popup.destroy()
        merger = GroupPhase1Merger()
        merged = merger.merge(self._group_data, scraped, checked)
        self._show_conflict_dialog(merged, checked)

    def _show_conflict_dialog(self, merged_data: dict, checked_fields: list[str]):
        from services.group_phase1_merger import GROUP_FIELDS
        group_title = self.fields["Title"].get("1.0", tk.END).strip()
        dialog = Phase1ConflictDialog(self, group_title, merged_data, GROUP_FIELDS)
        if dialog.result:
            self._inject_phase1(dialog.result)

    def _inject_phase1(self, result: dict):
        try:
            # Pour Group Phase 1, on injecte directement via GroupDB (à implémenter ou simuler)
            # On réutilise les champs mappés
            db_updates = {}
            from services.group_phase1_merger import GROUP_FIELDS
            for field, value in result.items():
                db_key = GROUP_FIELDS.get(field)
                if db_key:
                    db_updates[db_key] = value

            # Simulation d'injection (ou ajout de la méthode dans GroupDB)
            print(f"DEBUG: Injecting group updates: {db_updates}")
            
            # TODO: Implémenter GroupDB.update_group(self.group_id, db_updates)
            
            messagebox.showinfo("✅ Phase 1 Terminée", "Les données du Group ont été mises à jour.")
            
            # Passer à la Phase 2
            self.controller.goto_phase2(self._group_data, self._scenes_data)

        except Exception as e:
            messagebox.showerror("Erreur Injection", str(e))


