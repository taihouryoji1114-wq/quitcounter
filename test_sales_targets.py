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
