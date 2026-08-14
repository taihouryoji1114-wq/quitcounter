import tempfile
import unittest
from pathlib import Path

from core.data import DataManager
from core.store_ops import StoreOperationsManager


class StoreOperationsManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data = DataManager(Path(self.temp_dir.name) / "data.json")
        self.manager = StoreOperationsManager(self.data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_low_stock_automatically_appears_in_order_list(self):
        item = self.manager.add_item("たまご", "食材", "個", "ハナマサ", "2パック")
        self.manager.set_status(item["id"], "low")
        order = self.manager.order_list()[0]
        self.assertEqual(order["name"], "たまご")
        self.assertEqual(order["order_state"], "needed")

    def test_order_and_receive_flow_restores_stock(self):
        item = self.manager.add_item("ゴミ袋", "消耗品")
        self.manager.set_status(item["id"], "out")
        self.manager.mark_ordered(item["id"])
        self.assertEqual(self.manager.order_list()[0]["order_state"], "ordered")
        self.manager.receive(item["id"])
        self.assertEqual(self.manager.items()[0]["status"], "enough")
        self.assertEqual(self.manager.order_list(), [])

    def test_duplicate_item_name_is_rejected(self):
        self.manager.add_item("醤油")
        with self.assertRaises(ValueError):
            self.manager.add_item("醤油")

    def test_hygiene_is_complete_only_with_all_temperatures_and_checks(self):
        checks = {"receiving": True, "equipment": True, "toilet": True, "handwash": True}
        self.manager.save_hygiene("2026-08-14", {
            "デシャップ冷蔵庫1": 4, "デシャップ冷蔵庫2": 5.5,
            "デシャップ冷蔵庫3": 4.5,
            "厨房冷蔵庫1": 4, "厨房冷蔵庫2": 5, "厨房冷蔵庫3": 4,
            "厨房冷蔵庫4": 5, "厨房冷蔵庫5": 4,
            "デシャップ冷凍庫": -20, "厨房冷凍庫": -19, "外冷凍庫": -18,
        }, checks, "問題なし")
        self.assertTrue(self.manager.hygiene_complete("2026-08-14"))
        self.assertEqual(
            self.manager.hygiene_record("2026-08-14")["temperatures"]["外冷凍庫"], -18)

    def test_existing_unrelated_data_is_preserved(self):
        self.data.data["business_sales"] = [{"id": "keep"}]
        self.manager.add_item("塩")
        self.assertEqual(self.data.data["business_sales"], [{"id": "keep"}])


if __name__ == "__main__":
    unittest.main()
