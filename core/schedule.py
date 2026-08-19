"""Private, user-owned schedule records."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from core.data import data


class ScheduleManager:
    def __init__(self, data_manager=None):
        self._data_manager = data_manager or data

    def events(self, user_id, start_date=None, end_date=None):
        values = self._data_manager.data.get("personal_schedules", {}).get(user_id, [])
        result = [dict(value) for value in values if isinstance(value, dict)]
        if start_date:
            self._date(start_date)
            result = [value for value in result if value.get("date", "") >= start_date]
        if end_date:
            self._date(end_date)
            result = [value for value in result if value.get("date", "") <= end_date]
        return sorted(result, key=lambda value: (value.get("date", ""), value.get("start_time", ""),
                                                  value.get("created_at", "")))

    def add_event(self, user_id, title, event_date, start_time="", end_time="",
                  category="個人", note=""):
        title = str(title or "").strip()
        if not title:
            raise ValueError("予定を入力してください。")
        self._date(event_date)
        start_time = self._time(start_time)
        end_time = self._time(end_time)
        if start_time and end_time and end_time < start_time:
            raise ValueError("終了時刻は開始時刻より後にしてください。")
        item = {
            "id": uuid4().hex, "title": title[:100], "date": event_date,
            "start_time": start_time, "end_time": end_time,
            "category": str(category or "個人")[:20], "note": str(note or "").strip()[:500],
            "completed": False, "created_at": datetime.now().isoformat(timespec="minutes"),
        }
        self._data_manager.data.setdefault("personal_schedules", {}).setdefault(user_id, []).append(item)
        self._data_manager.save()
        return dict(item)

    def set_completed(self, user_id, event_id, completed):
        item = self._find(user_id, event_id)
        item["completed"] = bool(completed)
        self._data_manager.save()

    def delete_event(self, user_id, event_id):
        values = self._data_manager.data.setdefault("personal_schedules", {}).setdefault(user_id, [])
        before = len(values)
        values[:] = [value for value in values if not isinstance(value, dict) or value.get("id") != event_id]
        if len(values) == before:
            raise ValueError("予定が見つかりません。")
        self._data_manager.save()

    def _find(self, user_id, event_id):
        for item in self._data_manager.data.setdefault("personal_schedules", {}).setdefault(user_id, []):
            if isinstance(item, dict) and item.get("id") == event_id:
                return item
        raise ValueError("予定が見つかりません。")

    @staticmethod
    def _date(value):
        try:
            return datetime.strptime(str(value), "%Y-%m-%d")
        except ValueError as error:
            raise ValueError("日付が正しくありません。") from error

    @staticmethod
    def _time(value):
        value = str(value or "").strip()
        if not value:
            return ""
        try:
            return datetime.strptime(value, "%H:%M").strftime("%H:%M")
        except ValueError as error:
            raise ValueError("時刻が正しくありません。") from error


schedule = ScheduleManager()
