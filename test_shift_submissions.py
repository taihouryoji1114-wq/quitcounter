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
        self.manager.save("スタッフA", 2099, 9, "first", {
            "1": {"type": "絶対休み", "start": "", "end": ""},
        })
        result = self.manager.auto_schedule(
            2099, 9, "first", lunch_required=1, dinner_required=1)
        self.assertEqual(result["days"]["1"]["shortages"], {
            "lunch": 1, "dinner": 1,
        })
        self.assertFalse(result["days"]["1"]["staff"]["スタッフA"]["lunch"])


if __name__ == "__main__":
    unittest.main()
