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
                          {"16": {"type": "ランチ", "start": "11:30", "end": "15:30"},
                           "17": {"type": "絶対休み", "start": "", "end": ""}},
                          "18日は相談")
        saved = self.manager.submission("スタッフA", 2026, 8, "second")
        self.assertEqual(saved["days"], {
            "16": {"type": "ランチ", "start": "11:30", "end": "15:30"},
            "17": {"type": "絶対休み", "start": "", "end": ""},
        })
        self.assertEqual(saved["note"], "18日は相談")

    def test_empty_submission_is_allowed_and_means_days_off(self):
        self.manager.save("スタッフA", 2026, 8, "second", {}, "全日希望なし")
        saved = self.manager.submission("スタッフA", 2026, 8, "second")
        self.assertEqual(saved["days"], {})
        self.assertTrue(saved["submitted_at"])

    def test_old_labels_are_migrated_when_read(self):
        self.data.data.setdefault("store_shift_submissions", {}).setdefault(
            "2026-08-second", {})["スタッフA"] = {
                "days": {"16": "出勤可", "17": "休み"}, "submitted_at": "old"}
        saved = self.manager.submission("スタッフA", 2026, 8, "second")
        self.assertEqual(saved["days"]["16"]["type"], "通し")
        self.assertEqual(saved["days"]["17"]["type"], "絶対休み")


if __name__ == "__main__":
    unittest.main()
