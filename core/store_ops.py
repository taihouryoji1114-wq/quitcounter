"""Shared store operations: shortage detection, ordering, and hygiene records."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from core.data import data


class StoreOperationsManager:
    STATUSES = {"enough", "low", "out"}
    PREP_STATUSES = {"incomplete", "done"}
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

    def add_item(self, name, category="食材", unit="個", supplier="", required_stock="",
                 tracking_mode="simple", reorder_point="", current_stock=""):
        name = str(name or "").strip()
        if not name:
            raise ValueError("商品名を入力してください。")
        if any(value["name"] == name for value in self.items()):
            raise ValueError("同じ名前の商品が登録されています。")
        if tracking_mode not in {"simple", "count"}:
            tracking_mode = "simple"
        required_number = self._optional_number(required_stock, "必要在庫数") if tracking_mode == "count" else None
        reorder_number = self._optional_number(reorder_point, "発注ライン") if tracking_mode == "count" else None
        current_number = self._optional_number(current_stock, "現在庫数") if tracking_mode == "count" else None
        if tracking_mode == "count" and required_number is not None and reorder_number is not None:
            if reorder_number > required_number:
                raise ValueError("発注ラインは必要在庫数以下にしてください。")
        item = {
            "id": uuid4().hex, "name": name, "category": str(category or "その他").strip(),
            "unit": str(unit or "個").strip(), "supplier": str(supplier or "").strip(),
            "required_stock": required_number if tracking_mode == "count" else str(required_stock or "").strip(),
            "reorder_point": reorder_number, "current_stock": current_number,
            "tracking_mode": tracking_mode, "status": "enough",
            "active": True, "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        if tracking_mode == "count" and current_number is not None:
            item["status"] = self._status_for_count(current_number, reorder_number)
        self._data_manager.data.setdefault("store_inventory_items", []).append(item)
        self._data_manager.save()
        return dict(item)

    def set_count(self, item_id, count):
        item = self._find(item_id)
        if item.get("tracking_mode") != "count":
            raise ValueError("この商品は個数管理ではありません。")
        number = self._optional_number(count, "現在庫数")
        if number is None:
            raise ValueError("現在庫数を入力してください。")
        item["current_stock"] = number
        item["status"] = self._status_for_count(number, item.get("reorder_point"))
        item["updated_at"] = datetime.now().isoformat(timespec="seconds")
        if item["status"] == "enough":
            self._data_manager.data.setdefault("store_active_orders", {}).pop(item_id, None)
        self._event("count", item, count=number, status=item["status"])
        self._data_manager.save()
        return dict(item)

    def delete_item(self, item_id):
        item = self._find(item_id)
        item["active"] = False
        item["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._data_manager.data.setdefault("store_active_orders", {}).pop(item_id, None)
        self._event("deleted", item)
        self._data_manager.save()

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

    def prep_templates(self):
        values = self._data_manager.data.get("store_prep_templates", [])
        return [dict(value) for value in values if isinstance(value, dict) and value.get("active", True)]

    def add_prep_template(self, name, area="厨房"):
        name = str(name or "").strip()
        if not name:
            raise ValueError("仕込み名を入力してください。")
        if any(value.get("name") == name for value in self.prep_templates()):
            raise ValueError("同じ仕込み項目が登録されています。")
        item = {"id": uuid4().hex, "name": name, "area": str(area or "厨房").strip(),
                "active": True}
        self._data_manager.data.setdefault("store_prep_templates", []).append(item)
        self._data_manager.save()
        return dict(item)

    def delete_prep_template(self, item_id):
        for item in self._data_manager.data.setdefault("store_prep_templates", []):
            if isinstance(item, dict) and item.get("id") == item_id and item.get("active", True):
                item["active"] = False
                self._data_manager.save()
                return
        raise ValueError("仕込み項目が見つかりません。")

    def prep_items(self, record_date):
        day = self._date(record_date)
        states = self._data_manager.data.get("store_prep_records", {}).get(record_date, {})
        previous_date = (day - timedelta(days=1)).strftime("%Y-%m-%d")
        previous_states = self._data_manager.data.get("store_prep_records", {}).get(previous_date, {})
        result = [{**item, "status": ("done" if states.get(item["id"]) == "done" else "incomplete"),
                   "carried_over": previous_states.get(item["id"]) in {"incomplete", "pending", "missed"},
                   "source": "prep"}
                  for item in self.prep_templates()]
        existing_ids = {value["id"] for value in result}
        carried_tasks = self._data_manager.data.get("store_carried_tasks", {}).get(record_date, [])
        for task in carried_tasks:
            if not isinstance(task, dict):
                continue
            carry_id = task.get("id", "")
            if carry_id in existing_ids:
                continue
            result.insert(0, {"id": carry_id, "name": task.get("name", "引き継ぎ"),
                              "area": task.get("area", "厨房"),
                              "status": states.get(carry_id, "incomplete"), "carried_over": True,
                              "source": "handover"})
        return result

    def set_prep_status(self, record_date, item_id, status):
        self._date(record_date)
        if status not in self.PREP_STATUSES:
            raise ValueError("仕込み状況が正しくありません。")
        if not any(value["id"] == item_id for value in self.prep_items(record_date)):
            raise ValueError("仕込み項目が見つかりません。")
        self._data_manager.data.setdefault("store_prep_records", {}).setdefault(record_date, {})[item_id] = status
        self._data_manager.save()

    def handover_templates(self):
        values = self._data_manager.data.get("store_handover_templates", [])
        return [dict(value) for value in values if isinstance(value, dict) and value.get("active", True)]

    def add_handover_template(self, name, area, category=""):
        name = str(name or "").strip()
        area = self._handover_area(area)
        if not name:
            raise ValueError("チェック項目を入力してください。")
        if any(value.get("name") == name and value.get("area") == area
               for value in self.handover_templates()):
            raise ValueError("同じチェック項目が登録されています。")
        category = self._handover_category(area, category)
        item = {"id": uuid4().hex, "name": name, "area": area, "category": category,
                "active": True,
                "created_date": datetime.now().date().isoformat()}
        self._data_manager.data.setdefault("store_handover_templates", []).append(item)
        self._data_manager.save()
        return dict(item)

    def delete_handover_template(self, template_id):
        for item in self._data_manager.data.setdefault("store_handover_templates", []):
            if isinstance(item, dict) and item.get("id") == template_id and item.get("active", True):
                item["active"] = False
                self._data_manager.save()
                return
        raise ValueError("引き継ぎ項目が見つかりません。")

    def handover_checks(self, record_date):
        self._date(record_date)
        states = self._data_manager.data.get("store_handover_checks", {}).get(record_date, {})
        return [{**item, "checked": bool(states.get(item["id"], False))}
                for item in self.handover_templates()]

    def set_handover_check(self, record_date, template_id, checked):
        self._date(record_date)
        if not any(value["id"] == template_id for value in self.handover_templates()):
            raise ValueError("チェック項目が見つかりません。")
        self._data_manager.data.setdefault("store_handover_checks", {}).setdefault(
            record_date, {})[template_id] = bool(checked)
        self._data_manager.save()

    def carry_handover(self, record_date, template_id):
        day = self._date(record_date)
        template = next((value for value in self.handover_templates()
                         if value["id"] == template_id), None)
        if not template:
            raise ValueError("引き継ぎ項目が見つかりません。")
        target_date = (day + timedelta(days=1)).strftime("%Y-%m-%d")
        carry_id = f"handover:{record_date}:{template_id}"
        tasks = self._data_manager.data.setdefault("store_carried_tasks", {}).setdefault(target_date, [])
        if not any(isinstance(value, dict) and value.get("id") == carry_id for value in tasks):
            tasks.append({"id": carry_id, "name": template["name"], "area": template["area"],
                          "category": template.get("category", ""), "from_date": record_date})
            self._data_manager.save()
        return target_date

    def handovers(self, record_date):
        self._date(record_date)
        values = self._data_manager.data.get("store_handovers", {}).get(record_date, [])
        return [dict(value) for value in values if isinstance(value, dict)]

    def add_handover(self, record_date, message, area="厨房", category=""):
        self._date(record_date)
        message = str(message or "").strip()
        if not message:
            raise ValueError("引き継ぎ内容を入力してください。")
        area = self._handover_area(area)
        item = {"id": uuid4().hex, "message": message[:500],
                "area": area, "category": self._handover_category(area, category), "confirmed": False,
                "created_at": datetime.now().isoformat(timespec="minutes")}
        self._data_manager.data.setdefault("store_handovers", {}).setdefault(record_date, []).append(item)
        self._data_manager.save()
        return dict(item)

    def confirm_handover(self, record_date, handover_id):
        for item in self._data_manager.data.setdefault("store_handovers", {}).setdefault(record_date, []):
            if isinstance(item, dict) and item.get("id") == handover_id:
                item["confirmed"] = True
                self._data_manager.save()
                return
        raise ValueError("引き継ぎが見つかりません。")

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
    def _handover_area(value):
        value = str(value or "").strip()
        if value not in {"ホール", "デシャップ", "厨房"}:
            raise ValueError("引き継ぎ場所を選んでください。")
        return value

    @staticmethod
    def _handover_category(area, value):
        if area != "厨房":
            return ""
        value = str(value or "その他").strip()
        if value not in {"ちゃんこ", "深川", "魚", "米", "その他"}:
            return "その他"
        return value

    @staticmethod
    def _optional_number(value, label):
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label}は数字で入力してください。") from error
        if number < 0:
            raise ValueError(f"{label}は0以上で入力してください。")
        return int(number) if number.is_integer() else round(number, 2)

    @staticmethod
    def _status_for_count(count, reorder_point):
        if count <= 0:
            return "out"
        if reorder_point is not None and count <= reorder_point:
            return "low"
        return "enough"

    @staticmethod
    def _date(value):
        try:
            return datetime.strptime(str(value), "%Y-%m-%d")
        except ValueError as error:
            raise ValueError("日付が正しくありません。") from error


store_ops = StoreOperationsManager()
