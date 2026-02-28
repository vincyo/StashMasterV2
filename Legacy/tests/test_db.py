import unittest
from services.db import PerformerDB

class TestDB(unittest.TestCase):
    def setUp(self):
        self.db = PerformerDB()

    def tearDown(self):
        self.db.close()

    def test_get_known_performers(self):
        performers = self.db.get_known_performers()
        self.assertIsInstance(performers, list)
        if performers:
            self.assertIsInstance(performers[0], str)

if __name__ == '__main__':
    unittest.main()
