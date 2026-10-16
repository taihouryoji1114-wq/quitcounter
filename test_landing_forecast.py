from datetime import date
import unittest,tempfile
from pathlib import Path
from core.data import DataManager
from core.landing_forecast import monthly_forecast,simulate,save_snapshot
class ForecastTest(unittest.TestCase):
    def test_missing_is_not_zero_and_today_is_not_actual(self):
        records=[{'date':'2026-10-01','amount':100},{'date':'2026-10-03','amount':999}]
        r=monthly_forecast(records,'2026-10',date(2026,10,3))
        self.assertEqual(r['actual'],100);self.assertEqual(r['daily_average'],100)
        self.assertEqual(r['missing'],['2026-10-02']);self.assertEqual(r['landing'],3100)
        self.assertEqual(r['imputed'],100)
        self.assertEqual(r['remaining'],2900)
        self.assertEqual(simulate(r,sales_percent=10)['sales'],3390)
        r=monthly_forecast(records,'2026-10',date(2026,10,3),closed_dates=['2026-10-02'])
        self.assertEqual(r['landing'],3000)
    def test_seasonal_and_simulation(self):
        records=[{'date':f'2025-10-{d:02d}','amount':1000,'lunch_customers':3,'dinner_customers':7} for d in range(1,32)]
        r=monthly_forecast(records,'2026-10',date(2026,10,1))
        self.assertEqual(r['landing'],31000);self.assertEqual(r['customers'],310)
        self.assertTrue(all(e['basis']=='前年同月・同曜日' for e in r['estimates']))
        v=simulate(r,10,100,30,50,20,1000,2000)
        self.assertEqual(v['sales'],65100);self.assertEqual(v['profit_delta'],19870)
    def test_snapshot_immutable(self):
        with tempfile.TemporaryDirectory() as folder:
            dm=DataManager(Path(folder)/'data.json')
            f={'month':'2026-10','as_of':'2026-10-01','landing':100}
            save_snapshot(dm,f);f['landing']=200;save_snapshot(dm,f)
            self.assertEqual(dm.data['landing_forecast_history']['2026-10/2026-10-01']['forecast']['landing'],100)
    def test_no_customer_data_no_price_simulation(self):
        r=monthly_forecast([{'date':'2026-09-30','amount':100}],'2026-10',date(2026,10,1))
        with self.assertRaises(ValueError):simulate(r,price_change=100)
