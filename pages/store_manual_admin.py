from nicegui import ui

from core.auth import require_app_access, require_permission
from core.store_manual import store_manual
from core.theme import Theme
from pages.store_common import store_header_actions


@ui.page("/store-ops/settings/manuals")
def store_manual_admin_page():
    if not require_app_access("store_ops"):
        return
    if not require_permission("store_manage", "/store-ops"):
        return
    Theme.page("マニュアル設定｜店舗運営", app_name="store-ops")
    content = Theme.shell("マニュアル設定", "カテゴリーと手順を自由に追加",
                          back_to="/store-ops/settings", action=store_header_actions,
                          brand="店舗運営")

    def reload(message):
        ui.notify(message, type="positive")
        ui.navigate.to("/store-ops/settings/manuals")

    with content:
        categories = store_manual.categories()
        with ui.expansion("カテゴリーを追加", icon="create_new_folder", value=not categories).classes(
                "manual-admin-section w-full q-mb-sm"):
            category_name = ui.input("カテゴリー名").props("outlined dense maxlength=30").classes("w-full")
            category_color = ui.color_input("カテゴリー色", value="#E8F2EC").classes("w-full")
            category_icon = ui.input("アイコン名", value="menu_book").props("outlined dense").classes("w-full")

            def add_category():
                try:
                    store_manual.add_category(category_name.value, category_color.value,
                                              category_icon.value)
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                reload("カテゴリーを追加しました")
            ui.button("追加", icon="add", on_click=add_category).classes("w-full")

        if categories:
            with ui.expansion(f"カテゴリー管理　{len(categories)}件", icon="folder",
                              value=False).classes("manual-admin-section w-full q-mb-sm"):
                for category in categories:
                    with ui.row().classes("manual-admin-row w-full items-center no-wrap"):
                        ui.icon(category.get("icon", "menu_book")).style(
                            f"color:{category.get('color', '#557')}" )
                        ui.label(category["name"]).classes("grow text-xs font-black")
                        ui.button(icon="arrow_upward", on_click=lambda _, value=category: (
                            store_manual.move_category(value["id"], -1), reload("順番を変更しました")
                        )).props("flat round dense")
                        ui.button(icon="arrow_downward", on_click=lambda _, value=category: (
                            store_manual.move_category(value["id"], 1), reload("順番を変更しました")
                        )).props("flat round dense")

        with ui.expansion("新しいマニュアルを追加", icon="note_add", value=False).classes(
                "manual-admin-section w-full q-mb-sm"):
            title = ui.input("マニュアル名").props("outlined dense maxlength=60").classes("w-full")
            category = ui.select({value["id"]: value["name"] for value in categories},
                                 label="カテゴリー").props("outlined dense emit-value map-options").classes("w-full")
            summary = ui.textarea("最初に伝える結論").props("outlined autogrow maxlength=180").classes("w-full")
            steps = ui.textarea("手順（1行に1工程）").props("outlined autogrow").classes("w-full")
            caution = ui.textarea("注意点").props("outlined autogrow maxlength=300").classes("w-full")
            image_url = ui.input("写真URL（任意）").props("outlined dense").classes("w-full")
            quiz_note = ui.input("関連するちゃんはや問題・要点（任意）").props(
                "outlined dense maxlength=200").classes("w-full")
            visible = ui.switch("スタッフに表示", value=True)

            def add_manual():
                try:
                    store_manual.add_manual(title.value, category.value, summary.value, steps.value,
                                            caution.value, image_url.value, quiz_note.value,
                                            visible.value)
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                reload("マニュアルを追加しました")
            ui.button("マニュアルを追加", icon="add", on_click=add_manual).classes("w-full")

        manuals = store_manual.manuals(include_hidden=True)
        with ui.expansion(f"登録済みマニュアル　{len(manuals)}件", icon="edit_note",
                          value=False).classes("manual-admin-section w-full"):
            if not manuals:
                ui.label("まだ登録されていません").classes("text-xs text-grey-6 q-pa-md")
            for manual in manuals:
                with ui.row().classes("manual-admin-row w-full items-center no-wrap"):
                    with ui.column().classes("grow gap-0 min-w-0"):
                        ui.label(manual["title"]).classes("text-xs font-black")
                        category_name = next((value["name"] for value in categories
                                              if value["id"] == manual.get("category_id")), "未分類")
                        ui.label(category_name).classes("text-[9px] text-grey-6")

                    def edit(_, selected=manual):
                        with ui.dialog() as dialog, ui.card().classes("manual-admin-dialog q-pa-lg"):
                            ui.label("マニュアルを編集").classes("text-lg font-black")
                            e_title = ui.input("マニュアル名", value=selected["title"]).props("outlined dense").classes("w-full")
                            e_category = ui.select({value["id"]: value["name"] for value in categories},
                                                   value=selected.get("category_id"), label="カテゴリー").props("outlined dense emit-value map-options").classes("w-full")
                            e_summary = ui.textarea("結論", value=selected.get("summary", "")).props("outlined autogrow").classes("w-full")
                            e_steps = ui.textarea("手順（1行に1工程）", value="\n".join(selected.get("steps", []))).props("outlined autogrow").classes("w-full")
                            e_caution = ui.textarea("注意点", value=selected.get("caution", "")).props("outlined autogrow").classes("w-full")
                            e_image = ui.input("写真URL", value=selected.get("image_url", "")).props("outlined dense").classes("w-full")
                            e_quiz = ui.input("ちゃんはや連携メモ", value=selected.get("quiz_note", "")).props("outlined dense").classes("w-full")
                            e_visible = ui.switch("スタッフに表示", value=selected.get("visible", True))

                            def save():
                                store_manual.update_manual(selected["id"], title=e_title.value,
                                    category_id=e_category.value, summary=e_summary.value,
                                    steps=e_steps.value, caution=e_caution.value,
                                    image_url=e_image.value, quiz_note=e_quiz.value,
                                    visible=e_visible.value)
                                dialog.close()
                                reload("マニュアルを更新しました")
                            ui.button("変更を保存", icon="save", on_click=save).classes("w-full")
                        dialog.open()
                    ui.button(icon="edit", on_click=edit).props("flat round dense aria-label='編集'")
                    ui.button(icon="delete_outline", on_click=lambda _, value=manual: (
                        store_manual.delete_manual(value["id"]), reload("マニュアルを削除しました")
                    )).props("flat round dense color=negative aria-label='削除'")

        ui.add_css("""
        .manual-admin-section{overflow:hidden;border:1px solid #e0e8e3!important;border-radius:18px!important;background:#fff!important}.manual-admin-section>.q-expansion-item__container>.q-item{min-height:58px;font-size:13px;font-weight:900}.manual-admin-section .q-expansion-item__content{padding:8px 14px 16px}.manual-admin-row{padding:9px 2px;border-bottom:1px solid #edf1ef}.manual-admin-dialog{width:min(94vw,520px)!important;max-height:90vh;overflow-y:auto;border-radius:22px!important}
        """)
