from nicegui import ui

from core.theme import Theme, habit_card
from core.data import data
from core.utils import days_ago


@ui.page("/")
def home():

    Theme.page("Habitory")

    workouts = data.get_workouts()

    if workouts:
        latest = max(workouts, key=lambda x: x["date"])
        workout_subtitle = days_ago(latest["date"])
    else:
        workout_subtitle = "まだ記録なし"

    with ui.column().classes("w-full items-center q-pa-xl"):

        ui.label("🐰").classes("text-6xl")

        ui.label("Habitory").classes(
            "text-3xl font-bold"
        )

        ui.label(
            "習慣を育てよう"
        ).classes("text-grey-6")

        ui.space().style("height:25px")

        habit_card(
            icon="🚭",
            title="禁煙",
            subtitle=f'{len(data.data["users"])}人管理中',
            color="red",
            callback=lambda: ui.navigate.to("/smoking"),
        )

        ui.space().style("height:12px")

        habit_card(
            icon="💪",
            title="筋トレ",
            subtitle=workout_subtitle,
            color="orange",
            callback=lambda: ui.navigate.to("/workout"),
        )

        ui.space().style("height:12px")

        habit_card(
            icon="📖",
            title="読書",
            subtitle="近日追加",
            color="blue",
            callback=lambda: ui.notify("開発中です🚧"),
        )

        ui.space().style("height:12px")

        habit_card(
            icon="💧",
            title="水分",
            subtitle="近日追加",
            color="cyan",
            callback=lambda: ui.notify("開発中です🚧"),
        )

        ui.space().style("height:24px")

        ui.button(
            "⚙️ 設定",
            icon="settings",
            on_click=lambda: ui.navigate.to("/settings"),
        ).classes("w-80")