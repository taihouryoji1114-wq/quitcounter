from nicegui import ui

from core.auth import require_login
from core.clock import today_jst
from core.staffing import staffing
from core.theme import Theme


@ui.page("/mirai-kessan/staffing")
def staffing_page():
    if not require_login():
        return
    Theme.page("人件費管理｜未来決算", app_name="mirai-kessan")
    content = Theme.shell("人件費管理", "スタッフ名を保存せず、時給と勤務時間から自動計算",
                          back_to="/mirai-kessan/dashboard", brand="未来決算")
    with content:
        wages = staffing.wages()
        with ui.expansion("スタッフ別の時給設定", icon="groups", value=False).classes("staff-panel w-full"):
            wage_inputs = {}
            with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
                for name in staffing.STAFF:
                    wage_inputs[name] = ui.number(name, value=wages[name] or None, min=0, step=1).props(
                        "outlined dense prefix=¥ suffix=/時 inputmode=numeric")

            def save_wages():
                staffing.save_wages({name: field.value for name, field in wage_inputs.items()})
                ui.notify("時給設定を保存しました", type="positive")
            ui.button("時給を保存", icon="save", on_click=save_wages).classes("w-full q-mt-md")

        selected = today_jst().isoformat()
        ui.label("勤務時間を入力").classes("text-lg font-black q-mt-md")
        date_input = ui.input("日付", value=selected).props("outlined dense type=date").classes("w-full")
        hours_area = ui.column().classes("w-full gap-0")

        def render_day(record_date):
            hours_area.clear()
            values = staffing.day(record_date)
            with hours_area:
                hour_inputs = {}
                with ui.card().classes("surface-card w-full q-pa-md q-mt-sm"):
                    with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
                        for name in staffing.STAFF:
                            hour_inputs[name] = ui.number(name, value=values[name] or None, min=0, max=24, step=.25).props(
                                "outlined dense suffix=時間 inputmode=decimal")

                    def save_day():
                        try:
                            staffing.save_day(record_date, {name: field.value for name, field in hour_inputs.items()})
                        except ValueError as error:
                            ui.notify(str(error), type="negative")
                            return
                        ui.notify(f"保存しました：¥{staffing.day_total(record_date):,}", type="positive")
                        render_day(record_date)
                    ui.button("勤務時間を保存", icon="save", on_click=save_day).classes("w-full q-mt-md")
                    ui.label(f"この日の人件費　¥{staffing.day_total(record_date):,}").classes("text-base font-black text-primary q-mt-md")
                    ui.label(f"今月の人件費　¥{staffing.month_total(record_date[:7]):,}").classes("text-xl font-black q-mt-xs")
        date_input.on("change", lambda: render_day(date_input.value))
        render_day(selected)
        ui.add_css(".staff-panel{border-radius:20px!important;background:#fff!important;border:1px solid #E1E9E4!important}")
