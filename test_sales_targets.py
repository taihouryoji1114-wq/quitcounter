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

class RecommendationTests(unittest.TestCase):
    def test_only_remaining_sales_are_increased(self):
        from core.sales_targets import recommend_target
        records=[{'date':f'2026-11-{d:02d}','amount':100} for d in range(1,16)]
        result=recommend_target(records,'2026-11',date(2026,11,16))
        self.assertEqual(result['forecast']['landing'],3000)
        self.assertEqual(result['target'],3075)
        self.assertEqual(result['uplift'],.05)
    def test_sparse_missing_empty_and_finished(self):
        from core.sales_targets import recommend_target
        records=[{'date':'2026-11-01','amount':100}]
        result=recommend_target(records,'2026-11',date(2026,11,3))
        self.assertEqual(result['target'],result['forecast']['landing'])
        self.assertEqual(result['uplift'],0)
        self.assertIsNone(recommend_target([],'2026-11',date(2026,11,1))['target'])
        self.assertIsNone(recommend_target(records,'2026-11',date(2026,12,1))['target'])
    def test_closed_days_and_seasonal_baseline(self):
        from core.sales_targets import recommend_target
        records=[{'date':f'2025-11-{d:02d}','amount':200} for d in range(1,31)]
        result=recommend_target(records,'2026-11',date(2026,11,1),['2026-11-01'])
        self.assertEqual(result['target'],5800)
        self.assertEqual(result['forecast']['remaining_days'],29)
    def test_new_ui_renders_with_and_without_saved_goal(self):
        from unittest.mock import patch
        from nicegui import ui
        from pages.sales_targets import render_sales_targets
        plan=build_target_plan([],'2026-11',3000,date(2026,10,30))
        plan.update(id='saved',created_at='2026-10-30T12:00:00')
        for plans in ({},{'saved':plan}):
            with patch('pages.sales_targets.data',SimpleNamespace(data={'sales_target_plans':plans})),patch('pages.sales_targets.financials.sales_records',return_value=[]),patch('pages.sales_targets.today_jst',return_value=date(2026,10,30)):
                with ui.column():render_sales_targets('2026-11')

    def test_automatic_plan_without_manual_target_does_not_write(self):
        from core.sales_targets import automatic_target_plan
        from copy import deepcopy
        records=[{'date':'2026-10-29','amount':100}]
        before=deepcopy(records)
        plan=automatic_target_plan(records,'2026-11',date(2026,10,30))
        self.assertEqual(plan['id'],'automatic')
        self.assertEqual(plan['monthly_target'],3000)
        self.assertEqual(sum(r['target'] for r in plan['rows']),3000)
        self.assertEqual(records,before)
        self.assertIsNone(automatic_target_plan([],'2026-11',date(2026,10,30)))

    def test_zero_mode_preserves_history_and_positive_save_restores(self):
        from core.sales_targets import use_automatic_landing,automatic_target_plan
        manager=SimpleNamespace(data={},save=lambda:None)
        original=save_target_plan(manager,build_target_plan([],'2026-11',9000,date(2026,10,30)))
        use_automatic_landing(manager,'2026-11')
        self.assertEqual(manager.data['sales_target_modes']['2026-11'],'landing')
        self.assertEqual(manager.data['sales_target_plans'][original['id']]['monthly_target'],9000)
        records=[{'date':f'2026-11-{d:02d}','amount':100} for d in range(1,16)]
        automatic=automatic_target_plan(records,'2026-11',date(2026,11,16),use_landing=True)
        self.assertEqual(automatic['monthly_target'],3000)
        self.assertEqual(automatic_target_plan(records,'2026-11',date(2026,11,16))['monthly_target'],3075)
        save_target_plan(manager,build_target_plan(records,'2026-11',4000,date(2026,11,16)))
        self.assertEqual(manager.data['sales_target_modes']['2026-11'],'saved')
        self.assertEqual(len(manager.data['sales_target_plans']),2)
