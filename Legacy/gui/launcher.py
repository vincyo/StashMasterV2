import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import sv_ttk
from gui.app import launch_app

def center_window(window, width=400, height=300):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f'{width}x{height}+{x}+{y}')

def start_launcher():
    root = tk.Tk()
    root.title("StashMaster V2 - Launcher")
    
    # Appliquer le thème moderne sombre
    sv_ttk.set_theme("dark")
    
    center_window(root, 400, 250)
    
    ttk.Label(root, text="StashMaster V2", font=("Segoe UI", 16, "bold")).pack(pady=(20, 10))
    ttk.Label(root, text="Sélectionnez un module :", font=("Segoe UI", 10)).pack(pady=5)
    
    def on_select(module):
        root.withdraw()
        # Utiliser un prompt simple pour l'ID
        stash_id = simpledialog.askstring("Entrer l'ID", f"Entrez l'ID pour le module {module} :", parent=root)
        if not stash_id:
            messagebox.showwarning("ID requis", "Vous devez entrer un ID valide pour continuer.")
            root.deiconify()
            return
        root.destroy()
        # Lancer l'application principale maximisée
        launch_app(module, stash_id)
        
    ttk.Button(root, text="Performer", width=25, command=lambda: on_select("Performer")).pack(pady=5)
    ttk.Button(root, text="Group / DVD", width=25, command=lambda: on_select("Group")).pack(pady=5)
    ttk.Button(root, text="Scene", width=25, command=lambda: on_select("Scene")).pack(pady=5)
    
    root.mainloop()

if __name__ == "__main__":
    start_launcher()