import tempfile
import unittest
from datetime import datetime, timedelta
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

    def test_daily_order_destinations_are_saved_per_day(self):
        self.manager.set_daily_order_check("2026-08-20", "豊洲", True)
        today = self.manager.daily_order_checks("2026-08-20")
        tomorrow = self.manager.daily_order_checks("2026-08-21")
        self.assertTrue(today["豊洲"])
        self.assertFalse(today["鶏肉"])
        self.assertFalse(tomorrow["豊洲"])
        self.assertEqual(set(today), {"鶏肉", "ミクリード", "豊洲", "酒屋"})

    def test_staff_can_add_and_complete_order_request(self):
        item = self.manager.add_order_request("ラップを発注お願いします")
        self.assertEqual(self.manager.order_requests(open_only=True)[0]["message"],
                         "ラップを発注お願いします")
        self.manager.set_order_request_completed(item["id"], True)
        self.assertEqual(self.manager.order_requests(open_only=True), [])
        self.assertTrue(self.manager.order_requests()[0]["completed"])

    def test_order_request_can_be_deleted(self):
        item = self.manager.add_order_request("誤入力")
        self.manager.delete_order_request(item["id"])
        self.assertEqual(self.manager.order_requests(), [])

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

    def test_inventory_item_can_be_edited(self):
        item = self.manager.add_item("ラップ", "備品", "本")
        updated = self.manager.update_item(
            item["id"], "業務用ラップ", "消耗品", "箱", "仕入れ先A", "simple")
        self.assertEqual(updated["name"], "業務用ラップ")
        self.assertEqual(updated["category"], "消耗品")
        self.assertEqual(updated["unit"], "箱")
        self.assertEqual(updated["supplier"], "仕入れ先A")
        self.assertEqual(updated["tracking_mode"], "simple")

    def test_new_items_default_to_vegetable_purchasing_category(self):
        item = self.manager.add_item("長ねぎ")
        self.assertEqual(item["category"], "野菜仕入れ")

    def test_legacy_food_items_move_to_vegetable_purchasing(self):
        self.data.data["store_inventory_items"] = [{
            "id": "legacy-food", "name": "白菜", "category": "食材", "active": True,
        }]

        migrated = StoreOperationsManager(self.data).items()[0]

        self.assertEqual(migrated["category"], "野菜仕入れ")
        self.assertEqual(
            self.data.data["store_inventory_items"][0]["category"], "野菜仕入れ")

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

    def test_first_service_uses_current_prep_items_on_live_board(self):
        item = self.manager.add_prep_template("サバ", "厨房")
        self.manager.set_service_prep_quantity("2026-08-20", "lunch", item["id"], 1)

        board = self.manager.service_handover_board("2026-08-20", "lunch")
        prep = next(entry for entry in board["items"] if entry["kind"] == "prep")

        self.assertEqual(prep["name"], "サバ（残り1・2個必要）")
        self.assertEqual(prep["quantity"], 1)
        self.assertEqual(prep["from_date"], "2026-08-20")
        self.assertEqual(prep["from_period"], "lunch")

    def test_deleted_prep_template_is_hidden_but_record_remains(self):
        item = self.manager.add_prep_template("鶏団子", "厨房")
        self.manager.set_prep_status("2026-08-14", item["id"], "done")
        self.manager.delete_prep_template(item["id"])
        self.assertEqual(self.manager.prep_templates(), [])
        self.assertEqual(
            self.data.data["store_prep_records"]["2026-08-14"][item["id"]], "done")

    def test_prep_template_can_be_edited(self):
        item = self.manager.add_prep_template("鶏団子", "厨房")
        updated = self.manager.update_prep_template(item["id"], "つくね", "デシャップ")
        self.assertEqual(updated["name"], "つくね")
        self.assertEqual(updated["area"], "デシャップ")

    def test_prep_template_can_use_configured_subchecks_and_note(self):
        item = self.manager.add_prep_template(
            "唐揚げ", "厨房", ["血抜き", "味付け", "粉付け"], True)

        initial = self.manager.service_prep_items("2026-08-29", "lunch")[0]
        self.assertEqual(initial["check_items"], ["血抜き", "味付け", "粉付け"])
        self.assertEqual(initial["status"], "incomplete")
        self.assertTrue(initial["note_enabled"])

        self.manager.set_service_prep_subchecks(
            "2026-08-29", "lunch", item["id"], ["血抜き", "味付け"])
        self.manager.set_service_prep_note(
            "2026-08-29", "lunch", item["id"], "粉付けだけ未完了")
        partial = self.manager.service_prep_items("2026-08-29", "lunch")[0]
        self.assertEqual(partial["status"], "incomplete")
        self.assertEqual(partial["note"], "粉付けだけ未完了")

        self.manager.set_service_prep_subchecks(
            "2026-08-29", "lunch", item["id"], ["血抜き", "味付け", "粉付け"])
        complete = self.manager.service_prep_items("2026-08-29", "lunch")[0]
        self.assertEqual(complete["status"], "done")

    def test_existing_prep_templates_keep_normal_completion_by_default(self):
        item = self.manager.add_prep_template("鶏団子", "厨房")
        saved = self.manager.prep_templates()[0]
        self.assertEqual(saved["check_items"], [])
        self.assertFalse(saved["note_enabled"])
        self.manager.set_service_prep_status(
            "2026-08-29", "lunch", item["id"], "done")
        self.assertEqual(
            self.manager.service_prep_items("2026-08-29", "lunch")[0]["status"], "done")

    def test_prep_templates_can_be_reordered(self):
        first = self.manager.add_prep_template("唐揚げ", "厨房")
        second = self.manager.add_prep_template("つくね", "厨房")
        self.assertTrue(self.manager.move_prep_template(second["id"], -1))
        self.assertEqual([item["id"] for item in self.manager.prep_templates()],
                         [second["id"], first["id"]])
        self.assertFalse(self.manager.move_prep_template(second["id"], -1))

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

    def test_handover_template_can_be_edited(self):
        item = self.manager.add_handover_template("予約席を確認", "ホール")
        updated = self.manager.update_handover_template(
            item["id"], "予約人数を確認", "デシャップ")
        self.assertEqual(updated["name"], "予約人数を確認")
        self.assertEqual(updated["area"], "デシャップ")

    def test_handover_can_be_manually_sent_to_next_day_prep(self):
        item = self.manager.add_handover_template("唐揚げを仕込む", "厨房", "その他")
        self.manager.set_handover_check("2026-08-14", item["id"], False)
        self.manager.carry_handover("2026-08-14", item["id"])
        carried = [value for value in self.manager.prep_items("2026-08-15")
                   if value["id"] == f"handover:2026-08-14:{item['id']}"]
        self.assertEqual(len(carried), 1)
        self.assertTrue(carried[0]["carried_over"])

    def test_previous_day_board_contains_unfinished_prep_and_unconfirmed_note(self):
        prep = self.manager.add_prep_template("唐揚げ", "厨房")
        self.manager.set_prep_status("2026-08-19", prep["id"], "incomplete")
        self.manager.add_handover("2026-08-19", "ポン酢を補充", "ホール")
        board = self.manager.previous_day_board("2026-08-20")
        self.assertEqual(board["previous_date"], "2026-08-19")
        self.assertEqual({item["name"] for item in board["items"]},
                         {"唐揚げ", "ポン酢を補充"})

    def test_completed_carried_prep_disappears_from_board(self):
        prep = self.manager.add_prep_template("唐揚げ", "厨房")
        self.manager.set_prep_status("2026-08-19", prep["id"], "incomplete")
        self.assertTrue(self.manager.previous_day_board("2026-08-20")["items"])
        self.manager.set_prep_status("2026-08-20", prep["id"], "done")
        self.assertFalse(self.manager.previous_day_board("2026-08-20")["items"])

    def test_prep_statuses_can_be_reset_for_the_day(self):
        first = self.manager.add_prep_template("唐揚げ", "厨房")
        second = self.manager.add_prep_template("つくね", "厨房")
        self.manager.set_prep_status("2026-08-20", first["id"], "done")
        self.manager.set_prep_status("2026-08-20", second["id"], "done")
        self.manager.reset_prep_statuses("2026-08-20")
        self.assertEqual({item["status"] for item in self.manager.prep_items("2026-08-20")},
                         {"incomplete"})

    def test_leftover_rice_choice_is_always_shown_on_next_handover_board(self):
        rice = self.manager.add_prep_template("余り米", "厨房")
        self.manager.ensure_service_checklist("2026-08-20", "lunch")
        self.manager.set_service_prep_choice("2026-08-20", "lunch", rice["id"], "なし")
        board = self.manager.service_handover_board("2026-08-20", "dinner")
        result = [item for item in board["items"] if item["kind"] == "check_result"]
        self.assertEqual([item["name"] for item in result], ["余り米：なし"])
        self.assertTrue(result[0]["completed"])

    def test_service_board_moves_completed_items_to_completed_lane(self):
        prep = self.manager.add_prep_template("唐揚げ", "厨房")
        self.manager.ensure_service_checklist("2026-08-20", "lunch")
        self.manager.set_service_prep_status("2026-08-20", "lunch", prep["id"], "done")
        request = self.manager.add_order_request("ラップ 2本")
        self.manager.set_order_request_completed(request["id"], True)
        board = self.manager.service_handover_board("2026-08-20", "dinner")
        completed = [item for item in board["items"] if item.get("completed")]
        self.assertIn("唐揚げ", {item["name"] for item in completed})

    def test_old_completed_notes_do_not_fill_current_board(self):
        note = self.manager.add_handover("2026-08-10", "古い引き継ぎ", "ホール")
        self.manager.confirm_handover("2026-08-10", note["id"])
        board = self.manager.service_handover_board("2026-08-20", "lunch")
        self.assertNotIn("古い引き継ぎ", {item["name"] for item in board["items"]})

    def test_completed_handover_can_be_reopened(self):
        note = self.manager.add_handover("2026-08-19", "補充を確認", "ホール")
        self.manager.confirm_handover("2026-08-19", note["id"])
        self.manager.reopen_handover("2026-08-19", note["id"])
        reopened = self.manager.handovers("2026-08-19")[0]
        self.assertFalse(reopened["confirmed"])
        self.assertEqual(reopened["confirmed_at"], "")

    def test_unselected_leftover_rice_keeps_choice_controls_on_board(self):
        rice = self.manager.add_prep_template("余り米", "厨房")
        self.manager.ensure_service_checklist("2026-08-20", "lunch")
        board = self.manager.service_handover_board("2026-08-20", "dinner")
        item = next(value for value in board["items"] if value["id"] == rice["id"])
        self.assertTrue(item["choice_mode"])
        self.assertFalse(item["completed"])

    def test_completed_service_items_can_be_bulk_reset(self):
        normal = self.manager.add_prep_template("唐揚げ", "厨房")
        fish = self.manager.add_prep_template("サバ", "厨房")
        rice = self.manager.add_prep_template("余り米", "厨房")
        self.manager.set_service_prep_status("2026-08-20", "dinner", normal["id"], "done")
        self.manager.set_service_prep_quantity("2026-08-20", "dinner", fish["id"], 2)
        self.manager.set_service_prep_choice("2026-08-20", "dinner", rice["id"], "あり")
        self.assertEqual(self.manager.reset_service_prep_items(
            "2026-08-20", "dinner", [normal["id"], fish["id"], rice["id"]]), 3)
        self.assertEqual({item["status"] for item in self.manager.service_prep_items(
            "2026-08-20", "dinner")}, {"incomplete"})

    def test_service_context_period_changes_manually_and_stale_date_rolls_forward(self):
        self.assertEqual(
            self.manager.active_service_context("2026-08-20", "lunch"),
            ("2026-08-20", "lunch"),
        )
        self.assertEqual(
            self.manager.active_service_context("2026-08-22", "dinner"),
            ("2026-08-22", "dinner"),
        )
        self.assertEqual(self.manager.advance_service_context(),
                         ("2026-08-23", "lunch"))
        self.assertEqual(self.manager.advance_service_context(),
                         ("2026-08-23", "dinner"))

    def test_future_manual_service_context_is_not_moved_back(self):
        self.assertEqual(
            self.manager.active_service_context("2026-08-22", "dinner"),
            ("2026-08-22", "dinner"),
        )
        self.assertEqual(self.manager.advance_service_context(),
                         ("2026-08-23", "lunch"))
        self.assertEqual(
            self.manager.active_service_context("2026-08-22", "dinner"),
            ("2026-08-23", "lunch"),
        )

    def test_manual_service_advance_keeps_completed_lane(self):
        prep = self.manager.add_prep_template("唐揚げ", "厨房")
        self.manager.ensure_service_checklist("2026-08-19", "dinner")
        self.manager.set_service_prep_status("2026-08-19", "dinner", prep["id"], "done")
        self.manager.active_service_context("2026-08-20", "lunch")
        lunch_board = self.manager.service_handover_board("2026-08-20", "lunch")
        self.assertTrue(lunch_board["items"][0]["completed"])
        self.manager.advance_service_context()
        self.manager.advance_service_context()
        next_board = self.manager.service_handover_board("2026-08-21", "lunch")
        self.assertTrue(next_board["items"][0]["completed"])

    def test_completed_board_items_can_be_reopened_together(self):
        prep = self.manager.add_prep_template("唐揚げ", "厨房")
        self.manager.ensure_service_checklist("2026-08-20", "lunch")
        self.manager.set_service_prep_status("2026-08-20", "lunch", prep["id"], "done")
        board = self.manager.service_handover_board("2026-08-20", "dinner")
        self.assertTrue(board["items"][0]["completed"])
        self.assertEqual(self.manager.reopen_handover_board_items(board["items"]), 1)
        reopened = self.manager.service_handover_board("2026-08-20", "dinner")
        self.assertFalse(reopened["items"][0]["completed"])

    def test_minimum_stock_automatically_adds_item_to_purchase_list(self):
        item = self.manager.add_item("白菜", "野菜仕入れ", "個", "", "", "count", 2, 3)
        self.assertEqual(self.manager.purchase_list(), [])
        self.manager.set_count(item["id"], 2)
        purchase_list = self.manager.purchase_list()
        self.assertEqual([(value["name"], value["purchase_quantity"])
                          for value in purchase_list], [("白菜", 1)])

    def test_purchase_list_disappears_after_stock_exceeds_minimum(self):
        item = self.manager.add_item("ラップ", "備品", "本", "", "", "count", 3, 1)
        self.assertEqual(len(self.manager.purchase_list()), 1)
        self.manager.set_count(item["id"], 4)
        self.assertEqual(self.manager.purchase_list(), [])

    def test_completed_orders_are_not_carried_to_board(self):
        self.manager.set_daily_order_check("2026-08-19", "ミクリード", True)
        board = self.manager.previous_day_board("2026-08-20")
        self.assertFalse(any(item["name"] == "ミクリードへ発注済み"
                             for item in board["items"]))

    def test_unchecked_daily_items_move_to_board_after_operating_day(self):
        self.manager.ensure_daily_checklist("2026-08-19")
        self.manager.set_daily_order_attention("2026-08-19", "豊洲", True)
        board = self.manager.previous_day_board("2026-08-20")
        missed = [item for item in board["items"] if item["kind"] == "order_missed"]
        attention = [item for item in board["items"] if item["kind"] == "order_attention"]
        self.assertEqual(len(missed), 3)
        self.assertEqual([item["name"] for item in attention], ["豊洲への発注未完了"])

    def test_attention_prep_is_carried_without_overdue_style(self):
        prep = self.manager.add_prep_template("魚をおろす", "厨房")
        self.manager.set_prep_status("2026-08-19", prep["id"], "attention")
        board = self.manager.previous_day_board("2026-08-20")
        self.assertEqual(board["items"][0]["kind"], "attention")

    def test_kitchen_handover_templates_move_to_prep_once(self):
        self.manager.add_handover_template("出汁を取る", "厨房")
        self.manager.add_handover_template("予約席確認", "ホール")
        self.assertEqual(self.manager.move_kitchen_handovers_to_prep(), 1)
        self.assertEqual(self.manager.move_kitchen_handovers_to_prep(), 0)
        self.assertEqual([item["name"] for item in self.manager.prep_templates()], ["出汁を取る"])
        self.assertEqual([item["name"] for item in self.manager.handover_templates()], ["予約席確認"])

    def test_inventory_item_exposes_last_counted_date(self):
        item = self.manager.add_item("ラップ", "備品", "本", "", "", "count")
        self.manager.set_count(item["id"], 3)
        self.assertTrue(self.manager.items()[0]["last_inventory_check_at"])

    def test_inventory_check_updates_multiple_items_with_one_save(self):
        counted = self.manager.add_item("ラップ", "備品", "本", "", 8, "count", 3, 5)
        simple = self.manager.add_item("醤油", "調味料")
        save_calls = []
        original_save = self.data.save
        self.data.save = lambda: save_calls.append(True)
        try:
            saved = self.manager.save_inventory_check([
                {"item_id": counted["id"], "count": 2},
                {"item_id": simple["id"], "status": "out"},
            ])
        finally:
            self.data.save = original_save
        values = {item["name"]: item for item in self.manager.items()}
        self.assertEqual(saved, 2)
        self.assertEqual(len(save_calls), 1)
        self.assertEqual(values["ラップ"]["current_stock"], 2)
        self.assertEqual(values["ラップ"]["status"], "low")
        self.assertEqual(values["醤油"]["status"], "out")

    def test_inventory_check_reset_preserves_stock_orders_and_purchase_plan(self):
        item = self.manager.add_item("ラップ", "備品", "本", "", 8, "count", 3, 2)
        self.manager.mark_ordered(item["id"])
        self.manager.save_purchase_quantities({item["id"]: 4}, "2026-08-23")

        reset_at = self.manager.reset_inventory_check()

        saved = self.manager.items()[0]
        self.assertEqual(saved["current_stock"], 2)
        self.assertEqual(saved["status"], "low")
        self.assertEqual(self.manager.order_list()[0]["order_state"], "ordered")
        self.assertEqual(self.manager.purchase_quantities("2026-08-23")[item["id"]], 4)
        self.assertEqual(self.manager.inventory_check_reset_at(), reset_at)

    def test_handover_uses_only_area_without_subcategory(self):
        item = self.manager.add_handover_template("出汁を確認", "厨房", "ちゃんこ")
        self.assertEqual(item["category"], "")

    def test_open_order_request_is_carried_to_next_day_board(self):
        request = self.manager.add_order_request("ラップを発注")
        request_date = request["created_at"][:10]
        next_date = (datetime.fromisoformat(request_date) + timedelta(days=1)).date().isoformat()
        board = self.manager.previous_day_board(next_date)
        carried = [item for item in board["items"] if item["kind"] == "request"]
        self.assertEqual([item["name"] for item in carried], ["発注依頼：ラップを発注"])
        self.manager.set_order_request_completed(request["id"], True)
        self.assertFalse(any(item["kind"] == "request"
                             for item in self.manager.previous_day_board(next_date)["items"]))


if __name__ == "__main__":
    unittest.main()
