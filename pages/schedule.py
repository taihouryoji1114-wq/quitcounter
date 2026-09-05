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
    schedule.roll_over_unfinished(user_id, today.isoformat())
    notification_settings = schedule.notification_settings(user_id)
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
        with ui.dialog() as notification_dialog, ui.card().classes("schedule-dialog q-pa-lg"):
            ui.label("毎日の予定通知").classes("text-xl font-black")
            ui.label("この端末へ、自分の当日予定だけを通知します").classes("text-xs text-grey-7")
            notification_enabled = ui.switch(
                "通知を受け取る", value=notification_settings["enabled"]).props(
                    "color=primary").classes("w-full q-mt-md")
            notification_time = ui.input(
                "通知時刻", value=notification_settings["time"]).props(
                    "outlined dense type=time").classes("w-full")

            async def save_notification():
                saved = schedule.save_notification_settings(
                    user_id, notification_enabled.value, notification_time.value)
                if saved["enabled"]:
                    permission = await ui.run_javascript(
                        "typeof Notification === 'undefined' ? 'unsupported' : "
                        "(Notification.permission === 'granted' ? 'granted' : Notification.requestPermission())",
                        timeout=10)
                    if permission != "granted":
                        schedule.save_notification_settings(user_id, False, saved["time"])
                        ui.notify("端末の通知を許可してください", type="warning")
                        return
                notification_dialog.close()
                reload("通知設定を保存しました")

            ui.button("設定を保存", icon="notifications_active",
                      on_click=save_notification).classes("w-full q-mt-md")
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
            requires_check = ui.switch("完了チェックが必要な予定", value=False).props(
                "color=positive").classes("w-full q-mt-xs")
            ui.label("未完了なら翌日に自動で引き継ぎます").classes(
                "text-[10px] text-grey-6 q-mt-n2")
            repeat_monthly = ui.switch("毎月同じ日に繰り返す", value=False).props(
                "color=primary").classes("w-full q-mt-xs")
            ui.label("31日がない月は、その月の月末日に表示します").classes(
                "text-[10px] text-grey-6 q-mt-n2")

            def add_event():
                try:
                    schedule.add_event(user_id, title.value, event_date.value, start_time.value,
                                       end_time.value, category.value, note.value,
                                       event_end_date.value, requires_check.value,
                                       repeat_monthly.value)
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

        selected_event = {"item": None}
        with ui.dialog() as detail_dialog, ui.card().classes("schedule-dialog q-pa-lg"):
            with ui.row().classes("w-full items-center justify-between no-wrap"):
                ui.label("予定の内容").classes("text-xl font-black grow")
                ui.button(icon="close", on_click=detail_dialog.close).props("flat round")
            detail_name = ui.input("予定名").props("outlined dense").classes("w-full q-mt-sm")
            detail_category = ui.label().classes("detail-category")
            detail_date = ui.label().classes("text-sm font-bold text-grey-8 q-mt-sm")
            detail_time = ui.label().classes("text-sm text-grey-7")
            detail_note = ui.textarea("メモ", placeholder="必要なことを自由に追加").props(
                "outlined autogrow").classes("w-full q-mt-sm")
            detail_requires_check = ui.switch("完了チェックが必要", value=False).props(
                "color=positive").classes("w-full q-mt-sm")
            ui.label("チェックしなければ翌日へ自動で引き継ぎます").classes(
                "text-[10px] text-grey-6 q-mt-n2")
            detail_repeat_monthly = ui.switch("毎月同じ日に繰り返す", value=False).props(
                "color=primary").classes("w-full q-mt-xs")

            def save_event_detail():
                item = selected_event["item"]
                if not item:
                    return
                try:
                    updated = schedule.update_event(
                        user_id, item["id"], detail_name.value, detail_note.value,
                        detail_requires_check.value, detail_repeat_monthly.value)
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                selected_event["item"] = updated
                detail_dialog.close()
                reload("予定を更新しました")

            ui.button("変更を保存", icon="save", on_click=save_event_detail).props(
                "unelevated no-caps").classes("w-full q-mt-md")
            ui.separator().classes("q-my-md")

            def delete_from_detail():
                item = selected_event["item"]
                if not item:
                    return
                detail_dialog.close()
                open_delete(item)

            ui.button("この予定を削除", icon="delete_outline", on_click=delete_from_detail).props(
                "outline color=negative no-caps").classes("w-full q-mt-sm")

        def open_detail(item):
            selected_event["item"] = item
            detail_name.set_value(item["title"])
            detail_category.set_text(item.get("category", "個人"))
            date_text = item["date"].replace("-", "/")
            if item.get("end_date", item["date"]) != item["date"]:
                date_text += f" ～ {item['end_date'].replace('-', '/')}"
            detail_date.set_text(date_text)
            time_text = item.get("start_time", "")
            if item.get("end_time"):
                time_text += f" ～ {item['end_time']}"
            detail_time.set_text(time_text or "時間指定なし")
            detail_note.set_value(item.get("note") or "")
            detail_requires_check.set_value(item.get("requires_check", False))
            detail_repeat_monthly.set_value(item.get("repeat_monthly", False))
            detail_dialog.open()

        selected_day = {"date": today.isoformat()}
        with ui.dialog() as day_dialog, ui.card().classes("schedule-dialog q-pa-lg"):
            with ui.row().classes("w-full items-center justify-between no-wrap"):
                day_dialog_title = ui.label().classes("text-xl font-black")
                ui.button(icon="close", on_click=day_dialog.close).props("flat round")
            day_event_list = ui.column().classes("day-event-scroll w-full gap-2 q-mt-sm")
            ui.button("この日に予定を追加", icon="add").props(
                "flat no-caps").classes("w-full q-mt-sm").on("click", lambda: (
                    day_dialog.close(), event_date.set_value(selected_day["date"]),
                    event_end_date.set_value(selected_day["date"]), add_dialog.open()))

        def open_day(day_date, items):
            selected_day["date"] = day_date
            parsed = datetime.strptime(day_date, "%Y-%m-%d")
            day_dialog_title.set_text(parsed.strftime("%m月%d日の予定"))
            day_event_list.clear()
            with day_event_list:
                if not items:
                    ui.label("この日の予定はありません").classes(
                        "w-full text-center text-sm text-grey-6 q-py-lg")
                for item in items:
                    with ui.row().classes(
                            "day-dialog-event w-full items-center no-wrap").on(
                                "click", lambda _, value=item: (
                                    day_dialog.close(), open_detail(value))):
                        ui.element("div").classes(
                            f"event-dot {CATEGORY_CLASS.get(item.get('category'), 'event-other')}")
                        with ui.column().classes("event-main gap-0 grow min-w-0"):
                            ui.label(item["title"]).classes("text-sm font-black ellipsis")
                            time_text = item.get("start_time") or "時間指定なし"
                            ui.label(f"{time_text}  ·  {item.get('category', '個人')}").classes(
                                "text-[10px] text-grey-6")
                            if item.get("note"):
                                ui.label(item["note"]).classes("schedule-card-note")
                            if item.get("carried_from"):
                                ui.label("前日からの持ち越し").classes(
                                    "text-[9px] text-warning font-bold q-mt-xs")
                            if item.get("repeat_monthly"):
                                ui.label("↻ 毎月繰り返し").classes(
                                    "text-[9px] text-primary font-bold q-mt-xs")
                        with ui.column().classes("schedule-event-actions gap-1 items-center"):
                            if item.get("requires_check", False):
                                ui.checkbox(
                                    value=item.get("completed", False),
                                    on_change=lambda event, event_id=item["id"]: schedule.set_completed(
                                        user_id, event_id, event.value),
                                ).props("dense keep-color color=positive aria-label='予定を完了'")
                            ui.icon("chevron_right").classes("text-grey-5")
            day_dialog.open()

        today_events = schedule.events(user_id, today.isoformat(), today.isoformat())
        remaining = [item for item in today_events
                     if not item.get("requires_check") or not item.get("completed")]
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
                        if next_item.get("note"):
                            ui.label(next_item["note"]).classes("schedule-hero-note")
                with ui.element("div").classes("schedule-today-count"):
                    ui.label(str(len(remaining))).classes("text-2xl font-black")
                    ui.label("残り").classes("text-[9px] opacity-70")
            ui.button("新しい予定", icon="add", on_click=add_dialog.open).props(
                "unelevated no-caps").classes("schedule-add w-full q-mt-lg")
            ui.button("毎朝の通知", icon="notifications", on_click=notification_dialog.open).props(
                "flat no-caps").classes("schedule-notification-button w-full q-mt-xs")

        if notification_settings["enabled"]:
            notification_titles = [item["title"] for item in today_events]
            ui.run_javascript(f"""
            (() => {{
              const notifyTime = {notification_settings['time']!r};
              const titles = {notification_titles!r};
              const check = () => {{
                const now = new Date();
                const today = [now.getFullYear(), String(now.getMonth()+1).padStart(2,'0'), String(now.getDate()).padStart(2,'0')].join('-');
                const current = String(now.getHours()).padStart(2,'0') + ':' + String(now.getMinutes()).padStart(2,'0');
                const key = 'schedule:notified:' + today;
                if (typeof Notification !== 'undefined' && current >= notifyTime && !localStorage.getItem(key) && Notification.permission === 'granted') {{
                  const body = titles.length ? `本日の予定は${{titles.length}}件です。${{titles.slice(0,3).join('、')}}` : '本日の予定はありません。';
                  new Notification('今日のスケジュール', {{body, icon:'/static/schedule_icon.svg'}});
                  localStorage.setItem(key, '1');
                }}
              }};
              check(); window.scheduleNotifyTimer && clearInterval(window.scheduleNotifyTimer);
              window.scheduleNotifyTimer = setInterval(check, 30000);
            }})();
            """)

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
                first = max(datetime.strptime(item["date"], "%Y-%m-%d").date(), month)
                last = min(datetime.strptime(item.get("end_date", item["date"]), "%Y-%m-%d").date(),
                           next_month - timedelta(days=1))
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
                                "click", lambda _, value=day_date, items=day_events: open_day(value, items)):
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
                                                f"calendar-event {CATEGORY_CLASS.get(item.get('category'), 'event-other')}{edge}"
                                                + (" event-task" if item.get("requires_check") else "")
                                                + (" event-done" if item.get("requires_check")
                                                   and item.get("completed") else ""))

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
                        with ui.column().classes("event-main gap-0 grow min-w-0"):
                            ui.label(item["title"]).classes("text-sm font-black ellipsis")
                            date_text = item["date"].replace("-", "/")
                            if item.get("end_date", item["date"]) != item["date"]:
                                date_text += f" – {item['end_date'].replace('-', '/')}"
                            time_text = item.get("start_time", "")
                            if item.get("end_time"):
                                time_text += f"–{item['end_time']}"
                            ui.label(f"{date_text}  {time_text}  {item.get('category', '個人')}").classes(
                                "text-[9px] text-grey-6")
                            if item.get("repeat_monthly"):
                                ui.label("↻ 毎月繰り返し").classes(
                                    "text-[9px] text-primary font-bold")
                            if item.get("note"):
                                ui.label(item["note"]).classes("schedule-card-note")
                        with ui.column().classes("schedule-event-actions gap-1 items-center"):
                            if item.get("requires_check", False):
                                ui.checkbox(value=item.get("completed", False),
                                            on_change=lambda event, event_id=item["id"]:
                                            schedule.set_completed(user_id, event_id, event.value)).props(
                                                "dense keep-color color=positive aria-label='予定を完了'")
                            ui.button(icon="chevron_right", on_click=lambda _, value=item: open_detail(value)).props(
                                "flat round dense color=grey-6")

            ui.run_javascript("""
            setTimeout(() => {
              const calendar = document.getElementById('schedule-calendar-swipe');
              if (!calendar || calendar.dataset.swipeReady) return;
              calendar.dataset.swipeReady = '1';
              let startX = 0;
              let locked = false;
              const moveMonth = id => {
                if (locked) return;
                locked = true;
                document.getElementById(id)?.click();
                setTimeout(() => locked = false, 650);
              };
              calendar.addEventListener('touchstart', e => startX = e.touches[0].clientX, {passive:true});
              calendar.addEventListener('touchend', e => {
                const distance = e.changedTouches[0].clientX - startX;
                if (Math.abs(distance) > 105)
                  moveMonth(distance < 0 ? 'next-month-btn' : 'previous-month-btn');
              }, {passive:true});
              calendar.addEventListener('wheel', e => {
                if (Math.abs(e.deltaX) < 85) return;
                e.preventDefault();
                moveMonth(e.deltaX > 0 ? 'next-month-btn' : 'previous-month-btn');
              }, {passive:false});
            }, 150);
            """)

        calendar_view()

        ui.add_css("""
        body{background:linear-gradient(180deg,#F1F4F8 0,#F8F6F1 42%,#F6F3ED 100%);color:#182532}.schedule-dialog{width:min(94vw,460px)!important;border-radius:26px!important}.schedule-hero{position:relative;overflow:hidden;border:0!important;border-radius:30px!important;background:radial-gradient(circle at 90% 0,rgba(94,199,213,.48),transparent 37%),radial-gradient(circle at 8% 100%,rgba(93,115,187,.35),transparent 44%),linear-gradient(140deg,#102B48,#1D5680)!important;box-shadow:0 18px 42px rgba(20,52,82,.25)!important}.schedule-hero:after{content:'';position:absolute;width:130px;height:130px;border:1px solid rgba(255,255,255,.16);border-radius:50%;right:-55px;bottom:-72px}.schedule-hero-note{max-width:100%;margin-top:8px;padding:8px 10px;border-radius:11px;background:rgba(255,255,255,.12);font-size:10px;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere}.schedule-today-count{display:flex;flex-direction:column;align-items:center;justify-content:center;width:62px;height:62px;border-radius:20px;background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.19);backdrop-filter:blur(8px)}.schedule-add{background:#fff!important;color:#173A59!important;box-shadow:0 6px 16px rgba(4,24,43,.18)!important}.schedule-panel{border-radius:24px!important;background:rgba(255,255,255,.94)!important;border:1px solid rgba(220,225,228,.9)!important;box-shadow:0 10px 30px rgba(38,55,72,.07)!important}.calendar-panel{overflow:hidden}.schedule-weekdays,.schedule-calendar{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:4px}.schedule-weekdays{text-align:center;font-size:9px;font-weight:800;color:#89939C;margin:12px 0 5px}.schedule-day{position:relative;min-height:68px;padding:5px 3px;border-radius:12px;background:#F8F9FA;border:1px solid #EDF0F2;overflow:hidden;cursor:pointer;transition:.18s}.schedule-day:active{transform:scale(.96)}.schedule-day.empty{background:transparent;border:0}.schedule-today{border:2px solid #E48A70;background:#FFF8F4;box-shadow:0 4px 12px rgba(228,138,112,.12)}.schedule-today .day-number{display:inline-flex;align-items:center;justify-content:center;width:21px;height:21px;color:#fff;background:#E06F55;border-radius:50%}.day-number{font-size:10px;font-weight:900;margin-left:2px}.day-events{margin-top:4px;width:100%}.calendar-event{width:100%;height:12px;padding:1px 3px;font-size:6px;font-weight:800;line-height:10px;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-radius:2px;margin:0!important}.event-work{background:#3979B8!important}.event-private{background:#E47F68!important}.event-family{background:#8A6CC0!important}.event-health{background:#4E9B7B!important}.event-travel{background:#D99A3D!important}.event-other{background:#7D8993!important}.calendar-event.event-start{border-radius:7px 2px 2px 7px}.calendar-event.event-end{border-radius:2px 7px 7px 2px}.calendar-event.event-start.event-end{border-radius:7px}.category-legend{gap:14px;font-size:9px;font-weight:800;color:#737E87}.category-legend label:before{content:'';display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}.legend-work:before{background:#3979B8}.legend-private:before{background:#E47F68}.event-row{padding:12px 8px;border-bottom:1px solid #EEF0F2;align-items:flex-start!important}.event-dot{width:5px;min-height:38px;align-self:stretch;border-radius:9px;flex:none}.day-dialog-event{padding:12px;border:1px solid #E9EDF0;border-radius:16px;background:#FAFBFC;cursor:pointer;align-items:flex-start!important}.day-dialog-event:active{transform:scale(.98)}.schedule-card-note{width:100%;margin-top:6px;padding:7px 9px;border-radius:10px;background:#F1F4F6;color:#55636E;font-size:10px;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere}.detail-category{align-self:flex-start;padding:4px 10px;border-radius:999px;background:#EEF3F7;color:#536675;font-size:10px;font-weight:800}.detail-note{min-height:48px;padding:12px;border-radius:14px;background:#F6F7F8;white-space:pre-wrap}.month-events .q-item{border-radius:24px;padding:14px 16px;font-weight:800}.month-events .q-expansion-item__content{padding:0 8px 10px}
        .calendar-event.event-task{box-shadow:inset 3px 0 0 rgba(255,255,255,.9)}.calendar-event.event-done{opacity:.5;text-decoration:line-through}.day-event-scroll{max-height:58vh!important;overflow-y:auto!important;overscroll-behavior:contain;padding-right:3px}.day-dialog-event{display:grid!important;grid-template-columns:5px minmax(0,1fr) 44px!important;column-gap:10px!important;align-items:start!important}.event-main{width:100%!important;min-width:0!important;overflow:hidden!important}.event-main .ellipsis{max-width:100%!important}.schedule-event-actions{width:44px!important;min-width:44px!important;position:relative!important;z-index:3!important;background:#FAFBFC}.schedule-event-actions .q-checkbox{width:38px!important;height:38px!important;margin:0!important}.event-row{display:grid!important;grid-template-columns:5px minmax(0,1fr) 44px!important;column-gap:10px!important;align-items:start!important}.event-row .q-btn{width:38px!important;height:32px!important}.month-events .q-expansion-item__content{max-height:62vh;overflow-y:auto;overscroll-behavior:contain}.schedule-card-note{position:relative!important;z-index:0!important;max-height:130px;overflow-y:auto!important}
        @media(min-width:700px){.app-shell{width:min(100%,980px)!important}.schedule-calendar{gap:8px}.schedule-day{min-height:105px;padding:8px 6px}.day-number{font-size:13px}.calendar-event{height:17px;padding:2px 6px;font-size:9px;line-height:13px}.schedule-weekdays{font-size:11px}}
        """)
