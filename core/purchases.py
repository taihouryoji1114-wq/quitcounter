"""Persistent supplier purchase records shared with financial planning."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4


class PurchaseManager:
    def __init__(self, data_manager):
        self._data_manager = data_manager

    def records(self, month=None):
        records = self._data_manager.data.get("business_purchases", [])
        if month:
            records = [item for item in records if item.get("date", "").startswith(month)]
        return sorted(records, key=lambda item: (item["date"], item["id"]), reverse=True)

    def add(self, record_date, supplier, total):
        self._validate_date(record_date)
        supplier = str(supplier or "").strip()
        if not supplier:
            raise ValueError("仕入れ先を入力してください。")
        total = self._validate_total(total)
        record = {
            "id": uuid4().hex,
            "date": record_date,
            "supplier": supplier,
            "total": total,
        }
        self._data_manager.data.setdefault("business_purchases", []).append(record)
        hidden = self._data_manager.data.get("business_hidden_suppliers", [])
        if supplier in hidden:
            hidden.remove(supplier)
        self._data_manager.save()
        return record

    def delete(self, record_id):
        records = self._data_manager.data.get("business_purchases", [])
        record = next((item for item in records if item.get("id") == record_id), None)
        if record is None:
            raise ValueError("削除する仕入れ記録が見つかりません。")
        records.remove(record)
        self._data_manager.save()
        return record

    def suppliers(self):
        hidden = set(self._data_manager.data.get("business_hidden_suppliers", []))
        result = []
        for record in self.records():
            supplier = record.get("supplier")
            if supplier and supplier not in hidden and supplier not in result:
                result.append(supplier)
        return result

    def hide_supplier(self, supplier):
        supplier = str(supplier or "").strip()
        if not supplier:
            raise ValueError("削除する仕入れ先を選択してください。")
        hidden = self._data_manager.data.setdefault(
            "business_hidden_suppliers", []
        )
        if supplier not in hidden:
            hidden.append(supplier)
            self._data_manager.save()
        return supplier

    def daily_total(self, record_date):
        self._validate_date(record_date)
        return sum(
            int(item.get("total", 0))
            for item in self.records()
            if item.get("date") == record_date
        )

    def monthly_total(self, month):
        try:
            datetime.strptime(month, "%Y-%m")
        except (TypeError, ValueError) as error:
            raise ValueError("月は YYYY-MM 形式で指定してください。") from error
        return sum(int(item.get("total", 0)) for item in self.records(month))

    @staticmethod
    def _validate_date(value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError("日付を選択してください。") from error

    @staticmethod
    def _validate_total(value):
        try:
            numeric = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError("合計金額を1円以上で入力してください。") from error
        if numeric <= 0 or not numeric.is_integer():
            raise ValueError("合計金額を1円以上の整数で入力してください。")
        return int(numeric)


from core.data import data  # noqa: E402


purchases = PurchaseManager(data)
