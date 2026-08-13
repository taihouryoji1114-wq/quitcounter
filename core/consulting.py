"""Action-oriented management consulting for Future Financials."""

from __future__ import annotations

from datetime import date

from core.annual_reports import annual_reports
from core.data import data
from core.financials import financials
from core.purchases import purchases


class ConsultingManager:
    VALID_STATUSES = {"not_started", "in_progress", "completed"}
    QUESTIONS = (
        ("cash", "資金はいつまで持つ？"),
        ("loss", "赤字をどう解消する？"),
        ("debt", "借入は多すぎる？"),
        ("personnel", "人件費を見直すべき？"),
        ("cost", "原価を下げるべき？"),
        ("sales", "売上をいくら増やせばよい？"),
        ("investment", "新しい投資をしてよい？"),
    )

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

    def answer(self, month, question):
        """Turn stored figures into one decision, its basis and next actions."""
        labels = dict(self.QUESTIONS)
        if question not in labels:
            raise ValueError("質問を選んでください。")
        sales = financials.monthly_sales_total(month)
        summary = financials.monthly_sales_summary(month)
        cost = purchases.monthly_total(month, kind="cost")
        operations = financials.get_monthly_operations(month)
        supplies = purchases.monthly_total(month, kind="operating_supply")
        expenses = purchases.monthly_total(month, kind="expense")
        fees = financials.monthly_payment_summary(month)["total_fees"]
        ads = financials.get_monthly_advertising(month)["total"]
        gross = sales - cost
        fixed = sum((operations["personnel"], operations["rent"], operations["utilities"],
                     operations["other_admin"], supplies, expenses, fees, ads))
        profit = gross - fixed
        annual_periods = annual_reports.list_periods()
        annual = annual_reports.get_report(annual_periods[0]) if annual_periods else None
        values = annual["current"] if annual else {}
        result = annual_reports.calculate(values) if annual else None
        cash = sum(int(values.get(key, 0) or 0) for key in
                   ("cash_on_hand", "checking_deposit", "ordinary_deposit"))
        debt = sum(int(values.get(key, 0) or 0) for key in
                   ("short_term_loans", "long_term_loans"))
        one_percent = round(sales * .01)
        customers = summary["lunch_customers"] + summary["dinner_customers"]

        answer = {"question": labels[question], "actions": [], "target": ""}
        if question == "cash":
            if profit < 0 and cash:
                months = cash / abs(profit)
                answer.update(conclusion=f"今の赤字ペースなら、手元資金は約{months:.1f}か月分です。",
                              reason=f"決算時点の現預金 ¥{cash:,} ÷ 今月の暫定営業赤字 ¥{abs(profit):,} の概算です。税金・返済・入出金時期は未反映です。",
                              target="12か月資金繰りを入力し、不足月の3か月前に相談")
            else:
                answer.update(conclusion="現時点の入力だけでは、資金が尽きる月を確定できません。",
                              reason=f"決算時点の現預金は ¥{cash:,}。入金日・支払日・税金・元金返済の月別予定が必要です。",
                              target="今後12か月の月末現金をすべてプラスにする")
            answer["actions"] = ["12か月の入金・仕入支払・税金・返済を月別に入力", "最初に現金が不足する月を確認", "不足予測の3か月前を金融機関への相談期限にする"]
        elif question == "loss":
            gap = max(0, -profit)
            answer.update(conclusion=(f"まず月 ¥{gap:,} の改善が必要です。" if gap else "入力済み実績では営業黒字です。"),
                          reason=f"売上 ¥{sales:,}、粗利 ¥{gross:,}、入力済み営業利益 ¥{profit:,}です。",
                          target=f"月間営業利益を最低 ¥{max(1, round(sales*.03)):,} にする",
                          actions=["原価1%・人件費1%・客単価100円の効果を比較", "金額効果が大きく実行しやすい施策を1つ選ぶ", "翌月に実績との差を確認"])
        elif question == "debt":
            ordinary = result["ordinary_profit"] if result else 0
            years = debt / ordinary if debt and ordinary > 0 else None
            answer.update(conclusion=(f"利益基準の返済年数は約{years:.1f}年です。" if years else "現在の利益では借入の返済年数を算定できません。"),
                          reason=f"借入残高 ¥{debt:,}、年間経常利益 ¥{ordinary:,}です。",
                          target="年間返済額・返済後現金・黒字目標を同時に確定",
                          actions=["年間の元金返済予定を確認", "本業利益から返済できる額を計算", "不足する場合は借換え・返済条件を早めに相談"])
        elif question in ("personnel", "cost"):
            value = operations["personnel"] if question == "personnel" else cost
            base = gross if question == "personnel" else sales
            rate = value / base if base > 0 else None
            name = "労働分配率" if question == "personnel" else "原価率"
            answer.update(conclusion=(f"現在の{name}は {rate*100:.1f}%です。" if rate is not None else f"{name}はまだ計算できません。"),
                          reason=f"1%改善すると今月約 ¥{one_percent:,}、同水準なら年間約 ¥{one_percent*12:,} 改善します。",
                          target=f"まず1%改善し、月 ¥{one_percent:,} を残す",
                          actions=(["時間帯別売上とシフトを照合", "売上の薄い時間から配置を調整", "サービス品質を落とさず翌月比較"] if question == "personnel" else ["高原価商品・仕入単価・廃棄を確認", "値上げと仕入先交渉の効果を比較", "翌月の原価率で検証"]))
        elif question == "sales":
            margin = gross / sales if sales > 0 else 0
            needed = round(abs(profit) / margin) if profit < 0 and margin > 0 else 0
            spend_effect = customers * 100
            answer.update(conclusion=(f"現状の粗利率なら、赤字解消に月約 ¥{needed:,} の追加売上が必要です。" if needed else "入力済み実績は黒字です。利益目標から逆算できます。"),
                          reason=f"客単価を100円上げると、入力済み客数 {customers:,}人では月約 ¥{spend_effect:,} の売上効果です。",
                          target=f"追加売上 ¥{needed:,} または同額以上の費用改善",
                          actions=["客単価100円の効果と費用1%改善を比較", "必要売上を営業日数で割り1日目標にする", "ランチ・ディナー別に実績確認"])
        else:
            safe = bool(result and not result["balance_gap"] and result["equity"] > 0 and
                        result["current_assets"] >= result["current_liabilities"] and
                        (result["cash_months"] or 0) >= 2 and profit > 0)
            answer.update(conclusion=("条件付きで小さな投資を試せます。" if safe else "今は大きな新規投資より、資金防衛と黒字化を優先です。"),
                          reason="営業黒字・債務超過なし・流動資産が流動負債以上・現預金2か月分を安全条件にしています。",
                          target="投資上限と回収期限を決め、条件を満たしてから実行",
                          actions=["投資後も3か月分の支払資金が残るか確認", "最悪時の損失上限を決める", "小さく試し回収実績を見て拡大"])
        return answer

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
