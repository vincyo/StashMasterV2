import tkinter as tk
from tkinter import ttk

class PerformerBaseFrame(ttk.Frame):
    def __init__(self, parent, controller, stash_id):
        super().__init__(parent)
        self.controller = controller
        self.stash_id = stash_id
        self.fields = {}
        self.field_checkboxes = {}
        # To be defined in subclasses
        self.fields_list = [] 
        self.db_mapping = {}

    def create_header(self, title, buttons_config):
        bar = ttk.Frame(self, padding=5)
        bar.pack(fill=tk.X)
        
        ttk.Label(bar, text=f"{title} | ID: {self.stash_id}", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        btn_frame = ttk.Frame(bar)
        btn_frame.pack(side=tk.RIGHT, padx=5)
        
        for text, command in buttons_config:
            ttk.Button(btn_frame, text=text, command=command).pack(side=tk.LEFT, padx=2)

    def select_all_fields(self):
        for var in self.field_checkboxes.values():
            var.set(True)

    def select_empty_fields(self):
        for field, entry in self.fields.items():
            if field in self.field_checkboxes and entry:
                val = ""
                if isinstance(entry, tk.Entry):
                    val = entry.get().strip()
                elif isinstance(entry, tk.Text):
                    val = entry.get("1.0", tk.END).strip()
                
                if not val:
                    self.field_checkboxes[field].set(True)
                else:
                    self.field_checkboxes[field].set(False)

    def load_data(self):
        try:
            from services.db import PerformerDB
            db = PerformerDB()
            data = db.get_performer_by_id(self.stash_id)
            db.close()
        except Exception as e:
            print(f"Erreur DB: {e}")
            data = None
        
        if not data:
            return

        for field, db_key in self.db_mapping.items():
            entry = self.fields.get(field)
            if entry and db_key in data:
                value = data[db_key]
                if isinstance(value, (list, tuple)):
                    if field == "URLs":
                        value = "\n".join(value)
                    else:
                        value = ", ".join(value)
                
                if isinstance(entry, tk.Entry):
                    entry.delete(0, tk.END)
                    entry.insert(0, str(value) if value is not None else "")
                elif isinstance(entry, tk.Text):
                    entry.delete('1.0', tk.END)
                    entry.insert('1.0', str(value) if value is not None else "")
