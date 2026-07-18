from nicegui import app, ui
from datetime import date, datetime
import json

app.add_static_files('/static', 'static')

DATA_FILE = 'data.json'


def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "current_user": 0,
            "users": [
                {
                    "name": "良治",
                    "start_date": "2026-07-12",
                    "cigarettes_per_day": 10,
                    "price_per_pack": 1000
                },
                {
                    "name": "胡花",
                    "start_date": "2026-07-12",
                    "cigarettes_per_day": 10,
                    "price_per_pack": 1000
                }
            ]
        }


data = load_data()
current_user = data.get("current_user", 0)


def save_data():
    data["current_user"] = current_user

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4,
        )


def get_user():
    return data["users"][current_user]


def change_user(index):
    global current_user

    current_user = index

    save_data()

    ui.navigate.reload()
def calculate():

    user = get_user()

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


@ui.page("/")
def home():

    result = calculate()

    with ui.column().classes(
        "w-full items-center q-pa-xl"
    ):

        with ui.row().classes("gap-2"):

            ui.button(
                "良治",
                on_click=lambda: change_user(0),
            )

            ui.button(
                "胡花",
                on_click=lambda: change_user(1),
            )

        ui.space().style("height:20px")

        ui.label("🚭").classes("text-6xl")

        ui.label(
            str(result["days"])
        ).classes("text-8xl font-bold")
        ui.label(
            "DAYS"
        ).classes("text-2xl text-grey-6")

        ui.space().style("height:20px")

        with ui.card().classes("w-80"):

            ui.label(
                "🚬 吸わなかった本数"
            ).classes("text-sm text-grey-7")

            ui.label(
                f'{result["cigarettes"]}本'
            ).classes("text-3xl font-bold")

        ui.space().style("height:12px")

        with ui.card().classes("w-80"):

            ui.label(
                "💰 節約金額"
            ).classes("text-sm text-grey-7")

            ui.label(
                f'¥{result["money"]:,.0f}'
            ).classes("text-3xl font-bold text-green")

        ui.space().style("height:12px")

        with ui.card().classes("w-80"):

            ui.label(
                "⏰ 浮いた時間"
            ).classes("text-sm text-grey-7")

            ui.label(
                f'{result["hours"]}時間 {result["mins"]}分'
            ).classes("text-3xl font-bold")

        ui.space().style("height:25px")

        ui.button(
            "⚙️ 設定",
            on_click=lambda: ui.navigate.to("/settings"),
        ).classes("w-80")


@ui.page("/settings")
def settings():

    user = get_user()

    with ui.column().classes(
        "w-full items-center q-pa-xl"
    ):

        ui.label(
            "⚙️ 設定"
        ).classes("text-3xl font-bold")
        name = ui.input(
            "名前",
            value=user["name"],
        ).classes("w-80")

        start = ui.input(
            "禁煙開始日",
            value=user["start_date"],
        ).classes("w-80")

        cigs = ui.number(
            "1日の本数",
            value=user["cigarettes_per_day"],
        ).classes("w-80")

        price = ui.number(
            "1箱の値段",
            value=user["price_per_pack"],
        ).classes("w-80")

        def save():
            user["name"] = name.value
            user["start_date"] = start.value
            user["cigarettes_per_day"] = int(cigs.value)
            user["price_per_pack"] = int(price.value)

            save_data()

            ui.notify("保存しました！")

            ui.navigate.to("/")

        ui.space().style("height:20px")

        ui.button(
            "💾 保存",
            on_click=save,
        ).classes("w-80")

        ui.space().style("height:10px")

        ui.button(
            "← ホームへ戻る",
            on_click=lambda: ui.navigate.to("/"),
        ).classes("w-80")


ui.run(
    title="Habitory",
    host="0.0.0.0",
    port=8080,
    reload=True,
    favicon="static/habitory_icon.png",
)