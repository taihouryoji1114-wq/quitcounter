import random
import unittest

from core.restaurant_card_game import draw_gacha, initial_profile, level_up, run_business


class RestaurantCardGameTest(unittest.TestCase):
    def test_business_updates_cash_and_advances_year(self):
        profile = initial_profile()
        result = run_business(profile, random.Random(2))
        self.assertEqual(profile["year"], 2)
        self.assertEqual(profile["cash"], 2_000_000 + result["profit"])
        self.assertIsNotNone(profile["last_result"])

    def test_gacha_spends_gems_and_awards_staff_or_shards(self):
        profile = initial_profile()
        drawn, duplicate = draw_gacha(profile, random.Random(3))
        self.assertEqual(profile["gems"], 400)
        self.assertIn(drawn["id"], profile["owned"])
        self.assertIsInstance(duplicate, bool)

    def test_level_up_consumes_experience(self):
        profile = initial_profile()
        profile["owned"]["yamada"]["xp"] = 40
        self.assertEqual(level_up(profile, "yamada"), 2)
        self.assertEqual(profile["owned"]["yamada"]["xp"], 0)


if __name__ == "__main__":
    unittest.main()
