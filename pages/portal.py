from nicegui import ui

from core.auth import log_out, require_login
from core.theme import Theme


@ui.page("/")
def portal():
    if not require_login():
        return
    Theme.page("マイアプリ")

    def logout_action():
        ui.button(icon="logout", on_click=log_out).props("flat round").classes(
            "text-grey-8"
        )

    content = Theme.shell(
        "マイアプリ",
        "使いたいアプリを選ぶ",
        action=logout_action,
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
            "surface-card w-full q-pa-lg q-mb-md"
        ):
            ui.label("次のアプリ").classes("section-kicker")
            ui.label("Project Life").classes("text-xl font-bold q-mt-xs")
            ui.label("準備ができたら、ここへ追加します。").classes(
                "text-grey-7 q-mt-xs"
            )
