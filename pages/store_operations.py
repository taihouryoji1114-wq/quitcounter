from nicegui import ui

from core.auth import require_login
from core.clock import today_jst
from core.store_ops import store_ops
from core.theme import Theme


@ui.page("/store-ops")
def store_operations_page():
    if not require_login():
        return
    Theme.page("店舗運営｜R-BASE", app_name="store-ops")
    content = Theme.shell(
        "店舗運営", "不足に気づき、そのまま発注へ",
        back_to="/", brand="R-BASE",
    )
    items = store_ops.items()
    orders = store_ops.order_list()

    def reload(message=None):
        if message:
            ui.notify(message, type="positive")
        ui.navigate.to("/store-ops")

    with content:
        with ui.dialog() as add_dialog, ui.card().classes("store-dialog q-pa-lg"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("商品を登録").classes("text-xl font-black")
                ui.button(icon="close", on_click=add_dialog.close).props("flat round")
            name = ui.input("商品・備品名").props("outlined dense").classes("w-full")
            category = ui.select(["食材", "飲料", "調味料", "消耗品", "清掃用品", "その他"],
                                 value="食材", label="分類").props("outlined dense").classes("w-full q-mt-xs")
            unit = ui.input("単位", value="個").props("outlined dense").classes("w-full q-mt-xs")
            supplier = ui.input("いつもの仕入先（任意）").props("outlined dense").classes("w-full q-mt-xs")
            order_quantity = ui.input("いつもの発注量（例：2箱）").props("outlined dense").classes("w-full q-mt-xs")

            def add_item():
                try:
                    store_ops.add_item(name.value, category.value, unit.value,
                                       supplier.value, order_quantity.value)
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                add_dialog.close()
                reload("登録しました")
            ui.button("登録する", icon="add", on_click=add_item).classes("w-full q-mt-md")

        with ui.card().classes("store-hero w-full q-pa-lg text-white"):
            with ui.row().classes("w-full items-start justify-between no-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label("今、補充が必要").classes("text-[10px] opacity-75")
                    ui.label(f"{len(orders)}品").classes("text-4xl font-black q-mt-xs")
                    ui.label("気づいた人が『少ない』『なし』を押すだけ").classes(
                        "text-[9px] opacity-75 q-mt-sm")
                ui.icon("inventory_2").classes("text-4xl opacity-70")
            with ui.row().classes("w-full gap-2 q-mt-md"):
                ui.button("商品を追加", icon="add", on_click=add_dialog.open).props(
                    "unelevated no-caps").classes("store-hero-button grow")

        with ui.expansion(f"不足・発注リスト　{len(orders)}品", icon="shopping_cart",
                          value=bool(orders)).classes("store-panel w-full q-mt-sm"):
            if not orders:
                ui.label("現在、補充が必要なものはありません").classes(
                    "text-sm text-positive font-bold q-pa-md")
            else:
                for item in orders:
                    with ui.card().classes("order-card w-full q-pa-md q-mb-xs"):
                        with ui.row().classes("w-full items-center justify-between no-wrap"):
                            with ui.column().classes("gap-0 min-w-0"):
                                ui.label(item["name"]).classes("text-sm font-black")
                                detail = "・".join(value for value in (
                                    item["supplier"],
                                    f"発注 {item['order_quantity']}" if item["order_quantity"] else "",
                                ) if value)
                                ui.label(detail or "仕入先・発注量は未設定").classes(
                                    "text-[9px] text-grey-6 q-mt-xs")
                            status_label = "在庫なし" if item["status"] == "out" else "残り少ない"
                            ui.label(status_label).classes(
                                "stock-pill stock-out" if item["status"] == "out" else "stock-pill stock-low")
                        if item["order_state"] == "needed":
                            ui.button("発注済みにする", icon="send",
                                      on_click=lambda _, item_id=item["id"]: (
                                          store_ops.mark_ordered(item_id), reload("発注済みにしました")
                                      )).props("flat dense no-caps").classes("w-full q-mt-sm")
                        else:
                            with ui.row().classes("w-full items-center justify-between q-mt-sm"):
                                ui.label("発注済み").classes("text-[10px] font-bold text-primary")
                                ui.button("入荷した", icon="done",
                                          on_click=lambda _, item_id=item["id"]: (
                                              store_ops.receive(item_id), reload("入荷を反映しました")
                                          )).props("flat dense no-caps")

        with ui.expansion("在庫を確認", icon="checklist", value=True).classes(
            "store-panel w-full q-mt-sm"):
            if not items:
                ui.label("最初の商品を登録してください").classes("text-sm text-grey-6 q-pa-md")
            categories = []
            for item in items:
                if item["category"] not in categories:
                    categories.append(item["category"])
            for category_name in categories:
                ui.label(category_name).classes("category-title")
                for item in [value for value in items if value["category"] == category_name]:
                    with ui.row().classes("inventory-row w-full items-center no-wrap"):
                        with ui.column().classes("gap-0 inventory-name"):
                            ui.label(item["name"]).classes("text-xs font-black")
                            if item["supplier"]:
                                ui.label(item["supplier"]).classes("text-[8px] text-grey-6")
                        for status, label in (("enough", "ある"), ("low", "少ない"), ("out", "なし")):
                            active = item["status"] == status
                            ui.button(label, on_click=lambda _, item_id=item["id"], value=status: (
                                store_ops.set_status(item_id, value), reload()
                            )).props("unelevated dense no-caps").classes(
                                f"stock-button {'active-' + status if active else ''}")

        today = today_jst().isoformat()
        hygiene = store_ops.hygiene_record(today)
        with ui.expansion("今日の温度・衛生チェック", icon="health_and_safety",
                          value=not store_ops.hygiene_complete(today)).classes(
            "store-panel w-full q-mt-sm"):
            ui.label("温度").classes("text-xs font-black q-mb-xs")
            temperature_inputs = {}
            with ui.element("div").classes("temperature-grid w-full"):
                for appliance in ("冷蔵庫1", "冷蔵庫2", "冷凍庫"):
                    temperature_inputs[appliance] = ui.number(
                        appliance, value=hygiene["temperatures"][appliance], step=.1
                    ).props("outlined dense suffix=℃ inputmode=decimal")
            ui.label("衛生チェック").classes("text-xs font-black q-mt-md q-mb-xs")
            check_labels = {
                "receiving": "届いた食材に問題なし", "equipment": "器具の洗浄・消毒",
                "toilet": "トイレの清掃・消毒", "handwash": "手洗いを実施",
            }
            check_inputs = {key: ui.checkbox(label, value=hygiene["checks"][key]).classes(
                "w-full hygiene-check") for key, label in check_labels.items()}
            note = ui.input("気になったこと（任意）", value=hygiene["note"]).props(
                "outlined dense").classes("w-full q-mt-xs")

            def save_hygiene():
                try:
                    store_ops.save_hygiene(
                        today, {key: field.value for key, field in temperature_inputs.items()},
                        {key: field.value for key, field in check_inputs.items()}, note.value,
                    )
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                reload("今日の衛生記録を保存しました")
            ui.button("今日の記録を保存", icon="save", on_click=save_hygiene).classes(
                "w-full q-mt-md")

        with ui.card().classes("future-card w-full q-pa-md q-mt-sm"):
            ui.label("次の開発").classes("text-[9px] font-black text-primary")
            ui.label("仕込み状況・引き継ぎ").classes("text-base font-black q-mt-xs")
            ui.label("その後、タスク・清掃管理・マニュアル・行動指針へ広げます").classes(
                "text-[9px] text-grey-6 q-mt-xs")

        ui.add_css("""
        .store-dialog{width:min(92vw,440px)!important;border-radius:24px!important}.store-hero{border:0!important;border-radius:27px!important;background:linear-gradient(145deg,#173D30,#3D755D 65%,#C18A45 145%)!important;box-shadow:0 16px 38px rgba(26,65,48,.22)!important}.store-hero-button{background:rgba(255,255,255,.94)!important;color:#285941!important;border-radius:13px!important}.store-panel{border-radius:19px!important;background:#fff!important;border:1px solid #E1E9E4!important}.store-panel .q-item{min-height:52px!important}.order-card{border-radius:16px!important;border:1px solid #E4EAE6!important;box-shadow:none!important}.stock-pill{padding:5px 8px;border-radius:999px;font-size:8px;font-weight:900;white-space:nowrap}.stock-out{background:#FBE4E4;color:#A43D45}.stock-low{background:#FFF0CE;color:#966117}.category-title{font-size:10px;font-weight:900;color:#527060;padding:13px 4px 5px}.inventory-row{gap:5px;padding:8px 2px;border-bottom:1px solid #EDF1EE}.inventory-name{flex:1;min-width:70px}.stock-button{min-width:45px!important;border-radius:11px!important;background:#F2F4F3!important;color:#66726C!important;font-size:9px!important}.active-enough{background:#DFF2E7!important;color:#267149!important}.active-low{background:#FFF0CE!important;color:#966117!important}.active-out{background:#FBE2E2!important;color:#A43D45!important}.temperature-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.temperature-grid .q-field__label{font-size:9px!important}.hygiene-check{padding:4px 7px;border-radius:11px;background:#F5F7F5;margin-bottom:4px}.hygiene-check .q-checkbox__label{font-size:10px}.future-card{border-radius:18px!important;background:linear-gradient(145deg,#F0F6F2,#FFF8EA)!important;border:1px solid #E0E9E3!important;box-shadow:none!important}
        """)
