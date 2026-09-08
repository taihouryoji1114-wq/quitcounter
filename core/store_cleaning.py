"""Configurable, one-tap cleaning checks for store operations."""

from datetime import datetime
from uuid import uuid4

from core.data import data


class StoreCleaningManager:
    DEFAULTS = (
        ("厨房", "作業台を拭く"),
        ("厨房", "床を清掃する"),
        ("ホール", "テーブルを拭く"),
        ("ホール", "床を清掃する"),
        ("トイレ", "便器・洗面台を清掃する"),
    )

    def __init__(self, data_manager=None):
        self._data = data_manager or data

    def templates(self, active_only=True):
        values = self._data.data.get("store_cleaning_templates")
        if not isinstance(values, list) or not values:
            values = [
                {"id": uuid4().hex, "area": area, "name": name,
                 "sort_order": index, "active": True}
                for index, (area, name) in enumerate(self.DEFAULTS)
            ]
            self._data.data["store_cleaning_templates"] = values
            self._data.save()
        result = [dict(value) for value in values if isinstance(value, dict)]
        if active_only:
            result = [value for value in result if value.get("active", True)]
        return sorted(result, key=lambda value: int(value.get("sort_order", 999999)))

    def items(self, record_date):
        self._validate_date(record_date)
        states = self._data.data.get("store_cleaning_records", {}).get(record_date, {})
        return [{**item, **dict(states.get(item["id"], {})),
                 "done": bool(states.get(item["id"], {}).get("done", False))}
                for item in self.templates()]

    def toggle(self, record_date, item_id):
        self._validate_date(record_date)
        if not any(value["id"] == item_id for value in self.templates()):
            raise ValueError("清掃項目が見つかりません。")
        records = self._data.data.setdefault("store_cleaning_records", {}).setdefault(
            record_date, {})
        done = not bool(records.get(item_id, {}).get("done", False))
        records[item_id] = {
            "done": done,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "updated_by": "staff",
        }
        self._data.save()
        return done

    def save_template(self, name, area, item_id=None):
        name, area = str(name or "").strip(), str(area or "").strip()
        if not name or not area:
            raise ValueError("場所と清掃項目を入力してください。")
        values = self._data.data.setdefault("store_cleaning_templates", [])
        if item_id:
            target = next((value for value in values if value.get("id") == item_id), None)
            if not target:
                raise ValueError("清掃項目が見つかりません。")
            target.update(name=name[:40], area=area[:20])
        else:
            values.append({"id": uuid4().hex, "name": name[:40], "area": area[:20],
                           "sort_order": len(values), "active": True})
        self._data.save()

    def delete_template(self, item_id):
        target = next((value for value in self._data.data.setdefault(
            "store_cleaning_templates", []) if value.get("id") == item_id), None)
        if not target:
            raise ValueError("清掃項目が見つかりません。")
        target["active"] = False
        self._data.save()

    def move_template(self, item_id, direction):
        items = self.templates()
        index = next((i for i, value in enumerate(items) if value["id"] == item_id), None)
        target = index + direction if index is not None else -1
        if index is None or not 0 <= target < len(items):
            return False
        items[index]["sort_order"], items[target]["sort_order"] = (
            items[target].get("sort_order", target), items[index].get("sort_order", index))
        by_id = {value["id"]: value for value in items}
        for value in self._data.data.get("store_cleaning_templates", []):
            if value.get("id") in by_id:
                value["sort_order"] = by_id[value["id"]]["sort_order"]
        self._data.save()
        return True

    @staticmethod
    def _validate_date(value):
        datetime.strptime(str(value), "%Y-%m-%d")


store_cleaning = StoreCleaningManager()
