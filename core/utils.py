from datetime import date, datetime

from core.data import data


def calculate():

    user = data.get_user()

    start_date = datetime.strptime(
        user["start_date"],
        "%Y-%m-%d",
    ).date()

    days = (date.today() - start_date).days

    cigarettes = days * user["cigarettes_per_day"]

    money = cigarettes * (
        user["price_per_pack"] / 20
    )

    minutes = cigarettes * 5

    hours = minutes // 60
    mins = minutes % 60

    return {
        "days": days,
        "cigarettes": cigarettes,
        "money": money,
        "hours": hours,
        "mins": mins,
    }


def days_ago(text_date: str):

    workout_date = datetime.strptime(
        text_date,
        "%Y-%m-%d",
    ).date()

    diff = (date.today() - workout_date).days

    if diff == 0:
        return "今日"

    if diff == 1:
        return "昨日"

    return f"{diff}日前"