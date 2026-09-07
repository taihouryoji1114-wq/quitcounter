"""Monthly management evaluation built only from existing Future Financials data."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime


def shift_month(month, amount):
    parsed = datetime.strptime(month, "%Y-%m")
    index = parsed.year * 12 + parsed.month - 1 + amount
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


class MonthlyEvaluationService:
    """Create reproducible evaluations without modifying accounting records."""

    def __init__(self, financial_manager, purchase_manager, staffing_manager):
        self.financials = financial_manager
        self.purchases = purchase_manager
        self.staffing = staffing_manager

    @staticmethod
    def _number(value, default=0):
        try:
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return default

    def completion(self, month, as_of=None):
        sales = self.financials.sales_records(month=month)
        data = self.financials._data_manager.data
        operations = data.get("business_monthly_operations", {})
        missing = []
        year, number = (int(part) for part in month.split("-"))
        today = as_of or date.today()
        if (year, number) > (today.year, today.month) or (
            (year, number) == (today.year, today.month)
            and today.day < monthrange(year, number)[1]
        ):
            missing.append("月末の営業終了")
        if not sales:
            missing.append("売上")
        if not isinstance(operations, dict) or month not in operations:
            missing.append("月次費用")
        return {"ready": not missing, "missing": missing}

    def anomalies(self, preview):
        """Return only material changes, avoiding noisy small warnings."""
        metrics, comparisons, warnings = (
            preview["metrics"], preview["comparisons"], []
        )
        for key, label in (("cost_rate", "原価率"), ("personnel_rate", "人件費率")):
            average = comparisons[key]["average3"]
            value = metrics[key]
            if average is not None and value is not None and value - average >= .03:
                warnings.append(
                    f"{label}が過去3ヶ月平均より{(value-average)*100:.1f}ポイント高い"
                )
        average_margin = comparisons["operating_margin"]["average3"]
        margin = metrics["operating_margin"]
        if average_margin is not None and margin is not None and average_margin - margin >= .03:
            warnings.append(
                f"営業利益率が過去3ヶ月平均より{(average_margin-margin)*100:.1f}ポイント低い"
            )
        average_fixed = comparisons["fixed_costs"]["average3"]
        if average_fixed and metrics["fixed_costs"] > average_fixed * 1.15:
            warnings.append(
                f"固定費が過去3ヶ月平均より{(metrics['fixed_costs']/average_fixed-1)*100:.1f}%増加"
            )
        return warnings[:3]

    def snapshot(self, month, as_of=None):
        as_of = as_of or date.today()
        sales = self.financials.monthly_sales_total(month)
        cost = self.purchases.monthly_total(month, kind="cost")
        supplies = self.purchases.monthly_total(month, kind="operating_supply")
        expenses = self.purchases.monthly_total(month, kind="expense")
        operations = self.financials.get_monthly_operations(month)
        personnel = self.staffing.month_cost_summary(month, as_of)["company_cost"]
        if not personnel:
            personnel = operations["personnel"]
        advertising = self.financials.get_monthly_advertising(month)["total"]
        advertising_input_tax = self.financials.get_monthly_advertising(month)["input_tax"]
        fees = self.financials.monthly_payment_summary(month)["total_fees"]
        fixed_costs = (
            operations["rent"] + operations["utilities"] + advertising
            + operations["other_admin"]
        )
        gross = sales - cost
        operating_expenses = personnel + fixed_costs + supplies + expenses + fees
        operating = gross - operating_expenses
        # Monthly non-operating and corporate-tax actuals are not stored yet.  Do
        # not invent them: ordinary/net profit therefore use the registered scope.
        ordinary = operating
        net = ordinary
        purchase_input_tax = self.purchases.monthly_tax_summary(month)["input_tax"]
        consumption_tax = max(
            0, sales * 10 // 110 - purchase_input_tax - advertising_input_tax
        )
        post_repayment = net - operations["loan_payment"] - consumption_tax
        return {
            "sales": sales, "purchases": cost, "cost_rate": cost / sales if sales else None,
            "gross_profit": gross, "personnel": personnel,
            "personnel_rate": personnel / sales if sales else None,
            "fixed_costs": fixed_costs, "operating_expenses": operating_expenses,
            "operating_profit": operating,
            "operating_margin": operating / sales if sales else None,
            "ordinary_profit": ordinary, "net_profit": net,
            "consumption_tax_estimate": consumption_tax,
            "loan_payment": operations["loan_payment"],
            "post_repayment_profit": post_repayment,
        }

    def history(self, month, count=6, as_of=None):
        rows = []
        for offset in range(-count, 0):
            candidate = shift_month(month, offset)
            snap = self.snapshot(candidate, as_of)
            if snap["sales"]:
                rows.append({"month": candidate, **snap})
        return rows

    def targets(self):
        plan = self.financials.get_plan()
        sales = round(self._number(plan.get("sales")))
        if plan.get("cogs-mode") == "amount" and sales:
            cost_rate = self._number(plan.get("cogs"), sales * .32) / sales
        else:
            cost_rate = self._number(plan.get("cogs-rate"), 32) / 100
        if plan.get("personnel-mode") == "amount" and sales:
            personnel_rate = self._number(plan.get("personnel"), sales * .33) / sales
        else:
            entered_personnel_rate = self._number(plan.get("personnel-rate"), 35) / 100
            # The existing planner stores personnel as a percentage of gross profit.
            personnel_rate = entered_personnel_rate * max(0, 1 - cost_rate)
        profit = round(self._number(plan.get("target-profit")))
        return {
            "sales": sales or None, "cost_rate": cost_rate,
            "personnel_rate": personnel_rate, "operating_profit": profit or None,
        }

    @staticmethod
    def _average(rows, key):
        values = [row[key] for row in rows if row.get(key) is not None]
        return sum(values) / len(values) if values else None

    def preview(self, month, as_of=None):
        current = self.snapshot(month, as_of)
        history = self.history(month, 12, as_of)
        previous = next((row for row in reversed(history) if row["month"] == shift_month(month, -1)), None)
        previous_year = next(
            (row for row in history if row["month"] == shift_month(month, -12)), None
        )
        last3 = history[-3:]
        last6 = history[-6:]
        targets = self.targets()
        comparisons = {}
        for key in (
            "sales", "cost_rate", "personnel_rate", "fixed_costs", "loan_payment",
            "operating_profit", "operating_margin", "post_repayment_profit",
        ):
            comparisons[key] = {
                "previous": previous.get(key) if previous else None,
                "previous_year": previous_year.get(key) if previous_year else None,
                "average3": self._average(last3, key),
                "average6": self._average(last6, key),
                "high12": max(
                    (row[key] for row in history if row.get(key) is not None),
                    default=None,
                ),
                "low12": min(
                    (row[key] for row in history if row.get(key) is not None),
                    default=None,
                ),
            }
        return {
            "month": month, "metrics": current, "targets": targets,
            "comparisons": comparisons, "history_count": len(history),
            "completion": self.completion(month, as_of),
        }

    def forecast(self, month, as_of=None):
        as_of = as_of or date.today()
        year, number = (int(part) for part in month.split("-"))
        if (year, number) != (as_of.year, as_of.month):
            return None
        records = self.financials.sales_records(month=month)
        entered_days = {row["date"] for row in records if int(row.get("amount", 0)) > 0}
        if len(entered_days) < 5:
            return None
        elapsed = max(1, as_of.day)
        days = monthrange(year, number)[1]
        # Use the observed operating-day frequency, not a raw calendar-day run rate.
        expected_open_days = max(len(entered_days), round(days * len(entered_days) / elapsed))
        projected_sales = round(sum(int(row.get("amount", 0)) for row in records) / len(entered_days) * expected_open_days)
        snap = self.snapshot(month, as_of)
        variable_ratio = (
            (snap["purchases"] + self.purchases.monthly_total(month, kind="operating_supply")
             + self.purchases.monthly_total(month, kind="expense")) / snap["sales"]
            if snap["sales"] else 0
        )
        projected_operating = round(
            projected_sales * (1 - variable_ratio)
            - snap["personnel"] - snap["fixed_costs"]
            - self.financials.monthly_payment_summary(month)["total_fees"]
        )
        return {
            "sales": projected_sales, "operating_profit": projected_operating,
            "operating_margin": projected_operating / projected_sales if projected_sales else None,
            "basis": f"売上入力済み{len(entered_days)}営業日を基準",
        }

    def evaluate(self, month, as_of=None):
        preview = self.preview(month, as_of)
        if not preview["completion"]["ready"]:
            raise ValueError("未入力があります：" + "・".join(preview["completion"]["missing"]))
        m, t, c = preview["metrics"], preview["targets"], preview["comparisons"]
        score, good, issues, actions = 70, [], [], []

        def compare_rate(key, label, lower_is_better=True):
            nonlocal score
            value, target = m[key], t[key]
            if value is None:
                return
            gap = (value - target) * 100
            healthy = gap <= 0 if lower_is_better else gap >= 0
            if healthy:
                score += 7
                good.append(f"{label}が目標範囲内（{value*100:.1f}%）")
            elif abs(gap) >= 5:
                score -= 12
                issues.append(f"{label}が目標より{abs(gap):.1f}ポイント高い")
                actions.append(f"{label}を{target*100:.1f}%以下へ近づける")
            else:
                score -= 5
                issues.append(f"{label}が目標を{abs(gap):.1f}ポイント上回る")

        compare_rate("cost_rate", "原価率")
        compare_rate("personnel_rate", "人件費率")
        margin = m["operating_margin"] or 0
        if margin >= .10:
            score += 12; good.append(f"営業利益率を{margin*100:.1f}%確保")
        elif margin >= .05:
            score += 6; good.append(f"営業利益率は{margin*100:.1f}%で黒字")
        elif margin < 0:
            score -= 22; issues.append("営業利益が赤字"); actions.append("まず営業利益の黒字化を優先する")
        else:
            score -= 7; issues.append(f"営業利益率が{margin*100:.1f}%と低い")
        if m["post_repayment_profit"] >= 0:
            score += 8; good.append("借入返済後も利益が残る")
        else:
            score -= 16; issues.append("借入返済後の残額がマイナス"); actions.append("利益と元金返済額のバランスを確認する")
        previous_sales = c["sales"]["previous"]
        previous_profit = c["operating_profit"]["previous"]
        if previous_sales:
            sales_delta = (m["sales"] - previous_sales) / previous_sales
            if sales_delta >= .03:
                score += 4; good.append(f"売上が前月より{sales_delta*100:.1f}%増加")
            elif sales_delta <= -.10:
                score -= 7; issues.append(f"売上が前月より{abs(sales_delta)*100:.1f}%減少")
        if previous_profit is not None and m["operating_profit"] > previous_profit:
            score += 4; good.append("営業利益が前月より改善")
        average_fixed = c["fixed_costs"]["average3"]
        if average_fixed and m["fixed_costs"] > average_fixed * 1.15:
            score -= 6
            issues.append(
                f"固定費が過去3ヶ月平均より{(m['fixed_costs']/average_fixed-1)*100:.1f}%増加"
            )
            actions.append("固定費が増えた要因を確認する")
        if m["loan_payment"] and m["operating_profit"] > 0:
            repayment_burden = m["loan_payment"] / m["operating_profit"]
            if repayment_burden >= .70:
                score -= 6
                issues.append("営業利益に対する返済負担が大きい")
        if t["sales"] and m["sales"] < t["sales"]:
            actions.append(f"売上目標まであと¥{t['sales']-m['sales']:,}を目指す")
        if not actions:
            actions.append("今月の利益構造を維持し、前月との変化を確認する")
        score = max(0, min(100, round(score)))
        rank = "S" if score >= 90 else "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 45 else "D"
        health = "safe" if score >= 80 and m["post_repayment_profit"] >= 0 else "warning" if score >= 55 and m["operating_profit"] >= 0 else "danger"
        if not issues:
            summary = "利益・原価・人件費・返済負担を総合すると、安定した経営状態です。"
        elif m["operating_profit"] >= 0:
            summary = "黒字は確保できていますが、改善余地のある費用項目があります。"
        else:
            summary = "売上だけでなく費用と返済負担を含めると、利益構造の改善が必要です。"
        return {
            **preview, "score": score, "rank": rank, "health": health,
            "summary": summary, "good": good[:4], "issues": issues[:4],
            "actions": actions[:3], "evaluated_at": datetime.now().isoformat(timespec="seconds"),
        }
