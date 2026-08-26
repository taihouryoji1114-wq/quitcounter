"""Read-only integrity checks for daily Future Financials inputs."""

from __future__ import annotations

from calendar import monthrange
from collections import Counter
from datetime import date, datetime
from statistics import median


class BusinessAuditManager:
    PAYMENT_FIELDS = (
        "cash_sales", "credit_sales", "paypay_sales", "electronic_money_sales",
        "travel_agency_sales", "tabelog_points_sales", "hotpepper_points_sales",
    )

    def __init__(self, data_manager):
        self._data_manager = data_manager

    def inspect(self, month, through_date=None):
        parsed = datetime.strptime(str(month), "%Y-%m")
        through = through_date or date.today()
        if isinstance(through, str):
            through = datetime.strptime(through, "%Y-%m-%d").date()
        days = monthrange(parsed.year, parsed.month)[1]
        if (parsed.year, parsed.month) < (through.year, through.month):
            last_day = days
        elif (parsed.year, parsed.month) > (through.year, through.month):
            last_day = 0
        else:
            last_day = min(through.day, days)

        issues = []

        def add(level, area, title, detail, record_date="", path=""):
            issues.append({
                "level": level, "area": area, "title": title, "detail": detail,
                "date": record_date, "path": path,
            })

        monthly_operations = self._data_manager.data.get(
            "business_monthly_operations", {}
        )
        if not isinstance(monthly_operations, dict) or month not in monthly_operations:
            add(
                "missing", "月次費用", "月次費用がまだ保存されていません",
                "家賃・水道光熱費・その他管理費・借入元金返済を確認してください。",
                path=f"/mirai-kessan/month/{month}",
            )
        monthly_advertising = self._data_manager.data.get(
            "business_monthly_advertising", {}
        )
        if not isinstance(monthly_advertising, dict) or month not in monthly_advertising:
            add(
                "missing", "月次費用", "広告費がまだ保存されていません",
                "食べログ・ホットペッパー・その他広告費を確認してください。",
                path=f"/mirai-kessan/month/{month}",
            )

        sales = [row for row in self._data_manager.data.get("business_sales", [])
                 if str(row.get("date", "")).startswith(month)]
        sales_dates = Counter(str(row.get("date", "")) for row in sales)
        for record_date, count in sales_dates.items():
            if count > 1:
                add("danger", "売上", "同じ日の売上が重複しています",
                    f"{count}件あります。日別売上は1日1件にまとめます。", record_date,
                    f"/mirai-kessan/sales?date={record_date}")
        entered = {value for value in sales_dates if value}
        for day_number in range(1, last_day + 1):
            record_date = f"{month}-{day_number:02d}"
            if record_date not in entered:
                add("missing", "売上", "売上が未入力です",
                    "休業日でなければ入力してください。", record_date,
                    f"/mirai-kessan/sales?date={record_date}")

        positive_sales = [int(row.get("amount", 0) or 0) for row in sales
                          if int(row.get("amount", 0) or 0) > 0]
        typical_sales = median(positive_sales) if len(positive_sales) >= 3 else None
        for row in sales:
            record_date = str(row.get("date", ""))
            amount = int(row.get("amount", 0) or 0)
            if amount <= 0:
                add("danger", "売上", "売上が0円です", "入力途中または打ち間違いの可能性があります。",
                    record_date, f"/mirai-kessan/sales?date={record_date}")
            split_present = any(key in row for key in ("lunch_sales", "dinner_sales"))
            if split_present:
                split_total = int(row.get("lunch_sales", 0) or 0) + int(row.get("dinner_sales", 0) or 0)
                if split_total != amount:
                    add("danger", "売上", "ランチ・ディナー合計が売上と一致しません",
                        f"売上 {amount:,}円／時間帯合計 {split_total:,}円", record_date,
                        f"/mirai-kessan/sales?date={record_date}")
            payment_present = any(key in row for key in self.PAYMENT_FIELDS)
            if payment_present:
                payment_total = sum(int(row.get(key, 0) or 0) for key in self.PAYMENT_FIELDS)
                if payment_total != amount:
                    add("danger", "売上", "決済内訳が売上と一致しません",
                        f"売上 {amount:,}円／決済内訳 {payment_total:,}円", record_date,
                        f"/mirai-kessan/sales?date={record_date}")
            if typical_sales and amount > typical_sales * 2.5:
                add("warning", "売上", "通常よりかなり大きい売上です",
                    f"今月の入力中央値 {int(typical_sales):,}円に対して {amount:,}円です。",
                    record_date, f"/mirai-kessan/sales?date={record_date}")

        purchase_rows = [row for row in self._data_manager.data.get("business_purchases", [])
                         if str(row.get("date", "")).startswith(month)]
        purchase_keys = Counter((str(row.get("date", "")), str(row.get("supplier", "")).strip(),
                                 int(row.get("total", 0) or 0), row.get("kind", "cost"))
                                for row in purchase_rows)
        for (record_date, supplier, total, _), count in purchase_keys.items():
            if count > 1:
                add("warning", "仕入れ", "同じ仕入れが重複している可能性があります",
                    f"{supplier or '仕入れ先未入力'}・{total:,}円が{count}件あります。",
                    record_date, f"/mirai-kessan/shiire?date={record_date}")
        for row in purchase_rows:
            record_date = str(row.get("date", ""))
            total = int(row.get("total", 0) or 0)
            if not str(row.get("supplier", "")).strip():
                add("danger", "仕入れ", "仕入れ先が空欄です", "仕入れ先を入力してください。",
                    record_date, f"/mirai-kessan/shiire?date={record_date}")
            if total <= 0:
                add("danger", "仕入れ", "金額が0円以下です", "金額を確認してください。",
                    record_date, f"/mirai-kessan/shiire?date={record_date}")
            breakdown = row.get("tax_breakdown")
            if isinstance(breakdown, dict) and int(breakdown.get("total", 0) or 0) != total:
                add("danger", "仕入れ", "税率別合計と仕入合計が一致しません",
                    f"仕入合計 {total:,}円／税率別合計 {int(breakdown.get('total', 0) or 0):,}円",
                    record_date, f"/mirai-kessan/shiire?date={record_date}")

        hours = self._data_manager.data.get("business_staff_hours", {})
        for record_date, staff_rows in hours.items():
            if not str(record_date).startswith(month) or not isinstance(staff_rows, dict):
                continue
            for staff_name, shift in staff_rows.items():
                if not isinstance(shift, dict):
                    continue
                for label, start_key, end_key in (
                    ("ランチ", "lunch_start", "lunch_end"),
                    ("ディナー", "dinner_start", "dinner_end"),
                ):
                    start, end = str(shift.get(start_key, "") or ""), str(shift.get(end_key, "") or "")
                    if bool(start) != bool(end):
                        add("danger", "人件費", f"{staff_name}の{label}時刻が片方だけです",
                            "開始と終了を両方入力してください。", str(record_date),
                            f"/mirai-kessan/staffing?date={record_date}")

        priority = {"danger": 0, "warning": 1, "missing": 2}
        issues.sort(key=lambda item: (priority[item["level"]], item["date"], item["area"]))
        counts = Counter(item["level"] for item in issues)
        checked = len(sales) + len(purchase_rows) + sum(
            len(value) for key, value in hours.items()
            if str(key).startswith(month) and isinstance(value, dict)
        )
        return {
            "month": month, "checked_records": checked, "issues": issues,
            "danger": counts["danger"], "warning": counts["warning"],
            "missing": counts["missing"], "ok": not issues,
        }
