import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.consulting import ConsultingManager
from core.data import DataManager


class ConsultingManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data = DataManager(Path(self.temp_dir.name) / "data.json")
        self.manager = ConsultingManager(self.data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_progress_is_saved_without_replacing_other_data(self):
        self.data.data["business_sales"] = [{"id": "keep", "date": "2026-08-01", "amount": 1}]
        saved = self.manager.save_item("2026-08", "cash_defense", "in_progress", "銀行へ相談")
        self.assertEqual(saved["status"], "in_progress")
        self.assertEqual(self.data.data["business_sales"][0]["id"], "keep")

    def test_invalid_status_is_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.save_item("2026-08", "cost", "unknown")

    def test_diagnosis_prioritizes_cash_defense(self):
        annual = {
            "current": {"cash_on_hand": 100, "building_equipment": 900,
                        "payables": 500, "short_term_loans": 500},
        }
        calculated = {
            "balance_gap": 0, "current_assets": 100, "current_liabilities": 1000,
            "current_ratio": .1, "equity": 0, "ordinary_profit": -1,
        }
        with patch("core.consulting.annual_reports.list_periods", return_value=["2026-09"]), \
             patch("core.consulting.annual_reports.get_report", return_value=annual), \
             patch("core.consulting.annual_reports.calculate", return_value=calculated), \
             patch("core.consulting.financials.monthly_sales_total", return_value=0), \
             patch("core.consulting.purchases.monthly_total", return_value=0), \
             patch("core.consulting.financials.monthly_payment_summary", return_value={"total_fees": 0}), \
             patch("core.consulting.financials.get_monthly_advertising", return_value={"total": 0}), \
             patch("core.consulting.financials.get_monthly_operations", return_value={"personnel": 0, "rent": 0, "utilities": 0, "other_admin": 0, "loan_payment": 0}):
            result = self.manager.diagnose("2026-08")
        self.assertEqual(result["primary"]["key"], "cash_defense")

    def test_simulation_uses_annual_statement_and_explicit_customer_count(self):
        snapshot = {
            "sales": 10_000_000, "profit": -500_000,
        }
        with patch.object(self.manager, "annual_snapshot", return_value=snapshot):
            result = self.manager.simulate("2026-08", 1, 2, 100, 20_000)
        self.assertEqual(result["cost_effect"], 100_000)
        self.assertEqual(result["personnel_effect"], 200_000)
        self.assertEqual(result["spend_effect"], 2_000_000)
        self.assertEqual(result["new_profit"], 1_800_000)


if __name__ == "__main__":
    unittest.main()
