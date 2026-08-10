"""Reading timer and daily reading goals."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo


JAPAN = ZoneInfo("Asia/Tokyo")


class ReadingManager:
    def __init__(self, data_manager):
        self._data_manager = data_manager

    def _user(self, user_id=None):
        return self._data_manager.users.get_user(
            user_id or self._data_manager.active_user_id
        )

    @staticmethod
    def now():
        return datetime.now(JAPAN)

    def active_started_at(self, user_id=None):
        value = self._user(user_id).get("reading_active_started_at")
        return datetime.fromisoformat(value) if value else None

    def start(self, user_id=None, now=None):
        user = self._user(user_id)
        if user.get("reading_active_started_at"):
            raise ValueError("すでに読書中です。")
        started = now or self.now()
        user["reading_active_started_at"] = started.isoformat()
        self._data_manager.save()
        return started

    def stop(self, user_id=None, now=None):
        user = self._user(user_id)
        started_value = user.get("reading_active_started_at")
        if not started_value:
            raise ValueError("読書は開始されていません。")
        started = datetime.fromisoformat(started_value)
        ended = now or self.now()
        if ended < started:
            ended = started
        created = []
        cursor = started
        while cursor.date() < ended.date():
            boundary = datetime.combine(
                cursor.date() + timedelta(days=1), time.min,
                tzinfo=cursor.tzinfo,
            )
            created.append(self._session(cursor, boundary))
            cursor = boundary
        if ended > cursor or not created:
            created.append(self._session(cursor, ended))
        user.setdefault("reading_sessions", []).extend(created)
        user.pop("reading_active_started_at", None)
        self._data_manager.save()
        return created[-1]

    @staticmethod
    def _session(started, ended):
        return {
            "id": uuid4().hex,
            "date": started.date().isoformat(),
            "started_at": started.isoformat(),
            "ended_at": ended.isoformat(),
            "seconds": max(1, round((ended - started).total_seconds())),
        }

    def sessions(self, record_date=None, user_id=None):
        records = self._user(user_id).get("reading_sessions", [])
        if record_date:
            records = [item for item in records if item.get("date") == record_date]
        return list(records)

    def total_seconds(self, record_date, user_id=None, include_active=True, now=None):
        total = sum(item.get("seconds", 0) for item in self.sessions(record_date, user_id))
        active = self.active_started_at(user_id) if include_active else None
        current = now or self.now()
        if active and active.date().isoformat() == record_date:
            total += max(0, round((current - active).total_seconds()))
        return total

    def monthly_summary(self, month, user_id=None, now=None):
        try:
            datetime.strptime(month, "%Y-%m")
        except (TypeError, ValueError) as error:
            raise ValueError("月は YYYY-MM 形式で指定してください。") from error
        totals_by_date = {}
        for session in self.sessions(user_id=user_id):
            record_date = session.get("date", "")
            if not record_date.startswith(month):
                continue
            totals_by_date[record_date] = (
                totals_by_date.get(record_date, 0) + int(session.get("seconds", 0))
            )
        active = self.active_started_at(user_id)
        current = now or self.now()
        if active and active.date().strftime("%Y-%m") == month:
            record_date = active.date().isoformat()
            totals_by_date[record_date] = totals_by_date.get(record_date, 0) + max(
                0, round((current - active).total_seconds())
            )
        return {
            "month": month,
            "seconds": sum(totals_by_date.values()),
            "days": sum(1 for seconds in totals_by_date.values() if seconds > 0),
        }

    def get_goal_minutes(self, user_id=None):
        value = self._user(user_id).get("settings", {}).get("reading_goal_minutes")
        return int(value) if value is not None else None

    def set_goal_minutes(self, minutes, user_id=None):
        try:
            minutes = int(minutes)
        except (TypeError, ValueError) as error:
            raise ValueError("目標時間を1分以上で入力してください。") from error
        if minutes <= 0:
            raise ValueError("目標時間を1分以上で入力してください。")
        self._user(user_id).setdefault("settings", {})["reading_goal_minutes"] = minutes
        self._data_manager.save()
        return minutes


from core.data import data  # noqa: E402


reading = ReadingManager(data)
