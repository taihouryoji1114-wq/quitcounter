"""Shared store operations: shortage detection, ordering, and hygiene records."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from core.data import data


class StoreOperationsManager:
    STATUSES = {"enough", "low", "out"}
    TEMPERATURE_LOCATIONS = (
        "デシャップ冷蔵庫1", "デシャップ冷蔵庫2", "デシャップ冷蔵庫3",
        "厨房冷蔵庫1", "厨房冷蔵庫2", "厨房冷蔵庫3", "厨房冷蔵庫4", "厨房冷蔵庫5",
        "デシャップ冷凍庫", "厨房冷凍庫", "外冷凍庫",
    )

    def __init__(self, data_manager=None):
        self._data_manager = data_manager or data

    def items(self, active_only=True):
        values = self._data_manager.data.get("store_inventory_items", [])
        items = [dict(value) for value in values if isinstance(value, dict)]
        if active_only:
            items = [value for value in items if value.get("active", True)]
        return sorted(items, key=lambda value: (value.get("category", ""), value.get("name", "")))

    def add_item(self, name, category="食材", unit="個", supplier="", required_stock=""):
        name = str(name or "").strip()
        if not name:
            raise ValueError("商品名を入力してください。")
        if any(value["name"] == name for value in self.items()):
            raise ValueError("同じ名前の商品が登録されています。")
        item = {
            "id": uuid4().hex, "name": name, "category": str(category or "その他").strip(),
            "unit": str(unit or "個").strip(), "supplier": str(supplier or "").strip(),
            "required_stock": str(required_stock or "").strip(), "status": "enough",
            "active": True, "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._data_manager.data.setdefault("store_inventory_items", []).append(item)
        self._data_manager.save()
        return dict(item)

    def set_status(self, item_id, status):
        if status not in self.STATUSES:
            raise ValueError("在庫状態が正しくありません。")
        item = self._find(item_id)
        item["status"] = status
        item["updated_at"] = datetime.now().isoformat(timespec="seconds")
        if status == "enough":
            self._data_manager.data.setdefault("store_active_orders", {}).pop(item_id, None)
        self._event("status", item, status=status)
        self._data_manager.save()
        return dict(item)

    def order_list(self):
        active_orders = self._data_manager.data.get("store_active_orders", {})
        result = []
        for item in self.items():
            order = active_orders.get(item["id"], {}) if isinstance(active_orders, dict) else {}
            if item["status"] not in {"low", "out"} and not order:
                continue
            result.append({**item, "order_state": order.get("state", "needed"),
                           "ordered_at": order.get("ordered_at", "")})
        return sorted(result, key=lambda value: (
            0 if value["status"] == "out" else 1,
            0 if value["order_state"] == "needed" else 1,
            value["supplier"], value["name"],
        ))

    def mark_ordered(self, item_id):
        item = self._find(item_id)
        if item["status"] == "enough":
            raise ValueError("在庫ありの商品は発注できません。")
        now = datetime.now().isoformat(timespec="seconds")
        self._data_manager.data.setdefault("store_active_orders", {})[item_id] = {
            "state": "ordered", "ordered_at": now,
        }
        self._event("ordered", item)
        self._data_manager.save()

    def receive(self, item_id):
        item = self._find(item_id)
        item["status"] = "enough"
        item["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._data_manager.data.setdefault("store_active_orders", {}).pop(item_id, None)
        self._event("received", item)
        self._data_manager.save()

    def hygiene_record(self, record_date):
        self._date(record_date)
        stored = self._data_manager.data.get("store_hygiene_records", {}).get(record_date, {})
        temperatures = stored.get("temperatures", {}) if isinstance(stored, dict) else {}
        checks = stored.get("checks", {}) if isinstance(stored, dict) else {}
        return {
            "temperatures": {name: temperatures.get(name) for name in self.TEMPERATURE_LOCATIONS},
            "checks": {key: bool(checks.get(key, False)) for key in
                       ("receiving", "equipment", "toilet", "handwash")},
            "note": str(stored.get("note", "") if isinstance(stored, dict) else ""),
        }

    def save_hygiene(self, record_date, temperatures, checks, note=""):
        self._date(record_date)
        cleaned_temperatures = {}
        for name in self.TEMPERATURE_LOCATIONS:
            value = temperatures.get(name)
            if value in (None, ""):
                cleaned_temperatures[name] = None
                continue
            try:
                number = float(value)
            except (TypeError, ValueError) as error:
                raise ValueError("温度は数字で入力してください。") from error
            if number < -100 or number > 100:
                raise ValueError("温度は-100〜100℃で入力してください。")
            cleaned_temperatures[name] = round(number, 1)
        cleaned_checks = {key: bool(checks.get(key, False)) for key in
                          ("receiving", "equipment", "toilet", "handwash")}
        record = {"temperatures": cleaned_temperatures, "checks": cleaned_checks,
                  "note": str(note or "").strip()[:500],
                  "updated_at": datetime.now().isoformat(timespec="seconds")}
        self._data_manager.data.setdefault("store_hygiene_records", {})[record_date] = record
        self._data_manager.save()
        return record

    def hygiene_complete(self, record_date):
        record = self.hygiene_record(record_date)
        return (all(value is not None for value in record["temperatures"].values())
                and all(record["checks"].values()))

    def _find(self, item_id):
        for item in self._data_manager.data.setdefault("store_inventory_items", []):
            if isinstance(item, dict) and item.get("id") == item_id and item.get("active", True):
                return item
        raise ValueError("商品が見つかりません。")

    def _event(self, event_type, item, **extra):
        self._data_manager.data.setdefault("store_inventory_events", []).append({
            "type": event_type, "item_id": item["id"], "item_name": item["name"],
            "at": datetime.now().isoformat(timespec="seconds"), **extra,
        })

    @staticmethod
    def _date(value):
        try:
            return datetime.strptime(str(value), "%Y-%m-%d")
        except ValueError as error:
            raise ValueError("日付が正しくありません。") from error


store_ops = StoreOperationsManager()
