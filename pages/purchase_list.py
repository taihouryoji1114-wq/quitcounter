from nicegui import ui

from core.auth import current_role, require_app_access
from core.store_ops import store_ops
from core.theme import Theme


@ui.page("/store-ops/purchase-list")
def purchase_list_page():
    if not require_app_access("store_ops"):
        return
    Theme.page("仕入れリスト｜店舗運営", app_name="store-ops")
    content = Theme.shell("仕入れリスト", "この画面を見ながら、書いてある数だけ仕入れる",
                          back_to="/store-ops", brand="店舗運営")
    with content:
        if current_role() != "owner":
            with ui.card().classes("surface-card w-full q-pa-xl text-center"):
                ui.icon("lock").classes("text-4xl text-grey-5")
                ui.label("この画面は管理者専用です").classes("text-base font-black q-mt-sm")
            return
        purchase_items = store_ops.purchase_list()
        if not purchase_items:
            with ui.card().classes("surface-card w-full q-pa-xl text-center"):
                ui.icon("shopping_basket").classes("text-5xl text-grey-4")
                ui.label("仕入れる商品はありません").classes("text-lg font-black q-mt-sm")
                ui.label("在庫確認の赤い枠に仕入れ数を入力してください").classes(
                    "text-[10px] text-grey-6 q-mt-xs")
        else:
            grouped = {}
            for item in purchase_items:
                grouped.setdefault(item.get("supplier") or "仕入れ先未設定", []).append(item)
            for supplier, items in grouped.items():
                with ui.card().classes("purchase-card w-full q-pa-lg q-mb-sm"):
                    ui.label(supplier).classes("text-[10px] font-black text-primary")
                    for item in items:
                        quantity = item["purchase_quantity"]
                        if isinstance(quantity, float) and quantity.is_integer():
                            quantity = int(quantity)
                        with ui.row().classes("purchase-row w-full items-center no-wrap"):
                            ui.checkbox(value=False).props("dense color=positive")
                            ui.label(item["name"]).classes("text-sm font-black grow")
                            ui.label(f"{quantity}{item.get('unit', '個')}").classes(
                                "text-lg font-black text-negative")
        ui.add_css("""
        .purchase-card{border-radius:22px!important;border:1px solid #E1E9E4!important;box-shadow:0 8px 24px rgba(39,55,45,.05)!important}.purchase-row{padding:12px 0;border-bottom:1px solid #EDF1EE}.purchase-row:last-child{border-bottom:0}
        """)
