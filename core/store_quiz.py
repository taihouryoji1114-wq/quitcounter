"""Questions and temporary business notices shared by the store app."""

from datetime import datetime
from uuid import uuid4

from core.data import data


class StoreQuizManager:
    def __init__(self, data_manager=None):
        self._data_manager = data_manager or data

    def questions(self):
        return [dict(item) for item in self._data_manager.data.get("store_quiz_questions", [])
                if isinstance(item, dict) and item.get("active", True)]

    def add_question(self, question, answer, wrong_answers):
        question = str(question or "").strip()
        answer = str(answer or "").strip()
        wrong = [str(value or "").strip() for value in wrong_answers]
        wrong = [value for value in wrong if value]
        if not question:
            raise ValueError("問題文を入力してください。")
        if not answer:
            raise ValueError("正解を入力してください。")
        if len(wrong) != 3:
            raise ValueError("間違いの選択肢を3つ入力してください。")
        choices = [answer, *wrong]
        if len(set(choices)) != 4:
            raise ValueError("4つの選択肢はすべて違う内容にしてください。")
        item = {
            "id": uuid4().hex, "question": question[:200], "answer": answer[:100],
            "wrong_answers": [value[:100] for value in wrong], "active": True,
            "created_at": datetime.now().isoformat(timespec="minutes"),
        }
        self._data_manager.data.setdefault("store_quiz_questions", []).append(item)
        self._data_manager.save()
        return dict(item)

    def delete_question(self, question_id):
        for item in self._data_manager.data.setdefault("store_quiz_questions", []):
            if isinstance(item, dict) and item.get("id") == question_id and item.get("active", True):
                item["active"] = False
                self._data_manager.save()
                return
        raise ValueError("問題が見つかりません。")

    def notices(self):
        return [dict(item) for item in self._data_manager.data.get("store_business_notices", [])
                if isinstance(item, dict) and item.get("active", True)]

    def add_notice(self, title, details=""):
        title = str(title or "").strip()
        details = str(details or "").strip()
        if not title:
            raise ValueError("業務連絡の題名を入力してください。")
        item = {
            "id": uuid4().hex, "title": title[:100], "details": details[:1000],
            "active": True, "created_at": datetime.now().isoformat(timespec="minutes"),
        }
        self._data_manager.data.setdefault("store_business_notices", []).append(item)
        self._data_manager.save()
        return dict(item)

    def close_notice(self, notice_id):
        for item in self._data_manager.data.setdefault("store_business_notices", []):
            if isinstance(item, dict) and item.get("id") == notice_id and item.get("active", True):
                item["active"] = False
                self._data_manager.save()
                return
        raise ValueError("業務連絡が見つかりません。")


store_quiz = StoreQuizManager()
