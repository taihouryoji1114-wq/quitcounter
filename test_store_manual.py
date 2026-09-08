import tempfile
import unittest
from pathlib import Path

from core.data import DataManager
from core.store_manual import StoreManualManager


class StoreManualManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.manager = StoreManualManager(DataManager(Path(self.temp.name) / "data.json"))

    def tearDown(self):
        self.temp.cleanup()

    def test_admin_can_build_manual_from_settings_data(self):
        category = self.manager.add_category("仕込み", "#E8F2EC", "soup_kitchen")
        manual = self.manager.add_manual(
            "唐揚げの仕込み", category["id"], "鶏肉2kgを使用",
            "3分血抜き\n調味料を揉み込む\n30分置く", "空気を入れない")
        self.assertEqual(len(self.manager.manuals(category["id"])), 1)
        self.assertEqual(manual["steps"][1], "調味料を揉み込む")

    def test_manual_can_be_updated_and_soft_deleted(self):
        category = self.manager.add_category("接客")
        manual = self.manager.add_manual("ご案内", category["id"])
        updated = self.manager.update_manual(manual["id"], summary="席へご案内する")
        self.assertEqual(updated["summary"], "席へご案内する")
        self.manager.delete_manual(manual["id"])
        self.assertEqual(self.manager.manuals(), [])


if __name__ == "__main__":
    unittest.main()
