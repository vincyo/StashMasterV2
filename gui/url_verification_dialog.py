import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import time
import requests
from services.scrapers import HEADERS
from services.url_manager import URLOptimizer

class URLVerificationDialog(tk.Toplevel):
    """
    Interface interactive pour la vérification séquentielle des URLs prioritaires.
    Supporte 2 passes:
    - 1ère passe (4 sources): IAFD, FreeOnes, TheNude, XXXBios
    - Secours (2 sources): Babepedia, Boobpedia

    Important: les URLs des 6 sources sont pré-extraites dès le début.
    """
    
    def __init__(self, parent, url_manager, existing_urls, performer_name, use_fallback_sources=False):
        super().__init__(parent)
        self.url_manager = url_manager
        self.url_optimizer = URLOptimizer()
        self.existing_urls = existing_urls
        self.performer_name = performer_name
        self.final_urls = None
        self.use_fallback_sources = use_fallback_sources
        
        self.title(f"Vérification des URLs - {performer_name}")
        self.geometry("650x500")
        self.transient(parent)
        self.grab_set()
        
        # Centrer
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')
        
        # Main Container
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Fallback Sources Checkbox (at top)
        fallback_frame = ttk.Frame(main_frame)
        fallback_frame.pack(fill="x", pady=(0, 10))
        
        self.fallback_var = tk.BooleanVar(value=use_fallback_sources)
        self.fallback_check = ttk.Checkbutton(
            fallback_frame, 
            text="🔓 Vérifier aussi les sources de secours (Babepedia, Boobpedia)",
            variable=self.fallback_var,
            command=self.on_fallback_toggled
        )
        self.fallback_check.pack(side="left")
        
        ttk.Label(fallback_frame, text="(Par défaut: 4 sources 1ère passe uniquement)", foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=10)

        # Header
        self.header_lbl = ttk.Label(main_frame, text="Démarrage...", font=("Segoe UI", 12, "bold"))
        self.header_lbl.pack(pady=(0, 10))
        
        self.status_lbl = ttk.Label(main_frame, text="Préparation...", font=("Segoe UI", 10))
        self.status_lbl.pack(pady=5)
        
        # URL Input Area
        input_frame = ttk.LabelFrame(main_frame, text="URL Actuelle", padding=10)
        input_frame.pack(fill="x", pady=10)
        
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(input_frame, textvariable=self.url_var, font=("Consolas", 10))
        self.url_entry.pack(fill="x", pady=5)
        
        # Action Buttons for Input
        action_frame = ttk.Frame(input_frame)
        action_frame.pack(fill="x", pady=5)
        
        ttk.Button(action_frame, text="Ouvrir le lien", command=self.open_current_url).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Tester le lien", command=self.test_current_url).pack(side="left", padx=5)
        
        # Info / Feedback
        self.info_lbl = ttk.Label(main_frame, text="", foreground="gray", wraplength=600)
        self.info_lbl.pack(pady=10)
        
        # Navigation Buttons
        nav_frame = ttk.Frame(main_frame)
        nav_frame.pack(side="bottom", fill="x", pady=20)
        
        self.btn_ignore = ttk.Button(nav_frame, text="Ignorer / Passer", command=self.on_ignore)
        self.btn_ignore.pack(side="left")
        
        self.btn_search = ttk.Button(nav_frame, text="🔍 Rechercher Auto", command=self.on_auto_search)
        self.btn_search.pack(side="left", padx=10)
        
        self.btn_confirm = ttk.Button(nav_frame, text="✅ Confirmer & Suivant", command=self.on_confirm)
        self.btn_confirm.pack(side="right")
        
        # Bouton pour fermer sans attendre (visible seulement en fin de processus)
        self.btn_close_now = ttk.Button(nav_frame, text="⏭️ Terminer Maintenant", command=self.force_close)
        # Initialement caché
        
        self.progress = ttk.Progressbar(main_frame, mode="determinate")
        self.progress.pack(side="bottom", fill="x", pady=5)
        
        # State - Initialize based on fallback checkbox
        self.update_active_sources()
        self.current_step_idx = -1
        self.other_urls_buffer = []

        # Pré-extraction des URLs de secours (même si non vérifiées dans le flux)
        self._prefetched_fallback_urls = []
        self._prefetch_done = threading.Event()

        # Start process
        self.after(500, self.start_process)
    
    def update_active_sources(self):
        """Met à jour la liste des sources actives selon le checkbox"""
        if self.fallback_var.get():
            self.active_sources = self.url_manager.PRIMARY_SOURCES + self.url_manager.FALLBACK_SOURCES
        else:
            self.active_sources = self.url_manager.PRIMARY_SOURCES
        
        self.priority_results = [None] * len(self.active_sources)
    
    def on_fallback_toggled(self):
        """Callback quand le checkbox des sources de secours change"""
        # Ne peut être changé qu'avant le démarrage du processus
        if self.current_step_idx >= 0:
            messagebox.showinfo("Info", "Les sources ne peuvent pas être modifiées pendant le processus.")
            self.fallback_var.set(not self.fallback_var.get())  # Restore previous value
            return
        
        self.update_active_sources()

    def start_process(self):
        # Pré-extraire les URLs de secours en arrière-plan, dès le début
        self._start_prefetch_fallback_urls()

        # 1. Sort existing URLs
        self.sorted_slots = [None] * len(self.active_sources)
        self.other_urls_buffer = []
        
        domain_map = {domain: i for i, (domain, _) in enumerate(self.active_sources)}
        
        for url in self.existing_urls:
            url = url.strip()
            if not url: continue
            
            # Simple domain check
            key = self.url_manager.get_domain_key(url)
            idx = domain_map.get(key)
            
            if idx is not None:
                if self.sorted_slots[idx] is None:
                    # Check profile URL if needed? Or accept first one?
                    if self.url_manager.is_profile_url(url, key):
                        self.sorted_slots[idx] = url
                    else:
                        self.other_urls_buffer.append(url)
                else:
                    self.other_urls_buffer.append(url)
            else:
                self.other_urls_buffer.append(url)
        
        self.next_step()

    def _start_prefetch_fallback_urls(self):
        """Pré-extrait Babepedia/Boobpedia au démarrage pour une 2e passe instantanée."""
        performer = (self.performer_name or "").strip()
        if not performer:
            return

        # Ne pré-extrait que les sources de secours déclarées par URLManager
        fallback_domains = [d for (d, _) in getattr(self.url_manager, "FALLBACK_SOURCES", [])]
        if not fallback_domains:
            return

        existing_lower = [u.lower() for u in (self.existing_urls or [])]

        def run():
            prefetched = []
            for domain in fallback_domains:
                if any(domain in u for u in existing_lower):
                    continue
                try:
                    found = self.url_manager.search_url_for_domain(domain, performer)
                    if found:
                        prefetched.append(found)
                except Exception:
                    continue
            # Ne rien faire si la fenêtre est déjà fermée
            if self.winfo_exists():
                self._prefetched_fallback_urls = prefetched
            self._prefetch_done.set()

        threading.Thread(target=run, daemon=True).start()

    def next_step(self):
        self.current_step_idx += 1
        
        if self.current_step_idx >= len(self.active_sources):
            self.finish_process()
            return
            
        domain, scraper = self.active_sources[self.current_step_idx]
        self.header_lbl.config(text=f"Source {self.current_step_idx + 1}/{len(self.active_sources)} : {domain}")
        self.progress["value"] = ((self.current_step_idx) / len(self.active_sources)) * 100
        
        existing = self.sorted_slots[self.current_step_idx]
        
        if existing:
            self.url_var.set(existing)
            self.status_lbl.config(text="URL présente. Validation en cours...", foreground="blue")
            self.info_lbl.config(text="Une URL existe déjà pour ce domaine. Vérification de sa validité...")
            self.test_current_url(auto=True)
        else:
            self.url_var.set("")
            self.status_lbl.config(text="URL manquante.", foreground="orange")
            self.info_lbl.config(text=f"Aucune URL trouvée pour {domain}. Lancement de la recherche automatique...")
            self.on_auto_search()

    def test_current_url(self, auto=False):
        url = self.url_var.get().strip()
        if not url:
            if not auto: messagebox.showwarning("Attention", "Aucune URL à tester.")
            return

        self.set_busy(True)
        def run():
            is_ok = self.url_manager.is_url_reachable(url)
            # Utiliser winfo_exists() pour vérifier que le widget existe encore
            if self.winfo_exists():
                self.after(0, lambda: self.show_test_result(is_ok, auto))
        threading.Thread(target=run, daemon=True).start()

    def show_test_result(self, is_ok, auto):
        self.set_busy(False)
        if is_ok:
            self.status_lbl.config(text="URL Valide (200 OK)", foreground="green")
            self.info_lbl.config(text="Le lien fonctionne correctement. Vous pouvez confirmer.")
        else:
            self.status_lbl.config(text="URL Invalide / inaccessible", foreground="red")
            self.info_lbl.config(text="Le lien ne répond pas. Essayez de rechercher une nouvelle URL.")
            if auto:
                # If auto-check failed on existing URL, suggest search?
                pass

    def on_auto_search(self):
        domain, _ = self.active_sources[self.current_step_idx]
        self.set_busy(True)
        self.status_lbl.config(text=f"Recherche sur {domain}...", foreground="blue")
        
        def run():
            found = self.url_manager.search_url_for_domain(domain, self.performer_name)
            # Utiliser winfo_exists() pour vérifier que le widget existe encore
            if self.winfo_exists():
                self.after(0, lambda: self.show_search_result(found))
            
        threading.Thread(target=run, daemon=True).start()

    def show_search_result(self, found_url):
        self.set_busy(False)
        if found_url:
            self.url_var.set(found_url)
            self.status_lbl.config(text="URL trouvée !", foreground="green")
            self.info_lbl.config(text=f"Trouvé : {found_url}\nVeuillez confirmer si cela correspond au profil.")
            # Auto-test validity?
            self.test_current_url(auto=True)
        else:
            self.status_lbl.config(text="Aucun résultat.", foreground="red")
            self.info_lbl.config(text="La recherche automatique n'a rien donné. Vous pouvez entrer une URL manuellement ou passer.")

    def on_confirm(self):
        url = self.url_var.get().strip()
        # Allow empty confirmation? Means "None"
        self.priority_results[self.current_step_idx] = url if url else None
        self.next_step()

    def on_ignore(self):
        self.priority_results[self.current_step_idx] = None
        self.next_step()

    def open_current_url(self):
        url = self.url_var.get().strip()
        if url: webbrowser.open(url)
    
    def force_close(self):
        """Ferme immédiatement sans attendre la validation des URLs secondaires"""
        # Attendre un court instant la pré-extraction (meilleure chance d'avoir 6 URLs)
        try:
            self._prefetch_done.wait(timeout=1.5)
        except Exception:
            pass

        # Construct final list avec ce qu'on a déjà
        final_list = []
        for u in self.priority_results:
            if u: final_list.append(u)

        # Ajouter les URLs de secours pré-extraites (si absentes)
        seen = set(final_list)
        for u in getattr(self, "_prefetched_fallback_urls", []) or []:
            if u and u not in seen:
                final_list.append(u)
                seen.add(u)

        # Ajouter les URLs secondaires sans validation (trop lent)
        for u in self.other_urls_buffer:
            if u not in seen:
                final_list.append(u)
                seen.add(u)
        
        # Optimisation et tri
        final_list = self.url_optimizer.get_top_urls(final_list, limit=50, performer_name=self.performer_name)
        self.final_urls = final_list
        self.use_fallback_sources = self.fallback_var.get()  # Store preference
        print(f"[URLVerificationDialog] Fermeture forcée - {len(self.final_urls)} URLs optimisées")
        self.destroy()

    def set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.btn_confirm.config(state=state)
        self.btn_search.config(state=state)
        self.btn_ignore.config(state=state)
        self.url_entry.config(state=state)
        if busy:
            self.config(cursor="wait")
        else:
            self.config(cursor="")

    def finish_process(self):
        """Finalise le processus et ferme la fenêtre"""
        # Attendre un court instant la pré-extraction (meilleure chance d'avoir 6 URLs)
        try:
            self._prefetch_done.wait(timeout=1.5)
        except Exception:
            pass

        self.header_lbl.config(text="Finalisation...")
        self.status_lbl.config(text="Construction de la liste finale...", foreground="black")
        self.progress["value"] = 100
        
        print(f"[URLVerificationDialog] Finalisation - URLs prioritaires: {len([u for u in self.priority_results if u])}")
        print(f"[URLVerificationDialog] URLs secondaires: {len(self.other_urls_buffer)}")
        
        # Construct final list: Priorities first, then others (sans validation supplémentaire)
        final_list = []
        seen = set()
        
        # Ajouter les URLs prioritaires validées
        for u in self.priority_results:
            if u and u not in seen:
                final_list.append(u)
                seen.add(u)

        # Ajouter les URLs de secours pré-extraites (même si non vérifiées dans le flux)
        for u in getattr(self, "_prefetched_fallback_urls", []) or []:
            if u and u not in seen:
                final_list.append(u)
                seen.add(u)
        
        # Ajouter les URLs secondaires (sans re-validation pour éviter les blocages)
        # Les sources vérifiées dans le flux + la pré-extraction suffisent
        for u in self.other_urls_buffer:
            if u not in seen:
                final_list.append(u)
                seen.add(u)
                if len(final_list) >= 100:  # Limite temporaire haute avant optimisation
                    break
        
        # Application de l'optimisation : nettoyage, déduplication, tri par priorité
        print(f"[URLVerificationDialog] Avant optimisation: {len(final_list)} URLs")
        final_list = self.url_optimizer.get_top_urls(final_list, limit=50, performer_name=self.performer_name)
        
        self.final_urls = final_list
        self.use_fallback_sources = self.fallback_var.get()  # Store preference
        print(f"[URLVerificationDialog] Liste finale optimisée: {len(self.final_urls)} URLs")
        
        # Fermeture immédiate
        self.after(100, self.destroy)

