import calendar
from datetime import datetime, timedelta

from nicegui import ui

from core.auth import current_role, log_out, require_app_access, selected_user_id
from core.clock import today_jst
from core.schedule import schedule
from core.theme import Theme


CATEGORY_CLASS = {
    "仕事": "event-work", "個人": "event-private", "家族": "event-family",
    "健康": "event-health", "移動": "event-travel", "その他": "event-other",
}


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
        with ui.row().classes("gap-0"):
            if current_role() == "owner":
                ui.button(icon="apps", on_click=lambda: ui.navigate.to("/")).props(
                    "flat round aria-label='R-BASEへ戻る'").classes("text-grey-8")
            ui.button(icon="logout", on_click=lambda: log_out("/schedule/login")).props(
                "flat round").classes("text-grey-8")

    content = Theme.shell("My Schedule", "仕事も暮らしも、ひとつの流れに",
                          action=logout_action, brand="My Schedule")
    with content:
        with ui.dialog() as add_dialog, ui.card().classes("schedule-dialog q-pa-lg"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("予定を追加").classes("text-xl font-black")
                ui.button(icon="close", on_click=add_dialog.close).props("flat round")
            title = ui.input("予定").props("outlined dense autofocus").classes("w-full")
            with ui.row().classes("w-full gap-2 no-wrap"):
                event_date = ui.input("開始日", value=today.isoformat()).props(
                    "outlined dense type=date").classes("grow")
                event_end_date = ui.input("終了日", value=today.isoformat()).props(
                    "outlined dense type=date").classes("grow")
            ui.label("旅行などは終了日まで入れると、期間でつながります").classes(
                "text-[10px] text-grey-6 q-mt-n2")
            with ui.row().classes("w-full gap-2 no-wrap"):
                start_time = ui.input("開始", value="").props("outlined dense type=time").classes("grow")
                end_time = ui.input("終了", value="").props("outlined dense type=time").classes("grow")
            category = ui.select(["仕事", "個人", "家族", "健康", "移動", "その他"],
                                 value="個人", label="分類").props("outlined dense").classes("w-full")
            note = ui.textarea("メモ（任意）").props("outlined autogrow").classes("w-full")

            def add_event():
                try:
                    schedule.add_event(user_id, title.value, event_date.value, start_time.value,
                                       end_time.value, category.value, note.value,
                                       event_end_date.value)
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

        today_events = schedule.events(user_id, today.isoformat(), today.isoformat())
        remaining = [item for item in today_events if not item.get("completed")]
        next_item = remaining[0] if remaining else None
        with ui.card().classes("schedule-hero w-full q-pa-lg text-white"):
            with ui.row().classes("w-full justify-between items-start no-wrap"):
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label(today.strftime("%m月%d日 %a")).classes("text-xs opacity-70")
                    ui.label("次の予定" if next_item else "今日はゆっくり").classes(
                        "text-sm opacity-80 q-mt-sm")
                    ui.label(next_item["title"] if next_item else "予定はありません").classes(
                        "text-2xl font-black ellipsis")
                    if next_item:
                        time_text = next_item.get("start_time") or "時間指定なし"
                        ui.label(f"{time_text}  ·  {next_item.get('category', '個人')}").classes(
                            "text-xs opacity-80 q-mt-xs")
                with ui.element("div").classes("schedule-today-count"):
                    ui.label(str(len(remaining))).classes("text-2xl font-black")
                    ui.label("残り").classes("text-[9px] opacity-70")
            ui.button("新しい予定", icon="add", on_click=add_dialog.open).props(
                "unelevated no-caps").classes("schedule-add w-full q-mt-lg")

        @ui.refreshable
        def calendar_view():
            month = viewed_month[0]
            if month.month == 12:
                next_month = month.replace(year=month.year + 1, month=1)
            else:
                next_month = month.replace(month=month.month + 1)
            start, end = month.isoformat(), (next_month - timedelta(days=1)).isoformat()
            month_events = schedule.events(user_id, start, end)
            by_date = {}
            for item in month_events:
                first = max(datetime.strptime(item["date"], "%Y-%m-%d").date(), month.date())
                last = min(datetime.strptime(item.get("end_date", item["date"]), "%Y-%m-%d").date(),
                           (next_month - timedelta(days=1)).date())
                current = first
                while current <= last:
                    by_date.setdefault(current.isoformat(), []).append(item)
                    current += timedelta(days=1)

            def move(amount):
                current = viewed_month[0]
                total = current.year * 12 + current.month - 1 + amount
                viewed_month[0] = current.replace(year=total // 12, month=total % 12 + 1)
                calendar_view.refresh()

            with ui.card().classes("schedule-panel calendar-panel w-full q-pa-md q-mt-sm"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.button(icon="chevron_left", on_click=lambda: move(-1)).props(
                        "flat round id=previous-month-btn")
                    with ui.column().classes("gap-0 items-center"):
                        ui.label(month.strftime("%Y年")).classes("text-[9px] text-grey-5 font-bold")
                        ui.label(month.strftime("%m月")).classes("text-xl font-black")
                    ui.button(icon="chevron_right", on_click=lambda: move(1)).props(
                        "flat round id=next-month-btn")
                with ui.element("div").classes("schedule-weekdays w-full"):
                    for label in ("月", "火", "水", "木", "金", "土", "日"):
                        ui.label(label)
                with ui.element("div").props("id=schedule-calendar-swipe").classes(
                    "schedule-calendar w-full"):
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
                                "click", lambda _, value=day_date: (
                                    event_date.set_value(value), event_end_date.set_value(value), add_dialog.open())):
                                ui.label(str(day)).classes("day-number")
                                if day_events:
                                    with ui.column().classes("day-events gap-1"):
                                        for item in day_events[:3]:
                                            edge = ""
                                            if day_date == item["date"]:
                                                edge += " event-start"
                                            if day_date == item.get("end_date", item["date"]):
                                                edge += " event-end"
                                            ui.label(item["title"]).classes(
                                                f"calendar-event {CATEGORY_CLASS.get(item.get('category'), 'event-other')}{edge}")

                with ui.row().classes("category-legend w-full justify-center q-mt-sm"):
                    ui.label("仕事").classes("legend-work")
                    ui.label("プライベート").classes("legend-private")

            with ui.expansion(f"{month.month}月の予定　{len(month_events)}件", icon="calendar_month",
                              value=False).classes("schedule-panel month-events w-full q-mt-sm"):
                if not month_events:
                    ui.label("この月の予定はまだありません").classes("text-sm text-grey-6 q-pa-md")
                for item in month_events:
                    with ui.row().classes("event-row w-full items-center no-wrap"):
                        ui.element("div").classes(
                            f"event-dot {CATEGORY_CLASS.get(item.get('category'), 'event-other')}")
                        ui.checkbox(value=item.get("completed", False), on_change=lambda event, event_id=item["id"]:
                                    schedule.set_completed(user_id, event_id, event.value))
                        with ui.column().classes("gap-0 grow min-w-0"):
                            ui.label(item["title"]).classes("text-sm font-black ellipsis")
                            date_text = item["date"].replace("-", "/")
                            if item.get("end_date", item["date"]) != item["date"]:
                                date_text += f" – {item['end_date'].replace('-', '/')}"
                            time_text = item.get("start_time", "")
                            if item.get("end_time"):
                                time_text += f"–{item['end_time']}"
                            ui.label(f"{date_text}  {time_text}  {item.get('category', '個人')}").classes(
                                "text-[9px] text-grey-6")
                        ui.button(icon="delete_outline", on_click=lambda _, value=item: open_delete(value)).props(
                            "flat round dense color=negative")

            ui.run_javascript("""
            setTimeout(() => {
              const calendar = document.getElementById('schedule-calendar-swipe');
              if (!calendar || calendar.dataset.swipeReady) return;
              calendar.dataset.swipeReady = '1';
              let startX = 0;
              calendar.addEventListener('touchstart', e => startX = e.touches[0].clientX, {passive:true});
              calendar.addEventListener('touchend', e => {
                const distance = e.changedTouches[0].clientX - startX;
                if (Math.abs(distance) > 55)
                  document.getElementById(distance < 0 ? 'next-month-btn' : 'previous-month-btn')?.click();
              }, {passive:true});
              calendar.addEventListener('wheel', e => {
                if (Math.abs(e.deltaX) < 25) return;
                e.preventDefault();
                document.getElementById(e.deltaX > 0 ? 'next-month-btn' : 'previous-month-btn')?.click();
              }, {passive:false});
            }, 150);
            """)

        calendar_view()

        ui.add_css("""
        body{background:linear-gradient(180deg,#F1F4F8 0,#F8F6F1 42%,#F6F3ED 100%);color:#182532}.schedule-dialog{width:min(94vw,460px)!important;border-radius:26px!important}.schedule-hero{position:relative;overflow:hidden;border:0!important;border-radius:30px!important;background:radial-gradient(circle at 90% 0,rgba(94,199,213,.48),transparent 37%),radial-gradient(circle at 8% 100%,rgba(93,115,187,.35),transparent 44%),linear-gradient(140deg,#102B48,#1D5680)!important;box-shadow:0 18px 42px rgba(20,52,82,.25)!important}.schedule-hero:after{content:'';position:absolute;width:130px;height:130px;border:1px solid rgba(255,255,255,.16);border-radius:50%;right:-55px;bottom:-72px}.schedule-today-count{display:flex;flex-direction:column;align-items:center;justify-content:center;width:62px;height:62px;border-radius:20px;background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.19);backdrop-filter:blur(8px)}.schedule-add{background:#fff!important;color:#173A59!important;box-shadow:0 6px 16px rgba(4,24,43,.18)!important}.schedule-panel{border-radius:24px!important;background:rgba(255,255,255,.94)!important;border:1px solid rgba(220,225,228,.9)!important;box-shadow:0 10px 30px rgba(38,55,72,.07)!important}.calendar-panel{overflow:hidden}.schedule-weekdays,.schedule-calendar{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:4px}.schedule-weekdays{text-align:center;font-size:9px;font-weight:800;color:#89939C;margin:12px 0 5px}.schedule-day{position:relative;min-height:68px;padding:5px 3px;border-radius:12px;background:#F8F9FA;border:1px solid #EDF0F2;overflow:hidden;cursor:pointer;transition:.18s}.schedule-day:active{transform:scale(.96)}.schedule-day.empty{background:transparent;border:0}.schedule-today{border:2px solid #E48A70;background:#FFF8F4;box-shadow:0 4px 12px rgba(228,138,112,.12)}.schedule-today .day-number{display:inline-flex;align-items:center;justify-content:center;width:21px;height:21px;color:#fff;background:#E06F55;border-radius:50%}.day-number{font-size:10px;font-weight:900;margin-left:2px}.day-events{margin-top:4px;width:100%}.calendar-event{width:100%;height:12px;padding:1px 3px;font-size:6px;font-weight:800;line-height:10px;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-radius:2px;margin:0!important}.event-work{background:#3979B8!important}.event-private{background:#E47F68!important}.event-family{background:#8A6CC0!important}.event-health{background:#4E9B7B!important}.event-travel{background:#D99A3D!important}.event-other{background:#7D8993!important}.calendar-event.event-start{border-radius:7px 2px 2px 7px}.calendar-event.event-end{border-radius:2px 7px 7px 2px}.calendar-event.event-start.event-end{border-radius:7px}.category-legend{gap:14px;font-size:9px;font-weight:800;color:#737E87}.category-legend label:before{content:'';display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}.legend-work:before{background:#3979B8}.legend-private:before{background:#E47F68}.event-row{padding:10px 8px;border-bottom:1px solid #EEF0F2}.event-dot{width:5px;height:38px;border-radius:9px;flex:none}.month-events .q-item{border-radius:24px;padding:14px 16px;font-weight:800}.month-events .q-expansion-item__content{padding:0 8px 10px}
        @media(min-width:700px){.app-shell{width:min(100%,980px)!important}.schedule-calendar{gap:8px}.schedule-day{min-height:105px;padding:8px 6px}.day-number{font-size:13px}.calendar-event{height:17px;padding:2px 6px;font-size:9px;line-height:13px}.schedule-weekdays{font-size:11px}}
        """)
