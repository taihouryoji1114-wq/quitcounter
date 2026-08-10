"""JSON-backed domain data for Habitory Ver3."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from core.users import DEFAULT_USERS, STANDARD_FOODS, UserManager


DEFAULT_DATA_FILE = Path(__file__).resolve().parent.parent / "data.json"
DATA_FILE = Path(os.environ.get("HABITORY_DATA_FILE", DEFAULT_DATA_FILE))
BODY_PARTS = ("胸", "背中", "脚", "肩", "腕", "腹筋")
SCHEMA_VERSION = 3
MAX_AUTOMATIC_BACKUPS = 20


class DataManager:
    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path else DATA_FILE
        source = self._load()
        self.data, migrated = self._migrate(source)
        self.users = UserManager(self)
        if migrated:
            self._backup_before_migration()
            self.save()

    @staticmethod
    def _default():
        return {
            "schema_version": SCHEMA_VERSION,
            "current_user_id": "user1",
            "users": deepcopy(DEFAULT_USERS),
        }

    def _load(self):
        if not self.file_path.exists():
            return self._default()
        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                value = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"data.jsonを読み込めません: {error}") from error
        if not isinstance(value, dict):
            raise RuntimeError("data.jsonの形式が正しくありません。既存データは変更していません。")
        return value

    @staticmethod
    def _is_ver3(source):
        if source.get("schema_version") != SCHEMA_VERSION:
            return False
        users = source.get("users")
        return isinstance(users, dict) and all(
            isinstance(value, dict)
            and isinstance(value.get("profile"), dict)
            and isinstance(value.get("smoking"), dict)
            and isinstance(value.get("workout_records"), list)
            for value in users.values()
        )

    def _migrate(self, source):
        """Return the Ver3 model while preserving unknown root data."""
        if self._is_ver3(source):
            result = deepcopy(source)
            self._ensure_required_users(result)
            # Replace only untouched placeholder names. User-edited names are preserved.
            placeholder_names = {"user1": "ユーザー1", "user2": "ユーザー2"}
            for user_id, placeholder in placeholder_names.items():
                user = result.get("users", {}).get(user_id)
                if user and user.get("profile", {}).get("name") == placeholder:
                    user["profile"]["name"] = DEFAULT_USERS[user_id]["profile"]["name"]
            for user in result.get("users", {}).values():
                if not user.get("standard_foods_seeded"):
                    foods = user.setdefault("foods", [])
                    existing_names = {food.get("name") for food in foods}
                    foods.extend(
                        deepcopy(food)
                        for food in STANDARD_FOODS
                        if food["name"] not in existing_names
                    )
                    user["standard_foods_seeded"] = True
            return result, result != source

        # Unknown application data remains at root. Replaced Ver2 containers are
        # preserved in the byte-for-byte backup made before this result is saved.
        result = {
            key: deepcopy(value)
            for key, value in source.items()
            if key not in {"schema_version", "current_user", "current_user_id", "users", "smoking", "workout_records"}
        }
        result["schema_version"] = SCHEMA_VERSION

        profiles = {}
        legacy_users = source.get("users", {})
        if isinstance(legacy_users, dict):
            if isinstance(legacy_users.get("profiles"), dict):
                profiles = legacy_users["profiles"]
            active = legacy_users.get("active_id", source.get("current_user_id", source.get("current_user", 0)))
        elif isinstance(legacy_users, list):
            profiles = {
                str(index): user for index, user in enumerate(legacy_users) if isinstance(user, dict)
            }
            active = source.get("current_user", 0)
        else:
            active = source.get("current_user_id", source.get("current_user", 0))

        id_map = {"0": "user1", "1": "user2", 0: "user1", 1: "user2"}
        active_id = id_map.get(active, str(active))
        smoking_by_user = source.get("smoking", {})
        if not isinstance(smoking_by_user, dict):
            smoking_by_user = {}

        users = {}
        for legacy_id, profile in profiles.items():
            user_id = id_map.get(legacy_id, str(legacy_id))
            if not isinstance(profile, dict):
                continue
            smoking = smoking_by_user.get(legacy_id, smoking_by_user.get(user_id, {}))
            if not isinstance(smoking, dict):
                smoking = {}
            # Very early Ver2 stored smoking fields beside the name.
            smoking = {
                key: deepcopy(smoking.get(key, profile.get(key, DEFAULT_USERS.get(user_id, {}).get("smoking", {}).get(key, default))))
                for key, default in (
                    ("start_date", self.date_string_today()),
                    ("cigarettes_per_day", 0),
                    ("price_per_pack", 0),
                )
            }
            users[user_id] = {
                "profile": {"name": profile.get("name", "ユーザー")},
                "smoking": smoking,
                "workout_records": [],
            }

        if not users:
            users = deepcopy(DEFAULT_USERS)
        result["users"] = users
        self._ensure_required_users(result)
        if active_id not in result["users"]:
            active_id = next(iter(result["users"]))
        result["current_user_id"] = active_id

        for record in self._legacy_workouts(source, active_id):
            owner = record.pop("user_id")
            if owner not in result["users"]:
                result["users"][owner] = {
                    "profile": {"name": owner},
                    "smoking": {
                        "start_date": self.date_string_today(),
                        "cigarettes_per_day": 0,
                        "price_per_pack": 0,
                    },
                    "workout_records": [],
                }
            result["users"][owner]["workout_records"].append(record)
        for user in result["users"].values():
            user["workout_records"].sort(key=lambda item: item["date"])
        return result, True

    @staticmethod
    def _ensure_required_users(source):
        users = source.setdefault("users", {})
        if not users:
            users.update(deepcopy(DEFAULT_USERS))
        if source.get("current_user_id") not in users:
            source["current_user_id"] = next(iter(users))

    def _legacy_workouts(self, source, default_user_id):
        by_user_date = {}

        def add(record, parts_key):
            if not isinstance(record, dict) or not isinstance(record.get("date"), str):
                return
            parts = record.get(parts_key)
            if not isinstance(parts, list):
                return
            valid = list(dict.fromkeys(part for part in parts if part in BODY_PARTS))
            if not valid:
                return
            user_id = {"0": "user1", "1": "user2"}.get(record.get("user_id"), record.get("user_id", default_user_id))
            item = by_user_date.setdefault(
                (user_id, record["date"]),
                {"user_id": user_id, "date": record["date"], "body_parts": []},
            )
            for key, value in record.items():
                if key not in {parts_key, "user_id"}:
                    item[key] = deepcopy(value)
            for part in valid:
                if part not in item["body_parts"]:
                    item["body_parts"].append(part)

        for record in source.get("workout_records", []):
            add(record, "body_parts")
        for record in source.get("workout", []):
            add(record, "parts")
        return [by_user_date[key] for key in sorted(by_user_date)]

    def _backup_before_migration(self):
        if not self.file_path.exists():
            return None
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = self.file_path.with_name(f"{self.file_path.name}.ver2-backup.{timestamp}")
        try:
            with self.file_path.open("rb") as source, backup.open("xb") as destination:
                shutil.copyfileobj(source, destination)
                destination.flush()
                os.fsync(destination.fileno())
        except OSError as error:
            backup.unlink(missing_ok=True)
            raise RuntimeError(f"移行前バックアップを作成できません: {error}") from error
        return backup

    def save(self):
        """Atomically save JSON and sync the containing directory."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_name = None
        try:
            self._create_automatic_backup()
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.file_path.name}.", suffix=".tmp", dir=self.file_path.parent
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(self.data, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_name, self.file_path)
            directory = os.open(self.file_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError as error:
            if temporary_name:
                Path(temporary_name).unlink(missing_ok=True)
            raise RuntimeError(f"data.jsonを保存できません: {error}") from error

    def _create_automatic_backup(self):
        """Keep a local copy of the previous data before it is overwritten."""
        if not self.file_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = self.file_path.with_name(
            f"{self.file_path.name}.backup.{timestamp}"
        )
        with self.file_path.open("rb") as source, backup.open("xb") as destination:
            shutil.copyfileobj(source, destination)
            destination.flush()
            os.fsync(destination.fileno())

        backups = sorted(
            self.file_path.parent.glob(f"{self.file_path.name}.backup.*"),
            key=lambda path: path.name,
            reverse=True,
        )
        for old_backup in backups[MAX_AUTOMATIC_BACKUPS:]:
            old_backup.unlink(missing_ok=True)
        return backup

    @property
    def active_user_id(self):
        return self.users.current_user_id

    def get_current_user(self):
        return self.users.get_current_user()

    def get_profile(self, user_id=None):
        return self.users.get_user(user_id or self.active_user_id)["profile"]

    def get_users(self):
        # Compatibility for the existing, unchanged home screen.
        return {user_id: user["profile"] for user_id, user in self.users.get_users().items()}

    def select_user(self, user_id):
        self.users.switch_user(user_id)

    def add_user(self, user_id, name, smoking=None):
        return self.users.add_user(user_id, name, smoking)

    def get_smoking(self, user_id=None):
        return self.users.get_user(user_id or self.active_user_id)["smoking"]

    @staticmethod
    def date_string_today():
        from core.clock import today_jst_string

        return today_jst_string()

    @staticmethod
    def validate_smoking(smoking):
        try:
            datetime.strptime(smoking["start_date"], "%Y-%m-%d")
            cigarettes = int(smoking["cigarettes_per_day"])
            price = int(smoking["price_per_pack"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("禁煙設定の形式が正しくありません。") from error
        if cigarettes < 0 or price < 0:
            raise ValueError("本数と価格は0以上で入力してください。")

    def update_profile(
        self,
        name,
        start_date,
        cigarettes_per_day,
        price_per_pack,
        user_id=None,
    ):
        name = str(name).strip()
        smoking = {
            "start_date": start_date,
            "cigarettes_per_day": int(cigarettes_per_day),
            "price_per_pack": int(price_per_pack),
        }
        if not name:
            raise ValueError("名前を入力してください。")
        self.validate_smoking(smoking)
        user = self.users.get_user(user_id or self.active_user_id)
        user["profile"]["name"] = name
        user["smoking"] = smoking
        self.save()

    def get_workout_records(self, user_id=None):
        user = self.users.get_user(user_id or self.active_user_id)
        return user["workout_records"]

    def get_workout_for_date(self, record_date, user_id=None):
        return next(
            (
                record
                for record in self.get_workout_records(user_id)
                if record["date"] == record_date
            ),
            None,
        )

    def save_workout(self, record_date, body_parts, user_id=None):
        try:
            datetime.strptime(record_date, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError("記録日は YYYY-MM-DD 形式で指定してください。") from error
        selected = list(dict.fromkeys(body_parts))
        if not selected:
            raise ValueError("部位を1つ以上選択してください。")
        if any(part not in BODY_PARTS for part in selected):
            raise ValueError("未対応の部位が含まれています。")

        # Resolve the owner once. A user switch in another browser tab cannot
        # redirect this write to a different user's records.
        owner_id = user_id or self.active_user_id
        records = self.get_workout_records(owner_id)
        record = next((item for item in records if item["date"] == record_date), None)
        if record is None:
            record = {"date": record_date, "body_parts": []}
            records.append(record)
        record["body_parts"] = selected
        records.sort(key=lambda item: item["date"])
        self.save()

    def delete_workout(self, record_date, user_id=None):
        try:
            datetime.strptime(record_date, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError("記録日は YYYY-MM-DD 形式で指定してください。") from error

        records = self.get_workout_records(user_id)
        record = next(
            (item for item in records if item["date"] == record_date),
            None,
        )
        if record is None:
            raise ValueError("削除する筋トレ記録がありません。")
        records.remove(record)
        self.save()
        return record
data = DataManager()
