from datetime import datetime, timezone

from nicegui import ui

from store_preview.core.clock import JAPAN
from store_preview.core.store_ops import store_ops
from store_preview.core.live_board_review import live_board_review


STATUS_META = {
    "done": ("○", "good"),
    "attention": ("△", "warning"),
    "incomplete": ("×", "bad"),
}


def format_live_board_update_time(value):
    """Show both new offset-aware and legacy server timestamps in Japan time."""
    if not value:
        return "最終更新 まだありません"
    try:
        timestamp = datetime.fromisoformat(str(value))
        # Older records were written by the public server without a timezone.
        # That server runs in UTC, so interpret those values before displaying.
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return f"最終更新 {timestamp.astimezone(JAPAN):%Y/%m/%d %H:%M}"
    except (TypeError, ValueError):
        return "最終更新時刻を確認できません"


def handover_date_label(item):
    update = item.get("last_update", {})
    value = update.get("updated_at")
    if not value:
        return "記録日時なし"
    return format_live_board_update_time(value).replace("最終更新", "記録更新", 1)


def confirmation_items(items):
    return [item for item in items if item.get("source") != "daily_order"
            and item.get("visible", True) and item.get("item_type") != "memo"
            and (item.get("item_type") != "quantity" or item.get("progress_enabled"))]


def selected_live_status(item):
    return None if item.get("reviewed") is False else item.get("status")


def live_board_summary(items):
    eligible = confirmation_items(items)
    groups = {"△": [], "×": [], "未完了": []}
    seen = set()
    for item in eligible:
        if item.get("id") in seen:
            continue
        seen.add(item.get("id"))
        status = selected_live_status(item) if item.get("item_type") == "status" else item.get("status")
        if status is None:
            groups["未完了"].append(item)
            continue
        if status == "attention":
            groups["△"].append(item)
        elif status != "done":
            groups["×" if item.get("item_type") == "status" else "未完了"].append(item)
    return sum(item.get("reviewed", item.get("status") in {"done", "attention"}) for item in eligible), len(eligible), groups


def confirmation_label(checked, total):
    if not total:
        return "確認項目なし"
    return "全項目 確認済み ✓" if checked == total else f"未確認 あと{total - checked}件"


def render_live_board(business_date, period, period_label, aside=None, date_label=None):
    """Render the staff-facing board: every routine action happens in place."""
    categories = store_ops.live_board_categories()
    category_visibility = {value["name"]: value.get("visible", True) for value in categories}
    category_colors = {value["name"]: value.get("color", "#527A68") for value in categories}
    order_category = next((value for value in categories
                           if value.get("system_key") == "daily_order"), {
                               "name": store_ops.DAILY_ORDER_CATEGORY,
                               "visible": True,
                               "color": store_ops.DAILY_ORDER_CATEGORY_COLOR,
                           })
    order_category_name = order_category["name"]
    items = store_ops.service_prep_items(business_date, period)
    items = [item for item in items if item.get("visible", True)
             and category_visibility.get(item.get("area", "厨房"), True)
             and item.get("area", "厨房") != order_category_name]
    live_board_review.initialize_handover(items, {
        item["id"]: store_ops.handover_acknowledged(business_date, period, item) for item in items
    })
    for item in items:
        item["reviewed"] = live_board_review.checked(item["id"])
    review_day = {"value": live_board_review.day_key()}

    def current_context():
        nonlocal business_date, period
        today = live_board_review.day_key()
        if today > business_date:
            business_date, period = store_ops.active_service_context(today, period)
        if date_label is not None:
            year, month, day = map(int, today.split('-'))
            date_label.set_text(f"{year}年{month}月{day}日")

    def record_result(item_id, mark_checked=True):
        saved = next(value for value in store_ops.service_prep_items(business_date, period) if value['id'] == item_id)
        if mark_checked:
            live_board_review.record(saved)
        else:
            live_board_review.update_note(saved)

    category_names = [value["name"] for value in categories if value.get("visible", True)]
    for item in items:
        if item.get("area", "厨房") not in category_names:
            category_names.append(item.get("area", "厨房"))
    # Daily ordering always appears as the final section of the staff board.
    category_names = [name for name in category_names if name != order_category_name]
    category_colors.setdefault(order_category_name, order_category.get(
        "color", store_ops.DAILY_ORDER_CATEGORY_COLOR))

    def counts():
        return sum(live_board_review.checked(item["id"]) for item in items), len(items)

    complete, total = counts()

    def update_time_text():
        value = store_ops.live_board_last_updated_at(business_date, period)
        return format_live_board_update_time(value)

    @ui.refreshable
    def handover_list():
        snapshots = live_board_review.handovers({item['id'] for item in items})
        with ui.card().classes("live-handover-top w-full gap-1"):
            ui.label("引き継ぎリスト").classes("text-sm font-bold")
            ui.label("チェックした結果を保持します。午前4時には消えません。").classes("text-xs text-grey-7")
            if not snapshots:
                ui.label("チェックすると、ここに結果が表示されます").classes("text-sm text-grey-7 q-py-sm")
            for value in snapshots:
                with ui.column().classes("live-handover-group w-full gap-1"):
                    with ui.row().classes("w-full items-center justify-between gap-2"):
                        ui.label(value['name']).classes("live-handover-name")
                        if value.get('item_type') == 'quantity':
                            result = f"{value.get('quantity', 0)}{value.get('unit', '個')}"
                        elif value.get('item_type') == 'memo':
                            result = "確認済み"
                        else:
                            symbol = {'done': '○', 'attention': '△', 'incomplete': '×'}.get(value.get('status'), '—')
                            text = value.get('status_labels', {}).get(value.get('status')) if value.get('item_type') == 'status' else ('完了' if value.get('status') == 'done' else '未完了')
                            result = f"{symbol} {text or ''}"
                        ui.label(result).classes("live-handover-result")
                    if value.get('note'):
                        ui.label(value['note']).classes("text-sm whitespace-pre-wrap")
                    stamp = value.get('confirmed_at') or value.get('last_update', {}).get('updated_at')
                    ui.label(format_live_board_update_time(stamp).replace('最終更新', '確認')).classes("text-xs text-grey-7")
                    ui.checkbox("引き継ぎ確認", value=value.get('handover_acknowledged', False),
                                on_change=lambda e, item_id=value['id']: live_board_review.acknowledge(item_id, e.value)).props("dense")
    if aside is not None:
        with aside:
            handover_list()
    else:
        handover_list()

    def actor_text(value):
        update = value.get("last_update", {})
        if not update.get("staff_id"):
            return ""
        return f"{update.get('updated_by', '')} · {format_live_board_update_time(update.get('updated_at')).replace('最終更新 ', '')}"

    actor_labels = {}
    status_buttons = {}
    completion_painters = {}
    review_labels = {}
    board_expansion = ui.expansion(
        "厨房ライブボード", icon="dashboard", value=True,
    ).props("duration=160").classes("live-board-collapsed w-full")
    with ui.card() as board_card:
        board_card.classes("live-board-v2 w-full")
        with ui.row().classes("live-board-head w-full items-center justify-between no-wrap"):
            with ui.column().classes("gap-0"):
                ui.label("厨房ライブボード").classes("live-board-title")
                ui.label(f"{business_date.replace('-', '/')}　{period_label}").classes(
                    "live-board-date")
            with ui.row().classes("live-board-meta items-center no-wrap gap-1"):
                with ui.column().classes("live-board-summary gap-0 items-end"):
                    progress_label = ui.label(confirmation_label(complete, total)).classes("live-board-progress")
                    updated_label = ui.label(update_time_text()).classes("live-board-updated")
                with ui.button(icon="more_vert").props(
                        "flat round dense aria-label='LIVE BOARDメニュー'").classes("live-board-more"):
                    with ui.menu():
                        def reset_all():
                            live_board_review.uncheck([item['id'] for item in items])
                            reset_dialog.close()
                            refresh_progress(saved_message=False)
                            ui.notify("チェックを未確認に戻しました。引き継ぎは残っています。", type="positive")

                        with ui.dialog() as reset_dialog, ui.card().classes("home-reset-dialog"):
                            ui.label("チェックだけを未確認に戻しますか？").classes("text-lg font-bold")
                            ui.label("状態・数量・メモ・引き継ぎリストは残します。発注状況も変更しません。")
                            with ui.row().classes("w-full justify-end gap-2"):
                                ui.button("キャンセル", on_click=reset_dialog.close).props("flat no-caps")
                                ui.button("チェックをリセット", on_click=reset_all).props("color=negative no-caps")
                        ui.menu_item("チェックだけをリセット", on_click=reset_dialog.open)

        save_feedback = ui.label("チェックは毎朝4時にリセット。引き継ぎ結果は残ります。").classes("live-save-feedback").props('role=status aria-live=polite')

        def refresh_progress(saved_message=True):
            current_context()
            saved = {value["id"]: value for value in store_ops.service_prep_items(business_date, period)}
            for value in items:
                if value["id"] in saved:
                    value.update(saved[value["id"]])
                    value["reviewed"] = live_board_review.checked(value["id"])
                    if value["id"] in completion_painters:
                        completion_painters[value["id"]]()
                    if value["id"] in review_labels:
                        review_labels[value["id"]].set_text("確認済み" if value["reviewed"] else "未確認")
                    if value["id"] in actor_labels:
                        actor_labels[value["id"]].set_text(actor_text(value))
                    for status, button in status_buttons.get(value["id"], {}).items():
                        button.classes(remove="is-selected")
                        button.props(f"aria-pressed={str(selected_live_status(value) == status).lower()}")
                        if selected_live_status(value) == status:
                            button.classes(add="is-selected")
            done, all_items = counts()
            progress_label.set_text(confirmation_label(done, all_items))
            if saved_message:
                save_feedback.set_text("保存済み · " + update_time_text())
            updated_label.set_text(update_time_text())
            handover_list.refresh()
            unconfirmed_list.refresh()

        @ui.refreshable
        def unconfirmed_list():
            pending = [value for value in items if not live_board_review.checked(value["id"])]
            if not pending:
                return
            with ui.expansion("未確認の項目を確認する", icon="fact_check").classes("w-full"):
                ui.label("作業が未完了でも、確認したらそのまま記録できます。").classes("text-xs text-grey-7")
                for value in pending:
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label(value["name"]).classes("text-sm")

                        def confirm(selected=value):
                            current_context()
                            store_ops.confirm_service_prep_item(business_date, period, selected["id"])
                            record_result(selected["id"])
                            refresh_progress()

                        ui.button("この状態で確認", on_click=confirm).props("outline dense no-caps")
        unconfirmed_list()

        visible_categories = [c for c in category_names if any(i.get("area", "厨房") == c for i in items)]
        category_sections = {}
        def select_category(event):
            for name, section in category_sections.items():
                section.set_visibility(name == event.value)
        if visible_categories:
            ui.select(visible_categories, value=visible_categories[0], label="表示カテゴリー", on_change=select_category).props("outlined dense").classes("w-full q-mb-md")
        for category in category_names:
            grouped = [item for item in items if item.get("area", "厨房") == category]
            if not grouped:
                continue
            with ui.column().classes("live-board-section w-full gap-0") as category_section:
                category_sections[category] = category_section
                category_section.set_visibility(category == visible_categories[0])
                ui.label(category).classes("live-board-category").style(
                    f"--category-color:{category_colors.get(category, '#527A68')}")
                for item in grouped:
                    with ui.column().classes("live-board-item w-full gap-0"):
                        with ui.row().classes("w-full items-center justify-between no-wrap"):
                            with ui.column().classes("live-board-copy gap-0"):
                                ui.label(item["name"]).classes("live-board-name")
                                review_labels[item["id"]] = ui.label("確認済み" if item["reviewed"] else "未確認").classes("live-review-state")
                                actor_labels[item["id"]] = ui.label(actor_text(item)).classes("text-[9px] text-grey-7")
                                note_label = ui.label(item.get("note", "")).classes(
                                    "live-board-note")
                                note_label.set_visibility(bool(item.get("note")))
                            controls = ui.row().classes("live-board-controls items-center no-wrap")

                            item_type = item.get("item_type", "completion")
                            if item_type == "status":
                                buttons = {}
                                status_buttons[item["id"]] = buttons

                                def choose_status(status, selected=item, button_map=buttons):
                                    current_context()
                                    store_ops.set_service_prep_status(
                                        business_date, period, selected["id"], status)
                                    record_result(selected["id"])
                                    selected["status"] = status
                                    for key, button in button_map.items():
                                        button.classes(remove="is-selected")
                                        if key == status:
                                            button.classes(add="is-selected")
                                    refresh_progress()

                                with controls:
                                    for status, (symbol, css_name) in STATUS_META.items():
                                        label = item.get("status_labels", {}).get(status, "")
                                        with ui.column().classes("live-status-option gap-0 items-center"):
                                            button = ui.button(
                                                symbol, on_click=lambda _, value=status,
                                                fn=choose_status: fn(value)
                                            ).props("flat dense round no-caps").classes(
                                                f"live-status-button status-{css_name}")
                                            button.props(f'aria-label="状態を{symbol}にする" aria-pressed={str(selected_live_status(item) == status).lower()}')
                                            if selected_live_status(item) == status:
                                                button.classes(add="is-selected")
                                            buttons[status] = button
                                            if item.get("show_status_labels") and label:
                                                ui.label(label).classes("live-status-meaning")
                            elif item_type == "quantity":
                                quantity_label = ui.label().classes("live-quantity-value")

                                def quantity_text(value, selected=item):
                                    number = int(value) if float(value).is_integer() else value
                                    return f"{number}{selected.get('unit', '個')}"

                                quantity_label.set_text(quantity_text(item.get("quantity", 0)))

                                def change_quantity(direction, selected=item, label=quantity_label):
                                    current_context()
                                    value = float(selected.get("quantity", 0)) + (
                                        float(selected.get("step", 1)) * direction)
                                    store_ops.set_service_prep_quantity(
                                        business_date, period, selected["id"], value)
                                    record_result(selected["id"])
                                    minimum = float(selected.get("minimum_value", 0))
                                    maximum = selected.get("maximum_value")
                                    value = max(minimum, value)
                                    if maximum not in (None, ""):
                                        value = min(float(maximum), value)
                                    selected["quantity"] = value
                                    label.set_text(quantity_text(value, selected))
                                    selected["status"] = "done" if selected.get("progress_enabled") and value > minimum else "incomplete"
                                    refresh_progress()

                                with controls:
                                    quantity_label.move(controls)
                                    with ui.column().classes("live-quantity-stepper gap-0"):
                                        ui.button("＋", on_click=lambda fn=change_quantity: fn(1)).props(
                                            "flat dense aria-label='増やす'").classes("live-quantity-button")
                                        ui.button("−", on_click=lambda fn=change_quantity: fn(-1)).props(
                                            "flat dense aria-label='減らす'").classes("live-quantity-button")
                            elif item_type == "completion":
                                done_button = ui.button().props("flat dense no-caps")

                                def paint_completion(selected=item, button=done_button):
                                    checked = live_board_review.checked(selected["id"])
                                    done = checked and selected.get("status") == "done"
                                    button.set_text(("✓ 完了" if done else "未完了") if checked else "未確認")
                                    button.classes(remove="is-done is-pending")
                                    button.classes(add="is-done" if done else "is-pending")

                                def toggle_completion(selected=item, paint=paint_completion):
                                    current_context()
                                    selected["status"] = (
                                        "incomplete" if live_board_review.checked(selected["id"]) and selected.get("status") == "done" else "done")
                                    if selected.get("source") == "daily_order":
                                        store_ops.set_daily_order_check(
                                            business_date, selected["destination"],
                                            selected["status"] == "done")
                                    else:
                                        store_ops.set_service_prep_status(
                                            business_date, period, selected["id"], selected["status"])
                                    record_result(selected["id"])
                                    paint()
                                    refresh_progress()

                                completion_painters[item["id"]] = paint_completion
                                done_button.on("click", toggle_completion)
                                done_button.classes("live-completion-button")
                                done_button.move(controls)
                                paint_completion()

                            if item.get("note_enabled"):
                                with controls:
                                    with ui.button(icon="edit_note").props(
                                            "flat round dense aria-label='補足メモ'").classes(
                                                "live-note-button"):
                                        with ui.menu() as note_menu:
                                            note_menu.classes("live-note-menu")
                                            note_input = ui.input(
                                                "短文メモ", value=item.get("note", ""),
                                            ).props("outlined dense maxlength=40 counter").classes("w-full")

                                            def save_note(selected=item, field=note_input,
                                                          label=note_label, menu=note_menu):
                                                current_context()
                                                text = store_ops.set_service_prep_note(
                                                    business_date, period, selected["id"], field.value)
                                                record_result(selected["id"], mark_checked=False)
                                                selected["note"] = text
                                                label.set_text(text)
                                                label.set_visibility(bool(text))
                                                menu.close()
                                                refresh_progress()
                                                ui.notify("メモを保存しました", type="positive")

                                            ui.button("完了", on_click=save_note).props(
                                                "unelevated dense no-caps").classes("w-full")

        if order_category.get("visible", True):
            with ui.expansion("発注状況", icon="shopping_cart", value=False).classes("live-orders w-full gap-2"):
                ui.label("発注状況").classes("text-base font-bold")
                ui.label("確認件数・引き継ぎリストには含めません。").classes("text-xs text-grey-7")
                order_checks = store_ops.daily_order_checks(business_date)
                for destination in store_ops.DAILY_ORDER_DESTINATIONS:
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label(destination).classes("font-bold")
                        def save_order(event, name=destination):
                            current_context()
                            store_ops.set_daily_order_check(business_date, name, event.value)
                            updated_label.set_text(update_time_text())
                            save_feedback.set_text("保存済み · " + update_time_text())

                        ui.toggle({False: "未発注", True: "発注済み"},
                                  value=order_checks[destination], on_change=save_order).props(
                                      "unelevated no-caps").classes("live-order-select")

        if not items:
            ui.label("表示する項目はありません").classes("live-board-empty")
    board_card.move(board_expansion)

    def follow_review_day():
        today = live_board_review.day_key()
        if today != review_day['value']:
            review_day['value'] = today
            refresh_progress(saved_message=False)
            save_feedback.set_text("午前4時になったため、チェックを未確認に戻しました。引き継ぎは残っています。")

    # No reload: a note being typed stays intact across the boundary.
    ui.timer(1, follow_review_day)


    ui.add_css("""
    .live-handover-top{padding:8px 14px!important;margin-bottom:12px;border:1px solid #dce7de;border-radius:14px!important;background:#f4f7f3!important;box-shadow:none!important}.live-handover-details .q-item{min-height:36px;padding:2px 0}.live-handover-details .q-expansion-item__content{padding:4px 0}.live-handover-group{margin-top:6px}
    .live-handover,.live-orders{margin-top:18px;padding:14px;background:#f4f7f3;border:1px solid #dce7de;border-radius:14px}.live-handover-group{padding:10px;background:white;border-radius:9px}.live-handover-name{font-size:13px;overflow-wrap:anywhere}.live-orders{background:#f1f5fa}.live-order-select{width:175px;max-width:100%}
    .live-board-collapsed{overflow:hidden;border:1px solid rgba(255,255,255,.95)!important;border-radius:22px!important;background:linear-gradient(145deg,#fff,#eef4f0)!important;box-shadow:0 11px 0 #cad6cf,0 18px 28px rgba(35,58,47,.18)!important}.live-board-collapsed>.q-expansion-item__container>.q-item{min-height:76px!important;padding:0 20px!important;color:#173c30;font-size:15px;font-weight:950;letter-spacing:.04em}.live-board-collapsed .q-expansion-item__content{padding:0 8px 14px}.live-board-v2{padding:16px 14px 10px!important;border:1px solid #dfe8e2!important;border-radius:18px!important;background:rgba(255,255,255,.98)!important;color:#17352b!important;box-shadow:none!important}
    .live-board-head{padding:1px 3px 12px;border-bottom:1px solid #e5ece8}.live-board-title{font-size:22px;font-weight:950;letter-spacing:.06em}.live-board-date{font-size:10px;color:#718078;font-weight:750}.live-board-summary{margin-right:2px}.live-board-progress{padding:7px 12px;border-radius:999px;background:#173e31;color:white;font-size:13px;font-weight:950;letter-spacing:.05em}.live-board-updated{margin-top:3px;padding-right:2px;color:#718078;font-size:8px;font-weight:850;white-space:nowrap}.live-board-more{color:#60756b!important}
    .live-board-section{padding-top:15px}.live-board-category{width:100%;padding:7px 10px;color:#fff;font-size:11px;font-weight:950;letter-spacing:.08em;background:var(--category-color);border-radius:8px}.live-board-item{height:96px!important;min-height:96px!important;max-height:96px!important;padding:8px 2px;border-bottom:1px solid #edf1ef;overflow:hidden}.live-board-item>.q-row{height:79px!important;min-height:79px!important;max-height:79px!important}.live-board-copy{display:flex!important;flex:1;flex-direction:column;justify-content:center;min-width:0;max-height:76px;overflow:hidden}.live-board-name{display:-webkit-box;max-width:100%;max-height:36px;overflow:hidden;font-size:14px;font-weight:900;line-height:1.3;overflow-wrap:anywhere;-webkit-box-orient:vertical;-webkit-line-clamp:2}.live-board-note{display:-webkit-box;margin-top:3px;max-width:100%;max-height:30px;overflow:hidden;color:#a06b18;font-size:10px;font-weight:800;line-height:1.4;overflow-wrap:anywhere;-webkit-box-orient:vertical;-webkit-line-clamp:2}.live-board-controls{gap:5px!important;flex:0 0 auto;margin-left:8px}
    .live-completion-button{min-width:72px!important;min-height:42px!important;border-radius:12px!important;font-size:11px!important;font-weight:950!important}.live-completion-button.is-pending{color:#b92f36!important;background:#fde6e7!important;border:1px solid #f4b9bd!important}.live-completion-button.is-done{color:#17623e!important;background:#e2f3e9!important}
    .live-status-button{width:42px!important;height:42px!important;font-size:18px!important;font-weight:950!important;border:1px solid #dfe5e2!important;background:#fff!important}.live-status-button.status-good{color:#248455!important}.live-status-button.status-warning{color:#c68110!important}.live-status-button.status-bad{color:#ca4b4b!important}.live-status-button.is-selected{color:white!important;box-shadow:0 4px 12px rgba(30,45,38,.15)!important}.live-status-button.status-good.is-selected{background:#2b8d5d!important}.live-status-button.status-warning.is-selected{background:#d99520!important}.live-status-button.status-bad.is-selected{background:#d45555!important}.live-status-meaning{max-width:43px;font-size:7px;font-weight:800;color:#7a8580;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.live-status-option{width:43px}
    .live-board-item,.live-board-controls button,.live-note-menu{touch-action:manipulation;-webkit-tap-highlight-color:transparent}.live-quantity-stepper{overflow:hidden;border:1px solid #dce4e0;border-radius:10px;background:#f7f9f8}.live-quantity-button{width:38px!important;height:30px!important;min-height:30px!important;border-radius:0!important;color:#204b3a!important;font-size:15px!important;font-weight:900!important}.live-quantity-button+.live-quantity-button{border-top:1px solid #dce4e0!important}.live-quantity-value{min-width:54px;text-align:right;font-size:13px;font-weight:950}.live-note-button{width:38px!important;height:38px!important;color:#657a70!important}.live-note-menu{width:min(82vw,320px);padding:13px;border-radius:16px!important}.live-board-empty{padding:28px 3px;color:#78847e;font-size:12px}
    @media(max-width:390px){.live-board-v2{padding:16px 11px 10px!important}.live-board-name{font-size:13px}.live-board-controls{gap:3px!important;margin-left:5px}.live-status-button{width:38px!important;height:38px!important}.live-status-option{width:39px}.live-completion-button{min-width:67px!important}.live-quantity-value{min-width:52px;font-size:12px}.live-note-button{width:34px!important;height:34px!important}}
    """)
