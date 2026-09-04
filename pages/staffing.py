from datetime import date, timedelta

from fastapi import Request
from nicegui import ui

from core.auth import require_app_access, require_permission
from core.clock import today_jst
from core.staffing import staffing
from core.theme import Theme


@ui.page("/mirai-kessan/staffing")
def staffing_page(request: Request):
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("人件費管理｜未来決算", app_name="mirai-kessan")
    content = Theme.shell("人件費管理", "スタッフ名を保存せず、時給と勤務時間から自動計算",
                          back_to="/mirai-kessan/dashboard", brand="未来決算")
    with content:
        wages = staffing.wages()
        salaries = staffing.monthly_salaries()
        current_month = today_jst().strftime("%Y-%m")
        current_summary = staffing.month_cost_summary(current_month, today_jst())
        with ui.card().classes("staff-total-card w-full q-pa-lg q-mb-sm text-white"):
            ui.label("現時点の会社総負担").classes("text-[10px] opacity-70")
            ui.label(f"¥{current_summary['company_cost']:,}").classes(
                "text-3xl font-black q-mt-xs")
            ui.label(
                f"額面 ¥{current_summary['gross_wages']:,}・交通費 ¥{current_summary['transportation']:,}・会社負担保険 ¥{current_summary['employer_insurance']:,}"
            ).classes("text-[9px] opacity-75 q-mt-sm")
            with ui.row().classes("w-full justify-between items-center q-mt-sm no-wrap"):
                ui.label("月末着地予測").classes("text-[9px] opacity-70")
                ui.label(f"¥{current_summary['forecast_company_cost']:,}").classes(
                    "text-base font-black")
            if current_summary["planned_hourly_gross"]:
                ui.label(
                    f"予定シフト分を含む（バイト予定給与 ¥{current_summary['planned_hourly_gross']:,}）"
                ).classes("text-[8px] opacity-70")
            with ui.element("div").classes("staff-group-grid w-full q-mt-sm"):
                for title, key in (("社員系", "salaried"), ("アルバイト", "hourly")):
                    group = current_summary["groups"][key]
                    with ui.element("div").classes("staff-group-card"):
                        ui.label(title).classes("text-[9px] opacity-70")
                        ui.label(f"¥{group['company_cost']:,}").classes("text-base font-black")
                        ui.label(f"給与 {group['gross_wages']:,}・交通 {group['transportation']:,}・保険 {group['employer_insurance']:,}").classes("text-[7px] opacity-70")
        with ui.expansion("出勤チェック状況　出勤日を見る", icon="fact_check",
                          value=False).classes("attendance-progress-card staff-panel w-full q-mb-sm"):
            def move_attendance_month(offset):
                try:
                    selected_month = date.fromisoformat(f"{attendance_month.value}-01")
                    index = selected_month.year * 12 + selected_month.month - 1 + offset
                    target = date(index // 12, index % 12 + 1, 1).strftime("%Y-%m")
                except (ValueError, TypeError):
                    return
                if target <= current_month:
                    attendance_month.set_value(target)

            with ui.row().classes("w-full items-center no-wrap gap-2"):
                ui.button(icon="chevron_left", on_click=lambda: move_attendance_month(-1)).props(
                    "flat round aria-label='前月を見る'")
                attendance_month = ui.input("対象月", value=current_month,
                    on_change=lambda: attendance_days.refresh()).props(
                        f"outlined dense type=month max={current_month}").classes("grow min-w-0")
                ui.button(icon="chevron_right", on_click=lambda: move_attendance_month(1)).props(
                    "flat round aria-label='翌月を見る'")
            ui.button("今月に戻る", on_click=lambda: attendance_month.set_value(current_month)).props("flat dense")

            @ui.refreshable
            def attendance_days():
                month = str(attendance_month.value or "")
                try:
                    if month > current_month:
                        raise ValueError()
                    progress_by_name = staffing.attendance_progress(month, today_jst().isoformat())
                except (ValueError, TypeError):
                    ui.label("今月以前の対象月を選んでください。")
                    return
                ui.label(f"{month.replace('-', '年')}月の出勤記録").classes("text-sm font-bold q-mt-sm")
                ui.label("緑：出勤登録あり ／ 灰色：出勤登録なし").classes("text-xs text-grey-7")
                for name in staffing.SALARIED_STAFF:
                    progress = progress_by_name[name]
                    with ui.row().classes("w-full items-center justify-between q-mt-xs"):
                        with ui.column().classes("gap-0"):
                            ui.label(name).classes("text-xs font-black")
                            latest = (f"{int(progress['latest_date'][5:7])}月"
                                      f"{int(progress['latest_date'][8:10])}日" if progress["latest_date"] else "まだなし")
                            ui.label(f"最後の出勤：{latest}").classes("text-[9px] text-grey-6")
                        ui.label(f"出勤 {progress['checked_count']}日").classes("text-xs font-black text-primary")
                    with ui.element("div").classes("checked-date-list w-full q-mb-sm"):
                        for day_number in range(1, progress["target_count"] + 1):
                            attended = day_number in progress["checked_days"]
                            ui.label(f"{day_number}日").classes(
                                "checked-date-chip attended" if attended else "checked-date-chip unchecked")
            attendance_days()
        with ui.expansion("副社長・店長・社員の月額給与", icon="badge", value=False).classes(
            "staff-panel w-full"):
            ui.label("副社長は暦日按分、店長・社員は月10日休み・1出勤10時間を基準に配分します").classes(
                "text-[9px] text-grey-6 q-mb-xs")
            salary_inputs = {
                name: ui.number(f"{name}の額面給与", value=salaries[name] or None,
                                min=0, step=1).props("outlined dense prefix=¥ inputmode=numeric").classes("w-full q-mt-xs")
                for name in staffing.SALARIED_STAFF
            }
            def save_salaries():
                staffing.save_monthly_salaries({name: field.value for name, field in salary_inputs.items()})
                ui.notify("月額給与を保存しました", type="positive")
            ui.button("月額給与を保存", icon="save", on_click=save_salaries).classes("w-full q-mt-md")

        with ui.expansion("スタッフ別の時給設定", icon="groups", value=False).classes("staff-panel w-full"):
            wage_inputs = {}
            with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
                for name in staffing.HOURLY_STAFF:
                    wage_inputs[name] = ui.number(name, value=wages[name] or None, min=0, step=1).props(
                        "outlined dense prefix=¥ suffix=/時 inputmode=numeric")

            def save_wages():
                staffing.save_wages({name: field.value for name, field in wage_inputs.items()})
                ui.notify("時給設定を保存しました", type="positive")
            ui.button("時給を保存", icon="save", on_click=save_wages).classes("w-full q-mt-md")

        commute_rates = staffing.commute_rates()
        with ui.expansion("1出勤あたりの交通費", icon="directions_train", value=False).classes(
            "staff-panel w-full q-mt-sm"):
            commute_inputs = {}
            with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
                for name in staffing.STAFF:
                    commute_inputs[name] = ui.number(
                        name, value=commute_rates[name] or None, min=0, step=1
                    ).props("outlined dense prefix=¥ inputmode=numeric")
            def save_commute():
                staffing.save_commute_rates({name: field.value for name, field in commute_inputs.items()})
                ui.notify("交通費設定を保存しました", type="positive")
            ui.button("交通費を保存", icon="save", on_click=save_commute).classes("w-full q-mt-md")

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

        tomorrow = (today_jst() + timedelta(days=1)).isoformat()
        with ui.expansion("明日以降のシフトを簡単入力", icon="event_available", value=False).classes(
            "staff-panel w-full q-mt-sm"):
            ui.label("着地予想専用です。過去の実績から予定時間を見積もりますが、勤務実績には入力しません。").classes(
                "text-xs text-grey-8 q-mb-sm")
            plan_date = ui.input("予定日", value=tomorrow).props(
                f"outlined dense type=date min={tomorrow}").classes("w-full")
            plan_area = ui.column().classes("w-full gap-1")

        def render_simple_plan(record_date):
            plan_area.clear()
            templates = staffing.shift_templates(today_jst())
            existing = staffing.planned_day(record_date)
            with plan_area:
                selections = {}
                for name in staffing.HOURLY_STAFF:
                    selections[name] = {}
                    with ui.row().classes("simple-shift-row w-full items-center no-wrap"):
                        ui.label(name).classes("simple-shift-name")
                        for label, prefix in (("ランチ", "lunch"), ("ディナー", "dinner")):
                            template = templates[name].get(prefix)
                            checked = bool(existing[name].get(f"{prefix}_start"))
                            text = label
                            text += f" {template['start']}〜{template['end']}"
                            selections[name][prefix] = ui.checkbox(text, value=checked).props(
                                "dense")

                def save_simple():
                    try:
                        staffing.save_simple_plan(record_date, {
                            name: {prefix: field.value for prefix, field in fields.items()}
                            for name, fields in selections.items()
                        }, today_jst())
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    summary = staffing.month_cost_summary(record_date[:7], today_jst())
                    ui.notify(f"予定を保存しました。月末予測 ¥{summary['forecast_company_cost']:,}", type="positive")
                    ui.navigate.to("/mirai-kessan/staffing")
                ui.button("予定シフトを保存", icon="save", on_click=save_simple).classes("w-full q-mt-sm")

        plan_date.on("change", lambda: render_simple_plan(plan_date.value))
        render_simple_plan(tomorrow)

        requested_day = str(request.query_params.get("date", ""))
        try:
            selected = date.fromisoformat(requested_day).isoformat()
        except ValueError:
            selected = today_jst().isoformat()
        with ui.expansion("勤務・出勤を入力", icon="schedule", value=False).classes(
            "staff-panel w-full q-mt-sm"):
            date_input = ui.input("日付", value=selected).props("outlined dense type=date").classes("w-full")
            @ui.refreshable
            def timecard_progress_summary(month):
                progress = staffing.timecard_progress(month, today_jst().isoformat())
                with ui.expansion(
                    f"入力状況　{month.replace('-', '年')}月", icon="fact_check", value=True,
                ).classes("timecard-progress w-full q-mt-sm"):
                    with ui.element("div").classes("timecard-progress-grid w-full"):
                        for name in staffing.STAFF:
                            item = progress[name]
                            latest = (f"最終入力：{int(item['latest_date'][8:10])}日"
                                      if item["latest_date"] else "まだ入力なし")
                            with ui.element("div").classes(
                                    "timecard-progress-person entered" if item["latest_date"]
                                    else "timecard-progress-person"):
                                ui.label(name).classes("timecard-progress-name")
                                ui.label(latest).classes("timecard-progress-latest")
                                ui.label(f"{item['entered_count']}日分").classes(
                                    "timecard-progress-count")
                                ui.label("入力済み：" + ("・".join(map(str, item["entered_days"])) or "なし")).classes("text-xs break-words")
                                ui.label("未確認：" + ("・".join(map(str, item["missing_days"])) or "なし")).classes("text-xs text-orange-9 break-words")
                    ui.label("休みの日も、その人の入力欄を空欄のまま保存すると確認済みになります。未確認＝欠勤ではありません。").classes("text-xs q-mt-sm")

            timecard_progress_summary(selected[:7])
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
                        entered = values[name].get("entry_confirmed") or values[name]["attended"] or any(
                            values[name][key] for key in ("lunch_start", "lunch_end", "dinner_start", "dinner_end"))
                        with ui.expansion(f"{name}　{'入力済み' if entered else '未入力'}", value=False).classes("staff-shift w-full q-mb-xs") as staff_panel:
                            if name in staffing.HOURLY_STAFF:
                                for label, prefix in (("ランチ", "lunch"), ("ディナー", "dinner")):
                                    ui.label(label).classes("text-[10px] font-bold q-mt-xs")
                                    with ui.row().classes("w-full gap-2 no-wrap"):
                                        for title, suffix in (("開始", "start"), ("終了", "end")):
                                            key = f"{prefix}_{suffix}"
                                            shift_inputs[name][key] = ui.input(
                                                title, value=values[name][key]
                                            ).props(
                                                "outlined dense inputmode=numeric placeholder='10:00'"
                                            ).classes("grow")
                                    ui.button(
                                        f"{label}の入力を消す", icon="backspace",
                                        on_click=lambda _, person=name, session=prefix: (
                                            shift_inputs[person][f"{session}_start"].set_value(""),
                                            shift_inputs[person][f"{session}_end"].set_value(""),
                                        ),
                                    ).props("flat dense no-caps color=negative").classes(
                                        "timecard-clear-shift")
                                shift_inputs[name]["break_minutes"] = ui.number(
                                    "休憩時間（賄いを含む）", value=values[name]["break_minutes"] or None,
                                    min=0, max=1440, step=1
                                ).props("outlined dense suffix=分 inputmode=numeric").classes("w-full q-mt-xs")
                            else:
                                for key in ("lunch_start", "lunch_end", "dinner_start", "dinner_end"):
                                    shift_inputs[name][key] = ui.input(value="").props("type=hidden").classes("hidden")
                                shift_inputs[name]["attended"] = ui.checkbox(
                                    "この日は出勤", value=values[name]["attended"]
                                ).classes("q-mt-xs")
                                shift_inputs[name]["break_minutes"] = ui.number(value=0).props(
                                    "disable").classes("hidden")
                            if name in staffing.HOURLY_STAFF:
                                shift_inputs[name]["attended"] = ui.checkbox(value=False).props("disable").classes("hidden")
                            detail = staffing.day_detail(record_date, name)
                            if detail["total_minutes"]:
                                ui.label(
                                    f"{detail['total_minutes']//60}時間{detail['total_minutes']%60}分"
                                    f"（休憩 {detail['break_minutes']}分・支払対象 {detail['paid_minutes']//60}時間{detail['paid_minutes']%60}分・深夜 {detail['night_minutes']}分）　¥{detail['pay']:,}"
                                ).classes("text-[10px] font-bold text-primary q-mt-sm")

                            def save_person(_, person=name, panel=staff_panel):
                                try:
                                    staffing.save_person(record_date, person, {
                                        key: field.value for key, field in shift_inputs[person].items()
                                    })
                                except ValueError as error:
                                    ui.notify(str(error), type="negative")
                                    return
                                panel.set_text(f"{person}　入力済み")
                                timecard_progress_summary.refresh(record_date[:7])
                                attendance_days.refresh()
                                totals.refresh()
                                ui.notify(f"{person}の{record_date}を保存しました", type="positive")

                            ui.button("この人の入力を保存（空欄なら休み）", icon="save", on_click=save_person).classes("w-full q-mt-sm")

                    @ui.refreshable
                    def totals():
                        ui.label(f"この日の賃金・交通費　¥{staffing.day_total(record_date):,}").classes("text-base font-black text-primary q-mt-md")
                        summary = staffing.month_cost_summary(record_date[:7], today_jst())
                        ui.label(f"額面給与 ¥{summary['gross_wages']:,}＋交通費 ¥{summary['transportation']:,}＋会社負担保険 ¥{summary['employer_insurance']:,}").classes("text-xs text-grey-7 q-mt-xs")
                        ui.label(f"現時点の会社総負担　¥{summary['company_cost']:,}").classes("text-lg font-black text-primary")
                        ui.label(f"月末着地予測　¥{summary['forecast_company_cost']:,}").classes("text-sm font-black q-mt-xs")
                    totals()
        def change_timecard_date():
            timecard_progress_summary.refresh(date_input.value[:7])
            render_day(date_input.value)

        date_input.on("change", change_timecard_date)
        render_day(selected)
        ui.add_css(".staff-total-card{border:0!important;border-radius:24px!important;background:linear-gradient(145deg,#173D30,#52795D)!important;box-shadow:0 12px 30px rgba(24,61,45,.16)!important}.staff-group-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.staff-group-card{min-width:0;padding:9px;border-radius:13px;background:rgba(255,255,255,.12);overflow:hidden}.staff-group-card .q-label{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.attendance-progress-card{border-radius:19px!important;border:1px solid #E1E9E4!important;box-shadow:none!important}.checked-date-list{display:grid;grid-template-columns:repeat(7,1fr);gap:5px;margin-top:6px}.checked-date-chip{padding:6px 2px;border-radius:9px;font-size:9px;font-weight:900;text-align:center}.checked-date-chip.attended{background:#DDF1E5;color:#28704A;border:1px solid #B9DEC8}.checked-date-chip.unchecked{background:#F1F3F2;color:#9AA39E;border:1px solid #E4E8E5}.staff-panel,.staff-shift{border-radius:18px!important;background:#fff!important;border:1px solid #E1E9E4!important}.staff-shift .q-item{min-height:46px!important}.simple-shift-row{padding:6px 4px;border-bottom:1px solid #edf1ee;overflow-x:auto}.simple-shift-name{min-width:58px;font-size:10px;font-weight:900}.simple-shift-row .q-checkbox__label{font-size:9px;white-space:nowrap}.dependent-card{border:0!important;border-radius:17px!important;box-shadow:none!important}.dependent-badge{padding:4px 8px;border-radius:999px;background:rgba(255,255,255,.65);font-size:8px;font-weight:900}")
        ui.add_css(".staff-total-card *,.staff-group-card *,.attendance-progress-card *,.staff-panel *{min-width:0;box-sizing:border-box}.staff-total-card .text-2xl,.staff-total-card .text-xl,.staff-total-card .text-lg{max-width:100%;font-size:clamp(13px,5vw,22px)!important;letter-spacing:-.04em;white-space:nowrap;overflow:hidden;text-overflow:clip;font-variant-numeric:tabular-nums}.timecard-progress{border-radius:15px!important;background:#F8FAF8!important;border:1px solid #E1E9E4!important}.timecard-progress-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;padding:5px 10px 12px}.timecard-progress-person{min-width:0;padding:9px;border-radius:13px;background:#F1F3F2;border:1px solid #E4E8E5}.timecard-progress-person.entered{background:#E9F5ED;border-color:#C9E3D2}.timecard-progress-name{font-size:10px;font-weight:950}.timecard-progress-latest{font-size:11px;font-weight:950;color:#286B49}.timecard-progress-count{font-size:8px;color:#7A8780}.timecard-clear-shift{align-self:flex-end!important;margin-top:-2px!important;font-size:9px!important}@media(max-width:520px){.staff-total-card,.staff-panel,.attendance-progress-card{padding-left:13px!important;padding-right:13px!important}.staff-group-card{padding:8px 6px}}")
