from nicegui import ui

from core.auth import require_app_access
from core.clock import operational_date_jst
from core.store_ops import store_ops
from core.theme import Theme
from pages.store_common import store_header_actions


@ui.page("/store-ops/checklist")
def checklist_page():
    if not require_app_access("store_ops"):
        return
    Theme.page("今日のチェック表｜店舗運営", app_name="store-ops")
    store_ops.move_kitchen_handovers_to_prep()
    record_date = operational_date_jst().isoformat()
    store_ops.ensure_daily_checklist(record_date)
    prep_items = [item for item in store_ops.prep_items(record_date)
                  if item["status"] != "done"]
    order_checks = store_ops.daily_order_checks(record_date)
    order_attention = store_ops.daily_order_attention(record_date)
    content = Theme.shell("今日のチェック表", "完了した項目は一覧から消えます",
                          back_to="/store-ops", action=store_header_actions,
                          brand="店舗運営")
    with content:
        ui.label("毎日午前2時に新しいチェック表へ切り替わります").classes(
            "cutoff-note w-full")
        completion_target = {"kind": "", "id": "", "name": ""}
        with ui.dialog() as confirm_dialog, ui.card().classes("confirm-card q-pa-lg"):
            ui.label("完了にしますか？").classes("text-xl font-black")
            confirm_name = ui.label().classes("text-sm text-grey-7 q-mt-xs")

            def complete_item():
                if completion_target["kind"] == "prep":
                    store_ops.set_prep_status(record_date, completion_target["id"], "done")
                else:
                    store_ops.set_daily_order_check(
                        record_date, completion_target["id"], True)
                confirm_dialog.close()
                ui.navigate.to("/store-ops/checklist")

            with ui.row().classes("w-full gap-2 q-mt-md"):
                ui.button("戻る", on_click=confirm_dialog.close).props("flat").classes("grow")
                ui.button("完了にする", icon="check", on_click=complete_item).props(
                    "unelevated color=positive").classes("grow")

        def ask_complete(kind, item_id, name):
            completion_target.update(kind=kind, id=item_id, name=name)
            confirm_name.set_text(name)
            confirm_dialog.open()

        def mark_attention(kind, item_id):
            if kind == "prep":
                store_ops.set_prep_status(record_date, item_id, "attention")
            else:
                store_ops.set_daily_order_attention(record_date, item_id, True)
            ui.navigate.to("/store-ops/checklist")

        with ui.element("div").classes("check-grid w-full q-mt-md"):
            for item in prep_items:
                attention = item["status"] == "attention"
                with ui.card().classes("check-item attention" if attention else "check-item"):
                    ui.label(item["name"]).classes("check-name")
                    ui.label(item.get("area", "厨房")).classes("check-area")
                    with ui.row().classes("w-full gap-1 q-mt-sm no-wrap"):
                        ui.button("完了", icon="check", on_click=lambda _, value=item: ask_complete(
                            "prep", value["id"], value["name"])).props(
                                "unelevated dense no-caps color=positive").classes("grow")
                        ui.button(icon="change_history", on_click=lambda _, value=item: mark_attention(
                            "prep", value["id"])).props(
                                "flat dense round color=warning aria-label='注意として残す'")
            for destination in store_ops.DAILY_ORDER_DESTINATIONS:
                if order_checks[destination]:
                    continue
                attention = order_attention[destination]
                with ui.card().classes("check-item order attention" if attention else "check-item order"):
                    ui.label(destination).classes("check-name")
                    ui.label("発注").classes("check-area")
                    with ui.row().classes("w-full gap-1 q-mt-sm no-wrap"):
                        ui.button("完了", icon="check", on_click=lambda _, name=destination: ask_complete(
                            "order", name, f"{name}への発注")).props(
                                "unelevated dense no-caps color=positive").classes("grow")
                        ui.button(icon="change_history", on_click=lambda _, name=destination: mark_attention(
                            "order", name)).props(
                                "flat dense round color=warning aria-label='注意として残す'")

        if not prep_items and all(order_checks.values()):
            with ui.card().classes("all-done w-full q-pa-xl text-center"):
                ui.icon("task_alt").classes("text-6xl text-positive")
                ui.label("今日のチェックはすべて完了！").classes("text-xl font-black q-mt-sm")

        ui.add_css("""
        .cutoff-note{padding:10px 12px;border-radius:13px;background:#EEF5F1;color:#527060;font-size:10px;font-weight:800}.check-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.check-item{padding:13px!important;border-radius:18px!important;border:1px solid #E1E9E4!important;box-shadow:none!important;background:#fff!important}.check-item.attention{border:2px solid #E2A63B!important}.check-item.order{background:#F4F7FB!important}.check-name{font-size:13px;font-weight:900;line-height:1.25}.check-area{font-size:9px;color:#7A8780;margin-top:3px}.confirm-card{width:min(92vw,420px)!important;border-radius:24px!important}.all-done{border-radius:24px!important;border:1px solid #E1E9E4!important;box-shadow:none!important}@media(max-width:360px){.check-grid{grid-template-columns:1fr}}
        """)
