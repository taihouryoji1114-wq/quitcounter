from nicegui import ui

from core.auth import current_role, log_out
from pages.announcement_controls import announcement_player


def store_header_actions():
    announcement_player()
    with ui.row().classes("gap-0"):
        ui.button(icon="logout", on_click=lambda: log_out("/store-ops/login")).props(
            "flat round aria-label='ログアウト'").classes("text-grey-8")

def app_card(title, subtitle, icon, path, accent, badge_count=0):
    with ui.card().classes("store-app-card cursor-pointer q-pa-lg").on(
            "click", lambda _, target=path: ui.navigate.to(target)):
        if badge_count:
            ui.label(str(badge_count)).classes("store-app-badge")
        ui.icon(icon).classes(f"text-4xl {accent}")
        ui.label(title).classes("text-lg font-black q-mt-sm")
        ui.label(subtitle).classes("text-[10px] text-grey-6 q-mt-xs")
