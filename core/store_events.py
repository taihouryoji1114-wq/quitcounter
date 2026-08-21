"""Shared store event calendar."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from core.data import data


class StoreEventManager:
    CATEGORIES = ("親睦", "店舗イベント", "会議", "研修", "予約・貸切", "その他")

    def __init__(self, data_manager=None):
        self._data_manager = data_manager or data

    def events(self, start_date=None, end_date=None):
        values = [dict(value) for value in self._data_manager.data.get("store_events", [])
                  if isinstance(value, dict) and value.get("active", True)]
        if start_date:
            values = [value for value in values if value.get("end_date", value.get("date", "")) >= start_date]
        if end_date:
            values = [value for value in values if value.get("date", "") <= end_date]
        return sorted(values, key=lambda value: (value.get("date", ""), value.get("start_time", "")))

    def add(self, title, event_date, end_date=None, start_time="", end_time="",
            category="店舗イベント", details=""):
        title = str(title or "").strip()
        if not title:
            raise ValueError("イベント名を入力してください。")
        start = self._date(event_date)
        end = self._date(end_date or event_date)
        if end < start:
            raise ValueError("終了日は開始日以降にしてください。")
        if category not in self.CATEGORIES:
            raise ValueError("分類が正しくありません。")
        item = {"id": uuid4().hex, "title": title[:100], "date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"), "start_time": str(start_time or ""),
                "end_time": str(end_time or ""), "category": category,
                "details": str(details or "").strip()[:1000], "active": True,
                "created_at": datetime.now().isoformat(timespec="minutes")}
        self._data_manager.data.setdefault("store_events", []).append(item)
        self._data_manager.save()
        return dict(item)

    def delete(self, event_id):
        for item in self._data_manager.data.setdefault("store_events", []):
            if isinstance(item, dict) and item.get("id") == event_id and item.get("active", True):
                item["active"] = False
                self._data_manager.save()
                return
        raise ValueError("イベントが見つかりません。")

    @staticmethod
    def _date(value):
        try:
            return datetime.strptime(str(value), "%Y-%m-%d")
        except ValueError as error:
            raise ValueError("日付が正しくありません。") from error


store_events = StoreEventManager()
