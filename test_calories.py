import json
import tempfile
import unittest
from pathlib import Path

from core.calories import (
    ACTIVITY_FACTORS,
    NutritionSettingsManager,
    calculate_daily_expenditure,
)
from core.data import DataManager


class NutritionSettingsManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "data.json"
        self.manager = DataManager(self.path)
        self.calories = NutritionSettingsManager(self.manager)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_activity_factors(self):
        expected = {
            "少ない": 1.2,
            "普通": 1.375,
            "多い": 1.55,
            "非常に多い": 1.725,
        }
        self.assertEqual(ACTIVITY_FACTORS, expected)
        for level, factor in expected.items():
            self.assertEqual(
                calculate_daily_expenditure(1600, level),
                round(1600 * factor),
            )

    def test_optional_values_are_unset_without_error(self):
        saved = self.calories.save_settings()
        self.assertEqual(
            saved,
            {
                "protein_goal": None,
                "calorie_goal": None,
                "basal_metabolism": None,
                "activity_level": None,
            },
        )
        self.assertIsNone(self.calories.estimated_daily_expenditure())

    def test_settings_are_separated_by_user(self):
        self.calories.save_settings(120, 2000, 1600, "普通", "ryoji")
        self.calories.save_settings(90, 1800, 1400, "少ない", "koka")
        self.assertEqual(
            self.calories.get_settings("ryoji"),
            {
                "protein_goal": 120,
                "calorie_goal": 2000,
                "basal_metabolism": 1600,
                "activity_level": "普通",
            },
        )
        self.assertEqual(
            self.calories.get_settings("koka"),
            {
                "protein_goal": 90,
                "calorie_goal": 1800,
                "basal_metabolism": 1400,
                "activity_level": "少ない",
            },
        )

    def test_page_owner_is_stable_after_user_switch(self):
        page_user_id = self.manager.active_user_id
        self.manager.select_user("koka")
        self.manager.update_profile(
            "良治更新", "2026-07-12", 10, 600, page_user_id
        )
        self.calories.save_settings(120, 2000, 1600, "普通", page_user_id)
        self.assertEqual(self.manager.get_profile("ryoji")["name"], "良治更新")
        self.assertEqual(self.manager.get_profile("koka")["name"], "胡花")
        self.assertEqual(
            self.calories.get_settings("ryoji")["protein_goal"], 120
        )
        self.assertIsNone(self.calories.get_settings("koka")["protein_goal"])

    def test_existing_user_data_and_other_settings_are_preserved(self):
        manager = DataManager(self.path)
        manager.data["users"]["ryoji"]["settings"] = {
            "hydration_goal_ml": 2500,
            "future_setting": "keep",
        }
        manager.data["users"]["ryoji"]["hydration_records"] = [
            {"date": "2026-07-25", "amount": 1800}
        ]
        manager.save()
        calories = NutritionSettingsManager(manager)
        calories.save_settings(120, 2000, 1600, "普通")

        saved = json.loads(self.path.read_text(encoding="utf-8"))
        user = saved["users"]["ryoji"]
        self.assertEqual(user["settings"]["hydration_goal_ml"], 2500)
        self.assertEqual(user["settings"]["future_setting"], "keep")
        self.assertEqual(
            user["hydration_records"],
            [{"date": "2026-07-25", "amount": 1800}],
        )
        self.assertEqual(user["workout_records"], [])

    def test_invalid_values_do_not_save(self):
        before = json.loads(json.dumps(self.manager.data))
        with self.assertRaises(ValueError):
            self.calories.save_settings(120.5, 2000, 1600, "普通")
        with self.assertRaises(ValueError):
            self.calories.save_settings(120, 2000, 1600, "不明")
        self.assertEqual(self.manager.data, before)


if __name__ == "__main__":
    unittest.main()
