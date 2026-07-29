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

    def update_food(self, food_id, name, calories, protein, user_id=None):
        name = str(name).strip()
        if not name:
            raise ValueError("食品名を入力してください。")
        calories = self._non_negative_number(calories, "カロリー")
        protein = self._non_negative_number(protein, "タンパク質")
        if calories == 0 and protein == 0:
            raise ValueError("カロリーまたはタンパク質を入力してください。")

        foods = self._user(user_id).get("foods", [])
        food = next((item for item in foods if item.get("id") == food_id), None)
        if food is None:
            raise ValueError("選択された食品が見つかりません。")
        if any(
            item.get("id") != food_id and item.get("name") == name
            for item in foods
        ):
            raise ValueError("同じ食品名が既に登録されています。")
        food.update({"name": name, "calories": calories, "protein": protein})
        self._data_manager.save()
        return food

    def delete_food(self, food_id, user_id=None):
        foods = self._user(user_id).get("foods", [])
        food = next((item for item in foods if item.get("id") == food_id), None)
        if food is None:
            raise ValueError("選択された食品が見つかりません。")
        foods.remove(food)
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
        return self.add_meals(record_date, [food_id], amount, user_id)[0]

    def add_meals(
        self, record_date, food_ids, amount=1, user_id=None, meal_period="その他"
    ):
        self._validate_date(record_date)
        amount = self._positive_number(amount, "量")
        meal_period = self._validate_meal_period(meal_period)
        food_ids = list(dict.fromkeys(food_ids or []))
        if not food_ids:
            raise ValueError("食品を1つ以上選択してください。")

        owner_id = user_id or self._data_manager.active_user_id
        user = self._user(owner_id)
        foods_by_id = {
            item.get("id"): item for item in user.get("foods", [])
        }
        if any(food_id not in foods_by_id for food_id in food_ids):
            raise ValueError("選択された食品が見つかりません。")

        created = []
        for food_id in food_ids:
            food = foods_by_id[food_id]
            created.append(
                {
                    "id": uuid4().hex,
                    "date": record_date,
                    "food_id": food["id"],
                    "food_name": food["name"],
                    "meal_period": meal_period,
                    "amount": amount,
                    "calories": self._clean_number(food["calories"] * amount),
                    "protein": self._clean_number(food["protein"] * amount),
                }
            )
        user.setdefault("meal_records", []).extend(created)
        user["meal_records"].sort(key=lambda item: item["date"])
        self._data_manager.save()
        return created

    def add_manual_meal(
        self, record_date, calories, protein, name="手入力", user_id=None,
        meal_period="その他",
    ):
        """Save nutrition totals without requiring a registered food."""
        self._validate_date(record_date)
        name = str(name or "手入力").strip() or "手入力"
        calories = self._non_negative_number(calories, "カロリー")
        protein = self._non_negative_number(protein, "タンパク質")
        meal_period = self._validate_meal_period(meal_period)
        if calories == 0 and protein == 0:
            raise ValueError("カロリーまたはタンパク質を入力してください。")

        record = {
            "id": uuid4().hex,
            "date": record_date,
            "food_id": None,
            "food_name": name,
            "meal_period": meal_period,
            "amount": 1,
            "calories": calories,
            "protein": protein,
        }
        user = self._user(user_id)
        user.setdefault("meal_records", []).append(record)
        user["meal_records"].sort(key=lambda item: item["date"])
        self._data_manager.save()
        return record

    @staticmethod
    def _validate_meal_period(value):
        value = str(value or "その他")
        if value not in {"朝", "昼", "夜", "その他"}:
            raise ValueError("食事の時間帯を選択してください。")
        return value

    def delete_meal(self, meal_id, user_id=None):
        records = self._user(user_id).get("meal_records", [])
        record = next(
            (item for item in records if item.get("id") == meal_id),
            None,
        )
        if record is None:
            raise ValueError("選択された食事記録が見つかりません。")
        records.remove(record)
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

    def period_summary(self, start_date, end_date, user_id=None):
        self._validate_date(start_date)
        self._validate_date(end_date)
        if start_date > end_date:
            raise ValueError("集計期間の開始日と終了日が正しくありません。")
        records = [
            record
            for record in self.get_meal_records(user_id=user_id)
            if start_date <= record.get("date", "") <= end_date
        ]
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        return {
            "start_date": start_date,
            "end_date": end_date,
            "days": (end - start).days + 1,
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
