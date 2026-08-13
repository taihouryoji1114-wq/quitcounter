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
        self.staffing.save_day("2026-08-01", {
            "スタッフA": {"lunch_start": "10:00", "lunch_end": "15:00"},
            "スタッフB": {"dinner_start": "18:00", "dinner_end": "20:00"},
        })
        self.staffing.save_day("2026-08-02", {"スタッフA": {"lunch_start": "10:00", "lunch_end": "13:00"}})
        self.staffing.save_day("2026-09-01", {"スタッフA": {"lunch_start": "10:00", "lunch_end": "20:00"}})
        self.assertEqual(self.staffing.day_total("2026-08-01"), 9000)
        self.assertEqual(self.staffing.month_total("2026-08"), 12600)

    def test_requires_both_start_and_end(self):
        with self.assertRaises(ValueError):
            self.staffing.save_day("2026-08-01", {"スタッフA": {"lunch_start": "10:00"}})

    def test_accepts_one_minute_precision(self):
        self.staffing.save_wages({"スタッフA": 1200})
        self.staffing.save_day("2026-08-01", {"スタッフA": {"lunch_start": "10:00", "lunch_end": "11:01"}})
        self.assertEqual(self.staffing.day_total("2026-08-01"), 1220)

    def test_night_rate_and_crossing_midnight(self):
        self.staffing.save_wages({"スタッフA": 1200})
        self.staffing.save_day("2026-08-01", {"スタッフA": {"dinner_start": "21:00", "dinner_end": "01:00"}})
        detail = self.staffing.day_detail("2026-08-01", "スタッフA")
        self.assertEqual(detail["normal_minutes"], 60)
        self.assertEqual(detail["night_minutes"], 180)
        self.assertEqual(detail["pay"], 5700)


if __name__ == "__main__":
    unittest.main()
