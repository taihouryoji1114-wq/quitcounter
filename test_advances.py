import tempfile
import unittest
from pathlib import Path
from core.data import DataManager
from core.advances import AdvanceManager
from core.announcements import AnnouncementManager


class AdvanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = DataManager(Path(self.temp.name) / "data.json")
        self.manager = AdvanceManager(self.data)

    def test_month_overwrite_partial_refund_carry_and_reload(self):
        self.manager.save_month("2026-08", [100, 200, 300])
        self.manager.save_month("2026-08", [100, 200, 300])
        self.manager.refund("2026-09-01", [50, 0, 100])
        self.manager.save_month("2026-09", [10, 20, 30])
        self.assertEqual(self.manager.totals()[2], [60, 220, 230])
        reloaded = AdvanceManager(DataManager(self.data.file_path))
        self.assertEqual(reloaded.totals(), self.manager.totals())
        self.assertNotIn("business_purchases", self.data.data)

    def test_refund_cancel_and_overpayment_protection(self):
        self.manager.save_month("2026-08", [100, 200, 300])
        with self.assertRaises(ValueError):
            self.manager.refund("2026-09-01", [101, 0, 0])
        self.manager.refund("2026-09-01", [100, 0, 0])
        with self.assertRaises(ValueError):
            self.manager.save_month("2026-08", [50, 200, 300])
        self.manager.void_refund(self.manager.state()["refunds"][0]["id"])
        self.assertEqual(self.manager.totals()[2], [100, 200, 300])

    def test_double_click_refund_is_idempotent(self):
        self.manager.save_month("2026-09", [1000, 0, 0])
        self.manager.refund("2026-09-04", [100, 0, 0], "same-click")
        self.manager.refund("2026-09-04", [100, 0, 0], "same-click")
        self.assertEqual(self.manager.totals()[2], [900, 0, 0])

    def test_names_and_invalid_amounts(self):
        self.manager.save_names(["甲", "乙", "丙"])
        self.assertEqual(self.manager.names(), ["甲", "乙", "丙"])
        for values in ([1, 2], [-1, 0, 0], ["NaN", 0, 0], [1.5, 0, 0]):
            with self.assertRaises(ValueError):
                self.manager.save_month("2026-09", values)
        with self.assertRaises(ValueError):
            self.manager.save_names(["甲", "甲", "丙"])

    def test_announcements_edit_disable_delete_and_validate(self):
        manager = AnnouncementManager(self.data)
        row = manager.save("15:00", "ご飯の時間です。")
        manager.save("16:00", "在庫チェックの時間です。", False, row["id"])
        self.assertEqual(len(manager.items()), 1)
        self.assertFalse(manager.items()[0]["enabled"])
        for time, message in (("25:00", "ご飯"), ("15:00", ""), ("15:00", "あ" * 121)):
            with self.assertRaises(ValueError):
                manager.save(time, message)
        manager.delete(row["id"])
        self.assertEqual(manager.items(), [])
