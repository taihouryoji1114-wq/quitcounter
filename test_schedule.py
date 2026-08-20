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
        item = self.manager.add_event("user1", "予定", "2026-08-20")
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
