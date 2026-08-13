import tempfile
import unittest
from pathlib import Path

from core.data import DataManager
from core.staffing import StaffingManager


class StaffingManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data = DataManager(Path(self.temp_dir.name) / "data.json")
        self.staffing = StaffingManager(self.data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_has_fifteen_pseudonymous_staff_slots(self):
        self.assertEqual(len(self.staffing.STAFF), 15)
        self.assertEqual(self.staffing.STAFF[0], "スタッフA")
        self.assertEqual(self.staffing.STAFF[-1], "スタッフO")

    def test_month_total_uses_wage_and_daily_hours(self):
        self.staffing.save_wages({"スタッフA": 1200, "スタッフB": 1500})
        self.staffing.save_day("2026-08-01", {"スタッフA": 5, "スタッフB": 2})
        self.staffing.save_day("2026-08-02", {"スタッフA": 3})
        self.staffing.save_day("2026-09-01", {"スタッフA": 10})
        self.assertEqual(self.staffing.day_total("2026-08-01"), 9000)
        self.assertEqual(self.staffing.month_total("2026-08"), 12600)

    def test_rejects_more_than_24_hours(self):
        with self.assertRaises(ValueError):
            self.staffing.save_day("2026-08-01", {"スタッフA": 25})


if __name__ == "__main__":
    unittest.main()
