import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from core.data import DataManager
from core.shift_submissions import ShiftSubmissionManager
from core.staff_identity import STAFF_NAMES, staff_display_name, personal_staff_account
from core.auth import authenticate_pin, log_in, require_staff_identity


class StaffPersonalTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.manager = ShiftSubmissionManager(DataManager(Path(self.temp.name) / 'data.json'))
        self.pin = '0193'
        self.manager.set_staff_pin('スタッフB', self.pin)
        self.lookup = patch('core.shift_submissions.shift_submissions', self.manager)
        self.lookup.start()

    def tearDown(self):
        self.lookup.stop()
        self.temp.cleanup()

    def test_leading_zero_and_display_names(self):
        self.assertEqual(list(STAFF_NAMES.values()), ['Ha','Na','Ka','Sy','Ma','Fu','Si'])
        self.assertEqual(personal_staff_account(self.pin)['display_name'], 'Na')
        self.assertIsNone(personal_staff_account('193'))
        self.assertEqual(staff_display_name('スタッフＦ'), 'Fu')

    def test_personal_pin_is_store_only_and_never_grants_owner(self):
        with patch.dict(os.environ, {'RBASE_OWNER_PIN': self.pin}, clear=True):
            result = authenticate_pin(self.pin, 'store_ops')
            self.assertEqual(result['role'], 'staff')
            self.assertEqual(result['staff_id'], 'スタッフB')
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(authenticate_pin(self.pin, 'portal'))
            self.assertIsNone(authenticate_pin(self.pin, 'future_financials'))

    def test_duplicate_pin_fails_closed(self):
        self.manager.set_staff_pin('スタッフA', self.pin)
        with patch.dict(os.environ, {'RBASE_OWNER_PIN': self.pin}, clear=True):
            self.assertIsNone(authenticate_pin(self.pin, 'store_ops'))

    def test_other_staff_cannot_be_selected_server_side(self):
        with patch('core.auth.current_staff_id', return_value='スタッフB'):
            require_staff_identity('スタッフB')
            with self.assertRaises(ValueError):
                require_staff_identity('スタッフA')

    def test_new_login_clears_previous_identity(self):
        session = {'staff_id':'スタッフA','staff_display_name':'Ha','account_user_id':'user1','selected_user_id':'user1'}
        with patch('core.auth.app', SimpleNamespace(storage=SimpleNamespace(user=session))):
            log_in({'role':'staff','user_id':'','staff_id':'スタッフB','display_name':'Na'})
            self.assertEqual(session['staff_id'], 'スタッフB')
            self.assertNotIn('account_user_id', session)
            log_in({'role':'staff','user_id':''})
            self.assertNotIn('staff_id', session)

    def test_personal_page_can_render_with_saved_identity(self):
        from nicegui import ui
        from core.shift_board import ShiftBoardManager
        import pages.store_personal as page
        with patch.object(page, 'require_app_access', return_value=True), \
             patch.object(page, 'current_staff_id', return_value='スタッフB'), \
             patch.object(page, 'store_header_actions', lambda: None), \
             patch.object(page, 'shift_submissions', self.manager), \
             patch.object(page, 'shift_board', ShiftBoardManager(self.manager._data_manager)):
            with ui.column():
                page.personal_home()

if __name__ == '__main__':
    unittest.main()
