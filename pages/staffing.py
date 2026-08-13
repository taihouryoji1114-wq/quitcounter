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
                shift_inputs = {}
                with ui.card().classes("surface-card w-full q-pa-md q-mt-sm"):
                    ui.label("終了が開始より早い場合は翌日として計算します").classes("text-[9px] text-grey-6 q-mb-sm")
                    for name in staffing.STAFF:
                        shift_inputs[name] = {}
                        with ui.expansion(name, value=False).classes("staff-shift w-full q-mb-xs"):
                            for label, prefix in (("ランチ", "lunch"), ("ディナー", "dinner")):
                                ui.label(label).classes("text-[10px] font-bold q-mt-xs")
                                with ui.row().classes("w-full gap-2 no-wrap"):
                                    for title, suffix in (("開始", "start"), ("終了", "end")):
                                        key = f"{prefix}_{suffix}"
                                        shift_inputs[name][key] = ui.input(
                                            title, value=values[name][key]
                                        ).props("outlined dense type=time step=60").classes("grow")
                            detail = staffing.day_detail(record_date, name)
                            if detail["total_minutes"]:
                                ui.label(
                                    f"{detail['total_minutes']//60}時間{detail['total_minutes']%60}分"
                                    f"（深夜 {detail['night_minutes']}分）　¥{detail['pay']:,}"
                                ).classes("text-[10px] font-bold text-primary q-mt-sm")

                    def save_day():
                        try:
                            staffing.save_day(record_date, {
                                name: {key: field.value for key, field in fields.items()}
                                for name, fields in shift_inputs.items()
                            })
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
        ui.add_css(".staff-panel,.staff-shift{border-radius:18px!important;background:#fff!important;border:1px solid #E1E9E4!important}.staff-shift .q-item{min-height:46px!important}")
