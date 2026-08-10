from nicegui import ui

from core.auth import log_out, require_login, select_user_for_browser, selected_user_id
from core.clock import today_jst_string
from core.data import data
from core.hydration import hydration
from core.nutrition import nutrition
from core.reading import reading
from core.theme import Theme
from core.utils import smoking_summary


HABITS = (
    {"title": "禁煙", "icon": "🚭", "accent": "#D96C63", "route": "/habitory/smoking"},
    {"title": "筋トレ", "icon": "💪", "accent": "#5B8269", "route": "/habitory/workout"},
    {"title": "読書", "icon": "📚", "accent": "#8B7BB8", "route": "/habitory/reading"},
    {"title": "カレンダー", "icon": "🗓️", "accent": "#B27A52", "route": "/habitory/calendar"},
    {"title": "水分", "icon": "💧", "accent": "#659BB9", "route": "/habitory/hydration"},
)


@ui.page("/habitory")
def home():
    if not require_login():
        return
    Theme.page("Habitory")

    def settings_action():
        with ui.row().classes("items-center gap-1"):
            ui.button(icon="settings", on_click=lambda: ui.navigate.to("/habitory/settings")).props("flat round").classes("text-grey-8")
            ui.button(icon="logout", on_click=log_out).props("flat round").classes("text-grey-8")

    content = Theme.shell("Habitory", "育てる、毎日の習慣", action=settings_action)
    page_user_id = selected_user_id()
    current_user = data.users.get_user(page_user_id)
    profile = current_user["profile"]
    summary = smoking_summary(page_user_id)
    hydration_summary = hydration.summary(user_id=page_user_id)
    nutrition_summary = nutrition.daily_summary(user_id=page_user_id)
    reading_seconds = reading.total_seconds(today_jst_string(), page_user_id)
    reading_goal = reading.get_goal_minutes(page_user_id)
    with content:
        ui.label(f"こんにちは、{profile['name']}さん").classes("section-kicker q-mb-sm")
        with ui.card().classes("surface-card w-full q-pa-md q-mb-md"):
            ui.label("ユーザーを選択").classes("section-kicker q-mb-sm")
            with ui.row().classes("w-full gap-2"):
                for user_id, user in data.users.get_users().items():
                    selected = user_id == page_user_id
                    ui.button(
                        user["profile"]["name"],
                        on_click=lambda _, value=user_id: switch_user(value),
                    ).props("unelevated" if selected else "outline").classes("flex-1")
        for habit in HABITS:
            subtitle = (
                f"{summary['days']}日続いています" if habit["title"] == "禁煙"
                else (
                    f"今日 {nutrition_summary['calories']}kcal"
                    f" / {nutrition_summary['protein']}gタンパク質"
                ) if habit["title"] == "筋トレ"
                else (
                    f"{hydration_summary['amount']} / {hydration_summary['goal']}ml"
                    if hydration_summary["goal"]
                    else f"{hydration_summary['amount']}ml"
                ) if habit["title"] == "水分"
                else (
                    f"今日 {reading_seconds // 60}分"
                    + (f" / 目標 {reading_goal}分" if reading_goal else "")
                ) if habit["title"] == "読書"
                else "すべての記録を振り返る" if habit["title"] == "カレンダー"
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
        select_user_for_browser(user_id)
        ui.navigate.reload()
