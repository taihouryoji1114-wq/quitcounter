import tempfile
import unittest
from pathlib import Path

from core.data import DataManager
from core.purchases import PurchaseManager


class PurchaseManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.manager = DataManager(Path(self.temp_dir.name) / "data.json")
        self.purchases = PurchaseManager(self.manager)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_records_daily_and_monthly_totals(self):
        self.purchases.add("2026-08-10", "市場A", 12000)
        self.purchases.add("2026-08-10", "市場B", 8000)
        self.purchases.add("2026-08-11", "市場A", 5000)
        self.assertEqual(self.purchases.daily_total("2026-08-10"), 20000)
        self.assertEqual(self.purchases.monthly_total("2026-08"), 25000)

    def test_cost_and_other_expenses_are_separated(self):
        self.purchases.add("2026-08-10", "市場A", 12000, "cost")
        self.purchases.add("2026-08-10", "飲食店", 8000, "expense")
        self.assertEqual(
            self.purchases.monthly_total("2026-08", kind="cost"), 12000
        )
        self.assertEqual(
            self.purchases.monthly_total("2026-08", kind="expense"), 8000
        )
        self.assertEqual(len(self.purchases.records(record_date="2026-08-10")), 2)

    def test_tax_excluded_mixed_rates_are_calculated_per_rate(self):
        breakdown = self.purchases.calculate_tax_breakdown(
            amount_8=20000, amount_10=5000, price_mode="excluded"
        )
        self.assertEqual(breakdown["tax_8"], 1600)
        self.assertEqual(breakdown["tax_10"], 500)
        self.assertEqual(breakdown["total"], 27100)
        record = self.purchases.add(
            "2026-08-10", "市場A", 27100, tax_breakdown=breakdown
        )
        self.assertEqual(record["tax_breakdown"]["amount_8"], 20000)

    def test_tax_included_and_stated_tax_override(self):
        breakdown = self.purchases.calculate_tax_breakdown(
            amount_8=10800,
            amount_10=11000,
            exempt=300,
            price_mode="included",
            stated_tax_8=799,
        )
        self.assertEqual(breakdown["tax_8"], 799)
        self.assertEqual(breakdown["tax_10"], 1000)
        self.assertEqual(breakdown["total"], 22100)

    def test_one_percent_rate_can_be_recorded(self):
        included = self.purchases.calculate_tax_breakdown(
            amount_1=10100, price_mode="included"
        )
        self.assertEqual(included["tax_1"], 100)
        self.assertEqual(included["total"], 10100)
        excluded = self.purchases.calculate_tax_breakdown(
            amount_1=10000, price_mode="excluded"
        )
        self.assertEqual(excluded["tax_1"], 100)
        self.assertEqual(excluded["total"], 10100)

    def test_suppliers_are_reused_without_duplicates(self):
        self.purchases.add("2026-08-10", "市場A", 12000)
        self.purchases.add("2026-08-11", "市場A", 5000)
        self.purchases.add("2026-08-12", "市場B", 3000)
        self.assertEqual(self.purchases.suppliers(), ["市場B", "市場A"])

    def test_supplier_suggestion_can_be_hidden_without_deleting_records(self):
        self.purchases.add("2026-08-10", "入力ミス", 12000)
        self.purchases.hide_supplier("入力ミス")
        self.assertEqual(self.purchases.suppliers(), [])
        self.assertEqual(len(self.purchases.records()), 1)
        self.assertEqual(self.purchases.monthly_total("2026-08"), 12000)

    def test_hidden_supplier_returns_when_used_again(self):
        self.purchases.add("2026-08-10", "市場A", 12000)
        self.purchases.hide_supplier("市場A")
        self.purchases.add("2026-08-11", "市場A", 5000)
        self.assertEqual(self.purchases.suppliers(), ["市場A"])

    def test_record_can_be_deleted_and_data_is_persistent(self):
        record = self.purchases.add("2026-08-10", "市場A", 12000)
        self.purchases.delete(record["id"])
        reloaded = PurchaseManager(DataManager(self.manager.file_path))
        self.assertEqual(reloaded.records(), [])

    def test_update_purchase_and_tax_breakdown(self):
        record = self.purchases.add("2026-08-10", "市場A", 3860)
        breakdown = self.purchases.calculate_tax_breakdown(
            amount_10=3860,
            price_mode="included",
            stated_tax_10=350,
        )
        updated = self.purchases.update(
            record["id"], "2026-08-11", "小次郎", 3860,
            "cost", breakdown, "registered",
        )
        self.assertEqual(updated["supplier"], "小次郎")
        self.assertEqual(updated["tax_breakdown"]["tax_10"], 350)
        self.assertEqual(updated["date"], "2026-08-11")

    def test_kojiro_tax_migration_runs_only_once(self):
        record = self.purchases.add("2026-08-10", "小次郎", 3860)
        self.assertEqual(self.purchases.migrate_kojiro_tax_20260810(), 1)
        self.assertEqual(record["tax_breakdown"]["tax_10"], 350)
        self.assertEqual(self.purchases.migrate_kojiro_tax_20260810(), 0)


if __name__ == "__main__":
    unittest.main()
