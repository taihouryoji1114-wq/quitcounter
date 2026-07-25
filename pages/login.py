from nicegui import ui

from core.auth import is_authenticated, log_in, verify_pin
from core.theme import Theme


@ui.page("/login")
def login():
    Theme.page("Habitory ログイン")
    if is_authenticated():
        ui.navigate.to("/")
        return

    with ui.column().classes(
        "app-shell min-h-screen justify-center gap-0"
    ):
        ui.label("Habitory").classes("text-4xl font-bold metric-value")
        ui.label("あなたの習慣へ、おかえりなさい。").classes(
            "text-grey-7 q-mt-xs q-mb-xl"
        )
        with ui.card().classes("surface-card w-full q-pa-lg"):
            pin = ui.input("PIN").props(
                "outlined type=password inputmode=numeric autofocus"
            ).classes("w-full q-mb-md")

            def submit():
                if not verify_pin(pin.value):
                    pin.value = ""
                    ui.notify("PINが違います", type="negative")
                    return
                log_in()
                ui.navigate.to("/")

            pin.on("keydown.enter", lambda _: submit())
            ui.button(
                "ログイン", icon="lock_open", on_click=submit
            ).classes("w-full")
