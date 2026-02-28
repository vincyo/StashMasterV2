import tkinter as tk
from tkinter import ttk
from gui.performer_phase1 import PerformerPhase1Frame
from gui.performer_phase2 import PerformerPhase2Frame

class PerformerFrame(ttk.Frame):
    def __init__(self, parent, stash_id):
        super().__init__(parent)
        self.stash_id = stash_id
        self.current_frame = None
        self.phase1_data = {} # Pour stocker les données résolues de la phase 1
        
        self.goto_phase1()

    def goto_phase1(self):
        if self.current_frame:
            self.current_frame.destroy()
        
        self.current_frame = PerformerPhase1Frame(self, self, self.stash_id)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def goto_phase2(self, phase1_updates: dict):
        """Passe à la phase 2 en emportant les données résolues de la phase 1."""
        self.phase1_data = phase1_updates

        if self.current_frame:
            self.current_frame.destroy()
            
        # Initialise la phase 2 avec les données de la phase 1
        self.current_frame = PerformerPhase2Frame(self, self, self.stash_id, self.phase1_data)
        self.current_frame.pack(fill=tk.BOTH, expand=True)




    def return_to_menu(self):
        # Fermer la fenêtre actuelle
        self.master.destroy()
        # Relancer le launcher
        try:
            from gui.launcher import start_launcher
            start_launcher()
        except Exception as e:
            print(f"Erreur lors du retour au menu: {e}")


