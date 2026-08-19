import calendar
from datetime import date

from nicegui import ui

from core.auth import require_app_access, require_permission
from core.clock import today_jst
from core.financials import financials
from core.theme import Theme


@ui.page("/mirai-kessan/sales")
def sales_page():
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_input", "/mirai-kessan/login"):
        return
    Theme.page("売上入力｜未来決算", app_name="mirai-kessan")
    today = today_jst()
    selected_day = [today.isoformat()]
    viewed_month = [today.strftime("%Y-%m")]
    content = Theme.shell(
        "売上入力",
        "その日の売上を、1回入力するだけ",
        back_to="/mirai-kessan/dashboard",
    )

    with content:
        calendar_slot = ui.column().classes("w-full")

        with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
            with ui.card().classes("w-full q-pa-md q-mb-sm").style(
                "background:#FFF9F1;border:1px solid #F0DFC9;border-radius:18px"
            ):
                ui.label("ランチ").classes("font-bold q-mb-sm")
                lunch_sales = ui.number("売上", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                ).classes("w-full q-mb-sm")
                lunch_customers = ui.number("人数（任意）", min=0, step=1).props(
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
            ui.label("決済方法別の売上").classes("font-bold q-mt-sm q-mb-xs")
            ui.label(
                "ランチ＋ディナーの合計と同じ金額になるように入力してください。"
            ).classes("text-[10px] text-grey-6 q-mb-sm")
            with ui.element("div").classes("grid grid-cols-2 gap-2 w-full q-mb-sm"):
                cash_sales = ui.number("現金", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                )
                credit_sales = ui.number("クレジット", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                )
                paypay_sales = ui.number("PayPay", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                )
                electronic_money_sales = ui.number("電子マネー", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                )
                travel_agency_sales = ui.number("旅行社", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                )
                tabelog_points_sales = ui.number("食べログポイント", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                )
                hotpepper_points_sales = ui.number("ホットペッパーポイント", min=0, step=1).props(
                    "outlined prefix=¥ inputmode=numeric"
                )
            ui.label("グルメサイトのポイントは後日振り込まれる売上として扱います。").classes(
                "text-[10px] text-grey-6 q-mb-sm"
            )
            ui.label(
                "同じ日をもう一度保存すると、その日の金額を更新します。"
            ).classes("text-[10px] text-grey-6 q-mb-sm")

            def save_sales():
                record_date = selected_day[0]
                try:
                    financials.set_daily_sales(
                        record_date,
                        lunch_sales=lunch_sales.value,
                        dinner_sales=dinner_sales.value,
                        lunch_customers=lunch_customers.value,
                        dinner_customers=dinner_customers.value,
                        cash_sales=cash_sales.value,
                        credit_sales=credit_sales.value,
                        paypay_sales=paypay_sales.value,
                        electronic_money_sales=electronic_money_sales.value,
                        travel_agency_sales=travel_agency_sales.value,
                        tabelog_points_sales=tabelog_points_sales.value,
                        hotpepper_points_sales=hotpepper_points_sales.value,
                    )
                except ValueError as error:
                    ui.notify(f"保存できませんでした: {error}", type="negative")
                    return
                summary.refresh()
                history.refresh()
                sales_calendar.refresh()
                ui.notify("売上を保存しました", type="positive")

            ui.button("この日の売上を保存", icon="save", on_click=save_sales).classes(
                "w-full"
            )

        with ui.expansion("決済手数料率を設定", icon="percent").classes(
            "surface-card w-full q-mb-md"
        ):
            fee_rates = financials.get_payment_fee_rates()
            credit_fee = ui.number(
                "クレジット手数料", value=fee_rates["credit"] or None, min=0, max=100, step=0.01
            ).props("outlined suffix=% inputmode=decimal").classes("w-full q-mb-sm")
            paypay_fee = ui.number(
                "PayPay手数料", value=fee_rates["paypay"] or None, min=0, max=100, step=0.01
            ).props("outlined suffix=% inputmode=decimal").classes("w-full q-mb-sm")
            electronic_money_fee = ui.number(
                "電子マネー手数料", value=fee_rates["electronic_money"] or None, min=0, max=100, step=0.01
            ).props("outlined suffix=% inputmode=decimal").classes("w-full q-mb-sm")
            travel_agency_fee = ui.number(
                "旅行社手数料", value=fee_rates["travel_agency"] or None, min=0, max=100, step=0.01
            ).props("outlined suffix=% inputmode=decimal").classes("w-full q-mb-sm")
            def save_fee_rates():
                try:
                    financials.save_payment_fee_rates({
                        "credit": credit_fee.value,
                        "paypay": paypay_fee.value,
                        "electronic_money": electronic_money_fee.value,
                        "travel_agency": travel_agency_fee.value,
                    })
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                summary.refresh()
                ui.notify("決済手数料率を保存しました", type="positive")

            ui.button("手数料率を保存", icon="save", on_click=save_fee_rates).classes(
                "w-full"
            )

        @ui.refreshable
        def summary():
            month = selected_day[0][:7]
            values = financials.monthly_sales_summary(month)
            payments = financials.monthly_payment_summary(month)
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
                ui.separator().classes("q-my-md")
                ui.label("決済別・月累計").classes("text-xs font-bold text-grey-7")
                ui.label(
                    f"現金 ¥{payments['cash_sales']:,}　カード ¥{payments['credit_sales']:,}　"
                    f"PayPay ¥{payments['paypay_sales']:,}　電子マネー ¥{payments['electronic_money_sales']:,}　"
                    f"旅行社 ¥{payments['travel_agency_sales']:,}　"
                    f"ポイント ¥{payments['tabelog_points_sales'] + payments['hotpepper_points_sales']:,}"
                ).classes("text-[10px] text-grey-7 q-mt-xs")
                if payments["unclassified_sales"]:
                    ui.label(
                        f"決済内訳未登録 ¥{payments['unclassified_sales']:,}"
                    ).classes("text-[10px] text-orange-8 q-mt-xs")
                ui.label(
                    f"決済手数料見込 ¥{payments['total_fees']:,}"
                ).classes("font-bold q-mt-sm")

        summary()

        def select_sales_day(value=None):
            if value:
                selected_day[0] = str(value)
            records = financials.sales_records(record_date=selected_day[0])
            record = records[0] if records else {}
            lunch_sales.value = record.get("lunch_sales") or None
            dinner_sales.value = record.get("dinner_sales") or None
            lunch_customers.value = record.get("lunch_customers") or None
            dinner_customers.value = record.get("dinner_customers") or None
            cash_sales.value = record.get("cash_sales") or None
            credit_sales.value = record.get("credit_sales") or None
            paypay_sales.value = record.get("paypay_sales") or None
            electronic_money_sales.value = record.get("electronic_money_sales") or None
            travel_agency_sales.value = record.get("travel_agency_sales") or None
            tabelog_points_sales.value = record.get("tabelog_points_sales") or None
            hotpepper_points_sales.value = record.get("hotpepper_points_sales") or None
            summary.refresh()
            history.refresh()
            sales_calendar.refresh()

        @ui.refreshable
        def sales_calendar():
            month_text = viewed_month[0]
            year, month = (int(part) for part in month_text.split("-"))
            ui.label("売上入力カレンダー").classes("text-xl font-bold q-mt-md q-mb-xs")
            ui.label("赤い『未』は未入力、黄色の『途中』は一部だけ入力済みです。").classes(
                "text-xs text-grey-6 q-mb-sm"
            )
            with ui.card().classes("surface-card w-full q-pa-sm q-mb-md"):
                def move_month(offset):
                    month_index = year * 12 + month - 1 + offset
                    target_year, target_month_index = divmod(month_index, 12)
                    viewed_month[0] = f"{target_year:04d}-{target_month_index + 1:02d}"
                    sales_calendar.refresh()

                with ui.row().classes("w-full items-center justify-between q-mb-sm"):
                    ui.button("前月", icon="chevron_left", on_click=lambda: move_month(-1)).props(
                        "flat dense"
                    )
                    ui.label(f"{year}年{month}月").classes("font-bold text-lg")
                    ui.button("翌月", icon="chevron_right", on_click=lambda: move_month(1)).props(
                        "flat dense icon-right"
                    )
                with ui.element("div").classes("grid grid-cols-7 gap-1 w-full"):
                    for weekday in ("月", "火", "水", "木", "金", "土", "日"):
                        ui.label(weekday).classes("text-center text-xs text-grey-6 q-py-xs")
                    for week in calendar.monthcalendar(year, month):
                        for day_number in week:
                            if not day_number:
                                ui.element("div")
                                continue
                            day_value = f"{year:04d}-{month:02d}-{day_number:02d}"
                            day_date = date(year, month, day_number)
                            status = financials.sales_completion_status(day_value)
                            complete = status == "complete"
                            partial = status == "partial"
                            missing = day_date <= today and status == "missing"
                            selected = day_value == selected_day[0]
                            background = (
                                "#EAF5EE" if complete else "#FFF3D9" if partial
                                else "#FDECEC" if missing else "#F7F7F5"
                            )
                            border = "2px solid #355E4B" if selected else "1px solid #E2E4DF"
                            with ui.element("div").classes(
                                "q-pa-xs cursor-pointer flex flex-col items-center justify-center"
                            ).style(
                                f"min-height:52px;border-radius:12px;background:{background};border:{border}"
                            ).on("click", lambda _, value=day_value: select_sales_day(value)):
                                ui.label(str(day_number)).classes("text-xs")
                                if missing:
                                    ui.label("未").classes("text-lg font-black text-red-7")
                                elif partial:
                                    ui.label("途中").classes("text-xs font-black text-orange-8")
                                elif complete:
                                    ui.icon("check", color="positive", size="18px")

        with calendar_slot:
            sales_calendar()

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
                    with ui.row().classes("w-full items-center no-wrap q-mb-md"):
                        with ui.column().classes("gap-0"):
                            ui.label("選択日の売上合計").classes("text-[10px] text-grey-6")
                            ui.label(record["date"].replace("-", "/")).classes("font-bold")
                        ui.space()
                        ui.label(f"¥{record['amount']:,}").classes("text-2xl font-bold metric-value")

                        def delete_record(_, selected=record):
                            financials.delete_sales(selected["id"])
                            summary.refresh()
                            history.refresh()
                            sales_calendar.refresh()
                            ui.notify("売上記録を削除しました", type="positive")

                        ui.button(icon="delete_outline", on_click=delete_record).props(
                            "flat round color=negative"
                        )
                    ui.label("時間帯別").classes("text-xs font-bold text-grey-7 q-mb-xs")
                    with ui.element("div").classes("grid grid-cols-2 gap-2 w-full q-mb-md"):
                        for label, sales_field, customer_field, color in (
                            ("ランチ", "lunch_sales", "lunch_customers", "#FFF5E8"),
                            ("ディナー", "dinner_sales", "dinner_customers", "#F1EFFF"),
                        ):
                            with ui.element("div").classes("rounded-xl q-pa-sm").style(
                                f"background:{color}"
                            ):
                                ui.label(label).classes("text-[10px] text-grey-7")
                                ui.label(f"¥{int(record.get(sales_field, 0)):,}").classes("font-bold")
                                customers = record.get(customer_field)
                                ui.label(
                                    f"{customers}人" if customers is not None else "人数 未入力"
                                ).classes("text-[10px] text-grey-6")
                    ui.label("決済内訳").classes("text-xs font-bold text-grey-7 q-mb-xs")
                    with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
                        for label, field in (
                            ("現金", "cash_sales"),
                            ("カード", "credit_sales"),
                            ("PayPay", "paypay_sales"),
                            ("電子マネー", "electronic_money_sales"),
                            ("旅行社", "travel_agency_sales"),
                            ("ポイント", None),
                        ):
                            value = (
                                int(record.get("tabelog_points_sales", 0))
                                + int(record.get("hotpepper_points_sales", 0))
                                if field is None else int(record.get(field, 0))
                            )
                            if value:
                                with ui.row().classes(
                                    "w-full items-center justify-between rounded-lg bg-grey-2 q-px-sm q-py-xs"
                                ):
                                    ui.label(label).classes("text-[10px] text-grey-7")
                                    ui.label(f"¥{value:,}").classes("text-xs font-bold")

        history()
