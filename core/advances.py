"""Independent personal advances; never feed accounting or purchase totals."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from core.data import data


class AdvanceManager:
    def __init__(self, manager=None):
        self.manager = manager or data

    def state(self):
        return self.manager.data.get("personal_advances", {})

    def names(self):
        return self.state().get("names", ["立替者1", "立替者2", "立替者3"])

    def save_names(self, names):
        names = [str(name or "").strip() for name in names]
        if len(names) != 3 or any(not n or len(n) > 20 for n in names) or len(set(names)) != 3:
            raise ValueError("異なる3人の名前を20文字以内で入力してください。")
        self.manager.data.setdefault("personal_advances", {})["names"] = names
        self.manager.save()

    @staticmethod
    def amounts(values):
        try:
            numbers = [Decimal(str(v or 0)) for v in values]
            if len(numbers) != 3 or any(not n.is_finite() or n < 0 or n != n.to_integral_value() or n > 999999999 for n in numbers):
                raise ValueError()
            return [int(n) for n in numbers]
        except (ValueError, InvalidOperation, TypeError):
            raise ValueError("3人分の金額を0以上の整数で入力してください。")

    def totals(self):
        paid = [sum(row[i] for row in self.state().get("months", {}).values()) for i in range(3)]
        returned = [sum(r["amounts"][i] for r in self.state().get("refunds", []) if not r.get("voided")) for i in range(3)]
        return paid, returned, [paid[i] - returned[i] for i in range(3)]

    def save_month(self, month, values):
        if datetime.strptime(month, "%Y-%m").strftime("%Y-%m") != month:
            raise ValueError("対象月を選んでください。")
        values = self.amounts(values)
        previous = self.state().get("months", {}).get(month, [0, 0, 0])
        remaining = self.totals()[2]
        if any(remaining[i] - previous[i] + values[i] < 0 for i in range(3)):
            raise ValueError("返金済み額を下回ります。先に誤った返金記録を取り消してください。")
        self.manager.data.setdefault("personal_advances", {}).setdefault("months", {})[month] = values
        self.manager.save()

    def refund(self, day, values, request_id=None):
        if request_id and any(r["id"] == request_id for r in self.state().get("refunds", [])):
            return
        if datetime.strptime(day, "%Y-%m-%d").strftime("%Y-%m-%d") != day:
            raise ValueError("返金日を選んでください。")
        amounts = self.amounts(values)
        if not sum(amounts):
            raise ValueError("返金額を入力してください。")
        remaining = self.totals()[2]
        if any(amounts[i] > remaining[i] for i in range(3)):
            raise ValueError("各人の未返金額を超えて返金できません。")
        self.manager.data.setdefault("personal_advances", {}).setdefault("refunds", []).append(
            {"id": request_id or uuid4().hex, "day": day, "amounts": amounts})
        self.manager.save()

    def void_refund(self, record_id):
        for record in self.state().get("refunds", []):
            if record["id"] == record_id:
                record["voided"] = True
                self.manager.save()
                return
        raise ValueError("返金記録が見つかりません。")


advances = AdvanceManager()
