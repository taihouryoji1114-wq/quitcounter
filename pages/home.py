from nicegui import ui

from core.auth import current_role, log_out, require_app_access, select_user_for_browser, selected_user_id
from core.clock import today_jst_string
from core.data import data
from core.hydration import hydration
from core.nutrition import nutrition
from core.reading import reading
from core.theme import Theme
from core.utils import smoking_summary


HABITS = (
    {"title": "禁煙", "icon": "smoke_free", "accent": "#C85F5A", "tint": "#FBE9E7", "route": "/habitory/smoking"},
    {"title": "筋トレ", "icon": "fitness_center", "accent": "#44755C", "tint": "#E5F1EA", "route": "/habitory/workout"},
    {"title": "読書", "icon": "auto_stories", "accent": "#7463A4", "tint": "#EEEAF8", "route": "/habitory/reading"},
    {"title": "カレンダー", "icon": "calendar_month", "accent": "#A66A43", "tint": "#F8ECE3", "route": "/habitory/calendar"},
    {"title": "水分", "icon": "water_drop", "accent": "#4D88A8", "tint": "#E4F1F7", "route": "/habitory/hydration"},
)


@ui.page("/habitory")
def home():
    if not require_app_access("habitory"):
        return
    Theme.page("Habitory")

    def settings_action():
        with ui.row().classes("items-center gap-1"):
            if current_role() == "owner":
                ui.button(icon="apps", on_click=lambda: ui.navigate.to("/")).props(
                    "flat round aria-label='R-BASEへ戻る'").classes("text-grey-8")
            ui.button(icon="settings", on_click=lambda: ui.navigate.to("/habitory/settings")).props("flat round").classes("text-grey-8")
            ui.button(icon="logout", on_click=lambda: log_out("/habitory/login")).props(
                "flat round").classes("text-grey-8")

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
        if current_role() == "owner":
            with ui.card().classes("surface-card w-full q-pa-md q-mb-md"):
                ui.label("ユーザーを選択").classes("section-kicker q-mb-sm")
                with ui.row().classes("w-full gap-2"):
                    for user_id, user in data.users.get_users().items():
                        selected = user_id == page_user_id
                        ui.button(
                            user["profile"]["name"],
                            on_click=lambda _, value=user_id: switch_user(value),
                        ).props("unelevated" if selected else "outline").classes("flex-1")
        with ui.element("div").classes("habitory-grid w-full"):
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
                with ui.card().classes("habitory-tile cursor-pointer").on(
                    "click", lambda _, route=habit["route"]: ui.navigate.to(route)
                ):
                    with ui.row().classes("w-full items-center no-wrap gap-3"):
                        with ui.element("div").classes("habitory-icon").style(
                            f"background:{habit['tint']};color:{habit['accent']}"
                        ):
                            ui.icon(habit["icon"])
                        with ui.column().classes("gap-0 min-w-0 grow"):
                            ui.label(habit["title"]).classes("habitory-title")
                            ui.label(subtitle).classes("habitory-subtitle")
                        ui.icon("arrow_forward_ios").style(
                            f"color:{habit['accent']}"
                        ).classes("habitory-arrow")

        ui.add_css("""
        .habitory-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}
        .habitory-tile{min-width:0;min-height:116px;padding:15px 13px!important;border-radius:22px!important;background:rgba(255,255,255,.96)!important;border:1px solid #E5E9E5!important;box-shadow:0 9px 25px rgba(42,61,50,.07)!important}
        .habitory-tile:last-child{grid-column:1/-1;min-height:92px}
        .habitory-icon{width:42px;height:42px;flex:0 0 42px;display:flex;align-items:center;justify-content:center;border-radius:14px;font-size:23px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.65)}
        .habitory-title{font-size:15px;font-weight:900;line-height:1.25}.habitory-subtitle{max-width:100%;margin-top:4px;color:#758079;font-size:9px;font-weight:650;line-height:1.35;overflow-wrap:anywhere}.habitory-arrow{font-size:13px;opacity:.62}
        @media(min-width:560px){.habitory-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.habitory-tile:last-child{grid-column:auto;min-height:116px}}
        """)

    def switch_user(user_id):
        select_user_for_browser(user_id)
        ui.navigate.reload()
