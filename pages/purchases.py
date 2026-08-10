from datetime import date

from nicegui import ui

from core.auth import require_login
from core.purchases import purchases
from core.theme import Theme


@ui.page("/shiire")
def purchase_page():
    if not require_login():
        return
    Theme.page("仕入れノート")
    today = date.today()
    selected_month = [today.strftime("%Y-%m")]
    content = Theme.shell(
        "仕入れノート",
        "日付・仕入れ先・金額だけで、すばやく記録",
        back_to="/",
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
                values = purchases.suppliers()[:6]
                if not values:
                    return
                def open_supplier_editor():
                    with ui.dialog() as dialog, ui.card().classes(
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
                            dialog.close()
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
                        ui.button("閉じる", on_click=dialog.close).props(
                            "flat"
                        ).classes("w-full q-mt-sm")

                with ui.row().classes(
                    "w-full items-center justify-between q-mt-xs"
                ):
                    ui.label("最近の仕入れ先").classes("text-xs text-grey-6")
                    ui.button(
                        "候補を編集", icon="edit", on_click=open_supplier_editor
                    ).props("flat dense no-caps").classes("text-xs")
                with ui.row().classes("gap-2 q-mb-sm flex-wrap"):
                    for value in values:
                        ui.button(
                            value,
                            on_click=lambda _, name=value: setattr(supplier, "value", name),
                        ).props("outline dense no-caps")

            supplier_shortcuts()
            amount = ui.number(
                "仕入れ合計金額", min=1, step=1
            ).props("outlined prefix=¥ inputmode=numeric").classes("w-full q-mb-sm")

            def save_purchase():
                try:
                    purchases.add(purchase_date.value, supplier.value, amount.value)
                except (RuntimeError, ValueError) as error:
                    ui.notify(f"保存できませんでした: {error}", type="negative")
                    return
                amount.value = None
                supplier_shortcuts.refresh()
                totals.refresh()
                history.refresh()
                ui.notify("仕入れを保存しました", type="positive")

            ui.button(
                "この仕入れを登録", icon="add", on_click=save_purchase
            ).classes("w-full")

        @ui.refreshable
        def totals():
            day = purchase_date.value or today.isoformat()
            month = day[:7]
            with ui.element("div").classes("grid grid-cols-2 gap-3 w-full q-mb-md"):
                with ui.card().classes("surface-card q-pa-md"):
                    ui.label("選択日の合計").classes("text-xs text-grey-6")
                    ui.label(f"¥{purchases.daily_total(day):,}").classes(
                        "text-2xl font-bold metric-value q-mt-xs"
                    )
                with ui.card().classes("surface-card q-pa-md"):
                    ui.label(f"{month.replace('-', '年')}月の合計").classes(
                        "text-xs text-grey-6"
                    )
                    ui.label(f"¥{purchases.monthly_total(month):,}").classes(
                        "text-2xl font-bold metric-value q-mt-xs"
                    )

        totals()
        purchase_date.on("change", lambda _: totals.refresh())

        with ui.row().classes("w-full items-center justify-between q-mt-md q-mb-sm"):
            ui.label("仕入れ履歴").classes("text-xl font-bold")
            month_filter = ui.input(
                "表示月", value=selected_month[0]
            ).props("type=month outlined dense").classes("w-36")

        @ui.refreshable
        def history():
            records = purchases.records(month_filter.value)
            if not records:
                ui.label("この月の仕入れ記録はありません。").classes("text-grey-7")
                return
            current_day = None
            for record in records:
                if record["date"] != current_day:
                    current_day = record["date"]
                    ui.label(
                        f"{current_day.replace('-', '/')}　合計 ¥{purchases.daily_total(current_day):,}"
                    ).classes("section-kicker q-mt-md q-mb-xs")
                with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                    with ui.row().classes("w-full items-center no-wrap"):
                        with ui.column().classes("gap-0"):
                            ui.label(record["supplier"]).classes("font-bold")
                            ui.label(record["date"]).classes("text-xs text-grey-6")
                        ui.space()
                        ui.label(f"¥{record['total']:,}").classes("text-lg font-bold")

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

                        ui.button(icon="delete_outline", on_click=confirm_delete).props(
                            "flat round color=negative"
                        )

        history()
        month_filter.on("change", lambda _: history.refresh())
