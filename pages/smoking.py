from nicegui import ui

from core.auth import require_login, selected_user_id
from core.data import data
from core.theme import Theme
from core.utils import smoking_summary


@ui.page("/habitory/smoking")
def smoking():
    if not require_login():
        return
    Theme.page("禁煙")
    page_user_id = selected_user_id()
    summary = smoking_summary(page_user_id)
    content = Theme.shell("禁煙", "静かな毎日の積み重ね", back_to="/habitory")
    with content:
        with ui.card().classes("hero-card w-full q-pa-xl q-mb-md"):
            ui.label("継続日数").classes("section-kicker")
            with ui.row().classes("items-end q-mt-sm"):
                ui.label(str(summary["days"])).classes("text-7xl font-bold metric-value")
                ui.label("日").classes("text-2xl text-grey-7 q-ml-sm q-mb-sm")
            ui.label("今日も、あなたのペースで。").classes("text-grey-7 q-mt-sm")
        with ui.element("div").classes("grid grid-cols-2 gap-3 w-full q-mb-md"):
            for label, value in (("節約金額", f"¥{summary['money']:,.0f}"), ("吸わなかった本数", f"{summary['cigarettes']:,} 本")):
                with ui.card().classes("surface-card q-pa-md"):
                    ui.label(label).classes("text-grey-7 text-sm")
                    ui.label(value).classes("text-2xl font-bold metric-value q-mt-sm")
        with ui.card().classes("surface-card w-full q-pa-md"):
            ui.label("浮いた時間").classes("text-grey-7 text-sm")
            ui.label(f"{summary['hours']}時間 {summary['mins']}分").classes("text-2xl font-bold metric-value q-mt-sm")
