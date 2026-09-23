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
