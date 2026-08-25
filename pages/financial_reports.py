from collections import defaultdict
from datetime import date

from nicegui import ui

from core.auth import require_app_access, require_permission
from core.clock import today_jst
from core.financials import financials
from core.purchases import purchases
from core.theme import Theme


def _inside(value, start, end):
    return start <= str(value or "") <= end


@ui.page("/mirai-kessan/reports")
def financial_reports_page():
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("集計・印刷｜未来決算", app_name="mirai-kessan")
    today = today_jst()
    start_default = today.replace(day=1).isoformat()
    end_default = today.isoformat()
    content = Theme.shell(
        "集計・印刷", "期間を選び、A4印刷またはPDFで保存",
        back_to="/mirai-kessan/dashboard",
    )
    with content:
        with ui.card().classes("surface-card report-controls w-full q-pa-lg q-mb-md"):
            with ui.element("div").classes("report-date-grid w-full"):
                start_date = ui.input("開始日", value=start_default).props(
                    "type=date outlined")
                end_date = ui.input("終了日", value=end_default).props(
                    "type=date outlined")

            def update_report():
                try:
                    start = date.fromisoformat(str(start_date.value))
                    end = date.fromisoformat(str(end_date.value))
                except ValueError:
                    ui.notify("日付を正しく入力してください", type="negative")
                    return
                if start > end:
                    ui.notify("開始日は終了日以前にしてください", type="negative")
                    return
                report.refresh()

            with ui.row().classes("w-full gap-2 q-mt-md"):
                ui.button("集計する", icon="calculate", on_click=update_report).props(
                    "unelevated no-caps").classes("grow")
                ui.button("印刷・PDF", icon="print", on_click=lambda: ui.run_javascript(
                    "window.print()"  # nosec: fixed browser action
                )).props("outline no-caps").classes("grow")

        @ui.refreshable
        def report():
            start = str(start_date.value)
            end = str(end_date.value)
            sales_records = [item for item in financials.sales_records()
                             if _inside(item.get("date"), start, end)]
            purchase_records = [item for item in purchases.records()
                                if _inside(item.get("date"), start, end)]
            sales_total = sum(int(item.get("amount", 0) or 0) for item in sales_records)
            cost_total = sum(int(item.get("total", 0) or 0) for item in purchase_records
                             if item.get("kind", "cost") == "cost")
            supply_total = sum(int(item.get("total", 0) or 0) for item in purchase_records
                               if item.get("kind") == "operating_supply")
            expense_total = sum(int(item.get("total", 0) or 0) for item in purchase_records
                                if item.get("kind") == "expense")
            gross_profit = sales_total - cost_total
            supplier_values = defaultdict(lambda: {
                "count": 0, "cost": 0, "supply": 0, "expense": 0, "total": 0})
            for item in purchase_records:
                value = int(item.get("total", 0) or 0)
                supplier = str(item.get("supplier") or "仕入れ先未入力")
                row = supplier_values[supplier]
                row["count"] += 1
                row["total"] += value
                kind = item.get("kind", "cost")
                row[{"cost": "cost", "operating_supply": "supply",
                     "expense": "expense"}.get(kind, "expense")] += value

            with ui.element("section").classes("print-report w-full"):
                ui.label("未来決算　期間集計レポート").classes("report-title")
                ui.label(f"集計期間　{start.replace('-', '/')} 〜 {end.replace('-', '/')}").classes(
                    "report-period")
                with ui.element("div").classes("report-metrics w-full q-mt-md"):
                    for title, value, style in (
                        ("売上", sales_total, "sales"), ("原価", cost_total, "cost"),
                        ("粗利", gross_profit, "gross"),
                        ("営業用消耗品", supply_total, "supply"),
                        ("一般経費", expense_total, "expense"),
                    ):
                        with ui.element("div").classes(f"report-metric {style}"):
                            ui.label(title).classes("report-metric-label")
                            ui.label(f"¥{value:,}").classes("report-metric-value")
                with ui.row().classes("w-full gap-3 q-mt-sm"):
                    ui.label(f"売上入力日数　{len(sales_records)}日").classes("report-note")
                    ui.label(f"仕入れ明細　{len(purchase_records)}件").classes("report-note")

                ui.label("仕入れ先別集計").classes("report-section-title")
                with ui.element("div").classes("report-table-wrap"):
                    with ui.element("table").classes("report-table"):
                        with ui.element("thead"), ui.element("tr"):
                            for title in ("仕入れ先", "件数", "原価", "営業用品", "一般経費", "合計"):
                                with ui.element("th"):
                                    ui.label(title)
                        with ui.element("tbody"):
                            if not supplier_values:
                                with ui.element("tr"), ui.element("td").props("colspan=6"):
                                    ui.label("この期間の仕入れ記録はありません")
                            for supplier, values in sorted(
                                    supplier_values.items(), key=lambda pair: pair[1]["total"],
                                    reverse=True):
                                with ui.element("tr"):
                                    for text in (
                                        supplier, f"{values['count']}件", f"¥{values['cost']:,}",
                                        f"¥{values['supply']:,}", f"¥{values['expense']:,}",
                                        f"¥{values['total']:,}",
                                    ):
                                        with ui.element("td"):
                                            ui.label(text)

                ui.label("日別売上明細").classes("report-section-title")
                with ui.element("div").classes("report-table-wrap"):
                    with ui.element("table").classes("report-table"):
                        with ui.element("thead"), ui.element("tr"):
                            for title in ("日付", "ランチ", "ディナー", "売上合計"):
                                with ui.element("th"):
                                    ui.label(title)
                        with ui.element("tbody"):
                            if not sales_records:
                                with ui.element("tr"), ui.element("td").props("colspan=4"):
                                    ui.label("この期間の売上記録はありません")
                            for item in sorted(sales_records, key=lambda row: str(row.get("date"))):
                                with ui.element("tr"):
                                    for text in (
                                        str(item.get("date", "")).replace("-", "/"),
                                        f"¥{int(item.get('lunch_sales', 0) or 0):,}",
                                        f"¥{int(item.get('dinner_sales', 0) or 0):,}",
                                        f"¥{int(item.get('amount', 0) or 0):,}",
                                    ):
                                        with ui.element("td"):
                                            ui.label(text)

                ui.label("仕入れ明細").classes("report-section-title")
                with ui.element("div").classes("report-table-wrap"):
                    with ui.element("table").classes("report-table"):
                        with ui.element("thead"), ui.element("tr"):
                            for title in ("日付", "仕入れ先", "区分", "金額"):
                                with ui.element("th"):
                                    ui.label(title)
                        with ui.element("tbody"):
                            if not purchase_records:
                                with ui.element("tr"), ui.element("td").props("colspan=4"):
                                    ui.label("この期間の仕入れ記録はありません")
                            kind_labels = {
                                "cost": "原価", "operating_supply": "営業用消耗品",
                                "expense": "一般経費",
                            }
                            for item in sorted(purchase_records, key=lambda row: str(row.get("date"))):
                                with ui.element("tr"):
                                    for text in (
                                        str(item.get("date", "")).replace("-", "/"),
                                        str(item.get("supplier") or "仕入れ先未入力"),
                                        kind_labels.get(item.get("kind", "cost"), "一般経費"),
                                        f"¥{int(item.get('total', 0) or 0):,}",
                                    ):
                                        with ui.element("td"):
                                            ui.label(text)

        report()
        ui.add_css("""
        .report-date-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.print-report{padding:24px;border-radius:24px;background:#fff;border:1px solid #E3E6E2}.report-title{font-size:24px;font-weight:950;color:#173B2E}.report-period{font-size:11px;color:#6C7771;margin-top:4px}.report-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:7px}.report-metric{min-width:0;padding:11px 9px;border-radius:13px;background:#F1F4F2}.report-metric.sales{background:#E8F2EC}.report-metric.cost{background:#FFF0E9}.report-metric.gross{background:#EAF3FF}.report-metric-label{font-size:8px;font-weight:850;color:#647069}.report-metric-value{font-size:clamp(11px,3vw,17px);font-weight:950;white-space:nowrap;letter-spacing:-.05em}.report-note{font-size:9px;color:#67736C}.report-section-title{margin-top:25px;margin-bottom:8px;font-size:17px;font-weight:950}.report-table-wrap{width:100%;overflow-x:auto}.report-table{width:100%;border-collapse:collapse;font-size:9px}.report-table th,.report-table td{padding:8px 7px;border:1px solid #DDE2DE;text-align:right;white-space:nowrap}.report-table th{background:#EDF2EF;color:#43554C;font-weight:900}.report-table th:first-child,.report-table td:first-child{text-align:left}.report-table td:last-child{font-weight:900}
        @media(max-width:520px){.report-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.report-metric-value{font-size:16px}.print-report{padding:15px}.report-date-grid{grid-template-columns:1fr}}
        @media print{@page{size:A4 portrait;margin:12mm}body{background:#fff!important}.report-controls,.q-header,.q-drawer,.q-btn{display:none!important}.app-shell{width:100%!important;max-width:none!important;padding:0!important}.app-shell>div:first-child,.app-shell>div:nth-child(2),.app-shell>div:nth-child(3){display:none!important}.print-report{border:0!important;padding:0!important}.report-metrics{grid-template-columns:repeat(5,minmax(0,1fr))}.report-table-wrap{overflow:visible}.report-table{font-size:8pt}.report-table tr{break-inside:avoid}}
        """)
