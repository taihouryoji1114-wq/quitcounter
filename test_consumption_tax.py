import unittest
from copy import deepcopy
from datetime import date
from core.financials import FinancialManager
from core.purchases import PurchaseManager
from core.consumption_tax import period_tax, settlement, forecast_credits, transition_rate, validate_tax_settings
from core.financial_report_data import build_financial_report
from core.monthly_evaluation import MonthlyEvaluationService
from core.annual_reports import AnnualReportManager
from core.wealth_forecast import accumulate


class Memory:
    def __init__(self): self.data={}
    def save(self): pass

class NoStaff:
    def month_cost_summary(self,*args): return {'company_cost':0}

class TaxCalculationTests(unittest.TestCase):
    def setUp(self):
        self.store=Memory(); self.f=FinancialManager(self.store); self.p=PurchaseManager(self.store)
    def purchase(self,amount,rate,kind='cost',day='2026-10-01',status='registered'):
        breakdown=self.p.calculate_tax_breakdown(**{'amount_'+str(rate):amount},price_mode='included')
        return self.p.add(day,'test',amount,kind,breakdown,status)
    def settings(self,**kwargs):
        self.store.data.setdefault('business_tax_settings',{})['2026-10']=kwargs
    def test_gross_inputs_all_categories_and_no_double_subtraction(self):
        self.f.set_daily_sales('2026-10-01',1100000)
        self.purchase(324000,8);self.purchase(11000,10,'expense')
        self.f.save_monthly_operations('2026-10',personnel=200000,rent=110000,utilities=55000)
        self.f.save_monthly_advertising('2026-10',tabelog=22000)
        self.settings(expenses={k:dict(rate='10',status='registered') for k in ('rent','utilities','tabelog')},corporate_tax_amount=30000)
        r=build_financial_report('2026-10-01','2026-10-31',self.f,self.p,NoStaff(),date(2026,11,1))
        self.assertEqual(r['gross_profit'],776000)
        self.assertEqual(r['operating_profit'],378000)
        self.assertEqual(r['settlement']['tax']['net_tax'],58000)
        self.assertEqual(r['settlement']['pretax_profit'],320000)
        self.assertEqual(r['settlement']['net_profit'],290000)
    def test_unknown_credit_and_missing_corporate_never_look_final(self):
        self.f.set_daily_sales('2026-10-01',110000)
        r=self.purchase(11000,10,status='unknown')
        tax=period_tax(self.f,self.p,'2026-10-01','2026-10-31')
        self.assertEqual(tax['net_tax'],10000);self.assertEqual(tax['unconfirmed_credit'],1000)
        settled=settlement(self.f,self.p,dict(start='2026-10-01',end='2026-10-31',operating_profit=99000))
        self.assertIsNone(settled['corporate_tax']);self.assertIn('法人税前',settled['surplus_label'])
        self.p.review_credit(r['id'],'registered')
        self.assertEqual(period_tax(self.f,self.p,'2026-10-01','2026-10-31')['net_tax'],9000)
    def test_transition_requires_review_and_follows_purchase_date(self):
        self.assertEqual(transition_rate('2026-09-30'),.8)
        self.assertEqual(transition_rate('2026-10-01'),.7)
        self.assertEqual(transition_rate('2028-10-01'),.5)
        self.assertEqual(transition_rate('2030-10-01'),.3)
        self.assertEqual(transition_rate('2031-10-01'),0)
        r=self.purchase(11000,10,status='unregistered')
        self.assertEqual(self.p.monthly_tax_summary('2026-10')['input_tax'],0)
        self.p.review_credit(r['id'],'transition')
        self.assertEqual(self.p.monthly_tax_summary('2026-10')['input_tax'],700)
        self.p.update(r['id'],r['date'],r['supplier'],r['total'],invoice_status='unregistered')
        self.assertFalse(r.get('transition_eligible'))
    def test_same_dates_for_report_evaluation_and_tax(self):
        self.f.set_daily_sales('2026-10-01',110000)
        self.purchase(11000,10,day='2026-10-25')
        self.f.save_monthly_operations('2026-10',rent=31000,loan_payment=31000)
        self.settings(expenses={'rent':dict(rate='10',status='registered')},corporate_tax_amount=0)
        before=deepcopy(self.store.data)
        r=build_financial_report('2026-10-01','2026-10-10',self.f,self.p,NoStaff(),date(2026,10,10))
        snap=MonthlyEvaluationService(self.f,self.p,NoStaff()).snapshot('2026-10',date(2026,10,10))
        self.assertEqual(r['settlement']['loan_payment'],10000)
        self.assertEqual(r['settlement']['tax']['input_tax'],909)
        self.assertEqual(snap['post_repayment_profit'],r['settlement']['post_repayment_profit'])
        self.assertEqual(before,self.store.data)
    def test_tax_payment_reconciliation_and_principal_only_in_surplus(self):
        self.f.set_daily_sales('2026-10-01',1100000)
        self.f.save_monthly_operations('2026-10',loan_payment=400000)
        self.settings(tax_payments_in_expenses=100000,corporate_tax_amount=0,interest=20000,depreciation=30000)
        r=settlement(self.f,self.p,dict(start='2026-10-01',end='2026-10-31',operating_profit=1000000))
        self.assertEqual(r['net_profit'],950000)
        self.assertEqual(r['post_repayment_profit'],580000)
    def test_forecast_keeps_food_and_supplies_credit_separate(self):
        self.purchase(108000,8);self.purchase(110000,10,'operating_supply')
        result=forecast_credits(self.f,self.p,'2026-10',date(2026,10,31),108000,0)
        self.assertEqual(result['current_credit'],18000)
        self.assertEqual(550000*10/110-result['current_credit'],32000)
    def test_fiscal_credit_offsets_other_month_without_cash_refund(self):
        def row(month,tax): return dict(month=month,operating=100000,consumption_tax=tax,interest=0,depreciation=0,principal=0,investment=0,dividend=0)
        a=accumulate([row('2026-10',-20000),row('2026-11',50000)],0)[0]
        self.assertEqual(a['net'],170000);self.assertEqual(a['surplus_delta'],170000)
        b=accumulate([row('2026-10',-20000)],0)[0]
        self.assertEqual(b['net'],120000);self.assertEqual(b['surplus_delta'],100000)
    def test_annual_corporate_tax_and_confirmation_survive_save(self):
        manager=AnnualReportManager(self.store)
        report=manager.save_report('2026-09',dict(sales=1000000,corporate_taxes=300000))
        self.assertEqual(manager.calculate(report['current'])['net_income'],700000)
        self.assertIn('未確認',manager.calculate(dict(sales=100))['net_label'])
        report=manager.save_report('2027-09',dict(sales=100,corporate_taxes=0,corporate_tax_confirmed=True))
        self.assertEqual(manager.calculate(report['current'])['net_label'],'当期純利益')
    def test_settings_reject_non_finite_or_negative(self):
        for value in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):validate_tax_settings({'interest':value},30)

    def test_mixed_month_tax_keeps_registered_amount(self):
        self.f.set_daily_sales('2026-09-01',110000)
        self.f.set_daily_sales('2026-10-01',110000)
        self.store.data['business_tax_settings']={'2026-09':dict(corporate_tax_amount=50000)}
        self.store.data['finance_tax_policy']={'corporate_rate':30}
        r=build_financial_report('2026-09-01','2026-10-31',self.f,self.p,NoStaff(),date(2026,11,1))
        self.assertEqual(r['settlement']['corporate_tax'],80000)
        self.assertEqual(r['settlement']['net_profit'],120000)

    def test_payment_fee_credit_uses_dated_sales_not_day_proration(self):
        self.f.save_payment_fee_rates({"credit":3})
        self.store.data['business_sales']=[dict(id='a',date='2026-10-01',amount=110000,credit_sales=110000),dict(id='b',date='2026-10-31',amount=110000,credit_sales=110000)]
        self.settings(expenses={'payment_fees':dict(rate='10',status='registered')})
        first=period_tax(self.f,self.p,'2026-10-01','2026-10-01')
        full=period_tax(self.f,self.p,'2026-10-01','2026-10-31')
        self.assertGreater(full['input_tax'],0)
        self.assertAlmostEqual(first['input_tax'],full['input_tax']/2,delta=1)
