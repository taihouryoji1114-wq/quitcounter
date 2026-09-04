from nicegui import app, ui

from core.auth import current_role, has_permission, require_app_access
from core.clock import operational_date_jst, store_service_period_jst
from core.store_ops import store_ops
from core.store_quiz import store_quiz
from core.staffing import staffing
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
        notices = store_quiz.notices()
        if notices:
            with ui.card().classes("business-notice w-full q-pa-md q-mb-sm"):
                with ui.row().classes("w-full items-center gap-2 no-wrap q-mb-xs"):
                    ui.icon("campaign").classes("text-xl text-amber-9")
                    ui.label(f"業務連絡　{len(notices)}件").classes(
                        "text-sm font-black text-amber-10")
                for notice in notices:
                    with ui.card().classes("business-notice-card w-full q-pa-md q-mb-xs"):
                        ui.label(notice["title"]).classes("text-sm font-black")
                        if notice.get("details"):
                            ui.label(notice["details"]).classes(
                                "text-[10px] text-grey-7 whitespace-pre-wrap q-mt-xs")
                        staff_name = ui.select(
                            list(staffing.STAFF), label="確認するスタッフ名").props(
                            "outlined dense options-dense").classes(
                                "notice-staff-name w-full q-mt-sm")

                        def notice_response(needs_explanation, selected=notice, field=staff_name):
                            try:
                                store_quiz.respond_to_notice(
                                    selected["id"], field.value, needs_explanation)
                            except ValueError as error:
                                ui.notify(str(error), type="warning")
                                return
                            ui.notify(
                                "説明依頼を送りました" if needs_explanation else "確認済みにしました",
                                type="positive")
                            ui.navigate.to("/store-ops")

                        with ui.row().classes("w-full gap-2 q-mt-xs"):
                            ui.button("確認済み", icon="check",
                                      on_click=lambda _, fn=notice_response: fn(False)).props(
                                          "unelevated dense no-caps").classes("grow")
                            ui.button("説明を求める", icon="help_outline",
                                      on_click=lambda _, fn=notice_response: fn(True)).props(
                                          "outline dense no-caps color=warning").classes("grow")
                        acknowledgements = notice.get("acknowledgements", [])
                        explanation_requests = notice.get("explanation_requests", [])
                        if acknowledgements:
                            ui.label("確認済み：" + "、".join(
                                value.get("name", "") for value in acknowledgements)).classes(
                                    "notice-response-list text-positive")
                        if explanation_requests:
                            ui.label("説明希望：" + "、".join(
                                value.get("name", "") for value in explanation_requests)).classes(
                                    "notice-response-list text-warning")
        notice_history = [item for item in store_quiz.notices(include_closed=True)
                          if not item.get("active", True)]
        if notice_history:
            with ui.expansion(f"過去の業務連絡　{len(notice_history)}件", icon="history",
                              value=False).classes("notice-history w-full q-mb-sm"):
                with ui.element("div").classes("notice-history-scroll w-full"):
                    for notice in reversed(notice_history):
                        with ui.column().classes("w-full gap-0 q-py-xs"):
                            ui.label(notice["title"]).classes("text-xs font-black")
                            if notice.get("details"):
                                ui.label(notice["details"]).classes(
                                    "text-[9px] text-grey-6 whitespace-pre-wrap")
        year, month, day = (int(value) for value in business_date.split("-"))
        ui.label(f"{month}月{day}日　TODAY'S OPERATION").classes(
            "today-ribbon w-full")
        with ui.card().classes("store-board w-full q-pa-lg text-white"):
            with ui.row().classes("w-full items-start justify-between no-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label(f"{business_date.replace('-', '/')}　{period_label}営業").classes(
                        "text-[10px] opacity-80 tracking-wide")
                    ui.label("厨房ライブボード").classes("board-title font-black")
                ui.button("更新", icon="refresh", on_click=lambda: ui.navigate.to(
                    "/store-ops")).props("unelevated no-caps aria-label='最新の状態に更新'").classes(
                        "board-refresh")
            # ホームは厨房作業に集中し、申し送りと発注依頼は専用カードで扱う。
            board_items = [item for item in board["items"]
                           if item.get("kind") in {"prep", "check_result"}]
            order_checks = store_ops.daily_order_checks(business_date)
            order_attention = store_ops.daily_order_attention(business_date)
            for destination in store_ops.DAILY_ORDER_DESTINATIONS:
                board_items.append({
                    "id": destination, "kind": "order_check",
                    "name": f"{destination}へ発注", "area": "今日の発注",
                    "from_date": business_date, "from_period": period,
                    "completed": bool(order_checks[destination]),
                    "attention": bool(order_attention[destination]),
                })
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

            def reload_in_place():
                ui.run_javascript("""
                sessionStorage.setItem('storeBoardScrollY', String(window.scrollY));
                document.querySelectorAll('.prep-icon-pages').forEach((rail, index) =>
                  sessionStorage.setItem(`storeBoardRail${index}`, String(rail.scrollLeft)));
                window.location.reload();
                """)

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
                    elif item["kind"] == "order_check":
                        store_ops.set_daily_order_check(item["from_date"], item["id"], False)
                        store_ops.set_daily_order_attention(item["from_date"], item["id"], False)
                    elif item["kind"] in {"prep", "check_result"}:
                        store_ops.reset_service_prep_items(
                            item["from_date"], item["from_period"], [item["id"]])
                    elif item["kind"] == "note":
                        store_ops.reopen_handover(item["from_date"], item["id"])
                    keep_group_open(item)
                    long_press_dialog.close()
                    reload_in_place()

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

            summary_state = {"pending": len(pending_items), "done": len(done_items)}

            def complete_item(item, row=None, number_label=None, action=None):
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
                elif item["kind"] == "order_check":
                    store_ops.set_daily_order_check(item["from_date"], item["id"], True)
                keep_group_open(item)
                if row is None:
                    reload_in_place()
                    return
                item["completed"] = True
                row.classes(add="prep-icon-completed")
                if number_label:
                    number_label.set_text("完了")
                if action:
                    action.set_visibility(False)
                summary_state["pending"] = max(0, summary_state["pending"] - 1)
                summary_state["done"] += 1
                pending_summary.set_text(str(summary_state["pending"]))
                done_summary.set_text(f"完了済み {summary_state['done']}件")

            def save_rice_choice(item, choice):
                store_ops.set_service_prep_choice(
                    item["from_date"], item["from_period"], item["id"], choice)
                keep_group_open(item)
                reload_in_place()

            def save_prep_quantity(item, field):
                store_ops.set_service_prep_quantity(
                    item["from_date"], item["from_period"], item["id"], field.value)
                keep_group_open(item)
                reload_in_place()

            switch_target = {"next": None}
            with ui.dialog() as switch_dialog, ui.card().classes(
                    "board-action-dialog q-pa-lg"):
                ui.label("次の営業へ切り替えますか？").classes("text-lg font-black")
                switch_message = ui.label().classes("text-xs text-grey-7 q-mt-xs")

                def advance_service():
                    store_ops.advance_service_context()
                    switch_dialog.close()
                    ui.navigate.to("/store-ops")

                with ui.row().classes("w-full gap-2 q-mt-md"):
                    ui.button("まだ切り替えない", on_click=switch_dialog.close).props(
                        "flat no-caps").classes("grow")
                    ui.button("切り替える", icon="skip_next", on_click=advance_service).props(
                        "unelevated no-caps color=primary").classes("grow")

            def ask_advance_service():
                unfinished = sum(1 for item in board_items
                                 if board_group(item) == "prep" and not item.get("completed"))
                next_label = "ディナー" if period == "lunch" else "翌日のランチ"
                switch_message.set_text(
                    f"未完了が{unfinished}件あります。状態を残したまま{next_label}へ進みます。")
                switch_dialog.open()

            with ui.row().classes("w-full items-center gap-2 q-mt-sm"):
                pending_summary = ui.label(str(len(pending_items))).classes(
                    "board-count-badge")
                ui.label("未完了").classes("board-count-caption")
                done_summary = ui.label(f"完了済み {len(done_items)}件").classes(
                    "board-summary done")

            with ui.dialog() as reset_board_dialog, ui.card().classes(
                    "board-action-dialog q-pa-lg"):
                ui.label("仕込みを一括リセットしますか？").classes("text-lg font-black")
                ui.label("この営業の仕込みをすべて未完了へ戻します。発注チェックは変わりません。").classes(
                    "text-xs text-grey-7 q-mt-xs")

                def reset_prep_board():
                    grouped = {}
                    for item in board_items:
                        if item.get("kind") not in {"prep", "check_result"}:
                            continue
                        key = (item.get("from_date"), item.get("from_period"))
                        grouped.setdefault(key, []).append(item.get("id"))
                    changed = 0
                    for (source_date, source_period), item_ids in grouped.items():
                        changed += store_ops.reset_service_prep_items(
                            source_date, source_period, item_ids)
                    reset_board_dialog.close()
                    ui.notify(f"仕込み {changed}件を未完了へ戻しました", type="positive")
                    reload_in_place()

                with ui.row().classes("w-full gap-2 q-mt-md"):
                    ui.button("やめる", on_click=reset_board_dialog.close).props(
                        "flat no-caps").classes("grow")
                    ui.button("一括リセット", icon="restart_alt", on_click=reset_prep_board).props(
                        "unelevated no-caps color=warning").classes("grow")

            ui.button("仕込みを一括リセット", icon="restart_alt",
                      on_click=reset_board_dialog.open).props(
                          "flat no-caps").classes("prep-reset-all w-full q-mt-xs")
            ui.button(
                "ディナーへ切り替える" if period == "lunch" else "本日の営業を締める",
                icon="east", on_click=ask_advance_service,
            ).props("unelevated no-caps").classes("service-switch w-full q-mt-sm")
            def render_board_lane(items):
                def is_feature_item(value):
                    return bool(value.get("check_items") or value.get("note_enabled")
                                or value.get("quantity_mode") or value.get("choice_mode"))

                pages, current_page, used = [], [], 0
                for value in items:
                    weight = 2 if is_feature_item(value) else 1
                    # Six grid cells fit comfortably on a phone without clipping.
                    if current_page and used + weight > 6:
                        pages.append(current_page)
                        current_page, used = [], 0
                    current_page.append(value)
                    used += weight
                if current_page:
                    pages.append(current_page)

                with ui.column().classes("prep-icon-board w-full"):
                    with ui.row().classes("w-full items-center justify-between no-wrap"):
                        ui.label("タップして完了").classes("prep-icon-guide")
                        if len(pages) > 1:
                            ui.label(f"横へスワイプ　{len(pages)}ページ").classes(
                                "board-swipe-hint")
                    if not pages:
                        ui.label("仕込みはありません").classes("board-lane-empty")
                        return
                    with ui.element("div").classes("prep-icon-pages w-full"):
                        for page_number, page_items in enumerate(pages, 1):
                            with ui.element("div").classes("prep-icon-page"):
                                for item in page_items:
                                    feature = is_feature_item(item)
                                    slot = ui.element("div").classes(
                                        "prep-icon-slot prep-icon-feature-slot" if feature
                                        else "prep-icon-slot")
                                    tile_classes = "prep-icon prep-icon-feature" if feature else "prep-icon"
                                    if item.get("completed"):
                                        tile_classes += " prep-icon-completed"
                                    elif item.get("checked_items"):
                                        tile_classes += " prep-icon-progress"
                                    tile = ui.card().classes(tile_classes)
                                    tile.move(slot)
                                    with tile:
                                        with ui.row().classes("w-full items-start justify-between no-wrap"):
                                            ui.icon(
                                                "check_circle" if item.get("completed") else
                                                ("pending" if item.get("checked_items") else "restaurant"),
                                            ).classes("prep-icon-symbol")
                                            if item.get("note_enabled"):
                                                ui.icon("sticky_note_2").classes("prep-icon-badge")
                                        ui.label(item["name"]).classes("prep-icon-name")
                                        if item.get("check_items"):
                                            status_text = (
                                                f"{len(item.get('checked_items', []))}/"
                                                f"{len(item['check_items'])}")
                                        elif item.get("quantity_mode"):
                                            status_text = f"現在 {item.get('quantity', 0)}個"
                                        elif item.get("choice_mode"):
                                            status_text = item.get("choice") or "あり・なし"
                                        else:
                                            status_text = "完了" if item.get("completed") else "未完了"
                                        status_label = ui.label(status_text).classes("prep-icon-status")
                                        check_preview_label = None
                                        if item.get("check_items"):
                                            checked_preview = "　".join(
                                                f"✓ {name}" for name in item.get("checked_items", []))
                                            check_preview_label = ui.label(
                                                checked_preview).classes("prep-icon-checked-preview")

                                    if not feature:
                                        def tap_simple(_, value=item, card=tile, label=status_label):
                                            if value.get("completed"):
                                                open_long_press(value)
                                            else:
                                                complete_item(value, card, label)
                                                card.classes(add="prep-icon-completed")
                                                label.set_text("完了")
                                                ui.notify(
                                                    f"{value['name']}を完了しました",
                                                    type="positive", timeout=1800)
                                        tile.on("click", tap_simple)
                                        continue

                                    with ui.dialog() as detail_dialog, ui.card().classes(
                                            "prep-detail-dialog q-pa-lg"):
                                        with ui.row().classes("w-full items-start justify-between no-wrap"):
                                            with ui.column().classes("gap-0"):
                                                ui.label(item["name"]).classes("text-lg font-black")
                                                ui.label("仕込みの内容").classes("text-[9px] text-grey-6")
                                            ui.button(icon="close", on_click=detail_dialog.close).props(
                                                "flat round dense aria-label='閉じる'")
                                        check_fields = []
                                        if item.get("check_items"):
                                            for check_text in item["check_items"]:
                                                field = ui.checkbox(
                                                    check_text,
                                                    value=check_text in item.get("checked_items", []),
                                                ).classes("board-subcheck w-full")
                                                check_fields.append((check_text, field))

                                            def save_subchecks(_, value=item, fields=check_fields,
                                                               card=tile, label=status_label,
                                                               preview=check_preview_label):
                                                checked = [text for text, field in fields if field.value]
                                                store_ops.set_service_prep_subchecks(
                                                    value["from_date"], value["from_period"],
                                                    value["id"], checked)
                                                was_complete = bool(value.get("completed"))
                                                complete = len(checked) == len(fields)
                                                value["checked_items"] = checked
                                                label.set_text(f"{len(checked)}/{len(fields)}")
                                                if preview:
                                                    preview.set_text("　".join(
                                                        f"✓ {name}" for name in checked))
                                                card.classes(
                                                    add="prep-icon-completed" if complete else (
                                                        "prep-icon-progress" if checked else ""),
                                                    remove="prep-icon-progress" if complete else (
                                                        "prep-icon-completed" if checked else
                                                        "prep-icon-completed prep-icon-progress"),
                                                )
                                                value["completed"] = complete
                                                if complete != was_complete:
                                                    summary_state["pending"] += -1 if complete else 1
                                                    summary_state["done"] += 1 if complete else -1
                                                    pending_summary.set_text(
                                                        str(summary_state["pending"]))
                                                    done_summary.set_text(
                                                        f"完了済み {summary_state['done']}件")
                                            for _, field in check_fields:
                                                field.on_value_change(save_subchecks)
                                        if item.get("choice_mode"):
                                            with ui.row().classes("board-choice-row w-full gap-2 q-mt-sm"):
                                                ui.button("あり", on_click=lambda _, value=item:
                                                          save_rice_choice(value, "あり")).props(
                                                              "unelevated no-caps color=positive").classes("grow")
                                                ui.button("なし", on_click=lambda _, value=item:
                                                          save_rice_choice(value, "なし")).props(
                                                              "outline no-caps color=primary").classes("grow")
                                        elif item.get("quantity_mode"):
                                            quantity = ui.number(
                                                value=max(0, int(item.get("quantity", 0) or 0)),
                                                min=0, step=1, suffix="個",
                                            ).props("outlined inputmode=numeric").classes(
                                                "board-quantity w-full q-mt-sm")
                                            ui.button(
                                                "個数を保存", icon="save",
                                                on_click=lambda _, value=item, field=quantity:
                                                    save_prep_quantity(value, field),
                                            ).props("unelevated no-caps").classes(
                                                "board-quantity-save w-full")
                                        if item.get("note_enabled"):
                                            note = ui.textarea(
                                                "補足メモ", value=item.get("note", ""),
                                            ).props("outlined autogrow dense").classes(
                                                "board-note w-full q-mt-sm")
                                            ui.button(
                                                "メモを保存", icon="save",
                                                on_click=lambda _, value=item, field=note: (
                                                    store_ops.set_service_prep_note(
                                                        value["from_date"], value["from_period"],
                                                        value["id"], field.value),
                                                    ui.notify("メモを保存しました", type="positive"),
                                                ),
                                            ).props("flat dense no-caps").classes("board-note-save")
                                    if (item.get("note_enabled") and not item.get("check_items")
                                                and not item.get("quantity_mode")
                                                and not item.get("choice_mode")):
                                            ui.button(
                                                "完了にする", icon="check",
                                                on_click=lambda _, value=item, card=tile,
                                                label=status_label, dialog=detail_dialog: (
                                                    complete_item(value, card, label),
                                                    card.classes(add="prep-icon-completed"),
                                                    label.set_text("完了"),
                                                    dialog.close(),
                                                ),
                                            ).props("unelevated no-caps").classes(
                                                "board-ticket-complete w-full q-mt-sm")
                                    # Keep the dialog inside its card slot. Otherwise the hidden
                                    # dialog itself is counted as another CSS-grid item and pushes
                                    # visible cards off the page.
                                    detail_dialog.move(slot)
                                    tile.on("click", lambda _, dialog=detail_dialog: dialog.open())
                                if len(pages) > 1:
                                    ui.label(f"{page_number}/{len(pages)}").classes(
                                        "prep-page-number")
                    if len(pages) > 1:
                        with ui.row().classes("prep-page-controls w-full items-center justify-center"):
                            ui.button(icon="chevron_left", on_click=lambda: ui.run_javascript(
                                "const r=document.querySelector('.prep-icon-pages');"
                                "if(r)r.scrollBy({left:-r.clientWidth,behavior:'smooth'});"
                            )).props("flat round dense aria-label='前のページ'")
                            ui.label("ページを切り替える").classes("text-[8px] font-bold opacity-70")
                            ui.button(icon="chevron_right", on_click=lambda: ui.run_javascript(
                                "const r=document.querySelector('.prep-icon-pages');"
                                "if(r)r.scrollBy({left:r.clientWidth,behavior:'smooth'});"
                            )).props("flat round dense aria-label='次のページ'")

            with ui.expansion(
                "仕込み一覧を開く", icon="apps", value=False,
            ).props("duration=180").classes("prep-board-expansion w-full q-mt-sm"):
                render_board_lane(
                    [item for item in board_items if board_group(item) == "prep"])

        with ui.element("div").classes("store-app-grid w-full q-mt-md"):
            app_card("在庫確認", "現在数をまとめて入力", "inventory_2",
                     "/store-ops/inventory", "text-emerald-7")
            open_handovers = sum(
                1 for item in store_ops.all_handovers()
                if not item.get("confirmed", False))
            open_requests = len(store_ops.order_requests(open_only=True))
            app_card("自由引き継ぎ", "申し送りを記録・確認", "edit_note",
                     "/store-ops/handover", "text-amber-8", open_handovers)
            app_card("発注依頼", "必要な物をその場で共有", "add_shopping_cart",
                     "/store-ops/order-requests", "text-red-7", open_requests)
            app_card("シフト提出", "半月ごとの勤務希望", "calendar_month",
                     "/store-ops/shift-submission", "text-blue-7")

        with ui.row().classes("w-full items-center justify-between q-mt-lg q-mb-xs"):
            ui.label("その他の機能").classes("store-more-title")
            ui.label("横へスワイプ").classes("store-more-hint")
        with ui.element("div").classes("store-app-rail w-full"):
            app_card("アナウンス", "定時のお知らせ・お試し再生", "campaign",
                     "/store-ops/announcements", "text-amber-8")
            app_card("温度・衛生", "冷蔵庫温度と衛生記録", "health_and_safety",
                     "/store-ops/hygiene", "text-cyan-8")
            app_card("清掃", "清掃状況と担当確認", "cleaning_services",
                     "/store-ops/cleaning", "text-teal-7")
            app_card("マニュアル", "手順・考え方・行動指針", "menu_book",
                     "/store-ops/manual", "text-orange-8")
            app_card("イベントスケジュール", "店舗行事と予定を共有", "event",
                     "/store-ops/events", "text-purple-7")
            app_card("ちゃんはや", "ちゃんこで早押しクイズ", "quiz",
                     "/store-ops/chanhaya", "text-red-7")
            if current_role() == "owner":
                app_card("仕入れリスト", "購入する物と個数を確認", "shopping_basket",
                         "/store-ops/purchase-list", "text-deep-orange-7")
                app_card("登録・設定", "商品・仕込み項目を管理", "settings",
                         "/store-ops/settings", "text-grey-8")

        ui.add_css("""
        body{background:linear-gradient(180deg,rgba(244,247,244,.76),rgba(239,238,232,.88)),url('/static/store_ops_home_bg_v3.png') center top/cover no-repeat scroll!important}.today-ribbon{color:#527060;font-size:9px;font-weight:900;letter-spacing:.14em;margin-bottom:9px;padding-left:4px}.store-board{position:relative;overflow:hidden;border:0!important;border-radius:29px!important;background:radial-gradient(circle at 95% 0%,rgba(234,190,102,.48),transparent 34%),linear-gradient(145deg,rgba(16,47,38,.96),rgba(40,96,71,.95) 62%,rgba(85,122,74,.95) 120%)!important;box-shadow:0 20px 46px rgba(20,66,49,.28)!important}.store-board:after{content:'';position:absolute;width:180px;height:180px;border:1px solid rgba(255,255,255,.09);border-radius:50%;right:-70px;top:-90px;pointer-events:none}.board-title{font-size:23px;line-height:1.12;white-space:nowrap}.board-refresh{min-height:37px!important;color:#245B43!important;background:#fff!important;border:1px solid rgba(255,255,255,.65)!important;border-radius:999px!important;padding:3px 13px!important;font-size:10px!important;font-weight:900!important;box-shadow:0 6px 16px rgba(5,30,21,.2)!important}.board-summary{font-size:9px;font-weight:900;padding:5px 9px;border-radius:999px}.board-summary.pending{background:rgba(255,255,255,.18)}.board-summary.done{background:rgba(147,219,177,.22)}.prep-reset-all{color:#fff!important;font-size:9px!important;font-weight:900!important;opacity:.9}.board-expansion{border-radius:17px!important;background:rgba(7,31,24,.16)!important;border:1px solid rgba(255,255,255,.1)!important}.board-expansion .q-item{min-height:42px;color:#fff;font-size:11px;font-weight:900}.board-expansion .q-expansion-item__content{padding:4px 9px 10px}.board-lanes{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:8px;align-items:start}.board-lane{min-width:0;padding:7px;border-radius:13px;background:rgba(4,28,20,.16)}.board-lane-done{background:rgba(205,235,216,.10)}.board-lane-title{font-size:9px;font-weight:900;opacity:.84;padding:2px}.board-section-title{width:100%;margin-top:5px;padding:5px 4px 2px;border-top:1px solid rgba(255,255,255,.16);font-size:7px;font-weight:900;letter-spacing:.06em;opacity:.76}.board-row{position:relative!important;display:flex!important;flex-direction:column!important;align-items:flex-start!important;gap:3px!important;min-width:0;border-radius:11px!important;background:rgba(255,255,255,.95)!important;color:#20362D!important;box-shadow:0 4px 12px rgba(8,31,23,.10)!important}.board-row-done{flex-direction:row!important;align-items:center!important;background:rgba(232,244,236,.94)!important}.board-area{color:#6E8077;font-size:7px;font-weight:900}.board-name{max-width:100%;font-size:10px;font-weight:900;line-height:1.35;overflow-wrap:anywhere}.board-check{position:absolute!important;right:4px;bottom:4px;min-height:27px!important;min-width:27px!important;background:#246A4E!important;color:white!important}.board-manager-only{font-size:7px;font-weight:900;color:#9B6C21;background:#FFF1D5;padding:3px 5px;border-radius:999px}.board-lane-empty{font-size:9px;opacity:.65;padding:10px 2px}.store-app-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.store-app-card{position:relative;overflow:hidden;min-height:164px;border-radius:24px!important;border:1px solid rgba(255,255,255,.8)!important;box-shadow:0 13px 30px rgba(39,55,45,.10)!important;transition:transform .18s,box-shadow .18s!important;background:linear-gradient(145deg,rgba(246,249,247,.98),rgba(255,255,255,.96))!important}.store-app-card:after{content:'›';position:absolute;right:14px;bottom:9px;font-size:29px;font-weight:300;color:rgba(31,54,44,.26)}.store-app-grid>.store-app-card:nth-child(1){background:linear-gradient(145deg,rgba(237,245,255,.98),rgba(255,255,255,.96))!important}.store-app-grid>.store-app-card:nth-child(2){background:linear-gradient(145deg,rgba(234,248,243,.98),rgba(255,255,255,.96))!important}.store-app-grid>.store-app-card:nth-child(3){background:linear-gradient(145deg,rgba(255,244,229,.98),rgba(255,255,255,.96))!important}.store-app-grid>.store-app-card:nth-child(4){background:linear-gradient(145deg,rgba(243,238,255,.98),rgba(255,255,255,.96))!important}.store-app-card:hover{transform:translateY(-2px);box-shadow:0 18px 36px rgba(39,55,45,.15)!important}.store-more-title{font-size:13px;font-weight:950;color:#27493a}.store-more-hint{font-size:8px;font-weight:850;color:#718078}.store-app-rail{display:flex;gap:11px;overflow-x:auto;scroll-snap-type:x proximity;overscroll-behavior-x:contain;-webkit-overflow-scrolling:touch;scrollbar-width:none;padding:3px 2px 14px;touch-action:pan-x pan-y}.store-app-rail::-webkit-scrollbar{display:none}.store-app-rail>.store-app-card{flex:0 0 57%;min-height:138px!important;scroll-snap-align:start;padding:17px!important}.store-app-rail>.store-app-card .text-4xl{font-size:28px!important}.store-app-rail>.store-app-card .text-lg{font-size:14px!important}@media(min-width:700px){.store-app-rail>.store-app-card{flex-basis:31%}}@media(max-width:390px){.store-board{padding:17px!important}.board-title{font-size:20px}.board-refresh{padding:2px 10px!important}}
        """)
        ui.add_css("""
        .board-action-dialog{width:min(90vw,390px)!important;border-radius:23px!important}.service-switch{min-height:40px!important;border-radius:14px!important;background:rgba(255,255,255,.96)!important;color:#245B43!important;font-size:10px!important;font-weight:950!important}.board-quantity .q-field__control{min-height:34px!important;height:34px!important;background:#fff;border-radius:9px!important}.board-quantity-save{min-height:29px!important;margin-top:3px!important;border-radius:9px!important;background:#246A4E!important;font-size:8px!important}
        .business-notice{border-radius:18px!important;background:linear-gradient(135deg,#FFF5D9,#FFF)!important;border:1px solid #EBCB82!important;box-shadow:0 8px 22px rgba(119,82,25,.10)!important}.business-notice-card{border-radius:13px!important;border:1px solid #F0DFC0!important;box-shadow:none!important;background:rgba(255,255,255,.84)!important}
        .board-longpress{-webkit-touch-callout:none;user-select:none;cursor:context-menu}
        .board-choice-row .q-btn{min-height:27px!important;font-size:8px!important;border-radius:8px!important}
        .board-expansion .q-expansion-item__content{contain:content}.board-expansion .q-transition--slide-enter-active,.board-expansion .q-transition--slide-leave-active{transition:none!important;animation:none!important}.board-row{box-shadow:0 2px 7px rgba(8,31,23,.08)!important}
        .prep-board-expansion{border-radius:17px!important;background:rgba(5,29,21,.19)!important;border:1px solid rgba(255,255,255,.13)!important}.prep-board-expansion>.q-expansion-item__container>.q-item{min-height:44px!important;color:#fff!important;font-size:11px;font-weight:950}.prep-board-expansion .q-expansion-item__content{padding:1px 7px 8px}.prep-icon-board{padding:8px 1px 2px!important;gap:7px!important;touch-action:pan-x pan-y}.prep-icon-guide{font-size:9px;font-weight:900;opacity:.78}.board-swipe-hint{font-size:8px;font-weight:800;opacity:.68}.prep-icon-pages{display:flex;overflow-x:auto;overscroll-behavior-x:contain;scroll-snap-type:x mandatory;scroll-behavior:smooth;-webkit-overflow-scrolling:touch;scrollbar-width:none;touch-action:pan-x pan-y;padding:2px 0 7px}.prep-icon-pages::-webkit-scrollbar{display:none}.prep-icon-page{position:relative;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:repeat(4,108px);grid-auto-flow:row dense;grid-auto-rows:108px;align-content:start;gap:9px;flex:0 0 100%;width:100%;min-width:100%;max-width:100%;height:483px;box-sizing:border-box;overflow:hidden;scroll-snap-align:start;scroll-snap-stop:always;padding:2px 2px 22px}.prep-icon-slot{min-width:0;width:100%;height:108px}.prep-icon-feature-slot{grid-column:span 2}.prep-icon{position:relative!important;display:flex!important;flex-direction:column!important;justify-content:space-between!important;min-width:0!important;width:100%!important;height:108px!important;min-height:108px!important;max-height:108px!important;overflow:hidden!important;padding:10px!important;cursor:pointer;border-radius:20px!important;color:#17382c!important;background:linear-gradient(145deg,rgba(255,255,255,.99),rgba(225,238,230,.97))!important;border:1px solid rgba(255,255,255,.92)!important;box-shadow:0 7px 16px rgba(1,24,17,.18)!important;transition:transform .16s ease,background .2s ease,color .2s ease!important;-webkit-tap-highlight-color:transparent;user-select:none}.prep-icon:active{transform:scale(.96)}.prep-icon-feature{background:linear-gradient(135deg,#fffdf7,#f4ead1)!important;border-color:#f1d99f!important}.prep-icon-completed{color:#563b05!important;background:linear-gradient(145deg,#ffe991,#d9ac36)!important;border-color:#ffe286!important;box-shadow:0 7px 18px rgba(129,82,6,.23)!important}.prep-icon-progress{color:#5a3b05!important;background:linear-gradient(145deg,#fff2cc,#f0c574)!important;border-color:#f4d290!important}.prep-icon-symbol{font-size:22px!important;color:#2b7757}.prep-icon-completed .prep-icon-symbol,.prep-icon-progress .prep-icon-symbol{color:#855b08}.prep-icon-badge{font-size:17px!important;color:#a66c12}.prep-icon-name{display:-webkit-box;max-width:100%;max-height:34px;font-size:12px;font-weight:950;line-height:1.3;overflow:hidden;overflow-wrap:anywhere;-webkit-box-orient:vertical;-webkit-line-clamp:2}.prep-icon-status{flex:0 0 auto;max-width:100%;font-size:9px;font-weight:900;line-height:1.2;opacity:.72;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.prep-icon-checked-preview{display:-webkit-box;width:100%;max-height:21px;overflow:hidden;font-size:8px;font-weight:850;line-height:1.3;color:#806529;text-decoration:line-through;white-space:normal;overflow-wrap:anywhere;-webkit-box-orient:vertical;-webkit-line-clamp:2}.prep-page-number{position:absolute;left:50%;bottom:1px;transform:translateX(-50%);font-size:8px;font-weight:900;opacity:.62}.prep-page-controls{gap:4px!important;margin-top:-5px}.prep-page-controls .q-btn{color:#fff!important}.prep-detail-dialog{width:min(92vw,430px)!important;max-height:88vh;overflow-y:auto;border-radius:25px!important}.board-subcheck{font-size:11px;font-weight:850;padding:5px 2px;border-bottom:1px solid #eee}.board-subcheck:has(.q-checkbox__inner--truthy) .q-checkbox__label{text-decoration:line-through;color:#8b948f}.board-note .q-field__control{background:rgba(255,255,255,.88);border-radius:10px}.board-note-save{align-self:flex-end;color:#246A4E!important;font-size:8px!important}.notice-history{border:1px solid #E4E9E5!important;border-radius:16px!important;background:rgba(255,255,255,.9)!important}.notice-history .q-expansion-item__content{padding:3px 14px 10px}@media(min-width:700px){.prep-icon-page{grid-template-columns:repeat(4,minmax(0,1fr));grid-template-rows:repeat(2,118px);grid-auto-rows:118px;height:269px}.prep-icon-slot,.prep-icon,.prep-icon-feature{height:118px!important;min-height:118px!important;max-height:118px!important}.prep-icon-name{font-size:14px}}
        """)
        ui.add_css("""
        .store-board,.prep-board-expansion,.prep-icon-board,.prep-icon-pages{min-width:0!important;max-width:100%!important;box-sizing:border-box!important}
        .prep-icon-page>*{min-width:0!important;max-width:100%!important;box-sizing:border-box!important}
        /* Mobile live-board: six grid cells per page. Dialogs are moved out of the
           grid in Python, so only visible cards participate in this layout. */
        .prep-icon-page{grid-template-rows:repeat(3,126px)!important;grid-auto-rows:126px!important;height:418px!important;padding-bottom:20px!important}
        .prep-icon-slot{height:126px!important}
        .prep-icon{justify-content:flex-start!important;box-sizing:border-box!important;height:126px!important;min-height:126px!important;max-height:126px!important}
        .prep-icon>.q-row{flex:0 0 auto!important}
        .prep-icon-name{flex:0 0 auto!important;min-height:31px!important;max-height:31px!important;margin-top:5px!important}
        .prep-icon-status{margin-top:auto!important}
        .prep-icon-checked-preview{flex:0 0 auto!important;max-height:20px!important;line-height:1.25!important}
        @media(min-width:700px){.prep-icon-page{grid-template-rows:repeat(2,118px)!important;grid-auto-rows:118px!important;height:269px!important;padding-bottom:22px!important}.prep-icon-slot,.prep-icon{height:118px!important;min-height:118px!important;max-height:118px!important}}
        .notice-staff-name .q-field__control{min-height:38px!important;height:38px!important}
        .notice-response-list{font-size:8px;font-weight:900;margin-top:5px;overflow-wrap:anywhere}
        .notice-history-scroll{max-height:260px;overflow-y:auto;-webkit-overflow-scrolling:touch;padding-right:4px}
        .store-app-badge{position:absolute;z-index:3;right:13px;top:12px;display:grid;place-items:center;min-width:25px;height:25px;padding:0 7px;border-radius:999px;background:#E43F3F;color:#fff;font-size:11px;font-weight:950;box-shadow:0 4px 10px rgba(167,26,26,.28)}
        .board-count-badge{display:grid;place-items:center;min-width:26px;height:26px;padding:0 7px;border-radius:999px;background:#E84646;color:#fff;font-size:11px;font-weight:950;box-shadow:0 4px 10px rgba(0,0,0,.18)}
        .board-count-caption{font-size:9px;font-weight:900;opacity:.82}
        """)
        ui.run_javascript("""
        requestAnimationFrame(() => {
          const savedY = sessionStorage.getItem('storeBoardScrollY');
          if (savedY !== null) {
            sessionStorage.removeItem('storeBoardScrollY');
            setTimeout(() => window.scrollTo({top: Number(savedY), behavior: 'auto'}), 80);
          }
          document.querySelectorAll('.prep-icon-pages').forEach((rail, index) => {
            const savedX = sessionStorage.getItem(`storeBoardRail${index}`);
            if (savedX !== null) {
              sessionStorage.removeItem(`storeBoardRail${index}`);
              rail.scrollLeft = Number(savedX);
            }
          });
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
