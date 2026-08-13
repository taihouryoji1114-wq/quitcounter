"""Action-oriented management consulting for Future Financials."""

from __future__ import annotations

from datetime import date

from core.annual_reports import annual_reports
from core.data import data
from core.financials import financials
from core.purchases import purchases


class ConsultingManager:
    VALID_STATUSES = {"not_started", "in_progress", "completed"}

    def __init__(self, data_manager=None):
        self._data_manager = data_manager or data

    def diagnose(self, month):
        sales = financials.monthly_sales_total(month)
        cost = purchases.monthly_total(month, kind="cost")
        supplies = purchases.monthly_total(month, kind="operating_supply")
        expenses = purchases.monthly_total(month, kind="expense")
        fees = financials.monthly_payment_summary(month)["total_fees"]
        ads = financials.get_monthly_advertising(month)["total"]
        operations = financials.get_monthly_operations(month)
        gross = sales - cost
        operating_cost = sum((
            operations["personnel"], operations["rent"], operations["utilities"],
            operations["other_admin"], supplies, expenses, fees, ads,
        ))
        operating_profit = gross - operating_cost
        cost_rate = cost / sales if sales else None
        personnel_rate = operations["personnel"] / sales if sales else None

        annual_periods = annual_reports.list_periods()
        annual = annual_reports.get_report(annual_periods[0]) if annual_periods else None
        annual_result = annual_reports.calculate(annual["current"]) if annual else None
        recommendations = []

        def add(key, level, title, why, action, target, deadline):
            recommendations.append({
                "key": key, "level": level, "title": title, "why": why,
                "action": action, "target": target, "deadline": deadline,
            })

        if annual_result and annual_result["balance_gap"]:
            add("balance", 100, "決算入力を確定する",
                f"貸借差額が {abs(annual_result['balance_gap']):,}円あり、財務判断を確定できません。",
                "決算書の資産合計と負債・純資産合計を照合する",
                "貸借差額を0円にする", "今週")
        elif annual_result:
            working_capital = annual_result["current_assets"] - annual_result["current_liabilities"]
            if working_capital < 0:
                add("cash_defense", 95, "資金ショートを防ぐ",
                    f"短期資金が {abs(working_capital):,}円不足し、流動比率は {(annual_result['current_ratio'] or 0) * 100:.1f}%です。",
                    "今後12か月の入金・仕入支払・税金・返済を月別に並べ、不足月の前に金融機関へ借換えや返済条件を相談する",
                    "12か月資金繰り表を完成", "7日以内")
            if annual_result["equity"] < 0:
                add("negative_equity", 90, "債務超過の解消計画を作る",
                    f"純資産がマイナス {abs(annual_result['equity']):,}円です。単月黒字だけでなく累積赤字の解消が必要です。",
                    "年間の黒字目標を決め、債務超過額を年間黒字目標で割って解消年数を設定する",
                    "解消年数と年間黒字目標を決定", "今月中")
            debt = int(annual["current"].get("short_term_loans", 0) or 0) + int(
                annual["current"].get("long_term_loans", 0) or 0
            )
            if debt and annual_result["ordinary_profit"] <= 0:
                add("debt", 85, "借入返済を利益と分けて管理する",
                    f"借入残高は {debt:,}円で、経常利益がプラスでないため返済年数を算定できません。",
                    "年間元金返済額を確認し、本業黒字化に必要な利益と返済後に必要な現金を別々に設定する",
                    "年間返済額と必要利益を確定", "今月中")

        if sales <= 0:
            add("sales_input", 80, "月次実績を入力する", "売上が未入力のため、利益改善の優先順位を判定できません。",
                "売上・仕入れ・人件費・主要固定費を入力する", "今月の暫定利益を表示", "今日")
        else:
            if operating_profit < 0:
                add("profit", 75, "月次営業赤字を止める",
                    f"入力済み実績では営業赤字が {abs(operating_profit):,}円です。",
                    "赤字額を原価・人件費・固定費の3つに分け、最も実行しやすい改善から着手する",
                    f"月間 {abs(operating_profit):,}円以上改善", "次の30日")
            if cost_rate is not None and cost_rate > .36:
                gap = max(0, cost - round(sales * .36))
                add("cost", 60, "原価を改善する", f"原価率は {cost_rate * 100:.1f}%で、日本料理店の参考36%を上回ります。",
                    "高原価商品の値上げ、仕入単価、廃棄量を順に確認する", f"月間 {gap:,}円改善を検討", "次の30日")
            if personnel_rate is not None and personnel_rate > .33:
                gap = max(0, operations["personnel"] - round(sales * .33))
                add("personnel", 55, "人件費の使い方を見直す", f"人件費率は {personnel_rate * 100:.1f}%で、日本料理店の参考33%を上回ります。",
                    "時間帯別売上とシフトを照合し、売上の薄い時間から配置を調整する", f"月間 {gap:,}円改善を検討", "次のシフト作成時")

        if not recommendations:
            add("growth", 20, "小さく成長投資を試す", "重大な財務警告と月次赤字が見当たりません。",
                "広告・採用・設備の候補を、投資上限と回収期限を決めて1つだけ試す", "投資回収期限を事前設定", "今月中")

        stored = self.get_review(month)
        for item in recommendations:
            saved = stored.get("items", {}).get(item["key"], {})
            item["status"] = saved.get("status", "not_started")
            item["note"] = saved.get("note", "")
        recommendations.sort(key=lambda item: item["level"], reverse=True)
        return {
            "month": month, "recommendations": recommendations,
            "primary": recommendations[0], "sales": sales,
            "operating_profit": operating_profit,
        }

    def get_review(self, month):
        value = self._data_manager.data.get("business_consulting_reviews", {}).get(month, {})
        return value if isinstance(value, dict) else {}

    def save_item(self, month, key, status, note=""):
        if status not in self.VALID_STATUSES:
            raise ValueError("進捗状態が正しくありません。")
        reviews = self._data_manager.data.setdefault("business_consulting_reviews", {})
        review = reviews.setdefault(month, {"items": {}})
        review.setdefault("items", {})[key] = {
            "status": status, "note": str(note or "").strip()[:500],
            "updated_at": date.today().isoformat(),
        }
        self._data_manager.save()
        return review["items"][key]


consulting = ConsultingManager()
