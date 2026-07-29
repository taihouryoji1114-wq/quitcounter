import json
import tempfile
import unittest
from pathlib import Path

from core.data import DataManager
from core.hydration import HydrationManager


class HydrationManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "data.json"
        self.manager = DataManager(self.path)
        self.hydration = HydrationManager(self.manager)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_records_are_separated_by_user(self):
        self.hydration.add(500, "2026-07-25", "user1")
        self.hydration.add(300, "2026-07-25", "user2")
        self.assertEqual(self.hydration.get_amount("2026-07-25", "user1"), 500)
        self.assertEqual(self.hydration.get_amount("2026-07-25", "user2"), 300)

    def test_undo_last_added_amount(self):
        self.hydration.add(300, "2026-07-25", "user1")
        self.hydration.add(500, "2026-07-25", "user1")

        self.assertEqual(
            self.hydration.undo_last("2026-07-25", "user1"),
            500,
        )
        self.assertEqual(
            self.hydration.get_amount("2026-07-25", "user1"),
            300,
        )

    def test_undo_without_new_entry_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "取り消せる"):
            self.hydration.undo_last("2026-07-25", "user1")

    def test_page_owner_is_stable_after_user_switch(self):
        page_user_id = self.manager.active_user_id
        self.manager.select_user("user2")
        self.hydration.add(100, "2026-07-25", page_user_id)
        self.assertEqual(self.hydration.get_amount("2026-07-25", "user1"), 100)
        self.assertEqual(self.hydration.get_amount("2026-07-25", "user2"), 0)

    def test_any_positive_whole_ml_amount_can_be_added(self):
        self.hydration.add(250, "2026-07-25")
        self.hydration.add(37, "2026-07-25")
        self.assertEqual(self.hydration.get_amount("2026-07-25"), 287)
        with self.assertRaises(ValueError):
            self.hydration.add(0, "2026-07-25")

    def test_goal_is_optional_and_user_scoped(self):
        self.assertIsNone(self.hydration.get_goal("user1"))
        self.hydration.set_goal(2500, "user1")
        self.assertEqual(self.hydration.get_goal("user1"), 2500)
        self.assertIsNone(self.hydration.get_goal("user2"))
        self.hydration.set_goal("", "user1")
        self.assertIsNone(self.hydration.get_goal("user1"))

    def test_summary_and_existing_data_are_preserved(self):
        original = {
            "schema_version": 3,
            "current_user_id": "user1",
            "custom": {"keep": True},
            "users": {
                "user1": {
                    "profile": {"name": "ユーザー1"},
                    "smoking": {
                        "start_date": "2026-07-12",
                        "cigarettes_per_day": 10,
                        "price_per_pack": 600,
                    },
                    "workout_records": [{"date": "2026-07-20", "body_parts": ["胸"]}],
                },
                "user2": {
                    "profile": {"name": "ユーザー2"},
                    "smoking": {
                        "start_date": "2026-07-01",
                        "cigarettes_per_day": 10,
                        "price_per_pack": 600,
                    },
                    "workout_records": [],
                },
            },
        }
        self.path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
        manager = DataManager(self.path)
        hydration = HydrationManager(manager)
        hydration.set_goal(2500)
        hydration.add(1800, "2026-07-25")
        self.assertEqual(
            hydration.summary("2026-07-25"),
            {"amount": 1800, "goal": 2500, "percentage": 72},
        )
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["custom"], original["custom"])
        self.assertEqual(
            saved["users"]["user1"]["workout_records"],
            original["users"]["user1"]["workout_records"],
        )


if __name__ == "__main__":
    unittest.main()
