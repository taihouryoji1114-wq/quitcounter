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
        self.hydration.add(500, "2026-07-25", "ryoji")
        self.hydration.add(300, "2026-07-25", "koka")
        self.assertEqual(self.hydration.get_amount("2026-07-25", "ryoji"), 500)
        self.assertEqual(self.hydration.get_amount("2026-07-25", "koka"), 300)

    def test_page_owner_is_stable_after_user_switch(self):
        page_user_id = self.manager.active_user_id
        self.manager.select_user("koka")
        self.hydration.add(100, "2026-07-25", page_user_id)
        self.assertEqual(self.hydration.get_amount("2026-07-25", "ryoji"), 100)
        self.assertEqual(self.hydration.get_amount("2026-07-25", "koka"), 0)

    def test_amounts_accumulate_in_one_hundred_ml_units(self):
        self.hydration.add(300, "2026-07-25")
        self.hydration.add(500, "2026-07-25")
        self.assertEqual(self.hydration.get_amount("2026-07-25"), 800)
        with self.assertRaises(ValueError):
            self.hydration.add(250, "2026-07-25")

    def test_goal_is_optional_and_user_scoped(self):
        self.assertIsNone(self.hydration.get_goal("ryoji"))
        self.hydration.set_goal(2500, "ryoji")
        self.assertEqual(self.hydration.get_goal("ryoji"), 2500)
        self.assertIsNone(self.hydration.get_goal("koka"))
        self.hydration.set_goal("", "ryoji")
        self.assertIsNone(self.hydration.get_goal("ryoji"))

    def test_summary_and_existing_data_are_preserved(self):
        original = {
            "schema_version": 3,
            "current_user_id": "ryoji",
            "custom": {"keep": True},
            "users": {
                "ryoji": {
                    "profile": {"name": "良治"},
                    "smoking": {
                        "start_date": "2026-07-12",
                        "cigarettes_per_day": 10,
                        "price_per_pack": 600,
                    },
                    "workout_records": [{"date": "2026-07-20", "body_parts": ["胸"]}],
                },
                "koka": {
                    "profile": {"name": "胡花"},
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
            saved["users"]["ryoji"]["workout_records"],
            original["users"]["ryoji"]["workout_records"],
        )


if __name__ == "__main__":
    unittest.main()
