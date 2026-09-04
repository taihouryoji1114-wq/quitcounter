import json
from calendar import monthrange
from datetime import datetime

from nicegui import ui

from core.auth import current_role, log_out, require_app_access, require_permission
from core.clock import today_jst
from core.financials import financials
from core.purchases import purchases
from core.staffing import staffing
from core.theme import Theme


def _valid_month(value):
    try:
        parsed = datetime.strptime(str(value), "%Y-%m")
    except (TypeError, ValueError):
        return None
    return parsed.strftime("%Y-%m") if str(value) == parsed.strftime("%Y-%m") else None


def _shift_month(month, amount):
    parsed = datetime.strptime(month, "%Y-%m")
    total = parsed.year * 12 + parsed.month - 1 + amount
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _render_future_financials_home(selected_month=None):
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("未来決算", app_name="mirai-kessan")
    def header_actions():
        with ui.dialog() as menu_dialog, ui.card().classes("future-menu q-pa-lg"):
            with ui.row().classes("w-full items-center justify-between q-mb-md"):
                ui.label("未来決算メニュー").classes("text-xl font-black")
                ui.button(icon="close", on_click=menu_dialog.close).props("flat round")
            for title, icon, path in (
                ("経営コンサル", "psychology", "/mirai-kessan/consulting"),
                ("人件費管理", "groups", "/mirai-kessan/staffing"),
                ("立替管理", "account_balance_wallet", "/mirai-kessan/advances"),
                ("売上入力", "point_of_sale", "/mirai-kessan/sales"),
                ("仕入れノート", "inventory_2", "/mirai-kessan/shiire"),
                ("利益シミュレーション", "grid_view", "/mirai-kessan/block-map"),
                ("決算分析", "assessment", "/mirai-kessan/financial-analysis"),
            ):
                ui.button(
                    title, icon=icon, on_click=lambda _, target=path: ui.navigate.to(target)
                ).props("flat no-caps align=left").classes("future-menu-item w-full")
        with ui.row().classes("gap-0"):
            if current_role() == "owner":
                ui.button(icon="apps", on_click=lambda: ui.navigate.to("/")).props(
                    "flat round aria-label='R-BASEへ戻る'").classes("text-grey-8")
            ui.button(icon="menu", on_click=menu_dialog.open).props(
                "flat round aria-label='メニューを開く'"
            ).classes("text-grey-8")
            ui.button(icon="logout", on_click=lambda: log_out("/mirai-kessan/login")).props(
                "flat round aria-label='ログアウト'").classes("text-grey-8")

    content = Theme.shell(
        "経営ダッシュボード",
        "毎日の入力から、今月の経営状況を見える化",
        action=header_actions,
        brand="未来決算",
    )
    actual_current_month = today_jst().strftime("%Y-%m")
    current_month = _valid_month(selected_month) or actual_current_month
    dashboard_path = (
        "/mirai-kessan/dashboard" if current_month == actual_current_month
        else f"/mirai-kessan/month/{current_month}"
    )
    purchase_total = purchases.monthly_total(current_month, kind="cost")
    operating_supply_total = purchases.monthly_total(current_month, kind="operating_supply")
    other_expense_total = purchases.monthly_total(current_month, kind="expense")
    sales_total = financials.monthly_sales_total(current_month)
    payment_fees = financials.monthly_payment_summary(current_month)["total_fees"]
    advertising_summary = financials.get_monthly_advertising(current_month)
    advertising_total = advertising_summary["total"]
    today = today_jst()
    selected_year, selected_month_number = (int(part) for part in current_month.split("-"))
    days_in_month = monthrange(selected_year, selected_month_number)[1]
    if (selected_year, selected_month_number) < (today.year, today.month):
        elapsed_days = days_in_month
    elif (selected_year, selected_month_number) > (today.year, today.month):
        elapsed_days = 0
    else:
        elapsed_days = min(today.day, days_in_month)
    elapsed_ratio = elapsed_days / days_in_month
    purchase_tax = purchases.monthly_tax_summary(current_month)
    output_tax = sales_total * 10 // 110
    consumption_tax_estimate = max(
        0,
        output_tax - purchase_tax["input_tax"] - advertising_summary["input_tax"],
    )
    operations = financials.get_monthly_operations(current_month)
    staff_personnel_total = staffing.month_cost_summary(current_month, today)["company_cost"]
    if staff_personnel_total:
        operations["personnel"] = staff_personnel_total
    gross_profit = sales_total - purchase_total
    current_rent = round(operations["rent"] * elapsed_ratio)
    current_utilities = round(operations["utilities"] * elapsed_ratio)
    current_advertising = round(advertising_total * elapsed_ratio)
    operating_costs = (
        operations["personnel"] + current_rent + current_utilities
        + operations["other_admin"] + operating_supply_total + other_expense_total + payment_fees
        + current_advertising
    )
    operating_profit = gross_profit - operating_costs
    cash_after_tax_and_loan = (
        operating_profit - consumption_tax_estimate - operations["loan_payment"]
    )
    cost_rate = purchase_total / sales_total if sales_total else 0
    personnel_rate = operations["personnel"] / sales_total if sales_total else None
    labor_rate = operations["personnel"] / gross_profit if gross_profit > 0 else None
    monthly_entry_items = (
        ("人件費", operations["personnel"]),
        ("家賃", operations["rent"]),
        ("水道光熱費", operations["utilities"]),
        ("広告費", advertising_total),
        ("その他管理費", operations["other_admin"]),
        ("借入元金返済", operations["loan_payment"]),
    )
    missing_monthly_items = [title for title, value in monthly_entry_items if not value]
    completed_monthly_items = len(monthly_entry_items) - len(missing_monthly_items)
    month_label = current_month.replace("-", "年") + "月"
    with content:
        ui.button(
            "入力を自動チェック", icon="fact_check",
            on_click=lambda: ui.navigate.to("/mirai-kessan/audit"),
        ).props("unelevated no-caps").classes("audit-shortcut w-full q-mb-sm")
        ui.button(
            "期間集計・印刷を開く", icon="print",
            on_click=lambda: ui.navigate.to("/mirai-kessan/reports"),
        ).props("unelevated no-caps").classes("report-shortcut w-full q-mb-sm")
        with ui.card().classes("surface-card w-full q-pa-sm q-mb-sm"):
            with ui.row().classes("w-full items-center justify-between no-wrap"):
                ui.button(
                    icon="chevron_left",
                    on_click=lambda: ui.navigate.to(
                        f"/mirai-kessan/month/{_shift_month(current_month, -1)}"
                    ),
                ).props("flat round aria-label='前の月'")
                with ui.column().classes("items-center gap-0"):
                    ui.label(month_label).classes("text-base font-black")
                    if current_month != actual_current_month:
                        ui.button(
                            "今月へ戻る", on_click=lambda: ui.navigate.to("/mirai-kessan/dashboard")
                        ).props("flat dense no-caps").classes("text-[10px]")
                ui.button(
                    icon="chevron_right",
                    on_click=lambda: ui.navigate.to(
                        f"/mirai-kessan/month/{_shift_month(current_month, 1)}"
                    ),
                ).props("flat round aria-label='次の月'")

        detail_visible = [False]
        with ui.card().classes("w-full q-pa-lg q-mb-sm text-white cursor-pointer").style(
            "border-radius:28px;border:0;background:linear-gradient(145deg,#123D30 0%,#24664F 58%,#C18A45 145%);"
            "box-shadow:0 18px 42px rgba(18,61,48,.24)"
        ).on("click", lambda: (
            detail_visible.__setitem__(0, not detail_visible[0]),
            operation_details.set_visibility(detail_visible[0]),
        )):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-0"):
                    ui.label(month_label).classes("text-xs opacity-70")
                    ui.label("今月の経営スナップショット").classes("text-lg font-bold")
                ui.icon("insights").classes("text-3xl opacity-80")
            ui.label("売上実績").classes("text-xs opacity-70 q-mt-lg")
            ui.label(f"¥{sales_total:,}").classes("text-4xl font-black metric-value")
            with ui.element("div").classes("grid grid-cols-2 gap-2 w-full q-mt-lg"):
                with ui.element("div").classes("rounded-xl q-pa-sm").style(
                    "background:rgba(255,255,255,.12)"
                ):
                    ui.label("原価").classes("text-[10px] opacity-70")
                    ui.label(f"¥{purchase_total:,}").classes("font-bold")
                with ui.element("div").classes("rounded-xl q-pa-sm").style(
                    "background:rgba(255,255,255,.12)"
                ):
                    ui.label("粗利").classes("text-[10px] opacity-70")
                    ui.label(f"¥{gross_profit:,}").classes("font-bold")
            with ui.element("div").classes("snapshot-ratio-grid w-full q-mt-sm"):
                for title, value in (
                    ("原価率", f"{cost_rate * 100:.1f}%" if sales_total else "—"),
                    ("人件費率", f"{personnel_rate * 100:.1f}%" if personnel_rate is not None else "—"),
                    ("労働分配率", f"{labor_rate * 100:.1f}%" if labor_rate is not None else "—"),
                ):
                    with ui.element("div").classes("snapshot-ratio-card"):
                        ui.label(title).classes("snapshot-ratio-label")
                        ui.label(value).classes("snapshot-ratio-value")
            with ui.row().classes("items-center gap-1 q-mt-sm opacity-70"):
                ui.label("タップして費用・税金・返済を確認").classes("text-[9px]")
                ui.icon("expand_more").classes("text-sm")

        operation_details = ui.column().classes("w-full gap-0 q-mb-md")
        operation_details.set_visibility(False)
        with operation_details:
            with ui.card().classes("surface-card w-full q-pa-lg"):
                ui.label("月次費用を入力").classes("text-lg font-bold q-mb-xs")
                ui.label("請求や金額が分かった項目から入力してください。").classes(
                    "text-xs text-grey-6 q-mb-md"
                )
                with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
                    personnel_input = ui.number(
                        "人件費", value=operations["personnel"] or None, min=0, step=1
                    ).props("outlined prefix=¥ inputmode=numeric")
                    rent_input = ui.number(
                        "家賃", value=operations["rent"] or None, min=0, step=1
                    ).props("outlined prefix=¥ inputmode=numeric")
                    utilities_input = ui.number(
                        "水道光熱費", value=operations["utilities"] or None, min=0, step=1
                    ).props("outlined prefix=¥ inputmode=numeric")
                    other_admin_input = ui.number(
                        "その他管理費", value=operations["other_admin"] or None, min=0, step=1
                    ).props("outlined prefix=¥ inputmode=numeric")
                ui.label("広告費（請求書の税込合計）").classes(
                    "text-sm font-bold q-mt-md q-mb-sm"
                )
                with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
                    tabelog_ad_input = ui.number(
                        "食べログ", value=advertising_summary["tabelog"] or None, min=0, step=1
                    ).props("outlined prefix=¥ inputmode=numeric")
                    hotpepper_ad_input = ui.number(
                        "ホットペッパー", value=advertising_summary["hotpepper"] or None, min=0, step=1
                    ).props("outlined prefix=¥ inputmode=numeric")
                    other_ad_input = ui.number(
                        "その他の広告費", value=advertising_summary["other"] or None, min=0, step=1
                    ).props("outlined prefix=¥ inputmode=numeric")

                ui.separator().classes("q-my-md")
                ui.label("資金繰り").classes("text-sm font-bold")
                ui.label(
                    "元金返済は経費ではないため、営業利益には含めず手元資金からだけ差し引きます。"
                ).classes("text-[9px] text-grey-6 q-mb-sm")
                loan_input = ui.number(
                    "借入元金返済", value=operations["loan_payment"] or None, min=0, step=1
                ).props("outlined prefix=¥ inputmode=numeric").classes("w-full")

                def save_operations():
                    try:
                        financials.save_monthly_operations(
                            current_month,
                            personnel_input.value,
                            rent_input.value,
                            utilities_input.value,
                            other_admin_input.value,
                            loan_input.value,
                        )
                        financials.save_monthly_advertising(
                            current_month,
                            tabelog_ad_input.value,
                            hotpepper_ad_input.value,
                            other_ad_input.value,
                        )
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    ui.notify("月次入力を保存しました", type="positive")
                    ui.navigate.to(dashboard_path)

                ui.button("月次入力を保存", icon="save", on_click=save_operations).classes(
                    "w-full q-mt-md"
                )
            with ui.element("div").classes("grid grid-cols-2 gap-2 w-full q-mt-sm"):
                for title, value, color in (
                    ("人件費", operations["personnel"], "#EAF3FF"),
                    ("家賃", operations["rent"], "#F1EDFF"),
                    ("水道光熱費", operations["utilities"], "#E9F8F5"),
                    ("広告費", advertising_total, "#FFF0F2"),
                    ("営業用消耗品", operating_supply_total, "#EAF5FF"),
                    ("一般経費・管理費", other_expense_total + operations["other_admin"], "#F4F4F2"),
                    ("決済手数料", payment_fees, "#EDF5FF"),
                    ("消費税納付見込", consumption_tax_estimate, "#FFF4E5"),
                    ("借入元金返済", operations["loan_payment"], "#FCEEEE"),
                ):
                    with ui.element("div").classes("rounded-xl q-pa-sm").style(
                        f"background:{color}"
                    ):
                        ui.label(title).classes("text-[9px] text-grey-7")
                        ui.label(f"¥{value:,}").classes("text-sm font-bold")

        # The dashboard intentionally stops at the monthly snapshot. Detailed
        # tools live in the menu; the only second element is the current block.
        with ui.card().classes("surface-card w-full q-pa-md q-mb-md"):
            with ui.row().classes("w-full items-center justify-between no-wrap q-mb-sm"):
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label("今月の暫定利益ブロック").classes("text-base font-black")
                    ui.label("入力済みの数字だけで表示").classes("text-[9px] text-grey-6")
                ui.button(
                    icon="open_in_new", on_click=lambda: ui.navigate.to("/mirai-kessan/block-map")
                ).props("flat round aria-label='利益シミュレーションを開く'")
            if sales_total:
                gross_for_ratio = max(gross_profit, 1)
                cost_share = max(purchase_total / sales_total, .015)
                gross_share = max(gross_profit / sales_total, .015)
                breakdown = (
                    ("人件費", operations["personnel"], "#4A9FD0", operations["personnel"] / gross_for_ratio),
                    ("家賃", current_rent, "#8172B5", current_rent / gross_for_ratio),
                    ("水道光熱費", current_utilities, "#4CB7B4", current_utilities / gross_for_ratio),
                    ("広告費", current_advertising, "#D8943C", current_advertising / gross_for_ratio),
                    ("その他管理費", operations["other_admin"] + operating_supply_total + other_expense_total + payment_fees, "#99A29D", (operations["other_admin"] + operating_supply_total + other_expense_total + payment_fees) / gross_for_ratio),
                    ("営業利益" if operating_profit >= 0 else "営業損失", abs(operating_profit), "#4B77B7" if operating_profit >= 0 else "#C85C57", abs(operating_profit) / gross_for_ratio),
                )

                def dashboard_block(title, value, color, flex, note=""):
                    with ui.element("div").classes("actual-money-box").style(
                        f"background:{color};flex:{max(flex, .015)}"
                    ):
                        ui.label(title).classes("actual-block-title")
                        if flex >= .07:
                            ui.label(f"¥{value:,}").classes("actual-block-value")
                        if note and flex >= .11:
                            ui.label(note).classes("actual-block-note")

                with ui.element("div").classes("actual-box-map").style(
                    f"grid-template-rows:{cost_share}fr {gross_share}fr"
                ):
                    dashboard_block("売上", sales_total, "#355F4C", 1, "100%")
                    with ui.element("div").classes("actual-cost-block"):
                        dashboard_block("仕入れ・原価", purchase_total, "#82988D", 1, f"原価率 {cost_rate*100:.1f}%")
                    with ui.element("div").classes("actual-gross-block"):
                        dashboard_block("粗利", gross_profit, "#4F8C70", 1, f"粗利率 {gross_profit/sales_total*100:.1f}%")
                    with ui.element("div").classes("actual-breakdown"):
                        for title, value, color, flex in breakdown:
                            note = f"分配率 {labor_rate*100:.1f}%" if title == "人件費" and labor_rate is not None else ""
                            if title in ("営業利益", "営業損失"):
                                note = f"利益率 {operating_profit/sales_total*100:.1f}%"
                            dashboard_block(title, value, color, flex, note)
            else:
                ui.label("売上を入力すると表示されます").classes(
                    "text-xs text-grey-6 text-center q-pa-md"
                )
        ui.add_css("""
        .audit-shortcut{background:linear-gradient(135deg,#1E5A45,#33785F)!important;color:#fff!important;min-height:48px!important;border-radius:16px!important;font-weight:900!important}
        .future-menu{width:min(92vw,420px)!important;border-radius:26px!important}.future-menu-item{min-height:52px!important;justify-content:flex-start!important;font-size:14px!important}
        .metric-value,.rounded-xl .font-bold{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .actual-box-map{width:calc(100% + 12px)!important;margin-left:-6px;margin-right:-6px;height:330px;display:grid;grid-template-columns:1fr 1fr 1fr;overflow:hidden;background:#E8ECE9}.actual-money-box{min-height:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:#fff;overflow:hidden;padding:3px;box-sizing:border-box}.actual-box-map>.actual-money-box{grid-column:1;grid-row:1/3}.actual-cost-block{grid-column:2/4;grid-row:1;min-height:0;display:flex}.actual-cost-block>.actual-money-box,.actual-gross-block>.actual-money-box{width:100%}.actual-gross-block{grid-column:2;grid-row:2;min-height:0;display:flex}.actual-breakdown{grid-column:3;grid-row:2;min-height:0;display:flex;flex-direction:column;overflow:hidden}.actual-block-title{font-size:9px;font-weight:800;line-height:1.1}.actual-block-value{font-size:10px;font-weight:800;line-height:1.15;margin-top:2px;white-space:nowrap}.actual-block-note{font-size:7px;line-height:1.1;margin-top:2px;opacity:.9;white-space:nowrap}
        .snapshot-ratio-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.snapshot-ratio-card{min-width:0;padding:8px 5px;border-radius:12px;background:rgba(255,255,255,.14);text-align:center}.snapshot-ratio-label{font-size:8px;opacity:.72;white-space:nowrap}.snapshot-ratio-value{font-size:15px;font-weight:900;white-space:nowrap;margin-top:2px}
        """)
        ui.add_css("""
        .surface-card,.surface-card *,.rounded-xl,.rounded-xl *{min-width:0;box-sizing:border-box}.metric-value{max-width:100%;font-size:clamp(20px,9vw,36px)!important;letter-spacing:-.045em;font-variant-numeric:tabular-nums;overflow:hidden;text-overflow:clip}.actual-block-value{max-width:100%;font-size:clamp(7px,2.5vw,10px);letter-spacing:-.04em;text-overflow:clip}.snapshot-ratio-value{max-width:100%;font-size:clamp(11px,4vw,15px);overflow:hidden;text-overflow:clip}
        @media(max-width:520px){.surface-card{padding-left:14px!important;padding-right:14px!important}.actual-money-box{padding:2px 1px}.actual-block-title{max-width:100%;font-size:8px;overflow-wrap:anywhere}.actual-block-note{max-width:100%;white-space:normal;line-height:1.05}}
        """)
        return

        with ui.card().classes("surface-card w-full q-pa-md q-mb-md"):
            with ui.row().classes("w-full items-center justify-between no-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label("月次入力の完成度").classes("text-sm font-bold")
                    ui.label("損益5項目＋資金繰り1項目").classes("text-[9px] text-grey-6")
                ui.label(f"{completed_monthly_items}/{len(monthly_entry_items)} 項目").classes(
                    "text-lg font-black text-primary"
                )
            if missing_monthly_items:
                ui.label("未入力：" + "・".join(missing_monthly_items)).classes(
                    "text-[10px] q-mt-sm"
                ).style("color:#A66A17")
                ui.label("未入力項目は0円として暫定利益・資金増減を計算しています").classes(
                    "text-[9px] text-grey-6 q-mt-xs"
                )
            else:
                ui.label("主要な月次費用はすべて入力済みです").classes(
                    "text-[10px] text-positive q-mt-sm"
                )

        with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
            ui.label("暫定実績の利益構造").classes("text-lg font-bold")
            ui.label("入力済みの実績を、シミュレーションと同じ利益ブロックで表示").classes(
                "text-[10px] text-grey-6 q-mb-md"
            )
            if sales_total:
                gross_for_ratio = max(gross_profit, 1)
                cost_share = max(purchase_total / sales_total, 0.015)
                gross_share = max(gross_profit / sales_total, 0.015)
                breakdown = (
                    ("人件費", operations["personnel"], "#4A9FD0", operations["personnel"] / gross_for_ratio),
                    ("家賃", operations["rent"], "#8172B5", operations["rent"] / gross_for_ratio),
                    ("水道光熱費", operations["utilities"], "#4CB7B4", operations["utilities"] / gross_for_ratio),
                    ("広告費", advertising_total, "#D8943C", advertising_total / gross_for_ratio),
                    (
                        "その他管理費",
                        operations["other_admin"] + operating_supply_total + other_expense_total + payment_fees,
                        "#99A29D",
                        (operations["other_admin"] + operating_supply_total + other_expense_total + payment_fees) / gross_for_ratio,
                    ),
                    (
                        "営業利益" if operating_profit >= 0 else "営業損失",
                        abs(operating_profit),
                        "#4B77B7" if operating_profit >= 0 else "#C85C57",
                        abs(operating_profit) / gross_for_ratio,
                    ),
                )

                def actual_block(title, value, color, flex, note=""):
                    with ui.element("div").classes("actual-money-box").style(
                        f"background:{color};flex:{max(flex, 0.015)}"
                    ):
                        ui.label(title).classes("actual-block-title")
                        if flex >= 0.07:
                            ui.label(f"¥{value:,}").classes("actual-block-value")
                        if note and flex >= 0.11:
                            ui.label(note).classes("actual-block-note")

                with ui.element("div").classes("actual-box-map q-mb-md").style(
                    f"grid-template-rows:{cost_share}fr {gross_share}fr"
                ):
                    actual_block("売上", sales_total, "#355F4C", 1, "100%")
                    with ui.element("div").classes("actual-cost-block"):
                        actual_block(
                            "仕入れ・原価", purchase_total, "#82988D", 1,
                            f"原価率 {cost_rate * 100:.1f}%",
                        )
                    with ui.element("div").classes("actual-gross-block"):
                        actual_block(
                            "粗利", gross_profit, "#4F8C70", 1,
                            f"粗利率 {gross_profit / sales_total * 100:.1f}%",
                        )
                    with ui.element("div").classes("actual-breakdown"):
                        for title, value, color, flex in breakdown:
                            note = ""
                            if title == "人件費" and labor_rate is not None:
                                note = f"分配率 {labor_rate * 100:.1f}%"
                            elif title in ("営業利益", "営業損失"):
                                note = f"利益率 {operating_profit / sales_total * 100:.1f}%"
                            actual_block(title, value, color, flex, note)

                legend_components = (
                    ("原価（売上比）", purchase_total, "#82988D", cost_rate),
                    ("人件費（粗利比）", operations["personnel"], "#4A9FD0", labor_rate),
                    ("家賃（売上比）", operations["rent"], "#8172B5", operations["rent"] / sales_total),
                    ("水道光熱費（売上比）", operations["utilities"], "#4CB7B4", operations["utilities"] / sales_total),
                    ("広告費（売上比）", advertising_total, "#D8943C", advertising_total / sales_total),
                    ("その他費用（売上比）", operations["other_admin"] + operating_supply_total + other_expense_total + payment_fees, "#99A29D", (operations["other_admin"] + operating_supply_total + other_expense_total + payment_fees) / sales_total),
                    (("営業利益" if operating_profit >= 0 else "営業損失") + "（売上比）", operating_profit, "#4B77B7" if operating_profit >= 0 else "#C85C57", operating_profit / sales_total),
                )
                ui.label("現在の実際の比率").classes("text-[10px] text-primary font-bold q-mb-xs")
                with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
                    for title, value, color, ratio in legend_components:
                        with ui.row().classes("w-full items-center justify-between no-wrap"):
                            with ui.row().classes("items-center gap-1 no-wrap"):
                                ui.element("div").style(
                                    f"width:9px;height:9px;border-radius:3px;background:{color}"
                                )
                                ui.label(f"{title} {ratio * 100:.1f}%" if ratio is not None else title).classes(
                                    "text-[9px] text-grey-7"
                                )
                            ui.label(f"¥{value:,}").classes("text-[9px] font-bold")
                ui.separator().classes("q-my-md")
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("税金・借入返済後の資金増減目安").classes("text-xs text-grey-7")
                    ui.label(f"¥{cash_after_tax_and_loan:,}").classes(
                        "text-lg font-black text-negative" if cash_after_tax_and_loan < 0
                        else "text-lg font-black text-primary"
                    )
            else:
                ui.label("売上を入力すると図が表示されます").classes(
                    "text-sm text-grey-6 q-pa-md text-center"
                )

        ui.add_css("""
        .future-menu{width:min(92vw,420px)!important;border-radius:26px!important}.future-menu-item{min-height:52px!important;justify-content:flex-start!important;font-size:14px!important}
        .actual-box-map{width:100%!important;align-self:stretch;height:420px;display:grid;grid-template-columns:1fr 1fr 1fr;overflow:hidden;background:#E8ECE9}
        .actual-money-box{min-height:14px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:#fff;overflow:hidden;padding:3px;box-sizing:border-box}
        .actual-box-map>.actual-money-box{grid-column:1;grid-row:1/3}
        .actual-cost-block{grid-column:2/4;grid-row:1;min-height:0;display:flex}
        .actual-cost-block>.actual-money-box,.actual-gross-block>.actual-money-box{width:100%}
        .actual-gross-block{grid-column:2;grid-row:2;min-height:0;display:flex}
        .actual-breakdown{grid-column:3;grid-row:2;min-height:0;display:flex;flex-direction:column;overflow:hidden}
        .actual-block-title{font-size:10px;font-weight:800;line-height:1.15}
        .actual-block-value{font-size:12px;font-weight:800;line-height:1.2;margin-top:2px;white-space:nowrap}
        .actual-block-note{font-size:8px;line-height:1.15;margin-top:2px;opacity:.9;white-space:nowrap}
        @media(max-width:520px){.actual-box-map{width:calc(100% + 12px)!important;margin-left:-6px;margin-right:-6px;height:390px}.actual-block-title{font-size:9px}.actual-block-value{font-size:10px}.actual-block-note{font-size:7px}}
        """)
        ui.add_css("""
        .surface-card,.surface-card *{min-width:0;box-sizing:border-box}.actual-block-value{max-width:100%;font-size:clamp(7px,2.7vw,12px);letter-spacing:-.04em;overflow:hidden;text-overflow:clip}.actual-block-title,.actual-block-note{max-width:100%;overflow:hidden}
        @media(max-width:520px){.surface-card{padding-left:14px!important;padding-right:14px!important}.actual-box-map{width:calc(100% + 8px)!important;margin-left:-4px;margin-right:-4px}.actual-money-box{padding:2px 1px}.actual-block-title{font-size:8px;overflow-wrap:anywhere}.actual-block-value{font-size:clamp(7px,2.4vw,9px)}.actual-block-note{font-size:6px;white-space:normal;line-height:1.05}}
        """)

        with ui.card().classes("surface-card w-full q-pa-lg q-mb-lg"):
            ui.label("重要な経営指標").classes("text-lg font-bold q-mb-md")
            with ui.element("div").classes("grid grid-cols-2 gap-3 w-full"):
                with ui.element("div").classes("rounded-2xl q-pa-md").style(
                    "background:#FFF4E5"
                ):
                    ui.label("原価率").classes("text-xs font-bold").style("color:#9A5B18")
                    ui.label(
                        f"{cost_rate * 100:.1f}%" if sales_total else "—"
                    ).classes("text-2xl font-black q-mt-xs").style("color:#8A4D10")
                with ui.element("div").classes("rounded-2xl q-pa-md").style(
                    "background:#EAF3FF"
                ):
                    ui.label("労働分配率").classes("text-xs font-bold").style("color:#315F91")
                    ui.label(
                        f"{labor_rate * 100:.1f}%" if labor_rate is not None else "未入力"
                    ).classes("text-2xl font-black q-mt-xs").style("color:#244F7F")
                    if labor_rate is None:
                        ui.label("人件費の登録後に計算").classes("text-[9px] q-mt-xs").style("color:#6685A5")

        ui.label("クイックメニュー").classes("text-lg font-bold q-mb-sm")

        def menu_card(title, description, icon, color, path):
            with ui.card().classes(
                "habit-card w-full q-pa-md q-mb-sm cursor-pointer"
            ).on("click", lambda _, target=path: ui.navigate.to(target)):
                with ui.row().classes("w-full items-center no-wrap"):
                    with ui.element("div").classes(
                        "quick-menu-icon q-mr-md"
                    ).style(
                        f"--icon-color:{color};"
                        f"background:linear-gradient(145deg,{color},color-mix(in srgb,{color} 72%,#10271E))"
                    ):
                        ui.icon(icon).classes("quick-menu-glyph")
                    with ui.column().classes("gap-0"):
                        ui.label(title).classes("text-lg font-bold")
                        ui.label(description).classes("text-xs text-grey-7 q-mt-xs")
                    ui.space()
                    ui.icon("chevron_right").classes("text-2xl text-grey-7")

        menu_card("売上入力", "その日の売上を記録", "point_of_sale", "#C07B32", "/mirai-kessan/sales")
        menu_card("立替管理", "3人の立替額・返金・残額", "account_balance_wallet", "#398061", "/mirai-kessan/advances")
        menu_card(
            "仕入れノート", "原価・経費・消費税を記録",
            "inventory_2", "#3678C8", "/mirai-kessan/shiire",
        )
        menu_card("利益シミュレーション", "計画と暫定実績を図で比較", "grid_view", "#398061", "/mirai-kessan/block-map")
        menu_card("決算分析", "決算書を入力して会社の状態を診断", "assessment", "#75599B", "/mirai-kessan/financial-analysis")

        ui.add_css("""
        .quick-menu-icon{width:52px;height:52px;min-width:52px;max-width:52px;border-radius:15px;display:flex;align-items:center;justify-content:center;overflow:hidden;color:#fff;box-shadow:0 7px 15px color-mix(in srgb,var(--icon-color) 28%,transparent);border:1px solid rgba(255,255,255,.28)}
        .quick-menu-glyph{font-size:25px!important;line-height:1!important;width:28px;height:28px;display:flex!important;align-items:center;justify-content:center;overflow:hidden;text-shadow:0 1px 3px rgba(0,0,0,.14)}
        """)


@ui.page("/mirai-kessan/input")
def future_financials_input_hub():
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_input", "/mirai-kessan/login"):
        return
    Theme.page("未来決算｜日常入力", app_name="mirai-kessan")

    def actions():
        with ui.row().classes("gap-0"):
            if current_role() == "owner":
                ui.button(icon="apps", on_click=lambda: ui.navigate.to("/")).props("flat round")
            ui.button(icon="logout", on_click=lambda: log_out("/mirai-kessan/login")).props("flat round")

    content = Theme.shell("未来決算 日常入力", "許可された入力だけを、迷わず記録",
                          action=actions, brand="未来決算")
    with content:
        for title, subtitle, icon, path in (
            ("売上入力", "ランチ・ディナーと決済別売上", "point_of_sale", "/mirai-kessan/sales"),
            ("仕入れ入力", "原価・備品・その他経費", "inventory_2", "/mirai-kessan/shiire"),
            ("勤務・出勤入力", "出勤状況と勤務時間", "groups", "/mirai-kessan/attendance"),
        ):
            with ui.card().classes("habit-card w-full q-pa-lg q-mb-sm cursor-pointer").on(
                "click", lambda _, target=path: ui.navigate.to(target)):
                with ui.row().classes("w-full items-center no-wrap"):
                    ui.icon(icon).classes("text-3xl text-primary q-mr-md")
                    with ui.column().classes("gap-0 grow"):
                        ui.label(title).classes("text-lg font-black")
                        ui.label(subtitle).classes("text-xs text-grey-6")
                    ui.icon("chevron_right").classes("text-grey-6")


@ui.page("/mirai-kessan/dashboard")
def future_financials_home():
    _render_future_financials_home()


@ui.page("/mirai-kessan")
def future_financials_opening():
    if not require_app_access("future_financials"):
        return
    if current_role() not in {"owner", "executive"}:
        ui.navigate.to("/mirai-kessan/input")
        return
    _render_future_financials_home()


@ui.page("/mirai-kessan/month/{selected_month}")
def future_financials_month(selected_month: str):
    _render_future_financials_home(selected_month)


@ui.page("/mirai-kessan/block-map")
def future_financials():
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("未来決算", app_name="mirai-kessan")
    content = Theme.shell(
        "利益シミュレーション",
        "計画と暫定実績を切り替えて、お金の残り方を確認",
        back_to="/mirai-kessan/dashboard",
    )
    current_month = today_jst().strftime("%Y-%m")
    purchase_tax = purchases.monthly_tax_summary(current_month)
    payment_summary = financials.monthly_payment_summary(current_month)
    advertising_summary = financials.get_monthly_advertising(current_month)
    actuals = {
        "sales": financials.monthly_sales_total(current_month),
        "cogs": purchases.monthly_total(current_month, kind="cost"),
        "other": purchases.monthly_total(current_month, kind="expense") + purchases.monthly_total(current_month, kind="operating_supply"),
        "payment_fees": payment_summary["total_fees"],
        "advertising": advertising_summary["total"],
        "input_tax": purchase_tax["input_tax"] + advertising_summary["input_tax"],
        "estimated_tax_records": purchase_tax["estimated_records"],
        "excluded_unregistered_records": purchase_tax[
            "excluded_unregistered_records"
        ],
    }
    with content:
        async def save_plan_to_server():
            plan = await ui.run_javascript(
                """(() => {
                    const root = document.getElementById('mirai-app');
                    return root && root._collectPlan ? root._collectPlan() : null;
                })()""",
                timeout=5.0,
            )
            try:
                financials.save_plan(plan)
            except ValueError as error:
                ui.notify(str(error), type="negative")
                return
            ui.notify("月間計画を保存しました", type="positive")

        ui.button(on_click=save_plan_to_server).props(
            "id=save-plan-server aria-label='月間計画をサーバーへ保存'"
        ).classes("hidden")
        ui.add_body_html(
            "<script>"
            f"window.miraiActuals={json.dumps(actuals)};"
            f"window.miraiSavedPlan={json.dumps(financials.get_plan())};"
            "</script>"
        )
        ui.html(
            r'''
<div id="mirai-app">
  <details class="mk-card compact-section input-card">
    <summary class="compact-summary">月間計画を入力・編集</summary>
    <div class="mk-head"><div><small>SIMULATION</small><h2>月間の利益を試算</h2></div><button id="save-plan">計画を保存</button></div>
    <div class="view-switch"><button id="view-simulation" class="active">計画シミュレーション</button></div>
    <div id="view-note" class="view-note simulation">入力した計画値で「こうなったら利益はいくら残るか」を試算しています。</div>
    <div id="plan-fields" class="input-grid">
      <label>売上高<input id="sales" inputmode="numeric" value="3000000"></label>
      <div class="dual-plan-field">
        <div class="dual-plan-head"><span>売上原価</span><select id="cogs-mode"><option value="amount" selected>金額を固定</option><option value="rate">原価率を固定</option></select></div>
        <div class="dual-plan-inputs"><label>金額<input id="cogs" inputmode="numeric" value="900000"></label><label>売上比率（%）<input id="cogs-rate" inputmode="decimal" value="30"></label></div>
      </div>
      <div class="dual-plan-field">
        <div class="dual-plan-head"><span>人件費</span><select id="personnel-mode"><option value="amount" selected>金額を固定</option><option value="rate">労働分配率を固定</option></select></div>
        <div class="dual-plan-inputs"><label>金額<input id="personnel" inputmode="numeric" value="750000"></label><label>粗利に対する割合（%）<input id="personnel-rate" inputmode="decimal" value="35"></label></div>
      </div>
      <label>家賃<input id="rent" inputmode="numeric" value="200000"></label>
      <label>水道光熱費<input id="utilities" inputmode="numeric" value="100000"></label>
      <label>広告費<input id="advertising" inputmode="numeric" value="50000"></label>
      <label>その他管理費<input id="other-expenses" inputmode="numeric" value="50000"></label>
      <label>営業外収益<input id="non-op-income" inputmode="numeric" value="0"></label>
      <label>営業外費用・支払利息<input id="non-op-expense" inputmode="numeric" value="50000"></label>
      <label>目標経常利益<input id="target-profit" inputmode="numeric" value="700000"></label>
    </div>
  </details>

  <section class="mk-card result-card">
    <div class="mk-head"><div><small>PROFIT STRUCTURE</small><h2>利益ブロック図</h2></div><span>月間</span></div>
    <p class="block-guide">売上を「原価と粗利」に分け、粗利が「人件費・経費・利益」にどう分かれるかを面積で表示します。</p>
    <div id="profit-summary" class="summary-grid"></div>
    <div id="profit-map" class="box-map" aria-label="売上から費用を差し引いて利益が残る流れを表した図"></div>
    <div id="legend-title" class="legend-title">試算結果の実際の比率（入力値から自動計算）</div>
    <div id="block-legend" class="block-legend"></div>
    <div id="sales-answer" class="answer"></div>
  </section>

  <details class="mk-card compact-section cash-card">
    <summary class="compact-summary">税金・資金繰りの詳細</summary>
    <div class="mk-head"><div><small>TAX & CASH</small><h2>税金・資金繰り</h2></div><span>自動概算</span></div>
    <div class="tax-settings">
      <label>消費税の計算方式<select id="tax-method"><option value="general">一般課税</option><option value="simplified">簡易課税（飲食店・みなし仕入率60%）</option></select></label>
      <label>法人税等の概算実効税率（%）<input id="corporate-tax-rate" inputmode="decimal" value="30"></label>
    </div>
    <div id="tax-note" class="tax-note"></div>
    <div class="tax-note">法人税等は、現在「プラスの経常利益 × 設定した概算実効税率」で試算しています。会社の所在地・資本金・所得区分・欠損金などを反映した確定申告額ではありません。</div>
    <div class="input-grid compact">
      <label>売上で預かった消費税<input id="output-tax" inputmode="numeric" value="0" readonly></label>
      <label>仕入れ等で支払った消費税<input id="input-tax" inputmode="numeric" value="0" readonly></label>
      <label>消費税の納付見込<input id="consumption-tax" inputmode="numeric" value="0" readonly></label>
      <label>仕入税額の超過分<input id="tax-credit-excess" inputmode="numeric" value="0" readonly></label>
      <label>法人税等の見込<input id="corporate-tax" inputmode="numeric" value="0" readonly></label>
      <label>借入金の元金返済<input id="loan-payment" inputmode="numeric" value="200000"></label>
      <label>設備投資・その他<input id="investment" inputmode="numeric" value="0"></label>
    </div>
    <div id="cash-flow" class="cash-flow"></div>
  </details>
</div>
<style>
#mirai-app{width:100%;display:grid;gap:16px}.mk-card{background:#fff;border:1px solid #E5E9E6;border-radius:24px;padding:22px;box-shadow:0 8px 24px rgba(39,55,45,.055)}.mk-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}.mk-head small{color:#4F7C68;font-weight:800;letter-spacing:.14em}.mk-head h2{font-size:19px;margin:3px 0 0}.mk-head span{color:#7A867F;font-size:11px}.mk-head button{border:0;border-radius:10px;background:#EDF5F0;color:#39745A;padding:9px 14px;font-weight:700}.block-guide{margin:-8px 0 14px;color:#748078;font-size:11px;line-height:1.6}.input-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.input-grid label{color:#68746D;font-size:10px;font-weight:700}.input-grid input{width:100%;box-sizing:border-box;margin-top:5px;border:1px solid #DDE3DF;border-radius:10px;padding:10px;font-size:14px;outline:none}.input-grid input:focus{border-color:#4F7C68;box-shadow:0 0 0 3px rgba(79,124,104,.1)}.dual-plan-field{border:1px solid #DDE3DF;border-radius:13px;padding:10px;background:#FAFBFA}.dual-plan-head{display:flex;align-items:center;justify-content:space-between;gap:8px;color:#68746D;font-size:11px;font-weight:800}.dual-plan-head select{border:1px solid #DDE3DF;border-radius:8px;background:#fff;padding:6px;color:#39745A;font-size:10px;font-weight:700}.dual-plan-inputs{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:7px}.dual-plan-inputs input:disabled{background:#EFF2F0;color:#68746D}.target-settings{grid-column:1/-1;border:1px solid #DDE3DF;border-radius:13px;padding:10px;background:#FAFBFA}.target-settings summary{cursor:pointer;color:#39745A;font-size:11px;font-weight:800}.target-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px}.summary{background:#F5F8F6;border-radius:12px;padding:12px}.summary small{display:block;color:#748078;font-size:9px}.summary b{display:block;margin-top:3px;font-size:15px}.summary.negative b{color:#C84B45}.answer{margin-top:18px;border-radius:15px;background:#EAF1FF;padding:16px;color:#244F89}.answer small{display:block;font-size:10px}.answer b{display:block;font-size:22px;margin-top:3px}.answer span{font-size:11px}.compact{margin-bottom:18px}.cash-flow{display:grid;gap:7px}.cash-line{display:grid;grid-template-columns:1fr auto;gap:10px;padding:10px 0;border-bottom:1px solid #EEF0EE;font-size:12px}.cash-line strong{font-size:14px}.cash-line.final{border:0;border-radius:12px;background:#F3F6F4;padding:14px}.cash-line.final strong.negative{color:#C84B45}@media(max-width:520px){.mk-card{padding:18px 15px}.input-grid{grid-template-columns:1fr}.summary-grid{grid-template-columns:1fr 1fr}.target-grid{grid-template-columns:1fr 1fr}}
.compact-section{padding:0!important}.compact-summary{cursor:pointer;list-style:none;padding:18px 20px;font-size:14px;font-weight:900;color:#315A45}.compact-summary::-webkit-details-marker{display:none}.compact-summary:after{content:'＋';float:right}.compact-section[open]>.compact-summary:after{content:'−'}.compact-section[open]>.mk-head,.compact-section[open]>.view-switch,.compact-section[open]>.view-note,.compact-section[open]>.input-grid,.compact-section[open]>.tax-settings,.compact-section[open]>.tax-note,.compact-section[open]>.compact,.compact-section[open]>.cash-flow{margin-left:18px;margin-right:18px}.compact-section[open]>.cash-flow,.compact-section[open]>.input-grid{margin-bottom:20px}
.view-switch{display:grid;grid-template-columns:1fr 1fr;gap:6px;background:#EEF2EF;padding:5px;border-radius:13px;margin-bottom:10px}.view-switch button{border:0;border-radius:9px;background:transparent;padding:9px 5px;color:#718078;font-size:10px;font-weight:800}.view-switch button.active{background:#fff;color:#39745A;box-shadow:0 2px 8px rgba(39,55,45,.08)}.view-note{border-radius:11px;padding:10px 12px;margin-bottom:14px;font-size:10px;line-height:1.55}.view-note.simulation{background:#EAF1FF;color:#315A91}.view-note.provisional{background:#FFF2DB;color:#855D20}.diagnosis{margin-bottom:12px}.diagnosis-main{border-radius:14px;padding:12px;background:#FFF0ED;color:#8E3F38;font-size:11px;font-weight:800}.diagnosis-main.good{background:#EAF5EE;color:#39745A}.house-map{background:#F3F6F4;border-radius:18px;padding:12px}.house-map svg{display:block;width:100%;height:auto;overflow:visible}.house-part{transition:all .3s ease}.house-legend{display:grid;gap:7px;margin-top:12px}.legend-row{display:grid;grid-template-columns:12px 1fr auto;gap:8px;align-items:center;border-bottom:1px solid #EEF0EE;padding:7px 2px;font-size:10px}.legend-color{width:12px;height:12px;border-radius:3px}.legend-row span{color:#66736C}.legend-row strong{text-align:right}.legend-row small{display:block;color:#89938E}.legend-row.warning strong,.legend-row.warning small{color:#C84B45}.legend-row.warning{background:#FFF7F5;border-radius:8px;padding:7px}.house-caption{text-align:center;color:#748078;font-size:9px;margin-top:6px}
.target-settings{display:none}.house-status{text-align:center;margin-top:7px;font-size:11px;font-weight:900}.house-status.strong{color:#39745A}.house-status.caution{color:#B77822}.house-status.danger{color:#C84B45}
.box-map{height:380px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;background:#E8ECE9;padding:5px;border-radius:16px;overflow:hidden}.box-column{min-width:0;height:100%;display:flex;flex-direction:column;gap:5px}.box-spacer{min-height:0}.money-box{min-height:18px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;border-radius:9px;padding:4px;box-sizing:border-box;overflow:hidden;color:#fff}.money-box span{font-size:10px;font-weight:800;line-height:1.2}.money-box b{font-size:12px;margin-top:2px;white-space:nowrap}.money-box em{font-size:8px;font-style:normal;margin-top:2px;opacity:.9;white-space:nowrap}.box-sales{height:100%;background:#355F4C}.box-cost{background:#82988D}.box-gross{background:#4F8C70}.box-personnel{background:#4A9FD0}.box-rent{background:#8172B5}.box-utilities{background:#4CB7B4}.box-advertising{background:#D8943C}.box-other{background:#99A29D}.box-profit{background:#4B77B7}.box-loss{background:#C85C57}.block-legend{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:12px}.block-legend div{display:flex;justify-content:space-between;gap:6px;padding:7px 9px;background:#F6F8F6;border-radius:8px;font-size:9px}.block-legend i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px}.block-legend strong{white-space:nowrap}@media(max-width:520px){.box-map{height:330px;gap:3px;padding:3px}.box-column{gap:3px}.money-box{padding:2px}.money-box span{font-size:8px}.money-box b{font-size:9px}.money-box em{display:none}}
.block-sales-total{grid-column:1;grid-row:1/3}.block-cost-wide{grid-column:2/4;grid-row:1}.block-gross-total{grid-column:2;grid-row:2}.block-breakdown{grid-column:3;grid-row:2;min-height:0;display:flex;flex-direction:column;gap:5px;overflow:hidden}@media(max-width:520px){.block-breakdown{gap:3px}}
.legend-title{margin-top:13px;color:#39745A;font-size:10px;font-weight:800}.block-legend{margin-top:6px}.map-empty{height:100%;display:flex;align-items:center;justify-content:center;text-align:center;padding:24px;color:#68746D;background:#F5F8F6;font-size:12px;font-weight:700}
.box-map{gap:0;padding:0}.money-box{border-radius:0}.block-breakdown{gap:0}.block-sales-total{border-radius:0}.block-cost-wide{border-radius:0}
.tax-settings{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}.tax-settings label{color:#68746D;font-size:10px;font-weight:700}.tax-settings select,.tax-settings input{width:100%;box-sizing:border-box;margin-top:5px;border:1px solid #DDE3DF;border-radius:10px;padding:10px;background:#fff;font-size:12px}.tax-note{margin-bottom:12px;padding:10px 12px;border-radius:11px;background:#FFF7E8;color:#75551E;font-size:9px;line-height:1.55}.input-grid input[readonly]{background:#F1F5F2;color:#315A45;font-weight:800}@media(max-width:520px){.tax-settings{grid-template-columns:1fr}}
</style>
            ''',
            sanitize=False,
        ).classes("w-full")
        ui.add_body_html(
            r'''
<script>
(() => {
  function init(){
    const root=document.getElementById('mirai-app');
    if(!root){setTimeout(init,100);return}
    const $=id=>document.getElementById(id), ids=['sales','cogs','cogs-rate','personnel','personnel-rate','rent','utilities','advertising','other-expenses','non-op-income','non-op-expense','target-profit','tax-method','corporate-tax-rate','loan-payment','investment'], modes=['cogs-mode','personnel-mode'];
    const moneyIds=['sales','cogs','personnel','rent','utilities','advertising','other-expenses','non-op-income','non-op-expense','target-profit','loan-payment','investment'];
    const num=id=>Math.max(0,Number(String($(id).value).replace(/,/g,''))||0), yen=n=>new Intl.NumberFormat('ja-JP',{style:'currency',currency:'JPY',maximumFractionDigits:0}).format(n||0);
    const comma=n=>new Intl.NumberFormat('ja-JP',{maximumFractionDigits:0}).format(Math.round(Number(n)||0));
    const formatMoney=id=>{const field=$(id);if(field&&document.activeElement!==field)field.value=comma(num(id))};
    function box(label,value,share,cls,note=''){const safe=Math.max(.015,Math.abs(share));return `<div class="money-box ${cls}" style="flex:${safe}"><span>${label}</span>${safe>=.07?`<b>${yen(value)}</b>`:''}${note&&safe>=.11?`<em>${note}</em>`:''}</div>`}
    function legend(label,value,rate,color){const rateText=rate===null?'—':`${(rate*100).toFixed(1)}%`;return `<div><span><i style="background:${color}"></i>${label}　${rateText}</span><strong>${yen(value)}</strong></div>`}
    function syncPlanField(name){
      const mode=$(`${name}-mode`).value,sales=num('sales'),basis=name==='personnel'?Math.max(0,sales-num('cogs')):sales,amount=$(name),rate=$(`${name}-rate`);
      if(mode==='rate'){amount.value=Math.round(basis*(Math.max(0,Number(rate.value)||0)/100));amount.disabled=true;rate.disabled=false}
      else{rate.value=basis?((num(name)/basis)*100).toFixed(1):0;amount.disabled=false;rate.disabled=true}
    }
    function syncPlan(){syncPlanField('cogs');syncPlanField('personnel')}
    function update(){
      const sales=num('sales'),cogs=num('cogs'),personnel=num('personnel'),rent=num('rent'),utilities=num('utilities'),advertising=num('advertising'),otherExpenses=num('other-expenses'),otherSga=rent+utilities+advertising+otherExpenses,sga=personnel+otherSga,noi=num('non-op-income'),noe=num('non-op-expense'),target=num('target-profit');
      const gross=sales-cogs,operating=gross-sga,ordinary=operating+noi-noe,rate=sales?cogs/sales:0;
      const fixedOther=otherSga+noe-noi+target,personnelRate=Math.max(0,Number($('personnel-rate').value)||0)/100;
      const requiredGross=$('personnel-mode').value==='rate'?(personnelRate<1?fixedOther/(1-personnelRate):0):personnel+fixedOther;
      const cogsRate=Math.max(0,Number($('cogs-rate').value)||0)/100;
      const required=$('cogs-mode').value==='rate'?(cogsRate<1?requiredGross/(1-cogsRate):0):requiredGross+cogs;
      $('profit-summary').innerHTML=[['粗利',gross],['営業利益',operating],['経常利益',ordinary]].map(x=>`<div class="summary ${x[1]<0?'negative':''}"><small>${x[0]}</small><b>${yen(x[1])}</b></div>`).join('');
      const base=sales||1,costShare=sales?cogs/base:null,grossShare=sales?gross/base:null,profitShare=sales?operating/base:null;
      const pct=n=>n===null?'—':`${(n*100).toFixed(1)}%`, laborShare=gross>0?personnel/gross:null;
      const personnelShare=sales?personnel/base:null,rentShare=sales?rent/base:null,utilitiesShare=sales?utilities/base:null,advertisingShare=sales?advertising/base:null,otherShare=sales?otherExpenses/base:null,grossBase=Math.max(gross,1),personnelOfGross=personnel/grossBase,rentOfGross=rent/grossBase,utilitiesOfGross=utilities/grossBase,advertisingOfGross=advertising/grossBase,otherOfGross=otherExpenses/grossBase,profitOfGross=Math.max(Math.abs(operating)/grossBase,.015);
      if(sales<=0){$('profit-map').style.gridTemplateRows='1fr';$('profit-map').innerHTML='<div class="map-empty" style="grid-column:1/-1">売上を入力すると、費用と利益の比率を表示します</div>'}
      else if(gross<0){$('profit-map').style.gridTemplateRows='1fr';$('profit-map').innerHTML='<div class="map-empty" style="grid-column:1/-1">原価が売上を上回っています。入力値を確認してください</div>'}
      else{$('profit-map').style.gridTemplateRows=`${Math.max(costShare,.015)}fr ${Math.max(grossShare,.015)}fr`;$('profit-map').innerHTML=`${box('売上',sales,1,'box-sales block-sales-total','100%')}${box('仕入れ・原価',cogs,costShare,'box-cost block-cost-wide',`原価率 ${pct(costShare)}`)}${box('粗利',gross,Math.max(grossShare,.015),'box-gross block-gross-total',`粗利率 ${pct(grossShare)}`)}<div class="block-breakdown">${box('人件費',personnel,personnelOfGross,'box-personnel',`分配率 ${pct(laborShare)}`)}${box('家賃',rent,rentOfGross,'box-rent')}${box('光熱費',utilities,utilitiesOfGross,'box-utilities')}${box('広告費',advertising,advertisingOfGross,'box-advertising')}${box('その他',otherExpenses,otherOfGross,'box-other')}${box(operating<0?'営業損失':'営業利益',Math.abs(operating),profitOfGross,operating<0?'box-loss':'box-profit',`利益率 ${pct(profitShare)}`)}</div>`}
      $('block-legend').innerHTML=legend('原価（売上比）',cogs,costShare,'#82988D')+legend('人件費（粗利比・労働分配率）',personnel,laborShare,'#4A9FD0')+legend('家賃（売上比）',rent,rentShare,'#8172B5')+legend('水道光熱費（売上比）',utilities,utilitiesShare,'#4CB7B4')+legend('広告費（売上比）',advertising,advertisingShare,'#D8943C')+legend('その他管理費（売上比）',otherExpenses,otherShare,'#99A29D')+legend(operating<0?'営業損失（売上比）':'営業利益（売上比）',operating,profitShare,operating<0?'#C85C57':'#4B77B7');
      const gap=Math.max(0,required-sales);$('sales-answer').innerHTML=`<small>目標経常利益 ${yen(target)} に必要な売上</small><b>${yen(required)}</b><span>${gap>0?`現在の計画より ${yen(gap)} 増やす必要があります`:'現在の売上計画で達成圏内です'}</span>`;
      const outputTax=Math.floor(sales*10/110),plannedInputTax=Math.floor(cogs*8/108)+Math.floor((rent+utilities+advertising+otherExpenses)*10/110),actualMode=root.dataset.view==='provisional',generalInputTax=actualMode?Number((window.miraiActuals||{}).input_tax||0):plannedInputTax,taxMethod=$('tax-method').value,ct=Math.max(0,taxMethod==='simplified'?Math.floor(outputTax*.4):outputTax-generalInputTax),corpRate=num('corporate-tax-rate'),corp=Math.max(0,Math.round(Math.max(ordinary,0)*corpRate/100));
      const creditExcess=taxMethod==='general'?Math.max(0,generalInputTax-outputTax):0;
      $('output-tax').value=comma(outputTax);$('input-tax').value=comma(generalInputTax);$('consumption-tax').value=comma(ct);$('tax-credit-excess').value=comma(creditExcess);$('corporate-tax').value=comma(corp);
      const estimatedCount=Number((window.miraiActuals||{}).estimated_tax_records||0),taxSource=actualMode?`仕入れノートの税率別税額 ${yen(generalInputTax)}${estimatedCount?`（税率未設定 ${estimatedCount}件は原価8%・経費10%で補完）`:''}`:`計画上の原価8%・管理費10%の支払税 ${yen(generalInputTax)}`;
      $('tax-note').innerHTML=taxMethod==='simplified'?`消費税：税込売上10%として預かった税額 ${yen(outputTax)} × 40%で概算。飲食店のみなし仕入率60%を使用しています。`:`消費税：税込売上10%の預り税 ${yen(outputTax)} − ${taxSource}。給与は対象外、借入元金と支払利息は控除に含めていません。${creditExcess?` 現在は仕入税額が ${yen(creditExcess)} 上回るため、納付見込みは0円です。超過分は今後の預り税との相殺目安として表示しています。`:''}`;
      const loan=num('loan-payment'),inv=num('investment'),cash=ordinary-corp-ct-loan-inv;
      $('cash-flow').innerHTML=`<div class="cash-line"><span>経常利益からスタート</span><strong>${yen(ordinary)}</strong></div><div class="cash-line"><span>税金の支払</span><strong>− ${yen(ct+corp)}</strong></div><div class="cash-line"><span>借入元金・設備投資</span><strong>− ${yen(loan+inv)}</strong></div><div class="cash-line final"><span>手元資金の増減目安</span><strong class="${cash<0?'negative':''}">${yen(cash)}</strong></div>`;
      moneyIds.forEach(formatMoney);
    }
    moneyIds.forEach(id=>{$(id).addEventListener('focus',event=>{event.target.value=String(event.target.value).replace(/,/g,'');event.target.select()});$(id).addEventListener('blur',()=>{formatMoney(id);update()})});
    ids.filter(id=>!['sales','cogs','cogs-rate','personnel','personnel-rate'].includes(id)).forEach(id=>$(id).addEventListener('input',update));
    $('sales').addEventListener('input',()=>{syncPlan();update()});
    ['cogs','personnel'].forEach(id=>$(id).addEventListener('input',()=>{if($(`${id}-mode`).value==='amount')syncPlanField(id);if(id==='cogs')syncPlanField('personnel');update()}));
    ['cogs-rate','personnel-rate'].forEach(id=>$(id).addEventListener('input',()=>{const name=id.replace('-rate','');if($(`${name}-mode`).value==='rate')syncPlanField(name);if(name==='cogs')syncPlanField('personnel');update()}));
    modes.forEach(id=>$(id).addEventListener('change',()=>{syncPlan();update()}));
    try{const local=JSON.parse(localStorage.getItem('habitory-future-plan')||'null'),saved=Object.keys(window.miraiSavedPlan||{}).length?window.miraiSavedPlan:local;if(saved){ids.forEach(id=>{if(saved[id]!==undefined)$(id).value=saved[id]});modes.forEach(id=>{if(saved[id]!==undefined)$(id).value=saved[id]});if(saved['linkage-version']!=='amount-default-v1'){$('cogs-mode').value='amount';$('personnel-mode').value='amount'}if(saved['personnel-plan-basis']!=='gross-profit'){const gross=Math.max(0,num('sales')-num('cogs'));$('personnel-rate').value=gross?((num('personnel')/gross)*100).toFixed(1):0}if(saved['other-expenses']===undefined&&saved['other-sga']!==undefined){$('rent').value=0;$('utilities').value=0;$('advertising').value=0;$('other-expenses').value=saved['other-sga']}if(saved.sga!==undefined&&saved.personnel===undefined){$('personnel').value=Math.round(saved.sga*.65);$('other-expenses').value=Math.round(saved.sga*.35)}}}catch(e){}
    root._collectPlan=()=>{const data={'personnel-plan-basis':'gross-profit','linkage-version':'amount-default-v1'};[...ids,...modes].forEach(id=>data[id]=$(id).value);return data};
    $('save-plan').onclick=()=>{const bridge=document.getElementById('save-plan-server');if(bridge)bridge.click()};
    let simulationData=null;
    function setView(mode){
      const provisional=mode==='provisional',fields=$('plan-fields').querySelectorAll('input,select');
      if(provisional){
        root.dataset.view='provisional';
        simulationData={};[...ids,...modes].forEach(id=>simulationData[id]=$(id).value);
        const actual=window.miraiActuals||{};$('sales').value=actual.sales||0;$('cogs').value=actual.cogs||0;$('cogs-mode').value='amount';$('personnel').value=0;$('personnel-mode').value='amount';$('rent').value=0;$('utilities').value=0;$('advertising').value=actual.advertising||0;$('other-expenses').value=(actual.other||0)+(actual.payment_fees||0);$('non-op-income').value=0;$('non-op-expense').value=0;
        fields.forEach(field=>field.disabled=true);$('save-plan').disabled=true;$('view-note').className='view-note provisional';$('view-note').textContent=`暫定実績：売上・仕入れ・営業用消耗品・一般経費・広告費・決済手数料見込（${yen(actual.payment_fees||0)}）を反映しています。人件費など未入力の項目は0円のため、確定利益ではありません。`;$('legend-title').textContent='現在の実際の比率（入力済み実績から自動計算）';
      }else{
        root.dataset.view='simulation';
        if(simulationData){[...ids,...modes].forEach(id=>{if(simulationData[id]!==undefined)$(id).value=simulationData[id]})}
        fields.forEach(field=>field.disabled=false);$('save-plan').disabled=false;$('view-note').className='view-note simulation';$('view-note').textContent='入力した計画値で「こうなったら利益はいくら残るか」を試算しています。';$('legend-title').textContent='試算結果の実際の比率（入力値から自動計算）';syncPlan();
      }
      $('view-simulation').classList.toggle('active',!provisional);update();
    }
    $('view-simulation').onclick=()=>setView('simulation');
    syncPlan();update();
  }
  init();
})();
</script>
            '''
        )
