import tempfile
import unittest
from pathlib import Path

from core.data import DataManager
from core.store_quiz import StoreQuizManager


class StoreQuizManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data = DataManager(Path(self.temp_dir.name) / "data.json")
        self.manager = StoreQuizManager(self.data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_question_is_saved_and_soft_deleted(self):
        item = self.manager.add_question(
            "発注依頼を完了にできるのは？", "管理者",
            ["全スタッフ", "入力者", "誰もできない"],
        )
        self.assertEqual(self.manager.questions()[0]["answer"], "管理者")
        self.manager.delete_question(item["id"])
        self.assertEqual(self.manager.questions(), [])
        self.assertEqual(len(self.data.data["store_quiz_questions"]), 1)

    def test_duplicate_choices_are_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.add_question("問題", "同じ", ["同じ", "違う1", "違う2"])

    def test_question_pack_is_added_only_once(self):
        questions = (("黒豚は何グラム？", "150グラム", ["50グラム", "75グラム", "200グラム"]),)
        self.assertEqual(self.manager.seed_question_pack("basic", questions), 1)
        self.assertEqual(self.manager.seed_question_pack("basic", questions), 0)
        self.assertEqual(len(self.manager.questions()), 1)

    def test_notice_only_returns_active_items(self):
        item = self.manager.add_notice("本日の業務連絡", "予約があります")
        self.assertEqual(self.manager.notices()[0]["details"], "予約があります")
        self.manager.close_notice(item["id"])
        self.assertEqual(self.manager.notices(), [])
        history = self.manager.notices(include_closed=True)
        self.assertEqual(history[0]["title"], "本日の業務連絡")
        self.assertFalse(history[0]["active"])
        self.assertTrue(history[0]["closed_at"])


if __name__ == "__main__":
    unittest.main()
