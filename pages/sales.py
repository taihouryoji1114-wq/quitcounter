from nicegui import ui

from core.auth import require_login
from core.clock import today_jst
from core.financials import financials
from core.theme import Theme


@ui.page("/mirai-kessan/sales")
def sales_page():
    if not require_login():
        return
    Theme.page("売上入力｜未来決算", app_name="mirai-kessan")
    today = today_jst()
    selected_day = [today.isoformat()]
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
            with ui.card().classes("w-full q-pa-md q-mb-sm").style(
                "background:#FFF9F1;border:1px solid #F0DFC9;border-radius:18px"
            ):
                ui.label("ランチ").classes("font-bold q-mb-sm")
                lunch_sales = ui.number("売上", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                ).classes("w-full q-mb-sm")
                lunch_customers = ui.number("人数", min=0, step=1).props(
                    "outlined suffix=人 inputmode=numeric"
                ).classes("w-full")
            with ui.card().classes("w-full q-pa-md q-mb-sm").style(
                "background:#F5F3FF;border:1px solid #DDD7F2;border-radius:18px"
            ):
                ui.label("ディナー").classes("font-bold q-mb-sm")
                dinner_sales = ui.number("売上", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                ).classes("w-full q-mb-sm")
                dinner_customers = ui.number("人数", min=0, step=1).props(
                    "outlined suffix=人 inputmode=numeric"
                ).classes("w-full")
            ui.label(
                "同じ日をもう一度保存すると、その日の金額を更新します。"
            ).classes("text-[10px] text-grey-6 q-mb-sm")

            def save_sales():
                try:
                    financials.set_daily_sales(
                        selected_day[0],
                        lunch_sales=lunch_sales.value,
                        dinner_sales=dinner_sales.value,
                        lunch_customers=lunch_customers.value,
                        dinner_customers=dinner_customers.value,
                    )
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
            month = selected_day[0][:7]
            values = financials.monthly_sales_summary(month)
            with ui.card().classes("surface-card w-full q-pa-md q-mb-md"):
                ui.label(f"{month.replace('-', '年')}月の売上実績").classes(
                    "text-xs text-grey-6"
                )
                ui.label(f"¥{values['total']:,}").classes(
                    "text-3xl font-bold metric-value q-mt-xs"
                )
                with ui.element("div").classes("grid grid-cols-2 gap-2 w-full q-mt-md"):
                    for title, sales, customers, spend in (
                        ("ランチ", values["lunch_sales"], values["lunch_customers"], values["lunch_spend"]),
                        ("ディナー", values["dinner_sales"], values["dinner_customers"], values["dinner_spend"]),
                    ):
                        with ui.element("div").classes("rounded-xl bg-grey-2 q-pa-sm"):
                            ui.label(title).classes("text-xs text-grey-7")
                            ui.label(f"¥{sales:,}・{customers}人").classes("font-bold")
                            ui.label(f"客単価 ¥{spend:,}" if customers else "客単価 —").classes(
                                "text-[10px] text-grey-6"
                            )

        summary()

        @ui.refreshable
        def history():
            day = selected_day[0]
            ui.label(
                f"{day.replace('-', '/')} の売上"
            ).classes("text-xl font-bold q-mt-md q-mb-sm")
            records = financials.sales_records(record_date=day)
            if not records:
                ui.label("この日の売上記録はありません。").classes("text-grey-7")
                return
            for record in records:
                with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                    with ui.row().classes("w-full items-center no-wrap"):
                        ui.label(record["date"].replace("-", "/")).classes("font-bold")
                        ui.space()
                        ui.label(f"¥{record['amount']:,}").classes("text-lg font-bold")
                        split = "lunch_sales" in record
                        if split:
                            ui.label(
                                f"昼 ¥{record.get('lunch_sales', 0):,}・{record.get('lunch_customers', 0)}人 / "
                                f"夜 ¥{record.get('dinner_sales', 0):,}・{record.get('dinner_customers', 0)}人"
                            ).classes("text-[10px] text-grey-6")

                        def delete_record(_, selected=record):
                            financials.delete_sales(selected["id"])
                            summary.refresh()
                            history.refresh()
                            ui.notify("売上記録を削除しました", type="positive")

                        ui.button(icon="delete_outline", on_click=delete_record).props(
                            "flat round color=negative"
                        )

        history()

        def select_sales_day(value=None):
            if value:
                selected_day[0] = str(value)
            records = financials.sales_records(record_date=selected_day[0])
            record = records[0] if records else {}
            lunch_sales.value = record.get("lunch_sales") or None
            dinner_sales.value = record.get("dinner_sales") or None
            lunch_customers.value = record.get("lunch_customers") or None
            dinner_customers.value = record.get("dinner_customers") or None
            summary.refresh()
            history.refresh()

        sales_date.on_value_change(
            lambda event: select_sales_day(event.value)
        )
        sales_date.on(
            "change",
            lambda event: select_sales_day(event.args),
            js_handler="(event) => emit(event.target.value)",
        )
