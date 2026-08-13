import tempfile
import unittest
from datetime import date
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
        self.assertEqual(len(self.staffing.STAFF), 17)
        self.assertEqual(self.staffing.STAFF[0], "店長")
        self.assertEqual(self.staffing.STAFF[2], "スタッフA")
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

    def test_dependent_alert_uses_prior_income_and_projection(self):
        self.staffing.save_wages({"スタッフA": 1200})
        self.staffing.save_dependent_settings({
            "スタッフA": {"mode": "social", "limit": 1_300_000, "prior_income": 1_000_000}
        })
        self.staffing.save_day("2026-01-01", {
            "スタッフA": {"lunch_start": "10:00", "lunch_end": "15:00"}
        })
        status = self.staffing.dependent_status(2026, "スタッフA", date(2026, 8, 13))
        self.assertEqual(status["earned"], 1_006_000)
        self.assertEqual(status["remaining"], 294_000)
        self.assertIn(status["level"], ("warning", "danger", "over"))

    def test_general_tax_limit_defaults_to_1230000(self):
        settings = {"スタッフA": {"mode": "general"}}
        saved = self.staffing.save_dependent_settings(settings)
        self.assertEqual(saved["スタッフA"]["limit"], 1_230_000)

    def test_company_cost_includes_transport_and_employer_insurance(self):
        self.staffing.save_wages({"スタッフA": 1200})
        self.staffing.save_day("2026-08-01", {"スタッフA": {
            "lunch_start": "10:00", "lunch_end": "15:00", "transportation": 500,
        }})
        self.staffing.save_insurance_rates({
            "health": 5, "pension": 9.15, "care": 0, "employment": .85,
            "workers_comp": .3, "other": 0,
        })
        self.staffing.save_insurance_settings({"スタッフA": {
            "social": True, "standard_monthly": 100_000,
            "care": False, "employment": True,
        }})
        summary = self.staffing.month_cost_summary("2026-08")
        self.assertEqual(summary["gross_wages"], 6000)
        self.assertEqual(summary["transportation"], 500)
        self.assertGreater(summary["employer_insurance"], 14_000)
        self.assertEqual(summary["company_cost"], 6500 + summary["employer_insurance"])

    def test_salaried_staff_use_monthly_gross_not_hours(self):
        self.staffing.save_monthly_salaries({"店長": 350_000, "社員A": 280_000})
        self.staffing.save_wages({"店長": 99_999})
        self.staffing.save_day("2026-08-01", {"店長": {
            "lunch_start": "10:00", "lunch_end": "20:00", "transportation": 500,
        }})
        summary = self.staffing.month_cost_summary("2026-08")
        self.assertEqual(summary["gross_wages"], 630_000)
        self.assertEqual(summary["transportation"], 500)


if __name__ == "__main__":
    unittest.main()
