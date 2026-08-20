from datetime import date

from nicegui import ui

from core.auth import current_role, require_app_access
from core.clock import today_jst
from core.shift_submissions import shift_submissions
from core.theme import Theme


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
                          back_to="/store-ops", brand="店舗運営")
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
                    for day in range(period["start"], period["end"] + 1):
                        weekday = date(period["year"], period["month"], day).strftime("%a")
                        weekday_jp = {"Mon": "月", "Tue": "火", "Wed": "水", "Thu": "木",
                                      "Fri": "金", "Sat": "土", "Sun": "日"}[weekday]
                        with ui.row().classes("shift-day-row w-full items-center no-wrap"):
                            ui.label(f"{day}日（{weekday_jp}）").classes("shift-day-label")
                            fields[str(day)] = ui.select(
                                ["", *shift_submissions.OPTIONS],
                                value=submission["days"].get(str(day), ""),
                            ).props("outlined dense options-dense").classes("grow")
                    note = ui.textarea("希望・連絡事項（任意）", value=submission["note"]).props(
                        "outlined autogrow").classes("w-full q-mt-sm")

                    def save_submission():
                        try:
                            shift_submissions.save(
                                staff.value, period["year"], period["month"], period["half"],
                                {day: field.value for day, field in fields.items()}, note.value)
                        except ValueError as error:
                            ui.notify(str(error), type="negative")
                            return
                        ui.notify("シフト希望を提出しました", type="positive")

                    ui.button("この内容で提出", icon="send", on_click=save_submission).classes(
                        "shift-submit w-full q-mt-md")
                    if submission["submitted_at"]:
                        ui.label(f"前回提出：{submission['submitted_at'][5:].replace('-', '/')}").classes(
                            "text-[9px] text-grey-6 text-center w-full q-mt-xs")

            ui.button("入力を開く", icon="edit_calendar", on_click=open_editor).props(
                "outline no-caps").classes("w-full q-mt-md")

        if current_role() == "owner":
            with ui.expansion("管理者用・提出状況", icon="fact_check", value=False).classes(
                    "surface-card w-full q-mt-md"):
                overview = ui.column().classes("w-full gap-1")

                def show_overview():
                    try:
                        period = shift_submissions.period(
                            int(year.value), int(month.value), half.value)
                        submitted = shift_submissions.period_submissions(
                            int(year.value), int(month.value), half.value)
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    overview.clear()
                    with overview:
                        ui.label(period["label"]).classes("text-sm font-black q-mb-xs")
                        for name in shift_submissions.STAFF:
                            record = submitted.get(name)
                            with ui.row().classes("overview-row w-full items-center no-wrap"):
                                ui.icon("check_circle" if record else "radio_button_unchecked").classes(
                                    "text-positive" if record else "text-grey-4")
                                ui.label(name).classes("text-xs font-bold grow")
                                ui.label("提出済み" if record else "未提出").classes(
                                    "text-[10px] text-positive font-bold" if record
                                    else "text-[10px] text-grey-5")

                ui.button("選択中の期間を確認", icon="refresh", on_click=show_overview).props(
                    "outline no-caps").classes("w-full q-mb-sm")

        ui.add_css("""
        .shift-guide{border:0!important;border-radius:24px!important;color:white!important;background:linear-gradient(135deg,#173D30,#4F7C68)!important}
        .shift-day-row{padding:7px 0;border-bottom:1px solid #EDF1EE}.shift-day-label{width:76px;font-size:12px;font-weight:900}.shift-submit{background:#2F7457!important;color:#fff!important;border-radius:14px!important;font-weight:900!important}.overview-row{padding:8px 2px;border-bottom:1px solid #EDF1EE}
        """)
