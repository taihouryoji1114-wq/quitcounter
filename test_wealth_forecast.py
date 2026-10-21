import unittest
from datetime import date
from core.wealth_forecast import accumulate, project, fiscal_year, validate_settings


def row(month='2026-10', **changes):
    value = dict(month=month, operating=1000000, consumption_tax=0,
                 interest=0, depreciation=0, principal=400000, investment=0, dividend=0)
    value.update(changes)
    return value


class WealthForecastTests(unittest.TestCase):
    def test_user_example_and_opening_balances(self):
        result = accumulate([row()], 0, 3000000, 2000000)[0]
        self.assertEqual(result['retained_growth'], 1000000)
        self.assertEqual(result['surplus_growth'], 600000)
        self.assertEqual(result['retained_balance'], 4000000)
        self.assertEqual(result['surplus_balance'], 2600000)

    def test_depreciation_investment_dividend_and_tax_once(self):
        r = accumulate([row(operating=2000000, consumption_tax=100000,
                            interest=100000, depreciation=200000,
                            investment=300000, dividend=100000)], 25)[0]
        self.assertEqual(r['pretax'], 1600000)
        self.assertEqual(r['tax'], 400000)
        self.assertEqual(r['retained_growth'], 1100000)
        self.assertEqual(r['surplus_growth'], 600000)
        self.assertIsNone(r['retained_balance'])

    def test_fiscal_tax_nets_losses_but_does_not_invent_carryforward(self):
        r = accumulate([row('2026-08', operating=100, principal=0),
                        row('2026-09', operating=-200, principal=0),
                        row('2026-10', operating=100, principal=0)], 30)
        self.assertEqual(r[0]['tax'], 0)
        self.assertEqual(r[0]['retained_growth'], -100)
        self.assertEqual(r[1]['tax'], 30)
        self.assertEqual(r[1]['retained_growth'], -30)
        self.assertEqual(fiscal_year(date(2026,9,30)), 2026)
        self.assertEqual(fiscal_year(date(2026,10,1)), 2027)

    def fixture(self):
        base = dict(sales=3100000, projected_cost=930000, projected_fees=31000,
                    projected_personnel=500000, other_fixed=200000, principal=100000)
        settings = dict(corporate_tax_rate=30, repayment_end='2026-11', interest=10000)
        records = [dict(date=f'2025-12-{d:02d}', amount=200000) for d in range(1,32)]
        return base, settings, records

    def test_twenty_years_seasonality_and_loan_end(self):
        base, settings, records = self.fixture()
        r = project(base, records, settings, date(2026,10,18), 2046, 8/108)
        self.assertEqual(r['years'][-1]['year'], 2046)
        self.assertEqual(len(r['rows']), 240)
        months = {v['month']:v for v in r['rows']}
        self.assertEqual(months['2026-11']['principal'], 100000)
        self.assertEqual(months['2026-12']['principal'], 0)
        self.assertEqual(months['2026-12']['interest'], 0)
        self.assertEqual(months['2026-12']['sales'], 6200000)
        self.assertEqual(months['2045-12']['sales'], 6200000)
        self.assertNotIn(12, r['seasonal_missing'])
        self.assertIn(1, r['seasonal_missing'])

    def test_missing_data_and_manual_payroll(self):
        base, settings, records = self.fixture()
        base['projected_personnel'] = None
        self.assertFalse(project(base, records, settings, date(2026,10,18), 2028, 8/108)['years'])
        settings['payroll'] = 500000
        self.assertTrue(project(base, records, settings, date(2026,10,18), 2028, 8/108)['years'])
        settings['corporate_tax_rate'] = None
        self.assertTrue(project(base, records, settings, date(2026,10,18), 2028, 8/108)['years'])

    def test_invalid_inputs_and_explicit_zero(self):
        for settings in [dict(payroll=-1),dict(sales_growth=-100),dict(interest=float('nan')),dict(repayment_end='2026-99')]:
            with self.assertRaises(ValueError):validate_settings(settings)
        self.assertEqual(validate_settings(dict(corporate_tax_rate=0, opening_retained=-100))['opening_retained'], -100)
        for rate in (None,0,10,101):
            self.assertEqual(validate_settings(dict(corporate_tax_rate=rate))['corporate_tax_rate'],30)
        base, settings, records = self.fixture()
        settings['payroll'] = 0
        self.assertTrue(project(base, records, settings, date(2026,10,18), 2027, 0)['years'])

    def test_service_does_not_reuse_last_month_opening_balance(self):
        from unittest.mock import patch
        from core.wealth_forecast import load_projection
        base, settings, records = self.fixture()
        settings.update(opening_month='2026-09', opening_retained=9000000,
                        opening_surplus=4000000)
        base['messages'] = []
        with patch('core.finance_outlook.month_outlook', return_value=base), \
                patch('core.consumption_tax.forecast_credits', return_value=dict(fixed_credit=0,fee_fraction=0,current_credit=68889,cost_fraction=8/108,issues=[])), \
                patch('core.financials.financials') as finances, \
                patch('core.purchases.purchases') as purchases:
            finances.get_monthly_operations.return_value = {'loan_payment': 100000}
            finances._data_manager.data = {}
            finances.get_monthly_advertising.return_value = {'input_tax': 0}
            finances.sales_records.return_value = records
            purchases.monthly_total.return_value = 108000
            purchases.monthly_tax_summary.return_value = {'input_tax': 8000}
            r = load_projection(settings, date(2026,10,18), 2029)
            self.assertTrue(r['opening_stale'])
            self.assertIsNone(r['years'][0]['retained_balance'])
            self.assertEqual(settings['opening_retained'], 9000000)
            settings['opening_month'] = '2026-10'
            r = load_projection(settings, date(2026,10,18), 2029)
            self.assertFalse(r['opening_stale'])
            self.assertEqual(r['years'][0]['retained_balance'],
                             r['years'][0]['retained_growth'] + 9000000)
