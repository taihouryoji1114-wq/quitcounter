from nicegui import ui

from core.auth import require_login
from core.clock import today_jst
from core.purchases import purchases
from core.theme import Theme


@ui.page("/mirai-kessan/shiire")
def purchase_page():
    if not require_login():
        return
    Theme.page("仕入れノート", app_name="mirai-kessan")
    today = today_jst()
    selected_day = [today.isoformat()]
    content = Theme.shell(
        "仕入れノート",
        "普段は合計だけ、必要な時だけ税率別に記録",
        back_to="/mirai-kessan",
    )

    with content:
        with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
            ui.label("仕入れを入力").classes("section-kicker q-mb-md")
            purchase_date = ui.input(
                "日付", value=today.isoformat()
            ).props("type=date outlined").classes("w-full q-mb-sm")
            supplier = ui.input(
                "仕入れ先", placeholder="例：○○市場"
            ).props("outlined autocomplete=organization").classes("w-full q-mb-xs")

            @ui.refreshable
            def supplier_shortcuts():
                values = purchases.suppliers()
                if not values:
                    return
                with ui.dialog() as editor_dialog, ui.card().classes(
                    "surface-card w-80 max-w-full q-pa-lg"
                ):
                    ui.label("仕入れ先候補を編集").classes(
                        "text-xl font-bold q-mb-xs"
                    )
                    ui.label(
                        "削除しても過去の仕入れ記録と金額は残ります。"
                    ).classes("text-xs text-grey-6 q-mb-md")

                    def hide_selected(selected):
                        purchases.hide_supplier(selected)
                        editor_dialog.close()
                        supplier_shortcuts.refresh()
                        ui.notify("候補から削除しました", type="positive")

                    for name in values:
                        with ui.row().classes(
                            "w-full items-center no-wrap q-py-xs"
                        ):
                            ui.label(name).classes("font-bold")
                            ui.space()
                            ui.button(
                                icon="delete_outline",
                                on_click=lambda _, selected=name: hide_selected(selected),
                            ).props("flat round color=negative")
                    ui.button("閉じる", on_click=editor_dialog.close).props(
                        "flat"
                    ).classes("w-full q-mt-sm")

                with ui.row().classes(
                    "w-full items-center justify-between q-mt-xs"
                ):
                    ui.label("最近の仕入れ先").classes("text-xs text-grey-6")
                    ui.button(
                        "候補を編集", icon="edit", on_click=editor_dialog.open
                    ).props("flat dense no-caps").classes("text-xs")
                with ui.row().classes("gap-2 q-mb-sm flex-wrap"):
                    for value in values:
                        ui.button(
                            value,
                            on_click=lambda _, name=value: setattr(supplier, "value", name),
                        ).props("outline dense no-caps")

            supplier_shortcuts()
            entry_mode = ui.toggle(
                {"simple": "合計だけ", "tax": "税率を分けて計算"}, value="simple"
            ).props("spread no-caps").classes("w-full q-mb-sm")
            amount = ui.number(
                "仕入れ合計金額", min=1, step=1
            ).props("outlined prefix=¥ inputmode=numeric").classes("w-full q-mb-sm")
            simple_tax_rate = ui.select(
                {"8": "8％（食品・通常はこちら）", "10": "10％", "1": "1％（制度開始後）"},
                value="8",
                label="消費税率",
            ).props("outlined").classes("w-full q-mb-sm")

            tax_panel = ui.column().classes("w-full gap-2 q-mb-sm")
            tax_panel.bind_visibility_from(
                entry_mode, "value", backward=lambda value: value == "tax"
            )
            amount.bind_visibility_from(
                entry_mode, "value", backward=lambda value: value == "simple"
            )
            simple_tax_rate.bind_visibility_from(
                entry_mode, "value", backward=lambda value: value == "simple"
            )
            with tax_panel:
                price_mode = ui.toggle(
                    {"excluded": "税抜の納品書", "included": "税込の納品書"},
                    value="excluded",
                ).props("spread no-caps").classes("w-full")
                amount_8 = ui.number("8％対象の小計", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                ).classes("w-full")
                amount_10 = ui.number("10％対象の小計", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                ).classes("w-full")
                amount_1 = ui.number(
                    "1％対象の小計（制度開始後に使用）", min=0, step=1
                ).props("outlined prefix=¥ inputmode=numeric").classes("w-full")
                exempt = ui.number("非課税・対象外の小計", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                ).classes("w-full")
                with ui.expansion("商品ごとの金額を足し算する", icon="calculate").classes(
                    "w-full"
                ):
                    ui.label(
                        "小計が書かれていない時に、同じ税率の商品を＋でつないでください。"
                    ).classes("text-xs text-grey-6 q-mb-sm")
                    calc_8 = ui.input(
                        "8％の税抜金額", placeholder="例：1,200+350+980"
                    ).props("outlined autocorrect=off").classes("w-full q-mb-sm")
                    calc_10 = ui.input(
                        "10％の税抜金額", placeholder="例：500+300"
                    ).props("outlined autocorrect=off").classes("w-full q-mb-sm")
                    calc_1 = ui.input(
                        "1％の税抜金額（制度開始後）", placeholder="例：1000+500"
                    ).props("outlined autocorrect=off").classes("w-full q-mb-sm")
                    calc_exempt = ui.input(
                        "非課税・対象外", placeholder="例：200+100"
                    ).props("outlined autocorrect=off").classes("w-full q-mb-sm")

                    def apply_item_sums():
                        try:
                            amount_8.value = purchases.sum_amount_expression(calc_8.value)
                            amount_10.value = purchases.sum_amount_expression(calc_10.value)
                            amount_1.value = purchases.sum_amount_expression(calc_1.value)
                            exempt.value = purchases.sum_amount_expression(calc_exempt.value)
                        except ValueError as error:
                            ui.notify(str(error), type="negative")
                            return
                        price_mode.value = "excluded"
                        calculate_breakdown()
                        ui.notify("税率ごとの税抜小計へ反映しました", type="positive")

                    ui.button(
                        "足し算して小計へ反映", icon="add", on_click=apply_item_sums
                    ).classes("w-full")
                rounding = ui.select(
                    {"floor": "切り捨て", "half_up": "四捨五入", "ceil": "切り上げ"},
                    value="floor",
                    label="納品書の端数処理",
                ).props("outlined").classes("w-full")
                with ui.expansion("納品書記載の税額と合わない場合").classes("w-full"):
                    ui.label("空欄なら自動計算します。記載額が違う時だけ入力してください。").classes(
                        "text-xs text-grey-6 q-mb-sm"
                    )
                    stated_tax_8 = ui.number("記載されている8％税額", min=0, step=1).props(
                        "outlined prefix=¥ inputmode=numeric"
                    ).classes("w-full q-mb-sm")
                    stated_tax_10 = ui.number("記載されている10％税額", min=0, step=1).props(
                        "outlined prefix=¥ inputmode=numeric"
                    ).classes("w-full")
                    stated_tax_1 = ui.number("記載されている1％税額", min=0, step=1).props(
                        "outlined prefix=¥ inputmode=numeric"
                    ).classes("w-full")
                tax_result = ui.label().classes(
                    "w-full rounded-xl bg-green-50 text-green-900 q-pa-md font-bold"
                )

                def calculate_breakdown(notify=False):
                    try:
                        result = purchases.calculate_tax_breakdown(
                            amount_8=amount_8.value,
                            amount_10=amount_10.value,
                            exempt=exempt.value,
                            price_mode=price_mode.value,
                            rounding=rounding.value,
                            stated_tax_8=stated_tax_8.value,
                            stated_tax_10=stated_tax_10.value,
                            amount_1=amount_1.value,
                            stated_tax_1=stated_tax_1.value,
                        )
                    except ValueError as error:
                        tax_result.text = "金額を入力すると合計を表示します"
                        if notify:
                            ui.notify(str(error), type="negative")
                        return None
                    tax_result.text = (
                        f"消費税 ¥{result['tax_1'] + result['tax_8'] + result['tax_10']:,}　"
                        f"支払合計 ¥{result['total']:,}"
                    )
                    return result

                for field in (
                    amount_1, amount_8, amount_10, exempt,
                    stated_tax_1, stated_tax_8, stated_tax_10,
                ):
                    field.on("update:model-value", lambda _: calculate_breakdown())
                price_mode.on("update:model-value", lambda _: calculate_breakdown())
                rounding.on("update:model-value", lambda _: calculate_breakdown())
                calculate_breakdown()

            invoice_status = ui.select(
                {
                    "registered": "インボイスあり",
                    "unregistered": "インボイスなし",
                    "unknown": "不明・あとで確認",
                },
                value="unknown",
                label="インボイス",
            ).props("outlined").classes("w-full q-mb-sm")
            purchase_kind = ui.toggle(
                {
                    "cost": "原価（食材）",
                    "operating_supply": "営業用消耗品",
                    "expense": "一般経費",
                },
                value="cost",
            ).props("spread no-caps").classes("w-full q-mb-xs")
            ui.label(
                "ガスボンベ・袋・容器などは営業用消耗品、接待交際費・会議費・交通費などは一般経費"
            ).classes("text-[10px] text-grey-6 q-mb-sm")

            def save_purchase():
                try:
                    if entry_mode.value == "tax":
                        breakdown = calculate_breakdown(True)
                    else:
                        simple_amounts = {
                            "amount_1": amount.value if simple_tax_rate.value == "1" else 0,
                            "amount_8": amount.value if simple_tax_rate.value == "8" else 0,
                            "amount_10": amount.value if simple_tax_rate.value == "10" else 0,
                        }
                        breakdown = purchases.calculate_tax_breakdown(
                            price_mode="included", **simple_amounts
                        )
                    if entry_mode.value == "tax" and breakdown is None:
                        return
                    total = breakdown["total"]
                    purchases.add(
                        purchase_date.value,
                        supplier.value,
                        total,
                        purchase_kind.value,
                        breakdown,
                        invoice_status.value,
                    )
                except (RuntimeError, ValueError) as error:
                    ui.notify(f"保存できませんでした: {error}", type="negative")
                    return
                amount.value = None
                amount_1.value = amount_8.value = amount_10.value = exempt.value = None
                calc_1.value = calc_8.value = calc_10.value = calc_exempt.value = ""
                stated_tax_1.value = stated_tax_8.value = stated_tax_10.value = None
                supplier_shortcuts.refresh()
                totals.refresh()
                history.refresh()
                ui.notify("仕入れを保存しました", type="positive")

            ui.button(
                "この仕入れを登録", icon="add", on_click=save_purchase
            ).classes("w-full")

        @ui.refreshable
        def totals():
            day = selected_day[0]
            month = day[:7]
            with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                ui.label(
                    f"選択日 {day.replace('-', '/')} の合計"
                ).classes("text-xs text-grey-6")
                ui.label(f"¥{purchases.daily_total(day):,}").classes(
                    "text-2xl font-bold metric-value q-mt-xs"
                )
            with ui.element("div").classes("grid grid-cols-3 gap-2 w-full q-mb-md"):
                with ui.card().classes("surface-card q-pa-md"):
                    ui.label(f"{month.replace('-', '年')}月累計・原価").classes(
                        "text-xs text-grey-6"
                    )
                    ui.label(
                        f"¥{purchases.monthly_total(month, kind='cost'):,}"
                    ).classes(
                        "text-xl font-bold metric-value q-mt-xs"
                    )
                with ui.card().classes("surface-card q-pa-md"):
                    ui.label(f"{month.replace('-', '年')}月累計・営業用消耗品").classes(
                        "text-xs text-grey-6"
                    )
                    ui.label(
                        f"¥{purchases.monthly_total(month, kind='operating_supply'):,}"
                    ).classes(
                        "text-xl font-bold metric-value q-mt-xs"
                    )
                with ui.card().classes("surface-card q-pa-md"):
                    ui.label(f"{month.replace('-', '年')}月累計・一般経費").classes(
                        "text-xs text-grey-6"
                    )
                    ui.label(
                        f"¥{purchases.monthly_total(month, kind='expense'):,}"
                    ).classes("text-xl font-bold metric-value q-mt-xs")

        totals()
        def refresh_selected_day(value=None):
            if value:
                selected_day[0] = str(value)
            totals.refresh()
            history.refresh()

        @ui.refreshable
        def history():
            day = selected_day[0]
            ui.label(
                f"{day.replace('-', '/')} の仕入れ履歴"
            ).classes("text-xl font-bold q-mt-md q-mb-sm")
            records = purchases.records(record_date=day)
            if not records:
                ui.label("この日の仕入れ記録はありません。").classes("text-grey-7")
                return
            for record in records:
                with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                    with ui.row().classes("w-full items-center no-wrap"):
                        with ui.column().classes("gap-0"):
                            ui.label(record["supplier"]).classes("font-bold")
                            kind = record.get("kind", "cost")
                            kind_label = {
                                "cost": "原価（食材）",
                                "operating_supply": "営業用消耗品",
                                "expense": "一般経費",
                            }.get(kind, "一般経費")
                            kind_color = {
                                "cost": "primary",
                                "operating_supply": "blue",
                                "expense": "orange",
                            }.get(kind, "orange")
                            ui.badge(kind_label).props(f"color={kind_color}")
                            breakdown = record.get("tax_breakdown")
                            if breakdown:
                                mode = "税込" if breakdown["price_mode"] == "included" else "税抜"
                                ui.label(f"{mode}・消費税の内訳").classes(
                                    "text-[10px] font-bold text-grey-7 q-mt-xs"
                                )
                                tax_lines = []
                                for rate in (1, 8, 10):
                                    taxable = int(breakdown.get(f"amount_{rate}", 0))
                                    tax = int(breakdown.get(f"tax_{rate}", 0))
                                    if taxable or tax:
                                        tax_lines.append(
                                            f"{rate}％対象 ¥{taxable:,}（税 ¥{tax:,}）"
                                        )
                                if breakdown.get("exempt", 0):
                                    tax_lines.append(
                                        f"非課税・対象外 ¥{int(breakdown['exempt']):,}"
                                    )
                                ui.label(" ／ ".join(tax_lines)).classes(
                                    "text-xs text-grey-7"
                                )
                        ui.space()
                        with ui.column().classes("items-end gap-0"):
                            ui.label("支払合計").classes("text-[9px] text-grey-6")
                            ui.label(f"¥{record['total']:,}").classes("text-lg font-bold")

                        def open_edit(_, selected=record):
                            existing = selected.get("tax_breakdown") or {}
                            existing_simple_rate = (
                                "1" if existing.get("amount_1", 0) > 0
                                else "10" if existing.get("amount_10", 0) > 0
                                else "8"
                            )
                            with ui.dialog() as edit_dialog, ui.card().classes(
                                "surface-card w-[420px] max-w-full q-pa-lg"
                            ):
                                ui.label("仕入れ記録を編集").classes(
                                    "text-xl font-bold q-mb-md"
                                )
                                edit_date = ui.input(
                                    "日付", value=selected["date"]
                                ).props("type=date outlined").classes("w-full")
                                edit_supplier = ui.input(
                                    "仕入れ先", value=selected["supplier"]
                                ).props("outlined").classes("w-full")
                                edit_mode = ui.toggle(
                                    {"simple": "合計だけ", "tax": "税率別"},
                                    value="tax" if existing else "simple",
                                ).props("spread no-caps").classes("w-full")
                                edit_total = ui.number(
                                    "仕入れ合計金額",
                                    value=selected["total"], min=1, step=1,
                                ).props("outlined prefix=¥ inputmode=numeric").classes("w-full")
                                edit_total.bind_visibility_from(
                                    edit_mode, "value",
                                    backward=lambda value: value == "simple",
                                )
                                edit_simple_tax_rate = ui.select(
                                    {
                                        "8": "8％（食品・通常はこちら）",
                                        "10": "10％",
                                        "1": "1％（制度開始後）",
                                    },
                                    value=existing_simple_rate,
                                    label="消費税率",
                                ).props("outlined").classes("w-full")
                                edit_simple_tax_rate.bind_visibility_from(
                                    edit_mode, "value",
                                    backward=lambda value: value == "simple",
                                )
                                edit_tax_panel = ui.column().classes("w-full gap-2")
                                edit_tax_panel.bind_visibility_from(
                                    edit_mode, "value",
                                    backward=lambda value: value == "tax",
                                )
                                with edit_tax_panel:
                                    edit_price_mode = ui.toggle(
                                        {"excluded": "税抜", "included": "税込"},
                                        value=existing.get("price_mode", "included"),
                                    ).props("spread no-caps").classes("w-full")
                                    edit_amount_8 = ui.number(
                                        "8％対象額",
                                        value=existing.get(
                                            "amount_8", selected["total"] if not existing else 0
                                        ),
                                        min=0, step=1,
                                    ).props("outlined prefix=¥ inputmode=numeric").classes("w-full")
                                    edit_amount_10 = ui.number(
                                        "10％対象額",
                                        value=existing.get("amount_10", 0),
                                        min=0, step=1,
                                    ).props("outlined prefix=¥ inputmode=numeric").classes("w-full")
                                    edit_amount_1 = ui.number(
                                        "1％対象額（制度開始後に使用）",
                                        value=existing.get("amount_1", 0), min=0, step=1,
                                    ).props("outlined prefix=¥ inputmode=numeric").classes("w-full")
                                    edit_exempt = ui.number(
                                        "非課税・対象外額", value=existing.get("exempt", 0),
                                        min=0, step=1,
                                    ).props("outlined prefix=¥ inputmode=numeric").classes("w-full")
                                    edit_rounding = ui.select(
                                        {"floor": "切り捨て", "half_up": "四捨五入", "ceil": "切り上げ"},
                                        value=existing.get("rounding", "floor"),
                                        label="端数処理",
                                    ).props("outlined").classes("w-full")
                                    edit_tax_8 = ui.number(
                                        "納品書記載の8％税額",
                                        value=existing.get("tax_8"), min=0, step=1,
                                    ).props("outlined prefix=¥ inputmode=numeric").classes("w-full")
                                    edit_tax_10 = ui.number(
                                        "納品書記載の10％税額",
                                        value=existing.get("tax_10"), min=0, step=1,
                                    ).props("outlined prefix=¥ inputmode=numeric").classes("w-full")
                                    edit_tax_1 = ui.number(
                                        "納品書記載の1％税額",
                                        value=existing.get("tax_1"), min=0, step=1,
                                    ).props("outlined prefix=¥ inputmode=numeric").classes("w-full")
                                edit_invoice = ui.select(
                                    {
                                        "registered": "インボイスあり",
                                        "unregistered": "インボイスなし",
                                        "unknown": "不明・あとで確認",
                                    },
                                    value=selected.get("invoice_status", "unknown"),
                                    label="インボイス",
                                ).props("outlined").classes("w-full")
                                edit_kind = ui.toggle(
                                    {
                                        "cost": "原価（食材）",
                                        "operating_supply": "営業用消耗品",
                                        "expense": "一般経費",
                                    },
                                    value=selected.get("kind", "cost"),
                                ).props("spread no-caps").classes("w-full")

                                def save_edit():
                                    try:
                                        if edit_mode.value == "tax":
                                            edited_breakdown = purchases.calculate_tax_breakdown(
                                                amount_8=edit_amount_8.value,
                                                amount_10=edit_amount_10.value,
                                                exempt=edit_exempt.value,
                                                price_mode=edit_price_mode.value,
                                                rounding=edit_rounding.value,
                                                stated_tax_8=edit_tax_8.value,
                                                stated_tax_10=edit_tax_10.value,
                                                amount_1=edit_amount_1.value,
                                                stated_tax_1=edit_tax_1.value,
                                            )
                                            edited_total = edited_breakdown["total"]
                                        else:
                                            edited_total = edit_total.value
                                            simple_amounts = {
                                                "amount_1": edited_total if edit_simple_tax_rate.value == "1" else 0,
                                                "amount_8": edited_total if edit_simple_tax_rate.value == "8" else 0,
                                                "amount_10": edited_total if edit_simple_tax_rate.value == "10" else 0,
                                            }
                                            edited_breakdown = purchases.calculate_tax_breakdown(
                                                price_mode="included", **simple_amounts
                                            )
                                        purchases.update(
                                            selected["id"], edit_date.value,
                                            edit_supplier.value, edited_total,
                                            edit_kind.value, edited_breakdown,
                                            edit_invoice.value,
                                        )
                                    except (RuntimeError, ValueError) as error:
                                        ui.notify(f"変更できませんでした: {error}", type="negative")
                                        return
                                    edit_dialog.close()
                                    supplier_shortcuts.refresh()
                                    totals.refresh()
                                    history.refresh()
                                    ui.notify("仕入れ記録を変更しました", type="positive")

                                with ui.row().classes("w-full gap-2 q-mt-md"):
                                    ui.button("キャンセル", on_click=edit_dialog.close).props(
                                        "flat"
                                    ).classes("flex-1")
                                    ui.button(
                                        "変更を保存", icon="save", on_click=save_edit
                                    ).classes("flex-1")
                            edit_dialog.open()

                        def confirm_delete(_, selected=record):
                            with ui.dialog() as dialog, ui.card().classes(
                                "surface-card w-80 q-pa-lg"
                            ):
                                ui.label("この仕入れを削除しますか？").classes(
                                    "text-xl font-bold"
                                )
                                ui.label(
                                    f"{selected['supplier']}　¥{selected['total']:,}"
                                ).classes("text-grey-7 q-mb-md")

                                def delete_selected():
                                    purchases.delete(selected["id"])
                                    dialog.close()
                                    totals.refresh()
                                    history.refresh()
                                    ui.notify("仕入れ記録を削除しました", type="positive")

                                with ui.row().classes("w-full gap-2"):
                                    ui.button("キャンセル", on_click=dialog.close).props(
                                        "flat"
                                    ).classes("flex-1")
                                    ui.button(
                                        "削除", icon="delete", on_click=delete_selected
                                    ).props("color=negative").classes("flex-1")
                            dialog.open()

                        ui.button(icon="edit", on_click=open_edit).props(
                            "flat round aria-label='編集'"
                        )
                        ui.button(icon="delete_outline", on_click=confirm_delete).props(
                            "flat round color=negative"
                        )

        history()

        purchase_date.on_value_change(
            lambda event: refresh_selected_day(event.value)
        )
        purchase_date.on(
            "change",
            lambda event: refresh_selected_day(event.args),
            js_handler="(event) => emit(event.target.value)",
        )


@ui.page("/shiire")
def legacy_purchase_page():
    """Keep old bookmarks working while the page lives inside the PWA scope."""
    ui.navigate.to("/mirai-kessan/shiire")
