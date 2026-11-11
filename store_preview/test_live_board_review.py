import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from store_preview.core.clock import JAPAN
from store_preview.core.data import DataManager
from store_preview.core.live_board_review import LiveBoardReviewManager


class LiveBoardReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'sample.json'
        self.data = DataManager(self.path)
        self.reviews = LiveBoardReviewManager(self.data)
        self.item = {'id': 'one', 'name': '出汁', 'item_type': 'status',
                     'status': 'attention', 'reviewed': True, 'quantity': 3,
                     'note': '味を確認', 'last_update': {'updated_at': '2026-11-11T20:00:00+09:00'}}
        self.before = datetime(2026, 11, 12, 3, 59, 59, tzinfo=JAPAN)
        self.after = datetime(2026, 11, 12, 4, 0, 0, tzinfo=JAPAN)

    def test_initial_checks_empty_even_for_existing_done_results(self):
        self.reviews.initialize_handover([self.item])
        self.assertFalse(self.reviews.checked('one', self.before))
        self.assertEqual(self.reviews.handovers()[0]['status'], 'attention')

    def test_upgrade_preserves_existing_handover_acknowledgements(self):
        self.reviews.initialize_handover([self.item], {'one': True})
        self.assertTrue(self.reviews.handovers()[0]['handover_acknowledged'])
        self.assertFalse(self.reviews.checked('one', self.before))

    def test_0400_resets_checks_but_not_handover_or_acknowledgement(self):
        self.reviews.record(self.item, self.before)
        self.reviews.acknowledge('one', True)
        snapshot = self.reviews.handovers()
        self.assertTrue(self.reviews.checked('one', self.before))
        self.assertFalse(self.reviews.checked('one', self.after))
        self.assertEqual(self.reviews.handovers(), snapshot)
        self.assertTrue(self.reviews.handovers()[0]['handover_acknowledged'])

    def test_check_at_exact_boundary_belongs_to_new_day(self):
        self.reviews.record(self.item, self.after)
        self.assertTrue(self.reviews.checked('one', self.after))
        self.assertFalse(self.reviews.checked('one', self.before))

    def test_utc_and_japan_boundary_match(self):
        self.assertEqual(self.reviews.day_key(datetime(2026,11,11,18,59,59,tzinfo=timezone.utc)), '2026-11-11')
        self.assertEqual(self.reviews.day_key(datetime(2026,11,11,19,0,0,tzinfo=timezone.utc)), '2026-11-12')

    def test_manual_uncheck_preserves_all_result_fields(self):
        self.reviews.record(self.item, self.before)
        saved = self.reviews.handovers()
        self.reviews.uncheck(['one'], self.before)
        self.assertFalse(self.reviews.checked('one', self.before))
        self.assertEqual(self.reviews.handovers(), saved)

    def test_note_edit_after_cutoff_does_not_recheck(self):
        self.reviews.record(self.item, self.before)
        self.item['note'] = '翌朝の追記'
        with patch('store_preview.core.live_board_review.now_jst', return_value=self.after):
            self.reviews.update_note(self.item)
            self.assertFalse(self.reviews.checked('one'))
        self.assertEqual(self.reviews.handovers()[0]['note'], '翌朝の追記')
        self.assertEqual(self.reviews.handovers()[0]['confirmed_at'], self.before.isoformat(timespec='seconds'))

    def test_restart_and_days_without_opening_preserve_handover(self):
        self.reviews.record(self.item, self.before)
        restored = LiveBoardReviewManager(DataManager(self.path))
        self.assertTrue(restored.checked('one', self.before))
        self.assertFalse(restored.checked('one', datetime(2026,12,1,12,tzinfo=JAPAN)))
        self.assertEqual(restored.handovers(), self.reviews.handovers())

    def test_recheck_replaces_result_and_clears_previous_ack(self):
        self.reviews.record(self.item, self.before)
        self.reviews.acknowledge('one', True)
        self.item['status'] = 'done'
        self.reviews.record(self.item, self.after)
        self.assertEqual(len(self.reviews.handovers()), 1)
        self.assertEqual(self.reviews.handovers()[0]['status'], 'done')
        self.assertFalse(self.reviews.handovers()[0]['handover_acknowledged'])

    def test_initialization_is_once_and_does_not_modify_existing_records(self):
        self.data.data['store_service_prep_records']={'2026-11-11': {'dinner': {'one': 'attention'}}}
        prior = deepcopy(self.data.data)
        self.reviews.initialize_handover([self.item])
        self.reviews.initialize_handover([])
        self.assertEqual(len(self.reviews.handovers()), 1)
        for key,value in prior.items():
            self.assertEqual(self.data.data[key], value)

    def test_handover_has_all_checked_types_and_returns_copies(self):
        for n,kind in enumerate(('completion','status','quantity','memo')):
            self.reviews.record({**self.item, 'id': str(n), 'item_type':kind},self.before)
        values=self.reviews.handovers()
        self.assertEqual(len(values),4)
        values[0]['note']='outside mutation'
        self.assertNotEqual(self.reviews.handovers()[0]['note'],'outside mutation')


if __name__ == '__main__':
    unittest.main()
