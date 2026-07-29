import calendar
from datetime import date, timedelta

from nicegui import ui

from core.auth import require_login
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


@ui.page("/habitory/workout")
def workout():
    if not require_login():
        return
    Theme.page("筋トレ")
    page_user_id = data.active_user_id
    today = date.today()
    display_month = [today.replace(day=1)]
    content = Theme.shell("筋トレ", "今日の自分に、ひとつ記録を。", back_to="/habitory")
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
                delete_button.set_visibility(record is not None)

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

            def confirm_delete():
                with ui.dialog() as dialog, ui.card().classes("surface-card w-80 q-pa-lg"):
                    ui.label("この記録を削除しますか？").classes("text-xl font-bold")
                    ui.label(selected_date.value).classes("text-grey-7 q-mb-md")

                    def delete_record():
                        try:
                            data.delete_workout(selected_date.value, page_user_id)
                        except (RuntimeError, ValueError) as error:
                            ui.notify(f"削除できませんでした: {error}", type="negative")
                            return
                        dialog.close()
                        ui.notify("筋トレ記録を削除しました", type="positive")
                        sync_selected_date()
                        calendar_view.refresh()
                        recent_records.refresh()

                    with ui.row().classes("w-full gap-2"):
                        ui.button("キャンセル", on_click=dialog.close).props("flat").classes("flex-1")
                        ui.button("削除", icon="delete", on_click=delete_record).props("color=negative").classes("flex-1")
                dialog.open()

            delete_button = ui.button(
                "記録を削除",
                icon="delete_outline",
                on_click=confirm_delete,
            ).props("flat color=negative").classes("w-full q-mt-sm")
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
                            with ui.card().classes("calendar-day q-pa-xs cursor-pointer" + (" today-calendar-day" if current == today else "")).on(
                                "click", lambda _, d=text_date, p=parts: record_dialog(d, p)
                            ):
                                ui.label(str(number)).classes(
                                    "today-date-number" if current == today
                                    else "text-xs font-bold"
                                )
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

        ui.label("栄養の振り返り").classes("text-xl font-bold q-mb-sm")

        @ui.refreshable
        def nutrition_history():
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            past_dates = [
                record["date"]
                for record in nutrition.get_meal_records(user_id=page_user_id)
                if record.get("date", "") <= today.isoformat()
            ]
            first_date = min(past_dates) if past_dates else today.isoformat()
            periods = (
                ("今週", week_start.isoformat()),
                ("今月", month_start.isoformat()),
                ("記録開始から", first_date),
            )
            expenditure = nutrition_settings.estimated_daily_expenditure(
                page_user_id
            )
            for label, start_date in periods:
                totals = nutrition.period_summary(
                    start_date, today.isoformat(), page_user_id
                )
                with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                    ui.label(label).classes("font-bold")
                    ui.label(
                        f"{totals['calories']}kcal・タンパク質 {totals['protein']}g"
                    ).classes("text-lg font-bold metric-value q-mt-xs")
                    if expenditure is None:
                        ui.label(
                            "設定で基礎代謝と活動量を入力すると収支を表示します"
                        ).classes("text-xs text-grey-7 q-mt-xs")
                    else:
                        balance = totals["calories"] - expenditure * totals["days"]
                        sign = "+" if balance > 0 else ""
                        ui.label(
                            f"推定収支 {sign}{balance:,.0f}kcal"
                            f"（消費目安 {expenditure * totals['days']:,}kcal）"
                        ).classes(
                            "text-sm q-mt-xs "
                            + ("text-negative" if balance > 0 else "text-positive")
                        )

        nutrition_history()

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
                food_select.value = [food["id"]]
                food_select.update()
                food_name.value = ""
                food_calories.value = None
                food_protein.value = None
                ui.notify("食品を登録しました", type="positive")
                food_list.refresh()

            ui.button(
                "食品を登録", icon="add", on_click=save_food
            ).props("outline").classes("w-full")

        @ui.refreshable
        def food_list():
            foods = nutrition.get_foods(page_user_id)
            if not foods:
                ui.label("登録済みの食品はありません。").classes("text-grey-7 q-mb-md")
                return
            for food in foods:
                with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                    with ui.row().classes("w-full items-center no-wrap"):
                        with ui.column().classes("gap-0"):
                            ui.label(food["name"]).classes("font-bold")
                            ui.label(
                                f"{food['calories']}kcal・タンパク質 {food['protein']}g"
                            ).classes("text-sm text-grey-7")
                        ui.space()

                        def open_edit(_, selected=food):
                            with ui.dialog() as dialog, ui.card().classes("surface-card w-80 q-pa-lg"):
                                ui.label("食品を編集").classes("text-xl font-bold q-mb-md")
                                edit_name = ui.input("食品名", value=selected["name"]).props("outlined").classes("w-full")
                                edit_calories = ui.number("カロリー", value=selected["calories"], min=0).props("outlined suffix=kcal").classes("w-full")
                                edit_protein = ui.number("タンパク質", value=selected["protein"], min=0).props("outlined suffix=g").classes("w-full")

                                def save_edit():
                                    try:
                                        nutrition.update_food(
                                            selected["id"],
                                            edit_name.value,
                                            edit_calories.value,
                                            edit_protein.value,
                                            page_user_id,
                                        )
                                    except (RuntimeError, ValueError) as error:
                                        ui.notify(f"更新できませんでした: {error}", type="negative")
                                        return
                                    dialog.close()
                                    food_select.options = {
                                        item["id"]: item["name"]
                                        for item in nutrition.get_foods(page_user_id)
                                    }
                                    food_select.update()
                                    food_list.refresh()
                                    ui.notify("食品を更新しました", type="positive")

                                ui.button("変更を保存", icon="check", on_click=save_edit).classes("w-full")
                            dialog.open()

                        def confirm_food_delete(_, selected=food):
                            with ui.dialog() as dialog, ui.card().classes("surface-card w-80 q-pa-lg"):
                                ui.label("この食品を削除しますか？").classes("text-xl font-bold")
                                ui.label(selected["name"]).classes("text-grey-7 q-mb-md")

                                def delete_selected():
                                    nutrition.delete_food(selected["id"], page_user_id)
                                    dialog.close()
                                    if selected["id"] in (food_select.value or []):
                                        food_select.value = [
                                            value for value in food_select.value
                                            if value != selected["id"]
                                        ]
                                    food_select.options = {
                                        item["id"]: item["name"]
                                        for item in nutrition.get_foods(page_user_id)
                                    }
                                    food_select.update()
                                    food_list.refresh()
                                    ui.notify("食品を削除しました", type="positive")

                                with ui.row().classes("w-full gap-2"):
                                    ui.button("キャンセル", on_click=dialog.close).props("flat").classes("flex-1")
                                    ui.button("削除", on_click=delete_selected).props("color=negative").classes("flex-1")
                            dialog.open()

                        ui.button(icon="edit", on_click=open_edit).props("flat round")
                        ui.button(icon="delete_outline", on_click=confirm_food_delete).props("flat round color=negative")

        with ui.expansion(
            "登録済み食品を見る・編集する", icon="inventory_2"
        ).classes("surface-card w-full q-mb-md"):
            food_list()

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
                label="食品（複数選択できます）",
                multiple=True,
            ).props("outlined use-chips").classes("w-full q-mb-sm")
            meal_amount = ui.number(
                "選んだ食品の個数", value=1, min=0.1, step=0.1
            ).props("outlined suffix=個").classes("w-full q-mb-xs")
            ui.label(
                "例：ライス50gを100gなら2個、400gなら8個"
            ).classes("text-xs text-grey-7 q-mb-sm")

            def save_meal():
                try:
                    nutrition.add_meals(
                        meal_date.value,
                        food_select.value,
                        meal_amount.value,
                        page_user_id,
                    )
                except (RuntimeError, ValueError) as error:
                    ui.notify(f"保存できませんでした: {error}", type="negative")
                    return
                ui.notify("食事を記録しました", type="positive")
                food_select.value = []
                nutrition_summary.refresh()
                nutrition_history.refresh()
                meal_list.refresh()

            ui.button(
                "食事を記録", icon="check", on_click=save_meal
            ).classes("w-full")

            with ui.expansion(
                "カロリー・タンパク質を手入力", icon="edit_note"
            ).classes("w-full q-mt-md"):
                manual_name = ui.input(
                    "メモ（省略できます）", placeholder="外食、間食など"
                ).props("outlined").classes("w-full q-mb-sm")
                manual_calories = ui.number(
                    "カロリー", min=0
                ).props("outlined suffix=kcal").classes("w-full q-mb-sm")
                manual_protein = ui.number(
                    "タンパク質", min=0
                ).props("outlined suffix=g").classes("w-full q-mb-sm")

                def save_manual_meal():
                    try:
                        nutrition.add_manual_meal(
                            meal_date.value,
                            manual_calories.value,
                            manual_protein.value,
                            manual_name.value,
                            page_user_id,
                        )
                    except (RuntimeError, ValueError) as error:
                        ui.notify(f"保存できませんでした: {error}", type="negative")
                        return
                    manual_name.value = ""
                    manual_calories.value = None
                    manual_protein.value = None
                    nutrition_summary.refresh()
                    nutrition_history.refresh()
                    meal_list.refresh()
                    ui.notify("手入力の食事を記録しました", type="positive")

                ui.button(
                    "手入力で記録", icon="check", on_click=save_manual_meal
                ).props("outline").classes("w-full")

        ui.label("選択日の食事").classes("text-xl font-bold q-mt-lg q-mb-sm")

        @ui.refreshable
        def meal_list():
            records = nutrition.get_meal_records(meal_date.value, page_user_id)
            if not records:
                ui.label("この日の食事記録はありません。").classes("text-grey-7")
                return
            for record in records:
                with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                    with ui.row().classes("w-full items-center no-wrap"):
                        with ui.column().classes("gap-0"):
                            ui.label(record["food_name"]).classes("font-bold")
                            ui.label(
                                f"{record['amount']}食・{record['calories']}kcal・"
                                f"タンパク質 {record['protein']}g"
                            ).classes("text-sm text-grey-7")
                        ui.space()

                        def confirm_meal_delete(_, selected=record):
                            with ui.dialog() as dialog, ui.card().classes("surface-card w-80 q-pa-lg"):
                                ui.label("この食事を取り消しますか？").classes("text-xl font-bold")
                                ui.label(selected["food_name"]).classes("text-grey-7 q-mb-md")

                                def delete_selected():
                                    try:
                                        nutrition.delete_meal(
                                            selected["id"], page_user_id
                                        )
                                    except (RuntimeError, ValueError) as error:
                                        ui.notify(
                                            f"取り消せませんでした: {error}",
                                            type="negative",
                                        )
                                        return
                                    dialog.close()
                                    meal_list.refresh()
                                    nutrition_summary.refresh()
                                    nutrition_history.refresh()
                                    ui.notify("食事記録を取り消しました", type="positive")

                                with ui.row().classes("w-full gap-2"):
                                    ui.button("キャンセル", on_click=dialog.close).props("flat").classes("flex-1")
                                    ui.button("取り消す", icon="undo", on_click=delete_selected).props("color=negative").classes("flex-1")
                            dialog.open()

                        ui.button(
                            icon="undo",
                            on_click=confirm_meal_delete,
                        ).props("flat round color=negative")

        meal_list()
        meal_date.on("change", lambda _: meal_list.refresh())
