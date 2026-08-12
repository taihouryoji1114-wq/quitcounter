"""Independent annual financial statements and management diagnosis."""

from __future__ import annotations

from core.data import data


CURRENT_ASSET_FIELDS = (
    "cash_on_hand", "checking_deposit", "ordinary_deposit", "receivables",
    "merchandise", "temporary_payment", "prepaid", "substitute_payment",
    "other_current_assets",
)
FIXED_ASSET_FIELDS = (
    "building_equipment", "vehicles", "fixtures", "lump_sum_depreciable_assets",
    "telephone_rights", "investments", "security_deposit", "lease_deposit",
    "membership_deposit", "other_fixed_assets",
)
ASSET_FIELDS = (*CURRENT_ASSET_FIELDS, *FIXED_ASSET_FIELDS)
CURRENT_LIABILITY_FIELDS = (
    "payables", "short_term_loans", "unpaid_accounts", "accrued_expenses",
    "deposits_received", "unpaid_consumption_tax", "other_current_liabilities",
)
FIXED_LIABILITY_FIELDS = ("long_term_loans", "other_fixed_liabilities")
LIABILITY_FIELDS = (*CURRENT_LIABILITY_FIELDS, *FIXED_LIABILITY_FIELDS)
EQUITY_FIELDS = (
    "capital", "profit_reserve", "special_reserve", "retained_earnings",
    "other_equity",
)
SGA_FIELDS = (
    "executive_compensation", "salaries", "retirement_allowance",
    "statutory_welfare", "welfare", "temporary_wages", "recruitment_fees",
    "advertising", "freight", "utilities", "fuel", "office_supplies",
    "consumables", "rent", "insurance", "repairs", "taxes_and_dues",
    "entertainment", "travel", "communication", "fees", "membership_fees",
    "card_fees", "lease", "depreciation", "miscellaneous_expenses", "other_sga",
)
PL_INPUT_FIELDS = (
    "sales", "opening_inventory", "purchases", "closing_inventory",
    *SGA_FIELDS, "interest_income", "dividend_income", "miscellaneous_income",
    "interest_expense", "guarantee_amortization", "miscellaneous_loss",
    "extraordinary_income", "fixed_asset_disposal_loss", "extraordinary_loss",
    "corporate_taxes",
)
ALL_FIELDS = (*ASSET_FIELDS, *LIABILITY_FIELDS, *EQUITY_FIELDS, *PL_INPUT_FIELDS)


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
        extraordinary_loss = values["fixed_asset_disposal_loss"] + values["extraordinary_loss"]
        pretax_profit = ordinary_profit + values["extraordinary_income"] - extraordinary_loss
        net_income = pretax_profit - values["corporate_taxes"]
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


annual_reports = AnnualReportManager()
