"""Half-month shift availability submissions for store staff."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime

from core.data import data
from core.clock import today_jst
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
        pending = self._data_manager.data.get("store_shift_change_requests", {}).get(
            period["key"], {}).get(staff, {})
        return {"staff": staff, "period": period,
                "days": days,
                "note": str(stored.get("note", "")) if isinstance(stored, dict) else "",
                "submitted_at": str(stored.get("submitted_at", "")) if isinstance(stored, dict) else "",
                "pending_change": dict(pending) if isinstance(pending, dict)
                and pending.get("status") == "pending" else {}}

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
        submissions = self._data_manager.data.setdefault("store_shift_submissions", {}).setdefault(
            period["key"], {})
        existing = submissions.get(staff)
        if existing and today_jst() > date.fromisoformat(period["deadline"]):
            request = {**record, "status": "pending", "requested_at": record["submitted_at"]}
            self._data_manager.data.setdefault("store_shift_change_requests", {}).setdefault(
                period["key"], {})[staff] = request
            self._data_manager.save()
            return {**request, "change_request": True}
        submissions[staff] = record
        self._data_manager.save()
        return {**record, "change_request": False}

    def period_submissions(self, year, month, half):
        period = self.period(year, month, half)
        stored = self._data_manager.data.get("store_shift_submissions", {}).get(period["key"], {})
        return {staff: dict(record) for staff, record in stored.items()
                if staff in self.STAFF and isinstance(record, dict)}

    def pending_changes(self, year, month, half):
        period = self.period(year, month, half)
        stored = self._data_manager.data.get("store_shift_change_requests", {}).get(
            period["key"], {})
        return {staff: dict(record) for staff, record in stored.items()
                if staff in self.STAFF and isinstance(record, dict)
                and record.get("status") == "pending"}

    def auto_schedule(self, year, month, half, lunch_required=3, dinner_required=4,
                      thick_days=None, deputy_rest_priority=True,
                      employee_rest_priority=False):
        """Create a fair, editable draft from submitted availability.

        This never writes attendance records. It is deliberately a proposal so
        an owner can inspect shortages and adjust the roster before using it.
        """
        period = self.period(year, month, half)
        submissions = self.period_submissions(year, month, half)
        try:
            lunch_required = max(0, int(lunch_required))
            dinner_required = max(0, int(dinner_required))
        except (TypeError, ValueError) as error:
            raise ValueError("必要人数は数字で入力してください。") from error
        thick = {int(value) for value in (thick_days or [])
                 if str(value).strip().isdigit()}
        assigned = {name: 0 for name in self.STAFF}
        days = {}

        def priority(name):
            penalty = 0
            if deputy_rest_priority and name == "副社長":
                penalty += 100
            if employee_rest_priority and name == "社員A":
                penalty += 30
            return assigned[name] + penalty, assigned[name], self.STAFF.index(name)

        for day in range(period["start"], period["end"] + 1):
            extra = 1 if day in thick else 0
            day_plan = {name: {"lunch": False, "dinner": False, "time": ""}
                        for name in self.STAFF}
            shortages = {}
            for meal, required in (("lunch", lunch_required + extra),
                                   ("dinner", dinner_required + extra)):
                label = "ランチ" if meal == "lunch" else "ディナー"
                candidates = []
                for name, record in submissions.items():
                    value = self._day_value(record.get("days", {}).get(str(day), {}))
                    if value["type"] not in {label, "通し"}:
                        continue
                    candidates.append((name, value))
                candidates.sort(key=lambda pair: priority(pair[0]))
                selected = candidates[:required]
                for name, value in selected:
                    day_plan[name][meal] = True
                    day_plan[name]["time"] = (
                        f"{value['start'] or '—'}〜{value['end'] or '—'}"
                        if value["start"] or value["end"] else value["type"])
                    assigned[name] += 1
                shortages[meal] = max(0, required - len(selected))
            days[str(day)] = {"staff": day_plan, "shortages": shortages,
                              "thick": day in thick}
        result = {"period": period, "days": days, "assigned": assigned,
                  "settings": {"lunch_required": lunch_required,
                               "dinner_required": dinner_required,
                               "thick_days": sorted(thick),
                               "deputy_rest_priority": bool(deputy_rest_priority),
                               "employee_rest_priority": bool(employee_rest_priority)}}
        self._data_manager.data.setdefault("store_auto_shift_drafts", {})[
            period["key"]] = result
        self._data_manager.save()
        return result

    def review_change(self, staff, year, month, half, approved):
        self._staff(staff)
        period = self.period(year, month, half)
        requests = self._data_manager.data.setdefault("store_shift_change_requests", {}).setdefault(
            period["key"], {})
        request = requests.get(staff)
        if not isinstance(request, dict) or request.get("status") != "pending":
            raise ValueError("確認待ちの変更申請がありません。")
        now = datetime.now().isoformat(timespec="minutes")
        request["status"] = "approved" if approved else "rejected"
        request["reviewed_at"] = now
        if approved:
            self._data_manager.data.setdefault("store_shift_submissions", {}).setdefault(
                period["key"], {})[staff] = {
                    "days": dict(request.get("days", {})),
                    "note": str(request.get("note", "")),
                    "submitted_at": now,
                    "approved_change": True,
                }
        self._data_manager.save()
        return True

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
