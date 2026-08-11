"""Persistent daily business figures for the Future Financials app."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4


class FinancialManager:
    PAYMENT_FIELDS = (
        "cash_sales", "credit_sales", "paypay_sales",
        "electronic_money_sales", "travel_agency_sales", "tabelog_points_sales",
        "hotpepper_points_sales",
    )
    FEE_RATE_FIELDS = (
        "credit", "paypay", "electronic_money", "travel_agency",
    )
    PLAN_FIELDS = {
        "sales", "cogs", "cogs-rate", "cogs-mode", "personnel",
        "personnel-rate", "personnel-mode", "rent", "utilities",
        "advertising", "other-expenses", "non-op-income",
        "non-op-expense", "target-profit", "tax-method",
        "corporate-tax-rate", "loan-payment", "investment",
        "personnel-plan-basis", "linkage-version",
    }

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
        cash_sales=None,
        credit_sales=None,
        paypay_sales=None,
        electronic_money_sales=None,
        travel_agency_sales=None,
        tabelog_points_sales=None,
        hotpepper_points_sales=None,
    ):
        self._validate_date(record_date)
        split_entry = any(
            value not in (None, "")
            for value in (lunch_sales, dinner_sales, lunch_customers, dinner_customers)
        )
        payment_values = {
            "cash_sales": cash_sales,
            "credit_sales": credit_sales,
            "paypay_sales": paypay_sales,
            "electronic_money_sales": electronic_money_sales,
            "travel_agency_sales": travel_agency_sales,
            "tabelog_points_sales": tabelog_points_sales,
            "hotpepper_points_sales": hotpepper_points_sales,
        }
        payment_entry = any(
            value not in (None, "") for value in payment_values.values()
        )
        if payment_entry:
            payment_values = {
                key: self._validate_amount(value or 0)
                for key, value in payment_values.items()
            }
            payment_total = sum(payment_values.values())
        else:
            payment_total = None
        if split_entry:
            lunch_sales = self._validate_amount(lunch_sales or 0)
            dinner_sales = self._validate_amount(dinner_sales or 0)
            lunch_customers_entered = lunch_customers not in (None, "")
            dinner_customers_entered = dinner_customers not in (None, "")
            lunch_customers = (
                self._validate_count(lunch_customers) if lunch_customers_entered else None
            )
            dinner_customers = (
                self._validate_count(dinner_customers) if dinner_customers_entered else None
            )
            amount = lunch_sales + dinner_sales
        else:
            amount = payment_total if payment_entry else self._validate_amount(amount)
        if payment_total is not None:
            if amount and payment_total != amount:
                raise ValueError(
                    "ランチ・ディナーの売上合計と、決済方法別の合計が一致しません。"
                )
            amount = payment_total
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
            })
            for field, value in (
                ("lunch_customers", lunch_customers),
                ("dinner_customers", dinner_customers),
            ):
                if value is None:
                    record.pop(field, None)
                else:
                    record[field] = value
        else:
            for field in (
                "lunch_sales", "dinner_sales", "lunch_customers",
                "dinner_customers",
            ):
                record.pop(field, None)
        if payment_entry:
            record.update(payment_values)
        self._data_manager.save()
        return record

    def get_payment_fee_rates(self):
        stored = self._data_manager.data.get("business_payment_fee_rates", {})
        return {
            key: float(stored.get(key, 0))
            for key in self.FEE_RATE_FIELDS
        }

    def save_payment_fee_rates(self, rates):
        if not isinstance(rates, dict):
            raise ValueError("決済手数料率の形式が正しくありません。")
        cleaned = {}
        for key in self.FEE_RATE_FIELDS:
            try:
                value = float(rates.get(key, 0) or 0)
            except (TypeError, ValueError) as error:
                raise ValueError("決済手数料率は0〜100％で入力してください。") from error
            if value < 0 or value > 100:
                raise ValueError("決済手数料率は0〜100％で入力してください。")
            cleaned[key] = round(value, 4)
        self._data_manager.data["business_payment_fee_rates"] = cleaned
        self._data_manager.save()
        return dict(cleaned)

    def get_monthly_advertising(self, month):
        self._validate_month(month)
        stored = self._data_manager.data.get("business_monthly_advertising", {})
        values = stored.get(month, {}) if isinstance(stored, dict) else {}
        result = {
            key: int(values.get(key, 0))
            for key in ("tabelog", "hotpepper", "other")
        }
        result["total"] = sum(result.values())
        result["input_tax"] = sum(
            result[key] * 10 // 110 for key in ("tabelog", "hotpepper", "other")
        )
        return result

    def save_monthly_advertising(self, month, tabelog=0, hotpepper=0, other=0):
        self._validate_month(month)
        cleaned = {
            "tabelog": self._validate_amount(tabelog or 0),
            "hotpepper": self._validate_amount(hotpepper or 0),
            "other": self._validate_amount(other or 0),
        }
        self._data_manager.data.setdefault("business_monthly_advertising", {})[
            month
        ] = cleaned
        self._data_manager.save()
        return self.get_monthly_advertising(month)

    def monthly_payment_summary(self, month):
        records = self.sales_records(month=month)
        totals = {
            field: sum(int(item.get(field, 0)) for item in records)
            for field in self.PAYMENT_FIELDS
        }
        classified = sum(totals.values())
        totals["unclassified_sales"] = max(
            0, sum(int(item.get("amount", 0)) for item in records) - classified
        )
        rates = self.get_payment_fee_rates()
        fees = {
            "credit": round(totals["credit_sales"] * rates["credit"] / 100),
            "paypay": round(totals["paypay_sales"] * rates["paypay"] / 100),
            "electronic_money": round(
                totals["electronic_money_sales"] * rates["electronic_money"] / 100
            ),
            "travel_agency": round(
                totals["travel_agency_sales"] * rates["travel_agency"] / 100
            ),
        }
        totals["fees"] = fees
        totals["total_fees"] = sum(fees.values())
        return totals

    def sales_completion_status(self, record_date):
        records = self.sales_records(record_date=record_date)
        if not records:
            return "missing"
        record = records[0]
        lunch_complete = "lunch_sales" in record
        dinner_complete = all(
            key in record for key in ("dinner_sales", "dinner_customers")
        )
        payment_complete = (
            any(key in record for key in self.PAYMENT_FIELDS)
            and sum(int(record.get(key, 0)) for key in self.PAYMENT_FIELDS)
            == int(record.get("amount", 0))
        )
        return (
            "complete"
            if all((lunch_complete, dinner_complete, payment_complete))
            else "partial"
        )

    def get_plan(self):
        plan = self._data_manager.data.get("business_plan", {})
        return dict(plan) if isinstance(plan, dict) else {}

    def save_plan(self, plan):
        if not isinstance(plan, dict):
            raise ValueError("月間計画の形式が正しくありません。")
        cleaned = {
            key: value for key, value in plan.items()
            if key in self.PLAN_FIELDS and isinstance(value, (str, int, float))
        }
        self._data_manager.data["business_plan"] = cleaned
        self._data_manager.save()
        return dict(cleaned)

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
