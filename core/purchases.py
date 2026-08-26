"""Persistent supplier purchase records shared with financial planning."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, ROUND_HALF_UP
import unicodedata
from uuid import uuid4


class PurchaseManager:
    def __init__(self, data_manager):
        self._data_manager = data_manager

    def records(self, month=None, record_date=None, kind=None):
        records = self._data_manager.data.get("business_purchases", [])
        if month:
            records = [item for item in records if item.get("date", "").startswith(month)]
        if record_date:
            records = [item for item in records if item.get("date") == record_date]
        if kind:
            records = [
                item for item in records
                if item.get("kind", "cost") == kind
            ]
        return sorted(records, key=lambda item: (item["date"], item["id"]), reverse=True)

    def add(
        self,
        record_date,
        supplier,
        total,
        kind="cost",
        tax_breakdown=None,
        invoice_status="unknown",
    ):
        self._validate_date(record_date)
        supplier = str(supplier or "").strip()
        if not supplier:
            raise ValueError("仕入れ先を入力してください。")
        total = self._validate_total(total)
        if kind not in {"cost", "operating_supply", "expense"}:
            raise ValueError("支出の区分を選択してください。")
        if invoice_status not in {"registered", "unregistered", "unknown"}:
            raise ValueError("インボイスの区分を選択してください。")
        record = {
            "id": uuid4().hex,
            "date": record_date,
            "supplier": supplier,
            "total": total,
            "kind": kind,
            "invoice_status": invoice_status,
        }
        if tax_breakdown:
            record["tax_breakdown"] = self._validate_tax_breakdown(
                tax_breakdown, total
            )
        self._data_manager.data.setdefault("business_purchases", []).append(record)
        hidden = self._data_manager.data.get("business_hidden_suppliers", [])
        if supplier in hidden:
            hidden.remove(supplier)
        self._data_manager.save()
        return record

    def calculate_tax_breakdown(
        self,
        amount_8=0,
        amount_10=0,
        exempt=0,
        price_mode="excluded",
        rounding="floor",
        stated_tax_8=None,
        stated_tax_10=None,
        amount_1=0,
        stated_tax_1=None,
    ):
        """Calculate one invoice's tax once per rate, as required for invoices."""
        if price_mode not in {"included", "excluded"}:
            raise ValueError("税込・税抜を選択してください。")
        if rounding not in {"floor", "half_up", "ceil"}:
            raise ValueError("端数処理を選択してください。")
        amount_8 = self._validate_nonnegative(amount_8, "8％対象額")
        amount_10 = self._validate_nonnegative(amount_10, "10％対象額")
        amount_1 = self._validate_nonnegative(amount_1, "1％対象額")
        exempt = self._validate_nonnegative(exempt, "非課税・対象外額")
        if amount_1 + amount_8 + amount_10 + exempt <= 0:
            raise ValueError("税率別の金額を1円以上入力してください。")

        if price_mode == "excluded":
            calculated_1 = self._round_tax(Decimal(amount_1) * Decimal("0.01"), rounding)
            calculated_8 = self._round_tax(Decimal(amount_8) * Decimal("0.08"), rounding)
            calculated_10 = self._round_tax(Decimal(amount_10) * Decimal("0.10"), rounding)
        else:
            calculated_1 = self._round_tax(
                Decimal(amount_1) * Decimal(1) / Decimal(101), rounding
            )
            calculated_8 = self._round_tax(
                Decimal(amount_8) * Decimal(8) / Decimal(108), rounding
            )
            calculated_10 = self._round_tax(
                Decimal(amount_10) * Decimal(10) / Decimal(110), rounding
            )

        tax_1 = self._optional_tax(stated_tax_1, calculated_1, "1％の消費税")
        tax_8 = self._optional_tax(stated_tax_8, calculated_8, "8％の消費税")
        tax_10 = self._optional_tax(stated_tax_10, calculated_10, "10％の消費税")
        total = amount_1 + amount_8 + amount_10 + exempt
        if price_mode == "excluded":
            total += tax_1 + tax_8 + tax_10
        return {
            "price_mode": price_mode,
            "rounding": rounding,
            "amount_1": amount_1,
            "amount_8": amount_8,
            "amount_10": amount_10,
            "exempt": exempt,
            "tax_1": tax_1,
            "tax_8": tax_8,
            "tax_10": tax_10,
            "total": total,
        }

    @staticmethod
    def sum_amount_expression(value):
        """Sum a simple plus-separated list such as ``1,200+350+980``."""
        normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
        if not normalized:
            return 0
        parts = normalized.split("+")
        if any(not part.replace(",", "").strip().isdigit() for part in parts):
            raise ValueError("金額は『1200+350+980』のように入力してください。")
        return sum(int(part.replace(",", "").strip()) for part in parts)

    def delete(self, record_id):
        records = self._data_manager.data.get("business_purchases", [])
        record = next((item for item in records if item.get("id") == record_id), None)
        if record is None:
            raise ValueError("削除する仕入れ記録が見つかりません。")
        records.remove(record)
        self._data_manager.save()
        return record

    def update(
        self,
        record_id,
        record_date,
        supplier,
        total,
        kind="cost",
        tax_breakdown=None,
        invoice_status="unknown",
    ):
        records = self._data_manager.data.get("business_purchases", [])
        record = next((item for item in records if item.get("id") == record_id), None)
        if record is None:
            raise ValueError("編集する仕入れ記録が見つかりません。")
        self._validate_date(record_date)
        supplier = str(supplier or "").strip()
        if not supplier:
            raise ValueError("仕入れ先を入力してください。")
        total = self._validate_total(total)
        if kind not in {"cost", "operating_supply", "expense"}:
            raise ValueError("支出の区分を選択してください。")
        if invoice_status not in {"registered", "unregistered", "unknown"}:
            raise ValueError("インボイスの区分を選択してください。")
        record.update({
            "date": record_date,
            "supplier": supplier,
            "total": total,
            "kind": kind,
            "invoice_status": invoice_status,
        })
        if tax_breakdown:
            record["tax_breakdown"] = self._validate_tax_breakdown(
                tax_breakdown, total
            )
        else:
            record.pop("tax_breakdown", None)
        self._data_manager.save()
        return record

    def migrate_kojiro_tax_20260810(self):
        """Correct the known ¥3,860 inclusive-tax Kojiro invoice once."""
        migration_key = "kojiro_3860_tax_350_20260810"
        completed = self._data_manager.data.setdefault("business_migrations", [])
        if migration_key in completed:
            return 0
        changed = 0
        for record in self._data_manager.data.get("business_purchases", []):
            if record.get("supplier") != "小次郎" or int(record.get("total", 0)) != 3860:
                continue
            record["tax_breakdown"] = {
                "price_mode": "included",
                "rounding": "floor",
                "amount_8": 0,
                "amount_10": 3860,
                "exempt": 0,
                "tax_8": 0,
                "tax_10": 350,
                "total": 3860,
            }
            changed += 1
        completed.append(migration_key)
        self._data_manager.save()
        return changed

    def repair_zero_tax_breakdowns_20260826(self):
        """Repair taxable amounts whose calculated tax was overwritten by a blank UI value.

        Some number inputs can submit an empty optional tax field as numeric zero.  Older
        records affected by that behaviour have a positive taxable amount but zero tax.
        """
        migration_key = "repair_zero_tax_breakdowns_20260826"
        completed = self._data_manager.data.setdefault("business_migrations", [])
        if migration_key in completed:
            return 0
        changed = 0
        for record in self._data_manager.data.get("business_purchases", []):
            breakdown = record.get("tax_breakdown")
            if not isinstance(breakdown, dict):
                continue
            rates_to_repair = [
                rate for rate in (1, 8, 10)
                if int(breakdown.get(f"amount_{rate}", 0) or 0) > 0
                and int(breakdown.get(f"tax_{rate}", 0) or 0) == 0
            ]
            if not rates_to_repair:
                continue
            repaired = self.calculate_tax_breakdown(
                amount_1=breakdown.get("amount_1", 0),
                amount_8=breakdown.get("amount_8", 0),
                amount_10=breakdown.get("amount_10", 0),
                exempt=breakdown.get("exempt", 0),
                price_mode=breakdown.get("price_mode", "included"),
                rounding=breakdown.get("rounding", "floor"),
                stated_tax_1=(
                    breakdown.get("tax_1") if 1 not in rates_to_repair else None
                ),
                stated_tax_8=(
                    breakdown.get("tax_8") if 8 not in rates_to_repair else None
                ),
                stated_tax_10=(
                    breakdown.get("tax_10") if 10 not in rates_to_repair else None
                ),
            )
            record["tax_breakdown"] = repaired
            record["total"] = repaired["total"]
            changed += 1
        completed.append(migration_key)
        self._data_manager.save()
        return changed

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

    def daily_total(self, record_date, kind=None):
        self._validate_date(record_date)
        return sum(
            int(item.get("total", 0))
            for item in self.records(kind=kind)
            if item.get("date") == record_date
        )

    def monthly_total(self, month, kind=None):
        try:
            datetime.strptime(month, "%Y-%m")
        except (TypeError, ValueError) as error:
            raise ValueError("月は YYYY-MM 形式で指定してください。") from error
        return sum(
            int(item.get("total", 0))
            for item in self.records(month=month, kind=kind)
        )

    def monthly_tax_summary(self, month):
        """Return invoice-based input tax, estimating only legacy simple records."""
        try:
            datetime.strptime(month, "%Y-%m")
        except (TypeError, ValueError) as error:
            raise ValueError("月は YYYY-MM 形式で指定してください。") from error
        result = {
            "tax_1": 0,
            "tax_8": 0,
            "tax_10": 0,
            "input_tax": 0,
            "estimated_records": 0,
            "excluded_unregistered_records": 0,
        }
        for record in self.records(month=month):
            if record.get("invoice_status") == "unregistered":
                result["excluded_unregistered_records"] += 1
                continue
            breakdown = record.get("tax_breakdown")
            if breakdown:
                result["tax_1"] += int(breakdown.get("tax_1", 0))
                result["tax_8"] += int(breakdown.get("tax_8", 0))
                result["tax_10"] += int(breakdown.get("tax_10", 0))
                continue
            total = int(record.get("total", 0))
            if record.get("kind", "cost") == "cost":
                result["tax_8"] += self._round_tax(
                    Decimal(total) * Decimal(8) / Decimal(108), "floor"
                )
            else:
                result["tax_10"] += self._round_tax(
                    Decimal(total) * Decimal(10) / Decimal(110), "floor"
                )
            result["estimated_records"] += 1
        result["input_tax"] = (
            result["tax_1"] + result["tax_8"] + result["tax_10"]
        )
        return result

    @staticmethod
    def _validate_date(value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError("日付を選択してください。") from error

    @staticmethod
    def _validate_total(value):
        try:
            numeric = float(
                unicodedata.normalize("NFKC", str(value)).replace(",", "").strip()
            )
        except (TypeError, ValueError) as error:
            raise ValueError("合計金額を1円以上で入力してください。") from error
        if numeric <= 0 or not numeric.is_integer():
            raise ValueError("合計金額を1円以上の整数で入力してください。")
        return int(numeric)

    @staticmethod
    def _validate_nonnegative(value, label):
        if value in (None, ""):
            return 0
        try:
            numeric = float(
                unicodedata.normalize("NFKC", str(value)).replace(",", "").strip()
            )
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label}は0円以上の整数で入力してください。") from error
        if numeric < 0 or not numeric.is_integer():
            raise ValueError(f"{label}は0円以上の整数で入力してください。")
        return int(numeric)

    @staticmethod
    def _round_tax(value, rounding):
        modes = {
            "floor": ROUND_DOWN,
            "half_up": ROUND_HALF_UP,
            "ceil": ROUND_CEILING,
        }
        return int(value.quantize(Decimal("1"), rounding=modes[rounding]))

    def _optional_tax(self, value, calculated, label):
        # NiceGUI may serialize an untouched optional number field as 0.  A positive
        # taxable amount cannot legitimately have zero consumption tax, so retain
        # the automatic calculation instead of silently overwriting it.
        if value in (None, "", 0, 0.0, "0") and calculated > 0:
            return calculated
        return self._validate_nonnegative(value, label)

    @staticmethod
    def _validate_tax_breakdown(breakdown, total):
        required = {
            "price_mode", "rounding", "amount_8", "amount_10", "exempt",
            "tax_8", "tax_10", "total",
        }
        if not isinstance(breakdown, dict) or not required.issubset(breakdown):
            raise ValueError("消費税の内訳が正しくありません。")
        if int(breakdown["total"]) != total:
            raise ValueError("消費税の計算結果と合計金額が一致しません。")
        result = {key: breakdown[key] for key in required}
        result["amount_1"] = breakdown.get("amount_1", 0)
        result["tax_1"] = breakdown.get("tax_1", 0)
        return result


from core.data import data  # noqa: E402


purchases = PurchaseManager(data)
purchases.migrate_kojiro_tax_20260810()
purchases.repair_zero_tax_breakdowns_20260826()
