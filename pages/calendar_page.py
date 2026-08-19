import calendar
from datetime import date

from nicegui import ui

from core.auth import require_app_access, selected_user_id
from core.clock import today_jst
from core.data import data
from core.hydration import hydration
from core.nutrition import nutrition
from core.reading import reading
from core.theme import Theme


PART_COLORS = {
    "胸": "#CF6C6C", "背中": "#668BC9", "脚": "#5F9A73",
    "肩": "#C9A64B", "腕": "#9271B8", "腹筋": "#D88B50",
}


def show_day(record_date, user_id):
    workout = data.get_workout_for_date(record_date, user_id)
    meals = nutrition.get_meal_records(record_date, user_id)
    totals = nutrition.daily_summary(record_date, user_id)
    water = hydration.summary(record_date, user_id)["amount"]
    reading_seconds = reading.total_seconds(record_date, user_id)

    with ui.dialog() as dialog, ui.card().classes(
        "surface-card w-96 max-w-full q-pa-lg"
    ):
        ui.label(record_date).classes("text-2xl font-bold")
        ui.label("この日の記録").classes("text-grey-7 q-mb-md")

        ui.label("💪 筋トレ").classes("font-bold q-mb-xs")
        if workout:
            with ui.row().classes("gap-2 flex-wrap q-mb-md"):
                for part in workout["body_parts"]:
                    ui.badge(part).style(f"background:{PART_COLORS[part]}")
        else:
            ui.label("記録なし").classes("text-sm text-grey-6 q-mb-md")

        ui.label("🍽️ 食事").classes("font-bold q-mb-xs")
        if meals:
            for period in ("朝", "昼", "夜", "その他"):
                period_meals = [
                    meal for meal in meals
                    if meal.get("meal_period", "その他") == period
                ]
                for meal in period_meals:
                    ui.label(
                        f"{period}・{meal['food_name']}  "
                        f"{meal['calories']}kcal / {meal['protein']}g"
                    ).classes("text-sm text-grey-7")
            ui.label(
                f"合計 {totals['calories']}kcal・タンパク質 {totals['protein']}g"
            ).classes("font-bold q-mt-xs q-mb-md")
        else:
            ui.label("記録なし").classes("text-sm text-grey-6 q-mb-md")

        with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
            with ui.card().classes("bg-blue-1 q-pa-sm"):
                ui.label("💧 水分").classes("text-xs text-grey-7")
                ui.label(f"{water}ml").classes("font-bold")
            with ui.card().classes("bg-purple-1 q-pa-sm"):
                ui.label("📚 読書").classes("text-xs text-grey-7")
                ui.label(f"{reading_seconds // 60}分").classes("font-bold")

        ui.button("閉じる", on_click=dialog.close).props("flat").classes(
            "w-full q-mt-md"
        )
    dialog.open()


@ui.page("/habitory/calendar")
def calendar_page():
    if not require_app_access("habitory"):
        return
    Theme.page("カレンダー")
    user_id = selected_user_id()
    today = today_jst()
    display_month = [today.replace(day=1)]
    content = Theme.shell(
        "カレンダー", "毎日の積み重ねを、ひとつの場所で。", back_to="/habitory"
    )

    with content:
        @ui.refreshable
        def calendar_view():
            workout_dates = {
                item["date"] for item in data.get_workout_records(user_id)
            }
            meal_dates = {
                item["date"] for item in nutrition.get_meal_records(user_id=user_id)
            }
            water_dates = {
                item["date"] for item in hydration.get_records(user_id)
                if item.get("amount", 0) > 0
            }
            reading_dates = {
                item["date"] for item in reading.sessions(user_id=user_id)
            }
            active_reading = reading.active_started_at(user_id)
            if active_reading:
                reading_dates.add(active_reading.date().isoformat())

            with ui.card().classes("surface-card w-full q-pa-sm"):
                with ui.row().classes(
                    "w-full items-center justify-between no-wrap q-mb-sm"
                ):
                    ui.button(
                        icon="chevron_left", on_click=lambda: change_month(-1)
                    ).props("flat round")
                    ui.label(
                        f"{display_month[0].year}年 {display_month[0].month}月"
                    ).classes("text-lg font-bold")
                    with ui.row().classes("items-center no-wrap"):
                        ui.button("今日", on_click=go_today).props("flat dense")
                        ui.button(
                            icon="chevron_right", on_click=lambda: change_month(1)
                        ).props("flat round")

                with ui.element("div").classes("grid grid-cols-7 gap-1 w-full"):
                    for weekday in ("月", "火", "水", "木", "金", "土", "日"):
                        ui.label(weekday).classes(
                            "text-center text-grey-7 text-xs"
                        )
                    for week in calendar.monthcalendar(
                        display_month[0].year, display_month[0].month
                    ):
                        for number in week:
                            if not number:
                                ui.element("div").classes("min-h-[76px]")
                                continue
                            current = date(
                                display_month[0].year,
                                display_month[0].month,
                                number,
                            )
                            day = current.isoformat()
                            classes = "calendar-day q-pa-xs cursor-pointer"
                            if current == today:
                                classes += " today-calendar-day"
                            with ui.card().classes(classes).on(
                                "click", lambda _, value=day: show_day(value, user_id)
                            ):
                                ui.label(str(number)).classes(
                                    "today-date-number"
                                    if current == today else "text-xs font-bold"
                                )
                                with ui.row().classes("gap-1 q-mt-xs flex-wrap"):
                                    if day in workout_dates:
                                        ui.label("💪").classes("text-xs")
                                    if day in meal_dates:
                                        ui.label("🍽️").classes("text-xs")
                                    if day in water_dates:
                                        ui.label("💧").classes("text-xs")
                                    if day in reading_dates:
                                        ui.label("📚").classes("text-xs")

        def change_month(offset):
            year = display_month[0].year
            month = display_month[0].month + offset
            if month == 0:
                year, month = year - 1, 12
            elif month == 13:
                year, month = year + 1, 1
            display_month[0] = date(year, month, 1)
            calendar_view.refresh()

        def go_today():
            display_month[0] = today.replace(day=1)
            calendar_view.refresh()

        calendar_view()
        ui.label("💪 筋トレ　🍽️ 食事　💧 水分　📚 読書").classes(
            "text-xs text-grey-7 q-mt-sm text-center w-full"
        )
