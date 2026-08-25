from nicegui import ui

from core.auth import require_app_access
from core.clock import operational_date_jst, store_service_period_jst
from core.store_ops import store_ops
from core.theme import Theme
from pages.store_common import store_header_actions


@ui.page("/store-ops/checklist")
def checklist_page():
    if not require_app_access("store_ops"):
        return
    Theme.page("今日のチェック表｜店舗運営", app_name="store-ops")
    store_ops.move_kitchen_handovers_to_prep()
    record_date, period = store_ops.active_service_context(
        operational_date_jst().isoformat(), store_service_period_jst())
    period_label = "ランチ" if period == "lunch" else "ディナー"
    store_ops.ensure_service_checklist(record_date, period)
    all_prep_items = store_ops.service_prep_items(record_date, period)
    prep_items = [item for item in all_prep_items if item["status"] != "done"]
    completed_items = [item for item in all_prep_items if item["status"] == "done"]
    order_checks = store_ops.daily_order_checks(record_date)
    order_attention = store_ops.daily_order_attention(record_date)
    content = Theme.shell("今日のチェック表", f"{period_label}営業のチェック",
                          back_to="/store-ops", action=store_header_actions,
                          brand="店舗運営")
    with content:
        with ui.row().classes("cutoff-note w-full items-center justify-between gap-2"):
            ui.label(f"{record_date.replace('-', '/')}　{period_label}営業").classes("font-black")

            def advance_service():
                store_ops.advance_service_context()
                ui.navigate.to("/store-ops/checklist")

            ui.button("次の営業へ切り替え", icon="skip_next", on_click=advance_service).props(
                "unelevated dense no-caps").classes("manual-next")
        completion_target = {"kind": "", "id": "", "name": ""}
        with ui.dialog() as confirm_dialog, ui.card().classes("confirm-card q-pa-lg"):
            ui.label("完了にしますか？").classes("text-xl font-black")
            confirm_name = ui.label().classes("text-sm text-grey-7 q-mt-xs")

            def complete_item():
                if completion_target["kind"] == "prep":
                    store_ops.set_service_prep_status(
                        record_date, period, completion_target["id"], "done")
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
                store_ops.set_service_prep_status(record_date, period, item_id, "attention")
            else:
                store_ops.set_daily_order_attention(record_date, item_id, True)
            ui.navigate.to("/store-ops/checklist")

        with ui.element("div").classes("check-grid w-full q-mt-md"):
            for item in prep_items:
                attention = item["status"] == "attention"
                with ui.card().classes("check-item attention" if attention else "check-item"):
                    ui.label(item["name"]).classes("check-name")
                    ui.label(item.get("area", "厨房")).classes("check-area")
                    if item.get("choice_mode"):
                        ui.label("結果は必ず次の引き継ぎボードへ表示されます").classes(
                            "text-[8px] text-grey-6 q-mt-xs")
                        with ui.row().classes("w-full gap-1 q-mt-sm no-wrap"):
                            ui.button("あり", on_click=lambda _, value=item: (
                                store_ops.set_service_prep_choice(
                                    record_date, period, value["id"], "あり"),
                                ui.navigate.to("/store-ops/checklist")
                            )).props("unelevated dense no-caps color=positive").classes("grow")
                            ui.button("なし", on_click=lambda _, value=item: (
                                store_ops.set_service_prep_choice(
                                    record_date, period, value["id"], "なし"),
                                ui.navigate.to("/store-ops/checklist")
                            )).props("outline dense no-caps color=primary").classes("grow")
                    elif item.get("quantity_mode"):
                        quantity = ui.number(value=item.get("quantity", 0), min=0, step=1,
                                             suffix="個").props(
                                                 "outlined dense inputmode=numeric").classes(
                                                     "w-full q-mt-sm")
                        ui.label("2個以上なら引き継ぎません。0〜1個は次の営業へ引き継ぎます").classes(
                            "text-[8px] text-grey-6 q-mt-xs")
                        ui.button("個数を保存", icon="save", on_click=lambda _, value=item,
                                  field=quantity: (
                                      store_ops.set_service_prep_quantity(
                                          record_date, period, value["id"], field.value),
                                      ui.navigate.to("/store-ops/checklist")
                                  )).props("unelevated dense no-caps").classes("w-full q-mt-sm")
                    else:
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

        if completed_items:
            with ui.expansion(f"完了済み　{len(completed_items)}件", icon="task_alt",
                              value=False).classes("completed-list w-full q-mt-lg"):
                ui.label("戻したい項目をまとめて選択できます").classes(
                    "text-[10px] text-grey-6 q-mb-sm")
                selected_completed = set()
                for item in completed_items:
                    with ui.row().classes("completed-row w-full items-center no-wrap"):
                        ui.checkbox(on_change=lambda event, item_id=item["id"]: (
                            selected_completed.add(item_id) if event.value
                            else selected_completed.discard(item_id)
                        )).props("dense")
                        ui.label(item["name"]).classes("text-xs font-black grow")
                        if item.get("quantity_mode"):
                            ui.label(f"{item.get('quantity', 0)}個").classes("text-xs text-positive")
                        elif item.get("choice_mode"):
                            ui.label(item.get("choice", "")).classes("text-xs text-positive")
                ui.button("選択した項目を未完了へ戻す", icon="undo", on_click=lambda: (
                    store_ops.reset_service_prep_items(
                        record_date, period, list(selected_completed)),
                    ui.navigate.to("/store-ops/checklist")
                )).props("unelevated no-caps color=warning").classes("w-full q-mt-sm")

        ui.add_css("""
        .cutoff-note{padding:10px 12px;border-radius:13px;background:#EEF5F1;color:#527060;font-size:10px;font-weight:800}.manual-next{background:#2E7255!important;font-size:9px!important}.check-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.check-item{padding:13px!important;border-radius:18px!important;border:1px solid #E1E9E4!important;box-shadow:none!important;background:#fff!important}.check-item.attention{border:2px solid #E2A63B!important}.check-item.order{background:#F4F7FB!important}.check-name{font-size:13px;font-weight:900;line-height:1.25}.check-area{font-size:9px;color:#7A8780;margin-top:3px}.confirm-card{width:min(92vw,420px)!important;border-radius:24px!important}.all-done{border-radius:24px!important;border:1px solid #E1E9E4!important;box-shadow:none!important}.completed-list{border:1px solid #E1E9E4;border-radius:18px;background:#fff}.completed-row{padding:9px 4px;border-bottom:1px solid #EEF1EF}@media(max-width:360px){.check-grid{grid-template-columns:1fr}}
        """)
