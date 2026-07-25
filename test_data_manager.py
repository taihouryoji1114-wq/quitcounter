import json
import tempfile
import unittest
from pathlib import Path

from core.data import DataManager


class DataManagerWorkoutTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "data.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_saves_multiple_parts_without_duplicates_and_persists(self):
        manager = DataManager(self.path)
        manager.save_workout("2026-07-24", ["胸", "背中", "胸"])
        self.assertEqual(manager.get_workout_for_date("2026-07-24")["body_parts"], ["胸", "背中"])
        self.assertEqual(
            DataManager(self.path).get_workout_for_date("2026-07-24")["body_parts"], ["胸", "背中"]
        )

    def test_preserves_smoking_settings_and_legacy_workout_records(self):
        original = {
            "current_user": 0,
            "users": [{"name": "A", "start_date": "2026-01-01"}],
            "settings": {"theme": "dark"},
            "workout": [{"date": "2026-07-20", "parts": ["脚"]}],
        }
        self.path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
        manager = DataManager(self.path)
        manager.save_workout("2026-07-24", ["胸", "腹筋"])
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["users"]["user1"]["profile"], {"name": "A"})
        self.assertEqual(saved["users"]["user1"]["smoking"]["start_date"], "2026-01-01")
        self.assertEqual(saved["settings"], {"theme": "dark"})
        self.assertEqual(saved["workout"], original["workout"])
        self.assertEqual(
            manager.get_workout_for_date("2026-07-20")["body_parts"], ["脚"]
        )

    def test_smoking_and_workouts_are_separated_by_user(self):
        manager = DataManager(self.path)
        manager.save_workout("2026-07-24", ["胸"])
        user1_smoking = manager.get_smoking().copy()
        manager.select_user("user2")
        manager.save_workout("2026-07-24", ["脚", "腹筋"])
        manager.update_profile("ユーザー2", "2026-07-01", 8, 550)
        self.assertEqual(manager.get_workout_for_date("2026-07-24")["body_parts"], ["脚", "腹筋"])
        self.assertEqual(manager.get_smoking()["cigarettes_per_day"], 8)
        manager.select_user("user1")
        self.assertEqual(manager.get_workout_for_date("2026-07-24")["body_parts"], ["胸"])
        self.assertEqual(manager.get_smoking(), user1_smoking)

    def test_explicit_workout_owner_is_stable_after_user_switch(self):
        manager = DataManager(self.path)
        page_user_id = manager.active_user_id
        manager.select_user("user2")
        manager.save_workout("2026-07-25", ["肩"], page_user_id)
        self.assertEqual(
            manager.get_workout_for_date("2026-07-25", "user1")["body_parts"],
            ["肩"],
        )
        self.assertIsNone(manager.get_workout_for_date("2026-07-25", "user2"))

    def test_explicit_smoking_owner_does_not_follow_current_user(self):
        manager = DataManager(self.path)
        user1_smoking = manager.get_smoking("user1").copy()
        manager.select_user("user2")
        self.assertEqual(manager.get_smoking("user1"), user1_smoking)

    def test_deletes_only_the_selected_workout(self):
        manager = DataManager(self.path)
        manager.save_workout("2026-07-24", ["胸"])
        manager.save_workout("2026-07-25", ["脚"])

        manager.delete_workout("2026-07-24")

        self.assertIsNone(manager.get_workout_for_date("2026-07-24"))
        self.assertEqual(
            manager.get_workout_for_date("2026-07-25")["body_parts"],
            ["脚"],
        )

    def test_automatic_backup_preserves_previous_data(self):
        manager = DataManager(self.path)
        manager.save()
        previous = json.loads(self.path.read_text(encoding="utf-8"))

        manager.update_profile("変更後", "2026-07-01", 8, 550)

        backups = sorted(self.path.parent.glob("data.json.backup.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(
            json.loads(backups[0].read_text(encoding="utf-8")),
            previous,
        )


if __name__ == "__main__":
    unittest.main()
