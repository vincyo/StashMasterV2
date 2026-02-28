"""
BioWizard - Fenêtre dédiée à la génération de biographies en 3 étapes.
1. Génération Google Gemini
2. Affinage Ollama
3. Validation et injection
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading

from services.bio_generator import BioGenerator

class BioWizard(tk.Toplevel):
    def __init__(self, parent, db_data, stash_ctx, merged_data, scraped_results, checked_fields):
        super().__init__(parent)
        self.title("Assistant de Génération de Biographie IA")
        self.geometry("1000x750")
        self.minsize(800, 600)

        self.transient(parent)
        self.grab_set()

        # Stockage
        self.db_data = db_data
        self.stash_ctx = stash_ctx
        self.merged_data = merged_data
        self.scraped_results = scraped_results
        self.checked_fields = checked_fields
        self.final_bio = None  # Le résultat final sera stocké ici

        self._build_ui()
        self.wait_window()

    def _build_ui(self):
        # Barre de progression
        self.progress_frame = ttk.Frame(self)
        self.progress_label = ttk.Label(self.progress_frame, text="Prêt", font=("Segoe UI", 9, "italic"))
        self.progress_label.pack(side=tk.LEFT, padx=10)
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="indeterminate", length=200)
        self.progress_bar.pack(side=tk.LEFT, padx=5)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab1_google = ttk.Frame(self.notebook, padding=10)
        self.tab2_ollama = ttk.Frame(self.notebook, padding=10)
        self.tab3_validate = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.tab1_google, text="Étape 1 : Google Gemini")
        self.notebook.add(self.tab2_ollama, text="Étape 2 : Affinage Ollama", state="disabled")
        self.notebook.add(self.tab3_validate, text="Étape 3 : Validation", state="disabled")

        self._create_google_tab()
        self._create_ollama_tab()
        self._create_validate_tab()

    def _create_google_tab(self):
        frame = self.tab1_google
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        action_frame = ttk.Frame(frame)
        action_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 10))
        
        self.btn_gen_gemini = ttk.Button(action_frame, text="🚀 Lancer la génération Gemini", command=self._run_gemini_generation)
        self.btn_gen_gemini.pack(side=tk.LEFT)
        
        self.btn_copy_to_ollama = ttk.Button(action_frame, text="Continuer vers l'étape 2 ➡", state=tk.DISABLED, command=self._copy_to_ollama)
        self.btn_copy_to_ollama.pack(side=tk.LEFT, padx=10)

        self.txt_gemini_result = tk.Text(frame, wrap=tk.WORD, font=("Segoe UI", 10))
        self.txt_gemini_result.grid(row=1, column=0, sticky=tk.NSEW)
        self.txt_gemini_result.insert("1.0", "Cliquez sur 'Lancer la génération' pour créer une biographie avec Google Gemini...")
        self.txt_gemini_result.config(state=tk.DISABLED)

    def _create_ollama_tab(self):
        frame = self.tab2_ollama
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=1)
        
        action_frame = ttk.Frame(frame)
        action_frame.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW, pady=(0, 10))
        self.btn_refine_ollama = ttk.Button(action_frame, text="⚙️ Lancer l'affinage Ollama", command=self._run_ollama_refinement)
        self.btn_refine_ollama.pack(side=tk.LEFT)
        
        self.btn_copy_to_validate = ttk.Button(action_frame, text="Continuer vers la validation ➡", state=tk.DISABLED, command=self._copy_to_validation)
        self.btn_copy_to_validate.pack(side=tk.LEFT, padx=10)

        ttk.Label(frame, text="Biographie de base (Gemini)").grid(row=1, column=0, columnspan=2, sticky=tk.W)
        self.txt_ollama_input = tk.Text(frame, wrap=tk.WORD, height=8, font=("Segoe UI", 10), state=tk.DISABLED, relief=tk.SUNKEN)
        self.txt_ollama_input.grid(row=2, column=0, columnspan=2, sticky=tk.NSEW, pady=(0, 10))

        ttk.Label(frame, text="Biographie affinée (Ollama)").grid(row=3, column=0, columnspan=2, sticky=tk.W)
        self.txt_ollama_result = tk.Text(frame, wrap=tk.WORD, font=("Segoe UI", 10))
        self.txt_ollama_result.grid(row=4, column=0, columnspan=2, sticky=tk.NSEW)

    def _create_validate_tab(self):
        frame = self.tab3_validate
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        action_frame = ttk.Frame(frame)
        action_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 10))
        self.btn_inject = ttk.Button(action_frame, text="✅ Valider et Utiliser cette Bio", command=self._inject_bio)
        self.btn_inject.pack(side=tk.LEFT)

        self.txt_final_bio = tk.Text(frame, wrap=tk.WORD, font=("Segoe UI", 10))
        self.txt_final_bio.grid(row=1, column=0, sticky=tk.NSEW)

    def _run_gemini_generation(self):
        self._show_progress("Génération Gemini en cours...")
        self.btn_gen_gemini.config(state=tk.DISABLED)
        self.btn_copy_to_ollama.config(state=tk.DISABLED)

        def _do_generate():
            try:
                bio_gen = BioGenerator()
                ctx = bio_gen.build_context_from_v2(self.db_data, self.stash_ctx, self.scraped_results, self.merged_data, self.checked_fields)
                gemini_bio = bio_gen.generate_gemini_bio(ctx)

                def _update_ui():
                    self.txt_gemini_result.config(state=tk.NORMAL)
                    self.txt_gemini_result.delete("1.0", tk.END)
                    if gemini_bio:
                        self.txt_gemini_result.insert("1.0", gemini_bio)
                        self.btn_copy_to_ollama.config(state=tk.NORMAL)
                    else:
                        self.txt_gemini_result.insert("1.0", "La génération Gemini a échoué. Vérifiez la console pour les erreurs (clé API, etc.).")
                    self.txt_gemini_result.config(state=tk.DISABLED)
                    self.btn_gen_gemini.config(state=tk.NORMAL)

                self.after(0, _update_ui)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erreur Gemini", str(e)))
            finally:
                self.after(0, self._hide_progress)
        
        threading.Thread(target=_do_generate, daemon=True).start()

    def _copy_to_ollama(self):
        gemini_text = self.txt_gemini_result.get("1.0", tk.END)
        self.txt_ollama_input.config(state=tk.NORMAL)
        self.txt_ollama_input.delete("1.0", tk.END)
        self.txt_ollama_input.insert("1.0", gemini_text)
        self.txt_ollama_input.config(state=tk.DISABLED)
        self.txt_ollama_result.delete("1.0", tk.END) # Clear previous results
        self.notebook.tab(1, state="normal")
        self.notebook.select(self.tab2_ollama)

    def _run_ollama_refinement(self):
        gemini_bio = self.txt_ollama_input.get("1.0", tk.END).strip()
        if not gemini_bio or "échoué" in gemini_bio:
            messagebox.showwarning("Bio de base manquante", "La biographie de base (Gemini) est nécessaire pour l'affinage.")
            return

        self._show_progress("Affinage Ollama en cours...")
        self.btn_refine_ollama.config(state=tk.DISABLED)
        self.btn_copy_to_validate.config(state=tk.DISABLED)

        def _do_refine():
            try:
                bio_gen = BioGenerator()
                ctx = bio_gen.build_context_from_v2(self.db_data, self.stash_ctx, self.scraped_results, self.merged_data, self.checked_fields)
                ollama_bio = bio_gen.generate_ollama_bio(ctx, gemini_bio)

                def _update_ui():
                    self.txt_ollama_result.delete("1.0", tk.END)
                    if ollama_bio:
                        self.txt_ollama_result.insert("1.0", ollama_bio)
                        self.btn_copy_to_validate.config(state=tk.NORMAL)
                    else:
                         self.txt_ollama_result.insert("1.0", "L'affinage Ollama a échoué. Vérifiez que le serveur Ollama est bien lancé.")
                
                self.after(0, _update_ui)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erreur Ollama", str(e)))
            finally:
                self.after(0, self._hide_progress)
                self.after(0, self.btn_refine_ollama.config, {'state': tk.NORMAL})
        
        threading.Thread(target=_do_refine, daemon=True).start()
    
    def _copy_to_validation(self):
        ollama_text = self.txt_ollama_result.get("1.0", tk.END)
        self.txt_final_bio.delete("1.0", tk.END)
        self.txt_final_bio.insert("1.0", ollama_text)
        self.notebook.tab(2, state="normal")
        self.notebook.select(self.tab3_validate)

    def _inject_bio(self):
        """Stocke la bio finale et ferme la fenêtre."""
        self.final_bio = self.txt_final_bio.get("1.0", tk.END).strip()
        self.destroy()

    def _show_progress(self, message):
        self.progress_label.config(text=message)
        self.progress_frame.pack(fill=tk.X, padx=10, pady=5, before=self.notebook)
        self.progress_bar.start(10)

    def _hide_progress(self):
        self.progress_bar.stop()
        self.progress_frame.pack_forget()
