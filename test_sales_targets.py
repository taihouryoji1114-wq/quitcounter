from datetime import date
from types import SimpleNamespace
import unittest
from core.sales_targets import allocate, build_target_plan, save_target_plan, plan_results

class TargetTests(unittest.TestCase):
    def test_exact_allocation_and_empty_history(self):
        self.assertEqual(allocate(101,[1,1,1]),[34,34,33])
        p=build_target_plan([], '2026-11',3101,date(2026,10,18),['2026-11-01'])
        self.assertEqual(len(p['rows']),29)
        self.assertEqual(sum(r['target'] for r in p['rows']),3101)
        self.assertTrue(all(r['lunch']+r['dinner']==r['target'] for r in p['rows']))
        self.assertTrue(p['equal_allocation'])
    def test_missing_estimate_and_customer_targets(self):
        records=[{'date':'2026-10-01','amount':100,'lunch_sales':40,'dinner_sales':60,'lunch_customers':4,'dinner_customers':3}]
        p=build_target_plan(records,'2026-10',3100,date(2026,10,3))
        self.assertEqual(p['imputed'],100)
        self.assertEqual(p['remaining'],2900)
        self.assertEqual(p['rows'][0]['lunch_customers'],4)
        self.assertEqual(p['rows'][0]['dinner_customers'],3)
    def test_weekday_weights(self):
        records=[{'date':f'2026-09-{d:02d}','amount':200 if date(2026,9,d).weekday()==5 else 100} for d in range(1,31)]
        p=build_target_plan(records,'2026-10',3600,date(2026,10,1))
        by={r['date']:r['target'] for r in p['rows']}
        self.assertEqual(by['2026-10-03'],2*by['2026-10-02'])
    def test_immutable_plan_and_unknown_actual(self):
        dm=SimpleNamespace(data={},save=lambda:None)
        p=build_target_plan([], '2026-11',3000,date(2026,10,18))
        a=save_target_plan(dm,p);p['rows'][0]['target']=9999
        b=save_target_plan(dm,p)
        self.assertNotEqual(a['id'],b['id']);self.assertEqual(a['rows'][0]['target'],100)
        results=plan_results(a,[{'date':'2026-11-01','amount':0}],date(2026,11,3))
        self.assertEqual(results[0]['difference'],-100)
        self.assertIsNone(results[1]['actual'])
    def test_validation(self):
        for value in [-1,0,float('nan'),10.5]:
            with self.assertRaises(ValueError):build_target_plan([],'2026-11',value,date(2026,10,18))
        with self.assertRaises(ValueError):build_target_plan([],'2026-10',3000,date(2026,10,18))

class WeeklyAdjustmentTests(unittest.TestCase):
    def plan(self):
        return {'month':'2026-11','as_of':'2026-11-01','closed_dates':[], 'rows':[{'date':f'2026-11-{d:02d}','target':100,'lunch':40,'dinner':60} for d in range(1,8)]}
    def test_shortfall_and_excess_preserve_week_total(self):
        from core.sales_targets import weekly_adjustment
        from copy import deepcopy
        for actual in (0,50,150,900):
            p=self.plan();before=deepcopy(p)
            result=weekly_adjustment(p,[{'date':'2026-11-01','amount':actual}],date(2026,11,1),date(2026,11,2))
            future=[r['revised_target'] for r in result['rows'] if r['revised_target'] is not None]
            self.assertEqual(sum(future),max(0,700-actual))
            self.assertEqual(result['difference'],actual-100)
            self.assertEqual(p,before)
    def test_missing_is_not_zero_and_today_is_not_completed(self):
        from core.sales_targets import weekly_adjustment
        result=weekly_adjustment(self.plan(),[{'date':'2026-11-03','amount':10}],date(2026,11,1),date(2026,11,3))
        self.assertEqual(result['missing'],2)
        self.assertEqual(result['difference'],0)
        self.assertEqual(sum(r['revised_target'] or 0 for r in result['rows']),500)
    def test_finished_week_and_outside_week(self):
        from core.sales_targets import weekly_adjustment
        records=[{'date':f'2026-11-{d:02d}','amount':50} for d in range(1,8)]
        result=weekly_adjustment(self.plan(),records,date(2026,11,1),date(2026,11,9))
        self.assertEqual(result['unallocated'],350)
        self.assertTrue(all(r['revised_target'] is None for r in result['rows']))
        self.assertEqual(weekly_adjustment(self.plan(),records,date(2026,12,1),date(2026,12,2))['rows'],[])
    def test_print_includes_actual_and_adjusted_targets(self):
        from unittest.mock import patch
        from pages.sales_targets import target_table
        with patch('pages.sales_targets.today_jst',return_value=date(2026,11,2)),patch('pages.sales_targets.financials.sales_records',return_value=[{'date':'2026-11-01','amount':50}]):
            html=target_table(self.plan(),'2026-11-01',True)
        self.assertIn('¥50',html)
        self.assertIn('-50円',html)
        self.assertIn('新目標',html)
        self.assertIn('¥650',html)
        self.assertNotIn('手書き用',html)

    def test_past_actual_without_target_is_visible_in_print(self):
        from unittest.mock import patch
        from pages.sales_targets import target_table
        p=self.plan();p['as_of']='2026-11-06';p['rows']=p['rows'][5:]
        with patch('pages.sales_targets.today_jst',return_value=date(2026,11,6)),patch('pages.sales_targets.financials.sales_records',return_value=[{'date':'2026-11-01','amount':12345}]),patch('pages.sales_targets.data',SimpleNamespace(data={})):
            html=target_table(p,'2026-11-01',True)
        self.assertIn('¥12,345',html)
        self.assertIn('目標未設定',html)
        self.assertIn('入力済み1日分',html)

    def test_historical_targets_and_no_double_adjustment(self):
        from core.sales_targets import with_historical_targets, weekly_adjustment
        from copy import deepcopy
        old=self.plan();old['created_at']='2026-11-01T10:00:00'
        current=self.plan();current.update(as_of='2026-11-06',created_at='2026-11-06T10:00:00');current['rows']=current['rows'][5:]
        original=deepcopy(current)
        later=deepcopy(old);later['created_at']='2026-11-07T10:00:00';later['rows'][0]['target']=9999
        merged=with_historical_targets(current,[old,later])
        self.assertEqual(merged['rows'][0]['target'],100)
        self.assertTrue(merged['rows'][0]['historical_target'])
        result=weekly_adjustment(merged,[{'date':'2026-11-01','amount':50}],date(2026,11,1),date(2026,11,6))
        self.assertEqual(result['difference'],-50)
        self.assertEqual(sum(r['revised_target'] or 0 for r in result['rows']),200)
        self.assertEqual(original,current)
