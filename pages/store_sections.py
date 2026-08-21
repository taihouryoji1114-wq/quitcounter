from nicegui import ui

from core.auth import current_role, require_app_access
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


@ui.page("/store-ops/inventory")
def inventory_page():
    if not require_app_access("store_ops"):
        return
    items = store_ops.items()
    is_owner = current_role() == "owner"
    record_date = operational_date_jst().isoformat()
    purchase_quantities = store_ops.purchase_quantities(record_date)
    content = section_shell("在庫確認", "現在の在庫をまとめて入力")
    with content:
        fields, purchase_fields = [], []
        grouped = {}
        for item in items:
            grouped.setdefault(item.get("category", "その他"), []).append(item)
        for category, category_items in grouped.items():
            with ui.expansion(f"{category}　{len(category_items)}品", icon="folder",
                              value=False).classes("surface-card w-full q-mb-sm"):
                for item in category_items:
                    with ui.row().classes("inventory-row-new w-full items-center no-wrap"):
                        with ui.column().classes("gap-0 grow min-w-0"):
                            ui.label(item["name"]).classes("text-xs font-black")
                            ui.label(f"単位 {item.get('unit', '個')}").classes("text-[8px] text-grey-6")
                        if is_owner:
                            buy = ui.number(value=purchase_quantities.get(item["id"]),
                                            placeholder="仕入", step=.1).props(
                                                "outlined dense inputmode=decimal").classes("buy-field")
                            purchase_fields.append((item["id"], buy))
                        if item.get("tracking_mode") == "count":
                            field = ui.number(value=item.get("current_stock"), step=.1,
                                              suffix=item.get("unit", "個")).props(
                                                  "outlined dense inputmode=decimal").classes("stock-field")
                            fields.append((item["id"], "count", field))
                        else:
                            field = ui.select({"enough": "十分", "low": "少ない", "out": "なし"},
                                              value=item.get("status", "enough")).props(
                                                  "outlined dense options-dense").classes("stock-field")
                            fields.append((item["id"], "status", field))

        def save_all():
            updates = [{"item_id": item_id, kind: field.value}
                       for item_id, kind, field in fields if field.value not in (None, "")]
            try:
                store_ops.save_inventory_check(updates)
                if is_owner:
                    store_ops.save_purchase_quantities(
                        {item_id: field.value for item_id, field in purchase_fields}, record_date)
            except ValueError as error:
                ui.notify(str(error), type="negative")
                return
            ui.notify("在庫を保存しました", type="positive")

        ui.button("まとめて保存", icon="save", on_click=save_all).classes("w-full q-mt-md")
        if is_owner:
            ui.button("仕入れリストを開く", icon="shopping_basket", on_click=lambda: ui.navigate.to(
                "/store-ops/purchase-list")).props("outline no-caps").classes("w-full q-mt-sm")
        ui.add_css(".inventory-row-new{padding:9px 2px;border-bottom:1px solid #EDF1EE;gap:5px}.stock-field{width:100px}.buy-field{width:60px}.buy-field input{color:#C84949!important;font-weight:900!important}")


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
