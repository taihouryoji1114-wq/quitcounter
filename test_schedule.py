import tempfile
import unittest
from pathlib import Path

from core.data import DataManager
from core.schedule import ScheduleManager


class ScheduleManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data = DataManager(Path(self.temp_dir.name) / "data.json")
        self.manager = ScheduleManager(self.data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_events_are_private_per_user(self):
        self.manager.add_event("user1", "銀行", "2026-08-20", "10:00", "11:00", "仕事")
        self.assertEqual(len(self.manager.events("user1")), 1)
        self.assertEqual(self.manager.events("user2"), [])

    def test_events_are_sorted_and_filtered(self):
        self.manager.add_event("user1", "夜", "2026-08-21", "18:00")
        self.manager.add_event("user1", "朝", "2026-08-20", "09:00")
        values = self.manager.events("user1", "2026-08-20", "2026-08-20")
        self.assertEqual([value["title"] for value in values], ["朝"])

    def test_complete_and_delete_event(self):
        item = self.manager.add_event(
            "user1", "予定", "2026-08-20", requires_check=True)
        self.manager.set_completed("user1", item["id"], True)
        self.assertTrue(self.manager.events("user1")[0]["completed"])
        self.manager.delete_event("user1", item["id"])
        self.assertEqual(self.manager.events("user1"), [])

    def test_event_title_and_note_can_be_updated(self):
        item = self.manager.add_event("user1", "会議", "2026-08-20", note="")
        updated = self.manager.update_event("user1", item["id"], "経営会議", "資料を持参")
        self.assertEqual(updated["title"], "経営会議")
        self.assertEqual(updated["note"], "資料を持参")
        self.assertEqual(self.manager.events("user1")[0]["note"], "資料を持参")

    def test_normal_event_does_not_accept_completion(self):
        item = self.manager.add_event("user1", "食事会", "2026-08-20")
        self.assertFalse(item["requires_check"])
        with self.assertRaises(ValueError):
            self.manager.set_completed("user1", item["id"], True)

    def test_unfinished_check_event_rolls_over_to_target_day(self):
        item = self.manager.add_event(
            "user1", "振込", "2026-08-20", requires_check=True)
        changed = self.manager.roll_over_unfinished("user1", "2026-08-21")
        carried = self.manager.events("user1")[0]
        self.assertEqual(changed, 1)
        self.assertEqual(carried["date"], "2026-08-21")
        self.assertEqual(carried["end_date"], "2026-08-21")
        self.assertEqual(carried["carried_from"], "2026-08-20")

    def test_completed_check_event_is_not_rolled_over(self):
        item = self.manager.add_event(
            "user1", "提出", "2026-08-20", requires_check=True)
        self.manager.set_completed("user1", item["id"], True)
        self.assertEqual(self.manager.roll_over_unfinished("user1", "2026-08-21"), 0)
        self.assertEqual(self.manager.events("user1")[0]["date"], "2026-08-20")

    def test_event_can_be_changed_to_check_required_after_creation(self):
        item = self.manager.add_event("user1", "買い物", "2026-08-20")
        updated = self.manager.update_event(
            "user1", item["id"], "買い物", "牛乳", requires_check=True)
        self.assertTrue(updated["requires_check"])

    def test_monthly_event_is_created_on_same_day(self):
        self.manager.add_event(
            "user1", "家賃振込", "2026-08-10", requires_check=True,
            repeat_monthly=True)
        september = self.manager.events("user1", "2026-09-01", "2026-09-30")
        self.assertEqual(len(september), 1)
        self.assertEqual(september[0]["date"], "2026-09-10")
        self.assertTrue(september[0]["repeat_monthly"])
        self.assertFalse(september[0]["completed"])

    def test_monthly_event_uses_month_end_when_day_does_not_exist(self):
        self.manager.add_event(
            "user1", "月末確認", "2026-01-31", requires_check=True,
            repeat_monthly=True)
        february = self.manager.events("user1", "2026-02-01", "2026-02-28")
        self.assertEqual([item["date"] for item in february], ["2026-02-28"])

    def test_monthly_occurrences_have_independent_completion(self):
        august = self.manager.add_event(
            "user1", "請求確認", "2026-08-15", requires_check=True,
            repeat_monthly=True)
        september = self.manager.events("user1", "2026-09-01", "2026-09-30")[0]
        self.manager.set_completed("user1", august["id"], True)
        values = {item["id"]: item for item in self.manager.events("user1")}
        self.assertTrue(values[august["id"]]["completed"])
        self.assertFalse(values[september["id"]]["completed"])

    def test_invalid_time_range_is_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.add_event("user1", "予定", "2026-08-20", "18:00", "10:00")

    def test_multi_day_event_appears_on_each_overlapping_month(self):
        self.manager.add_event("user1", "旅行", "2026-08-30", category="個人",
                               event_end_date="2026-09-02")
        self.assertEqual(len(self.manager.events("user1", "2026-09-01", "2026-09-30")), 1)
        self.assertEqual(self.manager.events("user1")[0]["end_date"], "2026-09-02")

    def test_invalid_date_range_is_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.add_event("user1", "旅行", "2026-08-20",
                                   event_end_date="2026-08-19")


if __name__ == "__main__":
    unittest.main()
