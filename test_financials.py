import tempfile
import unittest
from pathlib import Path

from core.data import DataManager
from core.financials import FinancialManager


class FinancialManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.manager = DataManager(Path(self.temp_dir.name) / "data.json")
        self.financials = FinancialManager(self.manager)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_daily_sales_is_created_and_updated_without_duplicate(self):
        first = self.financials.set_daily_sales("2026-08-10", 120000)
        second = self.financials.set_daily_sales("2026-08-10", 135000)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.financials.sales_records()), 1)
        self.assertEqual(self.financials.monthly_sales_total("2026-08"), 135000)

    def test_monthly_total_and_delete(self):
        first = self.financials.set_daily_sales("2026-08-10", 120000)
        self.financials.set_daily_sales("2026-08-11", 80000)
        self.financials.set_daily_sales("2026-09-01", 50000)
        self.assertEqual(self.financials.monthly_sales_total("2026-08"), 200000)
        self.financials.delete_sales(first["id"])
        self.assertEqual(self.financials.monthly_sales_total("2026-08"), 80000)

    def test_lunch_dinner_people_and_average_spend(self):
        record = self.financials.set_daily_sales(
            "2026-08-10",
            lunch_sales=120000,
            dinner_sales=180000,
            lunch_customers=40,
            dinner_customers=30,
        )
        self.assertEqual(record["amount"], 300000)
        summary = self.financials.monthly_sales_summary("2026-08")
        self.assertEqual(summary["lunch_spend"], 3000)
        self.assertEqual(summary["dinner_spend"], 6000)

    def test_legacy_update_clears_old_split_values(self):
        self.financials.set_daily_sales(
            "2026-08-10", lunch_sales=100, dinner_sales=200,
            lunch_customers=1, dinner_customers=2,
        )
        record = self.financials.set_daily_sales("2026-08-10", 500)
        self.assertEqual(record["amount"], 500)
        self.assertNotIn("lunch_sales", record)
        self.assertEqual(self.financials.monthly_sales_summary("2026-08")["total"], 500)

    def test_business_plan_is_persistent_and_whitelisted(self):
        saved = self.financials.save_plan({
            "sales": "3000000", "cogs-mode": "rate", "unknown": "ignored",
        })
        self.assertNotIn("unknown", saved)
        reloaded = FinancialManager(DataManager(self.manager.file_path))
        self.assertEqual(reloaded.get_plan()["sales"], "3000000")
        self.assertEqual(reloaded.get_plan()["cogs-mode"], "rate")

    def test_payment_breakdown_and_fees_are_calculated(self):
        self.financials.save_payment_fee_rates({
            "credit": 3.0,
            "paypay": 2.0,
            "electronic_money": 1.5,
            "travel_agency": 5.0,
        })
        self.financials.set_daily_sales(
            "2026-08-04",
            lunch_sales=10000,
            dinner_sales=20000,
            cash_sales=10000,
            credit_sales=10000,
            paypay_sales=5000,
            electronic_money_sales=3000,
            travel_agency_sales=2000,
        )
        summary = self.financials.monthly_payment_summary("2026-08")
        self.assertEqual(summary["cash_sales"], 10000)
        self.assertEqual(summary["total_fees"], 300 + 100 + 45 + 100)

    def test_payment_total_must_match_lunch_and_dinner(self):
        with self.assertRaisesRegex(ValueError, "決済方法別の合計"):
            self.financials.set_daily_sales(
                "2026-08-04",
                lunch_sales=10000,
                dinner_sales=20000,
                cash_sales=10000,
                credit_sales=10000,
            )


if __name__ == "__main__":
    unittest.main()
