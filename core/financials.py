"""Persistent daily business figures for the Future Financials app."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4


class FinancialManager:
    def __init__(self, data_manager):
        self._data_manager = data_manager

    def sales_records(self, month=None, record_date=None):
        records = self._data_manager.data.get("business_sales", [])
        if month:
            self._validate_month(month)
            records = [item for item in records if item.get("date", "").startswith(month)]
        if record_date:
            self._validate_date(record_date)
            records = [item for item in records if item.get("date") == record_date]
        return sorted(records, key=lambda item: (item["date"], item["id"]), reverse=True)

    def set_daily_sales(self, record_date, amount):
        self._validate_date(record_date)
        amount = self._validate_amount(amount)
        records = self._data_manager.data.setdefault("business_sales", [])
        record = next((item for item in records if item.get("date") == record_date), None)
        if record is None:
            record = {"id": uuid4().hex, "date": record_date, "amount": amount}
            records.append(record)
        else:
            record["amount"] = amount
        self._data_manager.save()
        return record

    def delete_sales(self, record_id):
        records = self._data_manager.data.get("business_sales", [])
        record = next((item for item in records if item.get("id") == record_id), None)
        if record is None:
            raise ValueError("削除する売上記録が見つかりません。")
        records.remove(record)
        self._data_manager.save()
        return record

    def monthly_sales_total(self, month):
        return sum(int(item.get("amount", 0)) for item in self.sales_records(month=month))

    @staticmethod
    def _validate_date(value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError("日付を選択してください。") from error

    @staticmethod
    def _validate_month(value):
        try:
            datetime.strptime(value, "%Y-%m")
        except (TypeError, ValueError) as error:
            raise ValueError("月は YYYY-MM 形式で指定してください。") from error

    @staticmethod
    def _validate_amount(value):
        try:
            numeric = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError("売上を0円以上の整数で入力してください。") from error
        if numeric < 0 or not numeric.is_integer():
            raise ValueError("売上を0円以上の整数で入力してください。")
        return int(numeric)


from core.data import data  # noqa: E402


financials = FinancialManager(data)
