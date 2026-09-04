"""Pseudonymous staff wages and daily working hours."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from statistics import median

from core.data import data


class StaffingManager:
    STAFF = ("副社長", "店長", "社員A", *(f"スタッフ{chr(65 + index)}" for index in range(9)))
    SALARIED_STAFF = ("副社長", "店長", "社員A")
    HOURLY_STAFF = STAFF[3:]
    MONTHLY_REST_DAYS = 10
    SALARIED_DAILY_HOURS = 10
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

    def reset_august_2026_once(self):
        """User-authorized reset; retain a recovery archive and never repeat it."""
        marker = "reset_actual_timecards_2026_08_v1"
        migrations = self._data_manager.data.setdefault("data_migrations", {})
        if marker in migrations:
            return 0
        records = self._data_manager.data.setdefault("business_staff_hours", {})
        dates = [key for key in records if key.startswith("2026-08-")]
        archive = {key: records.pop(key) for key in dates}
        self._data_manager.data.setdefault("business_staff_reset_archives", {})[marker] = archive
        migrations[marker] = datetime.now().isoformat(timespec="seconds")
        self._data_manager.save()
        return len(dates)

    def save_person(self, record_date, name, values):
        if name not in self.STAFF:
            raise ValueError("スタッフを選んでください。")
        previous = self._data_manager.data.get("business_staff_hours", {}).get(record_date, {})
        combined = dict(previous)
        combined[name] = dict(values, entry_confirmed=True)
        self.save_day(record_date, combined)

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

    def monthly_salaries(self):
        stored = self._data_manager.data.get("business_staff_monthly_salaries", {})
        return {name: int(stored.get(name, 0) or 0) for name in self.SALARIED_STAFF}

    def save_monthly_salaries(self, values):
        cleaned = {name: self._amount(values.get(name, 0), "月額給与")
                   for name in self.SALARIED_STAFF}
        self._data_manager.data["business_staff_monthly_salaries"] = cleaned
        self._data_manager.save()
        return cleaned

    def commute_rates(self):
        stored = self._data_manager.data.get("business_staff_commute_rates", {})
        return {name: int(stored.get(name, 0) or 0) for name in self.STAFF}

    def save_commute_rates(self, values):
        cleaned = {name: self._amount(values.get(name, 0), "1出勤あたり交通費")
                   for name in self.STAFF}
        self._data_manager.data["business_staff_commute_rates"] = cleaned
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
                result[name]["attended"] = bool(value.get("attended", False))
                result[name]["break_minutes"] = int(value.get("break_minutes", 0) or 0)
                result[name]["entry_confirmed"] = bool(value.get("entry_confirmed", False))
            else:  # Preserve older duration-only entries.
                result[name] = {"lunch_start": "", "lunch_end": "", "dinner_start": "", "dinner_end": "", "transportation": 0, "attended": False, "break_minutes": 0}
        return result

    def planned_day(self, record_date):
        """Return a future roster plan without mixing it into actual timecards."""
        self._date(record_date)
        stored = self._data_manager.data.get("business_staff_shift_plans", {}).get(record_date, {})
        result = self.day(record_date)
        for name in self.HOURLY_STAFF:
            value = stored.get(name, {}) if isinstance(stored, dict) else {}
            result[name] = {
                key: str(value.get(key, "") or "")
                for key in ("lunch_start", "lunch_end", "dinner_start", "dinner_end")
            }
            result[name]["transportation"] = 0
            result[name]["attended"] = False
            result[name]["break_minutes"] = int(value.get("break_minutes", 0) or 0)
        return result

    def separate_legacy_future_plans(self, as_of=None):
        """Move old future simple-roster values out of actual timecards once."""
        as_of = as_of or date.today()
        migration_key = "separated_future_shift_plans_v1"
        migrations = self._data_manager.data.setdefault("data_migrations", {})
        if migrations.get(migration_key):
            return False
        records = self._data_manager.data.setdefault("business_staff_hours", {})
        plans = self._data_manager.data.setdefault("business_staff_shift_plans", {})
        changed = False
        for record_date, record in records.items():
            if record_date <= as_of.isoformat() or not isinstance(record, dict):
                continue
            plan = plans.setdefault(record_date, {})
            for name in self.HOURLY_STAFF:
                value = record.get(name, {})
                if not isinstance(value, dict) or not any(value.get(key) for key in (
                        "lunch_start", "lunch_end", "dinner_start", "dinner_end")):
                    continue
                plan[name] = dict(value)
                record[name] = {
                    "lunch_start": "", "lunch_end": "", "dinner_start": "", "dinner_end": "",
                    "transportation": 0, "attended": False, "break_minutes": 0,
                }
                changed = True
        migrations[migration_key] = datetime.now().isoformat(timespec="seconds")
        self._data_manager.save()
        return changed

    def attendance_progress(self, month, through_date=None):
        """Show which calendar days have been checked for salaried staff."""
        try:
            month_date = datetime.strptime(str(month), "%Y-%m")
        except ValueError as error:
            raise ValueError("対象月が正しくありません。") from error
        days_in_month = monthrange(month_date.year, month_date.month)[1]
        if through_date is None:
            through_day = days_in_month
        else:
            parsed = self._date(through_date).date()
            through_day = parsed.day if parsed.strftime("%Y-%m") == month else days_in_month
        through_day = max(0, min(days_in_month, through_day))
        records = self._data_manager.data.get("business_staff_hours", {})
        result = {}
        for name in self.SALARIED_STAFF:
            checked = []
            for day_number in range(1, through_day + 1):
                record_date = f"{month}-{day_number:02d}"
                record = records.get(record_date, {})
                if (isinstance(record, dict) and isinstance(record.get(name), dict)
                        and bool(record[name].get("attended", False))):
                    checked.append(day_number)
            missing = [value for value in range(1, through_day + 1) if value not in checked]
            result[name] = {
                "checked_days": checked, "missing_days": missing,
                "checked_count": len(checked), "target_count": through_day,
                "latest_date": f"{month}-{checked[-1]:02d}" if checked else "",
                "completion_rate": round(len(checked) / through_day * 100, 1) if through_day else 0,
            }
        return result

    def timecard_progress(self, month, through_date=None):
        """Return the latest recorded work day for every pseudonymous staff member."""
        try:
            month_date = datetime.strptime(str(month), "%Y-%m")
        except ValueError as error:
            raise ValueError("対象月が正しくありません。") from error
        days_in_month = monthrange(month_date.year, month_date.month)[1]
        if through_date is None:
            through_day = days_in_month
        else:
            parsed = self._date(through_date).date()
            through_day = parsed.day if parsed.strftime("%Y-%m") == month else days_in_month
        records = self._data_manager.data.get("business_staff_hours", {})
        result = {}
        for name in self.STAFF:
            entered_days = []
            for day_number in range(1, max(0, min(days_in_month, through_day)) + 1):
                record = records.get(f"{month}-{day_number:02d}", {})
                value = record.get(name, {}) if isinstance(record, dict) else {}
                if not isinstance(value, dict):
                    continue
                has_shift = any(value.get(key) for key in (
                    "lunch_start", "lunch_end", "dinner_start", "dinner_end"))
                if has_shift or bool(value.get("attended", False)) or value.get("entry_confirmed"):
                    entered_days.append(day_number)
            result[name] = {
                "entered_days": entered_days,
                "entered_count": len(entered_days),
                "latest_date": f"{month}-{entered_days[-1]:02d}" if entered_days else "",
                "missing_days": [day for day in range(1, max(0, min(days_in_month, through_day)) + 1)
                                 if day not in entered_days],
            }
        return result

    def _clean_day(self, record_date, values):
        self._date(record_date)
        cleaned = {}
        for name in self.STAFF:
            value = values.get(name, {}) if isinstance(values.get(name, {}), dict) else {}
            cleaned[name] = {key: self._time(value.get(key, "")) for key in
                             ("lunch_start", "lunch_end", "dinner_start", "dinner_end")}
            cleaned[name]["transportation"] = self._amount(value.get("transportation", 0), "交通費")
            cleaned[name]["attended"] = bool(value.get("attended", False))
            cleaned[name]["break_minutes"] = self._amount(value.get("break_minutes", 0), "休憩時間")
            cleaned[name]["entry_source"] = "manual"
            cleaned[name]["entry_confirmed"] = bool(value.get("entry_confirmed", False))
            cleaned[name]["entered_at"] = datetime.now().isoformat(timespec="seconds")
            for prefix in ("lunch", "dinner"):
                start, end = cleaned[name][f"{prefix}_start"], cleaned[name][f"{prefix}_end"]
                if bool(start) != bool(end):
                    raise ValueError(f"{name}の{prefix}開始・終了を両方入力してください。")
            worked_minutes = sum(self._minutes(cleaned[name]))
            if cleaned[name]["break_minutes"] > worked_minutes:
                raise ValueError(f"{name}の休憩時間が勤務時間を超えています。")
        return cleaned

    def save_day(self, record_date, values):
        cleaned = self._clean_day(record_date, values)
        self._data_manager.data.setdefault("business_staff_hours", {})[record_date] = cleaned
        self._data_manager.save()
        return cleaned

    def save_person_month(self, name, month, days, expected=None):
        """Validate the entire batch before writing; preserve other staff/days."""
        from core.clock import today_jst
        if name not in self.STAFF:
            raise ValueError("スタッフを選んでください。")
        if datetime.strptime(month, "%Y-%m").strftime("%Y-%m") != month:
            raise ValueError("対象月を選んでください。")
        records = self._data_manager.data.get("business_staff_hours", {})
        updates = {}
        for record_date, value in days.items():
            if not record_date.startswith(month + "-") or self._date(record_date).date() > today_jst():
                raise ValueError("対象月の今日以前の日付だけ入力できます。")
            if expected is not None and records.get(record_date, {}).get(name, {}) != expected.get(record_date, {}):
                raise ValueError(f"{record_date}は別の画面で更新されました。再読込して確認してください。")
            try:
                updates[record_date] = self._clean_day(record_date, {name: value})[name]
            except ValueError as error:
                raise ValueError(f"{record_date}：{error}") from error
        if updates:
            records = self._data_manager.data.setdefault("business_staff_hours", {})
            for record_date, value in updates.items():
                records.setdefault(record_date, {})[name] = value
            self._data_manager.save()
        return len(updates)

    def day_total(self, record_date):
        wages, shifts = self.wages(), self.day(record_date)
        return round(sum(self._shift_pay(wages[name], shifts[name]) for name in self.HOURLY_STAFF)
                     + self._day_transport(shifts))

    def shift_templates(self, as_of=None):
        """Return robust staff/session templates learned from recorded shifts."""
        as_of = as_of or date.today()
        cutoff = as_of.isoformat()
        records = self._data_manager.data.get("business_staff_hours", {})
        result = {}
        global_samples = {"lunch": [], "dinner": []}
        global_breaks = []
        for record_date in sorted(records, reverse=True):
            if record_date > cutoff:
                continue
            shifts = self.day(record_date)
            for name in self.HOURLY_STAFF:
                shift = shifts[name]
                if self._worked(shift):
                    global_breaks.append(shift["break_minutes"])
                for prefix in ("lunch", "dinner"):
                    start, end = shift[f"{prefix}_start"], shift[f"{prefix}_end"]
                    if not start or not end:
                        continue
                    start_minute = self._clock_minutes(start)
                    duration = self._clock_minutes(end) - start_minute
                    if duration <= 0:
                        duration += 24 * 60
                    global_samples[prefix].append((start_minute, duration))
        global_templates = {}
        defaults = {"lunch": (10 * 60, 5 * 60), "dinner": (17 * 60, 6 * 60)}
        for prefix in ("lunch", "dinner"):
            samples = global_samples[prefix]
            start_minute = round(median(value[0] for value in samples)) if samples else defaults[prefix][0]
            duration = round(median(value[1] for value in samples)) if samples else defaults[prefix][1]
            global_templates[prefix] = {
                "start": self._format_minutes(start_minute),
                "end": self._format_minutes(start_minute + duration),
                "sample_count": len(samples),
                "source": "全体実績" if samples else "初期設定",
            }
        for name in self.HOURLY_STAFF:
            result[name] = {}
            worked_days = []
            for prefix in ("lunch", "dinner"):
                samples = []
                for record_date in sorted(records, reverse=True):
                    if record_date > cutoff:
                        continue
                    shift = self.day(record_date)[name]
                    start, end = shift[f"{prefix}_start"], shift[f"{prefix}_end"]
                    if not start or not end:
                        continue
                    start_minute = self._clock_minutes(start)
                    end_minute = self._clock_minutes(end)
                    duration = end_minute - start_minute
                    if duration <= 0:
                        duration += 24 * 60
                    samples.append((start_minute, duration))
                    if len(samples) == 20:
                        break
                if samples:
                    start_minute = round(median(value[0] for value in samples))
                    duration = round(median(value[1] for value in samples))
                    result[name][prefix] = {
                        "start": self._format_minutes(start_minute),
                        "end": self._format_minutes(start_minute + duration),
                        "sample_count": len(samples),
                        "source": "本人実績",
                    }
                else:
                    result[name][prefix] = dict(global_templates[prefix])
            for record_date in sorted(records, reverse=True):
                if record_date > cutoff:
                    continue
                shift = self.day(record_date)[name]
                if self._worked(shift):
                    worked_days.append(shift["break_minutes"])
                    if len(worked_days) == 20:
                        break
            result[name]["break_minutes"] = round(median(worked_days)) if worked_days else (
                round(median(global_breaks)) if global_breaks else 0)
        return result

    def save_simple_plan(self, record_date, selections, as_of=None):
        """Save a future shift plan using learned lunch/dinner templates."""
        target = self._date(record_date).date()
        as_of = as_of or date.today()
        if target <= as_of:
            raise ValueError("簡単シフト入力は明日以降の日付を選んでください。")
        templates = self.shift_templates(as_of)
        values = self.planned_day(record_date)
        for name in self.HOURLY_STAFF:
            chosen = selections.get(name, {})
            for prefix in ("lunch", "dinner"):
                template = templates[name].get(prefix)
                enabled = bool(chosen.get(prefix, False))
                if enabled and not template:
                    raise ValueError(f"{name}の{prefix}実績がないため、最初の1回は時刻を入力してください。")
                values[name][f"{prefix}_start"] = template["start"] if enabled else ""
                values[name][f"{prefix}_end"] = template["end"] if enabled else ""
            values[name]["break_minutes"] = templates[name]["break_minutes"] if any(
                bool(chosen.get(prefix, False)) for prefix in ("lunch", "dinner")) else 0
        cleaned = {name: {
            key: values[name][key]
            for key in ("lunch_start", "lunch_end", "dinner_start", "dinner_end", "break_minutes")
        } for name in self.HOURLY_STAFF}
        self._data_manager.data.setdefault("business_staff_shift_plans", {})[record_date] = cleaned
        self._data_manager.save()
        return cleaned

    def month_total(self, month):
        datetime.strptime(month, "%Y-%m")
        wages = self.wages()
        records = self._data_manager.data.get("business_staff_hours", {})
        return round(sum(self._shift_pay(wages[name], self.day(record_date)[name])
                         for record_date in records if record_date.startswith(month)
                         for name in self.HOURLY_STAFF)
                     + sum(self.monthly_salaries().values())
                     + sum(self._day_transport(self.day(record_date))
                           for record_date in records if record_date.startswith(month)))

    def month_cost_summary(self, month, as_of=None):
        records = self._data_manager.data.get("business_staff_hours", {})
        plan_records = self._data_manager.data.get("business_staff_shift_plans", {})
        wages, settings, rates = self.wages(), self.insurance_settings(), self.insurance_rates()
        as_of = as_of or date.today()
        actual_cutoff = as_of.isoformat()
        year, month_number = int(month[:4]), int(month[5:7])
        days_in_month = monthrange(year, month_number)[1]
        if (year, month_number) < (as_of.year, as_of.month):
            elapsed_days = days_in_month
        elif (year, month_number) > (as_of.year, as_of.month):
            elapsed_days = 0
        else:
            elapsed_days = min(as_of.day, days_in_month)
        vice_progress = elapsed_days / days_in_month
        planned_days = max(1, days_in_month - self.MONTHLY_REST_DAYS)
        attendance = {name: sum(
            1 for day in records if day.startswith(month) and day <= actual_cutoff and self.day(day)[name]["attended"]
        ) for name in self.SALARIED_STAFF}
        salaries = self.monthly_salaries()
        salaried_actual = round(salaries["副社長"] * vice_progress) + sum(
            min(salaries[name], round(salaries[name] / planned_days * attendance[name]))
            for name in ("店長", "社員A"))
        gross = salaried_actual
        salaried_transport = hourly_transport = 0
        for record_date in records:
            if not record_date.startswith(month) or record_date > actual_cutoff:
                continue
            shifts = self.day(record_date)
            gross += sum(self._shift_pay(wages[name], shifts[name]) for name in self.HOURLY_STAFF)
            rates_by_staff = self.commute_rates()
            salaried_transport += sum(rates_by_staff[name] for name in self.SALARIED_STAFF
                                      if shifts[name]["attended"])
            hourly_transport += sum(rates_by_staff[name] for name in self.HOURLY_STAFF
                                    if self._worked(shifts[name]))
        transportation = salaried_transport + hourly_transport
        social_by_group = {"salaried": 0.0, "hourly": 0.0}
        employment_by_group = {"salaried": 0.0, "hourly": 0.0}
        for name in self.STAFF:
            setting = settings[name]
            if setting["social"]:
                rate = rates["health"] + rates["pension"] + rates["other"]
                if setting["care"]:
                    rate += rates["care"]
                if name == "副社長":
                    factor = vice_progress
                elif name in ("店長", "社員A"):
                    factor = min(1, attendance[name] / planned_days)
                else:
                    factor = 1
                group = "salaried" if name in self.SALARIED_STAFF else "hourly"
                social_by_group[group] += setting["standard_monthly"] * rate / 100 * factor
            if setting["employment"]:
                if name in self.SALARIED_STAFF:
                    salary_actual = (round(salaries[name] * vice_progress) if name == "副社長"
                                     else min(salaries[name], round(
                                         salaries[name] / planned_days * attendance[name])))
                    staff_gross = salary_actual + sum(
                        self.commute_rates()[name] for day in records if day.startswith(month)
                        and self.day(day)[name]["attended"])
                else:
                    staff_gross = sum(self._shift_pay(wages[name], self.day(day)[name])
                                      + (self.commute_rates()[name] if self._worked(self.day(day)[name]) else 0)
                                      for day in records if day.startswith(month) and day <= actual_cutoff)
                group = "salaried" if name in self.SALARIED_STAFF else "hourly"
                employment_by_group[group] += staff_gross * rates["employment"] / 100
        hourly_gross = gross - salaried_actual
        insurance_by_group = {
            "salaried": round(social_by_group["salaried"] + employment_by_group["salaried"]
                               + (salaried_actual + salaried_transport) * rates["workers_comp"] / 100),
            "hourly": round(social_by_group["hourly"] + employment_by_group["hourly"]
                             + (hourly_gross + hourly_transport) * rates["workers_comp"] / 100),
        }
        employer_insurance = sum(insurance_by_group.values())
        forecast_social_by_group = {"salaried": 0.0, "hourly": 0.0}
        for name in self.STAFF:
            setting = settings[name]
            if setting["social"]:
                rate = rates["health"] + rates["pension"] + rates["other"]
                if setting["care"]:
                    rate += rates["care"]
                group = "salaried" if name in self.SALARIED_STAFF else "hourly"
                forecast_social_by_group[group] += setting["standard_monthly"] * rate / 100
        planned_hourly_gross = sum(
            self._shift_pay(wages[name], self.planned_day(record_date)[name])
            for record_date in plan_records if record_date.startswith(month) and record_date > actual_cutoff
            for name in self.HOURLY_STAFF)
        planned_hourly_transport = sum(
            self.commute_rates()[name]
            for record_date in plan_records if record_date.startswith(month) and record_date > actual_cutoff
            for name in self.HOURLY_STAFF if self._worked(self.planned_day(record_date)[name]))
        forecast_gross = sum(salaries.values()) + hourly_gross + planned_hourly_gross
        forecast_transportation = transportation + planned_hourly_transport
        planned_employment = sum(
            (self._shift_pay(wages[name], self.planned_day(record_date)[name])
             + (self.commute_rates()[name] if self._worked(self.planned_day(record_date)[name]) else 0))
            * rates["employment"] / 100
            for record_date in plan_records if record_date.startswith(month) and record_date > actual_cutoff
            for name in self.HOURLY_STAFF if settings[name]["employment"])
        forecast_insurance = round(sum(forecast_social_by_group.values())
                                   + sum(employment_by_group.values()) + planned_employment
                                   + (forecast_gross + forecast_transportation) * rates["workers_comp"] / 100)
        groups = {
            "salaried": {"gross_wages": round(salaried_actual),
                         "transportation": round(salaried_transport),
                         "employer_insurance": insurance_by_group["salaried"]},
            "hourly": {"gross_wages": round(hourly_gross),
                       "transportation": round(hourly_transport),
                       "employer_insurance": insurance_by_group["hourly"]},
        }
        for values in groups.values():
            values["company_cost"] = sum(values.values())
        return {"gross_wages": round(gross), "transportation": round(transportation),
                "employer_insurance": employer_insurance,
                "company_cost": round(gross + transportation + employer_insurance),
                "planned_days": planned_days, "attendance": attendance,
                "elapsed_days": elapsed_days, "days_in_month": days_in_month,
                "daily_hours": self.SALARIED_DAILY_HOURS,
                "forecast_gross_wages": round(forecast_gross),
                "forecast_employer_insurance": forecast_insurance,
                "forecast_transportation": round(forecast_transportation),
                "planned_hourly_gross": round(planned_hourly_gross),
                "forecast_company_cost": round(forecast_gross + forecast_transportation + forecast_insurance),
                "groups": groups}

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
        break_minutes = shift.get("break_minutes", 0)
        normal_after_break = max(0, normal - break_minutes)
        night_after_break = max(0, night - max(0, break_minutes - normal))
        return {"normal_minutes": normal, "night_minutes": night,
                "break_minutes": break_minutes,
                "paid_minutes": normal_after_break + night_after_break,
                "total_minutes": normal + night,
                "pay": round(self._shift_pay(self.wages()[name], shift))}

    def _day_transport(self, shifts):
        rates = self.commute_rates()
        return sum(rates[name] for name in self.STAFF
                   if (shifts[name]["attended"] if name in self.SALARIED_STAFF
                       else self._worked(shifts[name])))

    @staticmethod
    def _worked(shift):
        return any(shift.get(key) for key in
                   ("lunch_start", "lunch_end", "dinner_start", "dinner_end"))

    @classmethod
    def _shift_pay(cls, wage, shift):
        normal, night = cls._minutes(shift)
        break_minutes = int(shift.get("break_minutes", 0) or 0)
        normal = max(0, normal - break_minutes)
        night = max(0, night - max(0, break_minutes - cls._minutes(shift)[0]))
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

    _clock_minutes = _minute

    @staticmethod
    def _format_minutes(value):
        value %= 1440
        return f"{value // 60:02d}:{value % 60:02d}"

    @staticmethod
    def _date(value):
        return datetime.strptime(str(value), "%Y-%m-%d")

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
        value = str(value or "").strip().replace("：", ":")
        if not value:
            return ""
        if value.isdigit() and len(value) in (3, 4):
            value = f"{value[:-2]}:{value[-2:]}"
        try:
            parsed = datetime.strptime(value, "%H:%M")
        except ValueError as error:
            raise ValueError("時刻は何時何分で入力してください。") from error
        return parsed.strftime("%H:%M")


staffing = StaffingManager()
staffing.reset_august_2026_once()
