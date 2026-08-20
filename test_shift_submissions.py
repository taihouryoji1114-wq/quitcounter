import tempfile
import unittest
from pathlib import Path

from core.data import DataManager
from core.shift_submissions import ShiftSubmissionManager


class ShiftSubmissionManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data = DataManager(Path(self.temp_dir.name) / "data.json")
        self.manager = ShiftSubmissionManager(self.data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_first_half_deadline_is_previous_month_twentieth(self):
        period = self.manager.period(2026, 9, "first")
        self.assertEqual(period["deadline"], "2026-08-20")
        self.assertEqual((period["start"], period["end"]), (1, 15))

    def test_second_half_deadline_is_month_fifth(self):
        period = self.manager.period(2026, 8, "second")
        self.assertEqual(period["deadline"], "2026-08-05")
        self.assertEqual((period["start"], period["end"]), (16, 31))

    def test_submission_is_saved_by_staff_and_period(self):
        self.manager.save("スタッフA", 2026, 8, "second",
                          {"16": "ランチ", "17": "休み"}, "18日は相談")
        saved = self.manager.submission("スタッフA", 2026, 8, "second")
        self.assertEqual(saved["days"], {"16": "ランチ", "17": "休み"})
        self.assertEqual(saved["note"], "18日は相談")


if __name__ == "__main__":
    unittest.main()
