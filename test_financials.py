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


if __name__ == "__main__":
    unittest.main()
