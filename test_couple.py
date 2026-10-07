import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.data import DataManager
from core.couple import CoupleGarden
from core.clock import today_jst

class CoupleTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'data.json'
        self.g=CoupleGarden(DataManager(self.path))

    def test_two_people_idempotent_and_persistent(self):
        self.g.check('user1'); self.g.check('user1'); self.g.check('user2')
        saved=CoupleGarden(DataManager(self.path)).state('user1')
        self.assertEqual(saved['days'][today_jst().isoformat()]['thanks'], ['user1','user2'])
        self.g.check('user2',True)
        self.assertEqual(len(self.g.state('user1')['days'][today_jst().isoformat()]['thanks']),2)

    def test_private_notes_and_ownership(self):
        self.g.note('user1','ありがとう','private')
        self.g.note('user1','ありがとう','shared',True)
        self.assertEqual([n['text'] for n in self.g.state('user2')['notes']],['shared'])
        private=self.g.state('user1')['notes'][0]['id']
        with self.assertRaises(ValueError):self.g.delete_note('user2',private)
        with self.assertRaises(ValueError):self.g.state('staff')
        self.g.delete_note('user1',private)
        self.assertEqual(len(self.g.state('user1')['notes']),1)

    def test_meeting_and_access(self):
        self.g.meeting('user1',today_jst().isoformat(),'最後まで話を聞く')
        self.assertEqual(len(self.g.state('user2')['meetings']),1)
        with self.assertRaises(ValueError):self.g.meeting('user1','2099-01-01','future')
        import pages.couple as page
        with patch.object(page,'is_authenticated',return_value=True),patch.object(page,'current_role',return_value='staff'):
            with self.assertRaises(ValueError):page.person_id()

    def test_page_renders(self):
        from nicegui import ui
        import pages.couple as page
        with patch.object(page,'person_id',return_value='user1'),patch.object(page,'garden',self.g):
            with ui.column():page.couple_page()
