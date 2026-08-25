from nicegui import app, ui

from core.auth import has_permission, require_app_access
from core.clock import operational_date_jst, store_service_period_jst
from core.store_ops import store_ops
from core.store_quiz import store_quiz
from core.theme import Theme
from pages.store_common import app_card, store_header_actions


@ui.page("/store-ops")
def store_dashboard_page():
    if not require_app_access("store_ops"):
        return
    Theme.page("店舗運営", app_name="store-ops")
    store_ops.move_kitchen_handovers_to_prep()
    business_date, period = store_ops.active_service_context(
        operational_date_jst().isoformat(), store_service_period_jst())
    period_label = "ランチ" if period == "lunch" else "ディナー"
    store_ops.ensure_service_checklist(business_date, period)
    board = store_ops.service_handover_board(business_date, period)
    can_manage = has_permission("store_manage")
    content = Theme.shell("店舗運営", "今日必要なことだけ、ひと目で",
                          action=store_header_actions, brand="店舗運営")
    with content:
        day = operational_date_jst()
        notices = store_quiz.notices()
        if notices:
            with ui.expansion(
                f"業務連絡　{len(notices)}件", icon="campaign", value=False,
            ).classes("business-notice w-full q-mb-sm"):
                for notice in notices:
                    with ui.card().classes("business-notice-card w-full q-pa-md q-mb-xs"):
                        ui.label(notice["title"]).classes("text-sm font-black")
                        if notice.get("details"):
                            ui.label(notice["details"]).classes(
                                "text-[10px] text-grey-7 whitespace-pre-wrap q-mt-xs")
        ui.label(f"{day.month}月{day.day}日　TODAY'S OPERATION").classes(
            "today-ribbon w-full")
        with ui.card().classes("store-board w-full q-pa-lg text-white"):
            with ui.row().classes("w-full items-start justify-between no-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label(f"{board['source_label']}から{period_label}へ").classes(
                        "text-[10px] opacity-80 tracking-wide")
                    ui.label("引き継ぎボード").classes("text-2xl font-black")
                ui.button("最新に更新", icon="refresh", on_click=lambda: ui.navigate.to(
                    "/store-ops")).props("unelevated no-caps aria-label='最新の状態に更新'").classes(
                        "board-refresh")
            board_items = board["items"]
            pending_items = [item for item in board_items if not item.get("completed", False)]
            done_items = [item for item in board_items if item.get("completed", False)]

            def board_group(item):
                if item["kind"] == "note":
                    return "note"
                if item["kind"] == "request":
                    return "request"
                return "prep"

            def keep_group_open(item):
                app.storage.user[f"store_board_{board_group(item)}_open"] = True

            long_press_target = {"item": None}
            with ui.dialog() as long_press_dialog, ui.card().classes(
                    "board-action-dialog q-pa-lg"):
                long_press_title = ui.label().classes("text-lg font-black")
                long_press_name = ui.label().classes("text-xs text-grey-7 q-mt-xs")

                def apply_long_press_action():
                    item = long_press_target["item"]
                    if not item:
                        return
                    if item["kind"] == "request":
                        store_ops.delete_order_request(item["id"])
                    elif item["kind"] in {"prep", "check_result"}:
                        store_ops.reset_service_prep_items(
                            item["from_date"], item["from_period"], [item["id"]])
                    elif item["kind"] == "note":
                        store_ops.reopen_handover(item["from_date"], item["id"])
                    keep_group_open(item)
                    long_press_dialog.close()
                    ui.navigate.to("/store-ops")

                with ui.row().classes("w-full gap-2 q-mt-md"):
                    ui.button("やめる", on_click=long_press_dialog.close).props(
                        "flat no-caps").classes("grow")
                    long_press_confirm = ui.button(
                        "実行する", on_click=apply_long_press_action).props(
                            "unelevated no-caps").classes("grow")

            def open_long_press(item):
                long_press_target["item"] = item
                deleting = item["kind"] == "request"
                long_press_title.set_text("発注依頼を削除しますか？" if deleting
                                          else "未完了へ戻しますか？")
                long_press_name.set_text(item["name"])
                long_press_confirm.set_text("削除する" if deleting else "未完了へ戻す")
                long_press_confirm.props(f"color={'negative' if deleting else 'warning'}")
                long_press_dialog.open()

            def complete_item(item):
                if item["kind"] == "request" and not has_permission("store_manage"):
                    ui.notify("発注依頼の完了は管理者のみ行えます", type="warning")
                    return
                if item["kind"] == "prep":
                    if item.get("quantity_mode"):
                        store_ops.set_service_prep_quantity(
                            item["from_date"], item["from_period"], item["id"], 2)
                    else:
                        store_ops.set_service_prep_status(
                            item["from_date"], item["from_period"], item["id"], "done")
                elif item["kind"] == "note":
                    store_ops.confirm_handover(item["from_date"], item["id"])
                elif item["kind"] == "request":
                    store_ops.set_order_request_completed(item["id"], True)
                keep_group_open(item)
                ui.navigate.to("/store-ops")

            def save_rice_choice(item, choice):
                store_ops.set_service_prep_choice(
                    item["from_date"], item["from_period"], item["id"], choice)
                keep_group_open(item)
                ui.navigate.to("/store-ops")

            with ui.row().classes("w-full items-center gap-2 q-mt-sm"):
                ui.label(f"未完了 {len(pending_items)}件").classes("board-summary pending")
                ui.label(f"完了済み {len(done_items)}件").classes("board-summary done")
                if done_items:
                    def reopen_all_done():
                        store_ops.reopen_handover_board_items(done_items)
                        ui.notify("チェック済みを未完了へ戻しました", type="positive")
                        ui.navigate.to("/store-ops")

                    ui.button("一括で左へ戻す", icon="undo", on_click=reopen_all_done).props(
                        "flat dense no-caps").classes("board-reopen-all")
            def render_board_group(title, icon, group_name):
                group_pending = [item for item in pending_items
                                 if board_group(item) == group_name]
                group_done = [item for item in done_items
                              if board_group(item) == group_name]
                state_key = f"store_board_{group_name}_open"

                def remember_group_state(event):
                    app.storage.user[state_key] = bool(event.value)

                expansion_title = f"{title}　未完了 {len(group_pending)}"
                with ui.expansion(
                    expansion_title, icon=icon,
                    value=bool(app.storage.user.get(state_key, False)),
                    on_value_change=remember_group_state,
                ).classes("board-expansion w-full q-mt-sm"):
                    with ui.element("div").classes("board-lanes w-full"):
                        render_board_lane(group_pending, False)
                        render_board_lane(group_done, True)

            def render_board_lane(items, completed):
                lane_classes = "board-lane board-lane-done gap-1" if completed else "board-lane gap-1"
                with ui.column().classes(lane_classes):
                    ui.label("チェック済み" if completed else "未完了").classes(
                        "board-lane-title")
                    if not items:
                        ui.label("まだありません" if completed else "ありません").classes(
                            "board-lane-empty")
                    for item in items:
                        if completed:
                            row = ui.card().classes(
                                "board-row board-row-done board-longpress w-full q-pa-sm").on(
                                    "contextmenu", lambda _, value=item: open_long_press(value))
                            with row:
                                ui.icon("check_circle").classes("text-positive text-sm")
                                ui.label(item["name"]).classes("board-name grow")
                            continue
                        row = ui.card().classes("board-row w-full q-pa-sm")
                        if item["kind"] == "request":
                            row.classes("board-longpress").on(
                                "contextmenu", lambda _, value=item: open_long_press(value))
                        with row:
                            ui.label(item["area"]).classes("board-area")
                            ui.label(item["name"]).classes("board-name")
                            if item.get("choice_mode"):
                                with ui.row().classes("board-choice-row w-full gap-1 q-mt-xs"):
                                    ui.button("あり", on_click=lambda _, value=item:
                                              save_rice_choice(value, "あり")).props(
                                                  "unelevated dense no-caps color=positive").classes("grow")
                                    ui.button("なし", on_click=lambda _, value=item:
                                              save_rice_choice(value, "なし")).props(
                                                  "outline dense no-caps color=primary").classes("grow")
                            elif item["kind"] == "request" and not can_manage:
                                ui.label("管理者対応").classes("board-manager-only")
                            elif item["kind"] != "check_result":
                                ui.button(icon="check", on_click=lambda _, value=item:
                                          complete_item(value)).props(
                                              "unelevated round dense aria-label='完了'").classes(
                                                  "board-check")

            render_board_group("厨房の仕込み引き継ぎ", "restaurant", "prep")
            render_board_group("自由引き継ぎ", "edit_note", "note")
            render_board_group("発注引き継ぎ", "shopping_cart", "request")

        with ui.element("div").classes("store-app-grid w-full q-mt-md"):
            app_card("シフト提出", "半月ごとの勤務希望", "calendar_month",
                     "/store-ops/shift-submission", "text-blue-7")
            app_card("清掃", "清掃状況と担当確認", "cleaning_services",
                     "/store-ops/cleaning", "text-teal-7")
            app_card("マニュアル", "手順・考え方・行動指針", "menu_book",
                     "/store-ops/manual", "text-orange-8")
            app_card("イベントスケジュール", "店舗行事と予定を共有", "event",
                     "/store-ops/events", "text-purple-7")
            app_card("ちゃんはや", "ちゃんこで早押しクイズ", "quiz",
                     "/store-ops/chanhaya", "text-red-7")

        ui.add_css("""
        body{background:linear-gradient(180deg,rgba(244,247,244,.68),rgba(239,238,232,.82)),url('/static/store_ops_home_bg_v3.png') center/cover fixed!important}.today-ribbon{color:#527060;font-size:9px;font-weight:900;letter-spacing:.14em;margin-bottom:9px;padding-left:4px}.store-board{position:relative;overflow:hidden;border:0!important;border-radius:29px!important;background:radial-gradient(circle at 95% 0%,rgba(234,190,102,.48),transparent 34%),linear-gradient(145deg,rgba(16,47,38,.96),rgba(40,96,71,.95) 62%,rgba(85,122,74,.95) 120%)!important;box-shadow:0 20px 46px rgba(20,66,49,.28)!important}.store-board:after{content:'';position:absolute;width:180px;height:180px;border:1px solid rgba(255,255,255,.09);border-radius:50%;right:-70px;top:-90px;pointer-events:none}.board-refresh{min-height:37px!important;color:#245B43!important;background:#fff!important;border:1px solid rgba(255,255,255,.65)!important;border-radius:999px!important;padding:3px 13px!important;font-size:10px!important;font-weight:900!important;box-shadow:0 6px 16px rgba(5,30,21,.2)!important}.board-summary{font-size:9px;font-weight:900;padding:5px 9px;border-radius:999px}.board-summary.pending{background:rgba(255,255,255,.18)}.board-summary.done{background:rgba(147,219,177,.22)}.board-expansion{border-radius:17px!important;background:rgba(7,31,24,.16)!important;border:1px solid rgba(255,255,255,.1)!important}.board-expansion .q-item{min-height:42px;color:#fff;font-size:11px;font-weight:900}.board-expansion .q-expansion-item__content{padding:4px 9px 10px}.board-lanes{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:8px;align-items:start}.board-lane{min-width:0;padding:7px;border-radius:13px;background:rgba(4,28,20,.16)}.board-lane-done{background:rgba(205,235,216,.10)}.board-lane-title{font-size:9px;font-weight:900;opacity:.84;padding:2px}.board-section-title{width:100%;margin-top:5px;padding:5px 4px 2px;border-top:1px solid rgba(255,255,255,.16);font-size:7px;font-weight:900;letter-spacing:.06em;opacity:.76}.board-row{position:relative!important;display:flex!important;flex-direction:column!important;align-items:flex-start!important;gap:3px!important;min-width:0;border-radius:11px!important;background:rgba(255,255,255,.95)!important;color:#20362D!important;box-shadow:0 4px 12px rgba(8,31,23,.10)!important}.board-row-done{flex-direction:row!important;align-items:center!important;background:rgba(232,244,236,.94)!important}.board-area{color:#6E8077;font-size:7px;font-weight:900}.board-name{max-width:100%;font-size:10px;font-weight:900;line-height:1.35;overflow-wrap:anywhere}.board-check{position:absolute!important;right:4px;bottom:4px;min-height:27px!important;min-width:27px!important;background:#246A4E!important;color:white!important}.board-manager-only{font-size:7px;font-weight:900;color:#9B6C21;background:#FFF1D5;padding:3px 5px;border-radius:999px}.board-lane-empty{font-size:9px;opacity:.65;padding:10px 2px}.store-app-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.store-app-card{position:relative;overflow:hidden;min-height:164px;border-radius:24px!important;border:1px solid rgba(255,255,255,.8)!important;box-shadow:0 13px 30px rgba(39,55,45,.10)!important;transition:transform .18s,box-shadow .18s!important;backdrop-filter:blur(9px)}.store-app-card:after{content:'›';position:absolute;right:14px;bottom:9px;font-size:29px;font-weight:300;color:rgba(31,54,44,.26)}.store-app-card:nth-child(1){background:linear-gradient(145deg,rgba(237,245,255,.95),rgba(255,255,255,.92))!important}.store-app-card:nth-child(2){background:linear-gradient(145deg,rgba(234,248,243,.95),rgba(255,255,255,.92))!important}.store-app-card:nth-child(3){background:linear-gradient(145deg,rgba(255,244,229,.95),rgba(255,255,255,.92))!important}.store-app-card:nth-child(4){background:linear-gradient(145deg,rgba(243,238,255,.95),rgba(255,255,255,.92))!important}.store-app-card:hover{transform:translateY(-3px);box-shadow:0 18px 36px rgba(39,55,45,.15)!important}
        """)
        ui.add_css("""
        .board-action-dialog{width:min(90vw,390px)!important;border-radius:23px!important}.board-reopen-all{margin-left:auto!important;color:#fff!important;background:rgba(255,255,255,.14)!important;border-radius:999px!important;font-size:8px!important;font-weight:900!important}
        .business-notice{border-radius:18px!important;background:linear-gradient(135deg,#FFF5D9,#FFF)!important;border:1px solid #EBCB82!important;box-shadow:0 8px 22px rgba(119,82,25,.10)!important}.business-notice .q-item{min-height:50px!important;color:#704B17;font-size:12px;font-weight:950}.business-notice-card{border-radius:13px!important;border:1px solid #F0DFC0!important;box-shadow:none!important}
        .board-longpress{-webkit-touch-callout:none;user-select:none;cursor:context-menu}
        .board-choice-row .q-btn{min-height:27px!important;font-size:8px!important;border-radius:8px!important}
        .board-expansion,.board-expansion .q-expansion-item__content{transform:translateZ(0);will-change:height;contain:layout paint}.q-transition--slide-enter-active,.q-transition--slide-leave-active{transition-duration:.16s!important;transition-timing-function:cubic-bezier(.2,.75,.25,1)!important}.board-row{box-shadow:0 2px 7px rgba(8,31,23,.08)!important}
        """)
        ui.run_javascript("""
        requestAnimationFrame(() => {
          document.querySelectorAll('.board-longpress').forEach(element => {
            if (element.dataset.longpressReady) return;
            element.dataset.longpressReady = '1';
            let timer = null;
            const cancel = () => { if (timer) clearTimeout(timer); timer = null; };
            element.addEventListener('pointerdown', event => {
              if (event.target.closest('button,input,.q-checkbox')) return;
              cancel();
              timer = setTimeout(() => {
                timer = null;
                element.dispatchEvent(new MouseEvent('contextmenu', {
                  bubbles: true, cancelable: true, clientX: event.clientX, clientY: event.clientY
                }));
                if (navigator.vibrate) navigator.vibrate(35);
              }, 650);
            }, {passive: true});
            ['pointerup','pointercancel','pointerleave'].forEach(name =>
              element.addEventListener(name, cancel, {passive: true}));
            element.addEventListener('contextmenu', event => event.preventDefault());
          });
        });
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
