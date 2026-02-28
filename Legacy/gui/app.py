import tkinter as tk
from tkinter import ttk
import sv_ttk
from gui.performer_frame import PerformerFrame
# Placeholders for future modules
from gui.group_frame import GroupFrame
# from gui.scene_frame import SceneFrame

def launch_app(module, stash_id):
    root = tk.Tk()
    root.title(f"StashMaster V2 - {module}")
    
    # Maximiser la fenêtre au démarrage (Windows)
    try:
        root.state('zoomed')
    except:
        # Fallback pour d'autres OS (Linux/Mac)
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{w}x{h}+0+0")

    # Appliquer le thème moderne
    sv_ttk.set_theme("dark")

    if module == "Performer":
        frame = PerformerFrame(root, stash_id)
    elif module == "Group":
        frame = GroupFrame(root, stash_id)
    # elif module == "Scene":
    #     frame = SceneFrame(root, stash_id)
    else:
        import tkinter.messagebox as mb
        mb.showerror("Erreur", f"Module inconnu: {module}")
        root.destroy()
        return
    frame.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
