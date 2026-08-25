from datetime import date
from pathlib import Path

from nicegui import ui

from core.auth import require_app_access, require_permission
from core.clock import today_jst
from core.financial_report_data import PAYMENT_COLUMNS, build_financial_report
from core.financial_report_pdf import create_financial_report_pdf
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
                with ui.element("div").classes("profit-flow"):
                    for label, value, style in (
                        ("売上", values["sales_total"], "sales"), ("原価", -values["cost_total"], "cost"),
                        ("粗利", values["gross_profit"], "gross"), ("人件費", -values["personnel"], "personnel"),
                        ("その他営業経費", -(values["operating_expenses"] - values["personnel"]), "expense"),
                        ("営業利益", values["operating_profit"], "profit"),
                    ):
                        with ui.element("div").classes(f"profit-step {style}"):
                            ui.label(label); ui.label(f"¥{value:,}").classes("profit-value")

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


def money(value):
    return f"¥{int(value):,}"


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


REPORT_CSS = """
.report-date-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.print-report{padding:24px;border-radius:24px;background:#fff;border:1px solid #E3E6E2}.report-title{font-size:24px;font-weight:950;color:#173B2E}.report-period{font-size:11px;color:#6C7771;margin-top:4px}.report-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.report-metric{min-width:0;padding:11px 9px;border-radius:13px;background:#F1F4F2}.report-metric.sales{background:#E8F2EC}.report-metric.cost{background:#FFF0E9}.report-metric.gross{background:#EAF3FF}.report-metric.personnel{background:#EAF4FB}.report-metric.profit{background:#E8F0FB}.report-metric-label{font-size:8px;font-weight:850;color:#647069}.report-metric-value{font-size:clamp(11px,3vw,17px);font-weight:950;white-space:nowrap;letter-spacing:-.05em}.report-section-title{margin-top:24px;margin-bottom:8px;font-size:17px;font-weight:950}.ratio-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px}.ratio-card{padding:9px;border-radius:11px;background:#F3F6F4;font-size:8px;font-weight:850;color:#647069}.ratio-value{font-size:15px;font-weight:950;color:#1D3C30;margin-top:2px}.profit-flow{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:4px}.profit-step{padding:10px 6px;border-radius:10px;color:#fff;background:#557666;font-size:8px;font-weight:850}.profit-step.cost{background:#879A90}.profit-step.gross{background:#4F8C70}.profit-step.personnel{background:#4A9FD0}.profit-step.expense{background:#8E9792}.profit-step.profit{background:#4B77B7}.profit-value{font-size:11px;font-weight:950;white-space:nowrap}.report-table-wrap{width:100%;overflow-x:auto}.report-table{width:100%;border-collapse:collapse;font-size:9px}.compact-table{max-width:450px}.report-table th,.report-table td{padding:8px 7px;border:1px solid #DDE2DE;text-align:right;white-space:nowrap}.report-table th{background:#EDF2EF;color:#43554C;font-weight:900}.report-table th:first-child,.report-table td:first-child{text-align:left}.report-table td:last-child{font-weight:900}.total-row td{background:#DDEAE2!important;border-top:2px solid #597566!important;font-weight:950!important}
@media(max-width:520px){.report-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.ratio-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.profit-flow{grid-template-columns:repeat(2,minmax(0,1fr))}.report-metric-value{font-size:16px}.print-report{padding:15px}.report-date-grid{grid-template-columns:1fr}}
@media print{@page{size:A4 portrait;margin:10mm}body{background:#fff!important}.report-controls,.q-header,.q-drawer,.q-btn{display:none!important}.app-shell{width:100%!important;max-width:none!important;padding:0!important}.app-shell>div:first-child,.app-shell>div:nth-child(2),.app-shell>div:nth-child(3){display:none!important}.print-report{border:0!important;padding:0!important}.report-table-wrap{overflow:visible}.report-table{font-size:7pt}.report-table tr{break-inside:avoid}.report-section-title{break-after:avoid}.profit-flow,.ratio-grid,.report-metrics{break-inside:avoid}}
"""
