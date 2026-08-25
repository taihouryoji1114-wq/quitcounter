"""Shared calculations for the on-screen, printed, and downloaded reports."""

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta

from core.clock import today_jst
from core.financials import financials
from core.purchases import purchases
from core.staffing import staffing


PAYMENT_COLUMNS = (
    ("現金", "cash_sales"), ("クレジット", "credit_sales"),
    ("PayPay", "paypay_sales"), ("電子マネー", "electronic_money_sales"),
    ("旅行社", "travel_agency_sales"),
)


def build_financial_report(start, end):
    start_day, end_day = date.fromisoformat(start), date.fromisoformat(end)
    sales = [row for row in financials.sales_records()
             if start <= str(row.get("date", "")) <= end]
    purchase_rows = [row for row in purchases.records()
                     if start <= str(row.get("date", "")) <= end]
    suppliers = defaultdict(lambda: {
        "count": 0, "cost": 0, "supply": 0, "expense": 0, "total": 0})
    for row in purchase_rows:
        amount = int(row.get("total", 0) or 0)
        values = suppliers[str(row.get("supplier") or "仕入れ先未入力")]
        values["count"] += 1
        values["total"] += amount
        values[{"cost": "cost", "operating_supply": "supply",
                "expense": "expense"}.get(row.get("kind", "cost"), "expense")] += amount

    sales_total = sum(int(row.get("amount", 0) or 0) for row in sales)
    cost_total = sum(int(row.get("total", 0) or 0) for row in purchase_rows
                     if row.get("kind", "cost") == "cost")
    supply_total = sum(int(row.get("total", 0) or 0) for row in purchase_rows
                       if row.get("kind") == "operating_supply")
    expense_total = sum(int(row.get("total", 0) or 0) for row in purchase_rows
                        if row.get("kind") == "expense")
    allocated = _allocated_monthly_costs(start_day, end_day)
    payment_totals = {field: sum(int(row.get(field, 0) or 0) for row in sales)
                      for _, field in PAYMENT_COLUMNS}
    payment_totals["points_sales"] = sum(
        int(row.get("tabelog_points_sales", 0) or 0)
        + int(row.get("hotpepper_points_sales", 0) or 0) for row in sales)
    classified_sales = sum(payment_totals.values())
    payment_totals["unclassified_sales"] = max(0, sales_total - classified_sales)
    rates = financials.get_payment_fee_rates()
    rate_fields = {"credit_sales": "credit", "paypay_sales": "paypay",
                   "electronic_money_sales": "electronic_money",
                   "travel_agency_sales": "travel_agency"}
    payment_fees = sum(round(payment_totals.get(field, 0)
                             * rates.get(rate_fields.get(field, ""), 0) / 100)
                       for _, field in PAYMENT_COLUMNS)
    gross_profit = sales_total - cost_total
    operating_expenses = (allocated["personnel"] + allocated["rent"]
                          + allocated["utilities"] + allocated["advertising"]
                          + allocated["other_admin"] + supply_total + expense_total
                          + payment_fees)
    operating_profit = gross_profit - operating_expenses
    expense_breakdown = (
        ("人件費", allocated["personnel"]), ("家賃", allocated["rent"]),
        ("水道光熱費", allocated["utilities"]), ("広告費", allocated["advertising"]),
        ("営業用品", supply_total), ("一般経費", expense_total),
        ("決済手数料", payment_fees), ("その他管理費", allocated["other_admin"]),
    )
    ratios = {
        "cost_rate": cost_total / sales_total if sales_total else None,
        "gross_margin": gross_profit / sales_total if sales_total else None,
        "personnel_rate": allocated["personnel"] / sales_total if sales_total else None,
        "labor_distribution": allocated["personnel"] / gross_profit if gross_profit > 0 else None,
        "operating_margin": operating_profit / sales_total if sales_total else None,
    }
    return {
        "start": start, "end": end, "sales": sales, "purchases": purchase_rows,
        "suppliers": sorted(suppliers.items(), key=lambda pair: pair[1]["total"], reverse=True),
        "payment_totals": payment_totals, "payment_fees": payment_fees,
        "sales_total": sales_total, "cost_total": cost_total,
        "gross_profit": gross_profit, "supply_total": supply_total,
        "expense_total": expense_total, "personnel": allocated["personnel"],
        "rent": allocated["rent"], "utilities": allocated["utilities"],
        "advertising": allocated["advertising"], "other_admin": allocated["other_admin"],
        "operating_expenses": operating_expenses, "operating_profit": operating_profit,
        "expense_breakdown": expense_breakdown, "ratios": ratios,
    }


def _allocated_monthly_costs(start, end):
    result = {key: 0 for key in
              ("personnel", "rent", "utilities", "advertising", "other_admin")}
    cursor = start.replace(day=1)
    today = today_jst()
    while cursor <= end:
        days = monthrange(cursor.year, cursor.month)[1]
        month_end = cursor.replace(day=days)
        selected_start, selected_end = max(start, cursor), min(end, month_end)
        selected_days = max(0, (selected_end - selected_start).days + 1)
        month = cursor.strftime("%Y-%m")
        operations = financials.get_monthly_operations(month)
        advertising = financials.get_monthly_advertising(month)["total"]
        for key in ("rent", "utilities", "other_admin"):
            result[key] += round(operations[key] * selected_days / days)
        result["advertising"] += round(advertising * selected_days / days)
        if cursor < today.replace(day=1):
            month_personnel = staffing.month_cost_summary(month, today)["company_cost"]
            result["personnel"] += round(month_personnel * selected_days / days)
        elif cursor.year == today.year and cursor.month == today.month:
            month_personnel = staffing.month_cost_summary(month, today)["company_cost"]
            effective_end = min(selected_end, today)
            covered = max(0, (effective_end - selected_start).days + 1)
            result["personnel"] += round(month_personnel * covered / max(1, today.day))
        cursor = (month_end.replace(day=28) + timedelta(days=4)).replace(day=1)
    return result
