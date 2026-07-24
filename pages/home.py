from nicegui import ui

from core.data import data
from core.hydration import hydration
from core.theme import Theme
from core.utils import smoking_summary


HABITS = (
    {"title": "禁煙", "icon": "🚭", "accent": "#D96C63", "route": "/smoking"},
    {"title": "筋トレ", "icon": "💪", "accent": "#5B8269", "route": "/workout"},
    {"title": "読書", "icon": "📚", "accent": "#8B7BB8", "route": None},
    {"title": "水分", "icon": "💧", "accent": "#659BB9", "route": "/hydration"},
)


@ui.page("/")
def home():
    Theme.page("Habitory")

    def settings_action():
        ui.button(icon="settings", on_click=lambda: ui.navigate.to("/settings")).props("flat round").classes("text-grey-8")

    content = Theme.shell("Habitory", "育てる、毎日の習慣", action=settings_action)
    current_user = data.get_current_user()
    profile = current_user["profile"]
    page_user_id = data.active_user_id
    summary = smoking_summary(page_user_id)
    hydration_summary = hydration.summary(user_id=page_user_id)
    with content:
        ui.label(f"こんにちは、{profile['name']}さん").classes("section-kicker q-mb-sm")
        with ui.card().classes("surface-card w-full q-pa-md q-mb-md"):
            ui.label("ユーザーを選択").classes("section-kicker q-mb-sm")
            with ui.row().classes("w-full gap-2"):
                for user_id, user in data.users.get_users().items():
                    selected = user_id == data.active_user_id
                    ui.button(
                        user["profile"]["name"],
                        on_click=lambda _, value=user_id: switch_user(value),
                    ).props("unelevated" if selected else "outline").classes("flex-1")
        for habit in HABITS:
            subtitle = (
                f"{summary['days']}日続いています" if habit["title"] == "禁煙"
                else "今日の記録を残す" if habit["title"] == "筋トレ"
                else (
                    f"{hydration_summary['amount']} / {hydration_summary['goal']}ml"
                    if hydration_summary["goal"]
                    else f"{hydration_summary['amount']}ml"
                ) if habit["title"] == "水分"
                else "近日公開"
            )
            with ui.card().classes("habit-card w-full q-pa-lg q-mb-md cursor-pointer").on(
                "click", lambda _, route=habit["route"]: ui.navigate.to(route) if route else ui.notify("近日公開です", type="info")
            ):
                with ui.row().classes("w-full items-center no-wrap"):
                    ui.label(habit["icon"]).classes("text-4xl q-mr-md")
                    with ui.column().classes("gap-0"):
                        ui.label(habit["title"]).classes("text-xl font-bold")
                        ui.label(subtitle).classes("text-grey-7 q-mt-xs")
                    ui.space()
                    ui.icon("chevron_right").style(f"color: {habit['accent']}").classes("text-2xl")

    def switch_user(user_id):
        data.select_user(user_id)
        ui.navigate.reload()
