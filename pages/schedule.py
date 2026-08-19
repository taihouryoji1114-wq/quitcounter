import calendar
from datetime import timedelta

from nicegui import ui

from core.auth import log_out, require_app_access, selected_user_id
from core.clock import today_jst
from core.schedule import schedule
from core.theme import Theme


@ui.page("/schedule")
def schedule_page():
    if not require_app_access("schedule"):
        return
    Theme.page("My Schedule", app_name="schedule")
    user_id = selected_user_id()
    today = today_jst()
    viewed_month = [today.replace(day=1)]

    def reload(message=None):
        if message:
            ui.notify(message, type="positive")
        ui.navigate.to("/schedule")

    def logout_action():
        ui.button(icon="logout", on_click=lambda: log_out("/schedule/login")).props(
            "flat round").classes("text-grey-8")

    content = Theme.shell("My Schedule", "予定を並べるだけで、今日が決まる",
                          action=logout_action, brand="My Schedule")
    with content:
        with ui.dialog() as add_dialog, ui.card().classes("schedule-dialog q-pa-lg"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("予定を追加").classes("text-xl font-black")
                ui.button(icon="close", on_click=add_dialog.close).props("flat round")
            title = ui.input("予定").props("outlined dense autofocus").classes("w-full")
            event_date = ui.input("日付", value=today.isoformat()).props(
                "outlined dense type=date").classes("w-full")
            with ui.row().classes("w-full gap-2 no-wrap"):
                start_time = ui.input("開始", value="").props("outlined dense type=time").classes("grow")
                end_time = ui.input("終了", value="").props("outlined dense type=time").classes("grow")
            category = ui.select(["仕事", "個人", "家族", "健康", "移動", "その他"],
                                 value="個人", label="分類").props("outlined dense").classes("w-full")
            note = ui.textarea("メモ（任意）").props("outlined autogrow").classes("w-full")

            def add_event():
                try:
                    schedule.add_event(user_id, title.value, event_date.value, start_time.value,
                                       end_time.value, category.value, note.value)
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                add_dialog.close()
                reload("予定を追加しました")
            ui.button("追加する", icon="add", on_click=add_event).classes("w-full q-mt-sm")

        delete_target = {"id": None}
        with ui.dialog() as delete_dialog, ui.card().classes("schedule-dialog q-pa-lg"):
            ui.label("この予定を削除しますか？").classes("text-lg font-black")
            delete_title = ui.label().classes("text-sm text-grey-7")

            def confirm_delete():
                schedule.delete_event(user_id, delete_target["id"])
                delete_dialog.close()
                reload("予定を削除しました")
            with ui.row().classes("w-full gap-2 q-mt-md"):
                ui.button("キャンセル", on_click=delete_dialog.close).props("flat").classes("grow")
                ui.button("削除", icon="delete", on_click=confirm_delete).props(
                    "unelevated color=negative").classes("grow")

        def open_delete(item):
            delete_target["id"] = item["id"]
            delete_title.set_text(item["title"])
            delete_dialog.open()

        with ui.card().classes("schedule-hero w-full q-pa-lg text-white"):
            ui.label(today.strftime("%Y年%m月%d日")).classes("text-[10px] opacity-70")
            ui.label("今日を整える").classes("text-3xl font-black q-mt-xs")
            today_events = schedule.events(user_id, today.isoformat(), today.isoformat())
            ui.label(f"今日の予定 {len(today_events)}件").classes("text-sm opacity-80 q-mt-xs")
            ui.button("予定を追加", icon="add", on_click=add_dialog.open).props(
                "unelevated no-caps").classes("schedule-add w-full q-mt-md")

        @ui.refreshable
        def calendar_view():
            month = viewed_month[0]
            start = month.isoformat()
            if month.month == 12:
                next_month = month.replace(year=month.year + 1, month=1)
            else:
                next_month = month.replace(month=month.month + 1)
            end = (next_month - timedelta(days=1)).isoformat()
            events = schedule.events(user_id, start, end)
            by_date = {}
            for item in events:
                by_date.setdefault(item["date"], []).append(item)

            with ui.card().classes("schedule-panel w-full q-pa-md q-mt-sm"):
                with ui.row().classes("w-full items-center justify-between"):
                    def move(amount):
                        current = viewed_month[0]
                        total = current.year * 12 + current.month - 1 + amount
                        viewed_month[0] = current.replace(year=total // 12, month=total % 12 + 1)
                        calendar_view.refresh()
                    ui.button(icon="chevron_left", on_click=lambda: move(-1)).props("flat round")
                    ui.label(month.strftime("%Y年%m月")).classes("text-lg font-black")
                    ui.button(icon="chevron_right", on_click=lambda: move(1)).props("flat round")
                with ui.element("div").classes("schedule-weekdays w-full"):
                    for label in ("月", "火", "水", "木", "金", "土", "日"):
                        ui.label(label)
                with ui.element("div").classes("schedule-calendar w-full"):
                    for week in calendar.monthcalendar(month.year, month.month):
                        for day in week:
                            if not day:
                                ui.element("div").classes("schedule-day empty")
                                continue
                            day_date = month.replace(day=day).isoformat()
                            day_events = by_date.get(day_date, [])
                            classes = "schedule-day"
                            if day_date == today.isoformat():
                                classes += " schedule-today"
                            with ui.element("div").classes(classes).on(
                                "click", lambda _, value=day_date: (event_date.set_value(value), add_dialog.open())):
                                ui.label(str(day)).classes("day-number")
                                if day_events:
                                    ui.label(str(len(day_events))).classes("event-count")
                                    ui.label(day_events[0]["title"]).classes("event-preview")
        calendar_view()

        upcoming_end = (today + timedelta(days=30)).isoformat()
        upcoming = schedule.events(user_id, today.isoformat(), upcoming_end)
        with ui.expansion(f"これからの予定　{len(upcoming)}件", icon="event",
                          value=True).classes("schedule-panel w-full q-mt-sm"):
            if not upcoming:
                ui.label("予定はまだありません").classes("text-sm text-grey-6 q-pa-md")
            for item in upcoming:
                with ui.row().classes("event-row w-full items-center no-wrap"):
                    ui.checkbox(value=item["completed"], on_change=lambda event, event_id=item["id"]:
                                schedule.set_completed(user_id, event_id, event.value))
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(item["title"]).classes("text-sm font-black")
                        time_text = item["start_time"]
                        if item["end_time"]:
                            time_text += f"–{item['end_time']}"
                        ui.label(f"{item['date']}  {time_text}  {item['category']}").classes(
                            "text-[9px] text-grey-6")
                    ui.button(icon="delete_outline", on_click=lambda _, value=item: open_delete(value)).props(
                        "flat round dense color=negative")

        ui.add_css("""
        body{background:#F6F4EF}.schedule-dialog{width:min(92vw,440px)!important;border-radius:24px!important}.schedule-hero{border:0!important;border-radius:28px!important;background:radial-gradient(circle at 80% 15%,rgba(212,149,82,.48),transparent 34%),linear-gradient(145deg,#12283F,#244C69)!important;box-shadow:0 16px 38px rgba(18,40,63,.22)!important}.schedule-add{background:#F8F3E8!important;color:#17314B!important}.schedule-panel{border-radius:20px!important;background:#fff!important;border:1px solid #E6E2D9!important;box-shadow:none!important}.schedule-weekdays,.schedule-calendar{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}.schedule-weekdays{text-align:center;font-size:9px;font-weight:800;color:#7B817E;margin:12px 0 5px}.schedule-day{position:relative;min-height:58px;padding:6px;border-radius:11px;background:#F8F7F3;border:1px solid #EEEBE4;overflow:hidden;cursor:pointer}.schedule-day.empty{background:transparent;border:0}.schedule-today{border:2px solid #D49552;background:#FFF8EC}.day-number{font-size:10px;font-weight:900}.event-count{position:absolute;right:5px;top:5px;min-width:17px;height:17px;border-radius:999px;background:#315D77;color:#fff;text-align:center;font-size:8px;line-height:17px}.event-preview{font-size:7px;color:#53606A;margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.event-row{padding:10px 4px;border-bottom:1px solid #EEEAE2}
        @media(min-width:700px){.app-shell{width:min(100%,980px)!important}.schedule-calendar{gap:8px}.schedule-day{min-height:92px;padding:9px}.day-number{font-size:13px}.event-preview{font-size:10px}.schedule-weekdays{font-size:11px}}
        """)
