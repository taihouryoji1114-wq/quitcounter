from nicegui import ui

from core.auth import current_role, log_out, require_app_access, require_permission
from core.clock import today_jst
from core.staffing import staffing
from core.theme import Theme


@ui.page("/mirai-kessan/attendance")
def attendance_input_page():
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_input", "/mirai-kessan/login"):
        return
    Theme.page("勤務・出勤入力｜未来決算", app_name="mirai-kessan")

    def actions():
        with ui.row().classes("gap-0"):
            if current_role() == "owner":
                ui.button(icon="apps", on_click=lambda: ui.navigate.to("/")).props(
                    "flat round aria-label='R-BASEへ戻る'")
            ui.button(icon="logout", on_click=lambda: log_out("/mirai-kessan/login")).props("flat round")

    content = Theme.shell("勤務・出勤入力", "給与額を見せず、勤務記録だけを入力",
                          action=actions, back_to="/mirai-kessan/input", brand="未来決算")
    selected_date = today_jst().isoformat()
    with content:
        @ui.refreshable
        def progress_summary(month):
            progress = staffing.timecard_progress(month, today_jst().isoformat())
            with ui.expansion(
                f"入力状況　{month.replace('-', '年')}月", icon="fact_check", value=False,
            ).classes("attendance-progress w-full q-mb-sm"):
                with ui.element("div").classes("attendance-progress-grid w-full"):
                    for name in staffing.STAFF:
                        item = progress[name]
                        latest = (f"{int(item['latest_date'][8:10])}日まで"
                                  if item["latest_date"] else "まだ入力なし")
                        with ui.element("div").classes(
                                "attendance-progress-person entered" if item["latest_date"]
                                else "attendance-progress-person"):
                            ui.label(name).classes("attendance-progress-name")
                            ui.label(latest).classes("attendance-progress-latest")
                            ui.label(f"{item['entered_count']}日分").classes(
                                "attendance-progress-count")

        progress_summary(selected_date[:7])
        date_input = ui.input("日付", value=selected_date).props(
            "outlined dense type=date").classes("w-full")
        input_area = ui.column().classes("w-full gap-0")

        def render(record_date):
            input_area.clear()
            values = staffing.day(record_date)
            with input_area:
                fields = {}
                with ui.card().classes("attendance-input-card w-full q-pa-md q-mt-sm"):
                    for name in staffing.STAFF:
                        fields[name] = {}
                        with ui.expansion(name, value=name in staffing.SALARIED_STAFF).classes(
                            "attendance-person w-full q-mb-xs"):
                            if name in staffing.SALARIED_STAFF:
                                fields[name]["attended"] = ui.checkbox(
                                    "この日は出勤", value=values[name]["attended"])
                                for key in ("lunch_start", "lunch_end", "dinner_start", "dinner_end"):
                                    fields[name][key] = ui.input(value="").props("type=hidden").classes("hidden")
                                fields[name]["break_minutes"] = ui.number(value=0).props("disable").classes("hidden")
                            else:
                                fields[name]["attended"] = ui.checkbox(value=False).props("disable").classes("hidden")
                                for label, prefix in (("ランチ", "lunch"), ("ディナー", "dinner")):
                                    ui.label(label).classes("text-[10px] font-bold q-mt-xs")
                                    with ui.row().classes("w-full gap-2 no-wrap"):
                                        fields[name][f"{prefix}_start"] = ui.input(
                                            "開始", value=values[name][f"{prefix}_start"]).props(
                                                "outlined dense inputmode=numeric placeholder='10:00'").classes("grow")
                                        fields[name][f"{prefix}_end"] = ui.input(
                                            "終了", value=values[name][f"{prefix}_end"]).props(
                                                "outlined dense inputmode=numeric placeholder='15:30'").classes("grow")
                                    ui.button(
                                        f"{label}の入力を消す", icon="backspace",
                                        on_click=lambda _, person=name, session=prefix: (
                                            fields[person][f"{session}_start"].set_value(""),
                                            fields[person][f"{session}_end"].set_value(""),
                                        ),
                                    ).props("flat dense no-caps color=negative").classes(
                                        "attendance-clear-shift")
                                fields[name]["break_minutes"] = ui.number(
                                    "休憩時間", value=values[name]["break_minutes"] or None,
                                    min=0, max=1440, step=1).props(
                                        "outlined dense suffix=分 inputmode=numeric").classes("w-full")

                    def save():
                        try:
                            staffing.save_day(record_date, {
                                name: {key: field.value for key, field in person_fields.items()}
                                for name, person_fields in fields.items()
                            })
                        except ValueError as error:
                            ui.notify(str(error), type="negative")
                            return
                        ui.notify("勤務・出勤を保存しました", type="positive")
                        progress_summary.refresh(record_date[:7])
                        render(record_date)
                    ui.button("保存する", icon="save", on_click=save).classes("w-full q-mt-md")

        def change_date():
            progress_summary.refresh(date_input.value[:7])
            render(date_input.value)

        date_input.on("change", change_date)
        render(selected_date)
        ui.add_css("""
        .attendance-input-card{border-radius:20px!important;border:1px solid #E1E9E4!important;box-shadow:none!important}.attendance-person{border-radius:14px!important;background:#F7F9F7!important;border:1px solid #E7ECE8!important}.attendance-person .q-item{min-height:48px!important}.attendance-progress{border-radius:18px!important;background:#fff!important;border:1px solid #E1E9E4!important}.attendance-progress-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;padding:5px 10px 12px}.attendance-progress-person{min-width:0;padding:9px;border-radius:13px;background:#F1F3F2;border:1px solid #E4E8E5}.attendance-progress-person.entered{background:#E9F5ED;border-color:#C9E3D2}.attendance-progress-name{font-size:10px;font-weight:950}.attendance-progress-latest{font-size:11px;font-weight:950;color:#286B49}.attendance-progress-count{font-size:8px;color:#7A8780}.attendance-clear-shift{align-self:flex-end!important;margin-top:-2px!important;font-size:9px!important}
        """)
