"""Create the downloadable counterpart of the on-screen financial report."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.financial_report_data import PAYMENT_COLUMNS


def create_financial_report_pdf(path, report):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    font_path = Path(__file__).resolve().parent.parent / "static" / "NotoSansJP-Variable.ttf"
    if "ReportJapanese" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ReportJapanese", str(font_path)))
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Title"], fontName="ReportJapanese",
                           fontSize=20, leading=25, textColor=colors.HexColor("#173B2E"))
    heading = ParagraphStyle("heading", parent=styles["Heading2"], fontName="ReportJapanese",
                             fontSize=14, leading=18, spaceBefore=9, spaceAfter=7,
                             textColor=colors.HexColor("#102B21"))
    normal = ParagraphStyle("normal-jp", parent=styles["BodyText"], fontName="ReportJapanese",
                            fontSize=8.5, leading=11, textColor=colors.HexColor("#111111"))
    right = ParagraphStyle("right-jp", parent=normal, alignment=TA_RIGHT)
    center = ParagraphStyle("center-jp", parent=normal, alignment=TA_CENTER)
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=11 * mm, leftMargin=11 * mm,
                            topMargin=11 * mm, bottomMargin=11 * mm,
                            title="未来決算 期間集計レポート")
    story = [Paragraph("未来決算　期間集計レポート", title),
             Paragraph(f"集計期間　{report['start'].replace('-', '/')} 〜 {report['end'].replace('-', '/')}", normal),
             Spacer(1, 4 * mm)]

    summary = [("売上", report["sales_total"]), ("原価", report["cost_total"]),
               ("粗利", report["gross_profit"]), ("人件費", report["personnel"]),
               ("営業経費", report["operating_expenses"]),
               ("営業利益" if report["operating_profit"] >= 0 else "営業損失", report["operating_profit"])]
    summary_table = Table([
        sum(([Paragraph(label, center), Paragraph(f"¥{value:,}", right)]
             for label, value in summary[:3]), []),
        sum(([Paragraph(label, center), Paragraph(f"¥{value:,}", right)]
             for label, value in summary[3:]), []),
    ], colWidths=[25 * mm, 34 * mm] * 3)
    summary_table.setStyle(_table_style(header=False, accent="#E8F2EC"))
    story.extend([summary_table, Spacer(1, 4 * mm), Paragraph("重要な経営比率", heading)])
    ratio_labels = (("原価率", "cost_rate"), ("粗利率", "gross_margin"),
                    ("人件費率", "personnel_rate"), ("労働分配率", "labor_distribution"),
                    ("営業利益率", "operating_margin"))
    ratio_row = []
    for label, key in ratio_labels:
        value = report["ratios"][key]
        ratio_row.extend([Paragraph(label, center), Paragraph("—" if value is None else f"{value * 100:.1f}%", right)])
    ratio_table = Table([ratio_row], colWidths=[20 * mm, 17 * mm] * len(ratio_labels))
    ratio_table.setStyle(_table_style(header=False, accent="#F1F4F2"))
    story.extend([ratio_table, Spacer(1, 4 * mm), Paragraph("利益ブロック", heading)])
    profit_table = _profit_block(report, normal, center)
    expense_rows = [[Paragraph("項目", center), Paragraph("期間配賦額", center)]]
    for label, value in report["expense_breakdown"]:
        expense_rows.append([Paragraph(label, normal), Paragraph(f"¥{value:,}", right)])
    expense_rows.append([Paragraph("営業経費合計", normal),
                         Paragraph(f"¥{report['operating_expenses']:,}", right)])
    expense_table = Table(expense_rows, colWidths=[58 * mm, 42 * mm], hAlign="LEFT", repeatRows=1)
    expense_table.setStyle(_table_style(total_row=True))
    story.extend([profit_table, Spacer(1, 4 * mm), Paragraph("営業経費の内訳", heading),
                  expense_table, Spacer(1, 4 * mm), Paragraph("決済方法別集計", heading)])

    payment_rows = [[Paragraph("決済方法", center), Paragraph("期間合計", center)]]
    for label, field in (*PAYMENT_COLUMNS, ("ポイント", "points_sales"), ("未分類", "unclassified_sales")):
        payment_rows.append([Paragraph(label, normal), Paragraph(f"¥{report['payment_totals'][field]:,}", right)])
    payment_rows.append([Paragraph("決済内訳合計", normal),
                         Paragraph(f"¥{sum(report['payment_totals'].values()):,}", right)])
    payment_table = Table(payment_rows, colWidths=[65 * mm, 50 * mm], repeatRows=1, hAlign="LEFT")
    payment_table.setStyle(_table_style(total_row=True))
    story.extend([payment_table, Spacer(1, 4 * mm), Paragraph("仕入れ先別集計", heading)])
    supplier_rows = [[Paragraph(value, center) for value in
                      ("仕入れ先", "件数", "原価", "営業用品", "一般経費", "合計")]]
    for supplier, values in report["suppliers"]:
        supplier_rows.append([Paragraph(str(supplier), normal), Paragraph(f"{values['count']}件", right),
                              Paragraph(f"¥{values['cost']:,}", right), Paragraph(f"¥{values['supply']:,}", right),
                              Paragraph(f"¥{values['expense']:,}", right), Paragraph(f"¥{values['total']:,}", right)])
    supplier_rows.append([Paragraph("合計", normal), Paragraph(f"{len(report['purchases'])}件", right),
                          Paragraph(f"¥{report['cost_total']:,}", right), Paragraph(f"¥{report['supply_total']:,}", right),
                          Paragraph(f"¥{report['expense_total']:,}", right),
                          Paragraph(f"¥{report['cost_total'] + report['supply_total'] + report['expense_total']:,}", right)])
    supplier_table = Table(supplier_rows, colWidths=[46 * mm, 17 * mm, 28 * mm, 28 * mm, 28 * mm, 31 * mm], repeatRows=1)
    supplier_table.setStyle(_table_style(total_row=True))
    story.extend([supplier_table, Spacer(1, 4 * mm), Paragraph("日別売上明細", heading)])
    headers = ["日付", "ランチ", "ディナー", *[label for label, _ in PAYMENT_COLUMNS], "ポイント", "売上合計"]
    daily_rows = [[Paragraph(value, center) for value in headers]]
    daily_totals = [0] * (len(headers) - 1)
    for row in sorted(report["sales"], key=lambda value: str(value.get("date", ""))):
        numbers = [int(row.get("lunch_sales", 0) or 0), int(row.get("dinner_sales", 0) or 0),
                   *[int(row.get(field, 0) or 0) for _, field in PAYMENT_COLUMNS],
                   int(row.get("tabelog_points_sales", 0) or 0) + int(row.get("hotpepper_points_sales", 0) or 0),
                   int(row.get("amount", 0) or 0)]
        daily_totals = [a + b for a, b in zip(daily_totals, numbers)]
        daily_rows.append([Paragraph(str(row.get("date", "")).replace("-", "/"), normal),
                           *[Paragraph(f"¥{value:,}", right) for value in numbers]])
    daily_rows.append([Paragraph("合計", normal), *[Paragraph(f"¥{value:,}", right) for value in daily_totals]])
    widths = [19 * mm, 19 * mm, 19 * mm, *[18 * mm for _ in PAYMENT_COLUMNS], 18 * mm, 22 * mm]
    daily_table = Table(daily_rows, colWidths=widths, repeatRows=1)
    daily_table.setStyle(_table_style(total_row=True)); story.append(daily_table)

    def page_number(canvas, document):
        canvas.saveState(); canvas.setFont("ReportJapanese", 8); canvas.setFillColor(colors.HexColor("#222222"))
        canvas.drawRightString(A4[0] - 11 * mm, 6 * mm, f"{document.page}ページ"); canvas.restoreState()
    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
    return path


def _profit_block(report, normal, center):
    """Render the same area-based structure used by the provisional dashboard."""
    sales = max(int(report["sales_total"]), 1)
    cost = max(int(report["cost_total"]), 0)
    gross = max(int(report["gross_profit"]), 0)
    total_height = 58 * mm
    cost_height = max(8 * mm, total_height * cost / sales)
    gross_height = max(8 * mm, total_height - cost_height)
    if cost_height + gross_height > total_height:
        scale = total_height / (cost_height + gross_height)
        cost_height *= scale; gross_height *= scale

    tiny = ParagraphStyle("profit-block-tiny", parent=center, fontSize=7.2, leading=8.2)

    def label(text, value, note="", style=None):
        parts = [f"<b>{text}</b>", f"¥{int(value):,}"]
        if note:
            parts.append(f"<font size='6'>{note}</font>")
        return Paragraph("<br/>".join(parts), style or center)

    def percent(key):
        value = report["ratios"].get(key)
        return "—" if value is None else f"{value * 100:.1f}%"

    def compact_label(text, value):
        return Paragraph(f"<b>{text}</b>　¥{int(value):,}", tiny)

    personnel = max(int(report["personnel"]), 0)
    other = max(int(report["operating_expenses"]) - personnel, 0)
    profit = abs(int(report["operating_profit"]))
    pieces = [
        ("人件費", personnel, "#4A9FD0"),
        ("その他営業経費", other, "#909A95"),
        ("営業利益" if report["operating_profit"] >= 0 else "営業損失",
         profit, "#4B77B7" if report["operating_profit"] >= 0 else "#C85C57"),
    ]
    piece_total = max(sum(value for _, value, _ in pieces), 1)
    piece_heights = [max(5 * mm, gross_height * value / piece_total) for _, value, _ in pieces]
    piece_scale = gross_height / sum(piece_heights)
    piece_heights = [height * piece_scale for height in piece_heights]
    breakdown = Table(
        [[compact_label(title, value)] for title, value, _ in pieces],
        colWidths=[58 * mm], rowHeights=piece_heights,
    )
    breakdown.setStyle(TableStyle([
        ("BACKGROUND", (0, index), (0, index), colors.HexColor(color))
        for index, (_, _, color) in enumerate(pieces)
    ] + [("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
         ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
         ("ALIGN", (0, 0), (-1, -1), "CENTER"),
         ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
         ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))

    grid = Table([
        [label("売上", report["sales_total"], "100%"),
         label("仕入れ・原価", report["cost_total"], f"原価率 {percent('cost_rate')}"), ""],
        ["", label("粗利", report["gross_profit"], f"粗利率 {percent('gross_margin')}"), breakdown],
    ], colWidths=[58 * mm] * 3, rowHeights=[cost_height, gross_height])
    grid.setStyle(TableStyle([
        ("SPAN", (0, 0), (0, 1)), ("SPAN", (1, 0), (2, 0)),
        ("BACKGROUND", (0, 0), (0, 1), colors.HexColor("#355F4C")),
        ("BACKGROUND", (1, 0), (2, 0), colors.HexColor("#82988D")),
        ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#4F8C70")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return grid


def _table_style(header=True, accent="#EDF2EF", total_row=False):
    commands = [("FONTNAME", (0, 0), (-1, -1), "ReportJapanese"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.2),
                ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#CBD5CF")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        commands.extend([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(accent)),
                         ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#334B40"))])
    else:
        commands.append(("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(accent)))
    if total_row:
        commands.extend([("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DDEAE2")),
                         ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#597566"))])
    return TableStyle(commands)
