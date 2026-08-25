from nicegui import ui

from core.auth import require_app_access, require_permission
from core.qr import data_url as qr_data_url
from core.store_ops import store_ops
from core.theme import Theme
from pages.store_common import store_header_actions


CATEGORIES = ["野菜仕入れ", "冷凍庫", "飲料", "調味料", "備品", "清掃用品", "その他"]
AREAS = ["厨房", "デシャップ", "ホール"]
STORE_LOGIN_URL = "https://quitcounter.onrender.com/store-ops/login"


@ui.page("/store-ops/settings")
def store_settings_page():
    if not require_app_access("store_ops"):
        return
    if not require_permission("store_manage", "/store-ops"):
        return
    Theme.page("登録・設定｜店舗運営", app_name="store-ops")
    content = Theme.shell(
        "登録・設定", "登録、編集、削除をひとつに",
        back_to="/store-ops", action=store_header_actions, brand="店舗運営",
    )

    def reload(message=None):
        if message:
            ui.notify(message, type="positive")
        ui.navigate.to("/store-ops/settings")

    def notify_error(error):
        ui.notify(str(error), type="negative")

    def confirm_delete(title, name, action):
        with ui.dialog() as dialog, ui.card().classes("settings-dialog q-pa-lg"):
            ui.label(title).classes("text-lg font-black")
            ui.label(name).classes("text-sm text-grey-7 q-mt-xs")
            ui.label("過去の記録は残し、今後の一覧から非表示にします").classes(
                "text-[9px] text-grey-6 q-mt-xs")

            def execute():
                try:
                    action()
                except ValueError as error:
                    notify_error(error)
                    return
                dialog.close()
                reload("削除しました")

            with ui.row().classes("w-full gap-2 q-mt-md"):
                ui.button("やめる", on_click=dialog.close).props("flat no-caps").classes("grow")
                ui.button("削除する", icon="delete", on_click=execute).props(
                    "unelevated color=negative no-caps").classes("grow")
        dialog.open()

    with content:
        with ui.card().classes("settings-hero w-full q-pa-lg q-mb-md"):
            ui.icon("tune").classes("text-3xl text-primary")
            ui.label("店舗で使う項目だけを管理").classes("text-lg font-black q-mt-sm")
            ui.label("普段の入力画面とは分けてあります").classes("text-[10px] text-grey-6")

        with ui.expansion("商品・備品を登録", icon="inventory_2", value=False).classes(
                "settings-section w-full q-mb-sm"):
            name = ui.input("商品・備品名").props("outlined dense").classes("w-full")
            category = ui.select(CATEGORIES, value="野菜仕入れ", label="分類").props(
                "outlined dense").classes("w-full q-mt-xs")
            unit = ui.select(list(store_ops.INVENTORY_UNITS), value="個", label="管理単位").props(
                "outlined dense use-input new-value-mode=add-unique").classes("w-full q-mt-xs")
            supplier = ui.input("いつもの仕入先（任意）").props("outlined dense").classes("w-full q-mt-xs")
            tracking = ui.select(
                {"count": "数量で管理", "simple": "3段階で管理"}, value="count",
                label="管理方法").props("outlined dense emit-value map-options").classes("w-full q-mt-xs")

            def add_item():
                try:
                    store_ops.add_item(name.value, category.value, unit.value,
                                       supplier.value, "", tracking.value, "", "")
                except ValueError as error:
                    notify_error(error)
                    return
                reload("商品・備品を登録しました")

            ui.button("登録する", icon="add", on_click=add_item).classes("w-full q-mt-md")

        with ui.expansion("仕込み項目を登録", icon="soup_kitchen", value=False).classes(
                "settings-section w-full q-mb-sm"):
            prep_name = ui.input("仕込み項目").props("outlined dense").classes("w-full")
            prep_area = ui.select(AREAS, value="厨房", label="場所").props(
                "outlined dense").classes("w-full q-mt-xs")

            def add_prep():
                try:
                    store_ops.add_prep_template(prep_name.value, prep_area.value)
                except ValueError as error:
                    notify_error(error)
                    return
                reload("仕込み項目を登録しました")

            ui.button("登録する", icon="add", on_click=add_prep).classes("w-full q-mt-md")

        with ui.expansion("引き継ぎ項目を登録", icon="campaign", value=False).classes(
                "settings-section w-full q-mb-md"):
            handover_name = ui.input("引き継ぎ項目").props("outlined dense").classes("w-full")
            handover_area = ui.select(AREAS, value="厨房", label="場所").props(
                "outlined dense").classes("w-full q-mt-xs")

            def add_handover():
                try:
                    store_ops.add_handover_template(handover_name.value, handover_area.value)
                except ValueError as error:
                    notify_error(error)
                    return
                reload("引き継ぎ項目を登録しました")

            ui.button("登録する", icon="add", on_click=add_handover).classes("w-full q-mt-md")

        items = store_ops.items()
        with ui.expansion(f"商品・備品の編集　{len(items)}件", icon="edit", value=False).classes(
                "settings-section w-full q-mb-sm"):
            for item in items:
                with ui.row().classes("settings-row w-full items-center no-wrap"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(item["name"]).classes("text-xs font-black")
                        ui.label(f"{item.get('category', 'その他')}・{item.get('unit', '個')}").classes(
                            "text-[9px] text-grey-6")

                    def edit_item(_, selected=item):
                        with ui.dialog() as dialog, ui.card().classes("settings-dialog q-pa-lg"):
                            ui.label("商品・備品を編集").classes("text-lg font-black q-mb-sm")
                            edit_name = ui.input("名前", value=selected["name"]).props("outlined dense").classes("w-full")
                            edit_category = ui.select(CATEGORIES, value=selected.get("category", "その他"),
                                                      label="分類").props("outlined dense").classes("w-full")
                            edit_unit = ui.select(list(store_ops.INVENTORY_UNITS),
                                                  value=selected.get("unit", "個"), label="管理単位").props(
                                                      "outlined dense use-input new-value-mode=add-unique").classes("w-full")
                            edit_supplier = ui.input("仕入先", value=selected.get("supplier", "")).props(
                                "outlined dense").classes("w-full")
                            edit_tracking = ui.select(
                                {"count": "数量で管理", "simple": "3段階で管理"},
                                value=selected.get("tracking_mode", "count"), label="管理方法").props(
                                    "outlined dense emit-value map-options").classes("w-full")

                            def save():
                                try:
                                    store_ops.update_item(selected["id"], edit_name.value,
                                                          edit_category.value, edit_unit.value,
                                                          edit_supplier.value, edit_tracking.value)
                                except ValueError as error:
                                    notify_error(error)
                                    return
                                dialog.close()
                                reload("商品・備品を更新しました")

                            ui.button("変更を保存", icon="save", on_click=save).classes("w-full q-mt-sm")
                        dialog.open()

                    ui.button(icon="edit", on_click=edit_item).props("flat round dense aria-label='編集'")
                    ui.button(icon="delete_outline", on_click=lambda _, selected=item: confirm_delete(
                        "この商品・備品を削除しますか？", selected["name"],
                        lambda: store_ops.delete_item(selected["id"]))).props(
                            "flat round dense color=negative aria-label='削除'")

        prep_items = store_ops.prep_templates()
        with ui.expansion(f"仕込み項目の編集　{len(prep_items)}件", icon="edit_note",
                          value=False).classes("settings-section w-full q-mb-sm"):
            for item in prep_items:
                with ui.row().classes("settings-row w-full items-center no-wrap"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(item["name"]).classes("text-xs font-black")
                        ui.label(item.get("area", "厨房")).classes("text-[9px] text-grey-6")

                    def edit_prep(_, selected=item):
                        with ui.dialog() as dialog, ui.card().classes("settings-dialog q-pa-lg"):
                            ui.label("仕込み項目を編集").classes("text-lg font-black q-mb-sm")
                            edit_name = ui.input("項目名", value=selected["name"]).props("outlined dense").classes("w-full")
                            edit_area = ui.select(AREAS, value=selected.get("area", "厨房"), label="場所").props(
                                "outlined dense").classes("w-full")

                            def save():
                                try:
                                    store_ops.update_prep_template(selected["id"], edit_name.value, edit_area.value)
                                except ValueError as error:
                                    notify_error(error)
                                    return
                                dialog.close()
                                reload("仕込み項目を更新しました")

                            ui.button("変更を保存", icon="save", on_click=save).classes("w-full q-mt-sm")
                        dialog.open()

                    ui.button(icon="edit", on_click=edit_prep).props("flat round dense aria-label='編集'")
                    ui.button(icon="delete_outline", on_click=lambda _, selected=item: confirm_delete(
                        "この仕込み項目を削除しますか？", selected["name"],
                        lambda: store_ops.delete_prep_template(selected["id"]))).props(
                            "flat round dense color=negative aria-label='削除'")

        handover_items = store_ops.handover_templates()
        with ui.expansion(f"引き継ぎ項目の編集　{len(handover_items)}件", icon="edit_note",
                          value=False).classes("settings-section w-full q-mb-md"):
            for item in handover_items:
                with ui.row().classes("settings-row w-full items-center no-wrap"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(item["name"]).classes("text-xs font-black")
                        ui.label(item.get("area", "厨房")).classes("text-[9px] text-grey-6")

                    def edit_handover(_, selected=item):
                        with ui.dialog() as dialog, ui.card().classes("settings-dialog q-pa-lg"):
                            ui.label("引き継ぎ項目を編集").classes("text-lg font-black q-mb-sm")
                            edit_name = ui.input("項目名", value=selected["name"]).props("outlined dense").classes("w-full")
                            edit_area = ui.select(AREAS, value=selected.get("area", "厨房"), label="場所").props(
                                "outlined dense").classes("w-full")

                            def save():
                                try:
                                    store_ops.update_handover_template(
                                        selected["id"], edit_name.value, edit_area.value)
                                except ValueError as error:
                                    notify_error(error)
                                    return
                                dialog.close()
                                reload("引き継ぎ項目を更新しました")

                            ui.button("変更を保存", icon="save", on_click=save).classes("w-full q-mt-sm")
                        dialog.open()

                    ui.button(icon="edit", on_click=edit_handover).props("flat round dense aria-label='編集'")
                    ui.button(icon="delete_outline", on_click=lambda _, selected=item: confirm_delete(
                        "この引き継ぎ項目を削除しますか？", selected["name"],
                        lambda: store_ops.delete_handover_template(selected["id"]))).props(
                            "flat round dense color=negative aria-label='削除'")

        with ui.expansion("スタッフのスマホに追加", icon="qr_code_2", value=False).classes(
                "settings-section w-full"):
            ui.label("QRコードをスタッフのスマホで読み取ります").classes(
                "text-[10px] text-grey-6 text-center w-full")
            ui.image(qr_data_url(STORE_LOGIN_URL)).classes("settings-qr q-mx-auto q-my-sm")
            ui.label("店舗用PINは初回だけ入力します").classes(
                "text-[9px] text-grey-6 text-center w-full")

            def copy_url():
                ui.run_javascript(f"navigator.clipboard.writeText('{STORE_LOGIN_URL}')")
                ui.notify("URLをコピーしました", type="positive")

            ui.button("URLをコピー", icon="content_copy", on_click=copy_url).props(
                "outline no-caps").classes("w-full")

        ui.add_css("""
        .settings-hero{border-radius:24px!important;border:1px solid #E0E8E2!important;background:linear-gradient(145deg,#EEF6F1,#FFF9EE)!important;box-shadow:none!important}
        .settings-section{border:1px solid #E0E7E2!important;border-radius:19px!important;background:#fff!important;overflow:hidden}.settings-section>.q-item{min-height:56px;font-size:13px;font-weight:900}.settings-section .q-expansion-item__content{padding:7px 13px 15px}.settings-row{padding:9px 2px;border-bottom:1px solid #EDF1EE}.settings-dialog{width:min(92vw,440px)!important;border-radius:23px!important}.settings-qr{width:210px;height:210px;border-radius:17px;background:#fff;padding:10px;border:1px solid #E1E9E4}
        """)
