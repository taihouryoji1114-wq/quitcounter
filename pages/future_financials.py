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


def _render_future_financials_home(selected_month=None, detailed=False, evaluation=False):
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("未来決算", app_name="mirai-kessan")
    content = Theme.shell(
        ("月次経営評価" if evaluation else "月次費用") if detailed else "未来決算",
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
    dashboard_path = ("/mirai-kessan/evaluation" if evaluation else "/mirai-kessan/details") + "?month=" + current_month
    with content:
        month_field = ui.input("対象月", value=current_month).props("type=month outlined").classes("w-full q-mb-md")
        month_field.on("change", lambda: ui.navigate.to(("/mirai-kessan/evaluation" if evaluation else "/mirai-kessan/details") + "?month=" + str(month_field.value)))
        if evaluation:
            with ui.card().classes("surface-card monthly-evaluation w-full q-pa-md q-mb-md"):
                with ui.row().classes("w-full items-start justify-between no-wrap"):
                    with ui.column().classes("gap-0 min-w-0"):
                        ui.label("月次経営評価").classes("text-base font-black")
                        ui.label("売上だけでなく、利益率・費用・返済まで総合判定").classes(
                            "text-[9px] finance-readable"
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
        else:
            with ui.card().classes("surface-card w-full q-pa-lg"):
                ui.label("月次費用を入力").classes("text-lg font-bold q-mb-xs")
                ui.label("請求や金額が分かった項目から入力してください。").classes(
                    "text-xs finance-readable q-mb-md"
                )
                with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
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
                ).classes("text-[9px] finance-readable q-mb-sm")
                loan_input = ui.number(
                    "借入元金返済", value=operations["loan_payment"] or None, min=0, step=1
                ).props("outlined prefix=¥ inputmode=numeric").classes("w-full")

                def save_operations():
                    try:
                        financials.save_monthly_operations(
                            current_month,
                            financials.get_monthly_operations(current_month)["personnel"],
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


@ui.page("/mirai-kessan/details")
def financial_details(month: str = ""):
    _render_future_financials_home(month, detailed=True)


@ui.page("/mirai-kessan/evaluation")
def financial_evaluation(month: str = ""):
    _render_future_financials_home(month, detailed=True, evaluation=True)


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
            for label,path in [("経営コンサル","/mirai-kessan/consulting"),("決算分析","/mirai-kessan/financial-analysis")]:
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
            *(([("人件費管理", "勤務時間・給与・会社負担", "groups", "/mirai-kessan/staffing"),
               ("立替管理", "立替・返金・残額", "account_balance_wallet", "/mirai-kessan/advances"),
               ("月次費用", "家賃・光熱費・広告費・返済", "receipt_long", "/mirai-kessan/details")]
               if current_role() in {"owner", "executive"} else
               [("勤務・出勤入力", "出勤状況と勤務時間", "groups", "/mirai-kessan/attendance")])),
        ):
            with ui.card().classes("habit-card w-full q-pa-lg q-mb-sm cursor-pointer").on(
                "click", lambda _, target=path: ui.navigate.to(target)):
                with ui.row().classes("w-full items-center no-wrap"):
                    ui.icon(icon).classes("text-3xl text-primary q-mr-md")
                    with ui.column().classes("gap-0 grow"):
                        ui.label(title).classes("text-lg font-black")
                        ui.label(subtitle).classes("text-xs finance-readable")
                    ui.icon("chevron_right").classes("finance-readable")


    with content:
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
