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

    def test_suppliers_are_reused_without_duplicates(self):
        self.purchases.add("2026-08-10", "市場A", 12000)
        self.purchases.add("2026-08-11", "市場A", 5000)
        self.purchases.add("2026-08-12", "市場B", 3000)
        self.assertEqual(self.purchases.suppliers(), ["市場B", "市場A"])

    def test_record_can_be_deleted_and_data_is_persistent(self):
        record = self.purchases.add("2026-08-10", "市場A", 12000)
        self.purchases.delete(record["id"])
        reloaded = PurchaseManager(DataManager(self.manager.file_path))
        self.assertEqual(reloaded.records(), [])


if __name__ == "__main__":
    unittest.main()
