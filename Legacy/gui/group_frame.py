import tkinter as tk
from tkinter import ttk
from gui.group_phase1 import GroupPhase1Frame
from gui.group_phase2 import GroupPhase2Frame

class GroupFrame(ttk.Frame):
    def __init__(self, parent, stash_id):
        super().__init__(parent)
        self.stash_id = stash_id
        self.current_frame = None
        
        # For now, just a label
        label = ttk.Label(self, text=f"Group Frame for ID: {self.stash_id}")
        label.pack(pady=20, padx=20)

        self.goto_phase1()

    def goto_phase1(self):
        if self.current_frame:
            self.current_frame.destroy()
        
        self.current_frame = GroupPhase1Frame(self, self, self.stash_id)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def goto_phase2(self, group_data, scenes_data):
        if self.current_frame:
            self.current_frame.destroy()
            
        self.current_frame = GroupPhase2Frame(self, self, self.stash_id, group_data, scenes_data)
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
