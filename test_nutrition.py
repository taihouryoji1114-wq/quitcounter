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
        for user in self.manager.data["users"].values():
            user["foods"] = []
        self.nutrition = NutritionManager(self.manager)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_foods_are_separated_by_user(self):
        self.nutrition.add_food("プロテイン", 140, 25, "user1")
        self.nutrition.add_food("ヨーグルト", 100, 10, "user2")
        self.assertEqual(
            [food["name"] for food in self.nutrition.get_foods("user1")],
            ["プロテイン"],
        )
        self.assertEqual(
            [food["name"] for food in self.nutrition.get_foods("user2")],
            ["ヨーグルト"],
        )

    def test_food_can_be_updated_and_deleted(self):
        food = self.nutrition.add_food("卵", 71, 6.1, "user1")
        updated = self.nutrition.update_food(
            food["id"], "卵（1個）", 71, 6.1, "user1"
        )
        self.assertEqual(updated["name"], "卵（1個）")

        deleted = self.nutrition.delete_food(food["id"], "user1")
        self.assertEqual(deleted["id"], food["id"])
        self.assertEqual(self.nutrition.get_foods("user1"), [])

    def test_meal_can_be_deleted_and_totals_are_updated(self):
        food = self.nutrition.add_food("卵", 71, 6.1, "user1")
        meal = self.nutrition.add_meal(
            "2026-07-25", food["id"], 2, "user1"
        )
        self.assertEqual(
            self.nutrition.daily_summary("2026-07-25", "user1")["calories"],
            142,
        )

        deleted = self.nutrition.delete_meal(meal["id"], "user1")

        self.assertEqual(deleted["id"], meal["id"])
        self.assertEqual(
            self.nutrition.daily_summary("2026-07-25", "user1")["calories"],
            0,
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

    def test_multiple_foods_are_saved_together(self):
        egg = self.nutrition.add_food("卵", 71, 6.1)
        rice = self.nutrition.add_food("ライス", 78, 1.25)
        meals = self.nutrition.add_meals(
            "2026-07-25", [egg["id"], rice["id"]]
        )
        self.assertEqual(len(meals), 2)
        self.assertEqual(
            self.nutrition.daily_summary("2026-07-25")["calories"],
            149,
        )

    def test_registered_food_can_be_saved_as_multiple_units(self):
        rice = self.nutrition.add_food("ライス50g", 78, 1.25)
        meal = self.nutrition.add_meal(
            "2026-07-25", rice["id"], 8
        )
        self.assertEqual(meal["amount"], 8)
        self.assertEqual(meal["calories"], 624)
        self.assertEqual(meal["protein"], 10)

    def test_manual_meal_is_included_in_totals(self):
        meal = self.nutrition.add_manual_meal(
            "2026-07-25", 650, 32.5, "外食"
        )
        self.assertEqual(meal["food_name"], "外食")
        self.assertIsNone(meal["food_id"])
        self.assertEqual(
            self.nutrition.daily_summary("2026-07-25"),
            {"date": "2026-07-25", "calories": 650, "protein": 32.5},
        )

    def test_meals_can_be_grouped_by_morning_lunch_and_dinner(self):
        egg = self.nutrition.add_food("卵", 71, 6.1)
        breakfast = self.nutrition.add_meals(
            "2026-07-25", [egg["id"]], meal_period="朝"
        )[0]
        dinner = self.nutrition.add_manual_meal(
            "2026-07-25", 500, 30, "夕食", meal_period="夜"
        )
        self.assertEqual(breakfast["meal_period"], "朝")
        self.assertEqual(dinner["meal_period"], "夜")

    def test_period_summary_aggregates_week(self):
        food = self.nutrition.add_food("卵", 71, 6.1)
        self.nutrition.add_meal("2026-07-20", food["id"], 1)
        self.nutrition.add_meal("2026-07-25", food["id"], 2)
        self.nutrition.add_meal("2026-07-27", food["id"], 3)
        summary = self.nutrition.period_summary(
            "2026-07-20", "2026-07-26"
        )
        self.assertEqual(summary["days"], 7)
        self.assertEqual(summary["calories"], 213)
        self.assertEqual(summary["protein"], 18.3)

    def test_meals_and_totals_are_separated_by_user(self):
        user1_food = self.nutrition.add_food(
            "プロテイン", 140, 25, "user1"
        )
        user2_food = self.nutrition.add_food(
            "ヨーグルト", 100, 10, "user2"
        )
        self.nutrition.add_meal(
            "2026-07-25", user1_food["id"], 2, "user1"
        )
        self.nutrition.add_meal(
            "2026-07-25", user2_food["id"], 1, "user2"
        )
        self.assertEqual(
            self.nutrition.daily_summary("2026-07-25", "user1")["calories"],
            280,
        )
        self.assertEqual(
            self.nutrition.daily_summary("2026-07-25", "user2")["calories"],
            100,
        )

    def test_page_owner_is_stable_after_user_switch(self):
        food = self.nutrition.add_food("プロテイン", 140, 25, "user1")
        page_user_id = self.manager.active_user_id
        self.manager.select_user("user2")
        self.nutrition.add_meal(
            "2026-07-25", food["id"], 1, page_user_id
        )
        self.assertEqual(
            len(self.nutrition.get_meal_records("2026-07-25", "user1")), 1
        )
        self.assertEqual(
            len(self.nutrition.get_meal_records("2026-07-25", "user2")), 0
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
        self.manager.data["users"]["user1"]["hydration_records"] = [
            {"date": "2026-07-25", "amount": 1800}
        ]
        self.manager.save()
        food = self.nutrition.add_food("プロテイン", 140, 25)
        self.nutrition.add_meal("2026-07-25", food["id"], 1)

        saved = json.loads(self.path.read_text(encoding="utf-8"))
        user = saved["users"]["user1"]
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
