from nicegui import app, ui

from core.auth import current_role, log_out


def store_header_actions():
    with ui.row().classes("gap-0"):
        if current_role() == "owner" and app.storage.user.get("return_to_chankocchi"):
            ui.button(icon="pets", on_click=lambda: ui.navigate.to("/chankocchi")).props(
                "flat round aria-label='ちゃんこっちへ戻る'").classes("text-amber-8")
        ui.button(icon="logout", on_click=lambda: log_out("/store-ops/login")).props(
            "flat round aria-label='ログアウト'").classes("text-grey-8")

def app_card(title, subtitle, icon, path, accent):
    with ui.card().classes("store-app-card cursor-pointer q-pa-lg").on(
            "click", lambda _, target=path: ui.navigate.to(target)):
        ui.icon(icon).classes(f"text-4xl {accent}")
        ui.label(title).classes("text-lg font-black q-mt-sm")
        ui.label(subtitle).classes("text-[10px] text-grey-6 q-mt-xs")
