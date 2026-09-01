from nicegui import ui

from core.auth import current_role, has_permission, require_app_access
from core.clock import operational_date_jst
from core.store_ops import store_ops
from core.theme import Theme
from pages.store_common import store_header_actions


def section_shell(title, subtitle):
    Theme.page(f"{title}｜店舗運営", app_name="store-ops")
    return Theme.shell(title, subtitle, back_to="/store-ops", action=store_header_actions,
                       brand="店舗運営")


@ui.page("/store-ops/handover")
def handover_page():
    if not require_app_access("store_ops"):
        return
    record_date = operational_date_jst().isoformat()
    notes = store_ops.handovers(record_date)
    content = section_shell("今日の引き継ぎ", "自由記入で共有する")
    with content:
        message = ui.textarea("引き継ぎ内容").props("outlined autogrow").classes("w-full")
        area = ui.toggle({"ホール": "ホール", "デシャップ": "デシャップ", "厨房": "厨房"},
                         value="厨房").props("unelevated spread no-caps").classes("w-full q-mt-sm")

        def add_note():
            try:
                store_ops.add_handover(record_date, message.value, area.value)
            except ValueError as error:
                ui.notify(str(error), type="negative")
                return
            ui.navigate.to("/store-ops/handover")

        ui.button("引き継ぎを追加", icon="send", on_click=add_note).classes("w-full q-mt-md")
        ui.separator().classes("q-my-lg")
        for note in reversed(notes):
            with ui.card().classes("surface-card w-full q-pa-lg q-mb-sm"):
                ui.label(note["area"]).classes("text-[9px] font-black text-primary")
                ui.label(note["message"]).classes("text-sm font-bold q-mt-xs")


@ui.page("/store-ops/order-requests")
def order_requests_page():
    if not require_app_access("store_ops"):
        return
    requests = store_ops.order_requests()
    open_requests = [item for item in requests if not item.get("completed", False)]
    completed_requests = [item for item in requests if item.get("completed", False)]
    can_manage = has_permission("store_manage")
    content = section_shell("発注依頼", "気づいたその場で、発注してほしい物を共有")
    with content:
        message = ui.textarea("発注してほしい物").props(
            "outlined autogrow placeholder='例：キッチンペーパー 2箱'").classes("w-full")

        def add_request():
            try:
                store_ops.add_order_request(message.value)
            except ValueError as error:
                ui.notify(str(error), type="negative")
                return
            ui.navigate.to("/store-ops/order-requests")

        ui.button("発注依頼を追加", icon="send", on_click=add_request).classes("w-full q-mt-sm")
        ui.label(f"未対応　{len(open_requests)}件").classes("text-base font-black q-mt-xl q-mb-sm")
        if not open_requests:
            ui.label("未対応の発注依頼はありません").classes("request-empty w-full")
        for request in open_requests:
            with ui.card().classes("request-card w-full q-pa-md q-mb-sm"):
                with ui.row().classes("w-full items-center no-wrap"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(request["message"]).classes("text-sm font-black")
                        ui.label(str(request.get("created_at", ""))[:16].replace("T", " ")).classes(
                            "text-[9px] text-grey-6 q-mt-xs")
                    if can_manage:
                        ui.button("対応済み", icon="check", on_click=lambda _, item_id=request["id"]: (
                            store_ops.set_order_request_completed(item_id, True),
                            ui.navigate.to("/store-ops/order-requests")
                        )).props("unelevated dense no-caps color=positive")
                    else:
                        ui.label("管理者対応").classes("request-manager-badge")
        if completed_requests:
            with ui.expansion(f"対応済み　{len(completed_requests)}件", icon="task_alt",
                              value=False).classes("request-completed w-full q-mt-lg"):
                for request in completed_requests:
                    with ui.row().classes("w-full items-center no-wrap q-py-sm"):
                        ui.label(request["message"]).classes("text-xs text-grey-7 grow")
                        if can_manage:
                            ui.button("戻す", icon="undo", on_click=lambda _, item_id=request["id"]: (
                                store_ops.set_order_request_completed(item_id, False),
                                ui.navigate.to("/store-ops/order-requests")
                            )).props("flat dense no-caps")
                        if current_role() == "owner":
                            ui.button(icon="delete_outline", on_click=lambda _, item_id=request["id"]: (
                                store_ops.delete_order_request(item_id),
                                ui.navigate.to("/store-ops/order-requests")
                            )).props("flat round dense color=negative aria-label='削除'")
        ui.add_css("""
        .request-card{border:1px solid #E1E9E4!important;border-radius:18px!important;box-shadow:none!important}
        .request-empty{padding:22px;border:1px dashed #C9D4CD;border-radius:18px;text-align:center;color:#7C8982;font-size:11px}
        .request-completed{border:1px solid #E1E9E4;border-radius:18px;background:#fff}
        .request-manager-badge{font-size:8px;font-weight:900;color:#9B6C21;background:#FFF1D5;padding:6px 8px;border-radius:999px;white-space:nowrap}
        """)


@ui.page("/store-ops/inventory")
def inventory_page():
    if not require_app_access("store_ops"):
        return
    items = store_ops.items()
    is_owner = current_role() == "owner"
    reset_at = store_ops.inventory_check_reset_at()
    content = section_shell("在庫確認", "現在の在庫をまとめて入力")
    with content:
        fields = []
        grouped = {}
        for item in items:
            grouped.setdefault(item.get("category", "その他"), []).append(item)
        for category, category_items in grouped.items():
            with ui.expansion(f"{category}　{len(category_items)}品", icon="folder",
                              value=False).classes("surface-card w-full q-mb-sm"):
                with ui.element("div").classes("inventory-grid-new w-full"):
                    for item in category_items:
                        last_check = str(item.get("last_inventory_check_at", ""))
                        was_reset = bool(reset_at and (not last_check or last_check <= reset_at))
                        with ui.card().classes("inventory-item-new"):
                            with ui.column().classes("gap-0 w-full min-w-0"):
                                ui.label(item["name"]).classes("inventory-item-name")
                                minimum = item.get("reorder_point")
                                unit = item.get("unit", "個")
                                if minimum is not None:
                                    minimum_text = (str(int(minimum)) if float(minimum).is_integer()
                                                    else str(minimum))
                                    ui.label(f"最低 {minimum_text}{unit}").classes(
                                        "minimum-stock-mark")
                                else:
                                    ui.label(f"単位 {unit}").classes("inventory-unit")
                            if item.get("tracking_mode") == "count":
                                field = ui.number(value=None if was_reset else item.get("current_stock"), step=.1,
                                                  suffix=item.get("unit", "個")).props(
                                                      "outlined dense inputmode=decimal").classes("stock-field")
                                fields.append((item["id"], "count", field))
                            else:
                                field = ui.select({"enough": "十分", "low": "少ない", "out": "なし"},
                                                  value=None if was_reset else item.get("status", "enough")).props(
                                                      "outlined dense options-dense").classes("stock-field")
                                fields.append((item["id"], "status", field))

        def save_all():
            updates = [{"item_id": item_id, kind: field.value}
                       for item_id, kind, field in fields if field.value not in (None, "")]
            try:
                store_ops.save_inventory_check(updates)
            except ValueError as error:
                ui.notify(str(error), type="negative")
                return
            ui.notify("在庫を保存しました", type="positive")

        ui.button("まとめて保存", icon="save", on_click=save_all).classes("w-full q-mt-md")
        with ui.dialog() as reset_dialog, ui.card().classes("surface-card w-80 q-pa-lg"):
            ui.label("在庫確認をリセットしますか？").classes("text-lg font-black")
            ui.label("現在の入力欄だけを未入力に戻します。商品・確認履歴・管理者の仕入れ予定は消えません。").classes(
                "text-xs text-grey-7 q-mt-sm")

            def reset_check():
                store_ops.reset_inventory_check()
                reset_dialog.close()
                ui.navigate.to("/store-ops/inventory")

            with ui.row().classes("w-full gap-2 q-mt-md"):
                ui.button("戻る", on_click=reset_dialog.close).props("flat").classes("grow")
                ui.button("リセット", icon="restart_alt", on_click=reset_check).props(
                    "unelevated color=negative").classes("grow")

        ui.button("在庫確認をリセット", icon="restart_alt", on_click=reset_dialog.open).props(
            "outline color=negative no-caps").classes("w-full q-mt-sm")
        if is_owner:
            ui.button("仕入れリストを開く", icon="shopping_basket", on_click=lambda: ui.navigate.to(
                "/store-ops/purchase-list")).props("outline no-caps").classes("w-full q-mt-sm")
        ui.add_css("""
        .inventory-grid-new{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;padding:7px 1px 10px}
        .inventory-item-new{display:flex!important;flex-direction:column!important;justify-content:space-between!important;min-width:0!important;min-height:132px;padding:11px!important;border-radius:16px!important;border:1px solid #E1E9E4!important;box-shadow:none!important;background:#fff!important}
        .inventory-item-name{display:-webkit-box;min-height:32px;max-height:32px;overflow:hidden;overflow-wrap:anywhere;-webkit-box-orient:vertical;-webkit-line-clamp:2;font-size:11px;font-weight:950;line-height:1.4;color:#17382C}
        .inventory-unit{margin-top:3px;font-size:8px;color:#8A9690}
        .stock-field{width:100%!important;margin-top:8px}.stock-field .q-field__control{min-height:40px!important;height:40px!important}.stock-field input{font-weight:900!important}
        .minimum-stock-mark{display:inline-flex;width:max-content;max-width:100%;margin-top:3px;padding:2px 6px;border-radius:999px;background:#FFF0CC;color:#8A5A08;font-size:8px;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        @media(min-width:760px){.inventory-grid-new{grid-template-columns:repeat(3,minmax(0,1fr))}.inventory-item-new{min-height:142px}.inventory-item-name{font-size:13px}}
        """)


@ui.page("/store-ops/hygiene")
def hygiene_page():
    if not require_app_access("store_ops"):
        return
    record_date = operational_date_jst().isoformat()
    record = store_ops.hygiene_record(record_date)
    content = section_shell("温度・衛生", "冷蔵庫・冷凍庫と衛生状況を記録")
    with content:
        temperatures = {}
        for name in store_ops.TEMPERATURE_LOCATIONS:
            temperatures[name] = ui.number(name, value=record["temperatures"][name], step=.1).props(
                "outlined dense suffix=℃ inputmode=decimal").classes("w-full q-mb-xs")
        labels = {"receiving": "届いた食材に問題なし", "equipment": "器具の洗浄・消毒",
                  "toilet": "トイレの清掃・消毒", "handwash": "手洗いを実施"}
        checks = {key: ui.checkbox(label, value=record["checks"][key]).classes("w-full")
                  for key, label in labels.items()}
        note = ui.input("気になったこと（任意）", value=record["note"]).props(
            "outlined dense").classes("w-full q-mt-sm")

        def save():
            store_ops.save_hygiene(record_date,
                                   {key: field.value for key, field in temperatures.items()},
                                   {key: field.value for key, field in checks.items()}, note.value)
            ui.notify("温度・衛生記録を保存しました", type="positive")

        ui.button("保存", icon="save", on_click=save).classes("w-full q-mt-md")
