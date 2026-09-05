from nicegui import ui

from core.auth import current_role, has_permission, require_app_access
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
    notes = store_ops.all_handovers()
    content = section_shell("自由引き継ぎ", "日付が変わっても残ります。不要になったら手動で削除してください。")
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
        def request_delete(note):
            with ui.dialog() as dialog, ui.card().classes("w-full max-w-sm"):
                ui.label("この引き継ぎを削除しますか？").classes("text-lg font-bold")
                ui.label(note["message"]).classes("whitespace-pre-wrap break-words")
                def delete():
                    store_ops.delete_handover(note["record_date"], note["id"])
                    dialog.close()
                    ui.navigate.to("/store-ops/handover")
                with ui.row():
                    ui.button("キャンセル", on_click=dialog.close).props("flat")
                    ui.button("削除する", on_click=delete).props("color=negative")
            dialog.open()

        for note in reversed(notes):
            with ui.card().classes("surface-card w-full q-pa-lg q-mb-sm"):
                ui.label(note["area"]).classes("text-[9px] font-black text-primary")
                ui.label(note["record_date"]).classes("text-xs text-grey-7")
                ui.label(note["message"]).classes("text-sm font-bold q-mt-xs whitespace-pre-wrap break-words")
                if note.get("confirmed"):
                    ui.label("確認済み").classes("text-positive text-xs")
                ui.button("削除", icon="delete_outline",
                          on_click=lambda _, item=note: request_delete(item)).props("flat color=negative")


@ui.page("/store-ops/order-requests")
def order_requests_page():
    if not require_app_access("store_ops"):
        return
    requests = store_ops.order_requests()
    open_requests = [item for item in requests if not item.get("completed", False)]
    completed_requests = [item for item in requests if item.get("completed", False)]
    can_manage = has_permission("store_manage")
    content = section_shell("発注依頼", "気づいたその場で、発注してほしい物を共有")
    with content:
        message = ui.textarea("発注してほしい物").props(
            "outlined autogrow placeholder='例：キッチンペーパー 2箱'").classes("w-full")

        def add_request():
            try:
                store_ops.add_order_request(message.value)
            except ValueError as error:
                ui.notify(str(error), type="negative")
                return
            ui.navigate.to("/store-ops/order-requests")

        ui.button("発注依頼を追加", icon="send", on_click=add_request).classes("w-full q-mt-sm")
        ui.label(f"未対応　{len(open_requests)}件").classes("text-base font-black q-mt-xl q-mb-sm")
        if not open_requests:
            ui.label("未対応の発注依頼はありません").classes("request-empty w-full")
        for request in open_requests:
            with ui.card().classes("request-card w-full q-pa-md q-mb-sm"):
                with ui.row().classes("w-full items-center no-wrap"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(request["message"]).classes("text-sm font-black")
                        ui.label(str(request.get("created_at", ""))[:16].replace("T", " ")).classes(
                            "text-[9px] text-grey-6 q-mt-xs")
                    if can_manage:
                        ui.button("対応済み", icon="check", on_click=lambda _, item_id=request["id"]: (
                            store_ops.set_order_request_completed(item_id, True),
                            ui.navigate.to("/store-ops/order-requests")
                        )).props("unelevated dense no-caps color=positive")
                    else:
                        ui.label("管理者対応").classes("request-manager-badge")
        if completed_requests:
            with ui.expansion(f"対応済み　{len(completed_requests)}件", icon="task_alt",
                              value=False).classes("request-completed w-full q-mt-lg"):
                for request in completed_requests:
                    with ui.row().classes("w-full items-center no-wrap q-py-sm"):
                        ui.label(request["message"]).classes("text-xs text-grey-7 grow")
                        if can_manage:
                            ui.button("戻す", icon="undo", on_click=lambda _, item_id=request["id"]: (
                                store_ops.set_order_request_completed(item_id, False),
                                ui.navigate.to("/store-ops/order-requests")
                            )).props("flat dense no-caps")
                        if current_role() == "owner":
                            ui.button(icon="delete_outline", on_click=lambda _, item_id=request["id"]: (
                                store_ops.delete_order_request(item_id),
                                ui.navigate.to("/store-ops/order-requests")
                            )).props("flat round dense color=negative aria-label='削除'")
        ui.add_css("""
        .request-card{border:1px solid #E1E9E4!important;border-radius:18px!important;box-shadow:none!important}
        .request-empty{padding:22px;border:1px dashed #C9D4CD;border-radius:18px;text-align:center;color:#7C8982;font-size:11px}
        .request-completed{border:1px solid #E1E9E4;border-radius:18px;background:#fff}
        .request-manager-badge{font-size:8px;font-weight:900;color:#9B6C21;background:#FFF1D5;padding:6px 8px;border-radius:999px;white-space:nowrap}
        """)


@ui.page("/store-ops/inventory")
def inventory_page():
    if not require_app_access("store_ops"):
        return
    items = store_ops.items()
    is_owner = current_role() == "owner"
    categories = store_ops.inventory_categories()
    subcategories = store_ops.inventory_subcategories()
    reset_at = store_ops.inventory_check_reset_at()
    content = section_shell("在庫確認", "現在の在庫をまとめて入力")
    with content:
        if is_owner:
            with ui.dialog() as category_dialog, ui.card().classes("surface-card w-96 q-pa-lg"):
                ui.label("小分類を設定").classes("text-xl font-black")
                ui.label("例：飲料の中に「ソフトドリンク」「焼酎」を作り、小枠だけ色分けします").classes("text-xs text-grey-7")
                category_select = ui.select(
                    {value["id"]: f'{value["parent"]} ＞ {value["name"]}' for value in subcategories},
                    label="編集する小分類（新規なら未選択）",
                ).props("outlined dense clearable options-dense").classes("w-full q-mt-md")
                parent_name = ui.select(
                    [value["name"] for value in categories], label="入れる大分類",
                ).props("outlined dense options-dense").classes("w-full")
                category_name = ui.input("小分類名").props("outlined dense").classes("w-full")
                category_color = ui.input("小枠の色", value="#E8F5E9").props(
                    "outlined dense type=color").classes("w-full")

                def load_category(event):
                    selected = next((value for value in subcategories
                                     if value["id"] == event.value), None)
                    if selected:
                        parent_name.value = selected["parent"]
                        category_name.value = selected["name"]
                        category_color.value = selected.get("color", "#F5F5F5")

                category_select.on_value_change(load_category)

                def save_category():
                    try:
                        store_ops.save_inventory_subcategory(
                            parent_name.value, category_name.value, category_color.value,
                            category_select.value)
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    category_dialog.close()
                    ui.navigate.to("/store-ops/inventory")

                ui.button("保存", icon="save", on_click=save_category).classes("w-full")
            with ui.dialog() as assign_dialog, ui.card().classes("surface-card w-96 q-pa-lg"):
                ui.label("商品を小分類へ入れる").classes("text-xl font-black")
                assign_item = ui.select({value["id"]: value["name"] for value in items},
                                        label="商品").props("outlined dense options-dense").classes("w-full")
                assign_group = ui.select(
                    {value["id"]: f'{value["parent"]} ＞ {value["name"]}' for value in subcategories},
                    label="小分類").props("outlined dense options-dense").classes("w-full")

                def save_assignment():
                    group = next((value for value in subcategories if value["id"] == assign_group.value), None)
                    if not assign_item.value or not group:
                        ui.notify("商品と小分類を選んでください", type="warning")
                        return
                    store_ops.assign_inventory_subcategory(
                        assign_item.value, group["name"], group["parent"])
                    assign_dialog.close()
                    ui.navigate.to("/store-ops/inventory")

                ui.button("この小分類へ入れる", icon="drive_file_move", on_click=save_assignment).classes("w-full")

            def open_assignment(item):
                assign_item.value = item["id"]
                current_group = next((value for value in subcategories
                                      if value["parent"] == item.get("category")
                                      and value["name"] == item.get("subcategory")), None)
                assign_group.value = current_group["id"] if current_group else None
                assign_dialog.open()
            with ui.row().classes("w-full gap-2 q-mb-md"):
                ui.button("小分類と色を設定", icon="palette", on_click=category_dialog.open).props(
                    "outline no-caps").classes("grow")
                ui.button("商品を小分類へ", icon="drive_file_move", on_click=assign_dialog.open).props(
                    "outline no-caps").classes("grow")
        fields = []
        grouped = {}
        for item in items:
            grouped.setdefault(item.get("category", "その他"), []).append(item)
        ordered_names = [value["name"] for value in categories]
        for category in sorted(grouped, key=lambda value: (
                ordered_names.index(value) if value in ordered_names else 999, value)):
            category_items = grouped[category]
            expansion = ui.expansion(f"{category}　{len(category_items)}品", icon="folder",
                                     value=False).classes("surface-card inventory-main-category w-full q-mb-sm")
            with expansion:
                group_names = []
                for item in category_items:
                    name = item.get("subcategory") or "未分類"
                    if name not in group_names:
                        group_names.append(name)
                configured = [value for value in subcategories if value["parent"] == category]
                configured_order = [value["name"] for value in configured]
                group_names.sort(key=lambda name: (configured_order.index(name)
                                                   if name in configured_order else 999, name))
                for group_name in group_names:
                    meta = next((value for value in configured if value["name"] == group_name), {})
                    group_items = [value for value in category_items
                                   if (value.get("subcategory") or "未分類") == group_name]
                    with ui.element("section").classes("inventory-subcategory w-full").style(
                            f"--subcategory-color:{meta.get('color', '#F3F5F4')}"):
                        ui.label(group_name).classes("inventory-subcategory-title")
                        with ui.element("div").classes("inventory-grid-new inventory-sort-grid w-full"):
                            for item in group_items:
                                last_check = str(item.get("last_inventory_check_at", ""))
                                was_reset = bool(reset_at and (not last_check or last_check <= reset_at))
                                with ui.card().classes("inventory-item-new inventory-sort-card").props(
                                        f'data-item-id="{item["id"]}"'):
                                    with ui.column().classes("gap-0 w-full min-w-0"):
                                        with ui.row().classes("w-full items-start no-wrap gap-1"):
                                            ui.label(item["name"]).classes("inventory-item-name grow")
                                            if is_owner:
                                                ui.button(icon="folder_open", on_click=lambda _, value=item:
                                                          open_assignment(value)).props(
                                                    "flat round dense size=sm aria-label='小分類を変更'").classes(
                                                    "inventory-group-button")
                                        minimum = item.get("reorder_point")
                                        unit = item.get("unit", "個")
                                        if minimum is not None:
                                            minimum_text = (str(int(minimum)) if float(minimum).is_integer()
                                                            else str(minimum))
                                            ui.label(f"最低 {minimum_text}{unit}").classes(
                                                "minimum-stock-mark")
                                        else:
                                            ui.label(f"単位 {unit}").classes("inventory-unit")
                                    if item.get("tracking_mode") == "count":
                                        field = ui.number(value=None if was_reset else item.get("current_stock"), step=.1,
                                                          suffix=item.get("unit", "個")).props(
                                                              "outlined dense inputmode=decimal").classes("stock-field")
                                        fields.append((item["id"], "count", field))
                                    else:
                                        field = ui.select({"enough": "十分", "low": "少ない", "out": "なし"},
                                                          value=None if was_reset else item.get("status", "enough")).props(
                                                              "outlined dense options-dense").classes("stock-field")
                                        fields.append((item["id"], "status", field))

        def save_all():
            updates = [{"item_id": item_id, kind: field.value}
                       for item_id, kind, field in fields if field.value not in (None, "")]
            try:
                store_ops.save_inventory_check(updates)
            except ValueError as error:
                ui.notify(str(error), type="negative")
                return
            ui.notify("在庫を保存しました", type="positive")

        ui.button("まとめて保存", icon="save", on_click=save_all).classes("w-full q-mt-md")
        with ui.dialog() as reset_dialog, ui.card().classes("surface-card w-80 q-pa-lg"):
            ui.label("在庫確認をリセットしますか？").classes("text-lg font-black")
            ui.label("現在の入力欄だけを未入力に戻します。商品・確認履歴・管理者の仕入れ予定は消えません。").classes(
                "text-xs text-grey-7 q-mt-sm")

            def reset_check():
                store_ops.reset_inventory_check()
                reset_dialog.close()
                ui.navigate.to("/store-ops/inventory")

            with ui.row().classes("w-full gap-2 q-mt-md"):
                ui.button("戻る", on_click=reset_dialog.close).props("flat").classes("grow")
                ui.button("リセット", icon="restart_alt", on_click=reset_check).props(
                    "unelevated color=negative").classes("grow")

        ui.button("在庫確認をリセット", icon="restart_alt", on_click=reset_dialog.open).props(
            "outline color=negative no-caps").classes("w-full q-mt-sm")
        if is_owner:
            ui.button("仕入れリストを開く", icon="shopping_basket", on_click=lambda: ui.navigate.to(
                "/store-ops/purchase-list")).props("outline no-caps").classes("w-full q-mt-sm")
            ui.on("inventory_reordered", lambda event: store_ops.reorder_inventory_items(
                (event.args or {}).get("ids", [])))
            ui.run_javascript("""
            (() => {
              let card=null, timer=null, active=false, startX=0, startY=0;
              const cancel=()=>{clearTimeout(timer);timer=null;if(card)card.classList.remove('drag-ready','dragging');card=null;active=false};
              document.querySelectorAll('.inventory-sort-card').forEach(el=>{
                el.addEventListener('pointerdown',e=>{if(e.target.closest('.q-field'))return;card=el;startX=e.clientX;startY=e.clientY;el.classList.add('drag-ready');timer=setTimeout(()=>{active=true;el.classList.add('dragging');navigator.vibrate?.(25)},550)});
                el.addEventListener('pointermove',e=>{
                  if(!card)return;
                  if(!active&&Math.hypot(e.clientX-startX,e.clientY-startY)>10){cancel();return}
                  if(!active)return;e.preventDefault();
                  const hit=document.elementFromPoint(e.clientX,e.clientY)?.closest('.inventory-sort-card');
                  if(hit&&hit!==card&&hit.parentElement===card.parentElement){const r=hit.getBoundingClientRect();hit.parentElement.insertBefore(card,(e.clientY>r.top+r.height/2||e.clientX>r.left+r.width/2)?hit.nextSibling:hit)}
                },{passive:false});
                el.addEventListener('pointerup',()=>{if(active&&card){const ids=[...card.parentElement.querySelectorAll('.inventory-sort-card')].map(x=>x.dataset.itemId);emitEvent('inventory_reordered',{ids})}cancel()});
                el.addEventListener('pointercancel',cancel);
              });
            })();
            """)
        ui.add_css("""
        .inventory-grid-new{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;padding:7px 1px 10px}
        .inventory-item-new{display:flex!important;flex-direction:column!important;justify-content:space-between!important;min-width:0!important;min-height:132px;padding:11px!important;border-radius:16px!important;border:1px solid #E1E9E4!important;box-shadow:none!important;background:#fff!important}
        .inventory-item-name{display:-webkit-box;min-height:32px;max-height:32px;overflow:hidden;overflow-wrap:anywhere;-webkit-box-orient:vertical;-webkit-line-clamp:2;font-size:11px;font-weight:950;line-height:1.4;color:#17382C}
        .inventory-unit{margin-top:3px;font-size:8px;color:#8A9690}
        .stock-field{width:100%!important;margin-top:8px}.stock-field .q-field__control{min-height:40px!important;height:40px!important}.stock-field input{font-weight:900!important}
        .minimum-stock-mark{display:inline-flex;width:max-content;max-width:100%;margin-top:3px;padding:2px 6px;border-radius:999px;background:#FFF0CC;color:#8A5A08;font-size:8px;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .inventory-main-category{background:#fff!important}.inventory-subcategory{margin:9px 0 13px;padding:8px;border-radius:17px;background:var(--subcategory-color)}.inventory-subcategory-title{padding:2px 5px 6px;font-size:12px;font-weight:950;color:#17382C}.inventory-group-button{margin:-7px -8px 0 0;color:#527269}.inventory-item-new{touch-action:pan-y;transition:transform .15s,box-shadow .15s}.inventory-item-new.drag-ready{box-shadow:0 4px 12px #17382C22!important}.inventory-item-new.dragging{z-index:20;transform:scale(1.035);box-shadow:0 12px 26px #17382C45!important}
        @media(min-width:760px){.inventory-grid-new{grid-template-columns:repeat(3,minmax(0,1fr))}.inventory-item-new{min-height:142px}.inventory-item-name{font-size:13px}}
        """)


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
