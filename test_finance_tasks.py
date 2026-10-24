import unittest
from copy import deepcopy
from datetime import date
from core.finance_tasks import build_finance_tasks

class Memory:
    def __init__(self):
        self.data={'business_monthly_operations':{'2026-10':{}},'business_monthly_advertising':{'2026-10':{}},'business_sales':[dict(date=f'2026-10-{d:02d}',amount=0) for d in range(1,5)]}

class FinanceTasksTests(unittest.TestCase):
    def test_explicit_zero_and_no_purchases_are_not_missing(self):
        manager=Memory();before=deepcopy(manager.data)
        self.assertEqual(build_finance_tasks(manager,'2026-10',date(2026,10,5),{}),[])
        self.assertEqual(manager.data,before)
    def test_sales_excludes_today_future_and_closed_day(self):
        m=Memory();m.data['business_sales']=[];m.data['landing_forecast_settings']={'closed_dates':['2026-10-02']}
        tasks=build_finance_tasks(m,'2026-10',date(2026,10,4),{})
        sales=next(t for t in tasks if t['area']=='売上')
        self.assertEqual([i['date'] for i in sales['items']],['2026-10-01','2026-10-03'])
        self.assertEqual(sales['items'][1]['path'],'/mirai-kessan/sales?date=2026-10-03')
    def test_monthly_costs_lead_to_selected_month_form(self):
        m=Memory();m.data['business_monthly_operations']={}
        t=build_finance_tasks(m,'2026-10',date(2026,10,5),{})[0]
        self.assertEqual(t['items'][0]['path'],'/mirai-kessan/details?month=2026-10')
    def test_published_work_requires_actual_but_off_blank_and_future_do_not(self):
        m=Memory();m.data['store_manual_shift_board']={'2026-10':{'published':{'entries':{'スタッフA':{'1':'ランチ','2':'休み','5':'ランチ'}},'cells':{}}}}
        tasks=build_finance_tasks(m,'2026-10',date(2026,10,5),{})
        work=next(t for t in tasks if t['area']=='人件費')
        self.assertEqual(len(work['items']),1)
        self.assertIn('Ha',work['items'][0]['detail'])
        m.data['business_staff_hours']={'2026-10-01':{'スタッフA':{'entry_confirmed':True}}}
        self.assertEqual(build_finance_tasks(m,'2026-10',date(2026,10,5),{}),[])
    def test_payroll_and_tax_missing_provide_actions(self):
        outlook={'payroll_issues':[{'reason':'シフトが未公開','staff':'スタッフA','date':'2026-10-07'},{'reason':'時給が未登録','staff':'スタッフB','date':'2026-10-07'}], 'report':{'settlement':{'tax':{'issues':[{}]}}}}
        tasks=build_finance_tasks(Memory(),'2026-10',date(2026,10,5),outlook)
        self.assertEqual([t['items'][0]['path'] for t in tasks],['/store-ops/shift-board','/mirai-kessan/staffing','/mirai-kessan/taxes?month=2026-10'])
    def test_future_month_not_missing(self):
        self.assertEqual(build_finance_tasks(Memory(),'2026-11',date(2026,10,5),{}),[])
