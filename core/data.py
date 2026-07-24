"""JSON-backed domain data for Habitory Ver2.0."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parent.parent / "data.json"
BODY_PARTS = ("胸", "背中", "脚", "肩", "腕", "腹筋")


class DataManager:
    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path else DATA_FILE
        self.data = self._migrate(self._load())

    @staticmethod
    def _default():
        return {
            "users": {
                "active_id": "ryoji",
                "profiles": {
                    "ryoji": {"name": "良治"},
                    "koka": {"name": "胡花"},
                },
            },
            "smoking": {
                "ryoji": {
                    "start_date": "2026-07-12",
                    "cigarettes_per_day": 10,
                    "price_per_pack": 600,
                },
                "koka": {
                    "start_date": "2026-07-01",
                    "cigarettes_per_day": 10,
                    "price_per_pack": 600,
                }
            },
            "workout_records": [],
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

    def _migrate(self, source):
        """Map the prototype schema without discarding any profile or workout data."""
        if isinstance(source.get("users"), dict) and isinstance(source.get("smoking"), dict):
            source.setdefault("workout_records", [])
            self._ensure_two_users(source)
            return source

        # Keep unknown keys and the former `workout` key. The latter is retained as
        # a rollback-friendly compatibility copy while `workout_records` is canonical.
        migrated = {key: value for key, value in source.items() if key not in {"current_user", "users"}}
        profiles, smoking = {}, {}
        legacy_users = source.get("users", [])
        if isinstance(legacy_users, list):
            for index, legacy in enumerate(legacy_users):
                if not isinstance(legacy, dict):
                    continue
                user_id = ("ryoji", "koka")[index] if index < 2 else str(index)
                profiles[user_id] = {"name": legacy.get("name", "ユーザー")}
                smoking[user_id] = {
                    "start_date": legacy.get("start_date", date_string_today()),
                    "cigarettes_per_day": legacy.get("cigarettes_per_day", 0),
                    "price_per_pack": legacy.get("price_per_pack", 0),
                }
        if not profiles:
            return self._default()

        active_index = source.get("current_user", 0)
        active_id = ("ryoji", "koka")[active_index] if isinstance(active_index, int) and active_index < 2 else str(active_index)
        if active_id not in profiles:
            active_id = next(iter(profiles))
        migrated["users"] = {"active_id": active_id, "profiles": profiles}
        migrated["smoking"] = smoking
        migrated["workout_records"] = self._normalise_workouts(source)
        self._ensure_two_users(migrated)
        return migrated

    @staticmethod
    def _ensure_two_users(source):
        """Guarantee the two Ver1 profiles while retaining every existing profile."""
        users = source["users"]
        profiles = users.setdefault("profiles", {})
        smoking = source.setdefault("smoking", {})
        defaults = DataManager._default()
        # Early Ver2 builds used numeric IDs. Promote them to stable IDs so the
        # selector consistently shows the intended two people, without losing data.
        for legacy_id, user_id in (("0", "ryoji"), ("1", "koka")):
            if legacy_id in profiles and user_id not in profiles:
                profiles[user_id] = profiles.pop(legacy_id)
                if legacy_id in smoking:
                    smoking[user_id] = smoking.pop(legacy_id)
                if users.get("active_id") == legacy_id:
                    users["active_id"] = user_id
        for user_id in ("ryoji", "koka"):
            profiles.setdefault(user_id, defaults["users"]["profiles"][user_id])
            smoking.setdefault(user_id, defaults["smoking"][user_id])
        if users.get("active_id") not in profiles:
            users["active_id"] = "ryoji"

    def save(self):
        """Atomically preserve JSON if a save is interrupted."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_name = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(prefix="habitory-", suffix=".json", dir=self.file_path.parent)
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(self.data, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_name, self.file_path)
        except OSError as error:
            if temporary_name:
                Path(temporary_name).unlink(missing_ok=True)
            raise RuntimeError(f"data.jsonを保存できません: {error}") from error

    @property
    def active_user_id(self):
        return self.data["users"]["active_id"]

    def get_profile(self):
        return self.data["users"]["profiles"][self.active_user_id]

    def get_users(self):
        return self.data["users"]["profiles"]

    def select_user(self, user_id):
        if user_id not in self.get_users():
            raise ValueError("選択されたユーザーが見つかりません。")
        self.data["users"]["active_id"] = user_id
        self.save()

    def get_smoking(self):
        return self.data["smoking"][self.active_user_id]

    def update_profile(self, name, start_date, cigarettes_per_day, price_per_pack):
        datetime.strptime(start_date, "%Y-%m-%d")
        if not str(name).strip():
            raise ValueError("名前を入力してください。")
        if cigarettes_per_day < 0 or price_per_pack < 0:
            raise ValueError("本数と価格は0以上で入力してください。")
        self.get_profile()["name"] = str(name).strip()
        self.data["smoking"][self.active_user_id] = {
            "start_date": start_date,
            "cigarettes_per_day": int(cigarettes_per_day),
            "price_per_pack": int(price_per_pack),
        }
        self.save()

    def _normalise_workouts(self, source=None):
        source = source if source is not None else self.data
        by_date = {}
        default_user_id = source.get("users", {}).get("active_id", "ryoji") if isinstance(source.get("users"), dict) else "ryoji"

        def add(record, parts_key):
            if not isinstance(record, dict) or not isinstance(record.get("date"), str):
                return
            parts = record.get(parts_key, [])
            if not isinstance(parts, list):
                return
            valid_parts = [part for part in parts if part in BODY_PARTS]
            if not valid_parts:
                return
            user_id = record.get("user_id", default_user_id)
            user_id = {"0": "ryoji", "1": "koka"}.get(user_id, user_id)
            item = by_date.setdefault((user_id, record["date"]), {"user_id": user_id, "date": record["date"], "body_parts": []})
            if parts_key == "body_parts":
                item.update({key: value for key, value in record.items() if key != "body_parts"})
            for part in valid_parts:
                if part not in item["body_parts"]:
                    item["body_parts"].append(part)

        for record in source.get("workout_records", []):
            add(record, "body_parts")
        # Ver1 prototype compatibility
        for record in source.get("workout", []):
            add(record, "parts")
        return sorted(by_date.values(), key=lambda item: (item["user_id"], item["date"]))

    def get_workout_records(self, user_id=None):
        user_id = user_id or self.active_user_id
        return [record for record in self._normalise_workouts() if record["user_id"] == user_id]

    def get_workout_for_date(self, record_date):
        return next((record for record in self.get_workout_records() if record["date"] == record_date), None)

    def save_workout(self, record_date, body_parts):
        try:
            datetime.strptime(record_date, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError("記録日は YYYY-MM-DD 形式で指定してください。") from error
        selected = []
        for part in body_parts:
            if part not in BODY_PARTS:
                raise ValueError("未対応の部位が含まれています。")
            if part not in selected:
                selected.append(part)
        if not selected:
            raise ValueError("部位を1つ以上選択してください。")

        records = self._normalise_workouts()
        record = next((item for item in records if item["date"] == record_date and item["user_id"] == self.active_user_id), None)
        if record is None:
            record = {"user_id": self.active_user_id, "date": record_date, "body_parts": []}
            records.append(record)
        record["body_parts"] = selected
        self.data["workout_records"] = sorted(records, key=lambda item: item["date"])
        self.save()
        return record


def date_string_today():
    return datetime.now().date().isoformat()


data = DataManager()
