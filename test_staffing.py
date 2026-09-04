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

    def test_has_nine_pseudonymous_staff_slots(self):
        self.assertEqual(len(self.staffing.STAFF), 12)
        self.assertEqual(self.staffing.STAFF[0], "副社長")
        self.assertEqual(self.staffing.STAFF[3], "スタッフA")
        self.assertEqual(self.staffing.STAFF[-1], "スタッフI")

    def test_person_month_batch_preserves_others_and_is_atomic(self):
        self.staffing.save_person("2026-08-01", "スタッフB", {"lunch_start": "1000", "lunch_end": "1500"})
        before = dict(self.data.data["business_staff_hours"]["2026-08-01"]["スタッフB"])
        rows = {"2026-08-01": {"dinner_start": "1700", "dinner_end": "2200", "entry_confirmed": True},
                "2026-08-02": {"entry_confirmed": True}}
        self.assertEqual(self.staffing.save_person_month("スタッフA", "2026-08", rows), 2)
        self.assertEqual(self.data.data["business_staff_hours"]["2026-08-01"]["スタッフB"], before)
        self.assertEqual(self.staffing.day("2026-08-01")["スタッフA"]["dinner_start"], "17:00")
        self.assertTrue(self.staffing.day("2026-08-02")["スタッフA"]["entry_confirmed"])
        with self.assertRaises(ValueError):
            self.staffing.save_person_month("スタッフA", "2026-08", {
                "2026-08-03": {"entry_confirmed": True},
                "2026-08-04": {"lunch_start": "1000"}})
        self.assertNotIn("2026-08-03", self.data.data["business_staff_hours"])

    def test_person_month_conflict_does_not_overwrite(self):
        self.staffing.save_person("2026-08-01", "スタッフA", {"entry_confirmed": True})
        with self.assertRaises(ValueError):
            self.staffing.save_person_month("スタッフA", "2026-08", {"2026-08-01": {}}, expected={})
        self.assertTrue(self.staffing.day("2026-08-01")["スタッフA"]["entry_confirmed"])
        with self.assertRaises(ValueError):
            self.staffing.save_person_month("スタッフA", "2026-08", {"2026-09-01": {}})

    def test_attendance_previous_month_includes_last_day(self):
        self.staffing.save_person("2026-08-31", "店長", {"attended": True})
        self.staffing.save_person("2026-09-01", "店長", {"attended": True})
        previous = self.staffing.attendance_progress("2026-08", "2026-09-04")["店長"]
        self.assertEqual(previous["target_count"], 31)
        self.assertEqual(previous["checked_days"], [31])
        current = self.staffing.attendance_progress("2026-09", "2026-09-04")["店長"]
        self.assertEqual(current["target_count"], 4)
        self.assertEqual(current["checked_days"], [1])
        february = self.staffing.attendance_progress("2024-02", "2026-09-04")["店長"]
        self.assertEqual(february["target_count"], 29)

    def test_authorized_august_reset_runs_once_and_preserves_other_data(self):
        self.staffing.save_day("2026-08-02", {"店長": {"attended": True}})
        self.staffing.save_day("2026-09-02", {"店長": {"attended": True}})
        self.staffing.save_wages({"スタッフA": 1300})
        self.staffing.save_simple_plan("2026-08-03", {"スタッフA": {"lunch": True}}, date(2026, 8, 1))
        self.assertEqual(self.staffing.reset_august_2026_once(), 1)
        self.assertFalse(self.staffing.day("2026-08-02")["店長"]["attended"])
        self.assertTrue(self.staffing.day("2026-09-02")["店長"]["attended"])
        self.assertEqual(self.staffing.wages()["スタッフA"], 1300)
        self.assertTrue(self.staffing.planned_day("2026-08-03")["スタッフA"]["lunch_start"])
        self.staffing.save_person("2026-08-02", "店長", {"attended": True})
        reloaded = StaffingManager(DataManager(self.data.file_path))
        self.assertEqual(reloaded.reset_august_2026_once(), 0)
        self.assertTrue(reloaded.day("2026-08-02")["店長"]["attended"])
        self.assertTrue(self.data.data["business_staff_reset_archives"])

    def test_person_save_tracks_rest_days_without_marking_other_people(self):
        self.staffing.save_person("2026-08-02", "スタッフA", {})
        self.staffing.save_person("2026-08-04", "スタッフA", {"lunch_start": "1000", "lunch_end": "1500"})
        progress = self.staffing.timecard_progress("2026-08", "2026-08-04")
        self.assertEqual(progress["スタッフA"]["entered_days"], [2, 4])
        self.assertEqual(progress["スタッフA"]["missing_days"], [1, 3])
        self.assertEqual(progress["スタッフB"]["entered_days"], [])
        self.assertTrue(self.staffing.day("2026-08-02")["スタッフA"]["entry_confirmed"])

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

    def test_simple_future_plan_uses_median_recorded_shift(self):
        self.staffing.save_wages({"スタッフA": 1200})
        self.staffing.save_day("2026-08-01", {"スタッフA": {
            "lunch_start": "10:00", "lunch_end": "15:00", "break_minutes": 30,
        }})
        self.staffing.save_day("2026-08-02", {"スタッフA": {
            "lunch_start": "10:30", "lunch_end": "15:30", "break_minutes": 30,
        }})
        self.staffing.save_day("2026-08-03", {"スタッフA": {
            "lunch_start": "10:00", "lunch_end": "15:00", "break_minutes": 30,
        }})
        self.staffing.save_simple_plan("2026-08-15", {
            "スタッフA": {"lunch": True, "dinner": False},
        }, date(2026, 8, 14))
        planned = self.staffing.planned_day("2026-08-15")["スタッフA"]
        self.assertEqual((planned["lunch_start"], planned["lunch_end"]), ("10:00", "15:00"))
        self.assertEqual(planned["break_minutes"], 30)
        actual = self.staffing.day("2026-08-15")["スタッフA"]
        self.assertEqual((actual["lunch_start"], actual["lunch_end"]), ("", ""))

    def test_every_hourly_staff_gets_lunch_and_dinner_templates(self):
        self.staffing.save_day("2026-08-01", {"スタッフB": {
            "lunch_start": "10:30", "lunch_end": "15:30",
            "dinner_start": "17:00", "dinner_end": "23:00",
        }})
        templates = self.staffing.shift_templates(date(2026, 8, 14))
        for name in self.staffing.HOURLY_STAFF:
            self.assertEqual(templates[name]["lunch"]["start"], "10:30")
            self.assertEqual(templates[name]["lunch"]["end"], "15:30")
            self.assertEqual(templates[name]["dinner"]["start"], "17:00")
            self.assertEqual(templates[name]["dinner"]["end"], "23:00")

    def test_future_plan_affects_forecast_but_not_current_actual(self):
        self.staffing.save_wages({"スタッフA": 1200})
        self.staffing.save_day("2026-08-01", {"スタッフA": {
            "lunch_start": "10:00", "lunch_end": "15:00",
        }})
        self.staffing.save_simple_plan("2026-08-15", {
            "スタッフA": {"lunch": True},
        }, date(2026, 8, 14))
        summary = self.staffing.month_cost_summary("2026-08", date(2026, 8, 14))
        self.assertEqual(summary["gross_wages"], 6000)
        self.assertEqual(summary["planned_hourly_gross"], 6000)
        self.assertEqual(summary["forecast_gross_wages"], 12000)

    def test_legacy_future_plan_is_removed_from_actual_timecard(self):
        self.staffing.save_day("2026-08-20", {"スタッフA": {
            "lunch_start": "10:00", "lunch_end": "15:00",
        }})
        self.assertTrue(self.staffing.separate_legacy_future_plans(date(2026, 8, 14)))
        self.assertEqual(self.staffing.day("2026-08-20")["スタッフA"]["lunch_start"], "")
        self.assertEqual(self.staffing.planned_day("2026-08-20")["スタッフA"]["lunch_start"], "10:00")

    def test_elapsed_plan_never_becomes_actual_after_reload(self):
        self.staffing.save_simple_plan("2026-08-15", {"スタッフA": {"lunch": True}}, date(2026, 8, 14))
        reloaded = StaffingManager(DataManager(self.data.file_path))
        summary = reloaded.month_cost_summary("2026-08", date(2026, 9, 4))
        self.assertEqual(summary["gross_wages"], 0)
        self.assertEqual(reloaded.day("2026-08-15")["スタッフA"]["lunch_start"], "")
        self.assertEqual(reloaded.timecard_progress("2026-08", "2026-08-31")["スタッフA"]["entered_count"], 0)

    def test_night_rate_and_crossing_midnight(self):
        self.staffing.save_wages({"スタッフA": 1200})
        self.staffing.save_day("2026-08-01", {"スタッフA": {"dinner_start": "21:00", "dinner_end": "01:00"}})
        detail = self.staffing.day_detail("2026-08-01", "スタッフA")
        self.assertEqual(detail["normal_minutes"], 60)
        self.assertEqual(detail["night_minutes"], 180)
        self.assertEqual(detail["pay"], 5700)

    def test_break_time_is_subtracted_from_hourly_pay(self):
        self.staffing.save_wages({"スタッフA": 1200})
        self.staffing.save_day("2026-08-01", {"スタッフA": {
            "lunch_start": "10:00", "lunch_end": "15:00", "break_minutes": 30,
        }})
        detail = self.staffing.day_detail("2026-08-01", "スタッフA")
        self.assertEqual(detail["total_minutes"], 300)
        self.assertEqual(detail["paid_minutes"], 270)
        self.assertEqual(detail["pay"], 5400)

    def test_break_cannot_exceed_work_time(self):
        with self.assertRaises(ValueError):
            self.staffing.save_day("2026-08-01", {"スタッフA": {
                "lunch_start": "10:00", "lunch_end": "11:00", "break_minutes": 61,
            }})

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
        self.staffing.save_commute_rates({"スタッフA": 500})
        self.staffing.save_day("2026-08-01", {"スタッフA": {
            "lunch_start": "10:00", "lunch_end": "15:00",
        }})
        self.staffing.save_insurance_rates({
            "health": 5, "pension": 9.15, "care": 0, "employment": .85,
            "workers_comp": .3, "other": 0,
        })
        self.staffing.save_insurance_settings({"スタッフA": {
            "social": True, "standard_monthly": 100_000,
            "care": False, "employment": True,
        }})
        summary = self.staffing.month_cost_summary("2026-08", date(2026, 8, 1))
        self.assertEqual(summary["gross_wages"], 6000)
        self.assertEqual(summary["transportation"], 500)
        self.assertGreater(summary["employer_insurance"], 14_000)
        self.assertEqual(summary["company_cost"], 6500 + summary["employer_insurance"])

    def test_salaried_staff_use_monthly_gross_not_hours(self):
        self.staffing.save_monthly_salaries({"店長": 350_000, "社員A": 280_000})
        self.staffing.save_wages({"店長": 99_999})
        self.staffing.save_commute_rates({"店長": 500})
        self.staffing.save_day("2026-08-01", {"店長": {
            "attended": True,
        }})
        summary = self.staffing.month_cost_summary("2026-08", date(2026, 8, 31))
        self.assertEqual(summary["planned_days"], 21)
        self.assertEqual(summary["attendance"]["店長"], 1)
        self.assertEqual(summary["gross_wages"], round(350_000 / 21))
        self.assertEqual(summary["transportation"], 500)
        self.assertEqual(summary["forecast_gross_wages"], 630_000)

    def test_salaried_actual_is_capped_at_monthly_salary(self):
        self.staffing.save_monthly_salaries({"店長": 310_000})
        for day in range(1, 23):
            self.staffing.save_day(f"2026-08-{day:02d}", {"店長": {"attended": True}})
        summary = self.staffing.month_cost_summary("2026-08", date(2026, 8, 31))
        self.assertEqual(summary["gross_wages"], 310_000)

    def test_vice_president_is_regular_salaried_staff(self):
        self.staffing.save_monthly_salaries({"副社長": 420_000})
        self.staffing.save_day("2026-08-01", {"副社長": {"attended": True}})
        summary = self.staffing.month_cost_summary("2026-08", date(2026, 8, 1))
        self.assertEqual(summary["attendance"]["副社長"], 1)
        self.assertEqual(summary["gross_wages"], round(420_000 / 31))
        self.assertEqual(summary["forecast_gross_wages"], 420_000)

    def test_vice_president_uses_calendar_day_progress_without_attendance(self):
        self.staffing.save_monthly_salaries({"副社長": 310_000})
        summary = self.staffing.month_cost_summary("2026-08", date(2026, 8, 10))
        self.assertEqual(summary["gross_wages"], 100_000)
        self.assertEqual(summary["attendance"]["副社長"], 0)
        self.assertEqual(summary["forecast_gross_wages"], 310_000)

    def test_attendance_progress_shows_checked_and_missing_dates(self):
        self.staffing.save_day("2026-08-01", {"店長": {"attended": True}})
        self.staffing.save_day("2026-08-03", {"店長": {"attended": False}})
        progress = self.staffing.attendance_progress("2026-08", "2026-08-04")
        self.assertEqual(progress["店長"]["checked_days"], [1])
        self.assertEqual(progress["店長"]["missing_days"], [2, 3, 4])
        self.assertEqual(progress["店長"]["latest_date"], "2026-08-01")

    def test_timecard_progress_tracks_each_staff_latest_work_day(self):
        self.staffing.save_day("2026-08-02", {
            "スタッフA": {"lunch_start": "1000", "lunch_end": "15:30"},
        })
        self.staffing.save_day("2026-08-05", {
            "スタッフA": {"dinner_start": "17:00", "dinner_end": "22:00"},
            "店長": {"attended": True},
        })
        progress = self.staffing.timecard_progress("2026-08", "2026-08-06")
        self.assertEqual(progress["スタッフA"]["entered_days"], [2, 5])
        self.assertEqual(progress["スタッフA"]["entered_count"], 2)
        self.assertEqual(progress["スタッフA"]["latest_date"], "2026-08-05")
        self.assertEqual(progress["店長"]["latest_date"], "2026-08-05")


if __name__ == "__main__":
    unittest.main()
