import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.data import DataManager
from core.shift_board import ShiftBoardManager


class ShiftBoardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'data.json'
        self.board = ShiftBoardManager(DataManager(self.path))

    def test_only_published_snapshot_is_shared_and_survives_reload(self):
        self.board.save_staff(2026, 9, 'スタッフA', {'1': '11:00〜15:00', '2': '休み', '3': ''})
        self.assertIsNone(self.board.month(2026, 9)['published'])
        self.board.publish(2026, 9)
        self.board.save_staff(2026, 9, 'スタッフA', {'1': '17:00〜22:00'})
        result = ShiftBoardManager(DataManager(self.path)).month(2026, 9)
        self.assertEqual(result['published']['entries']['スタッフA']['1'], '11:00〜15:00')
        self.assertEqual(result['published']['entries']['スタッフA']['2'], '休み')
        self.assertNotIn('3', result['published']['entries']['スタッフA'])
        self.assertEqual(result['draft']['スタッフA']['1'], '17:00〜22:00')
        self.assertIsNone(self.board.month(2026, 10)['published'])
        self.board.publish(2026, 9)
        self.assertEqual(self.board.month(2026, 9)['published']['entries']['スタッフA']['1'], '17:00〜22:00')

    def test_validation_is_atomic_and_preserves_other_people(self):
        self.board.save_staff(2026, 9, 'スタッフA', {'1': 'ランチ'})
        self.board.save_staff(2026, 9, 'スタッフB', {'2': '休み'})
        before = self.board.month(2026, 9)
        for entries in ({'31': 'ランチ'}, {'1': 'a' * 101}):
            with self.assertRaises(ValueError):
                self.board.save_staff(2026, 9, 'スタッフA', entries)
        self.assertEqual(before, self.board.month(2026, 9))
        with self.assertRaises(ValueError):
            self.board.publish(2026, 10)
        self.board.publish(2026, 9)
        self.assertEqual(set(self.board.month(2026, 9)['published']['entries']), {'スタッフA','スタッフB'})

    def test_editor_permission_checked_and_pages_render(self):
        from nicegui import ui
        import pages.store_shift_board as page
        with patch.object(page, 'has_permission', return_value=False):
            with self.assertRaises(ValueError):
                page.check_editor()
        for manager in (False, True):
            with patch.object(page, 'require_app_access', return_value=True), \
                 patch.object(page, 'current_staff_id', return_value='スタッフA'), \
                 patch.object(page, 'has_permission', return_value=manager), \
                 patch.object(page, 'store_header_actions', lambda: None), \
                 patch.object(page, 'shift_board', self.board):
                with ui.column():
                    page.shift_board_page()
                self.board.save_staff(2026, 9, 'スタッフA', {'1':'ランチ'})
                self.board.publish(2026, 9)
                with ui.column():
                    page.shift_board_page()

if __name__ == '__main__':
    unittest.main()

class ShiftBoardWishTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = DataManager(Path(self.temp.name) / 'data.json')
        self.board = ShiftBoardManager(self.data)
        self.data.data['store_shift_submissions'] = {'2026-10-first': {'スタッフA': {
            'submitted_at': '2026-09-20', 'days': {'1': {'type': 'ランチ','start':'11:30','end':'14:00'},
                '2': {'type':'絶対休み'}, '3':{'type':'通し','start':'11:00','end':'22:00'}}}}}

    def test_wishes_warnings_and_manual_time(self):
        cell = self.board.resolve(2026,10,'スタッフA','1','ランチ')
        self.assertIn('11:30〜14:00',cell['text'])
        self.assertEqual(cell['warning'],'')
        self.assertIn('希望はランチ',self.board.resolve(2026,10,'スタッフA','1','ディナー')['warning'])
        self.assertIn('休み希望',self.board.resolve(2026,10,'スタッフA','2','通し')['warning'])
        self.assertIn('希望がありません',self.board.resolve(2026,10,'スタッフA','4','ランチ')['warning'])
        self.assertIn('全体の時間',self.board.resolve(2026,10,'スタッフA','3','ランチ')['warning'])
        manual=self.board.resolve(2026,10,'スタッフA','1','ランチ 12:00〜15:00')
        self.assertEqual(manual['text'],'ランチ 12:00〜15:00')
        self.assertIn('異なります',manual['warning'])
        self.assertNotIn('副社長',self.board.STAFF)

    def test_half_publish_freezes_times_and_preserves_other_half(self):
        self.board.save_staff(2026,10,'スタッフA',{'1':'ランチ','16':'ディナー'})
        self.board.publish(2026,10,'first')
        first=self.board.month(2026,10)['published']
        self.assertNotIn('16',first['entries']['スタッフA'])
        self.assertNotIn('second',first['periods'])
        self.data.data['store_shift_submissions']['2026-10-first']['スタッフA']['days']['1']['start']='12:00'
        self.board.publish(2026,10,'second')
        final=self.board.month(2026,10)['published']
        self.assertIn('11:30',final['cells']['スタッフA']['1']['text'])
        self.assertEqual(final['entries']['スタッフA']['16'],'ディナー')
        expected=self.board.resolved(2026,10,{'スタッフA':{'1':'ランチ'}})
        self.data.data['store_shift_submissions']['2026-10-first']['スタッフA']['days']['1']['end']='13:00'
        with self.assertRaises(ValueError):self.board.publish(2026,10,'first',expected=expected)

    def test_inventory_timestamp_label(self):
        from pages.purchase_list import inventory_check_label
        self.assertEqual(inventory_check_label({'last_inventory_check_at':'2026-10-09T01:15:00+00:00'}),'在庫確認 2026/10/09 10:15')
        self.assertEqual(inventory_check_label({}),'在庫確認日時：記録なし')

class ApprovedBoardUpdateTest(unittest.TestCase):
    def test_approval_only_updates_published_person_and_half(self):
        from core.shift_submissions import ShiftSubmissionManager
        with tempfile.TemporaryDirectory() as tmp:
            data = DataManager(Path(tmp) / 'data.json')
            board = ShiftBoardManager(data)
            submissions = ShiftSubmissionManager(data)
            key = '2026-10-first'
            data.data['store_shift_submissions'] = {key: {'スタッフA': {
                'submitted_at': '2026-09-20', 'days': {'1': {'type':'ランチ','start':'11:00','end':'14:00'}}}}}
            board.save_staff(2026,10,'スタッフA',{'1':'ランチ','2':'ランチ 12:00〜15:00','16':'ディナー'})
            board.publish(2026,10)
            original = board.month(2026,10)['published']
            board.save_staff(2026,10,'スタッフA',{'1':'通し','3':'ランチ'})
            def request():
                data.data['store_shift_change_requests'] = {key: {'スタッフA': {'status':'pending', 'days': {
                    '1': {'type':'ランチ','start':'12:00','end':'15:00'},
                    '2': {'type':'絶対休み'}}}}}
            request()
            self.assertEqual(board.month(2026,10)['published'],original)
            submissions.review_change('スタッフA',2026,10,'first',False)
            self.assertEqual(board.month(2026,10)['published'],original)
            request()
            submissions.review_change('スタッフA',2026,10,'first',True)
            updated=board.month(2026,10)['published']
            self.assertEqual(updated['entries'],original['entries'])
            self.assertIn('12:00〜15:00',updated['cells']['スタッフA']['1']['text'])
            self.assertEqual(updated['cells']['スタッフA']['2']['text'],'ランチ 12:00〜15:00')
            self.assertIn('休み希望',updated['cells']['スタッフA']['2']['warning'])
            self.assertEqual(updated['cells']['スタッフA']['16'],original['cells']['スタッフA']['16'])
            self.assertNotIn('3',updated['entries']['スタッフA'])
            restored=ShiftBoardManager(DataManager(Path(tmp)/'data.json'))
            self.assertEqual(restored.month(2026,10)['published'],updated)

class LegacyShiftTimesTest(unittest.TestCase):
    def test_legacy_board_backfills_accepted_time_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = DataManager(Path(tmp)/'data.json')
            data.data['store_manual_shift_board'] = {'2026-10': {'draft': {}, 'published': {
                'entries': {'スタッフA': {'1':'ランチ'}}, 'updated_at':'2026/10/01 10:00'}}}
            data.data['store_shift_submissions'] = {'2026-10-first': {'スタッフA': {
                'submitted_at':'2026-09-20', 'days': {'1':{'type':'ランチ','start':'11:30','end':'14:30'}}}}}
            data.data['store_shift_change_requests'] = {'2026-10-first': {'スタッフA': {
                'status':'pending','days':{'1':{'type':'ランチ','start':'12:30','end':'15:00'}}}}}
            board = ShiftBoardManager(data)
            first = board.month(2026,10)['published']['cells']['スタッフA']['1']
            self.assertIn('11:30〜14:30',first['text'])
            self.assertNotIn('12:30',first['text'])
            data.data['store_shift_submissions']['2026-10-first']['スタッフA']['days']['1']['start']='13:00'
            self.assertEqual(board.month(2026,10)['published']['cells']['スタッフA']['1'],first)
