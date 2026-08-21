import tempfile
import unittest
from pathlib import Path

from core.data import DataManager
from core.store_events import StoreEventManager


class StoreEventManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data = DataManager(Path(self.temp_dir.name) / "data.json")
        self.manager = StoreEventManager(self.data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_event_with_details_and_date_range_is_saved(self):
        event = self.manager.add("スタッフ親睦会", "2026-08-24", "2026-08-25",
                                 "18:00", "21:00", "親睦", "浅草駅に集合")
        self.assertEqual(event["details"], "浅草駅に集合")
        self.assertEqual(self.manager.events("2026-08-01", "2026-08-31")[0]["end_date"],
                         "2026-08-25")

    def test_event_can_be_deleted_without_removing_record(self):
        event = self.manager.add("試食会", "2026-08-24")
        self.manager.delete(event["id"])
        self.assertEqual(self.manager.events(), [])
        self.assertEqual(len(self.data.data["store_events"]), 1)

    def test_invalid_date_range_is_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.add("イベント", "2026-08-25", "2026-08-24")


if __name__ == "__main__":
    unittest.main()
