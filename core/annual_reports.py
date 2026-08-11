"""Independent annual financial statements and management diagnosis."""

from __future__ import annotations

from core.data import data


ASSET_FIELDS = (
    "cash", "receivables", "inventory", "prepaid", "other_current_assets",
    "buildings", "vehicles", "equipment", "intangible_assets", "deposits",
    "investments", "other_fixed_assets",
)
LIABILITY_FIELDS = (
    "payables", "short_term_loans", "accrued_expenses", "unpaid_taxes",
    "other_current_liabilities", "long_term_loans", "other_fixed_liabilities",
)
EQUITY_FIELDS = ("capital", "capital_reserves", "retained_earnings")
SGA_FIELDS = (
    "executive_compensation", "salaries", "statutory_welfare", "welfare",
    "rent", "utilities", "depreciation", "advertising", "travel",
    "communication", "fees", "supplies", "taxes_and_dues", "insurance",
    "repairs", "other_sga",
)
PL_INPUT_FIELDS = (
    "sales", "opening_inventory", "purchases", "closing_inventory",
    *SGA_FIELDS, "non_operating_income", "non_operating_expense",
    "extraordinary_income", "extraordinary_loss", "corporate_taxes",
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
            amount = int(float(str(value or 0).replace(",", "")))
        except (TypeError, ValueError) as error:
            raise ValueError("金額は数字で入力してください。") from error
        return amount

    def list_periods(self):
        reports = self._data_manager.data.get("business_annual_reports", {})
        return sorted(reports, reverse=True) if isinstance(reports, dict) else []

    def get_report(self, period):
        period = self._period(period)
        reports = self._data_manager.data.get("business_annual_reports", {})
        stored = reports.get(period, {}) if isinstance(reports, dict) else {}
        return {
            "period": period,
            "current": {key: self._amount(stored.get("current", {}).get(key, 0)) for key in ALL_FIELDS},
            "previous": {key: self._amount(stored.get("previous", {}).get(key, 0)) for key in ALL_FIELDS},
        }

    def save_report(self, period, current, previous):
        period = self._period(period)
        cleaned = {
            "current": {key: self._amount((current or {}).get(key, 0)) for key in ALL_FIELDS},
            "previous": {key: self._amount((previous or {}).get(key, 0)) for key in ALL_FIELDS},
        }
        self._data_manager.data.setdefault("business_annual_reports", {})[period] = cleaned
        self._data_manager.save()
        return self.get_report(period)

    @staticmethod
    def calculate(values):
        values = {key: int(values.get(key, 0) or 0) for key in ALL_FIELDS}
        current_assets = sum(values[key] for key in ASSET_FIELDS[:5])
        fixed_assets = sum(values[key] for key in ASSET_FIELDS[5:])
        current_liabilities = sum(values[key] for key in LIABILITY_FIELDS[:5])
        fixed_liabilities = sum(values[key] for key in LIABILITY_FIELDS[5:])
        equity = sum(values[key] for key in EQUITY_FIELDS)
        cogs = values["opening_inventory"] + values["purchases"] - values["closing_inventory"]
        gross_profit = values["sales"] - cogs
        sga = sum(values[key] for key in SGA_FIELDS)
        operating_profit = gross_profit - sga
        ordinary_profit = operating_profit + values["non_operating_income"] - values["non_operating_expense"]
        pretax_profit = ordinary_profit + values["extraordinary_income"] - values["extraordinary_loss"]
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
            "quick_ratio": (values["cash"] + values["receivables"]) / current_liabilities if current_liabilities else None,
            "equity_ratio": equity / assets if assets else None,
            "operating_margin": operating_profit / values["sales"] if values["sales"] else None,
            "gross_margin": gross_profit / values["sales"] if values["sales"] else None,
            "debt_to_sales": (values["short_term_loans"] + values["long_term_loans"]) / values["sales"] if values["sales"] else None,
            "cash_months": values["cash"] / (values["sales"] / 12) if values["sales"] else None,
        }


annual_reports = AnnualReportManager()
