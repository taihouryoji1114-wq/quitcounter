import tempfile
import unittest
from pathlib import Path

from core.business_audit import BusinessAuditManager
from core.data import DataManager


class BusinessAuditManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data = DataManager(Path(self.temp_dir.name) / "data.json")
        self.audit = BusinessAuditManager(self.data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_finds_missing_sales_days_and_inconsistent_breakdowns(self):
        self.data.data["business_sales"] = [{
            "id": "sale-1", "date": "2026-08-01", "amount": 100,
            "lunch_sales": 60, "dinner_sales": 30,
            "cash_sales": 80, "credit_sales": 0,
        }]
        result = self.audit.inspect("2026-08", "2026-08-03")
        titles = [item["title"] for item in result["issues"]]
        self.assertIn("売上が未入力です", titles)
        self.assertIn("ランチ・ディナー合計が売上と一致しません", titles)
        self.assertIn("決済内訳が売上と一致しません", titles)
        self.assertEqual(result["missing"], 2)

    def test_finds_duplicate_purchase_and_tax_mismatch(self):
        row = {
            "date": "2026-08-02", "supplier": "仕入先", "total": 1080,
            "kind": "cost", "tax_breakdown": {"total": 1100},
        }
        self.data.data["business_purchases"] = [dict(row, id="a"), dict(row, id="b")]
        result = self.audit.inspect("2026-08", "2026-08-01")
        titles = [item["title"] for item in result["issues"]]
        self.assertIn("同じ仕入れが重複している可能性があります", titles)
        self.assertEqual(titles.count("税率別合計と仕入合計が一致しません"), 2)

    def test_finds_half_entered_staff_shift(self):
        self.data.data["business_staff_hours"] = {
            "2026-08-02": {"スタッフA": {"lunch_start": "10:00", "lunch_end": ""}}
        }
        result = self.audit.inspect("2026-08", "2026-08-01")
        self.assertTrue(any("時刻が片方だけ" in item["title"] for item in result["issues"]))


if __name__ == "__main__":
    unittest.main()
