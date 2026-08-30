from datetime import date
from html import escape

from nicegui import ui

from core.auth import current_role, require_app_access
from core.clock import today_jst
from core.shift_submissions import shift_submissions
from core.theme import Theme
from pages.store_common import store_header_actions


@ui.page("/store-ops/shift-submission")
def shift_submission_page():
    if not require_app_access("store_ops"):
        return
    Theme.page("シフト提出｜店舗運営", app_name="store-ops")
    today = today_jst()
    if today.day <= 5:
        default_half, default_month, default_year = "second", today.month, today.year
    elif today.day <= 20:
        default_half = "first"
        default_month = (today.month % 12) + 1
        default_year = today.year + (1 if today.month == 12 else 0)
    else:
        default_half = "second"
        default_month = (today.month % 12) + 1
        default_year = today.year + (1 if today.month == 12 else 0)

    content = Theme.shell("シフト提出", "半月ごとの希望をまとめて提出",
                          back_to="/store-ops", action=store_header_actions,
                          brand="店舗運営")
    with content:
        with ui.card().classes("shift-guide w-full q-pa-lg q-mb-md"):
            ui.label("提出期限").classes("text-[10px] font-black opacity-70")
            ui.label("前半分は前月20日・後半分は当月5日まで").classes(
                "text-base font-black q-mt-xs")

        with ui.card().classes("surface-card w-full q-pa-lg"):
            staff = ui.select(list(shift_submissions.STAFF), label="名前を選択").props(
                "outlined dense").classes("w-full")
            with ui.row().classes("w-full gap-2 no-wrap q-mt-sm"):
                year = ui.number("年", value=default_year, min=2026, max=2100, step=1).props(
                    "outlined dense").classes("grow")
                month = ui.select(list(range(1, 13)), value=default_month, label="月").props(
                    "outlined dense").classes("grow")
            half = ui.toggle({"first": "前半 1〜15日", "second": "後半 16日〜"},
                             value=default_half).props("unelevated spread no-caps").classes(
                                 "w-full q-mt-sm")
            ui.label("名前・期間を選んで「入力を開く」を押してください").classes(
                "text-[10px] text-grey-6 q-mt-sm")

            editor = ui.column().classes("w-full gap-0 q-mt-md")

            def open_editor():
                if not staff.value:
                    ui.notify("名前を選択してください", type="negative")
                    return
                try:
                    submission = shift_submissions.submission(
                        staff.value, int(year.value), int(month.value), half.value)
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                editor.clear()
                period = submission["period"]
                fields = {}
                with editor:
                    ui.separator().classes("q-my-sm")
                    ui.label(period["label"]).classes("text-lg font-black")
                    deadline = period["deadline"][5:].replace("-", "/")
                    ui.label(f"提出期限 {deadline}").classes("text-[10px] text-negative font-bold")
                    if submission.get("pending_change"):
                        ui.label("変更申請は管理者の確認待ちです").classes(
                            "pending-notice w-full q-mt-sm")
                    for day in range(period["start"], period["end"] + 1):
                        weekday = date(period["year"], period["month"], day).strftime("%a")
                        weekday_jp = {"Mon": "月", "Tue": "火", "Wed": "水", "Thu": "木",
                                      "Fri": "金", "Sat": "土", "Sun": "日"}[weekday]
                        with ui.column().classes("shift-day-row w-full gap-1"):
                            ui.label(f"{day}日（{weekday_jp}）").classes("shift-day-label")
                            saved_day = submission["days"].get(
                                str(day), {"type": "", "start": "", "end": ""})
                            with ui.element("div").classes("shift-input-grid w-full"):
                                shift_type = ui.select(
                                    ["", *shift_submissions.OPTIONS],
                                    value=saved_day.get("type", ""), label="希望",
                                ).props("outlined dense options-dense").classes("shift-kind")
                                with ui.row().classes("shift-time-pair w-full no-wrap gap-1"):
                                    start = ui.input("開始", value=saved_day.get("start", "")).props(
                                        "outlined dense type=time").classes("shift-time")
                                    end = ui.input("終了", value=saved_day.get("end", "")).props(
                                        "outlined dense type=time").classes("shift-time")
                            fields[str(day)] = {"type": shift_type, "start": start, "end": end}
                    note = ui.textarea("希望・連絡事項（任意）", value=submission["note"]).props(
                        "outlined autogrow").classes("w-full q-mt-sm")

                    def save_submission():
                        try:
                            result = shift_submissions.save(
                                staff.value, period["year"], period["month"], period["half"],
                                {day: {key: field.value for key, field in day_fields.items()}
                                 for day, day_fields in fields.items()}, note.value)
                        except ValueError as error:
                            ui.notify(str(error), type="negative")
                            return
                        if result.get("change_request"):
                            ui.notify("期限後のため、変更申請を送りました", type="warning")
                        else:
                            ui.notify("シフト希望を保存しました", type="positive")
                        open_editor()

                    expired_change = bool(submission["submitted_at"]) and today > date.fromisoformat(
                        period["deadline"])
                    button_text = "変更を申請" if expired_change else (
                        "この内容で変更" if submission["submitted_at"] else "この内容で提出")
                    ui.button(button_text, icon="send", on_click=save_submission).classes(
                        "shift-submit w-full q-mt-md")
                    if submission["submitted_at"]:
                        ui.label(f"前回提出：{submission['submitted_at'][5:].replace('-', '/')}").classes(
                            "text-[9px] text-grey-6 text-center w-full q-mt-xs")
                    ui.button("入力を閉じる", icon="expand_less", on_click=editor.clear).props(
                        "flat no-caps color=grey-7").classes("w-full q-mt-sm")

            ui.button("入力を開く", icon="edit_calendar", on_click=open_editor).props(
                "outline no-caps").classes("w-full q-mt-md")

        if current_role() == "owner":
            with ui.expansion("シフト案を自動作成", icon="auto_awesome", value=False).classes(
                    "surface-card w-full q-mt-md"):
                ui.label("提出された希望だけを使って、偏りを抑えた下書きを作ります").classes(
                    "text-xs font-black")
                ui.label("勤務実績には反映されません。人数不足の日も隠さず表示します。").classes(
                    "text-[9px] text-grey-6 q-mb-sm")
                with ui.row().classes("w-full gap-2 no-wrap"):
                    auto_lunch = ui.number(
                        "ランチ必要人数", value=3, min=0, max=30, step=1,
                    ).props("outlined dense").classes("grow")
                    auto_dinner = ui.number(
                        "ディナー必要人数", value=4, min=0, max=30, step=1,
                    ).props("outlined dense").classes("grow")
                auto_thick_days = ui.input(
                    "厚めにする日（例：5, 12, 20）",
                ).props("outlined dense").classes("w-full q-mt-sm")
                auto_deputy_rest = ui.switch(
                    "副社長はできるだけ休みを多くする", value=True,
                ).classes("text-[10px] font-bold")
                auto_employee_rest = ui.switch(
                    "社員Aの休みを1日多めにする", value=False,
                ).classes("text-[10px] font-bold")
                auto_leader_required = ui.switch(
                    "店長か副社長のどちらかは出勤にする", value=True,
                ).classes("text-[10px] font-bold")
                auto_pair_together = ui.switch(
                    "副社長と社員Aは出勤・休みを極力そろえる", value=True,
                ).classes("text-[10px] font-bold")
                auto_result = ui.column().classes("w-full gap-1 q-mt-sm")

                def build_auto_schedule():
                    raw_days = str(auto_thick_days.value or "").replace("、", ",")
                    thick_days = [value.strip() for value in raw_days.split(",")]
                    try:
                        result = shift_submissions.auto_schedule(
                            int(year.value), int(month.value), half.value,
                            auto_lunch.value, auto_dinner.value, thick_days,
                            auto_deputy_rest.value, auto_employee_rest.value,
                            auto_leader_required.value, auto_pair_together.value,
                        )
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    auto_result.clear()
                    with auto_result:
                        shortage_days = sum(
                            1 for value in result["days"].values()
                            if value["shortages"]["lunch"] or value["shortages"]["dinner"])
                        if shortage_days:
                            ui.label(f"人数不足の日が {shortage_days}日あります").classes(
                                "auto-shift-warning w-full")
                        else:
                            ui.label("必要人数を満たす案ができました").classes(
                                "auto-shift-success w-full")
                        table = ['<div class="shift-sheet-scroll"><table class="shift-sheet auto-shift-sheet">',
                                 '<thead><tr><th class="date-head">日付</th>']
                        for name in shift_submissions.STAFF:
                            table.append(f'<th class="staff-head">{escape(name)}</th>')
                        table.append('<th class="staff-head">不足</th></tr></thead><tbody>')
                        period = result["period"]
                        for day in range(period["start"], period["end"] + 1):
                            value = result["days"][str(day)]
                            weekday = date(period["year"], period["month"], day).strftime("%a")
                            weekday_jp = {"Mon": "月", "Tue": "火", "Wed": "水", "Thu": "木",
                                          "Fri": "金", "Sat": "土", "Sun": "日"}[weekday]
                            table.append(f'<tr><th class="date-cell"><b>{day}</b><span>{weekday_jp}</span></th>')
                            for name in shift_submissions.STAFF:
                                staff_plan = value["staff"][name]
                                lunch_on, dinner_on = staff_plan["lunch"], staff_plan["dinner"]
                                if lunch_on and dinner_on:
                                    text, css = "通し", "both-on"
                                elif lunch_on:
                                    text, css = "L", "lunch-on"
                                elif dinner_on:
                                    text, css = "D", "dinner-on"
                                else:
                                    text, css = "", "day-off"
                                if text and staff_plan["time"] not in {"ランチ", "ディナー", "通し"}:
                                    text += f'<small>{escape(staff_plan["time"])}</small>'
                                table.append(f'<td class="shift-cell {css}">{text}</td>')
                            shortage = value["shortages"]
                            shortage_text = " / ".join(part for part in (
                                f'L {shortage["lunch"]}' if shortage["lunch"] else "",
                                f'D {shortage["dinner"]}' if shortage["dinner"] else "",
                            ) if part)
                            table.append(f'<td class="shift-cell shortage">{shortage_text or "—"}</td></tr>')
                        table.append('</tbody></table></div>')
                        ui.html(''.join(table), sanitize=False).classes("w-full")
                        ui.label("L＝ランチ、D＝ディナー。これは編集前提の下書きです。").classes(
                            "text-[9px] text-grey-6 q-mt-xs")
                    ui.notify("シフト案を作成しました", type="positive")

                ui.button("シフト案を作る", icon="auto_awesome", on_click=build_auto_schedule).props(
                    "unelevated no-caps").classes("shift-submit w-full q-mt-sm")

            with ui.expansion("管理者用・提出状況", icon="fact_check", value=False).classes(
                    "surface-card w-full q-mt-md"):
                overview = ui.column().classes("w-full gap-1")

                def show_overview():
                    try:
                        period = shift_submissions.period(
                            int(year.value), int(month.value), half.value)
                        submitted = shift_submissions.period_submissions(
                            int(year.value), int(month.value), half.value)
                        pending = shift_submissions.pending_changes(
                            int(year.value), int(month.value), half.value)
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    overview.clear()
                    with overview:
                        ui.label(period["label"]).classes("text-sm font-black q-mb-xs")
                        ui.label("未入力の日は休み扱い。未提出とは区別して表示します").classes(
                            "text-[9px] text-grey-6 q-mb-sm")
                        if pending:
                            ui.label(f"変更申請　{len(pending)}件").classes(
                                "text-sm font-black text-warning q-mt-sm q-mb-xs")
                            for name, request in pending.items():
                                with ui.card().classes("change-request-card w-full q-pa-md q-mb-sm"):
                                    ui.label(name).classes("text-sm font-black")
                                    ui.label(f"申請日時 {request.get('requested_at', '')[5:].replace('-', '/')}").classes(
                                        "text-[9px] text-grey-6")
                                    changes = []
                                    for request_day, request_value in sorted(
                                            request.get("days", {}).items(), key=lambda value: int(value[0])):
                                        value = shift_submissions._day_value(request_value)
                                        text = value["type"] or "時間指定"
                                        if value["start"] or value["end"]:
                                            text += f" {value['start'] or '指定なし'}〜{value['end'] or '指定なし'}"
                                        changes.append(f"{request_day}日：{text}")
                                    ui.label("／".join(changes) if changes else "全日希望なし").classes(
                                        "request-summary q-mt-sm")
                                    with ui.row().classes("w-full gap-2 q-mt-sm"):
                                        ui.button("拒否", icon="close", on_click=lambda _, staff_name=name: (
                                            shift_submissions.review_change(
                                                staff_name, period["year"], period["month"],
                                                period["half"], False),
                                            show_overview()
                                        )).props("outline no-caps color=negative").classes("grow")
                                        ui.button("承認", icon="check", on_click=lambda _, staff_name=name: (
                                            shift_submissions.review_change(
                                                staff_name, period["year"], period["month"],
                                                period["half"], True),
                                            show_overview()
                                        )).props("unelevated no-caps color=positive").classes("grow")
                        table = ['<div class="shift-sheet-scroll"><table class="shift-sheet">',
                                 '<thead><tr><th class="date-head" rowspan="2">日付</th>']
                        for name in shift_submissions.STAFF:
                            table.append(f'<th class="staff-head" colspan="2">{escape(name)}</th>')
                        table.append('</tr><tr>')
                        for _ in shift_submissions.STAFF:
                            table.append('<th class="lunch-head">ランチ</th><th class="dinner-head">ディナー</th>')
                        table.append('</tr></thead><tbody>')
                        for day in range(period["start"], period["end"] + 1):
                            weekday = date(period["year"], period["month"], day).strftime("%a")
                            weekday_jp = {"Mon": "月", "Tue": "火", "Wed": "水", "Thu": "木",
                                          "Fri": "金", "Sat": "土", "Sun": "日"}[weekday]
                            weekend = " sunday" if weekday_jp == "日" else (
                                " saturday" if weekday_jp == "土" else "")
                            table.append(f'<tr><th class="date-cell{weekend}"><b>{day}</b><span>{weekday_jp}</span></th>')
                            for name in shift_submissions.STAFF:
                                record = submitted.get(name)
                                value = shift_submissions._day_value(
                                    record.get("days", {}).get(str(day), {})) if record else {
                                        "type": "", "start": "", "end": ""}
                                time_text = ""
                                if value["start"] or value["end"]:
                                    time_text = f"{value['start'] or '—'}〜{value['end'] or '—'}"
                                for meal in ("ランチ", "ディナー"):
                                    shift_type = value["type"]
                                    active = shift_type in {meal, "通し"}
                                    if shift_type == "絶対休み":
                                        text, css = "休", "absolute-off"
                                    elif active:
                                        text = time_text or ("通し" if shift_type == "通し" else "希望")
                                        css = "lunch-on" if meal == "ランチ" else "dinner-on"
                                    elif not record:
                                        text, css = "未提出", "not-submitted"
                                    else:
                                        text, css = "", "day-off"
                                    table.append(f'<td class="shift-cell {css}">{escape(text)}</td>')
                            table.append('</tr>')
                        table.append('</tbody></table></div>')
                        ui.html(''.join(table), sanitize=False).classes("w-full")

                ui.button("選択中の期間を確認", icon="refresh", on_click=show_overview).props(
                    "outline no-caps").classes("w-full q-mb-sm")

        ui.add_css("""
        .shift-guide{border:0!important;border-radius:24px!important;color:white!important;background:linear-gradient(135deg,#173D30,#4F7C68)!important}
        .shift-day-row{padding:9px 0;border-bottom:1px solid #EDF1EE}.shift-day-label{font-size:11px;font-weight:900}.shift-input-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:6px;align-items:start}.shift-kind{width:100%}.shift-time-pair{width:100%}.shift-time{width:50%;min-width:0;flex:1}.shift-time .q-field__label{font-size:9px}.pending-notice{padding:9px 11px;border-radius:10px;background:#FFF2D9;color:#966317;font-size:10px;font-weight:900}.shift-submit{background:#2F7457!important;color:#fff!important;border-radius:14px!important;font-weight:900!important}.change-request-card{border:1px solid #E6B65E!important;border-radius:17px!important;box-shadow:none!important;background:#FFFBF2!important}.request-summary{padding:8px 10px;border-radius:9px;background:#fff;font-size:9px;line-height:1.6}.admin-day-card{border:1px solid #E1E9E4!important;border-radius:17px!important;box-shadow:none!important}.admin-shift-row{padding:5px 0;border-top:1px solid #F0F2F1}.admin-staff-name{width:64px;flex:0 0 64px;font-size:10px;font-weight:900}.admin-shift-value{min-width:0;padding:5px 8px;border-radius:8px;font-size:9px;font-weight:800}.admin-shift-value.available{background:#DFF2E7;color:#276D49}.admin-shift-value.absolute-off{background:#FFE2E2;color:#A43E3E}.admin-shift-value.day-off{background:#F1F3F2;color:#7C8781}.admin-shift-value.not-submitted{background:#FFF0D7;color:#9A671D}
        .shift-sheet-scroll{width:100%;max-height:68vh;overflow:auto;border:1px solid #DDE5E0;border-radius:14px;background:#fff}.shift-sheet{border-collapse:separate;border-spacing:0;min-width:max-content;font-size:9px}.shift-sheet th,.shift-sheet td{border-right:1px solid #E1E7E3;border-bottom:1px solid #E1E7E3;text-align:center}.shift-sheet thead th{position:sticky;z-index:4;background:#243E34;color:#fff}.shift-sheet thead tr:first-child th{top:0;height:36px}.shift-sheet thead tr:nth-child(2) th{top:36px;height:28px}.date-head{left:0;z-index:7!important;min-width:58px}.staff-head{min-width:156px;font-size:10px}.lunch-head,.dinner-head{width:78px;min-width:78px}.lunch-head{background:#315F72!important}.dinner-head{background:#795B35!important}.date-cell{position:sticky;left:0;z-index:3;width:58px;height:48px;background:#F5F7F5;color:#34443C}.date-cell b,.date-cell span{display:block}.date-cell b{font-size:13px}.date-cell.saturday{color:#2E6FA2;background:#EFF7FC}.date-cell.sunday{color:#B24B4B;background:#FFF2F1}.shift-cell{width:78px;max-width:78px;height:48px;padding:4px;white-space:normal;font-weight:800;line-height:1.25}.shift-cell.lunch-on{background:#D9F0FA;color:#245D75}.shift-cell.dinner-on{background:#F8E8C9;color:#79551F}.shift-cell.absolute-off{background:#F8DADA;color:#9A3C3C}.shift-cell.not-submitted{color:#A08760;background:#FFF9ED;font-size:8px}.shift-cell.day-off{background:#FAFBFA}
        .auto-shift-warning,.auto-shift-success{padding:9px 11px;border-radius:10px;font-size:10px;font-weight:900}.auto-shift-warning{background:#FFF0D7;color:#946018}.auto-shift-success{background:#DFF2E7;color:#276D49}.auto-shift-sheet .staff-head{min-width:80px}.auto-shift-sheet .shift-cell{width:80px;max-width:80px}.auto-shift-sheet .both-on{background:#E6E0F7;color:#5B438D}.auto-shift-sheet .shortage{background:#FFF1EE;color:#B2463E}.auto-shift-sheet small{display:block;font-size:7px;line-height:1.2;margin-top:2px}
        """)
