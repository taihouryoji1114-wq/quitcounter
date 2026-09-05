"""Private, user-owned schedule records."""

from __future__ import annotations

import calendar
from datetime import datetime
from datetime import timedelta
from uuid import uuid4

from core.data import data


class ScheduleManager:
    def __init__(self, data_manager=None):
        self._data_manager = data_manager or data

    def events(self, user_id, start_date=None, end_date=None):
        if end_date:
            self._ensure_monthly_occurrences(user_id, end_date)
        values = self._data_manager.data.get("personal_schedules", {}).get(user_id, [])
        result = [dict(value) for value in values if isinstance(value, dict)]
        if start_date:
            self._date(start_date)
            result = [value for value in result if value.get("end_date", value.get("date", "")) >= start_date]
        if end_date:
            self._date(end_date)
            result = [value for value in result if value.get("date", "") <= end_date]
        return sorted(result, key=lambda value: (value.get("date", ""), value.get("start_time", ""),
                                                  value.get("created_at", "")))

    def notification_settings(self, user_id):
        saved = self._data_manager.data.get("personal_schedule_notifications", {}).get(
            user_id, {})
        return {"enabled": bool(saved.get("enabled", False)),
                "time": str(saved.get("time") or "08:00")}

    def save_notification_settings(self, user_id, enabled, notify_time="08:00"):
        notify_time = self._time(notify_time)
        if not notify_time:
            notify_time = "08:00"
        saved = {"enabled": bool(enabled), "time": notify_time}
        self._data_manager.data.setdefault("personal_schedule_notifications", {})[
            user_id] = saved
        self._data_manager.save()
        return dict(saved)

    def add_event(self, user_id, title, event_date, start_time="", end_time="",
                  category="個人", note="", event_end_date="", requires_check=False,
                  repeat_monthly=False):
        title = str(title or "").strip()
        if not title:
            raise ValueError("予定を入力してください。")
        self._date(event_date)
        event_end_date = str(event_end_date or event_date)
        self._date(event_end_date)
        if event_end_date < event_date:
            raise ValueError("終了日は開始日以降にしてください。")
        start_time = self._time(start_time)
        end_time = self._time(end_time)
        if start_time and end_time and end_time < start_time:
            raise ValueError("終了時刻は開始時刻より後にしてください。")
        event_id = uuid4().hex
        item = {
            "id": event_id, "title": title[:100], "date": event_date,
            "end_date": event_end_date,
            "start_time": start_time, "end_time": end_time,
            "category": str(category or "個人")[:20], "note": str(note or "").strip()[:500],
            "requires_check": bool(requires_check), "completed": False,
            "repeat_monthly": bool(repeat_monthly),
            "series_id": event_id if repeat_monthly else "",
            "repeat_day": int(event_date[-2:]) if repeat_monthly else None,
            "scheduled_date": event_date,
            "created_at": datetime.now().isoformat(timespec="minutes"),
        }
        self._data_manager.data.setdefault("personal_schedules", {}).setdefault(user_id, []).append(item)
        self._data_manager.save()
        return dict(item)

    def set_completed(self, user_id, event_id, completed):
        item = self._find(user_id, event_id)
        if not item.get("requires_check", False):
            raise ValueError("この予定には完了チェックが設定されていません。")
        item["completed"] = bool(completed)
        item["completed_at"] = (datetime.now().isoformat(timespec="minutes")
                                if completed else "")
        self._data_manager.save()

    def update_event(self, user_id, event_id, title, note="", requires_check=None,
                     repeat_monthly=None):
        title = str(title or "").strip()
        if not title:
            raise ValueError("予定名を入力してください。")
        item = self._find(user_id, event_id)
        item["title"] = title[:100]
        item["note"] = str(note or "").strip()[:500]
        if requires_check is not None:
            item["requires_check"] = bool(requires_check)
            if not item["requires_check"]:
                item["completed"] = False
                item["completed_at"] = ""
        if repeat_monthly is not None:
            repeat_monthly = bool(repeat_monthly)
            if repeat_monthly and not item.get("repeat_monthly"):
                item["repeat_monthly"] = True
                item["series_id"] = item.get("series_id") or item["id"]
                item["repeat_day"] = int(item.get("scheduled_date", item["date"])[-2:])
                item["scheduled_date"] = item.get("scheduled_date") or item["date"]
            elif not repeat_monthly and item.get("repeat_monthly"):
                series_id = item.get("series_id")
                current_scheduled = item.get("scheduled_date", item["date"])
                values = self._data_manager.data.setdefault("personal_schedules", {}).setdefault(
                    user_id, [])
                values[:] = [value for value in values if not (
                    isinstance(value, dict) and value.get("series_id") == series_id
                    and value.get("id") != item["id"]
                    and value.get("scheduled_date", value.get("date", "")) > current_scheduled)]
                item["repeat_monthly"] = False
                item["series_id"] = ""
                item["repeat_day"] = None
        item["updated_at"] = datetime.now().isoformat(timespec="minutes")
        self._data_manager.save()
        return dict(item)

    def _ensure_monthly_occurrences(self, user_id, through_date):
        """月間表示に必要な繰り返し予定を、同じ月内で重複せず生成する。"""
        through = self._date(through_date).date()
        values = self._data_manager.data.setdefault("personal_schedules", {}).setdefault(
            user_id, [])
        templates = {}
        for item in values:
            if isinstance(item, dict) and item.get("repeat_monthly") and item.get("series_id"):
                templates.setdefault(item["series_id"], item)
        changed = False
        for series_id, template in templates.items():
            first = self._date(template.get("scheduled_date", template["date"])).date()
            repeat_day = int(template.get("repeat_day") or first.day)
            duration = max(0, (self._date(template.get("end_date", template["date"])).date()
                               - self._date(template["date"]).date()).days)
            existing = {str(value.get("scheduled_date", value.get("date", "")))
                        for value in values if isinstance(value, dict)
                        and value.get("series_id") == series_id}
            year, month = first.year, first.month
            for _ in range(240):
                day = min(repeat_day, calendar.monthrange(year, month)[1])
                occurrence = first.replace(year=year, month=month, day=day)
                if occurrence > through:
                    break
                occurrence_text = occurrence.isoformat()
                if occurrence >= first and occurrence_text not in existing:
                    clone = dict(template)
                    clone.update({
                        "id": uuid4().hex, "date": occurrence_text,
                        "end_date": (occurrence + timedelta(days=duration)).isoformat(),
                        "scheduled_date": occurrence_text, "completed": False,
                        "completed_at": "", "carried_from": "", "carried_at": "",
                        "created_at": datetime.now().isoformat(timespec="minutes"),
                    })
                    values.append(clone)
                    existing.add(occurrence_text)
                    changed = True
                if month == 12:
                    year, month = year + 1, 1
                else:
                    month += 1
        if changed:
            self._data_manager.save()

    def roll_over_unfinished(self, user_id, target_date):
        """未完了のチェック予定を対象日へ移し、完了まで翌日へ持ち越す。"""
        self._date(target_date)
        self._ensure_monthly_occurrences(user_id, target_date)
        changed = 0
        values = self._data_manager.data.setdefault("personal_schedules", {}).setdefault(
            user_id, [])
        for item in values:
            if not isinstance(item, dict) or not item.get("requires_check", False):
                continue
            if item.get("completed", False):
                continue
            end_date = str(item.get("end_date") or item.get("date") or "")
            if not end_date or end_date >= target_date:
                continue
            if not item.get("carried_from"):
                item["carried_from"] = item.get("date", end_date)
            item["date"] = target_date
            item["end_date"] = target_date
            item["carried_at"] = datetime.now().isoformat(timespec="minutes")
            changed += 1
        if changed:
            self._data_manager.save()
        return changed

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
