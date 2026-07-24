import calendar
from datetime import date

from nicegui import ui

from core.calories import nutrition_settings
from core.data import BODY_PARTS, data
from core.nutrition import nutrition
from core.theme import Theme
from core.utils import days_ago


PART_COLORS = {"胸": "#CF6C6C", "背中": "#668BC9", "脚": "#5F9A73", "肩": "#C9A64B", "腕": "#9271B8", "腹筋": "#D88B50"}


def record_dialog(record_date, parts):
    with ui.dialog() as dialog, ui.card().classes("surface-card w-72 q-pa-lg"):
        ui.label(record_date).classes("text-xl font-bold")
        ui.label("この日の記録").classes("text-grey-7 text-sm q-mb-md")
        if parts:
            for part in parts:
                ui.label(f"●  {part}").style(f"color: {PART_COLORS[part]}").classes("text-lg font-bold q-mb-xs")
        else:
            ui.label("記録はありません").classes("text-grey-7")
        ui.button("閉じる", on_click=dialog.close).props("flat").classes("w-full q-mt-md")
    dialog.open()


@ui.page("/workout")
def workout():
    Theme.page("筋トレ")
    page_user_id = data.active_user_id
    today = date.today()
    display_month = [today.replace(day=1)]
    content = Theme.shell("筋トレ", "今日の自分に、ひとつ記録を。", back_to="/")
    with content:
        with ui.card().classes("surface-card w-full q-pa-lg q-mb-xl"):
            selected_date = ui.input("記録日", value=today.isoformat()).props("type=date outlined").classes("w-full q-mb-md")
            ui.label("鍛えた部位").classes("section-kicker q-mb-sm")
            checks = {}
            with ui.row().classes("w-full gap-x-4 gap-y-2 q-mb-md"):
                for part in BODY_PARTS:
                    checks[part] = ui.checkbox(part).props(f"color={PART_COLORS[part]}").classes("body-part")

            def sync_selected_date():
                record = data.get_workout_for_date(selected_date.value, page_user_id)
                selected_parts = record["body_parts"] if record else []
                for part, checkbox in checks.items():
                    checkbox.value = part in selected_parts
                save_button.text = "記録を更新" if record else "記録を保存"
                save_button.update()

            def save_record():
                parts = [part for part, checkbox in checks.items() if checkbox.value]
                try:
                    data.save_workout(selected_date.value, parts, page_user_id)
                except (RuntimeError, ValueError) as error:
                    ui.notify(f"保存できませんでした: {error}", type="negative")
                    return
                ui.notify("記録しました", type="positive")
                sync_selected_date()
                calendar_view.refresh()
                recent_records.refresh()

            save_button = ui.button("記録を保存", icon="check", on_click=save_record).classes("w-full")
            selected_date.on("change", lambda _: sync_selected_date())
            sync_selected_date()

        ui.label("カレンダー").classes("text-2xl font-bold q-mb-sm")

        @ui.refreshable
        def calendar_view():
            records = {
                record["date"]: record["body_parts"]
                for record in data.get_workout_records(page_user_id)
            }
            with ui.card().classes("surface-card w-full q-pa-sm q-mb-xl"):
                with ui.row().classes("w-full items-center justify-between no-wrap q-mb-sm"):
                    ui.button(icon="chevron_left", on_click=lambda: change_month(-1)).props("flat round")
                    ui.label(f"{display_month[0].year}年 {display_month[0].month}月").classes("text-lg font-bold")
                    with ui.row().classes("items-center no-wrap"):
                        ui.button("今日", on_click=go_today).props("flat dense")
                        ui.button(icon="chevron_right", on_click=lambda: change_month(1)).props("flat round")
                with ui.element("div").classes("grid grid-cols-7 gap-1 w-full"):
                    for weekday in ("月", "火", "水", "木", "金", "土", "日"):
                        ui.label(weekday).classes("text-center text-grey-7 text-xs")
                    for week in calendar.monthcalendar(display_month[0].year, display_month[0].month):
                        for number in week:
                            if not number:
                                ui.element("div").classes("min-h-[72px]")
                                continue
                            current = date(display_month[0].year, display_month[0].month, number)
                            text_date, parts = current.isoformat(), records.get(current.isoformat(), [])
                            with ui.card().classes("calendar-day q-pa-xs cursor-pointer" + (" border border-primary" if current == today else "")).on(
                                "click", lambda _, d=text_date, p=parts: record_dialog(d, p)
                            ):
                                ui.label(str(number)).classes("text-xs font-bold")
                                if parts:
                                    with ui.row().classes("gap-1 q-mt-xs flex-wrap"):
                                        for part in parts:
                                            ui.element("span").style(f"background:{PART_COLORS[part]};width:8px;height:8px;border-radius:999px")

        def change_month(offset):
            year, month = display_month[0].year, display_month[0].month + offset
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
        ui.label("最近の記録").classes("text-2xl font-bold q-mb-sm")

        @ui.refreshable
        def recent_records():
            records = list(reversed(data.get_workout_records(page_user_id)))
            if not records:
                ui.label("最初の記録を残してみましょう。").classes("text-grey-7")
                return
            for record in records[:6]:
                with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                    ui.label(days_ago(record["date"])).classes("text-sm text-grey-7")
                    ui.label(record["date"]).classes("font-bold")
                    with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
                        for part in record["body_parts"]:
                            ui.badge(part).style(f"background:{PART_COLORS[part]}")

        recent_records()

        ui.label("栄養管理").classes("text-2xl font-bold q-mt-xl q-mb-sm")

        @ui.refreshable
        def nutrition_summary():
            totals = nutrition.daily_summary(today.isoformat(), page_user_id)
            goals = nutrition_settings.get_settings(page_user_id)
            protein_goal = (
                f" / {goals['protein_goal']}g"
                if goals["protein_goal"] is not None
                else "g"
            )
            calorie_goal = (
                f" / {goals['calorie_goal']}kcal"
                if goals["calorie_goal"] is not None
                else "kcal"
            )
            with ui.element("div").classes(
                "grid grid-cols-2 gap-3 w-full q-mb-md"
            ):
                with ui.card().classes("surface-card q-pa-md"):
                    ui.label("🥩 タンパク質").classes("text-grey-7 text-sm")
                    ui.label(
                        f"{totals['protein']}g{protein_goal}"
                    ).classes("text-xl font-bold metric-value q-mt-sm")
                with ui.card().classes("surface-card q-pa-md"):
                    ui.label("🔥 カロリー").classes("text-grey-7 text-sm")
                    ui.label(
                        f"{totals['calories']}kcal{calorie_goal}"
                    ).classes("text-xl font-bold metric-value q-mt-sm")

        nutrition_summary()

        with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
            ui.label("食品を登録").classes("section-kicker q-mb-sm")
            food_name = ui.input("食品名").props("outlined").classes(
                "w-full q-mb-sm"
            )
            food_calories = ui.number(
                "カロリー（1食分）", min=0
            ).props("outlined suffix=kcal").classes("w-full q-mb-sm")
            food_protein = ui.number(
                "タンパク質（1食分）", min=0
            ).props("outlined suffix=g").classes("w-full q-mb-sm")

            def save_food():
                try:
                    food = nutrition.add_food(
                        food_name.value,
                        food_calories.value,
                        food_protein.value,
                        page_user_id,
                    )
                except (RuntimeError, ValueError) as error:
                    ui.notify(f"保存できませんでした: {error}", type="negative")
                    return
                food_select.options = {
                    item["id"]: item["name"]
                    for item in nutrition.get_foods(page_user_id)
                }
                food_select.value = food["id"]
                food_select.update()
                food_name.value = ""
                food_calories.value = None
                food_protein.value = None
                ui.notify("食品を登録しました", type="positive")

            ui.button(
                "食品を登録", icon="add", on_click=save_food
            ).props("outline").classes("w-full")

        with ui.card().classes("surface-card w-full q-pa-lg"):
            ui.label("食事を記録").classes("section-kicker q-mb-sm")
            meal_date = ui.input(
                "日付", value=today.isoformat()
            ).props("type=date outlined").classes("w-full q-mb-sm")
            food_select = ui.select(
                {
                    food["id"]: food["name"]
                    for food in nutrition.get_foods(page_user_id)
                },
                label="食品",
            ).props("outlined").classes("w-full q-mb-sm")
            meal_amount = ui.number(
                "量（1食分を1）", value=1, min=0.1, step=0.1
            ).props("outlined suffix=食").classes("w-full q-mb-sm")

            def save_meal():
                try:
                    nutrition.add_meal(
                        meal_date.value,
                        food_select.value,
                        meal_amount.value,
                        page_user_id,
                    )
                except (RuntimeError, ValueError) as error:
                    ui.notify(f"保存できませんでした: {error}", type="negative")
                    return
                ui.notify("食事を記録しました", type="positive")
                nutrition_summary.refresh()

            ui.button(
                "食事を記録", icon="check", on_click=save_meal
            ).classes("w-full")
