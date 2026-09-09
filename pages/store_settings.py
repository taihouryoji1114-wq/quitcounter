from nicegui import ui

from core.auth import require_app_access, require_permission
from core.qr import data_url as qr_data_url
from core.store_ops import store_ops
from core.store_quiz import store_quiz
from core.shift_submissions import shift_submissions
from core.theme import Theme
from pages.store_common import store_header_actions
from pages.announcement_controls import announcement_settings


CATEGORIES = ["野菜仕入れ", "冷食", "冷凍庫", "飲料", "調味料", "備品", "清掃用品", "その他"]
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
        announcement_settings()
        live_categories = store_ops.live_board_categories()
        live_areas = [value["name"] for value in live_categories] or AREAS
        with ui.card().classes("settings-hero w-full q-pa-lg q-mb-md"):
            ui.icon("tune").classes("text-3xl text-primary")
            ui.label("店舗で使う項目だけを管理").classes("text-lg font-black q-mt-sm")
            ui.label("普段の入力画面とは分けてあります").classes("text-[10px] text-grey-6")

        with ui.card().classes("manual-settings-link w-full q-pa-md q-mb-sm"):
            with ui.row().classes("w-full items-center no-wrap"):
                ui.icon("menu_book").classes("text-2xl text-orange-8")
                with ui.column().classes("grow gap-0"):
                    ui.label("マニュアル設定").classes("text-sm font-black")
                    ui.label("カテゴリー・手順・写真・注意点を追加編集").classes(
                        "text-[9px] text-grey-6")
                ui.button(icon="chevron_right", on_click=lambda: ui.navigate.to(
                    "/store-ops/settings/manuals")).props("flat round aria-label='開く'")

        with ui.card().classes("manual-settings-link w-full q-pa-md q-mb-sm"):
            with ui.row().classes("w-full items-center no-wrap"):
                ui.icon("cleaning_services").classes("text-2xl text-teal-7")
                with ui.column().classes("grow gap-0"):
                    ui.label("清掃設定").classes("text-sm font-black")
                    ui.label("場所・清掃項目・表示順を管理").classes(
                        "text-[9px] text-grey-6")
                ui.button(icon="chevron_right", on_click=lambda: ui.navigate.to(
                    "/store-ops/settings/cleaning")).props("flat round aria-label='開く'")

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
            minimum_stock = ui.number("最低在庫数", step=.1).props(
                "outlined dense inputmode=decimal").classes("w-full q-mt-xs")
            ui.label("この数以下になると、仕入れリストへ自動で追加されます").classes(
                "text-[9px] text-grey-6")

            def add_item():
                try:
                    store_ops.add_item(name.value, category.value, unit.value,
                                       supplier.value, "", tracking.value,
                                       minimum_stock.value, "")
                except ValueError as error:
                    notify_error(error)
                    return
                reload("商品・備品を登録しました")

            ui.button("登録する", icon="add", on_click=add_item).classes("w-full q-mt-md")

        with ui.expansion("LIVE BOARD カテゴリー管理", icon="view_agenda", value=False).classes(
                "settings-section w-full q-mb-sm"):
            category_name = ui.input("新しいカテゴリー名").props("outlined dense maxlength=30").classes(
                "w-full")
            category_color = ui.color_input("カテゴリー色", value="#527A68").classes("w-full")

            def add_live_category():
                try:
                    store_ops.add_live_board_category(category_name.value, category_color.value)
                except ValueError as error:
                    notify_error(error)
                    return
                reload("カテゴリーを追加しました")

            ui.button("カテゴリーを追加", icon="add", on_click=add_live_category).props(
                "unelevated no-caps").classes("w-full q-mb-sm")
            for category_item in live_categories:
                with ui.row().classes("settings-row w-full items-center no-wrap"):
                    ui.label(category_item["name"]).classes("text-xs font-black grow")
                    ui.button(icon="arrow_upward", on_click=lambda _, selected=category_item: (
                        store_ops.move_live_board_category(selected["id"], -1), reload()
                    )).props("flat round dense aria-label='上へ'")
                    ui.button(icon="arrow_downward", on_click=lambda _, selected=category_item: (
                        store_ops.move_live_board_category(selected["id"], 1), reload()
                    )).props("flat round dense aria-label='下へ'")

                    def edit_category(_, selected=category_item):
                        with ui.dialog() as dialog, ui.card().classes("settings-dialog q-pa-lg"):
                            ui.label("カテゴリー設定").classes("text-lg font-black")
                            field = ui.input("カテゴリー名", value=selected["name"]).props(
                                "outlined dense maxlength=30").classes("w-full")
                            color = ui.color_input(
                                "カテゴリー色", value=selected.get("color", "#527A68")
                            ).classes("w-full")
                            visible = ui.switch("LIVE BOARDに表示", value=selected.get("visible", True))

                            def save_category():
                                try:
                                    store_ops.update_live_board_category(
                                        selected["id"], field.value, visible.value, color.value)
                                except ValueError as error:
                                    notify_error(error)
                                    return
                                dialog.close()
                                reload("カテゴリーを更新しました")
                            ui.button("保存", on_click=save_category).classes("w-full")
                        dialog.open()
                    ui.button(icon="edit", on_click=edit_category).props("flat round dense")
                    ui.button(icon="delete_outline", on_click=lambda _, selected=category_item:
                              confirm_delete("このカテゴリーを削除しますか？", selected["name"],
                                             lambda: store_ops.delete_live_board_category(
                                                 selected["id"]))).props(
                                                     "flat round dense color=negative")

        with ui.expansion("LIVE BOARD 項目を登録", icon="soup_kitchen", value=False).classes(
                "settings-section w-full q-mb-sm"):
            prep_name = ui.input("仕込み項目").props("outlined dense").classes("w-full")
            prep_area = ui.select(live_areas, value=live_areas[0], label="カテゴリー").props(
                "outlined dense").classes("w-full q-mt-xs")
            prep_note = ui.switch("この仕込みで補足メモを使う", value=False).classes(
                "w-full q-mt-xs")
            prep_type = ui.select(
                ["完了型", "状態型（○△×）", "数量型", "メモ専用型", "特殊仕込み"], value="完了型", label="項目タイプ",
            ).props("outlined dense options-dense").classes("w-full q-mt-xs")
            prep_visible = ui.switch("LIVE BOARDに表示", value=True)
            with ui.expansion("タイプ別の詳細設定", icon="tune", value=False).classes(
                    "w-full q-mt-xs"):
                good_label = ui.input("○の意味", value="良好").props("outlined dense maxlength=20").classes("w-full")
                warning_label = ui.input("△の意味", value="注意").props("outlined dense maxlength=20").classes("w-full")
                bad_label = ui.input("×の意味", value="未完了").props("outlined dense maxlength=20").classes("w-full")
                show_labels = ui.switch("LIVE BOARDに意味も表示", value=False)
                quantity_unit = ui.input("数量の単位", value="個").props("outlined dense maxlength=12").classes("w-full")
                quantity_step = ui.number("＋−1回の増減量", value=1, step=.5).props("outlined dense").classes("w-full")
                quantity_initial = ui.number("初期値", value=0, step=.5).props("outlined dense").classes("w-full")
                quantity_min = ui.number("最低値", value=0, step=.5).props("outlined dense").classes("w-full")
                quantity_max = ui.number("最大値（空欄なら上限なし）", step=.5).props("outlined dense").classes("w-full")
                progress_enabled = ui.switch("数量を進捗数に含める", value=False)
                reset_mode = ui.select(["前回状態を引き継ぐ", "毎日初期値へ戻す"],
                                       value="前回状態を引き継ぐ", label="日次リセット").props(
                                           "outlined dense").classes("w-full")
                ui.separator().classes("q-my-sm")
                ui.label("特殊仕込みの表示日").classes("text-xs font-black")
                schedule_mode = ui.select(
                    {"weekly": "毎週", "monthly": "毎月", "date": "指定日"},
                    value="weekly", label="表示タイミング").props(
                        "outlined dense emit-value map-options").classes("w-full")
                schedule_weekday = ui.select(
                    {0: "月曜日", 1: "火曜日", 2: "水曜日", 3: "木曜日",
                     4: "金曜日", 5: "土曜日", 6: "日曜日"},
                    value=0, label="毎週の曜日").props(
                        "outlined dense emit-value map-options").classes("w-full")
                schedule_month_day = ui.number(
                    "毎月の日付", value=1, min=1, max=31, step=1).props(
                        "outlined dense").classes("w-full")
                schedule_date = ui.input("指定日（YYYY-MM-DD）").props(
                    "outlined dense maxlength=10").classes("w-full")
                special_note = ui.input("表示する補足（任意）").props(
                    "outlined dense maxlength=40").classes("w-full")

            def add_prep():
                try:
                    store_ops.add_prep_template(
                        prep_name.value, prep_area.value, None, prep_note.value,
                        item_type={"完了型": "completion", "状態型（○△×）": "status",
                                   "数量型": "quantity", "メモ専用型": "memo",
                                   "特殊仕込み": "special"}[prep_type.value],
                        status_labels={"done": good_label.value, "attention": warning_label.value,
                                       "incomplete": bad_label.value},
                        show_status_labels=show_labels.value, unit=quantity_unit.value,
                        step=quantity_step.value, initial_value=quantity_initial.value,
                        minimum_value=quantity_min.value, maximum_value=quantity_max.value,
                        visible=prep_visible.value,
                        reset_mode="daily" if reset_mode.value == "毎日初期値へ戻す" else "carry",
                        progress_enabled=progress_enabled.value,
                        schedule_mode=schedule_mode.value,
                        schedule_weekday=schedule_weekday.value,
                        schedule_month_day=schedule_month_day.value,
                        schedule_date=schedule_date.value,
                        special_note=special_note.value)
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

        with ui.expansion("ちゃんはやの問題を登録", icon="quiz", value=False).classes(
                "settings-section w-full q-mb-sm"):
            quiz_question = ui.textarea("問題文").props("outlined autogrow").classes("w-full")
            quiz_answer = ui.input("正解").props("outlined dense").classes("w-full")
            quiz_wrong = [ui.input(f"間違いの選択肢 {index}").props(
                "outlined dense").classes("w-full") for index in range(1, 4)]

            def add_quiz_question():
                try:
                    store_quiz.add_question(
                        quiz_question.value, quiz_answer.value,
                        [field.value for field in quiz_wrong],
                    )
                except ValueError as error:
                    notify_error(error)
                    return
                reload("ちゃんはやの問題を登録しました")

            ui.button("問題を登録する", icon="add", on_click=add_quiz_question).classes(
                "w-full q-mt-sm")

        quiz_items = store_quiz.questions()
        with ui.expansion(f"ちゃんはやの問題を編集　{len(quiz_items)}件", icon="edit_note",
                          value=False).classes("settings-section w-full q-mb-sm"):
            if not quiz_items:
                ui.label("登録した問題はまだありません").classes(
                    "text-[10px] text-grey-6 q-pa-sm")
            for item in quiz_items:
                with ui.row().classes("settings-row w-full items-center no-wrap"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(item["question"]).classes("text-xs font-black")
                        ui.label(f"正解：{item['answer']}").classes("text-[9px] text-positive")
                    ui.button(icon="delete_outline", on_click=lambda _, selected=item:
                              confirm_delete(
                                  "この問題を削除しますか？", selected["question"],
                                  lambda: store_quiz.delete_question(selected["id"]),
                              )).props("flat round dense color=negative aria-label='削除'")

        with ui.expansion("業務連絡を出す", icon="campaign", value=False).classes(
                "settings-section w-full q-mb-sm"):
            notice_title = ui.input("題名").props("outlined dense").classes("w-full")
            notice_details = ui.textarea("内容").props("outlined autogrow").classes("w-full")

            def add_notice():
                try:
                    store_quiz.add_notice(notice_title.value, notice_details.value)
                except ValueError as error:
                    notify_error(error)
                    return
                reload("業務連絡を掲載しました")

            ui.button("業務連絡を掲載", icon="campaign", on_click=add_notice).classes(
                "w-full q-mt-sm")

        notice_items = store_quiz.notices()
        if notice_items:
            with ui.expansion(f"掲載中の業務連絡　{len(notice_items)}件", icon="notifications_active",
                              value=False).classes("settings-section w-full q-mb-sm"):
                for item in notice_items:
                    with ui.row().classes("settings-row w-full items-center no-wrap"):
                        with ui.column().classes("gap-0 grow min-w-0"):
                            ui.label(item["title"]).classes("text-xs font-black")
                            ui.label(item.get("details", "")).classes("text-[9px] text-grey-6")
                        ui.button("終了", on_click=lambda _, selected=item: (
                            store_quiz.close_notice(selected["id"]), reload("掲載を終了しました")
                        )).props("flat dense no-caps color=negative")

        notice_history = [item for item in store_quiz.notices(include_closed=True)
                          if not item.get("active", True)]
        if notice_history:
            with ui.expansion(f"過去の業務連絡　{len(notice_history)}件", icon="history",
                              value=False).classes("settings-section w-full q-mb-sm"):
                for item in reversed(notice_history):
                    with ui.column().classes("settings-row w-full gap-0"):
                        ui.label(item["title"]).classes("text-xs font-black")
                        if item.get("details"):
                            ui.label(item["details"]).classes(
                                "text-[9px] text-grey-6 whitespace-pre-wrap")
                        ui.label(f"掲載：{item.get('created_at', '-')}　終了：{item.get('closed_at', '-')}").classes(
                            "text-[8px] text-grey-5")

        with ui.expansion("スタッフ個人PINを管理", icon="shield", value=False).classes(
                "settings-section w-full q-mb-sm"):
            ui.label("本人以外によるシフト希望の書き換えを防ぎます").classes(
                "text-[10px] text-grey-6")
            with ui.column().classes("w-full gap-1 q-mt-sm"):
                for staff_name in shift_submissions.STAFF:
                    visible_pin = shift_submissions.staff_pin_for_admin(staff_name)
                    configured = shift_submissions.has_staff_pin(staff_name)
                    with ui.row().classes("pin-admin-row w-full items-center justify-between"):
                        ui.label(staff_name).classes("text-xs font-black")
                        ui.label(
                            visible_pin or ("設定済み・再設定すると表示" if configured else "未設定")
                        ).classes("pin-admin-value")
            pin_staff = ui.select(list(shift_submissions.STAFF), label="スタッフ").props(
                "outlined dense").classes("w-full q-mt-sm")
            new_pin = ui.input(
                "新しい個人PIN（4〜8桁）", password=True, password_toggle_button=True,
            ).props("outlined dense inputmode=numeric maxlength=8").classes("w-full q-mt-sm")

            def save_staff_pin():
                if not pin_staff.value:
                    ui.notify("スタッフを選択してください", type="negative")
                    return
                try:
                    shift_submissions.set_staff_pin(pin_staff.value, new_pin.value)
                except ValueError as error:
                    notify_error(error)
                    return
                new_pin.value = ""
                ui.notify(f"{pin_staff.value}の個人PINを設定しました", type="positive")

            ui.button("個人PINを設定・変更", icon="key", on_click=save_staff_pin).classes(
                "w-full q-mt-sm")

        items = store_ops.items()
        with ui.expansion(f"商品・備品の編集　{len(items)}件", icon="edit", value=False).classes(
                "settings-section w-full q-mb-sm"):
            for item in items:
                with ui.row().classes("settings-row w-full items-center no-wrap"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(item["name"]).classes("text-xs font-black")
                        ui.label(f"{item.get('category', 'その他')}・{item.get('unit', '個')}").classes(
                            "text-[9px] text-grey-6")
                        minimum = item.get("reorder_point")
                        if minimum is not None:
                            minimum_text = (str(int(minimum)) if float(minimum).is_integer()
                                            else str(minimum))
                            ui.label(
                                f"最低在庫 設定済み：{minimum_text}{item.get('unit', '個')}"
                            ).classes("minimum-stock-configured")

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
                            edit_minimum = ui.number(
                                "最低在庫数", value=selected.get("reorder_point"), step=.1).props(
                                    "outlined dense inputmode=decimal").classes("w-full")
                            ui.label("この数以下になると、仕入れリストへ自動で追加されます").classes(
                                "text-[9px] text-grey-6")

                            def save():
                                try:
                                    store_ops.update_item(selected["id"], edit_name.value,
                                                          edit_category.value, edit_unit.value,
                                                          edit_supplier.value, edit_tracking.value)
                                    if edit_tracking.value == "count":
                                        store_ops.update_count_settings(
                                            selected["id"], edit_unit.value,
                                            reorder_point=edit_minimum.value)
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
        with ui.expansion(f"LIVE BOARD 項目管理　{len(prep_items)}件", icon="edit_note",
                          value=False).classes("settings-section w-full q-mb-sm"):
            for item in prep_items:
                with ui.row().classes("settings-row w-full items-center no-wrap"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(item["name"]).classes("text-xs font-black")
                        type_label = {"completion": "完了型", "status": "状態型",
                                      "quantity": "数量型", "memo": "メモ専用型",
                                      "special": "特殊仕込み"}.get(
                                          item.get("item_type"),
                                          "状態型" if item.get("status_mode") == "three" else "完了型")
                        ui.label(f"{item.get('area', '厨房')}・{type_label}").classes(
                            "text-[9px] text-grey-6")

                    def edit_prep(_, selected=item):
                        with ui.dialog() as dialog, ui.card().classes("settings-dialog q-pa-lg"):
                            ui.label("仕込み項目を編集").classes("text-lg font-black q-mb-sm")
                            edit_name = ui.input("項目名", value=selected["name"]).props("outlined dense").classes("w-full")
                            edit_area = ui.select(live_areas, value=selected.get("area", live_areas[0]), label="カテゴリー").props(
                                "outlined dense").classes("w-full")
                            edit_note = ui.switch(
                                "短文メモを使う",
                                value=bool(selected.get("note_enabled", False)),
                            ).classes("w-full")
                            current_type = selected.get("item_type") or (
                                "status" if selected.get("status_mode") == "three" else "completion")
                            type_names = {"completion": "完了型", "status": "状態型（○△×）",
                                          "quantity": "数量型", "memo": "メモ専用型",
                                          "special": "特殊仕込み"}
                            edit_type = ui.select(list(type_names.values()), value=type_names[current_type],
                                                  label="項目タイプ").props("outlined dense").classes("w-full")
                            edit_visible = ui.switch("LIVE BOARDに表示", value=selected.get("visible", True))
                            labels = selected.get("status_labels", {})
                            with ui.expansion("タイプ別の詳細設定", icon="tune", value=False).classes("w-full"):
                                edit_good = ui.input("○の意味", value=labels.get("done", "良好")).props("outlined dense maxlength=20").classes("w-full")
                                edit_warning = ui.input("△の意味", value=labels.get("attention", "注意")).props("outlined dense maxlength=20").classes("w-full")
                                edit_bad = ui.input("×の意味", value=labels.get("incomplete", "未完了")).props("outlined dense maxlength=20").classes("w-full")
                                edit_show_labels = ui.switch("意味も表示", value=selected.get("show_status_labels", False))
                                edit_unit = ui.input("単位", value=selected.get("unit", "個")).props("outlined dense maxlength=12").classes("w-full")
                                edit_step = ui.number("増減量", value=selected.get("step", 1), step=.5).props("outlined dense").classes("w-full")
                                edit_initial = ui.number("初期値", value=selected.get("initial_value", 0), step=.5).props("outlined dense").classes("w-full")
                                edit_minimum = ui.number("最低値", value=selected.get("minimum_value", 0), step=.5).props("outlined dense").classes("w-full")
                                edit_maximum = ui.number("最大値（空欄なら上限なし）", value=selected.get("maximum_value"), step=.5).props("outlined dense").classes("w-full")
                                edit_progress = ui.switch("数量を進捗数に含める", value=selected.get("progress_enabled", False))
                                edit_reset = ui.select(["前回状態を引き継ぐ", "毎日初期値へ戻す"],
                                    value=("毎日初期値へ戻す" if selected.get("reset_mode") == "daily"
                                           else "前回状態を引き継ぐ"), label="日次リセット").props("outlined dense").classes("w-full")
                                ui.separator().classes("q-my-sm")
                                ui.label("特殊仕込みの表示日").classes("text-xs font-black")
                                edit_schedule_mode = ui.select(
                                    {"weekly": "毎週", "monthly": "毎月", "date": "指定日"},
                                    value=selected.get("schedule_mode", "weekly"),
                                    label="表示タイミング").props(
                                        "outlined dense emit-value map-options").classes("w-full")
                                edit_schedule_weekday = ui.select(
                                    {0: "月曜日", 1: "火曜日", 2: "水曜日", 3: "木曜日",
                                     4: "金曜日", 5: "土曜日", 6: "日曜日"},
                                    value=selected.get("schedule_weekday", 0),
                                    label="毎週の曜日").props(
                                        "outlined dense emit-value map-options").classes("w-full")
                                edit_schedule_month_day = ui.number(
                                    "毎月の日付", value=selected.get("schedule_month_day", 1),
                                    min=1, max=31, step=1).props("outlined dense").classes("w-full")
                                edit_schedule_date = ui.input(
                                    "指定日（YYYY-MM-DD）", value=selected.get("schedule_date", "")
                                ).props("outlined dense maxlength=10").classes("w-full")
                                edit_special_note = ui.input(
                                    "表示する補足（任意）", value=selected.get("special_note", "")
                                ).props("outlined dense maxlength=40").classes("w-full")

                            def save():
                                try:
                                    store_ops.update_prep_template(
                                        selected["id"], edit_name.value, edit_area.value,
                                        selected.get("check_items", []), edit_note.value,
                                        item_type={value: key for key, value in type_names.items()}[edit_type.value],
                                        status_labels={"done": edit_good.value,
                                                       "attention": edit_warning.value,
                                                       "incomplete": edit_bad.value},
                                        show_status_labels=edit_show_labels.value,
                                        unit=edit_unit.value, step=edit_step.value,
                                        initial_value=edit_initial.value,
                                        minimum_value=edit_minimum.value,
                                        maximum_value=edit_maximum.value,
                                        visible=edit_visible.value,
                                        reset_mode="daily" if edit_reset.value == "毎日初期値へ戻す" else "carry",
                                        progress_enabled=edit_progress.value,
                                        schedule_mode=edit_schedule_mode.value,
                                        schedule_weekday=edit_schedule_weekday.value,
                                        schedule_month_day=edit_schedule_month_day.value,
                                        schedule_date=edit_schedule_date.value,
                                        special_note=edit_special_note.value)
                                except ValueError as error:
                                    notify_error(error)
                                    return
                                dialog.close()
                                reload("仕込み項目を更新しました")

                            ui.button("変更を保存", icon="save", on_click=save).classes("w-full q-mt-sm")
                        dialog.open()

                    ui.button(icon="edit", on_click=edit_prep).props("flat round dense aria-label='編集'")
                    ui.button(icon="arrow_upward", on_click=lambda _, selected=item: (
                        store_ops.move_prep_template(selected["id"], -1), reload()
                    )).props("flat round dense aria-label='上へ'")
                    ui.button(icon="arrow_downward", on_click=lambda _, selected=item: (
                        store_ops.move_prep_template(selected["id"], 1), reload()
                    )).props("flat round dense aria-label='下へ'")
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
        .settings-hero{border-radius:24px!important;border:1px solid #E0E8E2!important;background:linear-gradient(145deg,#EEF6F1,#FFF9EE)!important;box-shadow:none!important}.manual-settings-link{cursor:pointer;border:1px solid #eadfc9!important;border-radius:18px!important;background:linear-gradient(145deg,#fffdf8,#fff4dd)!important;box-shadow:0 5px 0 #dfcfad!important}
        .settings-section{border:1px solid #E0E7E2!important;border-radius:19px!important;background:#fff!important;overflow:hidden}.settings-section>.q-item{min-height:56px;font-size:13px;font-weight:900}.settings-section .q-expansion-item__content{padding:7px 13px 15px}.settings-row{padding:9px 2px;border-bottom:1px solid #EDF1EE}.settings-dialog{width:min(92vw,440px)!important;border-radius:23px!important}.settings-qr{width:210px;height:210px;border-radius:17px;background:#fff;padding:10px;border:1px solid #E1E9E4}.minimum-stock-configured{display:inline-flex;width:max-content;margin-top:3px;padding:2px 7px;border-radius:999px;background:#FFF0CC;color:#8A5A08;font-size:8px;font-weight:900}.pin-admin-row{min-height:31px;padding:4px 9px;border-radius:9px;background:#F4F7F5}.pin-admin-value{font-size:11px;font-weight:950;letter-spacing:.08em;color:#246A4E}
        """)
