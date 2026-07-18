from nicegui import ui

from core.data import data
from core.theme import Theme


@ui.page("/settings")
def settings():

    Theme.page("設定")

    user = data.get_user()

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

            data.save()

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