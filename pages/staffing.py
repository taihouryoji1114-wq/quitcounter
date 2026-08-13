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

        settings = staffing.dependent_settings()
        with ui.expansion("扶養アラート設定", icon="notifications_active", value=False).classes(
            "staff-panel w-full q-mt-sm"):
            ui.label("実名は使わず、本人が希望する管理基準を確認して設定してください。").classes("text-[9px] text-grey-6 q-mb-sm")
            dependent_inputs = {}
            options = {key: label for key, (label, _) in staffing.DEPENDENT_LIMITS.items()}
            for name in staffing.STAFF:
                dependent_inputs[name] = {}
                with ui.expansion(name, value=False).classes("staff-shift w-full q-mb-xs"):
                    dependent_inputs[name]["mode"] = ui.select(
                        options, value=settings[name]["mode"], label="管理する基準"
                    ).props("outlined dense options-dense").classes("w-full")
                    dependent_inputs[name]["limit"] = ui.number(
                        "年間上限（個別調整可）", value=settings[name]["limit"] or None,
                        min=0, step=1000).props("outlined dense prefix=¥ inputmode=numeric").classes("w-full q-mt-xs")
                    dependent_inputs[name]["prior_income"] = ui.number(
                        "当店の導入前給与", value=settings[name]["prior_income"] or None,
                        min=0, step=1000).props("outlined dense prefix=¥ inputmode=numeric").classes("w-full q-mt-xs")
                    dependent_inputs[name]["other_income"] = ui.number(
                        "他社での今年の給与", value=settings[name]["other_income"] or None,
                        min=0, step=1000).props("outlined dense prefix=¥ inputmode=numeric").classes("w-full q-mt-xs")

            def save_dependent():
                staffing.save_dependent_settings({name: {
                    key: field.value for key, field in fields.items()
                } for name, fields in dependent_inputs.items()})
                ui.notify("扶養アラート設定を保存しました", type="positive")
                ui.navigate.to("/mirai-kessan/staffing")
            ui.button("扶養設定を保存", icon="save", on_click=save_dependent).classes("w-full q-mt-md")

        with ui.expansion("今年の扶養アラート", icon="warning", value=False).classes("staff-panel w-full q-mt-sm"):
            year = today_jst().year
            alerts = [(name, staffing.dependent_status(year, name, today_jst())) for name in staffing.STAFF]
            visible_alerts = [(name, status) for name, status in alerts if status["mode"] != "none" and (status["earned"] or wages[name])]
            for name, status in visible_alerts:
                colors = {"safe": "#E8F4EC", "warning": "#FFF4D9", "danger": "#FFE4D4", "over": "#FFE0E0"}
                labels = {"safe": "余裕あり", "warning": "早めに確認", "danger": "要調整", "over": "上限到達"}
                with ui.card().classes("dependent-card w-full q-pa-sm q-mb-xs").style(f"background:{colors[status['level']]}"):
                    ui.label(f"{name}　{labels[status['level']]}　残り ¥{status['remaining']:,}").classes("text-xs font-bold")

        insurance = staffing.insurance_settings()
        rates = staffing.insurance_rates()
        with ui.expansion("会社負担の社会保険設定", icon="health_and_safety", value=False).classes("staff-panel w-full q-mt-sm"):
            ui.label("保険料額表の会社負担率を入力してください").classes("text-[9px] text-grey-6")
            rate_inputs = {key: ui.number(label, value=rates[key], min=0, step=.001).props("outlined dense suffix=% inputmode=decimal").classes("w-full q-mt-xs") for key, label in (("health","健康保険"),("pension","厚生年金"),("care","介護保険"),("employment","雇用保険・会社負担"),("workers_comp","労災保険"),("other","子ども・子育て拠出金等"))}
            insurance_inputs = {}
            for name in staffing.STAFF:
                insurance_inputs[name] = {}
                with ui.expansion(name, value=False).classes("staff-shift w-full q-mb-xs"):
                    insurance_inputs[name]["social"] = ui.checkbox("健康保険・厚生年金に加入", value=insurance[name]["social"])
                    insurance_inputs[name]["standard_monthly"] = ui.number("標準報酬月額", value=insurance[name]["standard_monthly"] or None, min=0).props("outlined dense prefix=¥")
                    insurance_inputs[name]["care"] = ui.checkbox("介護保険対象", value=insurance[name]["care"])
                    insurance_inputs[name]["employment"] = ui.checkbox("雇用保険対象", value=insurance[name]["employment"])
            def save_insurance():
                staffing.save_insurance_rates({key: field.value for key, field in rate_inputs.items()})
                staffing.save_insurance_settings({name: {key: field.value for key, field in fields.items()} for name, fields in insurance_inputs.items()})
                ui.notify("社会保険設定を保存しました", type="positive")
            ui.button("保険設定を保存", on_click=save_insurance).classes("w-full q-mt-sm")

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
                            shift_inputs[name]["transportation"] = ui.number(
                                "この日の交通費", value=values[name]["transportation"] or None,
                                min=0, step=1).props("outlined dense prefix=¥ inputmode=numeric").classes("w-full q-mt-xs")
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
                    summary = staffing.month_cost_summary(record_date[:7])
                    ui.label(f"額面給与 ¥{summary['gross_wages']:,}＋交通費 ¥{summary['transportation']:,}＋会社負担保険 ¥{summary['employer_insurance']:,}").classes("text-[10px] text-grey-7 q-mt-xs")
                    ui.label(f"会社の総負担　¥{summary['company_cost']:,}").classes("text-lg font-black text-primary")
        date_input.on("change", lambda: render_day(date_input.value))
        render_day(selected)
        ui.add_css(".staff-panel,.staff-shift{border-radius:18px!important;background:#fff!important;border:1px solid #E1E9E4!important}.staff-shift .q-item{min-height:46px!important}.dependent-card{border:0!important;border-radius:17px!important;box-shadow:none!important}.dependent-badge{padding:4px 8px;border-radius:999px;background:rgba(255,255,255,.65);font-size:8px;font-weight:900}")
