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
        ("year_plan", "この1年間でやるべきこと"),
        ("compare", "去年より良くなった？"),
        ("stress", "売上が下がってもどこまで耐えられる？"),
    )

    def __init__(self, data_manager=None):
        self._data_manager = data_manager or data

    def annual_snapshot(self, month=None):
        periods = annual_reports.list_periods()
        if not periods:
            return None
        report = annual_reports.get_report(periods[0])
        values = report["current"]
        result = annual_reports.calculate(values)
        personnel = sum(int(values.get(key, 0) or 0) for key in (
            "executive_compensation", "salaries", "retirement_allowance",
            "statutory_welfare", "welfare", "temporary_wages",
        ))
        cash = sum(int(values.get(key, 0) or 0) for key in
                   ("cash_on_hand", "checking_deposit", "ordinary_deposit"))
        debt = sum(int(values.get(key, 0) or 0) for key in
                   ("short_term_loans", "long_term_loans"))
        return {
            "period": periods[0], "values": values, "result": result,
            "sales": int(values.get("sales", 0) or 0), "cost": result.get("cogs", 0),
            "gross": result.get("gross_profit", 0), "personnel": personnel,
            "profit": result.get("operating_profit", 0), "cash": cash, "debt": debt,
        }

    def diagnose(self, month):
        snapshot = self.annual_snapshot(month)
        sales = snapshot["sales"] if snapshot else 0
        cost = snapshot["cost"] if snapshot else 0
        operating_profit = snapshot["profit"] if snapshot else 0
        cost_rate = cost / sales if sales else None
        personnel_rate = snapshot["personnel"] / sales if sales and snapshot else None

        annual = {"current": snapshot["values"]} if snapshot else None
        annual_result = snapshot["result"] if snapshot else None
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
            add("sales_input", 80, "決算書を入力する", "決算書の売上が未入力のため、利益改善の優先順位を判定できません。",
                "最新の貸借対照表と損益計算書を入力する", "決算書診断を表示", "今日")
        else:
            if operating_profit < 0:
                add("profit", 75, "年間営業赤字を止める",
                    f"最新決算では営業赤字が {abs(operating_profit):,}円です。",
                    "赤字額を原価・人件費・固定費の3つに分け、最も実行しやすい改善から着手する",
                    f"年間 {abs(operating_profit):,}円以上改善", "次の決算まで")
            if cost_rate is not None and cost_rate > .36:
                gap = max(0, cost - round(sales * .36))
                add("cost", 60, "原価を改善する", f"原価率は {cost_rate * 100:.1f}%で、日本料理店の参考36%を上回ります。",
                    "高原価商品の値上げ、仕入単価、廃棄量を順に確認する", f"月間 {gap:,}円改善を検討", "次の30日")
            if personnel_rate is not None and personnel_rate > .33:
                gap = max(0, snapshot["personnel"] - round(sales * .33))
                add("personnel", 55, "人件費の使い方を見直す", f"人件費率は {personnel_rate * 100:.1f}%で、日本料理店の参考33%を上回ります。",
                    "時間帯別売上とシフトを照合し、売上の薄い時間から配置を調整する", f"年間 {gap:,}円改善を検討", "次のシフト作成時")

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

    def executive_overview(self, month):
        """Plain-language, decision-first summary for the company owner."""
        snapshot = self.annual_snapshot(month)
        if not snapshot:
            return {
                "level": "unknown", "label": "まだ判断できません",
                "headline": "決算書を入力すると、会社全体の状態が分かります",
                "items": [],
                "known": ["日々入力した売上・仕入れ・人件費"],
                "unknown": ["会社全体の安全性", "債務超過の状態", "借入を含む将来のお金"],
                "next_input": "最新の決算書を入力 → 会社の安全性と債務超過の状態が分かる",
            }
        result = snapshot["result"]
        sales, cost, gross, profit = (snapshot[key] for key in ("sales", "cost", "gross", "profit"))
        personnel = snapshot["personnel"]
        items = []

        def add(level, title, detail):
            items.append({"level": level, "title": title, "detail": detail})

        if result.get("balance_gap"):
            add("danger", "決算書の数字が左右で合っていません",
                f"差は ¥{abs(result['balance_gap']):,}。安全性の判定前に入力を確認してください")
        else:
            short_gap = result.get("current_assets", 0) - result.get("current_liabilities", 0)
            if short_gap < 0:
                add("danger", "近い将来の支払いに注意",
                    f"決算日時点では、1年以内に払う金額が現金化しやすい資産を ¥{abs(short_gap):,}上回っています")
            else:
                add("good", "近い将来の支払い余力", f"決算日時点では ¥{short_gap:,}の余裕があります")
            if result.get("equity", 0) < 0:
                add("danger", "会社に残る財産がマイナス",
                    f"返すお金が会社の財産を ¥{abs(result['equity']):,}上回っています")
            else:
                add("good", "会社に残る財産", f"¥{result.get('equity', 0):,}のプラスです")
        add("good" if profit > 0 else "danger", "本業の利益",
            f"年間 ¥{profit:,}の{'黒字' if profit > 0 else '赤字'}です")
        cost_rate = cost / sales if sales else None
        labor_rate = personnel / gross if gross > 0 else None
        if cost_rate is not None:
            add("good" if cost_rate <= .36 else "warning", "食材の使い方",
                f"売上の {cost_rate*100:.1f}%です")
        if labor_rate is not None:
            add("good" if labor_rate <= .50 else "warning", "人件費の使い方",
                f"食材を引いた利益の {labor_rate*100:.1f}%です")
        if any(item["level"] == "danger" for item in items):
            level, label = "danger", "危険な点があります"
            headline = "会社全体は赤判定です。良い部分を守りながら、赤い原因から確認しましょう"
        elif any(item["level"] == "warning" for item in items):
            level, label = "warning", "注意が必要です"
            headline = "大きな危険は見つかっていませんが、今のうちに見直したい項目があります"
        else:
            level, label = "good", "現在は順調です"
            headline = "今の良い状態を守りながら、将来と成長の選択肢を確認できます"
        return {
            "level": level, "label": label, "headline": headline, "items": items,
            "known": ["最新決算時点の会社の安全性", "年間の本業利益", "食材と人件費の使い方"],
            "unknown": ["実際にお金が足りなくなる月", "借入残高の毎月の減り方", "1年後の通帳残高"],
            "next_input": "借入の返済予定・税金の支払予定を登録 → お金が足りなくなる月と金額が分かる",
        }

    def answer(self, month, question):
        """Turn stored figures into one decision, its basis and next actions."""
        labels = dict(self.QUESTIONS)
        if question not in labels:
            raise ValueError("質問を選んでください。")
        snapshot = self.annual_snapshot(month)
        if not snapshot:
            return {"question": labels[question], "conclusion": "先に最新の決算書を入力してください。", "reason": "経営コンサルは決算書の年間数字を基準に判断します。", "actions": ["決算分析で貸借対照表を入力", "損益計算書を入力", "貸借差額を0円にする"], "target": "最新決算書の入力を完成"}
        sales, cost, gross, profit = (snapshot[key] for key in ("sales", "cost", "gross", "profit"))
        result, cash, debt = snapshot["result"], snapshot["cash"], snapshot["debt"]
        one_percent = round(sales * .01)

        answer = {"question": labels[question], "actions": [], "target": ""}
        if question == "cash":
            if profit < 0 and cash:
                months = cash / (abs(profit) / 12)
                answer.update(conclusion=f"今の赤字ペースなら、手元資金は約{months:.1f}か月分です。",
                              reason=f"決算時点の現預金 ¥{cash:,} ÷ 年間営業赤字の月平均 ¥{round(abs(profit)/12):,} の概算です。税金・返済・入出金時期は未反映です。",
                              target="12か月資金繰りを入力し、不足月の3か月前に相談")
            else:
                answer.update(conclusion="現時点の入力だけでは、資金が尽きる月を確定できません。",
                              reason=f"決算時点の現預金は ¥{cash:,}。入金日・支払日・税金・元金返済の月別予定が必要です。",
                              target="今後12か月の月末現金をすべてプラスにする")
            answer["actions"] = ["12か月の入金・仕入支払・税金・返済を月別に入力", "最初に現金が不足する月を確認", "不足予測の3か月前を金融機関への相談期限にする"]
        elif question == "loss":
            gap = max(0, -profit)
            if gap:
                target = f"まず損益分岐点（営業利益0円）まで年間 ¥{gap:,} 改善する"
                actions = ["原価1%・人件費1%・客単価100円の効果を比較", "赤字額を埋める組み合わせを決める", "月次実績で改善ペースを確認"]
            else:
                margin = profit / sales if sales else 0
                target = f"現在の年間営業利益 ¥{profit:,}（利益率 {margin*100:.1f}%）以上を維持する"
                actions = ["現在の黒字を生んでいる売上と費用構造を確認", "原価・人件費・客単価の変化による利益減少を監視", "投資する場合も現在利益を下回らない条件を決める"]
            answer.update(conclusion=(f"まず年間 ¥{gap:,} の改善が必要です。" if gap else f"赤字解消は不要です。年間営業利益は ¥{profit:,} です。"),
                          reason=f"決算書の年間売上 ¥{sales:,}、粗利 ¥{gross:,}、営業利益 ¥{profit:,}です。",
                          target=target, actions=actions)
        elif question == "debt":
            ordinary = result["ordinary_profit"] if result else 0
            years = debt / ordinary if debt and ordinary > 0 else None
            answer.update(conclusion=(f"利益基準の返済年数は約{years:.1f}年です。" if years else "現在の利益では借入の返済年数を算定できません。"),
                          reason=f"借入残高 ¥{debt:,}、年間経常利益 ¥{ordinary:,}です。",
                          target="年間返済額・返済後現金・黒字目標を同時に確定",
                          actions=["年間の元金返済予定を確認", "本業利益から返済できる額を計算", "不足する場合は借換え・返済条件を早めに相談"])
        elif question in ("personnel", "cost"):
            value = snapshot["personnel"] if question == "personnel" else cost
            base = gross if question == "personnel" else sales
            rate = value / base if base > 0 else None
            name = "労働分配率" if question == "personnel" else "原価率"
            answer.update(conclusion=(f"現在の{name}は {rate*100:.1f}%です。" if rate is not None else f"{name}はまだ計算できません。"),
                          reason=f"決算書の年間売上を基準に、1%改善すると年間約 ¥{one_percent:,} 改善します。",
                          target=f"まず1%改善し、年間 ¥{one_percent:,} を残す",
                          actions=(["時間帯別売上とシフトを照合", "売上の薄い時間から配置を調整", "サービス品質を落とさず翌月比較"] if question == "personnel" else ["高原価商品・仕入単価・廃棄を確認", "値上げと仕入先交渉の効果を比較", "翌月の原価率で検証"]))
        elif question == "sales":
            margin = gross / sales if sales > 0 else 0
            needed = round(abs(profit) / margin) if profit < 0 and margin > 0 else 0
            answer.update(conclusion=(f"現状の粗利率なら、赤字解消に年間約 ¥{needed:,} の追加売上が必要です。" if needed else "最新決算は黒字です。利益目標から逆算できます。"),
                          reason="客単価の効果は、数日分の客数を年間換算せず、改善シミュレーションで年間客数を入力した場合だけ計算します。",
                          target=f"追加売上 ¥{needed:,} または同額以上の費用改善",
                          actions=["客単価100円の効果と費用1%改善を比較", "必要売上を営業日数で割り1日目標にする", "ランチ・ディナー別に実績確認"])
        elif question == "year_plan":
            working_capital = result.get("current_assets", 0) - result.get("current_liabilities", 0)
            equity = result.get("equity", 0)
            cost_rate = cost / sales if sales else 0
            personnel_rate = snapshot["personnel"] / sales if sales else 0
            food_one_percent = round(sales * .01)
            labor_one_percent = round(gross * .01)
            monthly_profit = round(profit / 12)
            first_focus = "毎月の支払いに困らない状態を作る" if working_capital < 0 else "今の黒字を安定させる"
            roadmap = [
                "1か月目｜まず数字を信頼できる状態にする。決算書の左右の差を0円にし、銀行にあるお金・借入残高・1年間の返済額を確認する",
                "2か月目｜お金が足りなくなる月を先に見つける。12か月分の入金、仕入れ、給料、税金、返済を月ごとに並べる",
                "3か月目｜3か月以内にお金が足りなくなるなら、足りなくなってからではなく今のうちに銀行へ相談する",
                f"4か月目｜毎月いくら残せばよいか決める。現在の年間営業利益は ¥{profit:,}、月平均は約 ¥{monthly_profit:,}",
                f"5か月目｜食材で年間 ¥{food_one_percent:,}残す挑戦をする。高い食材、廃棄、量、値付けの順に確認する",
                f"6か月目｜働き方で年間 ¥{labor_one_percent:,}残せるか試す。暇な時間の人数を減らし、忙しい時間の接客は守る",
                "7か月目｜値上げか売れ筋の入れ替えを1つだけ試す。変更前と変更後で、売上ではなく残った利益を比べる",
                "8か月目｜借入を返したあとも通帳残高が減り続けていないか確認する。苦しい場合は返済方法を早めに相談する",
                "9か月目｜広告費が本当にお客様につながったか確認する。効果が見えない支出は止めるか小さくする",
                "10か月目｜3か月分の支払い用のお金が残る場合だけ、採用・設備・販促を小さく試す",
                "11か月目｜来年の計画を『普通』『悪い場合』『良い場合』の3通りで作り、悪い場合でもお金が足りるか確認する",
                "12か月目｜この1年で実際に残せたお金を確認し、効いた行動だけを残して、来年やることを3つに絞る",
            ]
            observations = []
            if working_capital < 0:
                observations.append(f"近いうちに払うお金に対し、使えるお金が ¥{abs(working_capital):,}足りません")
            if equity < 0:
                observations.append(f"会社に残っている財産より返すお金が ¥{abs(equity):,}多い状態です")
            if profit < 0:
                observations.append(f"本業で年間 ¥{abs(profit):,}の赤字です")
            conclusion = f"この1年の最優先は『{first_focus}』です。最初から全部やらず、毎月1つずつ進めましょう。"
            answer.update(
                conclusion=conclusion,
                reason=("今の会社の状態は、" + "。".join(observations) + "。だから売上を増やす前に、支払いを止めない準備が先です。") if observations else
                       f"本業では年間 ¥{profit:,}残せています。食材は売上の {cost_rate*100:.1f}%、人件費は売上の {personnel_rate*100:.1f}%です。今の利益を守りながら改善できます。",
                target=(f"1年後も年間 ¥{profit:,}以上の本業利益を残し、支払い後の通帳残高を減らさない" if profit >= 0
                        else f"1年後までに年間 ¥{abs(profit):,}の赤字をなくし、支払い後の通帳残高を減らさない"),
                actions=roadmap,
            )
        elif question == "compare":
            report = annual_reports.get_report(snapshot["period"])
            previous_values = report.get("previous", {})
            if not previous_values or not any(previous_values.values()):
                answer.update(
                    conclusion="前年の決算書がないため、まだ比べられません。",
                    reason="今年と前年の決算書がそろうと、売上・本業利益・会社に残る財産・借入を比較できます。",
                    actions=["前年の決算書を登録する"],
                    target="前年と今年の2期分をそろえる",
                )
            else:
                previous = annual_reports.calculate(previous_values)
                previous_sales = int(previous_values.get("sales", 0) or 0)
                previous_debt = sum(int(previous_values.get(key, 0) or 0) for key in
                                    ("short_term_loans", "long_term_loans"))
                changes = [
                    f"売上は前年より ¥{sales-previous_sales:+,}",
                    f"本業利益は前年より ¥{profit-previous.get('operating_profit', 0):+,}",
                    f"会社に残る財産は前年より ¥{result.get('equity', 0)-previous.get('equity', 0):+,}",
                    f"借入は前年より ¥{debt-previous_debt:+,}",
                ]
                improved = profit >= previous.get("operating_profit", 0) and result.get("equity", 0) >= previous.get("equity", 0)
                answer.update(
                    conclusion="前年より良くなっています。" if improved else "良くなった部分と、悪くなった部分があります。",
                    reason="／".join(changes), actions=changes,
                    target="本業利益・会社に残る財産を増やし、借入を減らす",
                )
        elif question == "stress":
            gross_margin = gross / sales if sales else 0
            sales_buffer = round(profit / gross_margin) if profit > 0 and gross_margin > 0 else 0
            decline_rate = sales_buffer / sales if sales else 0
            if sales_buffer > 0:
                answer.update(
                    conclusion=f"単純計算では、年間売上が約 ¥{sales_buffer:,}（{decline_rate*100:.1f}%）下がると本業利益が0円になります。",
                    reason="食材の割合と固定費が今と同じ前提で、現在の本業利益がなくなる売上減少額を計算しています。",
                    actions=["5%売上減の場合を試す", "10%売上減の場合を試す", "そのときも支払い用の現金が残るか確認する"],
                    target="売上が10%下がっても、本業黒字と支払い資金を守れる状態",
                )
            else:
                answer.update(
                    conclusion="現在は売上減少に耐える余裕を計算できません。",
                    reason="本業利益が0円以下、または売上・食材の数字が不足しています。",
                    actions=["まず本業を黒字にする", "売上と食材原価を確定する"],
                    target="売上減少に耐えられる黒字幅を作る",
                )
        else:
            safe = bool(result and not result["balance_gap"] and result["equity"] > 0 and
                        result["current_assets"] >= result["current_liabilities"] and
                        (result["cash_months"] or 0) >= 2 and profit > 0)
            answer.update(conclusion=("条件付きで小さな投資を試せます。" if safe else "今は大きな新規投資より、資金防衛と黒字化を優先です。"),
                          reason="営業黒字・債務超過なし・流動資産が流動負債以上・現預金2か月分を安全条件にしています。",
                          target="投資上限と回収期限を決め、条件を満たしてから実行",
                          actions=["投資後も3か月分の支払資金が残るか確認", "最悪時の損失上限を決める", "小さく試し回収実績を見て拡大"])
        return answer

    def simulate(self, month, cost_points=0, personnel_points=0,
                 spend_increase=0, annual_customers=0):
        snapshot = self.annual_snapshot(month)
        if not snapshot:
            return None
        cost_effect = round(snapshot["sales"] * float(cost_points) / 100)
        personnel_effect = round(snapshot["sales"] * float(personnel_points) / 100)
        spend_effect = round(float(annual_customers or 0) * float(spend_increase))
        total = cost_effect + personnel_effect + spend_effect
        return {"cost_effect": cost_effect, "personnel_effect": personnel_effect,
                "spend_effect": spend_effect, "total": total,
                "new_profit": snapshot["profit"] + total}

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
