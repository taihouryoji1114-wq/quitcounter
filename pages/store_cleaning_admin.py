from nicegui import ui

from core.auth import require_app_access, require_permission
from core.store_cleaning import store_cleaning
from core.theme import Theme
from pages.store_common import store_header_actions


@ui.page("/store-ops/settings/cleaning")
def store_cleaning_admin_page():
    if not require_app_access("store_ops"):
        return
    if not require_permission("store_manage", "/store-ops"):
        return
    Theme.page("清掃設定｜店舗運営", app_name="store-ops")
    content = Theme.shell("清掃設定", "場所と清掃項目を自由に設定",
                          back_to="/store-ops/settings", action=store_header_actions,
                          brand="店舗運営")

    def reload(message=None):
        if message:
            ui.notify(message, type="positive")
        ui.navigate.to("/store-ops/settings/cleaning")

    with content:
        with ui.card().classes("surface-card w-full q-pa-lg"):
            ui.label("新しい清掃項目").classes("text-base font-black")
            area = ui.input("場所（例：厨房・ホール・トイレ）").props(
                "outlined dense maxlength=20").classes("w-full q-mt-sm")
            name = ui.input("清掃内容").props("outlined dense maxlength=40").classes(
                "w-full q-mt-xs")

            def add():
                try:
                    store_cleaning.save_template(name.value, area.value)
                except ValueError as error:
                    ui.notify(str(error), type="warning")
                    return
                reload("清掃項目を追加しました")

            ui.button("追加する", icon="add", on_click=add).props(
                "unelevated no-caps").classes("w-full q-mt-md")

        ui.label("登録済みの項目").classes("text-sm font-black q-mt-lg q-mb-xs")
        for item in store_cleaning.templates():
            with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                with ui.row().classes("w-full items-center no-wrap"):
                    with ui.column().classes("grow gap-0"):
                        ui.label(item["name"]).classes("text-sm font-black")
                        ui.label(item["area"]).classes("text-[9px] text-grey-6")
                    ui.button(icon="arrow_upward", on_click=lambda _, selected=item:
                              (store_cleaning.move_template(selected["id"], -1), reload())).props(
                        "flat round dense aria-label='上へ'")
                    ui.button(icon="arrow_downward", on_click=lambda _, selected=item:
                              (store_cleaning.move_template(selected["id"], 1), reload())).props(
                        "flat round dense aria-label='下へ'")
                    ui.button(icon="delete_outline", on_click=lambda _, selected=item:
                              (store_cleaning.delete_template(selected["id"]),
                               reload("削除しました"))).props(
                        "flat round dense color=negative aria-label='削除'")
