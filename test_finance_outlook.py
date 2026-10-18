import unittest
from core.finance_outlook import calculate_outlook, tax_and_repayment_threshold

class OutlookTest(unittest.TestCase):
    def test_threshold_and_ratios(self):
        r=calculate_outlook(1000000,300000,20000,200000,140000)
        self.assertEqual(r['break_even'],500000)
        self.assertEqual(r['profit'],340000)
        self.assertAlmostEqual(r['labor_rate'],2/7)
    def test_fee_classification_does_not_change_profit(self):
        a=calculate_outlook(1000000,300000,20000,200000,140000,True)
        b=calculate_outlook(1000000,300000,20000,200000,140000,False)
        self.assertEqual(a['profit'],b['profit'])
        self.assertNotEqual(a['break_even'],b['break_even'])
    def test_no_false_zero_and_nonpositive_gross(self):
        self.assertIsNone(calculate_outlook(100,None,0,20,10)['break_even'])
        r=calculate_outlook(100,110,0,20,10)
        self.assertIsNone(r['break_even']);self.assertIsNone(r['labor_rate'])
        self.assertEqual(r['profit'],-40)

    def test_tax_repayment_threshold(self):
        base=calculate_outlook(1000000,300000,20000,200000,140000)['break_even']
        cover=tax_and_repayment_threshold(1000000,300000,20000,200000,140000,50000,8/108)
        self.assertGreater(cover,base)
        profit=cover*(1-.32)-340000
        tax=max(0,cover*10/110-cover*.3*8/108)
        self.assertAlmostEqual(profit-tax-50000,0,delta=1)
        self.assertIsNone(tax_and_repayment_threshold(100,95,0,20,10,1))
