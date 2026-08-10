"""User-scoped nutrition settings and calorie estimation for Habitory Ver3."""

from __future__ import annotations

from datetime import datetime, time

from core.clock import now_jst, today_jst


ACTIVITY_FACTORS = {
    "少ない": 1.2,
    "普通": 1.375,
    "多い": 1.55,
    "非常に多い": 1.725,
}
NUTRITION_SETTING_KEYS = (
    "protein_goal",
    "calorie_goal",
    "basal_metabolism",
    "activity_level",
)


def calculate_daily_expenditure(basal_metabolism, activity_level):
    """Return estimated daily expenditure in kcal, rounded to a whole kcal."""
    basal_metabolism = NutritionSettingsManager.validate_number(
        basal_metabolism, "基礎代謝"
    )
    if basal_metabolism is None or activity_level in (None, ""):
        return None
    if activity_level not in ACTIVITY_FACTORS:
        raise ValueError("活動量を選択してください。")
    return round(basal_metabolism * ACTIVITY_FACTORS[activity_level])


def calculate_period_expenditure(daily_expenditure, start_date, end_date, now=None):
    """Estimate expenditure, prorating the current Japan day by elapsed time."""
    if daily_expenditure is None:
        return None
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    if start > end:
        raise ValueError("集計期間の開始日と終了日が正しくありません。")
    current = now or now_jst()
    japan_today = current.date() if now is not None else today_jst()
    if end < japan_today:
        day_units = (end - start).days + 1
    elif start > japan_today:
        day_units = 0
    else:
        full_days = max(0, (japan_today - start).days)
        elapsed = (current - datetime.combine(
            japan_today, time.min, tzinfo=current.tzinfo
        )).total_seconds()
        day_units = full_days + min(1, max(0, elapsed / 86400))
    return daily_expenditure * day_units


class NutritionSettingsManager:
    def __init__(self, data_manager):
        self._data_manager = data_manager

    def _user(self, user_id=None):
        return self._data_manager.users.get_user(
            user_id or self._data_manager.active_user_id
        )

    def get_settings(self, user_id=None):
        stored = self._user(user_id).get("settings", {})
        return {key: stored.get(key) for key in NUTRITION_SETTING_KEYS}

    def validate_settings(
        self,
        protein_goal=None,
        calorie_goal=None,
        basal_metabolism=None,
        activity_level=None,
    ):
        values = {
            "protein_goal": self.validate_number(
                protein_goal, "目標タンパク質"
            ),
            "calorie_goal": self.validate_number(calorie_goal, "目標カロリー"),
            "basal_metabolism": self.validate_number(
                basal_metabolism, "基礎代謝"
            ),
            "activity_level": activity_level or None,
        }
        if (
            values["activity_level"] is not None
            and values["activity_level"] not in ACTIVITY_FACTORS
        ):
            raise ValueError("活動量を選択してください。")
        return values

    def save_settings(
        self,
        protein_goal=None,
        calorie_goal=None,
        basal_metabolism=None,
        activity_level=None,
        user_id=None,
    ):
        values = self.validate_settings(
            protein_goal,
            calorie_goal,
            basal_metabolism,
            activity_level,
        )
        user = self._user(user_id)
        settings = user.setdefault("settings", {})
        for key, value in values.items():
            if value is None:
                settings.pop(key, None)
            else:
                settings[key] = value
        if not settings:
            user.pop("settings")
        self._data_manager.save()
        return values

    def estimated_daily_expenditure(self, user_id=None):
        settings = self.get_settings(user_id)
        return calculate_daily_expenditure(
            settings["basal_metabolism"],
            settings["activity_level"],
        )

    @staticmethod
    def validate_number(value, label):
        if value is None or str(value).strip() == "":
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label}は0より大きい数値で入力してください。") from error
        if numeric <= 0 or not numeric.is_integer():
            raise ValueError(f"{label}は0より大きい整数で入力してください。")
        return int(numeric)


from core.data import data  # noqa: E402  (created after DataManager is defined)


nutrition_settings = NutritionSettingsManager(data)
