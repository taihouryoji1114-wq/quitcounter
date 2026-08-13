"""Independent annual financial statements and management diagnosis."""

from __future__ import annotations

from core.data import data


CURRENT_ASSET_FIELDS = (
    "cash_on_hand", "checking_deposit", "ordinary_deposit", "receivables",
    "merchandise", "temporary_payment", "prepaid", "substitute_payment",
)
FIXED_ASSET_FIELDS = (
    "building_equipment", "vehicles", "fixtures", "lump_sum_depreciable_assets",
    "telephone_rights", "investments", "security_deposit", "lease_deposit",
    "membership_deposit",
)
ASSET_FIELDS = (*CURRENT_ASSET_FIELDS, *FIXED_ASSET_FIELDS)
CURRENT_LIABILITY_FIELDS = (
    "payables", "short_term_loans", "unpaid_accounts", "accrued_expenses",
    "deposits_received", "unpaid_consumption_tax",
)
FIXED_LIABILITY_FIELDS = ("long_term_loans", "other_fixed_liabilities")
LIABILITY_FIELDS = (*CURRENT_LIABILITY_FIELDS, *FIXED_LIABILITY_FIELDS)
EQUITY_FIELDS = (
    "capital", "profit_reserve", "special_reserve", "retained_earnings",
)
SGA_FIELDS = (
    "executive_compensation", "salaries", "retirement_allowance",
    "statutory_welfare", "welfare", "temporary_wages",
    "advertising", "freight", "utilities", "fuel", "office_supplies",
    "consumables", "rent", "insurance", "repairs", "taxes_and_dues",
    "entertainment", "travel", "communication", "fees", "membership_fees",
    "card_fees", "lease", "miscellaneous_expenses",
)
PL_INPUT_FIELDS = (
    "sales", "opening_inventory", "purchases", "closing_inventory",
    *SGA_FIELDS, "interest_income", "dividend_income", "miscellaneous_income",
    "interest_expense", "guarantee_amortization", "miscellaneous_loss",
    "extraordinary_income", "fixed_asset_disposal_loss",
)
# Values entered in the early summarized screen remain stored for recovery, but
# are intentionally excluded from totals because they are not on the statement.
HIDDEN_LEGACY_FIELDS = (
    "other_current_assets", "other_fixed_assets",
    "other_current_liabilities", "other_equity",
    "recruitment_fees", "depreciation", "other_sga",
    "extraordinary_loss", "corporate_taxes",
)
ALL_FIELDS = (
    *ASSET_FIELDS, *LIABILITY_FIELDS, *EQUITY_FIELDS, *PL_INPUT_FIELDS,
    *HIDDEN_LEGACY_FIELDS,
)


class AnnualReportManager:
    def __init__(self, manager=None):
        self._data_manager = manager or data

    @staticmethod
    def _period(value):
        value = str(value or "")
        if len(value) != 7 or value[4] != "-":
            raise ValueError("決算期を年月で入力してください。")
        try:
            year, month = (int(part) for part in value.split("-"))
        except ValueError as error:
            raise ValueError("決算期を年月で入力してください。") from error
        if year < 1900 or month < 1 or month > 12:
            raise ValueError("決算期を年月で入力してください。")
        return f"{year:04d}-{month:02d}"

    @staticmethod
    def _amount(value):
        try:
            normalized = str(value or 0).strip().replace(",", "")
            if normalized.startswith("△"):
                normalized = "-" + normalized[1:]
            amount = int(float(normalized))
        except (TypeError, ValueError) as error:
            raise ValueError("金額は数字で入力してください。マイナスは - または △ を付けます。") from error
        return amount

    def list_periods(self):
        reports = self._data_manager.data.get("business_annual_reports", {})
        return sorted(reports, reverse=True) if isinstance(reports, dict) else []

    def _statement_values(self, source):
        source = source if isinstance(source, dict) else {}
        result = {key: self._amount(source.get(key, 0)) for key in ALL_FIELDS}
        # Preserve entries made in the earlier summarized input screen.
        legacy = {
            "cash_on_hand": ("cash",), "merchandise": ("inventory",),
            "building_equipment": ("buildings",), "fixtures": ("equipment",),
            "telephone_rights": ("intangible_assets",),
            "security_deposit": ("deposits",), "investments": ("investments",),
            "unpaid_accounts": ("accrued_expenses",),
            "unpaid_consumption_tax": ("unpaid_taxes",),
            "profit_reserve": ("capital_reserves",),
            "miscellaneous_expenses": ("other_sga",),
            "miscellaneous_income": ("non_operating_income",),
            "interest_expense": ("non_operating_expense",),
        }
        for target, old_keys in legacy.items():
            if not result[target]:
                result[target] = sum(self._amount(source.get(key, 0)) for key in old_keys)
        return result

    def get_report(self, period):
        period = self._period(period)
        reports = self._data_manager.data.get("business_annual_reports", {})
        stored = reports.get(period, {}) if isinstance(reports, dict) else {}
        prior_periods = sorted(
            (value for value in reports if value < period), reverse=True
        ) if isinstance(reports, dict) else []
        if prior_periods:
            previous_values = reports.get(prior_periods[0], {}).get("current", {})
            previous_period = prior_periods[0]
        else:
            # Keep compatibility with reports saved by the first two-column version.
            previous_values = stored.get("previous", {})
            previous_period = None
        return {
            "period": period,
            "current": self._statement_values(stored.get("current", {})),
            "previous": self._statement_values(previous_values),
            "previous_period": previous_period,
        }

    def save_report(self, period, current, previous=None):
        period = self._period(period)
        reports = self._data_manager.data.setdefault("business_annual_reports", {})
        existing_current = reports.get(period, {}).get("current", {})
        merged_current = dict(existing_current) if isinstance(existing_current, dict) else {}
        merged_current.update(current or {})
        if previous is None:
            previous = reports.get(period, {}).get("previous", {})
        cleaned = {
            "current": {key: self._amount(merged_current.get(key, 0)) for key in ALL_FIELDS},
            "previous": {key: self._amount((previous or {}).get(key, 0)) for key in ALL_FIELDS},
        }
        reports[period] = cleaned
        self._data_manager.save()
        return self.get_report(period)

    @staticmethod
    def calculate(values):
        values = {key: int(values.get(key, 0) or 0) for key in ALL_FIELDS}
        current_assets = sum(values[key] for key in CURRENT_ASSET_FIELDS)
        fixed_assets = sum(values[key] for key in FIXED_ASSET_FIELDS)
        current_liabilities = sum(values[key] for key in CURRENT_LIABILITY_FIELDS)
        fixed_liabilities = sum(values[key] for key in FIXED_LIABILITY_FIELDS)
        equity = sum(values[key] for key in EQUITY_FIELDS)
        cogs = values["opening_inventory"] + values["purchases"] - values["closing_inventory"]
        gross_profit = values["sales"] - cogs
        sga = sum(values[key] for key in SGA_FIELDS)
        operating_profit = gross_profit - sga
        non_operating_income = values["interest_income"] + values["dividend_income"] + values["miscellaneous_income"]
        non_operating_expense = values["interest_expense"] + values["guarantee_amortization"] + values["miscellaneous_loss"]
        ordinary_profit = operating_profit + non_operating_income - non_operating_expense
        # The supplied statement shows 固定資産除却損 as the input account and
        # 特別損失 as its subtotal, so they must not be added together.
        extraordinary_loss = values["fixed_asset_disposal_loss"]
        pretax_profit = ordinary_profit + values["extraordinary_income"] - extraordinary_loss
        net_income = pretax_profit
        assets = current_assets + fixed_assets
        liabilities = current_liabilities + fixed_liabilities
        return {
            "current_assets": current_assets,
            "fixed_assets": fixed_assets,
            "assets": assets,
            "current_liabilities": current_liabilities,
            "fixed_liabilities": fixed_liabilities,
            "liabilities": liabilities,
            "equity": equity,
            "balance_gap": assets - liabilities - equity,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "sga": sga,
            "operating_profit": operating_profit,
            "ordinary_profit": ordinary_profit,
            "pretax_profit": pretax_profit,
            "net_income": net_income,
            "current_ratio": current_assets / current_liabilities if current_liabilities else None,
            "quick_ratio": (values["cash_on_hand"] + values["checking_deposit"] + values["ordinary_deposit"] + values["receivables"]) / current_liabilities if current_liabilities else None,
            "equity_ratio": equity / assets if assets else None,
            "operating_margin": operating_profit / values["sales"] if values["sales"] else None,
            "gross_margin": gross_profit / values["sales"] if values["sales"] else None,
            "debt_to_sales": (values["short_term_loans"] + values["long_term_loans"]) / values["sales"] if values["sales"] else None,
            "cash_months": (values["cash_on_hand"] + values["checking_deposit"] + values["ordinary_deposit"]) / (values["sales"] / 12) if values["sales"] else None,
        }

    @staticmethod
    def management_decision(current_values, previous_values=None):
        current = AnnualReportManager.calculate(current_values)
        previous = AnnualReportManager.calculate(previous_values or {})
        sales = int(current_values.get("sales", 0) or 0)
        previous_sales = int((previous_values or {}).get("sales", 0) or 0)
        debt = int(current_values.get("short_term_loans", 0) or 0) + int(
            current_values.get("long_term_loans", 0) or 0
        )
        personnel = sum(int(current_values.get(key, 0) or 0) for key in (
            "executive_compensation", "salaries", "retirement_allowance",
            "statutory_welfare", "welfare", "temporary_wages",
        ))
        working_capital = current["current_assets"] - current["current_liabilities"]
        cogs_rate = current["cogs"] / sales if sales else None
        labor_rate = personnel / current["gross_profit"] if current["gross_profit"] > 0 else None
        sales_growth = sales / previous_sales - 1 if previous_sales else None
        debt_payback_years = debt / current["ordinary_profit"] if current["ordinary_profit"] > 0 else None

        facts = {
            "working_capital": working_capital,
            "cogs_rate": cogs_rate,
            "labor_rate": labor_rate,
            "sales_growth": sales_growth,
            "debt": debt,
            "debt_payback_years": debt_payback_years,
        }
        if current["balance_gap"]:
            return {
                "mode": "verify", "label": "判断前に入力確認", "score": 0,
                "summary": "貸借が一致していないため、経営判断を確定できません。",
                "reasons": [f"貸借差額が {abs(current['balance_gap']):,}円あります。"],
                "actions": ["資産合計と負債・純資産合計を決算書と照合する"],
                "attack_conditions": ["貸借を一致させて診断を確定する"],
                "facts": facts,
            }

        defense = 0
        reasons = []
        actions = []
        if current["equity"] < 0:
            defense += 3
            reasons.append("債務超過で、損失への耐久力が低い")
            actions.append("債務超過を何年で解消するか利益計画を作る")
        if working_capital < 0:
            defense += 2
            reasons.append("流動負債が流動資産を上回っている")
            actions.append("税金・買掛金・借入返済を含む12か月資金繰り表を作る")
        if current["cash_months"] is not None and current["cash_months"] < 1:
            defense += 2
            reasons.append("現預金が月商1か月分未満")
            actions.append("最低現預金ラインを決め、下回る投資を止める")
        if debt_payback_years is None or debt_payback_years > 10:
            defense += 1
            reasons.append("現在の利益では借入返済が長期化する")
            actions.append("借入返済額と本業の利益目標を分けて管理する")

        improvement = 0
        if current["operating_profit"] <= 0:
            improvement += 3
            reasons.append("本業の営業利益が赤字")
            actions.append("原価・人件費・固定費を分けて黒字化余地を試算する")
        if previous_sales and sales_growth is not None and sales_growth > 0 and current["operating_profit"] < previous["operating_profit"]:
            improvement += 2
            reasons.append("増収なのに営業利益が減っている")
            actions.append("売上拡大より先に、増えた費用の科目を特定する")
        if cogs_rate is not None and cogs_rate >= 0.35:
            improvement += 1
            reasons.append(f"原価率が {cogs_rate * 100:.1f}%")
            actions.append("仕入価格・廃棄・メニュー構成別に原価改善額を決める")
        if labor_rate is not None and labor_rate >= 0.45:
            improvement += 1
            reasons.append(f"労働分配率が {labor_rate * 100:.1f}%")
            actions.append("時間帯別売上と人員配置を照合する")

        attack = 0
        attack_conditions = []
        if current["operating_profit"] > 0 and (current["operating_margin"] or 0) >= 0.05:
            attack += 1
        else:
            attack_conditions.append("営業利益率5%以上を安定させる")
        if working_capital > 0 and (current["cash_months"] or 0) >= 2:
            attack += 1
        else:
            attack_conditions.append("運転資金をプラスにし、現預金2か月分を確保する")
        if current["equity"] > 0 and (debt_payback_years is None or debt_payback_years <= 10):
            attack += 1
        else:
            attack_conditions.append("純資産をプラスにし、返済力を改善する")
        if sales_growth is not None and sales_growth > 0 and current["operating_profit"] >= previous["operating_profit"]:
            attack += 1
        elif previous_sales:
            attack_conditions.append("売上と営業利益がともに前年を上回る状態を作る")

        if defense >= 3:
            mode, label = "defense", "守りを優先"
            summary = "投資拡大より、資金確保と財務改善を先に進める局面です。"
        elif improvement >= 2:
            mode, label = "improve", "利益改善を優先"
            summary = "売上拡大だけでなく、利益構造の改善を優先する局面です。"
        elif attack >= 3:
            mode, label = "attack", "条件付きで攻める"
            summary = "財務余力を守りながら、効果を測れる投資を検討できる局面です。"
            reasons.append("収益・資金・返済力の複数条件を満たしている")
            actions.append("投資上限と回収期限を決め、採用・広告・設備投資を比較する")
        else:
            mode, label = "balance", "守りながら改善"
            summary = "大きな投資は抑え、利益と現預金を積み上げる局面です。"
            actions.append("四半期ごとに利益・現預金・借入残高を確認する")

        return {
            "mode": mode, "label": label, "score": max(defense, improvement, attack),
            "summary": summary, "reasons": list(dict.fromkeys(reasons))[:3],
            "actions": list(dict.fromkeys(actions))[:3],
            "attack_conditions": list(dict.fromkeys(attack_conditions))[:3],
            "facts": facts,
        }


annual_reports = AnnualReportManager()
