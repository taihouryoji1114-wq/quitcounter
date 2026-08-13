"""Pseudonymous staff wages and daily working hours."""

from __future__ import annotations

from datetime import datetime

from core.data import data


class StaffingManager:
    STAFF = tuple(f"スタッフ{chr(65 + index)}" for index in range(15))

    def __init__(self, manager=None):
        self._data_manager = manager or data

    def wages(self):
        stored = self._data_manager.data.get("business_staff_wages", {})
        return {name: int(stored.get(name, 0) or 0) for name in self.STAFF}

    def save_wages(self, values):
        cleaned = {name: self._amount(values.get(name, 0), "時給") for name in self.STAFF}
        self._data_manager.data["business_staff_wages"] = cleaned
        self._data_manager.save()
        return cleaned

    def day(self, record_date):
        self._date(record_date)
        stored = self._data_manager.data.get("business_staff_hours", {}).get(record_date, {})
        return {name: float(stored.get(name, 0) or 0) for name in self.STAFF}

    def save_day(self, record_date, values):
        self._date(record_date)
        cleaned = {name: self._hours(values.get(name, 0)) for name in self.STAFF}
        self._data_manager.data.setdefault("business_staff_hours", {})[record_date] = cleaned
        self._data_manager.save()
        return cleaned

    def day_total(self, record_date):
        wages, hours = self.wages(), self.day(record_date)
        return round(sum(wages[name] * hours[name] for name in self.STAFF))

    def month_total(self, month):
        datetime.strptime(month, "%Y-%m")
        wages = self.wages()
        records = self._data_manager.data.get("business_staff_hours", {})
        return round(sum(
            wages[name] * float(hours.get(name, 0) or 0)
            for record_date, hours in records.items() if record_date.startswith(month)
            for name in self.STAFF
        ))

    @staticmethod
    def _date(value):
        datetime.strptime(str(value), "%Y-%m-%d")

    @staticmethod
    def _amount(value, label):
        try:
            result = int(float(value or 0))
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label}は0以上の数字で入力してください。") from error
        if result < 0:
            raise ValueError(f"{label}は0以上の数字で入力してください。")
        return result

    @staticmethod
    def _hours(value):
        try:
            result = float(value or 0)
        except (TypeError, ValueError) as error:
            raise ValueError("勤務時間は0以上の数字で入力してください。") from error
        if result < 0 or result > 24:
            raise ValueError("勤務時間は0〜24時間で入力してください。")
        return round(result, 2)


staffing = StaffingManager()
