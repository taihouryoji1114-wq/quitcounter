import calendar
from datetime import date

from nicegui import ui

from core.auth import current_role, require_app_access
from core.clock import today_jst
from core.store_events import store_events
from core.theme import Theme
from pages.store_common import store_header_actions


CATEGORY_CLASS = {"親睦": "social", "店舗イベント": "store", "会議": "meeting",
                  "研修": "training", "予約・貸切": "booking", "その他": "other"}


def render_event_calendar(year, month):
    if not require_app_access("store_ops"):
        return
    year, month = int(year), int(month)
    if month < 1 or month > 12:
        ui.navigate.to("/store-ops/events")
        return
    Theme.page("イベントスケジュール｜店舗運営", app_name="store-ops")
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    events = store_events.events(first.isoformat(), last.isoformat())
    with ui.column().classes("event-page-shell gap-0"):
        with ui.row().classes("event-topbar w-full items-center justify-between no-wrap"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/store-ops")).props(
                "flat round aria-label='1つ前へ戻る'").classes("text-grey-8")
            store_header_actions()
        content = ui.column().classes("w-full gap-0")
    with content:
        with ui.dialog() as add_dialog, ui.card().classes("event-dialog q-pa-lg"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("イベントを追加").classes("text-xl font-black")
                ui.button(icon="close", on_click=add_dialog.close).props("flat round")
            title = ui.input("イベント名").props("outlined dense autofocus").classes("w-full")
            with ui.row().classes("w-full gap-2 no-wrap"):
                start_date = ui.input("開始日", value=first.isoformat()).props(
                    "outlined dense type=date").classes("grow")
                end_date = ui.input("終了日", value=first.isoformat()).props(
                    "outlined dense type=date").classes("grow")
            with ui.row().classes("w-full gap-2 no-wrap"):
                start_time = ui.input("開始時間").props("outlined dense type=time").classes("grow")
                end_time = ui.input("終了時間").props("outlined dense type=time").classes("grow")
            category = ui.select(list(store_events.CATEGORIES), value="店舗イベント",
                                 label="分類").props("outlined dense").classes("w-full")
            details = ui.textarea("詳細・持ち物・集合場所など").props(
                "outlined autogrow").classes("w-full")

            def save_event():
                try:
                    store_events.add(title.value, start_date.value, end_date.value,
                                     start_time.value, end_time.value, category.value, details.value)
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                add_dialog.close()
                ui.navigate.to(f"/store-ops/events/{year}/{month}")

            ui.button("予定を追加", icon="add", on_click=save_event).classes("w-full q-mt-sm")

        def open_add(day):
            selected = date(year, month, day).isoformat()
            start_date.value = selected
            end_date.value = selected
            add_dialog.open()

        def open_day(day):
            selected = date(year, month, day).isoformat()
            selected_events = [event for event in events
                               if event["date"] <= selected <= event["end_date"]]
            with ui.dialog() as day_dialog, ui.card().classes("event-dialog q-pa-lg"):
                with ui.row().classes("w-full items-center justify-between no-wrap"):
                    with ui.column().classes("gap-0"):
                        ui.label(f"{month}月{day}日").classes("text-2xl font-black")
                        ui.label(f"予定 {len(selected_events)}件").classes(
                            "text-[10px] text-grey-6")
                    ui.button(icon="close", on_click=day_dialog.close).props("flat round")
                if not selected_events:
                    ui.label("この日の予定はまだありません").classes("day-events-empty w-full")
                for event in selected_events:
                    css_class = CATEGORY_CLASS.get(event["category"], "other")
                    with ui.card().classes(f"day-event-card {css_class} w-full q-pa-md"):
                        with ui.row().classes("w-full items-start no-wrap"):
                            with ui.column().classes("gap-0 grow min-w-0"):
                                ui.label(event["category"]).classes("event-category")
                                ui.label(event["title"]).classes("text-sm font-black")
                                if event.get("start_time"):
                                    time_text = event["start_time"]
                                    if event.get("end_time"):
                                        time_text += f"〜{event['end_time']}"
                                    ui.label(time_text).classes("text-[10px] text-grey-6 q-mt-xs")
                                if event.get("details"):
                                    ui.label(event["details"]).classes("event-details q-mt-sm")
                            if current_role() == "owner":
                                ui.button(icon="delete_outline",
                                          on_click=lambda _, event_id=event["id"]: (
                                              store_events.delete(event_id),
                                              day_dialog.close(),
                                              ui.navigate.to(f"/store-ops/events/{year}/{month}")
                                          )).props("flat round dense color=grey-5")
                ui.button("この日に新しい予定を追加", icon="add", on_click=lambda: (
                    day_dialog.close(), open_add(day))).classes("w-full q-mt-sm")
            day_dialog.open()

        previous_month = 12 if month == 1 else month - 1
        previous_year = year - 1 if month == 1 else year
        next_month = 1 if month == 12 else month + 1
        next_year = year + 1 if month == 12 else year
        with ui.card().classes("calendar-hero w-full q-pa-lg").props(
                "id=event-calendar-swipe"):
            with ui.row().classes("w-full items-center justify-between no-wrap"):
                ui.button(icon="chevron_left", on_click=lambda: ui.navigate.to(
                    f"/store-ops/events/{previous_year}/{previous_month}")).props("flat round")
                with ui.column().classes("gap-0 items-center"):
                    ui.label(str(year)).classes("text-[9px] tracking-widest opacity-60")
                    ui.label(f"{month}月").classes("text-3xl font-black")
                ui.button(icon="chevron_right", on_click=lambda: ui.navigate.to(
                    f"/store-ops/events/{next_year}/{next_month}")).props("flat round")
            with ui.element("div").classes("event-calendar w-full q-mt-md"):
                for weekday in "月火水木金土日":
                    ui.label(weekday).classes("weekday")
                for _ in range(first.weekday()):
                    ui.element("div").classes("calendar-blank")
                today = today_jst()
                for day in range(1, last.day + 1):
                    selected_date = date(year, month, day).isoformat()
                    day_events = [event for event in events
                                  if event["date"] <= selected_date <= event["end_date"]]
                    classes = "event-day today" if date(year, month, day) == today else "event-day"
                    with ui.element("div").classes(classes).on(
                            "click", lambda _, value=day: open_day(value)):
                        ui.label(str(day)).classes("day-number")
                        for event in day_events[:3]:
                            event_starts = selected_date == event["date"] or day == 1 or date(
                                year, month, day).weekday() == 0
                            event_ends = selected_date == event["end_date"] or day == last.day or date(
                                year, month, day).weekday() == 6
                            segment = " segment-start" if event_starts else " segment-middle"
                            if event_ends:
                                segment += " segment-end"
                            with ui.element("div").classes(
                                    f"event-span {CATEGORY_CLASS.get(event['category'], 'other')}{segment}"):
                                if event_starts:
                                    ui.label(event["title"]).classes("event-span-label")

        ui.label("今月の予定").classes("text-lg font-black q-mt-xl q-mb-sm")
        if not events:
            ui.label("予定はまだありません。日付をタップして追加できます").classes(
                "empty-events w-full")
        for event in events:
            css_class = CATEGORY_CLASS.get(event["category"], "other")
            with ui.card().classes(f"event-card {css_class} w-full q-pa-lg q-mb-sm"):
                with ui.row().classes("w-full items-start no-wrap"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(event["category"]).classes("event-category")
                        ui.label(event["title"]).classes("text-base font-black q-mt-xs")
                        date_label = event["date"][5:].replace("-", "/")
                        if event["end_date"] != event["date"]:
                            date_label += f" 〜 {event['end_date'][5:].replace('-', '/')}"
                        time_label = ""
                        if event["start_time"]:
                            time_label = f"　{event['start_time']}"
                            if event["end_time"]:
                                time_label += f"〜{event['end_time']}"
                        ui.label(date_label + time_label).classes("text-[10px] text-grey-6 q-mt-xs")
                        if event["details"]:
                            ui.label(event["details"]).classes("event-details q-mt-sm")
                    if current_role() == "owner":
                        ui.button(icon="delete_outline", on_click=lambda _, event_id=event["id"]: (
                            store_events.delete(event_id),
                            ui.navigate.to(f"/store-ops/events/{year}/{month}")
                        )).props("flat round dense color=grey-5")

        ui.fab(icon="add", color="primary", direction="up").on(
            "click", add_dialog.open).classes("event-fab")
        ui.add_css("""
        body{background:radial-gradient(circle at 90% 0,#E8E1F8,transparent 27%),linear-gradient(180deg,#F8F7FB,#F4F2ED)!important}.event-page-shell{width:100%;max-width:1180px;margin:0 auto;padding:8px 10px 48px;box-sizing:border-box}.event-topbar{min-height:48px;margin-bottom:4px}.event-dialog{width:min(94vw,480px)!important;border-radius:25px!important}.day-events-empty{padding:20px;border:1px dashed #CBD1D5;border-radius:16px;text-align:center;font-size:11px;color:#899198}.day-event-card{position:relative;overflow:hidden;border:1px solid #E6E9EC!important;border-radius:17px!important;box-shadow:none!important}.day-event-card:before{content:'';position:absolute;left:0;top:0;bottom:0;width:5px}.day-event-card.social:before{background:#E6A445}.day-event-card.store:before{background:#41AF89}.day-event-card.meeting:before{background:#568DCD}.day-event-card.training:before{background:#9871BE}.day-event-card.booking:before{background:#D96579}.day-event-card.other:before{background:#8D969F}.calendar-hero{border:0!important;border-radius:24px!important;padding:18px!important;background:linear-gradient(145deg,#182A3B,#334B68 62%,#6B5B87)!important;color:white!important;box-shadow:0 20px 44px rgba(35,48,75,.25)!important;touch-action:pan-y}.event-calendar{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:7px}.weekday{text-align:center;font-size:10px;font-weight:900;opacity:.55}.event-day{position:relative;min-width:0;min-height:clamp(66px,9vh,96px);padding:8px;border-radius:14px;background:rgba(255,255,255,.10);cursor:pointer;transition:.18s}.event-day:hover{background:rgba(255,255,255,.18);transform:translateY(-2px)}.event-day.today{background:white;color:#203047;box-shadow:0 5px 15px rgba(11,23,40,.25)}.day-number{font-size:12px;font-weight:900}.event-span{height:15px;margin-top:4px;margin-left:-11.5px;margin-right:-11.5px;display:flex;align-items:center;min-width:0;color:#172536;box-shadow:0 2px 5px rgba(8,18,30,.13);position:relative;z-index:2}.event-span.segment-start{margin-left:0;border-radius:7px 0 0 7px;padding-left:5px}.event-span.segment-end{margin-right:0;border-radius:0 7px 7px 0}.event-span.segment-start.segment-end{border-radius:7px}.event-span.social{background:#FFBE63}.event-span.store{background:#5CE0B3}.event-span.meeting{background:#71B7FF}.event-span.training{background:#CB9BFF}.event-span.booking{background:#FF8297}.event-span.other{background:#D4D8DD}.event-span-label{font-size:7px;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1}.event-card{position:relative;overflow:hidden;border:0!important;border-radius:21px!important;box-shadow:0 10px 27px rgba(42,51,67,.08)!important}.event-card:before{content:'';position:absolute;left:0;top:0;bottom:0;width:5px}.event-card.social:before{background:#E6A445}.event-card.store:before{background:#41AF89}.event-card.meeting:before{background:#568DCD}.event-card.training:before{background:#9871BE}.event-card.booking:before{background:#D96579}.event-card.other:before{background:#8D969F}.event-category{font-size:9px;font-weight:900;color:#69757E}.event-details{padding:10px 12px;border-radius:12px;background:#F5F6F7;font-size:11px;line-height:1.6;white-space:pre-wrap}.empty-events{padding:24px;border:1px dashed #CBD1D5;border-radius:18px;text-align:center;font-size:11px;color:#899198}.event-fab{position:fixed!important;right:22px;bottom:28px;z-index:20}@media(min-width:700px){.event-page-shell{padding:14px 24px 64px}.calendar-hero{padding:26px!important}.event-calendar{gap:10px}.event-day{padding:12px;border-radius:18px}.day-number{font-size:14px}.event-span{height:19px;margin-left:-17px;margin-right:-17px}.event-span.segment-start{margin-left:0;padding-left:7px}.event-span.segment-end{margin-right:0}.event-span-label{font-size:9px}}
        """)
        ui.run_javascript(f"""
        (() => {{
          const calendar = document.querySelector('#event-calendar-swipe');
          if (!calendar || calendar.dataset.swipeReady) return;
          calendar.dataset.swipeReady = '1';
          let startX = 0, startY = 0, startedAt = 0, wheelX = 0, wheelTimer;
          const move = direction => {{
            window.location.href = direction === 'next'
              ? '/store-ops/events/{next_year}/{next_month}'
              : '/store-ops/events/{previous_year}/{previous_month}';
          }};
          calendar.addEventListener('touchstart', event => {{
            const touch = event.changedTouches[0];
            startX = touch.clientX; startY = touch.clientY; startedAt = Date.now();
          }}, {{passive: true}});
          calendar.addEventListener('touchend', event => {{
            const touch = event.changedTouches[0];
            const dx = touch.clientX - startX, dy = touch.clientY - startY;
            if (Date.now() - startedAt < 900 && Math.abs(dx) > 110 && Math.abs(dx) > Math.abs(dy) * 1.35)
              move(dx < 0 ? 'next' : 'previous');
          }}, {{passive: true}});
          calendar.addEventListener('wheel', event => {{
            if (Math.abs(event.deltaX) < Math.abs(event.deltaY) * 1.2) return;
            wheelX += event.deltaX;
            clearTimeout(wheelTimer);
            wheelTimer = setTimeout(() => wheelX = 0, 280);
            if (Math.abs(wheelX) > 220) {{
              const direction = wheelX > 0 ? 'next' : 'previous';
              wheelX = 0;
              move(direction);
            }}
          }}, {{passive: true}});
        }})();
        """)


@ui.page("/store-ops/events")
def events_current_page():
    today = today_jst()
    render_event_calendar(today.year, today.month)


@ui.page("/store-ops/events/{year}/{month}")
def events_month_page(year: int, month: int):
    render_event_calendar(year, month)
