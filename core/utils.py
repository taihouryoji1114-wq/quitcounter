from datetime import datetime

from core.clock import today_jst
from core.data import data


def smoking_summary(user_id=None):
    smoking = data.get_smoking(user_id)
    start_date = datetime.strptime(smoking["start_date"], "%Y-%m-%d").date()
    days = max(0, (today_jst() - start_date).days)
    cigarettes = days * smoking["cigarettes_per_day"]
    money = cigarettes * (smoking["price_per_pack"] / 20)
    minutes = cigarettes * 5
    return {"days": days, "cigarettes": cigarettes, "money": money, "hours": minutes // 60, "mins": minutes % 60}


def days_ago(text_date):
    difference = (today_jst() - datetime.strptime(text_date, "%Y-%m-%d").date()).days
    return "今日" if difference == 0 else "昨日" if difference == 1 else f"{difference}日前"
