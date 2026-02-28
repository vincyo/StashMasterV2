#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StashMaster V2 - Point d'entrée principal
Sélecteur de mode et fenêtre principale
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import os

# Ajout du répertoire courant au path pour les imports locaux
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.config_manager import ConfigManager

# Imports des Frames GUI
from gui.performer_frame import PerformerFrame
from gui.dvd_frame import DVDFrame
from gui.scene_frame import SceneFrame

class SelectorWindow(tk.Tk):
    """Fenêtre de démarrage pour choisir le type d'entité à traiter"""
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.title("StashMaster V2 - Sélecteur")
        self.geometry("400x300")
        self.resizable(False, False)
        
        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Que souhaitez-vous traiter ?", font=('Segoe UI', 14, 'bold')).pack(pady=(0, 20))
        
        btn_config = {'width': 30, 'padding': 10}
        
        ttk.Button(main_frame, text="👤 Performer", command=self._start_performer, **btn_config).pack(pady=5)
        ttk.Button(main_frame, text="📀 DVD / Groupe", command=self._start_dvd, **btn_config).pack(pady=5)
        ttk.Button(main_frame, text="🎬 Scène", command=self._start_scene, **btn_config).pack(pady=5)
        
        ttk.Label(main_frame, text="V2.0 - Optimisée", font=('Segoe UI', 8)).pack(side=tk.BOTTOM, pady=(10, 0))

    def _start_performer(self):
        performer_id = simpledialog.askstring("ID Stash", "Entrez l'ID du Performer (optionnel) :")
        self._launch_main_app("performer", performer_id)

    def _start_dvd(self):
        dvd_id = simpledialog.askstring("ID Stash", "Entrez l'ID du DVD (optionnel) :")
        self._launch_main_app("dvd", dvd_id)

    def _start_scene(self):
        scene_id = simpledialog.askstring("ID Stash", "Entrez l'ID de la Scène (optionnel) :")
        self._launch_main_app("scene", scene_id)

    def _launch_main_app(self, mode, entity_id):
        self.destroy()
        app = StashMasterApp(mode, entity_id)
        app.mainloop()

class StashMasterApp(tk.Tk):
    """Fenêtre principale de l'application après sélection du mode"""
    
    def __init__(self, mode, entity_id):
        super().__init__()
        self.mode = mode
        self.entity_id = entity_id
        
        mode_titles = {
            "performer": "Gestion Performer",
            "dvd": "Gestion DVD / Groupe",
            "scene": "Gestion Scène"
        }
        
        self.title(f"StashMaster V2 — {mode_titles.get(mode, 'Inconnu')}")
        self.state('zoomed') # Maximized on Windows
        
        self._setup_gui()

    def _setup_gui(self):
        if self.mode == "performer":
            frame = PerformerFrame(self, self.entity_id)
            frame.pack(fill=tk.BOTH, expand=True)
        elif self.mode == "dvd":
            frame = DVDFrame(self, self.entity_id)
            frame.pack(fill=tk.BOTH, expand=True)
        elif self.mode == "scene":
            frame = SceneFrame(self, self.entity_id)
            frame.pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    app = SelectorWindow()
    app.mainloop()
