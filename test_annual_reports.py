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
            "salaries": 500, "rent": 200,
        })
        self.assertEqual(result["assets"], 1000)
        self.assertEqual(result["liabilities"], 500)
        self.assertEqual(result["equity"], 500)
        self.assertEqual(result["gross_profit"], 1400)
        self.assertEqual(result["operating_profit"], 700)
        self.assertEqual(result["net_income"], 700)
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

    def test_hidden_legacy_summary_amounts_do_not_duplicate_totals(self):
        result = self.reports.calculate({
            "cash_on_hand": 1000,
            "other_current_assets": 11500000,
            "capital": 1000,
        })
        self.assertEqual(result["assets"], 1000)
        self.assertEqual(result["equity"], 1000)
        self.assertEqual(result["balance_gap"], 0)

    def test_decision_requires_balanced_statement(self):
        decision = self.reports.management_decision(
            {"cash_on_hand": 1000, "capital": 500}, {}
        )
        self.assertEqual(decision["mode"], "verify")

    def test_decision_prioritizes_defense_for_negative_equity_and_cash(self):
        values = {
            "cash_on_hand": 100, "building_equipment": 900,
            "payables": 500, "long_term_loans": 1500,
            "capital": 1000, "retained_earnings": -2000,
            "sales": 12000, "purchases": 4000, "salaries": 6000,
            "rent": 1500, "interest_expense": 500,
        }
        decision = self.reports.management_decision(values, {})
        self.assertEqual(decision["mode"], "defense")
        self.assertIn("守り", decision["label"])

    def test_decision_allows_attack_only_when_multiple_conditions_are_met(self):
        previous = {
            "cash_on_hand": 1800, "receivables": 200, "capital": 2000,
            "sales": 10000, "purchases": 3000, "salaries": 3000, "rent": 1000,
        }
        current = {
            "cash_on_hand": 3000, "receivables": 1000, "capital": 4000,
            "sales": 12000, "purchases": 3000, "salaries": 3000, "rent": 1000,
        }
        decision = self.reports.management_decision(current, previous)
        self.assertEqual(decision["mode"], "attack")

    def test_legacy_extraordinary_subtotal_is_not_counted_twice(self):
        result = self.reports.calculate({
            "sales": 1000,
            "fixed_asset_disposal_loss": 100,
            "extraordinary_loss": 100,
        })
        self.assertEqual(result["pretax_profit"], 900)

    def test_accounts_not_on_supplied_statement_do_not_affect_profit(self):
        result = self.reports.calculate({
            "sales": 1000,
            "recruitment_fees": 100,
            "depreciation": 100,
            "other_sga": 100,
            "corporate_taxes": 100,
        })
        self.assertEqual(result["operating_profit"], 1000)
        self.assertEqual(result["net_income"], 1000)

    def test_restaurant_health_compares_cost_and_personnel_to_sales(self):
        health = {item["key"]: item for item in self.reports.restaurant_health({
            "sales": 10000, "purchases": 4000, "salaries": 4000,
        })}
        self.assertEqual(health["cost"]["status"], "danger")
        self.assertEqual(health["personnel"]["status"], "danger")
        self.assertEqual(health["cost"]["display"], "40.0%")

    def test_decision_turns_restaurant_ratio_gap_into_yen_action(self):
        values = {
            "cash_on_hand": 1000, "capital": 1000,
            "sales": 10000, "purchases": 4000, "salaries": 4000,
            "rent": 2500,
        }
        decision = self.reports.management_decision(values, {})
        actions = " ".join(decision["actions"])
        self.assertIn("400円が改善検討額", actions)
        self.assertIn("700円が改善検討額", actions)

    def test_decision_explains_negative_working_capital_and_debt(self):
        values = {
            "cash_on_hand": 100, "building_equipment": 1900,
            "payables": 1000, "short_term_loans": 1000,
            "sales": 10000, "purchases": 3000,
            "salaries": 5000, "rent": 2500,
        }
        decision = self.reports.management_decision(values, {})
        actions = " ".join(decision["actions"])
        self.assertIn("短期資金が 1,900円不足", actions)
        self.assertIn("借入残高は 1,000円", actions)


if __name__ == "__main__":
    unittest.main()
