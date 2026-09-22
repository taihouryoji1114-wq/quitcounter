import tempfile
import unittest
from pathlib import Path
from core.data import DataManager
from core.store_ops import StoreOperationsManager
from pages.store_live_board import live_board_summary


class LiveBoardGroupsTest(unittest.TestCase):
    def test_names_are_grouped_and_attention_counts(self):
        items = [
            {'id': 'a', 'name': '唐揚げ', 'item_type': 'status', 'status': 'attention', 'note': '表示しない'},
            {'id': 'b', 'name': '出汁', 'item_type': 'status', 'status': 'incomplete'},
            {'id': 'c', 'name': '野菜', 'item_type': 'completion', 'status': 'incomplete'},
            {'id': 'd', 'name': '魚', 'item_type': 'completion', 'status': 'done'},
            {'id': 'e', 'source': 'daily_order', 'status': 'incomplete'},
            {'id': 'f', 'item_type': 'quantity', 'status': 'incomplete'},
            {'id': 'g', 'item_type': 'memo', 'status': 'incomplete'},
        ]
        done, total, groups = live_board_summary(items)
        self.assertEqual((done, total), (2, 4))
        self.assertEqual({k: [i['name'] for i in v] for k, v in groups.items()},
                         {'△': ['唐揚げ'], '×': ['出汁'], '未完了': ['野菜']})
        items[0]['status'] = 'done'
        self.assertEqual(live_board_summary(items)[2]['△'], [])

    def test_order_state_compatibility_rollover_and_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data.json'
            manager = StoreOperationsManager(DataManager(path))
            destination = manager.DAILY_ORDER_DESTINATIONS[0]
            manager.active_service_context('2026-09-21', 'lunch')
            manager.set_daily_order_state('2026-09-21', destination, 'not_needed')
            self.assertFalse(manager.daily_order_checks('2026-09-21')[destination])
            manager.active_service_context('2026-09-22', 'lunch')
            self.assertEqual(manager.daily_order_states('2026-09-22')[destination], 'not_needed')
            manager = StoreOperationsManager(DataManager(path))
            self.assertEqual(manager.daily_order_states('2026-09-22')[destination], 'not_needed')
            manager.set_daily_order_state('2026-09-22', destination, 'ordered')
            self.assertTrue(manager.daily_order_checks('2026-09-22')[destination])
            manager.set_daily_order_check('2026-09-22', destination, False)
            self.assertEqual(manager.daily_order_states('2026-09-22')[destination], 'unchecked')
            with self.assertRaises(ValueError):
                manager.set_daily_order_state('2026-09-22', destination, 'bad')

    def test_triangles_and_crosses_survive_day_change(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = StoreOperationsManager(DataManager(Path(directory) / 'data.json'))
            manager.active_service_context('2026-09-21', 'lunch')
            for name, status in [('唐揚げ', 'attention'), ('出汁', 'incomplete')]:
                item = manager.add_prep_template(name, '厨房')
                manager.set_service_prep_status('2026-09-21', 'lunch', item['id'], status)
            manager.active_service_context('2026-09-22', 'dinner')
            items = manager.service_prep_items('2026-09-22', 'lunch')
            self.assertEqual({i['name']: i['status'] for i in items}, {'唐揚げ': 'attention', '出汁': 'incomplete'})


if __name__ == '__main__':
    unittest.main()
