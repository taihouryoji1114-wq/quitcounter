"""User management for Habitory Ver3."""

from __future__ import annotations

import re
from copy import deepcopy


STANDARD_FOODS = [
    {"id": "standard-protein", "name": "プロテイン", "calories": 140, "protein": 25},
    {"id": "standard-egg-50g", "name": "卵（1個・50g）", "calories": 71, "protein": 6.1},
    {"id": "standard-natto-50g", "name": "納豆（1パック・50g）", "calories": 92, "protein": 8.25},
    {"id": "standard-salmon-50g", "name": "サーモン（しろさけ・50g）", "calories": 62, "protein": 11.15},
    {"id": "standard-tuna-50g", "name": "マグロ赤身（50g）", "calories": 57.5, "protein": 13.2},
    {"id": "standard-chicken-50g", "name": "鶏むね肉・皮なし（50g）", "calories": 52.5, "protein": 11.65},
    {"id": "standard-rice-50g", "name": "ライス・炊飯後（50g）", "calories": 78, "protein": 1.25},
]


DEFAULT_USERS = {
    "user1": {
        "profile": {"name": "良治"},
        "smoking": {
            "start_date": "2026-07-12",
            "cigarettes_per_day": 10,
            "price_per_pack": 600,
        },
        "workout_records": [],
        "foods": deepcopy(STANDARD_FOODS),
        "standard_foods_seeded": True,
    },
    "user2": {
        "profile": {"name": "胡花"},
        "smoking": {
            "start_date": "2026-07-01",
            "cigarettes_per_day": 10,
            "price_per_pack": 600,
        },
        "workout_records": [],
        "foods": deepcopy(STANDARD_FOODS),
        "standard_foods_seeded": True,
    },
}


class UserManager:
    """Small API around the user-owned portion of a DataManager."""

    def __init__(self, data_manager):
        self._data_manager = data_manager

    @property
    def current_user_id(self):
        return self._data_manager.data["current_user_id"]

    def get_current_user(self):
        return self._data_manager.data["users"][self.current_user_id]

    def get_user(self, user_id):
        try:
            return self._data_manager.data["users"][user_id]
        except KeyError as error:
            raise ValueError("選択されたユーザーが見つかりません。") from error

    def get_users(self):
        return self._data_manager.data["users"]

    def switch_user(self, user_id):
        self.get_user(user_id)
        self._data_manager.data["current_user_id"] = user_id
        self._data_manager.save()

    def add_user(self, user_id, name, smoking=None):
        """Add a user without changing the current user.

        This is intentionally UI-independent so a future settings screen can use it.
        """
        user_id = str(user_id).strip()
        name = str(name).strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", user_id):
            raise ValueError("ユーザーIDは半角英小文字・数字・_・-で指定してください。")
        if not name:
            raise ValueError("名前を入力してください。")
        if user_id in self.get_users():
            raise ValueError("同じユーザーIDが既に存在します。")

        defaults = {
            "start_date": self._data_manager.date_string_today(),
            "cigarettes_per_day": 0,
            "price_per_pack": 0,
        }
        if smoking is not None:
            if not isinstance(smoking, dict):
                raise ValueError("禁煙設定の形式が正しくありません。")
            defaults.update(deepcopy(smoking))
        self._data_manager.validate_smoking(defaults)
        self._data_manager.data["users"][user_id] = {
            "profile": {"name": name},
            "smoking": defaults,
            "workout_records": [],
        }
        self._data_manager.save()
        return self._data_manager.data["users"][user_id]
