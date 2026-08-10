from nicegui import ui

from core.auth import log_out, require_login
from core.theme import Theme


@ui.page("/")
def portal():
    if not require_login():
        return
    Theme.page("R-BASE")

    def logout_action():
        ui.button(icon="logout", on_click=log_out).props("flat round").classes(
            "text-grey-8"
        )

    content = Theme.shell(
        "アプリ一覧",
        "使いたいアプリを選ぶ",
        action=logout_action,
        brand="R-BASE",
    )
    with content:
        with ui.card().classes(
            "habit-card w-full q-pa-lg q-mb-md cursor-pointer"
        ).on("click", lambda _: ui.navigate.to("/habitory")):
            with ui.row().classes("w-full items-center no-wrap"):
                ui.image("/static/habitory_icon.png").classes(
                    "w-14 h-14 rounded-xl q-mr-md"
                )
                with ui.column().classes("gap-0"):
                    ui.label("Habitory").classes("text-xl font-bold")
                    ui.label("毎日の習慣と健康記録").classes(
                        "text-grey-7 q-mt-xs"
                    )
                ui.space()
                ui.icon("chevron_right").classes("text-2xl text-grey-7")

        with ui.card().classes(
            "habit-card w-full q-pa-lg q-mb-md cursor-pointer"
        ).on("click", lambda _: ui.navigate.to("/mirai-kessan")):
            with ui.row().classes("w-full items-center no-wrap"):
                ui.image("/static/mirai_kessan_icon.png").classes(
                    "w-14 h-14 rounded-xl q-mr-md"
                )
                with ui.column().classes("gap-0"):
                    ui.label("未来決算").classes("text-xl font-bold")
                    ui.label("利益目標から、必要な売上を逆算").classes(
                        "text-grey-7 q-mt-xs"
                    )
                ui.space()
                ui.icon("chevron_right").classes("text-2xl text-grey-7")
