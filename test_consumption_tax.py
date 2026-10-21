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
        self.assertEqual(r['settlement']['net_profit'],224000)
    def test_purchases_automatically_credit_all_statuses_without_mutation(self):
        self.f.set_daily_sales('2026-10-01',110000)
        rows=[self.purchase(11000,10,status=status) for status in ('unknown','registered','unregistered')]
        rows[-1]['credit_reviewed']=True
        before=deepcopy(self.store.data)
        tax=period_tax(self.f,self.p,'2026-10-01','2026-10-31')
        self.assertEqual(tax['net_tax'],7000)
        self.assertEqual(tax['unconfirmed_credit'],0)
        self.assertEqual(tax['issues'],[])
        self.assertEqual(before,self.store.data)
        settled=settlement(self.f,self.p,dict(start='2026-10-01',end='2026-10-31',operating_profit=77000))
        self.assertEqual(settled['corporate_tax'],21000)
        self.assertEqual(settled['net_profit'],49000)

    def test_legacy_purchase_estimates_tax_without_confirmation_task(self):
        self.p.add('2026-10-01','food',10800)
        self.p.add('2026-10-01','supply',11000,'operating_supply')
        tax=period_tax(self.f,self.p,'2026-10-01','2026-10-31')
        self.assertEqual(tax['input_tax'],1800)
        self.assertEqual(tax['issues'],[])

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
        self.assertEqual(r['net_profit'],665000)
        self.assertEqual(r['post_repayment_profit'],295000)
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

    def test_fixed_rate_ignores_legacy_month_amount_and_saved_rate(self):
        self.f.set_daily_sales('2026-09-01',110000)
        self.f.set_daily_sales('2026-10-01',110000)
        self.store.data['business_tax_settings']={'2026-09':dict(corporate_tax_amount=50000)}
        self.store.data['finance_tax_policy']={'corporate_rate':10}
        r=build_financial_report('2026-09-01','2026-10-31',self.f,self.p,NoStaff(),date(2026,11,1))
        self.assertEqual(r['settlement']['corporate_tax'],60000)
        self.assertEqual(r['settlement']['net_profit'],140000)

    def test_payment_fee_credit_uses_dated_sales_not_day_proration(self):
        self.f.save_payment_fee_rates({"credit":3})
        self.store.data['business_sales']=[dict(id='a',date='2026-10-01',amount=110000,credit_sales=110000),dict(id='b',date='2026-10-31',amount=110000,credit_sales=110000)]
        self.settings(expenses={'payment_fees':dict(rate='10',status='registered')})
        first=period_tax(self.f,self.p,'2026-10-01','2026-10-01')
        full=period_tax(self.f,self.p,'2026-10-01','2026-10-31')
        self.assertGreater(full['input_tax'],0)
        self.assertAlmostEqual(first['input_tax'],full['input_tax']/2,delta=1)

    def test_negative_profit_does_not_create_corporate_tax_refund(self):
        r=settlement(self.f,self.p,dict(start='2026-10-01',end='2026-10-31',operating_profit=-100000))
        self.assertEqual(r['corporate_tax'],0)
        self.assertEqual(r['net_profit'],-100000)
