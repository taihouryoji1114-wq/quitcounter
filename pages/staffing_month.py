from calendar import monthrange
from copy import deepcopy
from datetime import date

from nicegui import ui
from fastapi import Request
from core.auth import require_app_access, require_permission, has_permission
from core.clock import today_jst
from core.staffing import staffing
from core.theme import Theme


@ui.page("/mirai-kessan/staffing/month")
def monthly_timecards():
    if not require_app_access("future_financials") or not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("スタッフ別まとめ入力｜未来決算", app_name="mirai-kessan")
    content = Theme.shell("スタッフ別まとめ入力", "1人の1か月分を、日付順に続けて入力",
                          back_to="/mirai-kessan/staffing", brand="未来決算")
    dirty = set()
    with content:
        ui.button("日付別まとめ入力に切り替え", icon="groups", on_click=lambda: ui.navigate.to("/mirai-kessan/staffing/day")).props("flat")
        with ui.row().classes("w-full no-wrap gap-2"):
            person = ui.select(list(staffing.HOURLY_STAFF), value="スタッフA", label="スタッフ").props("outlined dense").classes("grow")
            month_input = ui.input("対象月", value=today_jst().strftime("%Y-%m")).props("outlined dense type=month").classes("grow")
        editor = ui.column().classes("w-full gap-2")

        def load():
            try:
                month = str(month_input.value)
                first = date.fromisoformat(month + "-01")
                if first > today_jst() or person.value not in staffing.HOURLY_STAFF:
                    raise ValueError()
            except (ValueError, TypeError):
                ui.notify("スタッフと今月以前の対象月を選んでください", type="negative")
                return
            selected = person.value
            dirty.clear()
            editor.clear()
            last = monthrange(first.year, first.month)[1]
            if month == today_jst().strftime("%Y-%m"):
                last = today_jst().day
            expected = {}
            rows = {}
            with editor:
                ui.label(f"入力中：{selected} ／ {first.year}年{first.month}月").classes("text-lg font-bold")
                ui.label("1000 → 10:00 の数字入力OK。休みは「休み」を選択。何も触らない日は未入力のまま残ります。").classes("text-xs")
                progress = staffing.timecard_progress(month, today_jst().isoformat())[selected]
                ui.label(f"入力済み {progress['entered_count']}日 ／ 未確認 {len(progress['missing_days'])}日").classes("text-sm font-bold text-primary")
                counter = ui.label("変更なし").classes("text-sm text-orange-9")
                with ui.column().classes("month-hours-scroll w-full gap-2"):
                    for number in range(1, last + 1):
                        record_date = f"{month}-{number:02d}"
                        expected[record_date] = deepcopy(staffing._data_manager.data.get("business_staff_hours", {}).get(record_date, {}).get(selected, {}))
                        values = staffing.day(record_date)[selected]
                        working = values["attended"] or any(values[k] for k in ("lunch_start", "lunch_end", "dinner_start", "dinner_end"))
                        status = "出勤" if working else "休み" if values.get("entry_confirmed") else "未入力"
                        with ui.card().classes("month-hours-row w-full q-pa-sm") as card:
                            if status != "未入力":
                                card.style("border-left:4px solid #368264")
                            with ui.row().classes("w-full items-center no-wrap justify-between"):
                                weekday = "月火水木金土日"[date(first.year, first.month, number).weekday()]
                                ui.label(f"{number}日（{weekday}）").classes("font-bold")
                                state = ui.select(["未入力", "出勤", "休み"], value=status).props("outlined dense").style("width:110px")
                            inputs = {}
                            if selected in staffing.HOURLY_STAFF:
                                with ui.element("div").classes("month-hours-grid"):
                                    for key, label in (("lunch_start", "昼・開始"), ("lunch_end", "昼・終了"), ("dinner_start", "夜・開始"), ("dinner_end", "夜・終了")):
                                        inputs[key] = ui.input(label, value=values[key]).props("outlined dense inputmode=numeric placeholder=10:00").classes("w-full")
                                inputs["break_minutes"] = ui.number("休憩（分）", value=values["break_minutes"], min=0).props("outlined dense inputmode=numeric").classes("w-full")
                            row = {"state": state, "inputs": inputs, "changing": False, "values": values}
                            rows[record_date] = row
                            def changed(_, day=record_date, item=row):
                                if item["changing"]:
                                    return
                                item["changing"] = True
                                item["state"].set_value("出勤")
                                item["changing"] = False
                                dirty.add(day)
                                counter.set_text(f"未保存：{len(dirty)}日分")
                            def state_changed(_, day=record_date, item=row, tile=card):
                                if item["changing"]:
                                    return
                                item["changing"] = True
                                if item["state"].value != "出勤":
                                    for key, field in item["inputs"].items():
                                        field.set_value(0 if key == "break_minutes" else "")
                                item["changing"] = False
                                dirty.add(day)
                                tile.style("border-left:4px solid #D19132")
                                counter.set_text(f"未保存：{len(dirty)}日分")
                            for field in inputs.values():
                                field.on_value_change(changed)
                            state.on_value_change(state_changed)
                def save():
                    if not has_permission("future_dashboard"):
                        return
                    updates = {}
                    for day in dirty:
                        row = rows[day]
                        work = row["state"].value == "出勤"
                        value = {key: field.value for key, field in row["inputs"].items()}
                        if work and selected in staffing.HOURLY_STAFF and not any(value.get(k) for k in ("lunch_start", "lunch_end", "dinner_start", "dinner_end")):
                            ui.notify(f"{day}の勤務時間を入力してください", type="negative")
                            return
                        value["attended"] = work and selected in staffing.SALARIED_STAFF
                        value["entry_confirmed"] = row["state"].value != "未入力"
                        value["transportation"] = row["values"].get("transportation", 0) if work else 0
                        updates[day] = value
                    try:
                        count = staffing.save_person_month(selected, month, updates, expected)
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    dirty.clear()
                    person.set_value(selected)
                    month_input.set_value(month)
                    load()
                    ui.notify(f"{selected}の{count}日分を保存しました", type="positive")
                ui.button(f"{selected}の変更分をまとめて保存", icon="save", on_click=save).classes("w-full q-py-sm")

        def request_load():
            if not dirty:
                load()
                return
            with ui.dialog() as dialog, ui.card():
                ui.label("未保存の入力があります。破棄して切り替えますか？")
                ui.button("入力に戻る", on_click=dialog.close)
                ui.button("破棄して切り替える", on_click=lambda: (dialog.close(), load())).props("color=negative")
            dialog.open()
        ui.button("選んだスタッフ・月を開く", icon="calendar_month", on_click=request_load).classes("w-full q-my-sm").move(target_index=2)
        load()
    ui.add_css(".month-hours-scroll{max-height:62vh;overflow-y:auto;overscroll-behavior:contain;padding:2px 2px 8px}.month-hours-row{border:1px solid #dce5df;border-radius:14px!important;box-shadow:none!important}.month-hours-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;width:100%}.month-hours-grid .q-field{min-width:0}.month-hours-row .q-field__native{font-size:16px}@media(min-width:650px){.month-hours-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}")


@ui.page("/mirai-kessan/staffing/day")
def daily_timecards(request: Request):
    if not require_app_access("future_financials") or not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("日付別まとめ入力｜未来決算", app_name="mirai-kessan")
    content = Theme.shell("日付別まとめ入力", "その日の全スタッフを一覧で入力・まとめて保存",
                          back_to="/mirai-kessan/staffing", brand="未来決算")
    dirty = set()
    with content:
        ui.button("スタッフ別まとめ入力に切り替え", on_click=lambda: ui.navigate.to("/mirai-kessan/staffing/month")).props("flat")
        try:
            initial_day = date.fromisoformat(request.query_params.get("date", "")).isoformat()
        except ValueError:
            initial_day = today_jst().isoformat()
        selected_day = ui.input("対象日", value=initial_day).props(f"outlined type=date max={today_jst().isoformat()}").classes("w-full")
        editor = ui.column().classes("w-full")

        def load():
            try:
                record_date = date.fromisoformat(selected_day.value).isoformat()
                if record_date > today_jst().isoformat():
                    raise ValueError()
            except (ValueError, TypeError):
                ui.notify("今日以前の日付を選んでください", type="negative")
                return
            dirty.clear()
            editor.clear()
            expected = deepcopy(staffing._data_manager.data.get("business_staff_hours", {}).get(record_date, {}))
            values = staffing.day(record_date)
            rows = {}
            with editor:
                ui.label(f"入力中：{record_date}").classes("text-lg font-bold")
                ui.label("変更したスタッフだけ保存します。休みは「休み」を選択。1000のように時刻を直接入力できます。").classes("text-xs")
                counter = ui.label("変更なし").classes("text-orange-9 font-bold")
                with ui.column().classes("w-full gap-2").style("max-height:62vh;overflow-y:auto;padding:3px"):
                    for name in staffing.HOURLY_STAFF:
                        value = values[name]
                        work = value["attended"] or any(value[k] for k in ("lunch_start", "lunch_end", "dinner_start", "dinner_end"))
                        status = "出勤" if work else "休み" if value.get("entry_confirmed") else "未入力"
                        with ui.card().classes("w-full q-pa-sm").style("border:1px solid #d7e3da;border-radius:14px;box-shadow:none"):
                            with ui.row().classes("w-full justify-between items-center"):
                                ui.label(name).classes("font-bold")
                                state = ui.select(["未入力", "出勤", "休み"], value=status).props("outlined dense").style("width:110px")
                            inputs = {}
                            if name in staffing.HOURLY_STAFF:
                                with ui.element("div").classes("daily-time-grid"):
                                    for key, label in (("lunch_start", "昼・開始"), ("lunch_end", "昼・終了"), ("dinner_start", "夜・開始"), ("dinner_end", "夜・終了")):
                                        inputs[key] = ui.input(label, value=value[key]).props("outlined dense inputmode=numeric placeholder=10:00")
                                inputs["break_minutes"] = ui.number("休憩（分）", value=value["break_minutes"], min=0).props("outlined dense inputmode=numeric").classes("w-full")
                            row = {"state": state, "inputs": inputs, "changing": False}
                            rows[name] = row
                            def changed(_, person=name, item=row):
                                if item["changing"]:
                                    return
                                item["changing"] = True
                                item["state"].set_value("出勤")
                                item["changing"] = False
                                dirty.add(person)
                                counter.set_text(f"未保存：{len(dirty)}人")
                            def state_changed(_, person=name, item=row):
                                if item["changing"]:
                                    return
                                item["changing"] = True
                                if item["state"].value != "出勤":
                                    for key, field in item["inputs"].items():
                                        field.set_value(0 if key == "break_minutes" else "")
                                item["changing"] = False
                                dirty.add(person)
                                counter.set_text(f"未保存：{len(dirty)}人")
                            state.on_value_change(state_changed)
                            for field in inputs.values():
                                field.on_value_change(changed)
                def save():
                    if not has_permission("future_dashboard"):
                        return
                    updates = {}
                    for name in dirty:
                        row = rows[name]
                        work = row["state"].value == "出勤"
                        value = {key: field.value for key, field in row["inputs"].items()}
                        if work and name in staffing.HOURLY_STAFF and not any(value.get(k) for k in ("lunch_start", "lunch_end", "dinner_start", "dinner_end")):
                            ui.notify(f"{name}の勤務時間を入力してください", type="negative")
                            return
                        updates[name] = dict(value, attended=work and name in staffing.SALARIED_STAFF,
                            entry_confirmed=row["state"].value != "未入力",
                            transportation=values[name].get("transportation", 0) if work else 0)
                    try:
                        count = staffing.save_date_batch(record_date, updates, expected)
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    selected_day.set_value(record_date)
                    load()
                    ui.notify(f"{record_date}の{count}人分を保存しました", type="positive")
                ui.button("この日の変更分をまとめて保存", icon="save", on_click=save).classes("w-full q-py-sm")
        def request_load():
            if not dirty:
                load()
                return
            with ui.dialog() as dialog, ui.card():
                ui.label("未保存の入力を破棄して日付を切り替えますか？")
                ui.button("入力に戻る", on_click=dialog.close)
                ui.button("破棄して切り替える", on_click=lambda: (dialog.close(), load())).props("color=negative")
            dialog.open()
        ui.button("選んだ日を開く", icon="calendar_month", on_click=request_load).classes("w-full").move(target_index=2)
        load()
    ui.add_css(".daily-time-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;width:100%}.daily-time-grid .q-field{min-width:0}.daily-time-grid input{font-size:16px}@media(min-width:650px){.daily-time-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}")
