import tempfile
import unittest
from datetime import date
from pathlib import Path

from core.data import DataManager
from core.financials import FinancialManager
from core.monthly_evaluation import MonthlyEvaluationService
from core.purchases import PurchaseManager


class FakeStaffing:
    def __init__(self, values=None):
        self.values = values or {}

    def month_cost_summary(self, month, _as_of):
        return {"company_cost": self.values.get(month, 0)}


class MonthlyEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data = DataManager(Path(self.temp_dir.name) / "data.json")
        self.financials = FinancialManager(self.data)
        self.purchases = PurchaseManager(self.data)
        self.staffing = FakeStaffing({"2026-08": 300000})
        self.service = MonthlyEvaluationService(
            self.financials, self.purchases, self.staffing
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def enter_month(self, month="2026-08", sales=1_500_000, cost=450_000):
        self.financials.set_daily_sales(f"{month}-01", sales)
        self.purchases.add(f"{month}-02", "市場", cost, "cost")
        self.financials.save_monthly_operations(
            month, rent=120000, utilities=50000, other_admin=30000,
            loan_payment=50000,
        )

    def test_snapshot_uses_existing_records_without_mutating_them(self):
        self.enter_month()
        before = dict(self.data.data)
        result = self.service.snapshot("2026-08", date(2026, 9, 1))
        self.assertEqual(result["gross_profit"], 1_050_000)
        self.assertEqual(result["operating_profit"], 550_000)
        self.assertEqual(result["post_repayment_profit"], 396_970)
        self.assertEqual(self.data.data, before)

    def test_formal_evaluation_is_blocked_before_month_end(self):
        self.enter_month("2026-09")
        with self.assertRaisesRegex(ValueError, "月末の営業終了"):
            self.service.evaluate("2026-09", date(2026, 9, 7))

    def test_evaluation_has_rank_reasons_actions_and_can_be_persisted(self):
        self.enter_month()
        result = self.service.evaluate("2026-08", date(2026, 9, 1))
        self.assertIn(result["rank"], "SABCD")
        self.assertTrue(result["good"])
        self.assertTrue(result["actions"])
        saved = self.financials.save_monthly_evaluation("2026-08", result)
        self.assertEqual(
            FinancialManager(DataManager(self.data.file_path))
            .get_monthly_evaluation("2026-08")["score"],
            saved["score"],
        )

    def test_material_anomaly_ignores_small_changes(self):
        for month, cost in (("2026-05", 300000), ("2026-06", 300000), ("2026-07", 300000)):
            self.enter_month(month, cost=cost)
        self.enter_month("2026-08", cost=600000)
        preview = self.service.preview("2026-08", date(2026, 9, 1))
        self.assertTrue(any("原価率" in item for item in self.service.anomalies(preview)))

    def test_existing_gross_profit_personnel_target_is_converted_to_sales_rate(self):
        self.financials.save_plan({
            "sales": 1_000_000, "cogs-mode": "rate", "cogs-rate": 30,
            "personnel-mode": "rate", "personnel-rate": 35,
            "personnel-plan-basis": "gross-profit",
        })
        targets = self.service.targets()
        self.assertAlmostEqual(targets["cost_rate"], .30)
        self.assertAlmostEqual(targets["personnel_rate"], .245)

    def test_forecast_waits_for_enough_sales_days(self):
        self.financials.save_monthly_operations("2026-09", rent=100000)
        for day in range(1, 5):
            self.financials.set_daily_sales(f"2026-09-{day:02d}", 100000)
        self.assertIsNone(self.service.forecast("2026-09", date(2026, 9, 7)))
        self.financials.set_daily_sales("2026-09-05", 100000)
        forecast = self.service.forecast("2026-09", date(2026, 9, 7))
        self.assertGreater(forecast["sales"], 500000)


if __name__ == "__main__":
    unittest.main()
