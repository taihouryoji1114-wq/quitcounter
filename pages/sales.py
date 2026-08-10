from datetime import date

from nicegui import ui

from core.auth import require_login
from core.financials import financials
from core.theme import Theme


@ui.page("/mirai-kessan/sales")
def sales_page():
    if not require_login():
        return
    Theme.page("売上入力｜未来決算")
    today = date.today()
    content = Theme.shell(
        "売上入力",
        "その日の売上を、1回入力するだけ",
        back_to="/mirai-kessan",
    )

    with content:
        with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
            sales_date = ui.input("日付", value=today.isoformat()).props(
                "type=date outlined"
            ).classes("w-full q-mb-sm")
            amount = ui.number("その日の売上", min=0, step=1).props(
                "outlined prefix=¥ inputmode=numeric"
            ).classes("w-full q-mb-sm")
            ui.label(
                "同じ日をもう一度保存すると、その日の金額を更新します。"
            ).classes("text-[10px] text-grey-6 q-mb-sm")

            def save_sales():
                try:
                    financials.set_daily_sales(sales_date.value, amount.value)
                except ValueError as error:
                    ui.notify(f"保存できませんでした: {error}", type="negative")
                    return
                summary.refresh()
                history.refresh()
                ui.notify("売上を保存しました", type="positive")

            ui.button("この日の売上を保存", icon="save", on_click=save_sales).classes(
                "w-full"
            )

        @ui.refreshable
        def summary():
            month = (sales_date.value or today.isoformat())[:7]
            with ui.card().classes("surface-card w-full q-pa-md q-mb-md"):
                ui.label(f"{month.replace('-', '年')}月の売上実績").classes(
                    "text-xs text-grey-6"
                )
                ui.label(f"¥{financials.monthly_sales_total(month):,}").classes(
                    "text-3xl font-bold metric-value q-mt-xs"
                )

        summary()

        @ui.refreshable
        def history():
            month = (sales_date.value or today.isoformat())[:7]
            ui.label("日別売上").classes("text-xl font-bold q-mt-md q-mb-sm")
            records = financials.sales_records(month=month)
            if not records:
                ui.label("この月の売上記録はありません。").classes("text-grey-7")
                return
            for record in records:
                with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                    with ui.row().classes("w-full items-center no-wrap"):
                        ui.label(record["date"].replace("-", "/")).classes("font-bold")
                        ui.space()
                        ui.label(f"¥{record['amount']:,}").classes("text-lg font-bold")

                        def delete_record(_, selected=record):
                            financials.delete_sales(selected["id"])
                            summary.refresh()
                            history.refresh()
                            ui.notify("売上記録を削除しました", type="positive")

                        ui.button(icon="delete_outline", on_click=delete_record).props(
                            "flat round color=negative"
                        )

        history()

        def refresh_month():
            summary.refresh()
            history.refresh()

        sales_date.on("change", lambda _: refresh_month())
