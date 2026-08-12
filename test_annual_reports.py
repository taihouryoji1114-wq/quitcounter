import tempfile
import unittest
from pathlib import Path

from core.annual_reports import AnnualReportManager
from core.data import DataManager


class AnnualReportManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data = DataManager(Path(self.temp_dir.name) / "data.json")
        self.reports = AnnualReportManager(self.data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_report_is_saved_independently_by_period(self):
        self.reports.save_report(
            "2026-03", {"cash_on_hand": 1000, "sales": 5000}, {"cash_on_hand": 800, "sales": 4000}
        )
        self.reports.save_report("2025-03", {"cash_on_hand": 700}, {})
        self.assertEqual(self.reports.list_periods(), ["2026-03", "2025-03"])
        self.assertEqual(self.reports.get_report("2026-03")["current"]["cash_on_hand"], 1000)
        self.assertNotIn("business_annual_reports", self.data.data.get("users", {}))

    def test_financial_statement_totals_and_ratios(self):
        result = self.reports.calculate({
            "cash_on_hand": 300, "receivables": 200, "merchandise": 100,
            "building_equipment": 400, "payables": 200, "long_term_loans": 300,
            "capital": 500, "sales": 2000, "purchases": 600,
            "salaries": 500, "rent": 200, "corporate_taxes": 50,
        })
        self.assertEqual(result["assets"], 1000)
        self.assertEqual(result["liabilities"], 500)
        self.assertEqual(result["equity"], 500)
        self.assertEqual(result["gross_profit"], 1400)
        self.assertEqual(result["operating_profit"], 700)
        self.assertEqual(result["net_income"], 650)
        self.assertEqual(result["current_ratio"], 3)

    def test_negative_retained_earnings_is_preserved(self):
        saved = self.reports.save_report(
            "2026-03", {"capital": 1000, "retained_earnings": -2500}, {}
        )
        self.assertEqual(saved["current"]["retained_earnings"], -2500)
        self.assertEqual(self.reports.calculate(saved["current"])["equity"], -1500)

    def test_previous_period_is_loaded_from_prior_saved_report(self):
        self.reports.save_report("2025-03", {"sales": 4000, "cash_on_hand": 800})
        current = self.reports.save_report("2026-03", {"sales": 5000, "cash_on_hand": 1000})
        self.assertEqual(current["previous_period"], "2025-03")
        self.assertEqual(current["previous"]["sales"], 4000)
        self.assertEqual(current["previous"]["cash_on_hand"], 800)

    def test_legacy_summary_fields_are_mapped_without_data_loss(self):
        self.data.data["business_annual_reports"] = {
            "2026-09": {"current": {"cash": 1234, "inventory": 500, "buildings": 900}}
        }
        report = self.reports.get_report("2026-09")
        self.assertEqual(report["current"]["cash_on_hand"], 1234)
        self.assertEqual(report["current"]["merchandise"], 500)
        self.assertEqual(report["current"]["building_equipment"], 900)

    def test_triangle_amount_is_saved_as_negative(self):
        saved = self.reports.save_report("2026-09", {"temporary_payment": "△59,960"})
        self.assertEqual(saved["current"]["temporary_payment"], -59960)


if __name__ == "__main__":
    unittest.main()
