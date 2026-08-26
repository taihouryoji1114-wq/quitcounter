from datetime import date
from pathlib import Path

from nicegui import ui

from core.auth import require_app_access, require_permission
from core.annual_reports import annual_reports
from core.clock import today_jst
from core.consulting import consulting
from core.financial_report_data import PAYMENT_COLUMNS, build_financial_report
from core.financial_report_pdf import create_financial_report_pdf
from core.financials import financials
from core.purchases import purchases
from core.staffing import staffing
from core.theme import Theme


@ui.page("/mirai-kessan/reports")
def financial_reports_page():
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("集計・印刷｜未来決算", app_name="mirai-kessan")
    today = today_jst()
    content = Theme.shell("集計・印刷", "経営判断に必要な数字を、紙とPDFで同じ構成に",
                          back_to="/mirai-kessan/dashboard")
    with content:
        with ui.card().classes("surface-card report-controls w-full q-pa-lg q-mb-md"):
            with ui.element("div").classes("report-date-grid w-full"):
                start_date = ui.input("開始日", value=today.replace(day=1).isoformat()).props("type=date outlined")
                end_date = ui.input("終了日", value=today.isoformat()).props("type=date outlined")

            def selected():
                try:
                    start, end = date.fromisoformat(str(start_date.value)), date.fromisoformat(str(end_date.value))
                except ValueError as error:
                    raise ValueError("日付を正しく入力してください") from error
                if start > end:
                    raise ValueError("開始日は終了日以前にしてください")
                return start.isoformat(), end.isoformat()

            def update_report():
                try:
                    selected()
                except ValueError as error:
                    ui.notify(str(error), type="negative"); return
                report_view.refresh()

            def download_pdf():
                try:
                    start, end = selected()
                except ValueError as error:
                    ui.notify(str(error), type="negative"); return
                values = build_financial_report(start, end)
                output = Path("/tmp") / f"未来決算_{start}_{end}.pdf"
                create_financial_report_pdf(output, values)
                ui.download(str(output), filename=output.name)

            with ui.row().classes("w-full gap-2 q-mt-md"):
                ui.button("集計する", icon="calculate", on_click=update_report).props("unelevated no-caps").classes("grow")
                ui.button("PDFとして保存", icon="picture_as_pdf", on_click=download_pdf).props(
                    "unelevated no-caps color=negative").classes("grow")
                ui.button("紙に印刷", icon="print", on_click=lambda: ui.run_javascript("window.print()" )).props(
                    "outline no-caps").classes("grow")

        with ui.card().classes("surface-card report-controls w-full q-pa-md q-mb-md"):
            ui.label("経営資料セット").classes("text-base font-black")
            ui.label("用途の違う資料は分けて、必要なものだけ確認・印刷します").classes("text-[10px] text-grey-6 q-mb-sm")
            with ui.element("div").classes("report-links"):
                for title, caption, icon, path in (
                    ("期間実績", "売上・利益・決済・仕入", "summarize", "/mirai-kessan/reports"),
                    ("経営コンサル", "問題の優先順位と次の行動", "psychology", "/mirai-kessan/reports/consulting"),
                    ("決算分析", "会社の収益性と安全性", "assessment", "/mirai-kessan/reports/financial-analysis"),
                    ("人件費管理", "総負担額・比率・勤務状況", "groups", "/mirai-kessan/reports/staffing"),
                ):
                    with ui.card().classes("report-link-card q-pa-sm cursor-pointer").on(
                        "click", lambda _, target=path: ui.navigate.to(target)):
                        ui.icon(icon).classes("text-primary text-lg")
                        ui.label(title).classes("text-xs font-black")
                        ui.label(caption).classes("text-[8px] text-grey-6")

        @ui.refreshable
        def report_view():
            values = build_financial_report(str(start_date.value), str(end_date.value))
            ratios = values["ratios"]
            with ui.element("section").classes("print-report w-full"):
                ui.label("未来決算　期間集計レポート").classes("report-title")
                ui.label(f"集計期間　{values['start'].replace('-', '/')} 〜 {values['end'].replace('-', '/')}").classes("report-period")
                with ui.element("div").classes("report-metrics w-full q-mt-md"):
                    for title, value, style in (
                        ("売上", values["sales_total"], "sales"), ("原価", values["cost_total"], "cost"),
                        ("粗利", values["gross_profit"], "gross"), ("人件費", values["personnel"], "personnel"),
                        ("営業経費", values["operating_expenses"], "expense"),
                        ("営業利益" if values["operating_profit"] >= 0 else "営業損失", values["operating_profit"], "profit"),
                    ):
                        with ui.element("div").classes(f"report-metric {style}"):
                            ui.label(title).classes("report-metric-label"); ui.label(f"¥{value:,}").classes("report-metric-value")

                ui.label("重要な経営比率").classes("report-section-title")
                with ui.element("div").classes("ratio-grid"):
                    for label, key in (("原価率", "cost_rate"), ("粗利率", "gross_margin"),
                                       ("人件費率", "personnel_rate"), ("労働分配率", "labor_distribution"),
                                       ("営業利益率", "operating_margin")):
                        with ui.element("div").classes("ratio-card"):
                            ui.label(label); value = ratios[key]
                            ui.label("—" if value is None else f"{value * 100:.1f}%").classes("ratio-value")

                ui.label("利益ブロック").classes("report-section-title")
                render_profit_block(values)

                ui.label("営業経費の内訳").classes("report-section-title")
                expense_rows = list(values["expense_breakdown"])
                render_two_column_table(expense_rows, "項目", "期間配賦額",
                                        ("営業経費合計", values["operating_expenses"]))

                ui.label("決済方法別集計").classes("report-section-title")
                payment_rows = [(label, values["payment_totals"][field]) for label, field in PAYMENT_COLUMNS]
                payment_rows.append(("ポイント", values["payment_totals"]["points_sales"]))
                payment_rows.append(("未分類", values["payment_totals"]["unclassified_sales"]))
                render_two_column_table(payment_rows, "決済方法", "期間合計",
                                        ("決済内訳合計", sum(value for _, value in payment_rows)))

                ui.label("仕入れ先別集計").classes("report-section-title")
                with ui.element("div").classes("report-table-wrap"), ui.element("table").classes("report-table"):
                    table_header(("仕入れ先", "件数", "原価", "営業用品", "一般経費", "合計"))
                    with ui.element("tbody"):
                        for supplier, row in values["suppliers"]:
                            table_row((supplier, f"{row['count']}件", money(row["cost"]), money(row["supply"]),
                                       money(row["expense"]), money(row["total"])))
                        table_row(("合計", f"{len(values['purchases'])}件", money(values["cost_total"]),
                                   money(values["supply_total"]), money(values["expense_total"]),
                                   money(values["cost_total"] + values["supply_total"] + values["expense_total"])), "total-row")

                ui.label("日別売上明細").classes("report-section-title")
                headers = ("日付", "ランチ", "ディナー", "現金", "クレジット", "PayPay", "電子マネー", "旅行社", "ポイント", "売上合計")
                totals = [0] * 9
                with ui.element("div").classes("report-table-wrap"), ui.element("table").classes("report-table"):
                    table_header(headers)
                    with ui.element("tbody"):
                        for row in sorted(values["sales"], key=lambda item: str(item.get("date", ""))):
                            numbers = [int(row.get("lunch_sales", 0) or 0), int(row.get("dinner_sales", 0) or 0),
                                       *[int(row.get(field, 0) or 0) for _, field in PAYMENT_COLUMNS],
                                       int(row.get("tabelog_points_sales", 0) or 0) + int(row.get("hotpepper_points_sales", 0) or 0),
                                       int(row.get("amount", 0) or 0)]
                            totals = [a + b for a, b in zip(totals, numbers)]
                            table_row((str(row.get("date", "")).replace("-", "/"), *[money(number) for number in numbers]))
                        table_row(("合計", *[money(number) for number in totals]), "total-row")

        report_view()
        ui.add_css(REPORT_CSS)


def report_shell(title, subtitle):
    if not require_app_access("future_financials"):
        return None
    if not require_permission("future_dashboard", "/mirai-kessan/input"):
        return None
    Theme.page(f"{title}｜未来決算", app_name="mirai-kessan")
    content = Theme.shell(title, subtitle, back_to="/mirai-kessan/reports")
    with content:
        with ui.row().classes("report-controls w-full gap-2 q-mb-md"):
            ui.button("紙・PDFで出力", icon="print", on_click=lambda: ui.run_javascript("window.print()")) \
                .props("unelevated no-caps").classes("grow")
            ui.button("資料一覧", icon="folder_open", on_click=lambda: ui.navigate.to("/mirai-kessan/reports")) \
                .props("outline no-caps").classes("grow")
    ui.add_css(REPORT_CSS + MANAGEMENT_REPORT_CSS)
    return content


def report_heading(title, period, description):
    ui.label(title).classes("report-title")
    ui.label(period).classes("report-period")
    ui.label(description).classes("management-lead")


def management_metric(label, value, tone=""):
    with ui.element("div").classes(f"management-metric {tone}"):
        ui.label(label).classes("management-metric-label")
        ui.label(value).classes("management-metric-value")


@ui.page("/mirai-kessan/reports/consulting")
def consulting_report_page():
    content = report_shell("経営コンサル資料", "問題を重要な順に並べ、次の行動を確認")
    if content is None:
        return
    today = today_jst()
    month = today.strftime("%Y-%m")
    overview = consulting.executive_overview(month)
    diagnosis = consulting.diagnose(month)
    snapshot = consulting.annual_snapshot(month)
    with content, ui.element("section").classes("print-report management-report w-full"):
        period = f"基準　{snapshot['period'].replace('-', '/')} 決算" if snapshot else "決算書未入力"
        report_heading("未来決算　経営コンサル報告書", period,
                       "数字の説明ではなく、会社を守りながら改善する順番を示します。")
        with ui.element("div").classes(f"consulting-verdict {overview['level']}"):
            ui.label(overview["label"]).classes("text-xs font-black")
            ui.label(overview["headline"]).classes("text-xl font-black")
        ui.label("まず取り組むこと").classes("report-section-title")
        with ui.element("div").classes("action-list"):
            for index, item in enumerate(diagnosis["recommendations"][:5], 1):
                with ui.element("article").classes("action-card"):
                    ui.label(f"優先 {index}").classes("action-rank")
                    ui.label(item["title"]).classes("action-title")
                    ui.label(item["why"]).classes("action-reason")
                    with ui.element("div").classes("action-next"):
                        ui.label("次の行動").classes("action-next-label")
                        ui.label(item["action"])
                    ui.label(f"目標：{item['target']}　／　期限：{item['deadline']}").classes("action-target")
        ui.label("判断できること・まだ不足していること").classes("report-section-title")
        with ui.element("div").classes("knowledge-grid"):
            for title, rows, tone in (("分かっている", overview["known"], "known"),
                                      ("まだ分からない", overview["unknown"], "unknown")):
                with ui.element("div").classes(f"knowledge-card {tone}"):
                    ui.label(title).classes("font-black")
                    for row in rows:
                        ui.label(f"・{row}").classes("text-xs")
        if overview.get("next_input"):
            ui.label(f"次に入力するもの：{overview['next_input']}").classes("next-input")


@ui.page("/mirai-kessan/reports/financial-analysis")
def financial_analysis_report_page():
    content = report_shell("決算分析資料", "収益性と安全性を1枚で確認")
    if content is None:
        return
    periods = annual_reports.list_periods()
    with content, ui.element("section").classes("print-report management-report w-full"):
        if not periods:
            report_heading("未来決算　決算分析報告書", "決算書未入力", "決算書を入力すると分析できます。")
            ui.button("決算書を入力", on_click=lambda: ui.navigate.to("/mirai-kessan/financial-analysis"))
            return
        period = periods[0]
        values = annual_reports.get_report(period)["current"]
        result = annual_reports.calculate(values)
        report_heading("未来決算　決算分析報告書", f"決算期　{period.replace('-', '/')}（9月締め）",
                       "利益を生む力と、支払いに耐える力を分けて確認します。")
        with ui.element("div").classes("management-metrics"):
            management_metric("売上", money(values.get("sales", 0)))
            management_metric("粗利", money(result["gross_profit"]), "good")
            management_metric("営業利益", money(result["operating_profit"]), "good" if result["operating_profit"] >= 0 else "danger")
            management_metric("純利益", money(result["net_income"]), "good" if result["net_income"] >= 0 else "danger")
        ui.label("会社の安全性").classes("report-section-title")
        working_capital = result["current_assets"] - result["current_liabilities"]
        with ui.element("div").classes("management-metrics"):
            management_metric("純資産", money(result["equity"]), "danger" if result["equity"] < 0 else "good")
            management_metric("運転資金", money(working_capital), "danger" if working_capital < 0 else "good")
            management_metric("流動比率", ratio_text(result["current_ratio"]), "danger" if (result["current_ratio"] or 0) < 1 else "good")
            management_metric("自己資本比率", ratio_text(result["equity_ratio"]), "danger" if (result["equity_ratio"] or 0) < .1 else "good")
        ui.label("収益性").classes("report-section-title")
        with ui.element("div").classes("management-metrics three"):
            management_metric("粗利率", ratio_text(result["gross_margin"]))
            management_metric("営業利益率", ratio_text(result["operating_margin"]), "danger" if (result["operating_margin"] or 0) < 0 else "good")
            management_metric("現預金月商倍率", "—" if result["cash_months"] is None else f"{result['cash_months']:.1f}か月",
                              "danger" if (result["cash_months"] or 0) < 1 else "good")
        ui.label("確認ポイント").classes("report-section-title")
        messages = []
        if result["balance_gap"]:
            messages.append(f"貸借差額が {money(abs(result['balance_gap']))} あります。分析確定前に入力を照合してください。")
        if working_capital < 0:
            messages.append(f"1年以内の支払いが短期資産を {money(abs(working_capital))} 上回っています。資金繰りを最優先で確認します。")
        if result["equity"] < 0:
            messages.append(f"純資産が {money(result['equity'])} の債務超過です。毎年の黒字額と解消年数を決めます。")
        if not messages:
            messages.append("重大な貸借不一致・債務超過・短期資金不足は見つかりません。")
        for message in messages:
            ui.label(f"・{message}").classes("analysis-message")


@ui.page("/mirai-kessan/reports/staffing")
def staffing_report_page():
    content = report_shell("人件費管理資料", "社員・アルバイト・会社負担を分けて確認")
    if content is None:
        return
    today = today_jst()
    month = today.strftime("%Y-%m")
    summary = staffing.month_cost_summary(month, today)
    sales = financials.monthly_sales_total(month)
    cost = purchases.monthly_total(month, kind="cost")
    gross = sales - cost
    personnel_rate = summary["company_cost"] / sales if sales else None
    distribution = summary["company_cost"] / gross if gross > 0 else None
    with content, ui.element("section").classes("print-report management-report w-full"):
        report_heading("未来決算　人件費管理報告書", f"対象月　{month.replace('-', '/')}　{today.day}日現在",
                       "給与だけでなく、交通費と会社負担の保険料まで含めて判断します。")
        with ui.element("div").classes("management-metrics"):
            management_metric("給与総額", money(summary["gross_wages"]))
            management_metric("交通費", money(summary["transportation"]))
            management_metric("会社負担保険", money(summary["employer_insurance"]))
            management_metric("会社の総負担", money(summary["company_cost"]), "primary")
        with ui.element("div").classes("management-metrics three"):
            management_metric("人件費率", ratio_text(personnel_rate))
            management_metric("労働分配率", ratio_text(distribution))
            management_metric("月末着地予想", money(summary["forecast_company_cost"]), "primary")
        ui.label("社員とアルバイトの内訳").classes("report-section-title")
        group_rows = []
        for key, label in (("salaried", "社員"), ("hourly", "アルバイト")):
            group = summary["groups"][key]
            group_rows.append((label, group["gross_wages"], group["transportation"],
                               group["employer_insurance"], group["company_cost"]))
        with ui.element("div").classes("report-table-wrap"), ui.element("table").classes("report-table"):
            table_header(("区分", "給与", "交通費", "会社負担保険", "総負担"))
            with ui.element("tbody"):
                for row in group_rows:
                    table_row((row[0], *[money(value) for value in row[1:]]))
                table_row(("合計", money(summary["gross_wages"]), money(summary["transportation"]),
                           money(summary["employer_insurance"]), money(summary["company_cost"])), "total-row")


def money(value):
    return f"¥{int(value):,}"


def ratio_text(value):
    return "—" if value is None else f"{value * 100:.1f}%"


def table_header(labels):
    with ui.element("thead"), ui.element("tr"):
        for label in labels:
            with ui.element("th"): ui.label(label)


def table_row(values, row_class=""):
    with ui.element("tr").classes(row_class):
        for value in values:
            with ui.element("td"): ui.label(str(value))


def render_two_column_table(rows, first, second, total):
    with ui.element("div").classes("report-table-wrap"), ui.element("table").classes("report-table compact-table"):
        table_header((first, second))
        with ui.element("tbody"):
            for label, value in rows: table_row((label, money(value)))
            table_row((total[0], money(total[1])), "total-row")


def render_profit_block(values):
    sales = max(int(values["sales_total"]), 0)
    if not sales:
        ui.label("売上を入力すると表示されます").classes("text-xs text-grey-6 q-pa-md")
        return
    cost = max(int(values["cost_total"]), 0)
    gross = max(int(values["gross_profit"]), 0)
    gross_base = max(gross, 1)
    other = max(int(values["operating_expenses"]) - int(values["personnel"]), 0)
    breakdown = (
        ("人件費", int(values["personnel"]), "#4A9FD0"),
        ("その他営業経費", other, "#909A95"),
        ("営業利益" if values["operating_profit"] >= 0 else "営業損失",
         abs(int(values["operating_profit"])), "#4B77B7" if values["operating_profit"] >= 0 else "#C85C57"),
    )

    def block(title, value, color, note="", classes=""):
        with ui.element("div").classes(f"report-money-box {classes}").style(f"background:{color}"):
            ui.label(title).classes("report-block-title")
            ui.label(f"¥{value:,}").classes("report-block-value")
            if note:
                ui.label(note).classes("report-block-note")

    cost_share = max(cost / sales, .02)
    gross_share = max(gross / sales, .02)
    with ui.element("div").classes("report-block-map").style(
        f"grid-template-rows:{cost_share}fr {gross_share}fr"):
        block("売上", sales, "#355F4C", "100%", "report-sales")
        block("仕入れ・原価", cost, "#82988D", f"原価率 {cost / sales * 100:.1f}%", "report-cost")
        block("粗利", int(values["gross_profit"]), "#4F8C70",
              f"粗利率 {values['gross_profit'] / sales * 100:.1f}%", "report-gross")
        with ui.element("div").classes("report-breakdown"):
            for title, value, color in breakdown:
                with ui.element("div").classes("report-money-box").style(
                    f"background:{color};flex:{max(value / gross_base, .02)}"):
                    ui.label(title).classes("report-block-title")
                    ui.label(f"¥{value:,}").classes("report-block-value")


REPORT_CSS = """
.report-date-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.report-links{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px}.report-link-card{min-width:0;border-radius:14px!important;box-shadow:none!important;background:#F5F7F5!important}.print-report{padding:24px;border-radius:24px;background:#fff;border:1px solid #E3E6E2}.report-title{font-size:24px;font-weight:950;color:#173B2E}.report-period{font-size:11px;color:#6C7771;margin-top:4px}.report-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.report-metric{min-width:0;padding:11px 9px;border-radius:13px;background:#F1F4F2}.report-metric.sales{background:#E8F2EC}.report-metric.cost{background:#FFF0E9}.report-metric.gross{background:#EAF3FF}.report-metric.personnel{background:#EAF4FB}.report-metric.profit{background:#E8F0FB}.report-metric-label{font-size:8px;font-weight:850;color:#647069}.report-metric-value{font-size:clamp(11px,3vw,17px);font-weight:950;white-space:nowrap;letter-spacing:-.05em}.report-section-title{margin-top:24px;margin-bottom:8px;font-size:17px;font-weight:950}.ratio-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px}.ratio-card{padding:9px;border-radius:11px;background:#F3F6F4;font-size:8px;font-weight:850;color:#647069}.ratio-value{font-size:15px;font-weight:950;color:#1D3C30;margin-top:2px}.report-block-map{height:280px;display:grid;grid-template-columns:1fr 1fr 1fr;overflow:hidden;background:#E8ECE9}.report-money-box{min-height:9px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:#fff;overflow:hidden;padding:3px;box-sizing:border-box}.report-sales{grid-column:1;grid-row:1/3}.report-cost{grid-column:2/4;grid-row:1}.report-gross{grid-column:2;grid-row:2}.report-breakdown{grid-column:3;grid-row:2;min-height:0;display:flex;flex-direction:column;overflow:hidden}.report-block-title{font-size:9px;font-weight:900;line-height:1.1}.report-block-value{font-size:11px;font-weight:950;line-height:1.15;margin-top:2px;white-space:nowrap}.report-block-note{font-size:7px;opacity:.9;margin-top:2px}.report-table-wrap{width:100%;overflow-x:auto}.report-table{width:100%;border-collapse:collapse;font-size:9px}.compact-table{max-width:450px}.report-table th,.report-table td{padding:8px 7px;border:1px solid #DDE2DE;text-align:right;white-space:nowrap}.report-table th{background:#EDF2EF;color:#43554C;font-weight:900}.report-table th:first-child,.report-table td:first-child{text-align:left}.report-table td:last-child{font-weight:900}.total-row td{background:#DDEAE2!important;border-top:2px solid #597566!important;font-weight:950!important}
@media(max-width:520px){.report-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.ratio-grid,.report-links{grid-template-columns:repeat(2,minmax(0,1fr))}.report-metric-value{font-size:16px}.print-report{padding:15px}.report-date-grid{grid-template-columns:1fr}.report-block-map{height:250px}}
@media print{@page{size:A4 portrait;margin:10mm}body{background:#fff!important}.report-controls,.q-header,.q-drawer,.q-btn{display:none!important}.app-shell{width:100%!important;max-width:none!important;padding:0!important}.app-shell>div:first-child,.app-shell>div:nth-child(2),.app-shell>div:nth-child(3){display:none!important}.print-report{border:0!important;padding:0!important}.report-table-wrap{overflow:visible}.report-table{font-size:7pt}.report-table tr{break-inside:avoid}.report-section-title{break-after:avoid}.report-block-map,.ratio-grid,.report-metrics{break-inside:avoid}.report-block-map{height:68mm}}
"""

MANAGEMENT_REPORT_CSS = """
.management-report{max-width:920px;margin:0 auto}.management-lead{margin-top:12px;padding:11px 13px;border-radius:12px;background:#F3F6F4;color:#526159;font-size:11px;font-weight:700}.consulting-verdict{margin-top:16px;padding:16px;border-radius:16px;background:#EAF2ED;color:#173B2E}.consulting-verdict.danger,.consulting-verdict.critical{background:#FBE9E7;color:#8C2520}.management-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-top:16px}.management-metrics.three{grid-template-columns:repeat(3,minmax(0,1fr))}.management-metric{min-width:0;padding:12px;border-radius:14px;background:#F1F4F2}.management-metric.good{background:#E7F3EA}.management-metric.danger{background:#FCE9E7}.management-metric.primary{background:#173B2E;color:white}.management-metric-label{font-size:8px;font-weight:850;opacity:.72}.management-metric-value{font-size:clamp(13px,2.6vw,20px);font-weight:950;white-space:nowrap;letter-spacing:-.04em}.action-list{display:grid;gap:9px}.action-card{position:relative;padding:14px;border-radius:14px;border:1px solid #DFE5E1;background:#fff}.action-rank{position:absolute;right:10px;top:10px;color:#A06B11;font-size:9px;font-weight:950}.action-title{padding-right:54px;font-size:15px;font-weight:950;color:#173B2E}.action-reason{font-size:10px;color:#68736D;margin-top:4px}.action-next{margin-top:9px;padding:9px;border-radius:10px;background:#EEF4F0;font-size:10px}.action-next-label{font-size:8px;font-weight:950;color:#2E6B52}.action-target{font-size:9px;font-weight:800;color:#7A5A17;margin-top:7px}.knowledge-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.knowledge-card{padding:12px;border-radius:13px;background:#EAF3ED}.knowledge-card.unknown{background:#FFF3DE}.next-input{margin-top:10px;padding:11px;border-radius:11px;background:#173B2E;color:white;font-size:11px;font-weight:850}.analysis-message{padding:8px 10px;margin-bottom:6px;border-left:4px solid #C98A28;background:#FFF7E8;font-size:10px}.attendance-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.attendance-card{padding:12px;border-radius:13px;background:#F2F5F3}
@media(max-width:520px){.management-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.management-metrics.three{grid-template-columns:1fr}.knowledge-grid{grid-template-columns:1fr}.attendance-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media print{.management-report{max-width:none}.action-card,.management-metric,.knowledge-card,.attendance-card{break-inside:avoid}.management-lead{background:#F3F6F4!important}.management-metric.primary{background:#173B2E!important;color:#fff!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""
