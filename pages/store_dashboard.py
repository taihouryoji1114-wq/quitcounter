from nicegui import ui

from core.auth import require_app_access
from core.clock import operational_date_jst
from core.store_ops import store_ops
from core.theme import Theme
from pages.store_common import app_card, store_header_actions


@ui.page("/store-ops")
def store_dashboard_page():
    if not require_app_access("store_ops"):
        return
    Theme.page("店舗運営", app_name="store-ops")
    store_ops.move_kitchen_handovers_to_prep()
    business_date = operational_date_jst().isoformat()
    board = store_ops.previous_day_board(business_date)
    store_ops.ensure_daily_checklist(business_date)
    content = Theme.shell("店舗運営", "今日必要なことだけ、ひと目で",
                          action=store_header_actions, brand="店舗運営")
    with content:
        with ui.card().classes("store-board w-full q-pa-lg text-white"):
            with ui.row().classes("w-full items-start justify-between no-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label("前日から今日へ").classes("text-[10px] opacity-75")
                    ui.label("引き継ぎボード").classes("text-2xl font-black")
                ui.icon("assignment_late").classes("text-4xl opacity-70")
            board_items = board["items"]
            if not board_items:
                ui.label("引き継ぎはありません").classes("board-empty q-mt-md")
            for item in board_items:
                is_overdue = item["kind"] in {"prep", "request", "note", "order_missed"}
                with ui.row().classes(
                        "board-row overdue w-full items-center no-wrap" if is_overdue
                        else "board-row w-full items-center no-wrap"):
                    ui.label(item["area"]).classes("board-area")
                    ui.label(item["name"]).classes("text-xs font-black grow")
                    if item["kind"] in {"prep", "attention"}:
                        ui.button("完了", on_click=lambda _, item_id=item["id"]: (
                            store_ops.set_prep_status(business_date, item_id, "done"),
                            ui.navigate.to("/store-ops")
                        )).props("flat dense no-caps")
                    elif item["kind"] == "note":
                        ui.button("完了", on_click=lambda _, item_id=item["id"]: (
                            store_ops.confirm_handover(board["previous_date"], item_id),
                            ui.navigate.to("/store-ops")
                        )).props("flat dense no-caps")
                    elif item["kind"] == "request":
                        ui.button("完了", on_click=lambda _, item_id=item["id"]: (
                            store_ops.set_order_request_completed(item_id, True),
                            ui.navigate.to("/store-ops")
                        )).props("flat dense no-caps")
                    elif item["kind"] in {"order_missed", "order_attention"}:
                        destination = item["name"].replace("への発注未完了", "")
                        ui.button("完了", on_click=lambda _, name=destination: (
                            store_ops.set_daily_order_check(board["previous_date"], name, True),
                            ui.navigate.to("/store-ops")
                        )).props("flat dense no-caps")

        with ui.element("div").classes("store-app-grid w-full q-mt-md"):
            app_card("シフト提出", "半月ごとの勤務希望", "calendar_month",
                     "/store-ops/shift-submission", "text-blue-7")
            app_card("清掃", "清掃状況と担当確認", "cleaning_services",
                     "/store-ops/cleaning", "text-teal-7")
            app_card("マニュアル", "手順・考え方・行動指針", "menu_book",
                     "/store-ops/manual", "text-orange-8")
            app_card("イベントスケジュール", "店舗行事と予定を共有", "event",
                     "/store-ops/events", "text-purple-7")

        ui.add_css("""
        .store-board{border:0!important;border-radius:27px!important;background:linear-gradient(145deg,#173D30,#3D755D 65%,#C18A45 145%)!important;box-shadow:0 16px 38px rgba(26,65,48,.22)!important}.board-row{padding:9px 10px;border-radius:13px;background:rgba(255,255,255,.14);margin-top:6px}.board-row.overdue{background:rgba(198,61,61,.42);border:1px solid rgba(255,180,180,.35)}.board-area{min-width:48px;font-size:8px;font-weight:900}.board-row .q-btn{color:white!important}.board-empty{padding:14px;border-radius:13px;background:rgba(255,255,255,.12);text-align:center;font-size:11px;font-weight:800}.store-app-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.store-app-card{min-height:155px;border-radius:22px!important;border:1px solid #E1E9E4!important;box-shadow:0 8px 24px rgba(39,55,45,.05)!important}
        """)


def placeholder_page(title, subtitle, icon):
    if not require_app_access("store_ops"):
        return
    Theme.page(f"{title}｜店舗運営", app_name="store-ops")
    content = Theme.shell(title, subtitle, back_to="/store-ops", action=store_header_actions,
                          brand="店舗運営")
    with content:
        with ui.card().classes("surface-card w-full q-pa-xl text-center"):
            ui.icon(icon).classes("text-6xl text-primary")
            ui.label("このページを次に作り込みます").classes("text-base font-black q-mt-md")


@ui.page("/store-ops/cleaning")
def cleaning_page():
    placeholder_page("清掃", "毎日の清掃を漏れなく", "cleaning_services")


@ui.page("/store-ops/manual")
def manual_page():
    placeholder_page("マニュアル", "手順と考え方をひとつに", "menu_book")


@ui.page("/store-ops/events")
def events_page():
    placeholder_page("イベントスケジュール", "店舗の予定を共有", "event")
