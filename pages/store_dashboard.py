from nicegui import ui

from core.auth import require_app_access
from core.clock import operational_date_jst, store_service_period_jst
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
    period = store_service_period_jst()
    period_label = "ランチ" if period == "lunch" else "ディナー"
    store_ops.ensure_service_checklist(business_date, period)
    board = store_ops.service_handover_board(business_date, period)
    content = Theme.shell("店舗運営", "今日必要なことだけ、ひと目で",
                          action=store_header_actions, brand="店舗運営")
    with content:
        day = operational_date_jst()
        ui.label(f"{day.month}月{day.day}日　TODAY'S OPERATION").classes(
            "today-ribbon w-full")
        with ui.card().classes("store-board w-full q-pa-lg text-white"):
            with ui.row().classes("w-full items-start justify-between no-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label(f"{board['source_label']}から{period_label}へ").classes(
                        "text-[10px] opacity-80 tracking-wide")
                    ui.label("引き継ぎボード").classes("text-2xl font-black")
                ui.icon("assignment_late").classes("text-4xl opacity-70")
            board_items = board["items"]
            if not board_items:
                ui.label("引き継ぎはありません").classes("board-empty q-mt-md")
            groups = (
                ("チェック表のやり残し", "checklist",
                 {"prep"}),
                ("チェック結果", "fact_check", {"check_result"}),
                ("自由引き継ぎ", "campaign", {"note"}),
                ("発注依頼", "add_shopping_cart", {"request"}),
            )
            for group_label, group_icon, kinds in groups:
                group_items = [item for item in board_items if item["kind"] in kinds]
                if not group_items:
                    continue
                with ui.column().classes("board-group w-full gap-1 q-mt-md"):
                    with ui.row().classes("w-full items-center gap-2 q-mb-xs"):
                        ui.icon(group_icon).classes("text-base opacity-80")
                        ui.label(group_label).classes("text-[11px] font-black grow")
                        ui.label(str(len(group_items))).classes("board-count")
                    for item in group_items:
                        row_class = "board-row w-full items-center no-wrap"
                        with ui.row().classes(row_class):
                            ui.label(item["area"]).classes("board-area")
                            ui.label(item["name"]).classes("text-xs font-black grow")
                            if item["kind"] == "prep":
                                ui.button("完了", icon="check",
                                          on_click=lambda _, value=item: (
                                              store_ops.set_service_prep_quantity(
                                                  value["from_date"], value["from_period"],
                                                  value["id"], 2)
                                              if value.get("quantity_mode") else
                                              store_ops.set_service_prep_status(
                                                  value["from_date"], value["from_period"],
                                                  value["id"], "done"),
                                              ui.navigate.to("/store-ops")
                                          )).props("unelevated dense no-caps").classes(
                                              "board-complete")
                            elif item["kind"] == "check_result":
                                ui.label("記録").classes("board-result")
                            elif item["kind"] == "note":
                                ui.button("完了", icon="check",
                                          on_click=lambda _, value=item: (
                                              store_ops.confirm_handover(
                                                  value["from_date"], value["id"]),
                                              ui.navigate.to("/store-ops")
                                          )).props("unelevated dense no-caps").classes(
                                              "board-complete")
                            elif item["kind"] == "request":
                                ui.button("完了", icon="check",
                                          on_click=lambda _, item_id=item["id"]: (
                                              store_ops.set_order_request_completed(item_id, True),
                                              ui.navigate.to("/store-ops")
                                          )).props("unelevated dense no-caps").classes(
                                              "board-complete")

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
        body{background:linear-gradient(180deg,rgba(244,247,244,.68),rgba(239,238,232,.82)),url('/static/store_ops_home_bg_v3.png') center/cover fixed!important}.today-ribbon{color:#527060;font-size:9px;font-weight:900;letter-spacing:.14em;margin-bottom:9px;padding-left:4px}.store-board{position:relative;overflow:hidden;border:0!important;border-radius:29px!important;background:radial-gradient(circle at 95% 0%,rgba(234,190,102,.48),transparent 34%),linear-gradient(145deg,rgba(16,47,38,.96),rgba(40,96,71,.95) 62%,rgba(85,122,74,.95) 120%)!important;box-shadow:0 20px 46px rgba(20,66,49,.28)!important}.store-board:after{content:'';position:absolute;width:180px;height:180px;border:1px solid rgba(255,255,255,.09);border-radius:50%;right:-70px;top:-90px;pointer-events:none}.board-group{padding:10px;border-radius:17px;background:rgba(7,31,24,.16);border:1px solid rgba(255,255,255,.08)}.board-count{min-width:22px;height:22px;display:flex;align-items:center;justify-content:center;border-radius:999px;background:rgba(255,255,255,.17);font-size:9px;font-weight:900}.board-row{padding:9px 9px 9px 11px;border-radius:13px;background:rgba(255,255,255,.94);color:#20362D;margin-top:3px;box-shadow:0 4px 12px rgba(8,31,23,.12)}.board-row.attention{background:#FFF9EA;border:1px solid #EBD8A5}.board-area{min-width:48px;color:#6E8077;font-size:8px;font-weight:900}.board-result{font-size:9px;font-weight:900;color:#527060;background:#E7F0EB;padding:5px 8px;border-radius:999px}.board-complete{min-height:32px!important;border-radius:10px!important;background:#246A4E!important;color:white!important;font-size:10px!important;padding:0 10px!important;box-shadow:0 4px 10px rgba(36,106,78,.22)}.board-empty{padding:17px;border-radius:15px;background:rgba(255,255,255,.12);text-align:center;font-size:11px;font-weight:800}.store-app-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.store-app-card{position:relative;overflow:hidden;min-height:164px;border-radius:24px!important;border:1px solid rgba(255,255,255,.8)!important;box-shadow:0 13px 30px rgba(39,55,45,.10)!important;transition:transform .18s,box-shadow .18s!important;backdrop-filter:blur(9px)}.store-app-card:after{content:'›';position:absolute;right:14px;bottom:9px;font-size:29px;font-weight:300;color:rgba(31,54,44,.26)}.store-app-card:nth-child(1){background:linear-gradient(145deg,rgba(237,245,255,.95),rgba(255,255,255,.92))!important}.store-app-card:nth-child(2){background:linear-gradient(145deg,rgba(234,248,243,.95),rgba(255,255,255,.92))!important}.store-app-card:nth-child(3){background:linear-gradient(145deg,rgba(255,244,229,.95),rgba(255,255,255,.92))!important}.store-app-card:nth-child(4){background:linear-gradient(145deg,rgba(243,238,255,.95),rgba(255,255,255,.92))!important}.store-app-card:hover{transform:translateY(-3px);box-shadow:0 18px 36px rgba(39,55,45,.15)!important}
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
