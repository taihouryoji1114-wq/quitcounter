"""Shared store operations: shortage detection, ordering, and hygiene records."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from core.data import data


class StoreOperationsManager:
    STATUSES = {"enough", "low", "out"}
    INVENTORY_UNITS = ("個", "本", "袋", "パック", "ケース", "箱", "缶", "瓶", "枚", "束", "kg", "L")
    PREP_STATUSES = {"incomplete", "attention", "done"}
    TEMPERATURE_LOCATIONS = (
        "デシャップ冷蔵庫1", "デシャップ冷蔵庫2", "デシャップ冷蔵庫3",
        "厨房冷蔵庫1", "厨房冷蔵庫2", "厨房冷蔵庫3", "厨房冷蔵庫4", "厨房冷蔵庫5",
        "デシャップ冷凍庫", "厨房冷凍庫", "外冷凍庫",
    )
    DAILY_ORDER_DESTINATIONS = ("鶏肉", "ミクリード", "豊洲", "酒屋")
    DEFAULT_INVENTORY_CATEGORIES = (
        ("野菜仕入れ", "#E8F5E9"), ("冷食", "#E3F2FD"),
        ("冷凍庫", "#E8EAF6"), ("飲料", "#E0F7FA"),
        ("調味料", "#FFF3E0"), ("備品", "#F3E5F5"),
        ("清掃用品", "#EDE7F6"), ("その他", "#F5F5F5"),
    )

    def __init__(self, data_manager=None):
        self._data_manager = data_manager or data
        self._migrate_inventory_categories()

    def _migrate_inventory_categories(self):
        """Move legacy food items to vegetables before reusing the label as 冷食."""
        changed = False
        for item in self._data_manager.data.get("store_inventory_items", []):
            if isinstance(item, dict) and item.get("category") == "食材":
                item["category"] = "野菜仕入れ"
                changed = True
        if changed:
            self._data_manager.save()

    def items(self, active_only=True):
        values = self._data_manager.data.get("store_inventory_items", [])
        items = [dict(value) for value in values if isinstance(value, dict)]
        last_checks = {}
        for event in self._data_manager.data.get("store_inventory_events", []):
            if not isinstance(event, dict) or event.get("type") not in {"count", "status"}:
                continue
            item_id = event.get("item_id")
            checked_at = str(event.get("at", ""))
            if item_id and checked_at > last_checks.get(item_id, ""):
                last_checks[item_id] = checked_at
        for item in items:
            item["last_inventory_check_at"] = (
                item.get("last_inventory_check_at") or last_checks.get(item.get("id"), ""))
        if active_only:
            items = [value for value in items if value.get("active", True)]
        category_order = {value["name"]: index for index, value in enumerate(
            self.inventory_categories())}
        return sorted(items, key=lambda value: (
            category_order.get(value.get("category", "その他"), 999),
            int(value.get("sort_order", 999999)), value.get("name", "")))

    def inventory_categories(self):
        """Return configurable inventory sections in display order."""
        saved = self._data_manager.data.get("store_inventory_categories")
        if not isinstance(saved, list) or not saved:
            saved = [{"id": uuid4().hex, "name": name, "color": color,
                      "sort_order": index}
                     for index, (name, color) in enumerate(self.DEFAULT_INVENTORY_CATEGORIES)]
            self._data_manager.data["store_inventory_categories"] = saved
            self._data_manager.save()
        return sorted((dict(value) for value in saved if isinstance(value, dict)),
                      key=lambda value: int(value.get("sort_order", 999)))

    def inventory_subcategories(self):
        saved = self._data_manager.data.get("store_inventory_subcategories")
        if not isinstance(saved, list) or not saved:
            saved = [
                {"id": uuid4().hex, "parent": "飲料", "name": "ソフトドリンク",
                 "color": "#E3F2FD", "sort_order": 0},
                {"id": uuid4().hex, "parent": "飲料", "name": "焼酎",
                 "color": "#FFF3E0", "sort_order": 1},
            ]
            self._data_manager.data["store_inventory_subcategories"] = saved
            self._data_manager.save()
        return sorted((dict(value) for value in saved if isinstance(value, dict)),
                      key=lambda value: (value.get("parent", ""),
                                         int(value.get("sort_order", 999))))

    def save_inventory_subcategory(self, parent, name, color="#F5F5F5",
                                   subcategory_id=None):
        parent, name = str(parent or "").strip(), str(name or "").strip()
        if not parent or not name:
            raise ValueError("大分類と小分類名を入力してください。")
        values = self._data_manager.data.setdefault("store_inventory_subcategories", [])
        if subcategory_id:
            target = next((value for value in values
                           if value.get("id") == subcategory_id), None)
            if target is None:
                raise ValueError("小分類が見つかりません。")
            old_parent, old_name = target.get("parent"), target.get("name")
            target.update(parent=parent, name=name, color=str(color or "#F5F5F5"))
            for item in self._data_manager.data.get("store_inventory_items", []):
                if item.get("category") == old_parent and item.get("subcategory") == old_name:
                    item.update(category=parent, subcategory=name)
        else:
            order = sum(value.get("parent") == parent for value in values)
            values.append({"id": uuid4().hex, "parent": parent, "name": name,
                           "color": str(color or "#F5F5F5"), "sort_order": order})
        self._data_manager.save()

    def assign_inventory_subcategory(self, item_id, subcategory="", parent=None):
        item = self._find(item_id)
        if parent:
            item["category"] = str(parent).strip()
        item["subcategory"] = str(subcategory or "").strip()
        self._data_manager.save()

    def reorder_inventory_items(self, item_ids):
        ids = [str(value) for value in item_ids or []]
        known = {value.get("id"): value for value in
                 self._data_manager.data.get("store_inventory_items", [])}
        for order, item_id in enumerate(ids):
            if item_id in known:
                known[item_id]["sort_order"] = order
        self._data_manager.save()

    def save_inventory_category(self, name, color="#F5F5F5", category_id=None):
        name = str(name or "").strip()
        if not name:
            raise ValueError("分類名を入力してください。")
        categories = self._data_manager.data.setdefault("store_inventory_categories", [])
        if category_id:
            target = next((value for value in categories if value.get("id") == category_id), None)
            if target is None:
                raise ValueError("分類が見つかりません。")
            old_name = target.get("name")
            target.update(name=name, color=str(color or "#F5F5F5"))
            for item in self._data_manager.data.get("store_inventory_items", []):
                if item.get("category") == old_name:
                    item["category"] = name
        else:
            if any(value.get("name") == name for value in categories):
                raise ValueError("同じ分類名があります。")
            categories.append({"id": uuid4().hex, "name": name,
                               "color": str(color or "#F5F5F5"),
                               "sort_order": len(categories)})
        self._data_manager.save()

    def move_inventory_category(self, category_id, direction):
        categories = self.inventory_categories()
        index = next((i for i, value in enumerate(categories)
                      if value.get("id") == category_id), None)
        if index is None:
            raise ValueError("分類が見つかりません。")
        other = index + (-1 if direction == "up" else 1)
        if 0 <= other < len(categories):
            categories[index]["sort_order"], categories[other]["sort_order"] = other, index
            self._data_manager.data["store_inventory_categories"] = categories
            self._data_manager.save()

    def move_inventory_item(self, item_id, direction):
        target = self._find(item_id)
        siblings = [value for value in self.items()
                    if value.get("category") == target.get("category")]
        index = next((i for i, value in enumerate(siblings) if value["id"] == item_id), None)
        other = index + (-1 if direction == "up" else 1) if index is not None else -1
        if 0 <= other < len(siblings):
            ordered_ids = [value["id"] for value in siblings]
            ordered_ids[index], ordered_ids[other] = ordered_ids[other], ordered_ids[index]
            order_map = {value: i for i, value in enumerate(ordered_ids)}
            for item in self._data_manager.data.get("store_inventory_items", []):
                if item.get("id") in order_map:
                    item["sort_order"] = order_map[item["id"]]
            self._data_manager.save()

    def add_item(self, name, category="野菜仕入れ", unit="個", supplier="", required_stock="",
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
        item["last_inventory_check_at"] = datetime.now().isoformat(timespec="seconds")
        item["status"] = self._status_for_count(number, item.get("reorder_point"))
        item["updated_at"] = datetime.now().isoformat(timespec="seconds")
        if item["status"] == "enough":
            self._data_manager.data.setdefault("store_active_orders", {}).pop(item_id, None)
        self._event("count", item, count=number, status=item["status"])
        self._data_manager.save()
        return dict(item)

    def save_inventory_check(self, updates):
        """在庫確認画面の複数項目を、検証後に一度だけ保存する。"""
        prepared = []
        for update in updates or []:
            item = self._find(update.get("item_id"))
            if item.get("tracking_mode") == "count":
                number = self._optional_number(update.get("count"), "現在庫数")
                if number is None:
                    raise ValueError(f"{item['name']}の在庫数を入力してください。")
                prepared.append((item, "count", number))
            else:
                status = update.get("status")
                if status not in self.STATUSES:
                    raise ValueError(f"{item['name']}の在庫状態を選んでください。")
                prepared.append((item, "status", status))

        checked_at = datetime.now().isoformat(timespec="microseconds")
        for item, kind, value in prepared:
            if kind == "count":
                item["current_stock"] = value
                item["status"] = self._status_for_count(value, item.get("reorder_point"))
                extra = {"count": value, "status": item["status"]}
            else:
                item["status"] = value
                extra = {"status": value}
            item["last_inventory_check_at"] = checked_at
            item["updated_at"] = checked_at
            if item["status"] == "enough":
                self._data_manager.data.setdefault("store_active_orders", {}).pop(
                    item["id"], None)
            self._event(kind, item, **extra)
        if prepared:
            self._data_manager.save()
        return len(prepared)

    def inventory_check_reset_at(self):
        """在庫確認フォームを最後に手動リセットした時刻を返す。"""
        return str(self._data_manager.data.get("store_inventory_check_reset_at", ""))

    def reset_inventory_check(self):
        """在庫の実績や発注情報を残したまま、確認フォームだけを未入力に戻す。"""
        reset_at = datetime.now().isoformat(timespec="microseconds")
        self._data_manager.data["store_inventory_check_reset_at"] = reset_at
        self._data_manager.save()
        return reset_at

    def update_count_settings(self, item_id, unit, required_stock=None,
                              reorder_point=None, current_stock=None):
        """既存商品を数量管理へ変更する。"""
        item = self._find(item_id)
        required_number = self._optional_number(required_stock, "必要在庫数")
        reorder_number = self._optional_number(reorder_point, "発注ライン")
        current_number = self._optional_number(current_stock, "現在庫数")
        if required_stock in (None, ""):
            required_number = item.get("required_stock")
        if reorder_point in (None, ""):
            reorder_number = item.get("reorder_point")
        if current_stock in (None, ""):
            current_number = item.get("current_stock")
        if (required_number is not None and reorder_number is not None
                and reorder_number > required_number):
            raise ValueError("発注ラインは必要在庫数以下にしてください。")
        item.update({
            "unit": str(unit or "個").strip(), "required_stock": required_number,
            "reorder_point": reorder_number, "current_stock": current_number,
            "tracking_mode": "count",
            "status": self._status_for_count(current_number, reorder_number)
            if current_number is not None else item.get("status", "enough"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        })
        self._event("count_settings", item)
        self._data_manager.save()
        return dict(item)

    def delete_item(self, item_id):
        item = self._find(item_id)
        item["active"] = False
        item["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._data_manager.data.setdefault("store_active_orders", {}).pop(item_id, None)
        self._event("deleted", item)
        self._data_manager.save()

    def update_item(self, item_id, name, category, unit="個", supplier="",
                    tracking_mode="count"):
        item = self._find(item_id)
        name = str(name or "").strip()
        if not name:
            raise ValueError("商品名を入力してください。")
        if any(value["id"] != item_id and value["name"] == name
               for value in self.items()):
            raise ValueError("同じ名前の商品が登録されています。")
        if tracking_mode not in {"simple", "count"}:
            tracking_mode = "count"
        item.update({
            "name": name,
            "category": str(category or "その他").strip(),
            "unit": str(unit or "個").strip(),
            "supplier": str(supplier or "").strip(),
            "tracking_mode": tracking_mode,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        })
        self._event("updated", item)
        self._data_manager.save()
        return dict(item)

    def set_status(self, item_id, status):
        if status not in self.STATUSES:
            raise ValueError("在庫状態が正しくありません。")
        item = self._find(item_id)
        item["status"] = status
        item["last_inventory_check_at"] = datetime.now().isoformat(timespec="seconds")
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
            shortage = None
            if item.get("tracking_mode") == "count":
                required = item.get("required_stock")
                current = item.get("current_stock")
                if required is not None and current is not None:
                    shortage = max(0, round(float(required) - float(current), 2))
                    if float(shortage).is_integer():
                        shortage = int(shortage)
            result.append({**item, "order_state": order.get("state", "needed"),
                           "ordered_at": order.get("ordered_at", ""),
                           "suggested_order_quantity": shortage})
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
        if item.get("tracking_mode") == "count" and item.get("required_stock") is not None:
            item["current_stock"] = item["required_stock"]
        item["status"] = "enough"
        item["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._data_manager.data.setdefault("store_active_orders", {}).pop(item_id, None)
        self._event("received", item)
        self._data_manager.save()

    def purchase_quantities(self, record_date=None):
        """Return the owner's current purchase plan by inventory item."""
        if record_date is None:
            from core.clock import operational_date_jst
            record_date = operational_date_jst().isoformat()
        self._date(record_date)
        stored = self._data_manager.data.get("store_purchase_quantities", {})
        if not isinstance(stored, dict):
            stored = {}
        legacy = {key: value for key, value in stored.items()
                  if not (len(str(key)) == 10 and str(key)[4] == "-" and str(key)[7] == "-")}
        day_values = stored.get(record_date, {})
        if not isinstance(day_values, dict):
            day_values = {}
        if legacy and not day_values:
            day_values = dict(legacy)
            for key in legacy:
                stored.pop(key, None)
            stored[record_date] = day_values
            self._data_manager.save()
        return {item["id"]: day_values.get(item["id"]) for item in self.items()}

    def save_purchase_quantities(self, quantities, record_date=None):
        """Replace the purchase plan; zero/blank values remove an item from the list."""
        if record_date is None:
            from core.clock import operational_date_jst
            record_date = operational_date_jst().isoformat()
        self._date(record_date)
        cleaned = {}
        for item_id, value in (quantities or {}).items():
            item = self._find(item_id)
            number = self._optional_number(value, f"{item['name']}の仕入れ数")
            if number is None or number == 0:
                continue
            if number < 0:
                raise ValueError("仕入れ数は0以上で入力してください。")
            cleaned[item_id] = number
        stored = self._data_manager.data.setdefault("store_purchase_quantities", {})
        for key in list(stored):
            if not (len(str(key)) == 10 and str(key)[4] == "-" and str(key)[7] == "-"):
                stored.pop(key, None)
        stored[record_date] = cleaned
        self._data_manager.save()
        return len(cleaned)

    def set_purchase_item_completed(self, item_id, completed, record_date=None):
        """Hide or restore one low-stock item on a specific operating day's list."""
        if record_date is None:
            from core.clock import operational_date_jst
            record_date = operational_date_jst().isoformat()
        self._date(record_date)
        self._find(item_id)
        stored = self._data_manager.data.setdefault("store_purchase_completed", {})
        day_values = stored.setdefault(record_date, {})
        if completed:
            day_values[item_id] = datetime.now().isoformat(timespec="minutes")
        else:
            day_values.pop(item_id, None)
        if not day_values:
            stored.pop(record_date, None)
        self._data_manager.save()

    def purchase_list(self, record_date=None, include_completed=False):
        """Return counted items which have reached their minimum stock level.

        The purchase quantity is calculated automatically so the stock becomes one unit
        higher than the minimum.  This keeps the list useful without a second manual
        entry step on the inventory screen.
        """
        if record_date is None:
            from core.clock import operational_date_jst
            record_date = operational_date_jst().isoformat()
        self._date(record_date)
        completed_values = self._data_manager.data.get(
            "store_purchase_completed", {}).get(record_date, {})
        if not isinstance(completed_values, dict):
            completed_values = {}
        result = []
        for item in self.items():
            if item.get("tracking_mode") != "count":
                continue
            minimum = item.get("reorder_point")
            current = item.get("current_stock")
            if minimum is None or current is None or float(current) > float(minimum):
                continue
            quantity = max(1, round(float(minimum) - float(current) + 1, 2))
            if float(quantity).is_integer():
                quantity = int(quantity)
            completed = item["id"] in completed_values
            if completed and not include_completed:
                continue
            result.append({**item, "purchase_quantity": quantity, "auto_added": True,
                           "completed": completed})
        return sorted(result, key=lambda value: (
            float(value.get("current_stock", 0)) - float(value.get("reorder_point", 0)),
            value.get("name", ""),
        ))

    def daily_order_checks(self, record_date):
        self._date(record_date)
        stored = self._data_manager.data.get("store_daily_order_checks", {}).get(record_date, {})
        if not isinstance(stored, dict):
            stored = {}
        return {name: bool(stored.get(name, False)) for name in self.DAILY_ORDER_DESTINATIONS}

    def ensure_daily_checklist(self, record_date):
        """Mark that this operating day's checklist has been opened."""
        self._date(record_date)
        days = self._data_manager.data.setdefault("store_checklist_days", {})
        if record_date not in days:
            days[record_date] = {"opened_at": datetime.now().isoformat(timespec="minutes")}
            self._data_manager.save()

    def daily_order_attention(self, record_date):
        self._date(record_date)
        stored = self._data_manager.data.get("store_daily_order_attention", {}).get(
            record_date, {})
        return {name: bool(stored.get(name, False)) for name in self.DAILY_ORDER_DESTINATIONS}

    def set_daily_order_attention(self, record_date, destination, attention):
        self._date(record_date)
        if destination not in self.DAILY_ORDER_DESTINATIONS:
            raise ValueError("発注先が正しくありません。")
        self._data_manager.data.setdefault("store_daily_order_attention", {}).setdefault(
            record_date, {})[destination] = bool(attention)
        self._data_manager.save()

    def set_daily_order_check(self, record_date, destination, checked):
        self._date(record_date)
        if destination not in self.DAILY_ORDER_DESTINATIONS:
            raise ValueError("発注先が正しくありません。")
        self._data_manager.data.setdefault("store_daily_order_checks", {}).setdefault(
            record_date, {})[destination] = bool(checked)
        self._data_manager.save()

    def order_requests(self, open_only=False):
        values = self._data_manager.data.get("store_order_requests", [])
        result = [dict(value) for value in values if isinstance(value, dict)]
        if open_only:
            result = [value for value in result if not value.get("completed", False)]
        return sorted(result, key=lambda value: (
            bool(value.get("completed", False)), value.get("created_at", "")))

    def add_order_request(self, message):
        message = str(message or "").strip()
        if not message:
            raise ValueError("発注してほしいものを入力してください。")
        item = {
            "id": uuid4().hex, "message": message[:200], "completed": False,
            "created_at": datetime.now().isoformat(timespec="minutes"),
        }
        self._data_manager.data.setdefault("store_order_requests", []).append(item)
        self._data_manager.save()
        return dict(item)

    def set_order_request_completed(self, request_id, completed):
        for item in self._data_manager.data.setdefault("store_order_requests", []):
            if isinstance(item, dict) and item.get("id") == request_id:
                item["completed"] = bool(completed)
                item["completed_at"] = (datetime.now().isoformat(timespec="minutes")
                                        if completed else "")
                self._data_manager.save()
                return
        raise ValueError("発注依頼が見つかりません。")

    def delete_order_request(self, request_id):
        values = self._data_manager.data.setdefault("store_order_requests", [])
        before = len(values)
        values[:] = [value for value in values
                     if not isinstance(value, dict) or value.get("id") != request_id]
        if len(values) == before:
            raise ValueError("発注依頼が見つかりません。")
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

    @staticmethod
    def _prep_options(check_items=None, note_enabled=False):
        if isinstance(check_items, str):
            check_items = check_items.replace("、", "\n").splitlines()
        cleaned = []
        for value in check_items or []:
            text = str(value or "").strip()
            if text and text not in cleaned:
                cleaned.append(text[:80])
        return cleaned[:12], bool(note_enabled)

    def add_prep_template(self, name, area="厨房", check_items=None, note_enabled=False):
        name = str(name or "").strip()
        if not name:
            raise ValueError("仕込み名を入力してください。")
        if any(value.get("name") == name for value in self.prep_templates()):
            raise ValueError("同じ仕込み項目が登録されています。")
        checks, note_enabled = self._prep_options(check_items, note_enabled)
        item = {"id": uuid4().hex, "name": name, "area": str(area or "厨房").strip(),
                "check_items": checks, "note_enabled": note_enabled, "active": True}
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

    def update_prep_template(self, item_id, name, area="厨房", check_items=None,
                             note_enabled=False):
        values = self._data_manager.data.setdefault("store_prep_templates", [])
        item = next((value for value in values if isinstance(value, dict)
                     and value.get("id") == item_id and value.get("active", True)), None)
        if not item:
            raise ValueError("仕込み項目が見つかりません。")
        name = str(name or "").strip()
        if not name:
            raise ValueError("仕込み名を入力してください。")
        if any(value.get("id") != item_id and value.get("name") == name
               and value.get("active", True) for value in values if isinstance(value, dict)):
            raise ValueError("同じ仕込み項目が登録されています。")
        checks, note_enabled = self._prep_options(check_items, note_enabled)
        item.update(name=name, area=str(area or "厨房").strip(),
                    check_items=checks, note_enabled=note_enabled)
        self._data_manager.save()
        return dict(item)

    def move_prep_template(self, item_id, direction):
        """登録済みの仕込み項目を1つ上または下へ移動する。"""
        if direction not in {-1, 1}:
            raise ValueError("移動先が正しくありません。")
        values = self._data_manager.data.setdefault("store_prep_templates", [])
        active_indexes = [index for index, value in enumerate(values)
                          if isinstance(value, dict) and value.get("active", True)]
        current_position = next(
            (position for position, index in enumerate(active_indexes)
             if values[index].get("id") == item_id), None)
        if current_position is None:
            raise ValueError("仕込み項目が見つかりません。")
        target_position = current_position + direction
        if target_position < 0 or target_position >= len(active_indexes):
            return False
        current_index = active_indexes[current_position]
        target_index = active_indexes[target_position]
        values[current_index], values[target_index] = values[target_index], values[current_index]
        self._data_manager.save()
        return True

    def prep_items(self, record_date):
        day = self._date(record_date)
        states = self._data_manager.data.get("store_prep_records", {}).get(record_date, {})
        previous_date = (day - timedelta(days=1)).strftime("%Y-%m-%d")
        previous_states = self._data_manager.data.get("store_prep_records", {}).get(previous_date, {})
        previous_started = previous_date in self._data_manager.data.get("store_checklist_days", {})
        result = [{**item, "status": (states.get(item["id"])
                                      if states.get(item["id"]) in self.PREP_STATUSES
                                      else "incomplete"),
                   "carried_over": ((previous_started or item["id"] in previous_states)
                                    and previous_states.get(item["id"]) != "done"),
                   "carry_priority": ("attention" if previous_states.get(item["id"]) == "attention"
                                      else "overdue"),
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

    @staticmethod
    def _service_period(period):
        if period not in {"lunch", "dinner"}:
            raise ValueError("営業区分が正しくありません。")
        return period

    @staticmethod
    def _is_quantity_prep(item):
        name = str(item.get("name", ""))
        return "サバ" in name or "ホッケ" in name

    @staticmethod
    def _is_leftover_rice(item):
        return "余り米" in str(item.get("name", ""))

    def ensure_service_checklist(self, record_date, period):
        self._date(record_date)
        period = self._service_period(period)
        sessions = self._data_manager.data.setdefault("store_checklist_sessions", {})
        day = sessions.setdefault(record_date, {})
        if period not in day:
            day[period] = {"opened_at": datetime.now().isoformat(timespec="minutes")}
            self._data_manager.save()

    def active_service_context(self, default_date, default_period):
        """Return the checklist context selected by staff.

        Once initialized, both the operating date and lunch/dinner period stay fixed
        until ``advance_service_context`` is used.  This prevents a date change from
        making completed work appear to have reset itself.
        """
        context = self._data_manager.data.get("store_active_service_context", {})
        record_date = str(context.get("date", ""))
        period = str(context.get("period", ""))
        changed = False
        try:
            self._date(record_date)
            self._service_period(period)
        except (TypeError, ValueError):
            record_date = str(default_date)
            period = self._service_period(default_period)
            changed = True
        if changed:
            self._data_manager.data["store_active_service_context"] = {
                "date": record_date, "period": period,
            }
            self._data_manager.save()
        self.ensure_service_checklist(record_date, period)
        return record_date, period

    def advance_service_context(self):
        """Move to the next service only when a staff member explicitly requests it."""
        context = self._data_manager.data.get("store_active_service_context", {})
        record_date = str(context.get("date", ""))
        period = self._service_period(str(context.get("period", "lunch")))
        day = self._date(record_date)
        # Keep both lanes exactly as staff left them. The next service starts from
        # this snapshot instead of rebuilding every template as uncompleted.
        board = self.service_handover_board(record_date, period)
        for item in self.service_prep_items(
                board["source_date"], board["source_period"]):
            if item.get("quantity_mode"):
                self.set_service_prep_quantity(
                    record_date, period, item["id"], item.get("quantity", 0))
            elif item.get("choice_mode"):
                self.set_service_prep_choice(
                    record_date, period, item["id"], item.get("choice", ""))
            else:
                self.set_service_prep_status(
                    record_date, period, item["id"], item.get("status", "incomplete"))
        if period == "lunch":
            next_date, next_period = record_date, "dinner"
        else:
            next_date = (day + timedelta(days=1)).strftime("%Y-%m-%d")
            next_period = "lunch"
        self._data_manager.data["store_active_service_context"] = {
            "date": next_date, "period": next_period,
        }
        self.ensure_service_checklist(next_date, next_period)
        self._data_manager.save()
        return next_date, next_period

    def service_prep_items(self, record_date, period):
        self._date(record_date)
        period = self._service_period(period)
        states = self._data_manager.data.get("store_service_prep_records", {}).get(
            record_date, {}).get(period, {})
        quantities = self._data_manager.data.get("store_service_prep_quantities", {}).get(
            record_date, {}).get(period, {})
        choices = self._data_manager.data.get("store_service_prep_choices", {}).get(
            record_date, {}).get(period, {})
        subchecks = self._data_manager.data.get("store_service_prep_subchecks", {}).get(
            record_date, {}).get(period, {})
        notes = self._data_manager.data.get("store_service_prep_notes", {}).get(
            record_date, {}).get(period, {})
        result = []
        for item in self.prep_templates():
            quantity_mode = self._is_quantity_prep(item)
            choice_mode = self._is_leftover_rice(item)
            quantity = int(quantities.get(item["id"], 0) or 0) if quantity_mode else None
            choice = choices.get(item["id"], "") if choice_mode else ""
            status = states.get(item["id"], "incomplete")
            if quantity_mode:
                status = "done" if quantity >= 2 else "incomplete"
            elif choice_mode:
                status = "done" if choice in {"あり", "なし"} else "incomplete"
            elif status not in self.PREP_STATUSES:
                status = "incomplete"
            check_items = list(item.get("check_items", []))
            checked = [value for value in subchecks.get(item["id"], [])
                       if value in check_items]
            if check_items:
                status = "done" if len(checked) == len(check_items) else "incomplete"
            result.append({**item, "status": status, "quantity_mode": quantity_mode,
                           "quantity": quantity, "choice_mode": choice_mode,
                           "choice": choice, "checked_items": checked,
                           "note": str(notes.get(item["id"], ""))})
        return result

    def set_service_prep_subchecks(self, record_date, period, item_id, checked_items):
        self._date(record_date)
        period = self._service_period(period)
        item = next((value for value in self.prep_templates() if value["id"] == item_id), None)
        if not item or not item.get("check_items"):
            raise ValueError("個別チェックを使う仕込み項目が見つかりません。")
        allowed = list(item["check_items"])
        checked = [value for value in (checked_items or []) if value in allowed]
        values = self._data_manager.data.setdefault(
            "store_service_prep_subchecks", {}).setdefault(record_date, {}).setdefault(period, {})
        values[item_id] = checked
        self._data_manager.save()
        return checked

    def set_service_prep_note(self, record_date, period, item_id, note):
        self._date(record_date)
        period = self._service_period(period)
        item = next((value for value in self.prep_templates() if value["id"] == item_id), None)
        if not item or not item.get("note_enabled"):
            raise ValueError("メモを使う仕込み項目が見つかりません。")
        values = self._data_manager.data.setdefault(
            "store_service_prep_notes", {}).setdefault(record_date, {}).setdefault(period, {})
        text = str(note or "").strip()[:500]
        if text:
            values[item_id] = text
        else:
            values.pop(item_id, None)
        self._data_manager.save()
        return text

    def set_service_prep_status(self, record_date, period, item_id, status):
        self._date(record_date)
        period = self._service_period(period)
        if status not in self.PREP_STATUSES:
            raise ValueError("仕込み状況が正しくありません。")
        item = next((value for value in self.prep_templates() if value["id"] == item_id), None)
        if not item:
            raise ValueError("仕込み項目が見つかりません。")
        if self._is_quantity_prep(item) or self._is_leftover_rice(item):
            raise ValueError("この項目は専用の入力方法で記録してください。")
        self._data_manager.data.setdefault("store_service_prep_records", {}).setdefault(
            record_date, {}).setdefault(period, {})[item_id] = status
        self._data_manager.save()

    def set_service_prep_quantity(self, record_date, period, item_id, quantity):
        self._date(record_date)
        period = self._service_period(period)
        item = next((value for value in self.prep_templates() if value["id"] == item_id), None)
        if not item or not self._is_quantity_prep(item):
            raise ValueError("個数で管理する項目が見つかりません。")
        try:
            quantity = max(0, int(quantity or 0))
        except (TypeError, ValueError) as error:
            raise ValueError("個数は数字で入力してください。") from error
        self._data_manager.data.setdefault("store_service_prep_quantities", {}).setdefault(
            record_date, {}).setdefault(period, {})[item_id] = quantity
        self._data_manager.save()

    def set_service_prep_choice(self, record_date, period, item_id, choice):
        self._date(record_date)
        period = self._service_period(period)
        item = next((value for value in self.prep_templates() if value["id"] == item_id), None)
        if not item or not self._is_leftover_rice(item):
            raise ValueError("あり・なしで管理する項目が見つかりません。")
        if choice not in {"あり", "なし", ""}:
            raise ValueError("あり、または、なしを選んでください。")
        values = self._data_manager.data.setdefault(
            "store_service_prep_choices", {}).setdefault(record_date, {}).setdefault(period, {})
        if choice:
            values[item_id] = choice
        else:
            values.pop(item_id, None)
        self._data_manager.save()

    def reset_service_prep_items(self, record_date, period, item_ids):
        """Return several completed checklist entries to their uncompleted state."""
        self._date(record_date)
        period = self._service_period(period)
        selected = set(item_ids or [])
        changed = 0
        for item in self.prep_templates():
            if item["id"] not in selected:
                continue
            if self._is_quantity_prep(item):
                self._data_manager.data.setdefault(
                    "store_service_prep_quantities", {}).setdefault(
                        record_date, {}).setdefault(period, {})[item["id"]] = 0
            elif self._is_leftover_rice(item):
                self._data_manager.data.setdefault(
                    "store_service_prep_choices", {}).setdefault(
                        record_date, {}).setdefault(period, {}).pop(item["id"], None)
            else:
                self._data_manager.data.setdefault(
                    "store_service_prep_records", {}).setdefault(
                        record_date, {}).setdefault(period, {})[item["id"]] = "incomplete"
            self._data_manager.data.setdefault(
                "store_service_prep_subchecks", {}).setdefault(
                    record_date, {}).setdefault(period, {}).pop(item["id"], None)
            changed += 1
        if changed:
            self._data_manager.save()
        return changed

    def service_handover_board(self, record_date, period):
        """Return the active handover board, including today's completed lane."""
        day = self._date(record_date)
        period = self._service_period(period)
        if period == "dinner":
            source_date, source_period = record_date, "lunch"
            source_label = "ランチ"
        else:
            source_date = (day - timedelta(days=1)).strftime("%Y-%m-%d")
            source_period = "dinner"
            source_label = "前日ディナー"
        sessions = self._data_manager.data.get("store_checklist_sessions", {})
        source_started = source_period in sessions.get(source_date, {})
        items = []
        prep_date, prep_period = (source_date, source_period) if source_started else (
            record_date, period)
        if source_started or self.prep_templates():
            for prep in self.service_prep_items(prep_date, prep_period):
                if prep.get("choice_mode") and prep.get("choice"):
                    items.append({"id": prep["id"], "kind": "check_result",
                                  "name": f"{prep['name']}：{prep['choice']}",
                                  "area": prep.get("area", "厨房"),
                                  "from_date": prep_date, "from_period": prep_period,
                                  "completed": True})
                    continue
                detail = prep["name"]
                if prep.get("quantity_mode"):
                    detail = f"{detail}（残り{prep.get('quantity', 0)}・2個必要）"
                items.append({"id": prep["id"], "kind": "prep", "name": detail,
                              "area": prep.get("area", "厨房"), "from_date": prep_date,
                              "from_period": prep_period,
                              "quantity_mode": prep.get("quantity_mode", False),
                              "quantity": prep.get("quantity", 0),
                              "choice_mode": prep.get("choice_mode", False),
                              "check_items": list(prep.get("check_items", [])),
                              "checked_items": list(prep.get("checked_items", [])),
                              "note_enabled": bool(prep.get("note_enabled", False)),
                              "note": prep.get("note", ""),
                              "completed": prep["status"] == "done"})
        handover_days = self._data_manager.data.get("store_handovers", {})
        for note_date in sorted(handover_days):
            if note_date > record_date:
                continue
            for note in self.handovers(note_date):
                confirmed = bool(note.get("confirmed", False))
                if not note.get("deleted_at"):
                    items.append({"id": note["id"], "kind": "note",
                                  "name": note.get("message", "引き継ぎ"),
                                  "area": note.get("area", "厨房"), "from_date": note_date,
                                  "completed": confirmed})
        for request in self.order_requests():
            completed = bool(request.get("completed", False))
            completed_date = str(request.get("completed_at", ""))[:10]
            if completed and completed_date not in {record_date, source_date}:
                continue
            items.append({"id": request["id"], "kind": "request",
                          "name": request.get("message", "発注依頼"), "area": "発注依頼",
                          "from_date": str(request.get("created_at", ""))[:10],
                          "completed": completed})
        return {"source_date": source_date, "source_period": source_period,
                "source_label": source_label, "items": items}

    def reopen_handover_board_items(self, items):
        """Move every completed handover-board item back to the pending lane."""
        changed = 0
        for item in items or []:
            if not item.get("completed"):
                continue
            kind = item.get("kind")
            if kind in {"prep", "check_result"}:
                changed += self.reset_service_prep_items(
                    item.get("from_date"), item.get("from_period"), [item.get("id")])
            elif kind == "note":
                self.reopen_handover(item.get("from_date"), item.get("id"))
                changed += 1
            elif kind == "request":
                self.set_order_request_completed(item.get("id"), False)
                changed += 1
        return changed

    def previous_day_board(self, record_date):
        """前日のチェック残り・自由引き継ぎ・発注依頼を返す。"""
        day = self._date(record_date)
        previous_date = (day - timedelta(days=1)).strftime("%Y-%m-%d")
        items = []
        for prep in self.prep_items(record_date):
            if prep.get("carried_over") and prep.get("status") != "done":
                items.append({
                    "id": prep.get("id"),
                    "kind": ("attention" if prep.get("carry_priority") == "attention" else "prep"),
                    "name": prep.get("name", "仕込み"),
                    "area": prep.get("area", "厨房"), "from_date": previous_date,
                })
        for note in self.handovers(previous_date):
            if not note.get("confirmed", False):
                items.append({
                    "id": note.get("id"), "kind": "note", "name": note.get("message", "引き継ぎ"),
                    "area": note.get("area", "厨房"), "from_date": previous_date,
                })
        order_days = self._data_manager.data.get("store_daily_order_checks", {})
        if (previous_date in self._data_manager.data.get("store_checklist_days", {})
                or previous_date in order_days):
            previous_orders = self.daily_order_checks(previous_date)
            previous_attention = self.daily_order_attention(previous_date)
            for destination, ordered in previous_orders.items():
                if not ordered:
                    items.append({
                        "id": f"order-missed:{previous_date}:{destination}",
                        "kind": "order_attention" if previous_attention[destination] else "order_missed",
                        "name": f"{destination}への発注未完了", "area": "発注",
                        "from_date": previous_date,
                    })
        for request in self.order_requests(open_only=True):
            created_date = str(request.get("created_at", ""))[:10]
            if created_date and created_date <= previous_date:
                items.append({
                    "id": request.get("id"), "kind": "request",
                    "name": f"発注依頼：{request.get('message', '')}", "area": "発注依頼",
                    "from_date": created_date,
                })
        return {"previous_date": previous_date, "items": items}

    def set_prep_status(self, record_date, item_id, status):
        self._date(record_date)
        if status not in self.PREP_STATUSES:
            raise ValueError("仕込み状況が正しくありません。")
        if not any(value["id"] == item_id for value in self.prep_items(record_date)):
            raise ValueError("仕込み項目が見つかりません。")
        self._data_manager.data.setdefault("store_prep_records", {}).setdefault(record_date, {})[item_id] = status
        self._data_manager.save()

    def reset_prep_statuses(self, record_date):
        """Reset every visible prep item for the day to incomplete."""
        self._date(record_date)
        records = self._data_manager.data.setdefault("store_prep_records", {}).setdefault(
            record_date, {})
        for item in self.prep_items(record_date):
            records[item["id"]] = "incomplete"
        self._data_manager.save()

    def move_kitchen_handovers_to_prep(self):
        """Move legacy kitchen check templates into today's unified checklist once."""
        existing = {(item.get("name"), item.get("area")) for item in self.prep_templates()}
        moved = 0
        for item in self._data_manager.data.setdefault("store_handover_templates", []):
            if not isinstance(item, dict) or not item.get("active", True):
                continue
            if item.get("area") != "厨房":
                continue
            key = (item.get("name"), "厨房")
            if key not in existing:
                self._data_manager.data.setdefault("store_prep_templates", []).append({
                    "id": uuid4().hex, "name": item.get("name", "厨房作業"),
                    "area": "厨房", "active": True,
                })
                existing.add(key)
            item["active"] = False
            moved += 1
        if moved:
            self._data_manager.save()
        return moved

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
        item = {"id": uuid4().hex, "name": name, "area": area, "category": "",
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

    def update_handover_template(self, template_id, name, area="厨房"):
        values = self._data_manager.data.setdefault("store_handover_templates", [])
        item = next((value for value in values if isinstance(value, dict)
                     and value.get("id") == template_id and value.get("active", True)), None)
        if not item:
            raise ValueError("引き継ぎ項目が見つかりません。")
        name = str(name or "").strip()
        area = self._handover_area(area)
        if not name:
            raise ValueError("チェック項目を入力してください。")
        if any(value.get("id") != template_id and value.get("name") == name
               and value.get("area") == area and value.get("active", True)
               for value in values if isinstance(value, dict)):
            raise ValueError("同じチェック項目が登録されています。")
        item.update(name=name, area=area)
        self._data_manager.save()
        return dict(item)

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
        return [dict(value) for value in values
                if isinstance(value, dict) and not value.get("deleted_at")]

    def all_handovers(self):
        """Keep free handovers visible across dates until explicitly deleted."""
        return [dict(note, record_date=record_date)
                for record_date in sorted(self._data_manager.data.get("store_handovers", {}))
                for note in self.handovers(record_date)]

    def delete_handover(self, record_date, handover_id):
        self._date(record_date)
        for item in self._data_manager.data.get("store_handovers", {}).get(record_date, []):
            if isinstance(item, dict) and item.get("id") == handover_id:
                item["deleted_at"] = datetime.now().isoformat(timespec="seconds")
                self._data_manager.save()
                return
        raise ValueError("引き継ぎが見つかりません。")

    def add_handover(self, record_date, message, area="厨房", category=""):
        self._date(record_date)
        message = str(message or "").strip()
        if not message:
            raise ValueError("引き継ぎ内容を入力してください。")
        area = self._handover_area(area)
        item = {"id": uuid4().hex, "message": message[:500],
                "area": area, "category": "", "confirmed": False,
                "created_at": datetime.now().isoformat(timespec="minutes")}
        self._data_manager.data.setdefault("store_handovers", {}).setdefault(record_date, []).append(item)
        self._data_manager.save()
        return dict(item)

    def confirm_handover(self, record_date, handover_id):
        for item in self._data_manager.data.setdefault("store_handovers", {}).setdefault(record_date, []):
            if isinstance(item, dict) and item.get("id") == handover_id:
                item["confirmed"] = True
                item["confirmed_at"] = datetime.now().isoformat(timespec="minutes")
                self._data_manager.save()
                return
        raise ValueError("引き継ぎが見つかりません。")

    def reopen_handover(self, record_date, handover_id):
        """Return an accidentally completed free handover to the open lane."""
        for item in self._data_manager.data.setdefault("store_handovers", {}).setdefault(
                record_date, []):
            if isinstance(item, dict) and item.get("id") == handover_id:
                item["confirmed"] = False
                item["confirmed_at"] = ""
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
        # 旧データとの互換性のため引数は残すが、分類は場所の3区分だけに統一する。
        return ""

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
