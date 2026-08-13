"""Pseudonymous staff wages and daily working hours."""

from __future__ import annotations

from datetime import datetime

from core.data import data


class StaffingManager:
    STAFF = ("店長", "社員A", *(f"スタッフ{chr(65 + index)}" for index in range(15)))
    DEPENDENT_LIMITS = {
        "general": ("一般の税扶養", 1_230_000),
        "young": ("19〜22歳（控除維持）", 1_500_000),
        "social": ("社会保険の扶養", 1_300_000),
        "senior": ("60歳以上・一定の障害（社保）", 1_800_000),
        "custom": ("個別設定", 0),
        "none": ("扶養管理なし", 0),
    }

    def __init__(self, manager=None):
        self._data_manager = manager or data

    def wages(self):
        stored = self._data_manager.data.get("business_staff_wages", {})
        return {name: int(stored.get(name, 0) or 0) for name in self.STAFF}

    def insurance_rates(self):
        stored = self._data_manager.data.get("business_employer_insurance_rates", {})
        return {"health": float(stored.get("health", 0) or 0),
                "pension": float(stored.get("pension", 9.15) or 9.15),
                "care": float(stored.get("care", 0.795) or 0.795),
                "employment": float(stored.get("employment", 0.85) or 0.85),
                "workers_comp": float(stored.get("workers_comp", 0.3) or 0.3),
                "other": float(stored.get("other", 0) or 0)}

    def save_insurance_rates(self, values):
        cleaned = {}
        for key in ("health", "pension", "care", "employment", "workers_comp", "other"):
            rate = float(values.get(key, 0) or 0)
            if rate < 0 or rate > 100:
                raise ValueError("保険料率は0〜100%で入力してください。")
            cleaned[key] = round(rate, 4)
        self._data_manager.data["business_employer_insurance_rates"] = cleaned
        self._data_manager.save()
        return cleaned

    def insurance_settings(self):
        stored = self._data_manager.data.get("business_staff_insurance_settings", {})
        return {name: {"social": bool(stored.get(name, {}).get("social", False)),
                       "standard_monthly": int(stored.get(name, {}).get("standard_monthly", 0) or 0),
                       "care": bool(stored.get(name, {}).get("care", False)),
                       "employment": bool(stored.get(name, {}).get("employment", False))}
                for name in self.STAFF}

    def save_insurance_settings(self, values):
        cleaned = {name: {"social": bool(values.get(name, {}).get("social", False)),
                          "standard_monthly": self._amount(values.get(name, {}).get("standard_monthly", 0), "標準報酬月額"),
                          "care": bool(values.get(name, {}).get("care", False)),
                          "employment": bool(values.get(name, {}).get("employment", False))}
                   for name in self.STAFF}
        self._data_manager.data["business_staff_insurance_settings"] = cleaned
        self._data_manager.save()
        return cleaned

    def save_wages(self, values):
        cleaned = {name: self._amount(values.get(name, 0), "時給") for name in self.STAFF}
        self._data_manager.data["business_staff_wages"] = cleaned
        self._data_manager.save()
        return cleaned

    def dependent_settings(self):
        stored = self._data_manager.data.get("business_staff_dependent_settings", {})
        result = {}
        for name in self.STAFF:
            value = stored.get(name, {}) if isinstance(stored.get(name, {}), dict) else {}
            mode = value.get("mode", "social")
            if mode not in self.DEPENDENT_LIMITS:
                mode = "social"
            default_limit = self.DEPENDENT_LIMITS[mode][1]
            legacy = int(value.get("prior_income", 0) or 0)
            result[name] = {"mode": mode, "limit": int(value.get("limit", default_limit) or default_limit),
                            "prior_income": int(value.get("store_prior_income", legacy) or 0),
                            "other_income": int(value.get("other_income", 0) or 0)}
        return result

    def save_dependent_settings(self, values):
        cleaned = {}
        for name in self.STAFF:
            value = values.get(name, {})
            mode = value.get("mode", "social")
            if mode not in self.DEPENDENT_LIMITS:
                raise ValueError("扶養区分が正しくありません。")
            default_limit = self.DEPENDENT_LIMITS[mode][1]
            cleaned[name] = {"mode": mode,
                             "limit": self._amount(value.get("limit", default_limit), "上限額") if mode != "none" else 0,
                             "store_prior_income": self._amount(value.get("prior_income", 0), "当店の導入前給与"),
                             "other_income": self._amount(value.get("other_income", 0), "他社給与")}
        self._data_manager.data["business_staff_dependent_settings"] = cleaned
        self._data_manager.save()
        return cleaned

    def day(self, record_date):
        self._date(record_date)
        stored = self._data_manager.data.get("business_staff_hours", {}).get(record_date, {})
        result = {}
        for name in self.STAFF:
            value = stored.get(name, {})
            if isinstance(value, dict):
                result[name] = {key: str(value.get(key, "") or "") for key in
                                ("lunch_start", "lunch_end", "dinner_start", "dinner_end")}
                result[name]["transportation"] = int(value.get("transportation", 0) or 0)
            else:  # Preserve older duration-only entries.
                result[name] = {"lunch_start": "", "lunch_end": "", "dinner_start": "", "dinner_end": "", "transportation": 0}
        return result

    def save_day(self, record_date, values):
        self._date(record_date)
        cleaned = {}
        for name in self.STAFF:
            value = values.get(name, {}) if isinstance(values.get(name, {}), dict) else {}
            cleaned[name] = {key: self._time(value.get(key, "")) for key in
                             ("lunch_start", "lunch_end", "dinner_start", "dinner_end")}
            cleaned[name]["transportation"] = self._amount(value.get("transportation", 0), "交通費")
            for prefix in ("lunch", "dinner"):
                start, end = cleaned[name][f"{prefix}_start"], cleaned[name][f"{prefix}_end"]
                if bool(start) != bool(end):
                    raise ValueError(f"{name}の{prefix}開始・終了を両方入力してください。")
        self._data_manager.data.setdefault("business_staff_hours", {})[record_date] = cleaned
        self._data_manager.save()
        return cleaned

    def day_total(self, record_date):
        wages, shifts = self.wages(), self.day(record_date)
        return round(sum(self._shift_pay(wages[name], shifts[name]) + shifts[name]["transportation"] for name in self.STAFF))

    def month_total(self, month):
        datetime.strptime(month, "%Y-%m")
        wages = self.wages()
        records = self._data_manager.data.get("business_staff_hours", {})
        return round(sum(self._shift_pay(wages[name], self.day(record_date)[name]) + self.day(record_date)[name]["transportation"]
                         for record_date in records if record_date.startswith(month)
                         for name in self.STAFF))

    def month_cost_summary(self, month):
        records = self._data_manager.data.get("business_staff_hours", {})
        wages, settings, rates = self.wages(), self.insurance_settings(), self.insurance_rates()
        gross = transportation = 0
        for record_date in records:
            if not record_date.startswith(month):
                continue
            shifts = self.day(record_date)
            gross += sum(self._shift_pay(wages[name], shifts[name]) for name in self.STAFF)
            transportation += sum(shifts[name]["transportation"] for name in self.STAFF)
        social = labor = 0
        for name in self.STAFF:
            setting = settings[name]
            if setting["social"]:
                rate = rates["health"] + rates["pension"] + rates["other"]
                if setting["care"]:
                    rate += rates["care"]
                social += setting["standard_monthly"] * rate / 100
            if setting["employment"]:
                staff_gross = sum(self._shift_pay(wages[name], self.day(day)[name]) + self.day(day)[name]["transportation"] for day in records if day.startswith(month))
                labor += staff_gross * rates["employment"] / 100
        labor += (gross + transportation) * rates["workers_comp"] / 100
        employer_insurance = round(social + labor)
        return {"gross_wages": round(gross), "transportation": round(transportation),
                "employer_insurance": employer_insurance,
                "company_cost": round(gross + transportation + employer_insurance)}

    def year_staff_total(self, year, name):
        records = self._data_manager.data.get("business_staff_hours", {})
        wage = self.wages()[name]
        return round(sum(self._shift_pay(wage, self.day(record_date)[name])
                         for record_date in records if record_date.startswith(f"{int(year):04d}-")))

    def dependent_status(self, year, name, as_of=None):
        as_of = as_of or datetime.now().date()
        setting = self.dependent_settings()[name]
        earned = self.year_staff_total(year, name) + setting["prior_income"] + setting["other_income"]
        if setting["mode"] == "none":
            return {"mode": "none", "earned": earned, "limit": 0, "remaining": None,
                    "projected": earned, "level": "none"}
        elapsed = max(1, as_of.timetuple().tm_yday) if as_of.year == int(year) else 365
        projected = round(earned / elapsed * 365) if earned else 0
        limit = setting["limit"]
        ratio = max(earned, projected) / limit if limit else 0
        level = "over" if earned >= limit else "danger" if ratio >= .95 else "warning" if ratio >= .8 else "safe"
        return {"mode": setting["mode"], "earned": earned, "limit": limit,
                "remaining": max(0, limit - earned), "projected": projected, "level": level}

    def day_detail(self, record_date, name):
        shift = self.day(record_date)[name]
        normal, night = self._minutes(shift)
        return {"normal_minutes": normal, "night_minutes": night,
                "total_minutes": normal + night,
                "pay": round(self._shift_pay(self.wages()[name], shift))}

    @classmethod
    def _shift_pay(cls, wage, shift):
        normal, night = cls._minutes(shift)
        return wage * normal / 60 + wage * 1.25 * night / 60

    @classmethod
    def _minutes(cls, shift):
        normal = night = 0
        for prefix in ("lunch", "dinner"):
            start, end = shift.get(f"{prefix}_start"), shift.get(f"{prefix}_end")
            if not start or not end:
                continue
            start_min, end_min = cls._minute(start), cls._minute(end)
            if end_min <= start_min:
                end_min += 1440
            for minute in range(start_min, end_min):
                clock = minute % 1440
                if clock >= 1320 or clock < 300:
                    night += 1
                else:
                    normal += 1
        return normal, night

    @staticmethod
    def _minute(value):
        hour, minute = (int(part) for part in value.split(":"))
        return hour * 60 + minute

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
    def _time(value):
        value = str(value or "").strip()
        if not value:
            return ""
        try:
            parsed = datetime.strptime(value, "%H:%M")
        except ValueError as error:
            raise ValueError("時刻は何時何分で入力してください。") from error
        return parsed.strftime("%H:%M")


staffing = StaffingManager()
