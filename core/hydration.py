"""User-scoped hydration records for Habitory Ver3."""

from __future__ import annotations

from datetime import datetime

from core.clock import today_jst_string


class HydrationManager:
    def __init__(self, data_manager):
        self._data_manager = data_manager

    def _user(self, user_id=None):
        return self._data_manager.users.get_user(
            user_id or self._data_manager.active_user_id
        )

    def get_records(self, user_id=None):
        records = self._user(user_id).get("hydration_records", [])
        return sorted(records, key=lambda record: record["date"])

    def get_amount(self, record_date=None, user_id=None):
        record_date = record_date or today_jst_string()
        self._validate_date(record_date)
        record = next(
            (
                item
                for item in self.get_records(user_id)
                if item.get("date") == record_date
            ),
            None,
        )
        return int(record.get("amount", 0)) if record else 0

    def add(self, amount, record_date=None, user_id=None):
        amount = self._validate_amount(amount)
        record_date = record_date or today_jst_string()
        self._validate_date(record_date)

        # Resolve the owner once so another tab switching users cannot redirect
        # this write.
        owner_id = user_id or self._data_manager.active_user_id
        user = self._user(owner_id)
        records = user.setdefault("hydration_records", [])
        record = next(
            (item for item in records if item.get("date") == record_date),
            None,
        )
        if record is None:
            record = {"date": record_date, "amount": 0, "entries": []}
            records.append(record)
        record["amount"] = int(record.get("amount", 0)) + amount
        record.setdefault("entries", []).append(amount)
        records.sort(key=lambda item: item["date"])
        self._data_manager.save()
        return record

    def undo_last(self, record_date=None, user_id=None):
        record_date = record_date or today_jst_string()
        self._validate_date(record_date)
        user = self._user(user_id)
        records = user.get("hydration_records", [])
        record = next(
            (item for item in records if item.get("date") == record_date),
            None,
        )
        if record is None or not record.get("entries"):
            raise ValueError("取り消せる直前の水分記録がありません。")

        amount = int(record["entries"].pop())
        record["amount"] = max(0, int(record.get("amount", 0)) - amount)
        if record["amount"] == 0:
            records.remove(record)
        self._data_manager.save()
        return amount

    def get_goal(self, user_id=None):
        goal = self._user(user_id).get("settings", {}).get("hydration_goal_ml")
        return int(goal) if goal is not None else None

    def set_goal(self, amount, user_id=None):
        user = self._user(user_id)
        goal = self.validate_goal(amount)
        if goal is None:
            settings = user.get("settings")
            if settings:
                settings.pop("hydration_goal_ml", None)
                if not settings:
                    user.pop("settings")
            self._data_manager.save()
            return None

        user.setdefault("settings", {})["hydration_goal_ml"] = goal
        self._data_manager.save()
        return goal

    @classmethod
    def validate_goal(cls, amount):
        if amount is None or str(amount).strip() == "":
            return None
        return cls._validate_amount(amount)

    def summary(self, record_date=None, user_id=None):
        amount = self.get_amount(record_date, user_id)
        goal = self.get_goal(user_id)
        percentage = round(amount / goal * 100) if goal else None
        return {"amount": amount, "goal": goal, "percentage": percentage}

    @staticmethod
    def _validate_date(record_date):
        try:
            datetime.strptime(record_date, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError("記録日は YYYY-MM-DD 形式で指定してください。") from error

    @staticmethod
    def _validate_amount(amount):
        try:
            numeric = float(amount)
        except (TypeError, ValueError) as error:
            raise ValueError("水分量を1ml以上で入力してください。") from error
        if not numeric.is_integer():
            raise ValueError("水分量は整数で入力してください。")
        amount = int(numeric)
        if amount <= 0:
            raise ValueError("水分量を1ml以上で入力してください。")
        return amount


from core.data import data  # noqa: E402  (created after DataManager is defined)


hydration = HydrationManager(data)
