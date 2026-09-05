"""Half-month shift availability submissions for store staff."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
import base64
import hashlib
import hmac
import os
import secrets
import unicodedata

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
            request = {**record, "status": "pending", "requested_at": record["submitted_at"],
                       "original_days": dict(existing.get("days", {})),
                       "original_note": str(existing.get("note", ""))}
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

    def cancel_submission(self, staff, year, month, half, pin=None, administrator=False):
        self._staff(staff)
        if not administrator and not self.verify_staff_pin(staff, pin):
            raise ValueError("個人PINが違います。")
        period = self.period(year, month, half)
        records = self._data_manager.data.setdefault("store_shift_submissions", {}).setdefault(period["key"], {})
        if staff not in records:
            raise ValueError("取り消す提出がありません。")
        now = datetime.now().isoformat(timespec="minutes")
        if not administrator and today_jst() > date.fromisoformat(period["deadline"]):
            self._data_manager.data.setdefault("store_shift_change_requests", {}).setdefault(period["key"], {})[staff] = {
                "action": "cancel", "status": "pending", "requested_at": now}
            self._data_manager.save()
            return {"change_request": True}
        self._archive_cancelled(staff, period["key"], now)
        request = self._data_manager.data.get("store_shift_change_requests", {}).get(period["key"], {}).get(staff)
        if request and request.get("status") == "pending":
            request["status"] = "cancelled"
        self._data_manager.save()
        return {"change_request": False}

    def _archive_cancelled(self, staff, key, now):
        record = self._data_manager.data.get("store_shift_submissions", {}).get(key, {}).pop(staff, None)
        if record is not None:
            self._data_manager.data.setdefault("store_shift_cancelled_archive", []).append(
                {"staff": staff, "period": key, "record": record, "cancelled_at": now})
        self._data_manager.data.get("store_auto_shift_drafts", {}).pop(key, None)

    def pending_changes(self, year, month, half):
        period = self.period(year, month, half)
        stored = self._data_manager.data.get("store_shift_change_requests", {}).get(
            period["key"], {})
        return {staff: dict(record) for staff, record in stored.items()
                if staff in self.STAFF and isinstance(record, dict)
                and record.get("status") == "pending"}

    @staticmethod
    def _clean_pin(pin):
        value = unicodedata.normalize("NFKC", str(pin or "")).strip()
        if not value.isdigit() or not 4 <= len(value) <= 8:
            raise ValueError("個人PINは4〜8桁の数字で設定してください。")
        return value

    def has_staff_pin(self, staff):
        self._staff(staff)
        stored = self._data_manager.data.get("store_shift_staff_pins", {}).get(staff, {})
        return bool(isinstance(stored, dict) and stored.get("salt") and stored.get("digest"))

    def set_staff_pin(self, staff, pin):
        """Set a staff PIN and keep an authenticated encrypted admin-viewable copy."""
        self._staff(staff)
        value = self._clean_pin(pin)
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", value.encode("utf-8"), salt.encode("ascii"), 120_000,
        ).hex()
        self._data_manager.data.setdefault("store_shift_staff_pins", {})[staff] = {
            "salt": salt, "digest": digest, "sealed_pin": self._seal_pin(value),
        }
        self._data_manager.save()

    @staticmethod
    def _pin_secret():
        return os.environ.get("STORAGE_SECRET", "habitory-local-pin-key").encode("utf-8")

    @classmethod
    def _seal_pin(cls, value):
        nonce = secrets.token_bytes(16)
        key = hashlib.sha256(cls._pin_secret() + nonce).digest()
        encrypted = bytes(byte ^ key[index % len(key)]
                          for index, byte in enumerate(value.encode("utf-8")))
        payload = nonce + encrypted
        tag = hmac.new(cls._pin_secret(), payload, hashlib.sha256).digest()[:16]
        return base64.urlsafe_b64encode(payload + tag).decode("ascii")

    @classmethod
    def _open_pin(cls, sealed):
        try:
            raw = base64.urlsafe_b64decode(str(sealed).encode("ascii"))
            payload, tag = raw[:-16], raw[-16:]
            if not hmac.compare_digest(
                    tag, hmac.new(cls._pin_secret(), payload, hashlib.sha256).digest()[:16]):
                return None
            nonce, encrypted = payload[:16], payload[16:]
            key = hashlib.sha256(cls._pin_secret() + nonce).digest()
            return bytes(byte ^ key[index % len(key)]
                         for index, byte in enumerate(encrypted)).decode("utf-8")
        except (ValueError, UnicodeError):
            return None

    def staff_pin_for_admin(self, staff):
        """Return a PIN only for the administrator settings UI."""
        self._staff(staff)
        stored = self._data_manager.data.get("store_shift_staff_pins", {}).get(staff, {})
        if not isinstance(stored, dict):
            return None
        return self._open_pin(stored.get("sealed_pin", ""))

    def verify_staff_pin(self, staff, pin):
        self._staff(staff)
        try:
            value = self._clean_pin(pin)
        except ValueError:
            return False
        stored = self._data_manager.data.get("store_shift_staff_pins", {}).get(staff, {})
        if not isinstance(stored, dict) or not stored.get("salt") or not stored.get("digest"):
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", value.encode("utf-8"), stored["salt"].encode("ascii"), 120_000,
        ).hex()
        return hmac.compare_digest(digest, stored["digest"])

    def auto_schedule(self, year, month, half, lunch_required=3, dinner_required=4,
                      thick_days=None, deputy_rest_priority=True,
                      employee_rest_priority=False,
                      require_manager_or_deputy=True,
                      align_deputy_employee=True):
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

        salaried = tuple(StaffingManager.SALARIED_STAFF)
        all_days = list(range(period["start"], period["end"] + 1))
        rest_days = {}
        for index, name in enumerate(salaried):
            record = submissions.get(name, {})
            absolute = {day for day in all_days if self._day_value(
                record.get("days", {}).get(str(day), {}))["type"] == "絶対休み"}
            needed = max(0, 5 - len(absolute))
            available = [day for day in all_days if day not in absolute and day not in thick]
            available += [day for day in all_days if day not in absolute and day in thick]
            if align_deputy_employee and name == "社員A" and "副社長" in rest_days:
                preferred = [day for day in rest_days["副社長"] if day not in absolute]
                chosen = preferred[:needed]
                chosen += [day for day in available if day not in chosen][:needed - len(chosen)]
            else:
                offset = (index * 5) % max(1, len(available))
                rotated = available[offset:] + available[:offset]
                chosen = rotated[:needed]
            rest_days[name] = absolute | set(chosen)

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
                selected = []
                for name in salaried:
                    if day in rest_days[name]:
                        continue
                    value = self._day_value(submissions.get(name, {}).get(
                        "days", {}).get(str(day), {}))
                    selected.append((name, value if value["type"] else {
                        "type": "通し", "start": "", "end": ""}))
                candidates = []
                for name, record in submissions.items():
                    if name in salaried:
                        continue
                    value = self._day_value(record.get("days", {}).get(str(day), {}))
                    if value["type"] not in {label, "通し"}:
                        continue
                    candidates.append((name, value))
                candidates.sort(key=lambda pair: priority(pair[0]))
                selected += candidates[:max(0, required - len(selected))]
                if require_manager_or_deputy and required and not any(
                        pair[0] in {"副社長", "店長"} for pair in selected):
                    leader = next((pair for pair in candidates
                                   if pair[0] in {"副社長", "店長"}), None)
                    if leader:
                        selected[-1:] = [leader]
                selected_names = {name for name, _value in selected}
                pair_names = {"副社長", "社員A"}
                if align_deputy_employee and required >= 2 and len(
                        selected_names & pair_names) == 1:
                    missing_name = (pair_names - selected_names).pop()
                    missing = next((pair for pair in candidates if pair[0] == missing_name), None)
                    if missing:
                        replace_index = next((index for index in range(len(selected) - 1, -1, -1)
                                              if selected[index][0] not in pair_names
                                              and selected[index][0] != "店長"), None)
                        if replace_index is not None:
                            selected[replace_index] = missing
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
                               "employee_rest_priority": bool(employee_rest_priority),
                               "require_manager_or_deputy": bool(require_manager_or_deputy),
                               "align_deputy_employee": bool(align_deputy_employee),
                               "salaried_rest_days": {name: sorted(value)
                                                       for name, value in rest_days.items()}}}
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
        if approved and request.get("action") == "cancel":
            self._archive_cancelled(staff, period["key"], now)
        elif approved:
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
