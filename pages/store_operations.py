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
        delete_target = {"id": None, "name": ""}
        with ui.dialog() as delete_dialog, ui.card().classes("store-dialog q-pa-lg"):
            ui.label("この商品を削除しますか？").classes("text-lg font-black")
            delete_name = ui.label().classes("text-sm text-grey-7 q-mt-xs")

            def confirm_delete():
                try:
                    store_ops.delete_item(delete_target["id"])
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                delete_dialog.close()
                reload("商品を削除しました")
            with ui.row().classes("w-full gap-2 q-mt-md"):
                ui.button("キャンセル", on_click=delete_dialog.close).props("flat").classes("grow")
                ui.button("削除する", icon="delete", on_click=confirm_delete).props(
                    "unelevated color=negative").classes("grow")

        def open_delete(item):
            delete_target.update(id=item["id"], name=item["name"])
            delete_name.set_text(item["name"])
            delete_dialog.open()

        prep_delete_target = {"id": None, "name": ""}
        with ui.dialog() as prep_delete_dialog, ui.card().classes("store-dialog q-pa-lg"):
            ui.label("この仕込み項目を削除しますか？").classes("text-lg font-black")
            prep_delete_name = ui.label().classes("text-sm text-grey-7 q-mt-xs")
            ui.label("過去の記録は残り、今後の一覧から非表示になります").classes(
                "text-[10px] text-grey-6 q-mt-xs")

            def confirm_prep_delete():
                try:
                    store_ops.delete_prep_template(prep_delete_target["id"])
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                prep_delete_dialog.close()
                reload("仕込み項目を削除しました")
            with ui.row().classes("w-full gap-2 q-mt-md"):
                ui.button("キャンセル", on_click=prep_delete_dialog.close).props("flat").classes("grow")
                ui.button("削除する", icon="delete", on_click=confirm_prep_delete).props(
                    "unelevated color=negative").classes("grow")

        def open_prep_delete(item):
            prep_delete_target.update(id=item["id"], name=item["name"])
            prep_delete_name.set_text(item["name"])
            prep_delete_dialog.open()

        with ui.dialog() as add_dialog, ui.card().classes("store-dialog q-pa-lg"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("商品を登録").classes("text-xl font-black")
                ui.button(icon="close", on_click=add_dialog.close).props("flat round")
            name = ui.input("商品・備品名").props("outlined dense").classes("w-full")
            category = ui.select(["食材", "飲料", "調味料", "備品", "清掃用品", "その他"],
                                 value="食材", label="分類").props("outlined dense").classes("w-full q-mt-xs")
            unit = ui.input("単位", value="個").props("outlined dense").classes("w-full q-mt-xs")
            supplier = ui.input("いつもの仕入先（任意）").props("outlined dense").classes("w-full q-mt-xs")
            tracking_mode = ui.select(
                {"simple": "かんたん管理", "count": "個数で正確に管理"},
                value="simple", label="管理方法",
            ).props("outlined dense emit-value map-options").classes("w-full q-mt-xs")
            required_stock = ui.number("必要在庫数（個数管理用）").props(
                "outlined dense inputmode=decimal").classes("w-full q-mt-xs")
            reorder_point = ui.number("発注ライン（この数以下で発注）").props(
                "outlined dense inputmode=decimal").classes("w-full q-mt-xs")
            current_stock = ui.number("現在庫数（任意）").props(
                "outlined dense inputmode=decimal").classes("w-full q-mt-xs")
            ui.label("かんたん管理では数字欄の入力は不要です").classes("text-[9px] text-grey-6")

            def add_item():
                try:
                    store_ops.add_item(name.value, category.value, unit.value,
                                       supplier.value, required_stock.value,
                                       tracking_mode.value, reorder_point.value, current_stock.value)
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
                    ui.label("気づいた人が在庫状態を押すだけ").classes(
                        "text-[9px] opacity-75 q-mt-sm")
                ui.icon("inventory_2").classes("text-4xl opacity-70")
            with ui.row().classes("w-full gap-2 q-mt-md"):
                ui.button("商品を追加", icon="add", on_click=add_dialog.open).props(
                    "unelevated no-caps").classes("store-hero-button grow")

        with ui.expansion(f"不足・発注リスト　{len(orders)}品", icon="shopping_cart",
                          value=False).classes("store-panel order-panel w-full q-mt-sm"):
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
                                    (f"必要在庫 {item.get('required_stock') or item.get('order_quantity')}"
                                     if item.get("required_stock") or item.get("order_quantity") else ""),
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

        with ui.expansion("在庫を確認", icon="checklist", value=False).classes(
            "store-panel inventory-panel w-full q-mt-sm"):
            if not items:
                ui.label("最初の商品を登録してください").classes("text-sm text-grey-6 q-pa-md")
            category_aliases = {"消耗品": "備品"}
            grouped_items = {}
            for item in items:
                display_category = category_aliases.get(item["category"], item["category"])
                grouped_items.setdefault(display_category, []).append(item)
            category_order = ["食材", "飲料", "調味料", "備品", "清掃用品", "その他"]
            for category_name in sorted(grouped_items, key=lambda value: (
                    category_order.index(value) if value in category_order else 99, value)):
                category_items = grouped_items[category_name]
                with ui.expansion(f"{category_name}　{len(category_items)}品", icon="folder",
                                  value=False).classes("inventory-category w-full"):
                    for item in category_items:
                        with ui.row().classes("inventory-row w-full items-center no-wrap"):
                            with ui.column().classes("gap-0 inventory-name"):
                                ui.label(item["name"]).classes("text-xs font-black")
                                if item["supplier"]:
                                    ui.label(item["supplier"]).classes("text-[8px] text-grey-6")
                            if item.get("tracking_mode") == "count":
                                count_input = ui.number(value=item.get("current_stock"), suffix=item.get("unit", "個"),
                                                        step=1).props("outlined dense inputmode=decimal").classes(
                                                            "count-input")
                                ui.button(icon="save", on_click=lambda _, item_id=item["id"], field=count_input: (
                                    store_ops.set_count(item_id, field.value), reload("在庫数を更新しました")
                                )).props("flat round dense")
                            else:
                                for status, label in (("enough", "十分"), ("low", "発注ライン"),
                                                      ("out", "在庫切れ")):
                                    active = item["status"] == status
                                    ui.button(label, on_click=lambda _, item_id=item["id"], value=status: (
                                        store_ops.set_status(item_id, value), reload()
                                    )).props("unelevated dense no-caps").classes(
                                        f"stock-button {'active-' + status if active else ''}")
                            ui.button(icon="delete_outline", on_click=lambda _, value=item: open_delete(value)).props(
                                "flat round dense color=negative aria-label='商品を削除'").tooltip("商品を削除")

        today = today_jst().isoformat()
        hygiene = store_ops.hygiene_record(today)
        with ui.expansion("今日の温度・衛生チェック", icon="health_and_safety",
                          value=False).classes(
            "store-panel hygiene-panel w-full q-mt-sm"):
            ui.label("温度").classes("text-xs font-black q-mb-xs")
            temperature_inputs = {}
            temperature_groups = (
                ("デシャップ・冷蔵庫", store_ops.TEMPERATURE_LOCATIONS[0:3]),
                ("厨房・冷蔵庫", store_ops.TEMPERATURE_LOCATIONS[3:8]),
                ("冷凍庫", store_ops.TEMPERATURE_LOCATIONS[8:11]),
            )
            for group_label, appliances in temperature_groups:
                ui.label(group_label).classes("temperature-group-label")
                with ui.element("div").classes("temperature-grid w-full"):
                    for appliance in appliances:
                        short_label = appliance.replace("デシャップ", "").replace("厨房", "").replace("外", "外 ")
                        temperature_inputs[appliance] = ui.number(
                            short_label, value=hygiene["temperatures"][appliance], step=.1
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

        prep_items = store_ops.prep_items(today)
        with ui.expansion("今日の仕込み状況", icon="soup_kitchen", value=False).classes(
            "store-panel prep-panel w-full q-mt-sm"):
            with ui.row().classes("w-full items-end gap-2 q-mb-sm"):
                prep_name = ui.input("仕込み項目を追加").props("outlined dense").classes("grow")
                prep_area = ui.select(["厨房", "デシャップ", "ホール"], value="厨房",
                                      label="場所").props("outlined dense").classes("prep-area")

                def add_prep():
                    try:
                        store_ops.add_prep_template(prep_name.value, prep_area.value)
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    reload("仕込み項目を追加しました")
                ui.button(icon="add", on_click=add_prep).props("unelevated round")
            if not prep_items:
                ui.label("よく行う仕込みを登録すると、毎日同じ一覧で確認できます").classes(
                    "text-xs text-grey-6 q-pa-sm")
            for item in prep_items:
                with ui.row().classes("inventory-row w-full items-center no-wrap"):
                    with ui.column().classes("gap-0 grow"):
                        ui.label(item["name"]).classes("text-xs font-black")
                        detail = f"{item['area']}・前日から持ち越し" if item.get("carried_over") else item["area"]
                        ui.label(detail).classes(
                            "text-[8px] text-negative font-bold" if item.get("carried_over")
                            else "text-[8px] text-grey-6")
                    for status, label in (("incomplete", "未完了"), ("done", "完了")):
                        active = item["status"] == status
                        ui.button(label, on_click=lambda _, item_id=item["id"], value=status: (
                            store_ops.set_prep_status(today, item_id, value), reload()
                        )).props("unelevated dense no-caps").classes(
                            f"prep-button {'active-prep-' + status if active else ''}")
                    if item.get("source") == "prep":
                        ui.button(icon="delete_outline",
                                  on_click=lambda _, value=item: open_prep_delete(value)).props(
                                      "flat round dense color=negative aria-label='仕込み項目を削除'").tooltip(
                                          "仕込み項目を削除")

        handovers = store_ops.handovers(today)
        handover_checks = store_ops.handover_checks(today)
        with ui.expansion(f"今日の引き継ぎ　{sum(not value['confirmed'] for value in handovers)}件未確認",
                          icon="campaign", value=False).classes(
                              "store-panel handover-panel w-full q-mt-sm"):
            ui.label("定型チェック項目").classes("text-xs font-black q-mb-xs")
            with ui.row().classes("w-full items-end gap-2 q-mb-sm"):
                check_name = ui.input("チェック項目を追加").props("outlined dense").classes("grow")
                check_area = ui.select(["ホール", "デシャップ", "厨房"], value="厨房",
                                       label="場所").props("outlined dense").classes("prep-area")

                def add_check_item():
                    try:
                        store_ops.add_handover_template(check_name.value, check_area.value)
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    reload("引き継ぎチェックを追加しました")
                ui.button(icon="add", on_click=add_check_item).props("unelevated round")
            for area in ("ホール", "デシャップ", "厨房"):
                area_items = [value for value in handover_checks if value["area"] == area]
                if not area_items:
                    continue
                ui.label(area).classes("category-title")
                for item in area_items:
                    ui.checkbox(item["name"], value=item["checked"], on_change=lambda event,
                                item_id=item["id"]: store_ops.set_handover_check(
                                    today, item_id, event.value)).classes("w-full hygiene-check")

            ui.separator().classes("q-my-md")
            ui.label("自由記入").classes("text-xs font-black q-mb-xs")
            handover_area = ui.select(["ホール", "デシャップ", "厨房"], value="厨房",
                                      label="場所").props("outlined dense").classes("w-full")
            handover_message = ui.textarea("引き継ぎ内容").props("outlined autogrow").classes("w-full")

            def add_handover():
                try:
                    store_ops.add_handover(today, handover_message.value, handover_area.value)
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                reload("引き継ぎを追加しました")
            ui.button("引き継ぎを追加", icon="add", on_click=add_handover).classes("w-full q-mb-md")
            if not handovers:
                ui.label("今日の引き継ぎはありません").classes("text-xs text-grey-6 q-pa-sm")
            for item in reversed(handovers):
                with ui.card().classes("handover-card w-full q-pa-md q-mb-xs"):
                    ui.label(item["message"]).classes("text-sm font-bold")
                    ui.label(f"{item.get('area', '厨房')}・{item['created_at'][-5:]}").classes(
                        "text-[9px] text-grey-6 q-mt-xs")
                    if item["confirmed"]:
                        ui.label("確認済み").classes("text-[10px] text-positive font-bold q-mt-xs")
                    else:
                        ui.button("確認しました", icon="done", on_click=lambda _, item_id=item["id"]: (
                            store_ops.confirm_handover(today, item_id), reload("確認済みにしました")
                        )).props("flat dense no-caps").classes("w-full q-mt-xs")

        with ui.card().classes("future-card future-panel w-full q-pa-md q-mt-sm"):
            ui.label("次の開発").classes("text-[9px] font-black text-primary")
            ui.label("タスク・清掃管理").classes("text-base font-black q-mt-xs")
            ui.label("その後、マニュアル・行動指針へ広げます").classes(
                "text-[9px] text-grey-6 q-mt-xs")

        ui.add_css("""
        .store-dialog{width:min(92vw,440px)!important;border-radius:24px!important}.store-hero{border:0!important;border-radius:27px!important;background:linear-gradient(145deg,#173D30,#3D755D 65%,#C18A45 145%)!important;box-shadow:0 16px 38px rgba(26,65,48,.22)!important}.store-hero-button{background:rgba(255,255,255,.94)!important;color:#285941!important;border-radius:13px!important}.store-panel{border-radius:19px!important;background:#fff!important;border:1px solid #E1E9E4!important}.store-panel .q-item{min-height:52px!important}.order-card,.handover-card{border-radius:16px!important;border:1px solid #E4EAE6!important;box-shadow:none!important}.stock-pill{padding:5px 8px;border-radius:999px;font-size:8px;font-weight:900;white-space:nowrap}.stock-out{background:#FBE4E4;color:#A43D45}.stock-low{background:#FFF0CE;color:#966117}.category-title{font-size:10px;font-weight:900;color:#527060;padding:13px 4px 5px}.inventory-category{border-bottom:1px solid #EDF1EE}.inventory-category .q-item{min-height:46px!important}.inventory-row{gap:5px;padding:8px 2px;border-bottom:1px solid #EDF1EE}.inventory-name{flex:1;min-width:70px}.stock-button,.prep-button{min-width:45px!important;border-radius:11px!important;background:#F2F4F3!important;color:#66726C!important;font-size:9px!important}.active-enough,.active-prep-done{background:#DFF2E7!important;color:#267149!important}.active-low{background:#FFF0CE!important;color:#966117!important}.active-out{background:#FBE2E2!important;color:#A43D45!important}.active-prep-incomplete{background:#E9ECEA!important;color:#526059!important}.count-input{width:110px}.prep-area{width:105px}.temperature-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:6px}.temperature-grid .q-field__label{font-size:9px!important}.temperature-group-label{font-size:9px;font-weight:800;color:#718078;margin:8px 0 4px}.hygiene-check{padding:4px 7px;border-radius:11px;background:#F5F7F5;margin-bottom:4px}.hygiene-check .q-checkbox__label{font-size:10px}.future-card{border-radius:18px!important;background:linear-gradient(145deg,#F0F6F2,#FFF8EA)!important;border:1px solid #E0E9E3!important;box-shadow:none!important}
        @media (min-width:700px){
          .app-shell{width:min(100%,1180px)!important;padding:38px 36px 68px!important}
          .app-shell>div:last-child{display:grid!important;grid-template-columns:minmax(0,1.15fr) minmax(300px,.85fr);column-gap:18px;align-items:start}
          .store-hero{grid-column:1 / -1;padding:28px 32px!important}
          .order-panel{grid-column:1;grid-row:2}
          .inventory-panel{grid-column:1;grid-row:3}
          .hygiene-panel{grid-column:2;grid-row:2 / span 2;position:sticky;top:18px}
          .prep-panel{grid-column:1;grid-row:4}.handover-panel{grid-column:2;grid-row:4}
          .future-panel{grid-column:1 / -1;grid-row:5}
          .store-panel{margin-top:14px!important}
          .store-panel .q-item{min-height:64px!important;padding:0 20px!important;font-size:16px}
          .inventory-row{gap:10px;padding:12px 8px}.inventory-name{min-width:150px}
          .inventory-name .text-xs{font-size:14px!important}.inventory-name .text-\[8px\]{font-size:11px!important}
          .stock-button{min-width:70px!important;min-height:42px!important;font-size:12px!important}
          .prep-button{min-width:72px!important;min-height:42px!important;font-size:11px!important}
          .order-card{padding:18px!important}.stock-pill{font-size:10px;padding:7px 10px}
          .temperature-grid{grid-template-columns:repeat(3,1fr);gap:10px}.temperature-grid .q-field__label{font-size:11px!important}
          .temperature-group-label{font-size:11px;margin-top:12px}
          .hygiene-check{padding:8px 10px;margin-bottom:7px}.hygiene-check .q-checkbox__label{font-size:13px}
        }
        @media (min-width:700px) and (max-width:850px) and (orientation:portrait){
          .app-shell>div:last-child{grid-template-columns:minmax(0,1fr) minmax(275px,.82fr);column-gap:12px}
          .app-shell{padding-left:22px!important;padding-right:22px!important}
          .stock-button{min-width:58px!important}
        }
        """)
