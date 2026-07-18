from nicegui import ui

from core.data import data
from core.utils import calculate
from core.theme import Theme


def change_user(index):
    data.change_user(index)
    ui.navigate.reload()


@ui.page("/smoking")
def smoking():

    Theme.page("禁煙")

    result = calculate()

    with ui.column().classes("w-full items-center q-pa-xl"):

        # タイトル
        ui.label("🚭 禁煙").classes(
            "text-4xl font-bold"
        )

        ui.space().style("height:20px")

        # ユーザー切替
        with ui.row().classes("gap-2"):

            for index, user in enumerate(data.data["users"]):

                color = (
                    "primary"
                    if index == data.current_user
                    else "grey"
                )

                ui.button(
                    user["name"],
                    color=color,
                    on_click=lambda i=index: change_user(i),
                )

        ui.space().style("height:20px")

        # 継続日数
        ui.label("継続日数").classes(
            "text-grey-6"
        )

        ui.label(
            str(result["days"])
        ).classes("text-8xl font-bold")

        ui.label("DAYS").classes(
            "text-2xl text-grey-6"
        )

        ui.space().style("height:20px")

        # 吸わなかった本数
        with ui.card().classes("w-80"):

            ui.label("🚬 吸わなかった本数").classes(
                "text-sm text-grey-7"
            )

            ui.label(
                f'{result["cigarettes"]}本'
            ).classes("text-3xl font-bold")

        ui.space().style("height:12px")

        # 節約金額
        with ui.card().classes("w-80"):

            ui.label("💰 節約金額").classes(
                "text-sm text-grey-7"
            )

            ui.label(
                f'¥{result["money"]:,.0f}'
            ).classes(
                "text-3xl font-bold text-green"
            )

        ui.space().style("height:12px")

        # 浮いた時間
        with ui.card().classes("w-80"):

            ui.label("⏰ 浮いた時間").classes(
                "text-sm text-grey-7"
            )

            ui.label(
                f'{result["hours"]}時間 {result["mins"]}分'
            ).classes("text-3xl font-bold")

        ui.space().style("height:30px")

        ui.button(
            "🏠 ホーム",
            on_click=lambda: ui.navigate.to("/"),
        ).classes("w-80")

        ui.space().style("height:10px")

        ui.button(
            "⚙️ 設定",
            on_click=lambda: ui.navigate.to("/settings"),
        ).classes("w-80")