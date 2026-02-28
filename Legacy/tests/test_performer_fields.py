import unittest
from gui.performer_frame import PerformerFrame
import tkinter as tk

class TestPerformerFields(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        # On passe un stash_id de test
        self.frame = PerformerFrame(self.root, "1")

    def tearDown(self):
        self.root.destroy()

    def test_phase1_fields(self):
        # Le PerformerFrame démarre en Phase 1
        phase1_frame = self.frame.current_frame
        
        # Vérifier que les champs de la Phase 1 sont bien créés
        for field in phase1_frame.fields_list:
            self.assertIn(field, phase1_frame.fields)
            self.assertIsNotNone(phase1_frame.fields[field])

    def test_phase2_fields(self):
        # Naviguer vers la Phase 2
        self.frame.goto_phase2()
        phase2_frame = self.frame.current_frame

        # Vérifier que les champs de la Phase 2 sont bien créés
        for field in phase2_frame.fields_list:
            self.assertIn(field, phase2_frame.fields)
            self.assertIsNotNone(phase2_frame.fields[field])

if __name__ == "__main__":
    unittest.main()
