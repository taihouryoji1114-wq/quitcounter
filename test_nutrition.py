import json
import tempfile
import unittest
from pathlib import Path

from core.calories import NutritionSettingsManager
from core.data import DataManager
from core.nutrition import NutritionManager


class NutritionManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "data.json"
        self.manager = DataManager(self.path)
        self.nutrition = NutritionManager(self.manager)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_foods_are_separated_by_user(self):
        self.nutrition.add_food("プロテイン", 140, 25, "ryoji")
        self.nutrition.add_food("ヨーグルト", 100, 10, "koka")
        self.assertEqual(
            [food["name"] for food in self.nutrition.get_foods("ryoji")],
            ["プロテイン"],
        )
        self.assertEqual(
            [food["name"] for food in self.nutrition.get_foods("koka")],
            ["ヨーグルト"],
        )

    def test_amount_calculates_calories_and_protein(self):
        food = self.nutrition.add_food("プロテイン", 140, 25)
        meal = self.nutrition.add_meal(
            "2026-07-25", food["id"], 1.5
        )
        self.assertEqual(meal["calories"], 210)
        self.assertEqual(meal["protein"], 37.5)
        self.assertEqual(
            self.nutrition.daily_summary("2026-07-25"),
            {
                "date": "2026-07-25",
                "calories": 210,
                "protein": 37.5,
            },
        )

    def test_meals_and_totals_are_separated_by_user(self):
        ryoji_food = self.nutrition.add_food(
            "プロテイン", 140, 25, "ryoji"
        )
        koka_food = self.nutrition.add_food(
            "ヨーグルト", 100, 10, "koka"
        )
        self.nutrition.add_meal(
            "2026-07-25", ryoji_food["id"], 2, "ryoji"
        )
        self.nutrition.add_meal(
            "2026-07-25", koka_food["id"], 1, "koka"
        )
        self.assertEqual(
            self.nutrition.daily_summary("2026-07-25", "ryoji")["calories"],
            280,
        )
        self.assertEqual(
            self.nutrition.daily_summary("2026-07-25", "koka")["calories"],
            100,
        )

    def test_page_owner_is_stable_after_user_switch(self):
        food = self.nutrition.add_food("プロテイン", 140, 25, "ryoji")
        page_user_id = self.manager.active_user_id
        self.manager.select_user("koka")
        self.nutrition.add_meal(
            "2026-07-25", food["id"], 1, page_user_id
        )
        self.assertEqual(
            len(self.nutrition.get_meal_records("2026-07-25", "ryoji")), 1
        )
        self.assertEqual(
            len(self.nutrition.get_meal_records("2026-07-25", "koka")), 0
        )

    def test_meal_keeps_food_snapshot(self):
        food = self.nutrition.add_food("プロテイン", 140, 25)
        meal = self.nutrition.add_meal("2026-07-25", food["id"], 1)
        food["calories"] = 999
        food["protein"] = 999
        self.assertEqual(meal["food_name"], "プロテイン")
        self.assertEqual(meal["calories"], 140)
        self.assertEqual(meal["protein"], 25)

    def test_existing_data_and_goals_are_preserved(self):
        goals = NutritionSettingsManager(self.manager)
        goals.save_settings(120, 2000, 1600, "普通")
        self.manager.data["users"]["ryoji"]["hydration_records"] = [
            {"date": "2026-07-25", "amount": 1800}
        ]
        self.manager.save()
        food = self.nutrition.add_food("プロテイン", 140, 25)
        self.nutrition.add_meal("2026-07-25", food["id"], 1)

        saved = json.loads(self.path.read_text(encoding="utf-8"))
        user = saved["users"]["ryoji"]
        self.assertEqual(user["settings"]["protein_goal"], 120)
        self.assertEqual(user["settings"]["calorie_goal"], 2000)
        self.assertEqual(
            user["hydration_records"],
            [{"date": "2026-07-25", "amount": 1800}],
        )
        self.assertEqual(user["workout_records"], [])

    def test_invalid_food_and_meal_do_not_save(self):
        before = json.loads(json.dumps(self.manager.data))
        with self.assertRaises(ValueError):
            self.nutrition.add_food("", 140, 25)
        with self.assertRaises(ValueError):
            self.nutrition.add_food("水", 0, 0)
        self.assertEqual(self.manager.data, before)
        food = self.nutrition.add_food("プロテイン", 140, 25)
        with self.assertRaises(ValueError):
            self.nutrition.add_meal("2026-07-25", food["id"], 0)


if __name__ == "__main__":
    unittest.main()
