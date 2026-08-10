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

    def set_daily_sales(
        self,
        record_date,
        amount=None,
        lunch_sales=None,
        dinner_sales=None,
        lunch_customers=None,
        dinner_customers=None,
    ):
        self._validate_date(record_date)
        split_entry = any(
            value is not None
            for value in (lunch_sales, dinner_sales, lunch_customers, dinner_customers)
        )
        if split_entry:
            lunch_sales = self._validate_amount(lunch_sales or 0)
            dinner_sales = self._validate_amount(dinner_sales or 0)
            lunch_customers = self._validate_count(lunch_customers or 0)
            dinner_customers = self._validate_count(dinner_customers or 0)
            amount = lunch_sales + dinner_sales
        else:
            amount = self._validate_amount(amount)
        records = self._data_manager.data.setdefault("business_sales", [])
        record = next((item for item in records if item.get("date") == record_date), None)
        if record is None:
            record = {"id": uuid4().hex, "date": record_date, "amount": amount}
            records.append(record)
        else:
            record["amount"] = amount
        if split_entry:
            record.update({
                "lunch_sales": lunch_sales,
                "dinner_sales": dinner_sales,
                "lunch_customers": lunch_customers,
                "dinner_customers": dinner_customers,
            })
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

    def monthly_sales_summary(self, month):
        records = self.sales_records(month=month)
        result = {
            "total": sum(int(item.get("amount", 0)) for item in records),
            "lunch_sales": sum(int(item.get("lunch_sales", 0)) for item in records),
            "dinner_sales": sum(int(item.get("dinner_sales", 0)) for item in records),
            "lunch_customers": sum(int(item.get("lunch_customers", 0)) for item in records),
            "dinner_customers": sum(int(item.get("dinner_customers", 0)) for item in records),
        }
        result["lunch_spend"] = (
            round(result["lunch_sales"] / result["lunch_customers"])
            if result["lunch_customers"] else 0
        )
        result["dinner_spend"] = (
            round(result["dinner_sales"] / result["dinner_customers"])
            if result["dinner_customers"] else 0
        )
        return result

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

    @staticmethod
    def _validate_count(value):
        try:
            numeric = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError("人数を0人以上の整数で入力してください。") from error
        if numeric < 0 or not numeric.is_integer():
            raise ValueError("人数を0人以上の整数で入力してください。")
        return int(numeric)


from core.data import data  # noqa: E402


financials = FinancialManager(data)
