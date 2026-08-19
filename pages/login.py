from nicegui import ui

from core.auth import authenticate_pin, can_access, is_authenticated, log_in
from core.theme import Theme


def login_screen(app_id, name, destination, subtitle, app_name="habitory"):
    Theme.page(f"{name} ログイン", app_name=app_name)
    if is_authenticated() and can_access(app_id):
        ui.navigate.to(destination)
        return

    with ui.column().classes(
        "app-shell min-h-screen justify-center gap-0"
    ):
        ui.label(name).classes("text-4xl font-bold metric-value")
        ui.label(subtitle).classes(
            "text-grey-7 q-mt-xs q-mb-xl"
        )
        with ui.card().classes("surface-card w-full q-pa-lg"):
            pin = ui.input("PIN").props(
                "outlined type=password inputmode=numeric autofocus"
            ).classes("w-full q-mb-md")

            def submit():
                account = authenticate_pin(pin.value, app_id)
                if not account:
                    pin.value = ""
                    ui.notify("PINが違います", type="negative")
                    return
                log_in(account)
                ui.navigate.to(destination)

            pin.on("keydown.enter", lambda _: submit())
            ui.button(
                "ログイン", icon="lock_open", on_click=submit
            ).classes("w-full")


@ui.page("/login")
def login():
    login_screen("portal", "R-BASE", "/", "良治さん専用の管理入口")


@ui.page("/habitory/login")
def habitory_login():
    login_screen("habitory", "Habitory", "/habitory", "自分の習慣と健康記録")


@ui.page("/store-ops/login")
def store_ops_login():
    login_screen("store_ops", "店舗運営", "/store-ops", "今日の店舗確認を始める",
                 app_name="store-ops")


@ui.page("/mirai-kessan/login")
def future_financials_login():
    login_screen("future_financials", "未来決算", "/mirai-kessan",
                 "会社の数字を確認する", app_name="mirai-kessan")


@ui.page("/schedule/login")
def schedule_login():
    login_screen("schedule", "My Schedule", "/schedule", "自分だけの予定を開く")
