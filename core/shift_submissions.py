"""Half-month shift availability submissions for store staff."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime

from core.data import data
from core.staffing import StaffingManager


class ShiftSubmissionManager:
    OPTIONS = ("通し", "ランチ", "ディナー", "絶対休み")
    STAFF = StaffingManager.STAFF

    def __init__(self, data_manager=None):
        self._data_manager = data_manager or data

    @staticmethod
    def period(year, month, half):
        year, month = int(year), int(month)
        if half not in {"first", "second"}:
            raise ValueError("提出期間が正しくありません。")
        last = monthrange(year, month)[1]
        start, end = (1, 15) if half == "first" else (16, last)
        label = f"{year}年{month}月 {'前半（1〜15日）' if half == 'first' else f'後半（16〜{last}日）'}"
        if half == "first":
            previous_month = 12 if month == 1 else month - 1
            previous_year = year - 1 if month == 1 else year
            deadline = date(previous_year, previous_month, 20)
        else:
            deadline = date(year, month, 5)
        return {"key": f"{year:04d}-{month:02d}-{half}", "year": year, "month": month,
                "half": half, "start": start, "end": end, "label": label,
                "deadline": deadline.isoformat()}

    def submission(self, staff, year, month, half):
        self._staff(staff)
        period = self.period(year, month, half)
        stored = self._data_manager.data.get("store_shift_submissions", {}).get(
            period["key"], {}).get(staff, {})
        raw_days = dict(stored.get("days", {})) if isinstance(stored, dict) else {}
        days = {str(day): self._day_value(value) for day, value in raw_days.items()}
        return {"staff": staff, "period": period,
                "days": days,
                "note": str(stored.get("note", "")) if isinstance(stored, dict) else "",
                "submitted_at": str(stored.get("submitted_at", "")) if isinstance(stored, dict) else ""}

    def save(self, staff, year, month, half, days, note=""):
        self._staff(staff)
        period = self.period(year, month, half)
        cleaned = {}
        for day in range(period["start"], period["end"] + 1):
            value = self._day_value((days or {}).get(str(day), {}))
            if value["type"] and value["type"] not in self.OPTIONS:
                raise ValueError(f"{day}日の希望が正しくありません。")
            if value["start"] and not self._valid_time(value["start"]):
                raise ValueError(f"{day}日の開始時間が正しくありません。")
            if value["end"] and not self._valid_time(value["end"]):
                raise ValueError(f"{day}日の終了時間が正しくありません。")
            if value["type"] or value["start"] or value["end"]:
                cleaned[str(day)] = value
        record = {"days": cleaned, "note": str(note or "").strip()[:500],
                  "submitted_at": datetime.now().isoformat(timespec="minutes")}
        self._data_manager.data.setdefault("store_shift_submissions", {}).setdefault(
            period["key"], {})[staff] = record
        self._data_manager.save()
        return record

    def period_submissions(self, year, month, half):
        period = self.period(year, month, half)
        stored = self._data_manager.data.get("store_shift_submissions", {}).get(period["key"], {})
        return {staff: dict(record) for staff, record in stored.items()
                if staff in self.STAFF and isinstance(record, dict)}

    def _staff(self, staff):
        if staff not in self.STAFF:
            raise ValueError("スタッフを選択してください。")

    @classmethod
    def _day_value(cls, value):
        if isinstance(value, dict):
            shift_type = str(value.get("type", "")).strip()
            start = str(value.get("start", "")).strip()
            end = str(value.get("end", "")).strip()
        else:
            shift_type, start, end = str(value or "").strip(), "", ""
        if shift_type == "出勤可":
            shift_type = "通し"
        elif shift_type == "休み":
            shift_type = "絶対休み"
        return {"type": shift_type, "start": start, "end": end}

    @staticmethod
    def _valid_time(value):
        try:
            datetime.strptime(value, "%H:%M")
            return True
        except ValueError:
            return False


shift_submissions = ShiftSubmissionManager()
