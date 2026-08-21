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
    content = Theme.shell("イベントスケジュール", "親睦会も店舗イベントも、みんなで共有",
                          back_to="/store-ops", action=store_header_actions,
                          brand="店舗運営")
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

        previous_month = 12 if month == 1 else month - 1
        previous_year = year - 1 if month == 1 else year
        next_month = 1 if month == 12 else month + 1
        next_year = year + 1 if month == 12 else year
        with ui.card().classes("calendar-hero w-full q-pa-lg"):
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
                            "click", lambda _, value=day: open_add(value)):
                        ui.label(str(day)).classes("day-number")
                        for event in day_events[:3]:
                            ui.element("div").classes(
                                f"event-dot {CATEGORY_CLASS.get(event['category'], 'other')}")

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

        ui.fab(icon="add", on_click=add_dialog.open).props(
            "color=primary direction=up").classes("event-fab")
        ui.add_css("""
        body{background:radial-gradient(circle at 90% 0,#E8E1F8,transparent 27%),linear-gradient(180deg,#F8F7FB,#F4F2ED)!important}.event-dialog{width:min(94vw,480px)!important;border-radius:25px!important}.calendar-hero{border:0!important;border-radius:29px!important;background:linear-gradient(145deg,#182A3B,#334B68 62%,#6B5B87)!important;color:white!important;box-shadow:0 20px 44px rgba(35,48,75,.25)!important}.event-calendar{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}.weekday{text-align:center;font-size:9px;font-weight:900;opacity:.55}.event-day{position:relative;min-height:55px;padding:7px;border-radius:14px;background:rgba(255,255,255,.10);cursor:pointer;transition:.18s}.event-day:hover{background:rgba(255,255,255,.18);transform:translateY(-2px)}.event-day.today{background:white;color:#203047;box-shadow:0 5px 15px rgba(11,23,40,.25)}.day-number{font-size:11px;font-weight:900}.event-dot{width:5px;height:5px;border-radius:50%;display:inline-block;margin:10px 2px 0 0}.event-dot.social{background:#FFBE63}.event-dot.store{background:#5CE0B3}.event-dot.meeting{background:#71B7FF}.event-dot.training{background:#CB9BFF}.event-dot.booking{background:#FF8297}.event-dot.other{background:#D4D8DD}.event-card{position:relative;overflow:hidden;border:0!important;border-radius:21px!important;box-shadow:0 10px 27px rgba(42,51,67,.08)!important}.event-card:before{content:'';position:absolute;left:0;top:0;bottom:0;width:5px}.event-card.social:before{background:#E6A445}.event-card.store:before{background:#41AF89}.event-card.meeting:before{background:#568DCD}.event-card.training:before{background:#9871BE}.event-card.booking:before{background:#D96579}.event-card.other:before{background:#8D969F}.event-category{font-size:9px;font-weight:900;color:#69757E}.event-details{padding:10px 12px;border-radius:12px;background:#F5F6F7;font-size:11px;line-height:1.6;white-space:pre-wrap}.empty-events{padding:24px;border:1px dashed #CBD1D5;border-radius:18px;text-align:center;font-size:11px;color:#899198}.event-fab{position:fixed!important;right:22px;bottom:28px;z-index:20}
        """)


@ui.page("/store-ops/events")
def events_current_page():
    today = today_jst()
    render_event_calendar(today.year, today.month)


@ui.page("/store-ops/events/{year}/{month}")
def events_month_page(year: int, month: int):
    render_event_calendar(year, month)
