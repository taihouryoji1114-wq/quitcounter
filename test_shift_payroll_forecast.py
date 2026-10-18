import tempfile
import unittest
from pathlib import Path
from datetime import date
from copy import deepcopy
from core.data import DataManager
from core.staffing import StaffingManager
from core.shift_payroll_forecast import effective_plans, board_shift

class ShiftPayrollTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = DataManager(Path(self.tmp.name)/'data.json')
        self.staff = StaffingManager(self.data)
        self.data.data['business_staff_wages'] = {'スタッフA': 1000, 'スタッフB': 1000}
        self.today = date(2026,10,18)
    def tearDown(self):
        self.tmp.cleanup()
    def board(self, text, kind='ディナー', warning=''):
        self.data.data['store_manual_shift_board'] = {'2026-10':{
            'draft':{'スタッフA':{'19':'ディナー 17:00〜23:00'}},
            'published':{'entries':{'スタッフA':{'19':text}},
                         'cells':{'スタッフA':{'19':dict(text=text,kind=kind,warning=warning)}}}}}
    def test_published_snapshot_precedes_legacy_plan_without_writes(self):
        self.board('ディナー\n希望 18:00〜22:00')
        self.data.data['business_staff_shift_plans'] = {'2026-10-19':{
            'スタッフA':dict(dinner_start='17:00',dinner_end='23:00'),
            'スタッフB':dict(lunch_start='10:00',lunch_end='12:00')}}
        before = deepcopy(self.data.data)
        s = self.staff.month_cost_summary('2026-10',self.today)
        self.assertEqual(s['planned_hourly_gross'],6000)
        self.assertEqual(s['plan_coverage']['board_cells'],1)
        self.assertEqual(s['company_cost'],0)
        self.assertEqual(before,self.data.data)
    def test_unpublished_draft_and_unapproved_requests_never_used(self):
        self.board('ディナー 18:00〜22:00')
        self.data.data['store_manual_shift_board']['2026-10']['published'] = None
        s = self.staff.month_cost_summary('2026-10',self.today)
        self.assertEqual(s['planned_hourly_gross'],0)
        self.assertEqual(s['plan_coverage']['board_cells'],0)
    def test_off_overrides_previous_work_and_partial_day_is_missing(self):
        self.board('休み','off')
        self.data.data['business_staff_shift_plans'] = {'2026-10-19':{'スタッフA':dict(dinner_start='18:00',dinner_end='22:00')}}
        plans, coverage = effective_plans(self.staff,'2026-10',self.today)
        self.assertFalse(self.staff._worked(plans['2026-10-19']['スタッフA']))
        self.assertNotIn('2026-10-19',coverage['missing_by_staff']['スタッフA'])
        self.assertIn('2026-10-19',coverage['missing_by_staff']['スタッフB'])
    def test_unknown_time_does_not_use_initial_default_or_old_plan(self):
        self.board('ランチ','ランチ')
        self.data.data['business_staff_shift_plans'] = {'2026-10-19':{'スタッフA':dict(lunch_start='10:00',lunch_end='15:00')}}
        plans, coverage = effective_plans(self.staff,'2026-10',self.today)
        self.assertFalse(self.staff._worked(plans['2026-10-19']['スタッフA']))
        self.assertIn('2026-10-19',coverage['missing_by_staff']['スタッフA'])
    def test_approved_snapshot_change_updates_cost(self):
        self.board('ディナー\n希望 18:00〜22:00')
        a = self.staff.month_cost_summary('2026-10',self.today)['planned_hourly_gross']
        self.data.data['store_manual_shift_board']['2026-10']['published']['cells']['スタッフA']['19']['text'] = 'ディナー\n希望 19:00〜22:00'
        b = self.staff.month_cost_summary('2026-10',self.today)['planned_hourly_gross']
        self.assertEqual(a-b,1000)
    def test_ambiguous_whole_day_request_and_invalid_times(self):
        for cell in [dict(text='ディナー\n希望 10:00〜22:00',kind='ディナー',warning='希望時間は通し全体の時間です。'),
                     dict(text='18:00〜99:00',kind='時間指定'),dict(text='18:00〜',kind='時間指定')]:
            self.assertIsNone(board_shift(cell,{})[0])
    def test_unknown_wage_and_night_premium(self):
        self.board('ディナー 22:00〜23:00')
        self.assertEqual(self.staff.month_cost_summary('2026-10',self.today)['planned_hourly_gross'],1250)
        self.data.data['business_staff_wages']['スタッフA']=0
        self.assertEqual(self.staff.month_cost_summary('2026-10',self.today)['plan_coverage']['unknown_wages'],1)
