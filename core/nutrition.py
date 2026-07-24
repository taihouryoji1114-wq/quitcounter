"""User-scoped food master and meal records for Habitory Ver3."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4


class NutritionManager:
    def __init__(self, data_manager):
        self._data_manager = data_manager

    def _user(self, user_id=None):
        return self._data_manager.users.get_user(
            user_id or self._data_manager.active_user_id
        )

    def get_foods(self, user_id=None):
        return list(self._user(user_id).get("foods", []))

    def add_food(self, name, calories, protein, user_id=None):
        name = str(name).strip()
        if not name:
            raise ValueError("食品名を入力してください。")
        calories = self._non_negative_number(calories, "カロリー")
        protein = self._non_negative_number(protein, "タンパク質")
        if calories == 0 and protein == 0:
            raise ValueError("カロリーまたはタンパク質を入力してください。")

        user = self._user(user_id)
        foods = user.setdefault("foods", [])
        if any(food.get("name") == name for food in foods):
            raise ValueError("同じ食品名が既に登録されています。")
        food = {
            "id": uuid4().hex,
            "name": name,
            "calories": calories,
            "protein": protein,
        }
        foods.append(food)
        self._data_manager.save()
        return food

    def get_meal_records(self, record_date=None, user_id=None):
        records = self._user(user_id).get("meal_records", [])
        if record_date is not None:
            self._validate_date(record_date)
            records = [
                record for record in records if record.get("date") == record_date
            ]
        return list(records)

    def add_meal(self, record_date, food_id, amount, user_id=None):
        self._validate_date(record_date)
        amount = self._positive_number(amount, "量")

        # Resolve the owner once so a user switch in another tab cannot redirect
        # the food lookup or the resulting meal record.
        owner_id = user_id or self._data_manager.active_user_id
        user = self._user(owner_id)
        food = next(
            (item for item in user.get("foods", []) if item.get("id") == food_id),
            None,
        )
        if food is None:
            raise ValueError("選択された食品が見つかりません。")

        record = {
            "id": uuid4().hex,
            "date": record_date,
            "food_id": food["id"],
            "food_name": food["name"],
            "amount": amount,
            "calories": self._clean_number(food["calories"] * amount),
            "protein": self._clean_number(food["protein"] * amount),
        }
        user.setdefault("meal_records", []).append(record)
        user["meal_records"].sort(key=lambda item: item["date"])
        self._data_manager.save()
        return record

    def daily_summary(self, record_date=None, user_id=None):
        record_date = record_date or date.today().isoformat()
        records = self.get_meal_records(record_date, user_id)
        return {
            "date": record_date,
            "calories": self._clean_number(
                sum(float(record.get("calories", 0)) for record in records)
            ),
            "protein": self._clean_number(
                sum(float(record.get("protein", 0)) for record in records)
            ),
        }

    @staticmethod
    def _validate_date(record_date):
        try:
            datetime.strptime(record_date, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError("記録日は YYYY-MM-DD 形式で指定してください。") from error

    @classmethod
    def _non_negative_number(cls, value, label):
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label}は0以上の数値で入力してください。") from error
        if number < 0:
            raise ValueError(f"{label}は0以上の数値で入力してください。")
        return cls._clean_number(number)

    @classmethod
    def _positive_number(cls, value, label):
        number = cls._non_negative_number(value, label)
        if number <= 0:
            raise ValueError(f"{label}は0より大きい数値で入力してください。")
        return number

    @staticmethod
    def _clean_number(value):
        value = round(float(value), 2)
        return int(value) if value.is_integer() else value


from core.data import data  # noqa: E402  (created after DataManager is defined)


nutrition = NutritionManager(data)
