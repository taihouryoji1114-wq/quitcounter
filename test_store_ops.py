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

    def test_counted_stock_enters_order_list_at_reorder_point(self):
        item = self.manager.add_item("ガスボンベ", "消耗品", "本", "", 6, "count", 2, 5)
        self.assertEqual(item["status"], "enough")
        updated = self.manager.set_count(item["id"], 2)
        self.assertEqual(updated["status"], "low")
        self.assertEqual(self.manager.order_list()[0]["name"], "ガスボンベ")

    def test_counted_stock_calculates_order_quantity_and_receive_refills_target(self):
        item = self.manager.add_item("ゴミ袋", "備品", "袋", "", 8, "count", 3, 2)
        order = self.manager.order_list()[0]
        self.assertEqual(order["suggested_order_quantity"], 6)
        self.manager.mark_ordered(item["id"])
        self.manager.receive(item["id"])
        received = self.manager.items()[0]
        self.assertEqual(received["current_stock"], 8)
        self.assertEqual(received["status"], "enough")

    def test_existing_simple_item_can_change_to_count_tracking(self):
        item = self.manager.add_item("ラップ", "備品")
        updated = self.manager.update_count_settings(item["id"], "本", 5, 2, 1)
        self.assertEqual(updated["tracking_mode"], "count")
        self.assertEqual(updated["unit"], "本")
        self.assertEqual(updated["status"], "low")

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

    def test_prep_progress_is_saved_per_day(self):
        item = self.manager.add_prep_template("鶏団子", "厨房")
        self.manager.set_prep_status("2026-08-14", item["id"], "done")
        self.assertEqual(self.manager.prep_items("2026-08-14")[0]["status"], "done")
        self.assertEqual(self.manager.prep_items("2026-08-15")[0]["status"], "incomplete")

    def test_deleted_prep_template_is_hidden_but_record_remains(self):
        item = self.manager.add_prep_template("鶏団子", "厨房")
        self.manager.set_prep_status("2026-08-14", item["id"], "done")
        self.manager.delete_prep_template(item["id"])
        self.assertEqual(self.manager.prep_templates(), [])
        self.assertEqual(
            self.data.data["store_prep_records"]["2026-08-14"][item["id"]], "done")

    def test_handover_can_be_confirmed(self):
        item = self.manager.add_handover("2026-08-14", "ガスボンベ残り1本", "厨房")
        self.manager.confirm_handover("2026-08-14", item["id"])
        self.assertTrue(self.manager.handovers("2026-08-14")[0]["confirmed"])

    def test_deleted_inventory_item_is_hidden(self):
        item = self.manager.add_item("誤登録")
        self.manager.delete_item(item["id"])
        self.assertEqual(self.manager.items(), [])

    def test_incomplete_prep_is_carried_to_next_day(self):
        item = self.manager.add_prep_template("唐揚げ", "厨房")
        self.manager.set_prep_status("2026-08-14", item["id"], "incomplete")
        next_item = self.manager.prep_items("2026-08-15")[0]
        self.assertTrue(next_item["carried_over"])
        self.assertEqual(next_item["status"], "incomplete")

    def test_handover_check_is_saved_by_area(self):
        item = self.manager.add_handover_template("予約席を確認", "ホール")
        self.manager.set_handover_check("2026-08-14", item["id"], True)
        self.assertTrue(self.manager.handover_checks("2026-08-14")[0]["checked"])

    def test_deleted_handover_template_is_hidden_but_record_remains(self):
        item = self.manager.add_handover_template("予約席を確認", "ホール")
        self.manager.set_handover_check("2026-08-14", item["id"], True)
        self.manager.delete_handover_template(item["id"])
        self.assertEqual(self.manager.handover_templates(), [])
        self.assertTrue(
            self.data.data["store_handover_checks"]["2026-08-14"][item["id"]])

    def test_handover_can_be_manually_sent_to_next_day_prep(self):
        item = self.manager.add_handover_template("唐揚げを仕込む", "厨房", "その他")
        self.manager.set_handover_check("2026-08-14", item["id"], False)
        self.manager.carry_handover("2026-08-14", item["id"])
        carried = [value for value in self.manager.prep_items("2026-08-15")
                   if value["id"] == f"handover:2026-08-14:{item['id']}"]
        self.assertEqual(len(carried), 1)
        self.assertTrue(carried[0]["carried_over"])

    def test_kitchen_handover_category_is_saved(self):
        item = self.manager.add_handover_template("出汁を確認", "厨房", "ちゃんこ")
        self.assertEqual(item["category"], "ちゃんこ")


if __name__ == "__main__":
    unittest.main()
