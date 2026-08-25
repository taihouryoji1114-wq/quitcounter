from nicegui import app, ui

from core.auth import current_role, has_permission, log_out


MENU_ITEMS = (
    ("今日のチェック表", "checklist", "/store-ops/checklist"),
    ("在庫確認", "inventory_2", "/store-ops/inventory"),
    ("仕入れリスト", "shopping_basket", "/store-ops/purchase-list"),
    ("温度・衛生", "health_and_safety", "/store-ops/hygiene"),
    ("自由引き継ぎ", "campaign", "/store-ops/handover"),
    ("発注依頼", "add_shopping_cart", "/store-ops/order-requests"),
    ("登録・設定", "settings", "/store-ops/settings"),
)


def store_header_actions():
    with ui.row().classes("gap-0"):
        if current_role() == "owner" and app.storage.user.get("return_to_chankocchi"):
            ui.button(icon="pets", on_click=lambda: ui.navigate.to("/chankocchi")).props(
                "flat round aria-label='ちゃんこっちへ戻る'").classes("text-amber-8")
        ui.button(icon="menu", on_click=lambda: open_store_menu()).props(
            "flat round aria-label='メニュー'").classes("text-grey-8")
        ui.button(icon="logout", on_click=lambda: log_out("/store-ops/login")).props(
            "flat round aria-label='ログアウト'").classes("text-grey-8")


def open_store_menu():
    with ui.dialog() as dialog, ui.card().classes("store-menu-dialog q-pa-lg"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("店舗メニュー").classes("text-xl font-black")
            ui.button(icon="close", on_click=dialog.close).props("flat round")
        ui.button("ホーム", icon="home", on_click=lambda: ui.navigate.to("/store-ops")).props(
            "flat no-caps align=left").classes("w-full")
        for label, icon, path in MENU_ITEMS:
            if path == "/store-ops/purchase-list" and current_role() != "owner":
                continue
            if label == "登録・設定" and not has_permission("store_manage"):
                continue
            ui.button(label, icon=icon, on_click=lambda _, target=path: ui.navigate.to(target)).props(
                "flat no-caps align=left").classes("w-full")
    dialog.open()
    ui.add_css(".store-menu-dialog{width:min(92vw,420px)!important;border-radius:24px!important}")


def app_card(title, subtitle, icon, path, accent):
    with ui.card().classes("store-app-card cursor-pointer q-pa-lg").on(
            "click", lambda _, target=path: ui.navigate.to(target)):
        ui.icon(icon).classes(f"text-4xl {accent}")
        ui.label(title).classes("text-lg font-black q-mt-sm")
        ui.label(subtitle).classes("text-[10px] text-grey-6 q-mt-xs")
