import json
from calendar import monthrange
from datetime import datetime

from nicegui import ui

from core.auth import current_role, log_out, require_app_access, require_permission
from core.clock import today_jst
from core.financials import financials
from core.monthly_evaluation import MonthlyEvaluationService
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


def _render_future_financials_home(selected_month=None, detailed=False):
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("未来決算", app_name="mirai-kessan")
    content = Theme.shell(
        "未来決算",
        "",
        brand="未来決算",
    )
    actual_current_month = today_jst().strftime("%Y-%m")
    current_month = _valid_month(selected_month) or actual_current_month
    if not detailed:
        from pages.finance_home import compact_finance_home
        with content:
            compact_finance_home(current_month)
        return
    evaluator = MonthlyEvaluationService(financials, purchases, staffing)
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
    management_preview = evaluator.preview(current_month, today)
    landing_forecast = evaluator.forecast(current_month, today)
    saved_evaluation = financials.get_monthly_evaluation(current_month)
    material_warnings = evaluator.anomalies(management_preview)
    recent_trends = evaluator.history(current_month, 6, today) + [
        {"month": current_month, **management_preview["metrics"]}
    ]
    targets = management_preview["targets"]
    provisional_health = (
        "safe" if operating_profit >= 0
        and (cost_rate <= targets["cost_rate"] if sales_total else False)
        and (personnel_rate <= targets["personnel_rate"] if personnel_rate is not None else False)
        else "warning" if operating_profit >= 0 else "danger"
    )
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
            health_label = {"safe": "安全", "warning": "注意", "danger": "危険"}[
                saved_evaluation.get("health", provisional_health)
            ]
            ui.label(f"店舗の健康状態　{health_label}").classes(
                f"health-chip {saved_evaluation.get('health', provisional_health)}"
            )
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
                for title, raw_value, target, previous_value in (
                    ("原価率", cost_rate if sales_total else None, targets["cost_rate"], management_preview["comparisons"]["cost_rate"]["previous"]),
                    ("人件費率", personnel_rate, targets["personnel_rate"], management_preview["comparisons"]["personnel_rate"]["previous"]),
                    ("労働分配率", labor_rate, .50, None),
                ):
                    tone = (
                        "unknown" if raw_value is None else
                        "safe" if raw_value <= target else
                        "warning" if raw_value <= target + .03 else "danger"
                    )
                    with ui.element("div").classes(f"snapshot-ratio-card {tone}"):
                        ui.label(title).classes("snapshot-ratio-label")
                        ui.label(
                            f"{raw_value * 100:.1f}%" if raw_value is not None else "—"
                        ).classes("snapshot-ratio-value")
                        if raw_value is not None:
                            comparison = (
                                f"前月 {(raw_value-previous_value)*100:+.1f}pt"
                                if previous_value is not None else f"目標 {target*100:.1f}%"
                            )
                            ui.label(comparison).classes("snapshot-ratio-delta")
            with ui.element("div").classes("snapshot-profit-grid w-full q-mt-sm"):
                for title, value in (
                    ("営業利益", operating_profit),
                    ("返済後に残る利益", cash_after_tax_and_loan),
                ):
                    with ui.element("div").classes(
                        "snapshot-profit-card " + ("negative" if value < 0 else "")
                    ):
                        ui.label(title).classes("text-[9px] opacity-70")
                        ui.label(f"¥{value:,}").classes("text-base font-black")
            if landing_forecast:
                ui.label(
                    f"月末予想　売上 ¥{landing_forecast['sales']:,} ／ "
                    f"営業利益 ¥{landing_forecast['operating_profit']:,}"
                ).classes("landing-line")
            if material_warnings:
                ui.label("⚠ " + material_warnings[0]).classes("snapshot-warning")
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

        with ui.card().classes("surface-card monthly-evaluation w-full q-pa-md q-mb-md"):
            with ui.row().classes("w-full items-start justify-between no-wrap"):
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label("月次経営評価").classes("text-base font-black")
                    ui.label("売上だけでなく、利益率・費用・返済まで総合判定").classes(
                        "text-[9px] text-grey-6"
                    )
                if saved_evaluation:
                    ui.label(saved_evaluation.get("rank", "—")).classes(
                        "evaluation-rank " + saved_evaluation.get("health", "warning")
                    )

            evaluation_changed = bool(
                saved_evaluation
                and saved_evaluation.get("metrics") != management_preview["metrics"]
            )
            if saved_evaluation:
                ui.label(
                    f"総合スコア {saved_evaluation.get('score', 0)} / 100"
                ).classes("evaluation-score")
                ui.label(saved_evaluation.get("summary", "")).classes("evaluation-summary")
                if evaluation_changed:
                    ui.label("評価後に数字が変更されています。再評価してください").classes(
                        "evaluation-stale"
                    )
                with ui.element("div").classes("evaluation-columns"):
                    for title, icon, values, kind in (
                        ("良かった点", "trending_up", saved_evaluation.get("good", []), "good"),
                        ("改善ポイント", "priority_high", saved_evaluation.get("issues", []), "warning"),
                        ("来月やるべきこと", "flag", saved_evaluation.get("actions", []), "action"),
                    ):
                        with ui.element("div").classes(f"evaluation-list {kind}"):
                            with ui.row().classes("items-center gap-1 no-wrap"):
                                ui.icon(icon).classes("text-sm")
                                ui.label(title).classes("text-[10px] font-black")
                            for value in values:
                                ui.label("・" + value).classes("evaluation-item")
            else:
                missing = management_preview["completion"]["missing"]
                if missing:
                    ui.label("正式評価まで：" + "・".join(missing)).classes(
                        "evaluation-waiting"
                    )
                ui.label(
                    "月途中は暫定表示のままです。月末後、入力を確認してから評価を保存します。"
                ).classes("evaluation-summary")

            def save_evaluation():
                try:
                    result = evaluator.evaluate(current_month, today)
                    financials.save_monthly_evaluation(current_month, result)
                except ValueError as error:
                    ui.notify(str(error), type="warning")
                    return
                ui.notify("月次経営評価を保存しました", type="positive")
                ui.navigate.to(dashboard_path)

            evaluation_button = ui.button(
                "再評価して保存" if saved_evaluation else "今月の入力を完了して評価する",
                icon="verified", on_click=save_evaluation,
            ).props("unelevated no-caps").classes("evaluation-button w-full q-mt-md")
            if not management_preview["completion"]["ready"]:
                evaluation_button.props("disable")

            with ui.expansion("数字の意味と比較を見る", icon="compare_arrows").classes(
                "evaluation-detail w-full q-mt-sm"
            ):
                previous = management_preview["comparisons"]
                for label, key, value, is_rate in (
                    ("売上", "sales", sales_total, False),
                    ("原価率", "cost_rate", management_preview["metrics"]["cost_rate"], True),
                    ("人件費率", "personnel_rate", management_preview["metrics"]["personnel_rate"], True),
                    ("営業利益率", "operating_margin", management_preview["metrics"]["operating_margin"], True),
                ):
                    prior = previous[key]["previous"]
                    if is_rate:
                        shown = f"{value*100:.1f}%" if value is not None else "—"
                        delta = f"前月比 {(value-prior)*100:+.1f}pt" if value is not None and prior is not None else "前月比較なし"
                        average = previous[key]["average3"]
                        year_ago = previous[key]["previous_year"]
                        extra = " ／ ".join(
                            part for part in (
                                f"3ヶ月平均 {average*100:.1f}%" if average is not None else "",
                                f"前年同月 {year_ago*100:.1f}%" if year_ago is not None else "",
                            ) if part
                        )
                    else:
                        shown = f"¥{value:,}"
                        delta = f"前月比 {((value-prior)/prior)*100:+.1f}%" if prior else "前月比較なし"
                        average = previous[key]["average3"]
                        year_ago = previous[key]["previous_year"]
                        extra = " ／ ".join(
                            part for part in (
                                f"3ヶ月平均 ¥{round(average):,}" if average is not None else "",
                                f"前年同月 ¥{round(year_ago):,}" if year_ago is not None else "",
                            ) if part
                        )
                    with ui.element("div").classes("meaning-row"):
                        ui.label(label).classes("meaning-label")
                        ui.label(shown).classes("meaning-value")
                        ui.label(delta).classes("meaning-delta")
                        if extra:
                            ui.label(extra).classes("meaning-extra")
                ui.label("利益と負担の内訳").classes("detail-subtitle")
                for label, value in (
                    ("粗利益", gross_profit),
                    ("固定費", management_preview["metrics"]["fixed_costs"]),
                    ("営業利益", operating_profit),
                    ("経常利益（登録済み範囲）", management_preview["metrics"]["ordinary_profit"]),
                    ("当期純利益（概算）", management_preview["metrics"]["net_profit"]),
                    ("消費税納付見込", management_preview["metrics"]["consumption_tax_estimate"]),
                    ("借入元金返済", management_preview["metrics"]["loan_payment"]),
                    ("返済後に残る利益", management_preview["metrics"]["post_repayment_profit"]),
                ):
                    with ui.element("div").classes("meaning-row compact"):
                        ui.label(label).classes("meaning-label")
                        ui.label(f"¥{value:,}").classes(
                            "meaning-value " + ("negative-text" if value < 0 else "")
                        )

            with ui.expansion("直近の月次推移", icon="show_chart").classes(
                "evaluation-detail w-full q-mt-sm"
            ):
                max_sales = max((row["sales"] for row in recent_trends), default=1) or 1
                for row in recent_trends:
                    with ui.element("div").classes("trend-row"):
                        ui.label(row["month"].replace("-", "/")).classes("trend-month")
                        with ui.element("div").classes("trend-track"):
                            ui.element("div").classes("trend-bar").style(
                                f"width:{max(3, row['sales']/max_sales*100):.1f}%"
                            )
                        with ui.column().classes("gap-0 items-end"):
                            ui.label(f"売上 ¥{row['sales']:,}").classes("trend-sales")
                            ui.label(
                                f"営業利益 ¥{row['operating_profit']:,}"
                            ).classes(
                                "trend-profit " + ("negative-text" if row["operating_profit"] < 0 else "")
                            )
        ui.add_css("""
        .audit-shortcut{background:linear-gradient(135deg,#1E5A45,#33785F)!important;color:#fff!important;min-height:48px!important;border-radius:16px!important;font-weight:900!important}
        .future-menu{width:min(92vw,420px)!important;border-radius:26px!important}.future-menu-item{min-height:52px!important;justify-content:flex-start!important;font-size:14px!important}
        .metric-value,.rounded-xl .font-bold{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .actual-box-map{width:calc(100% + 12px)!important;margin-left:-6px;margin-right:-6px;height:330px;display:grid;grid-template-columns:1fr 1fr 1fr;overflow:hidden;background:#E8ECE9}.actual-money-box{min-height:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:#fff;overflow:hidden;padding:3px;box-sizing:border-box}.actual-box-map>.actual-money-box{grid-column:1;grid-row:1/3}.actual-cost-block{grid-column:2/4;grid-row:1;min-height:0;display:flex}.actual-cost-block>.actual-money-box,.actual-gross-block>.actual-money-box{width:100%}.actual-gross-block{grid-column:2;grid-row:2;min-height:0;display:flex}.actual-breakdown{grid-column:3;grid-row:2;min-height:0;display:flex;flex-direction:column;overflow:hidden}.actual-block-title{font-size:9px;font-weight:800;line-height:1.1}.actual-block-value{font-size:10px;font-weight:800;line-height:1.15;margin-top:2px;white-space:nowrap}.actual-block-note{font-size:7px;line-height:1.1;margin-top:2px;opacity:.9;white-space:nowrap}
        .snapshot-ratio-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.snapshot-ratio-card{min-width:0;padding:8px 5px;border-radius:12px;background:rgba(255,255,255,.14);text-align:center}.snapshot-ratio-card.safe{box-shadow:inset 0 -3px #77D09A}.snapshot-ratio-card.warning{box-shadow:inset 0 -3px #F0C45F}.snapshot-ratio-card.danger{box-shadow:inset 0 -3px #EF8178}.snapshot-ratio-label{font-size:8px;opacity:.72;white-space:nowrap}.snapshot-ratio-value{font-size:15px;font-weight:900;white-space:nowrap;margin-top:2px}.snapshot-ratio-delta{margin-top:2px;font-size:7px;opacity:.78;white-space:nowrap}
        .health-chip{align-self:flex-start;margin-top:10px;padding:5px 10px;border-radius:999px;font-size:10px;font-weight:950;background:rgba(255,255,255,.15)}.health-chip.safe{color:#BDF1D0}.health-chip.warning{color:#FFE39C}.health-chip.danger{color:#FFC4BC}.snapshot-profit-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}.snapshot-profit-card{min-width:0;padding:9px;border-radius:12px;background:rgba(177,239,199,.15)}.snapshot-profit-card.negative{background:rgba(255,149,137,.18);color:#FFD5CF}.snapshot-profit-card .font-black{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-variant-numeric:tabular-nums}.landing-line{margin-top:8px;padding:8px 10px;border-radius:10px;background:rgba(255,255,255,.12);font-size:9px;font-weight:850}.snapshot-warning{margin-top:7px;padding:7px 9px;border-radius:9px;background:rgba(255,215,130,.18);color:#FFE7AF;font-size:9px;font-weight:850}
        .monthly-evaluation{border:1px solid #E1E8E3!important;background:linear-gradient(155deg,#fff 0%,#F6FAF7 100%)!important}.evaluation-rank{display:flex;align-items:center;justify-content:center;flex:0 0 auto;width:52px;height:52px;border-radius:16px;font-family:Georgia,serif;font-size:29px;font-weight:950}.evaluation-rank.safe{background:#DDF2E5;color:#1D704A}.evaluation-rank.warning{background:#FFF0C9;color:#946510}.evaluation-rank.danger{background:#FCE0DD;color:#A83E37}.evaluation-score{margin-top:13px;color:#173D2E;font-size:22px;font-weight:950;font-variant-numeric:tabular-nums}.evaluation-summary{margin-top:7px;color:#53625A;font-size:11px;line-height:1.65}.evaluation-stale,.evaluation-waiting{margin-top:10px;padding:9px 11px;border-radius:11px;background:#FFF1D6;color:#8A5C13;font-size:10px;font-weight:850}.evaluation-columns{display:grid;gap:8px;margin-top:12px}.evaluation-list{padding:11px;border-radius:13px}.evaluation-list.good{background:#E9F5ED;color:#276347}.evaluation-list.warning{background:#FFF3DA;color:#7C571A}.evaluation-list.action{background:#EAF1FA;color:#315A88}.evaluation-item{margin-top:4px;font-size:10px;line-height:1.45}.evaluation-button{min-height:48px!important;border-radius:14px!important;background:#1E654A!important;font-weight:950!important}.evaluation-detail{border-radius:13px!important;background:#F3F6F4!important}.meaning-row{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:9px 2px;border-bottom:1px solid #E4E9E6}.meaning-row.compact{padding:7px 2px}.meaning-label{font-size:10px;font-weight:850;color:#5F6D65}.meaning-value{font-size:13px;font-weight:950;color:#173D2E}.meaning-delta,.meaning-extra{grid-column:1/-1;text-align:right;font-size:9px;color:#7B8780}.meaning-extra{font-size:8px;color:#8E9892}.detail-subtitle{margin-top:14px;font-size:11px;font-weight:950;color:#315A45}.negative-text{color:#BA433D!important}.trend-row{display:grid;grid-template-columns:42px minmax(40px,1fr) auto;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid #E4E9E6}.trend-month{font-size:9px;font-weight:850;color:#68756E}.trend-track{height:8px;border-radius:999px;background:#E2E8E4;overflow:hidden}.trend-bar{height:100%;border-radius:999px;background:linear-gradient(90deg,#4D8B6E,#87B99E)}.trend-sales{font-size:9px;font-weight:900;color:#284F3E}.trend-profit{font-size:8px;color:#567064}
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
        menu_card("決算分析", "決算書を入力して会社の状態を診断", "assessment", "#75599B", "/mirai-kessan/financial-analysis")

        ui.add_css("""
        .quick-menu-icon{width:52px;height:52px;min-width:52px;max-width:52px;border-radius:15px;display:flex;align-items:center;justify-content:center;overflow:hidden;color:#fff;box-shadow:0 7px 15px color-mix(in srgb,var(--icon-color) 28%,transparent);border:1px solid rgba(255,255,255,.28)}
        .quick-menu-glyph{font-size:25px!important;line-height:1!important;width:28px;height:28px;display:flex!important;align-items:center;justify-content:center;overflow:hidden;text-shadow:0 1px 3px rgba(0,0,0,.14)}
        """)


@ui.page("/mirai-kessan/details")
def financial_details():
    _render_future_financials_home(detailed=True)


@ui.page("/mirai-kessan/forecast")
def financial_forecast_page(month: str = "", price_change: int = 0):
    if not require_app_access("future_financials") or not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("着地予測・比較｜未来決算", app_name="mirai-kessan")
    content = Theme.shell("未来を試す", "実績を残したまま、これからの条件を比較", brand="未来決算")
    from pages.landing_forecast import render_landing_forecast
    with content:
        render_landing_forecast(_valid_month(month) or today_jst().strftime("%Y-%m"), price_change=price_change)
        with ui.expansion("経営分析・コンサル", icon="analytics").classes("w-full"):
            for label,path in [("経営の詳しい数字","/mirai-kessan/details"),("経営コンサル","/mirai-kessan/consulting"),("決算分析","/mirai-kessan/financial-analysis")]:
                ui.button(label,on_click=lambda _,url=path:ui.navigate.to(url)).props("flat").classes("w-full")


@ui.page("/mirai-kessan/input")
def future_financials_input_hub():
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_input", "/mirai-kessan/login"):
        return
    Theme.page("未来決算｜日常入力", app_name="mirai-kessan")

    content = Theme.shell("未来決算 日常入力", "許可された入力だけを、迷わず記録",
                          brand="未来決算")
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


    with content:
        if current_role() in {"owner", "executive"}:
            with ui.expansion("人件費・月次入力・確認", icon="settings").classes("w-full"):
                for label,path in [("人件費管理","/mirai-kessan/staffing"),("立替管理","/mirai-kessan/advances"),("月次費用","/mirai-kessan/details"),("入力チェック","/mirai-kessan/audit")]:
                    ui.button(label,on_click=lambda _,url=path:ui.navigate.to(url)).props("flat").classes("w-full")
        with ui.expansion("アカウント", icon="person").classes("w-full"):
            if current_role() == "owner":
                ui.button("R-BASEへ戻る",on_click=lambda:ui.navigate.to("/")).props("flat")
            ui.button("ログアウト",on_click=lambda:log_out("/mirai-kessan/login")).props("flat")


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
    ui.navigate.to("/mirai-kessan/forecast")
