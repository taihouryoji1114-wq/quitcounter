import tempfile
import unittest
from unittest.mock import patch
from datetime import date
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

    def test_cancel_before_deadline_requires_own_pin_and_can_resubmit(self):
        self.manager.set_staff_pin("スタッフA", "1234")
        self.manager.set_staff_pin("スタッフB", "5678")
        with patch("core.shift_submissions.today_jst", return_value=date(2026, 9, 1)):
            self.manager.save("スタッフA", 2026, 9, "second", {"16": {"type": "ランチ"}})
            self.manager.save("スタッフB", 2026, 9, "second", {})
            with self.assertRaises(ValueError):
                self.manager.cancel_submission("スタッフA", 2026, 9, "second", pin="5678")
            result = self.manager.cancel_submission("スタッフA", 2026, 9, "second", pin="1234")
            self.assertFalse(result["change_request"])
            self.assertNotIn("スタッフA", self.manager.period_submissions(2026, 9, "second"))
            self.assertIn("スタッフB", self.manager.period_submissions(2026, 9, "second"))
            self.assertTrue(self.data.data["store_shift_cancelled_archive"])
            self.manager.save("スタッフA", 2026, 9, "second", {"17": {"type": "ディナー"}})
            self.assertTrue(self.manager.submission("スタッフA", 2026, 9, "second")["submitted_at"])

    def test_late_cancel_keeps_submission_until_approved(self):
        self.manager.set_staff_pin("スタッフA", "1234")
        self.manager.save("スタッフA", 2026, 9, "second", {"16": {"type": "ランチ"}})
        with patch("core.shift_submissions.today_jst", return_value=date(2026, 9, 6)):
            self.assertTrue(self.manager.cancel_submission("スタッフA", 2026, 9, "second", pin="1234")["change_request"])
            self.assertIn("スタッフA", self.manager.period_submissions(2026, 9, "second"))
            self.manager.review_change("スタッフA", 2026, 9, "second", False)
            self.assertIn("スタッフA", self.manager.period_submissions(2026, 9, "second"))
            self.manager.cancel_submission("スタッフA", 2026, 9, "second", pin="1234")
            self.manager.review_change("スタッフA", 2026, 9, "second", True)
            self.assertNotIn("スタッフA", self.manager.period_submissions(2026, 9, "second"))
            self.assertEqual(self.manager.pending_changes(2026, 9, "second"), {})

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

    def test_staff_pin_is_hashed_and_verified_per_person(self):
        self.manager.set_staff_pin("スタッフA", "１２３４")
        stored = self.data.data["store_shift_staff_pins"]["スタッフA"]
        self.assertNotIn("1234", stored.values())
        self.assertEqual(self.manager.staff_pin_for_admin("スタッフA"), "1234")
        self.assertTrue(self.manager.has_staff_pin("スタッフA"))
        self.assertTrue(self.manager.verify_staff_pin("スタッフA", "1234"))
        self.assertFalse(self.manager.verify_staff_pin("スタッフA", "9999"))
        self.assertFalse(self.manager.has_staff_pin("スタッフB"))

    def test_staff_pin_rejects_non_numeric_or_short_values(self):
        with self.assertRaises(ValueError):
            self.manager.set_staff_pin("スタッフA", "12")
        with self.assertRaises(ValueError):
            self.manager.set_staff_pin("スタッフA", "abcd")

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

    def test_edit_before_deadline_updates_immediately(self):
        first = {"1": {"type": "ランチ", "start": "11:00", "end": "15:00"}}
        changed = {"1": {"type": "通し", "start": "11:00", "end": "22:00"}}
        self.manager.save("スタッフA", 2099, 9, "first", first, "最初")
        result = self.manager.save("スタッフA", 2099, 9, "first", changed, "変更")
        self.assertFalse(result["change_request"])
        self.assertEqual(
            self.manager.submission("スタッフA", 2099, 9, "first")["days"], changed)

    def test_edit_after_deadline_waits_for_admin_approval(self):
        first = {"16": {"type": "ランチ", "start": "11:00", "end": "15:00"}}
        changed = {"16": {"type": "ディナー", "start": "17:00", "end": "22:00"}}
        self.manager.save("スタッフA", 2026, 8, "second", first, "最初")
        result = self.manager.save("スタッフA", 2026, 8, "second", changed, "変更希望")
        self.assertTrue(result["change_request"])
        self.assertEqual(
            self.manager.submission("スタッフA", 2026, 8, "second")["days"], first)
        self.assertIn(
            "スタッフA", self.manager.pending_changes(2026, 8, "second"))
        pending = self.manager.pending_changes(2026, 8, "second")["スタッフA"]
        self.assertEqual(pending["original_days"], first)
        self.assertTrue(
            self.manager.review_change("スタッフA", 2026, 8, "second", True))
        self.assertEqual(
            self.manager.submission("スタッフA", 2026, 8, "second")["days"], changed)
        self.assertEqual(
            self.manager.pending_changes(2026, 8, "second"), {})

    def test_auto_schedule_builds_fair_draft_without_attendance_records(self):
        for name in ("スタッフA", "スタッフB", "スタッフC"):
            self.manager.save(name, 2099, 9, "first", {
                "1": {"type": "通し", "start": "11:00", "end": "22:00"},
                "2": {"type": "通し", "start": "11:00", "end": "22:00"},
            })

        result = self.manager.auto_schedule(
            2099, 9, "first", lunch_required=2, dinner_required=2,
            thick_days=[2], deputy_rest_priority=False)

        first_day = result["days"]["1"]
        self.assertEqual(first_day["shortages"], {"lunch": 0, "dinner": 0})
        self.assertEqual(
            sum(value["lunch"] for value in first_day["staff"].values()), 2)
        self.assertEqual(
            sum(value["dinner"] for value in first_day["staff"].values()), 2)
        self.assertEqual(result["days"]["2"]["shortages"], {"lunch": 0, "dinner": 0})
        self.assertNotIn("staff_attendance", self.data.data)
        self.assertIn("2099-09-first", self.data.data["store_auto_shift_drafts"])

    def test_auto_schedule_reports_shortage_and_respects_absolute_day_off(self):
        for name in ("副社長", "店長", "社員A"):
            self.manager.save(name, 2099, 9, "first", {
                "1": {"type": "絶対休み", "start": "", "end": ""},
            })
        result = self.manager.auto_schedule(
            2099, 9, "first", lunch_required=1, dinner_required=1)
        self.assertEqual(result["days"]["1"]["shortages"], {
            "lunch": 1, "dinner": 1,
        })
        self.assertFalse(result["days"]["1"]["staff"]["スタッフA"]["lunch"])

    def test_unsubmitted_hourly_staff_is_off_but_salaried_staff_get_five_days_off(self):
        result = self.manager.auto_schedule(
            2099, 9, "first", lunch_required=3, dinner_required=3,
            deputy_rest_priority=False)
        for name in ("副社長", "店長", "社員A"):
            worked = sum(1 for value in result["days"].values()
                         if value["staff"][name]["lunch"])
            self.assertEqual(worked, 10)
        self.assertFalse(any(value["staff"]["スタッフA"]["lunch"]
                             for value in result["days"].values()))

    def test_salaried_absolute_days_are_included_in_five_days_off(self):
        self.manager.save("社員A", 2099, 9, "first", {
            "3": {"type": "絶対休み"}, "7": {"type": "絶対休み"},
        })
        result = self.manager.auto_schedule(
            2099, 9, "first", lunch_required=3, dinner_required=3)
        rest = result["settings"]["salaried_rest_days"]["社員A"]
        self.assertEqual(len(rest), 5)
        self.assertTrue({3, 7}.issubset(rest))

    def test_manual_shift_changes_are_locked_during_recalculation(self):
        self.manager.save("スタッフA", 2099, 9, "first", {
            "1": {"type": "通し"}, "2": {"type": "通し"},
        })
        result = self.manager.auto_schedule(
            2099, 9, "first", lunch_required=3, dinner_required=3,
            manual_overrides={"1": {"スタッフA": "休み"},
                              "2": {"スタッフA": "通し"}})
        self.assertFalse(result["days"]["1"]["staff"]["スタッフA"]["lunch"])
        self.assertTrue(result["days"]["2"]["staff"]["スタッフA"]["lunch"])
        self.assertEqual(result["settings"]["manual_overrides"]["1"]["スタッフA"],
                         "休み")

    def test_auto_schedule_keeps_a_leader_and_pairs_deputy_with_employee(self):
        for name in ("副社長", "店長", "社員A", "スタッフA"):
            self.manager.save(name, 2099, 9, "first", {
                "1": {"type": "通し", "start": "11:00", "end": "22:00"},
            })
        result = self.manager.auto_schedule(
            2099, 9, "first", lunch_required=3, dinner_required=3,
            deputy_rest_priority=False, require_manager_or_deputy=True,
            align_deputy_employee=True)
        for meal in ("lunch", "dinner"):
            staff = result["days"]["1"]["staff"]
            self.assertTrue(staff["副社長"][meal] or staff["店長"][meal])
            self.assertEqual(staff["副社長"][meal], staff["社員A"][meal])

    def test_thick_day_adds_one_person_to_each_meal(self):
        for name in ("スタッフA", "スタッフB", "スタッフC", "スタッフD"):
            self.manager.save(name, 2099, 9, "first", {"2": {"type": "通し"}})
        result = self.manager.auto_schedule(
            2099, 9, "first", lunch_required=3, dinner_required=3,
            thick_days=[2], deputy_rest_priority=False)
        staff = result["days"]["2"]["staff"]
        self.assertEqual(sum(value["lunch"] for value in staff.values()), 4)
        self.assertEqual(sum(value["dinner"] for value in staff.values()), 4)

    def test_hourly_priority_accepts_all_submitted_days_and_reports_cuts(self):
        for name in ("スタッフA", "スタッフB", "スタッフC"):
            self.manager.save(name, 2099, 9, "first", {"1": {"type": "通し"}})
        hourly = self.manager.auto_schedule(
            2099, 9, "first", lunch_required=1, dinner_required=1,
            staffing_priority="hourly", require_manager_or_deputy=False)
        employee = self.manager.auto_schedule(
            2099, 9, "first", lunch_required=1, dinner_required=1,
            staffing_priority="employees", require_manager_or_deputy=False)
        self.assertTrue(all(hourly["days"]["1"]["staff"][name]["lunch"]
                            for name in ("スタッフA", "スタッフB", "スタッフC")))
        self.assertGreater(employee["preference_summary"]["スタッフA"]["cut_days"], -1)
        self.assertEqual(hourly["preference_summary"]["スタッフA"]["cut_days"], 0)


if __name__ == "__main__":
    unittest.main()
