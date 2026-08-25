"""Create a downloadable Japanese PDF for the selected financial-report period."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


PAYMENT_COLUMNS = (
    ("現金", "cash_sales"), ("クレジット", "credit_sales"),
    ("PayPay", "paypay_sales"), ("電子マネー", "electronic_money_sales"),
    ("旅行社", "travel_agency_sales"), ("ポイント", "tabelog_points_sales"),
    ("ポイント(その他)", "hotpepper_points_sales"),
)


def create_financial_report_pdf(path, start, end, summary, suppliers, sales_records,
                                payment_fees=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    font_path = Path(__file__).resolve().parent.parent / "static" / "NotoSansJP-Variable.ttf"
    if "ReportJapanese" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ReportJapanese", str(font_path)))
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "jp-title", parent=styles["Title"], fontName="ReportJapanese",
        fontSize=20, leading=25, textColor=colors.HexColor("#173B2E"),
    )
    heading = ParagraphStyle(
        "jp-heading", parent=styles["Heading2"], fontName="ReportJapanese",
        fontSize=12, leading=16, spaceBefore=8, spaceAfter=6,
        textColor=colors.HexColor("#234D3C"),
    )
    normal = ParagraphStyle(
        "jp-normal", parent=styles["BodyText"], fontName="ReportJapanese",
        fontSize=8, leading=11,
    )
    right = ParagraphStyle("jp-right", parent=normal, alignment=TA_RIGHT)
    center = ParagraphStyle("jp-center", parent=normal, alignment=TA_CENTER)

    doc = SimpleDocTemplate(
        str(path), pagesize=landscape(A4), rightMargin=12 * mm,
        leftMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
        title="未来決算 期間集計レポート",
    )
    story = [
        Paragraph("未来決算　期間集計レポート", title),
        Paragraph(f"集計期間　{start.replace('-', '/')} 〜 {end.replace('-', '/')}", normal),
        Spacer(1, 5 * mm),
    ]

    summary_rows = [[Paragraph(label, center), Paragraph(f"¥{int(value):,}", right)]
                    for label, value in summary]
    summary_table = Table(summary_rows, colWidths=[34 * mm, 40 * mm], hAlign="LEFT")
    summary_table.setStyle(_table_style(header=False, accent="#E8F2EC"))
    story.extend([summary_table, Spacer(1, 5 * mm), Paragraph("決済方法別集計", heading)])

    payment_totals = {field: sum(int(row.get(field, 0) or 0) for row in sales_records)
                      for _, field in PAYMENT_COLUMNS}
    payment_rows = [[Paragraph("決済方法", center), Paragraph("売上", center),
                     Paragraph("手数料見込", center)]]
    fee_map = payment_fees or {}
    for label, field in PAYMENT_COLUMNS:
        payment_rows.append([
            Paragraph(label, normal), Paragraph(f"¥{payment_totals[field]:,}", right),
            Paragraph(f"¥{int(fee_map.get(field, 0) or 0):,}", right),
        ])
    payment_table = Table(payment_rows, colWidths=[45 * mm, 38 * mm, 38 * mm], hAlign="LEFT")
    payment_table.setStyle(_table_style())
    story.extend([payment_table, Spacer(1, 5 * mm), Paragraph("仕入れ先別集計", heading)])

    supplier_rows = [[Paragraph(value, center) for value in
                      ("仕入れ先", "件数", "原価", "営業用品", "一般経費", "合計")]]
    if suppliers:
        for supplier, values in suppliers:
            supplier_rows.append([
                Paragraph(str(supplier), normal), Paragraph(f"{values['count']}件", right),
                Paragraph(f"¥{values['cost']:,}", right),
                Paragraph(f"¥{values['supply']:,}", right),
                Paragraph(f"¥{values['expense']:,}", right),
                Paragraph(f"¥{values['total']:,}", right),
            ])
    else:
        supplier_rows.append([Paragraph("この期間の記録はありません", normal), "", "", "", "", ""])
    supplier_table = Table(
        supplier_rows, colWidths=[60 * mm, 20 * mm, 33 * mm, 33 * mm, 33 * mm, 35 * mm],
        repeatRows=1,
    )
    supplier_table.setStyle(_table_style())
    story.extend([supplier_table, PageBreak(), Paragraph("日別・決済方法別売上", heading)])

    daily_headers = ["日付", "ランチ", "ディナー", *[label for label, _ in PAYMENT_COLUMNS], "合計"]
    daily_rows = [[Paragraph(value, center) for value in daily_headers]]
    for row in sorted(sales_records, key=lambda value: str(value.get("date", ""))):
        values = [
            str(row.get("date", "")).replace("-", "/"),
            f"¥{int(row.get('lunch_sales', 0) or 0):,}",
            f"¥{int(row.get('dinner_sales', 0) or 0):,}",
            *[f"¥{int(row.get(field, 0) or 0):,}" for _, field in PAYMENT_COLUMNS],
            f"¥{int(row.get('amount', 0) or 0):,}",
        ]
        daily_rows.append([Paragraph(values[0], normal), *[Paragraph(v, right) for v in values[1:]]])
    if len(daily_rows) == 1:
        daily_rows.append([Paragraph("この期間の売上記録はありません", normal),
                           *["" for _ in daily_headers[1:]]])
    widths = [23 * mm, 24 * mm, 24 * mm, *[21 * mm for _ in PAYMENT_COLUMNS], 26 * mm]
    daily_table = Table(daily_rows, colWidths=widths, repeatRows=1)
    daily_table.setStyle(_table_style())
    story.append(daily_table)

    def page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("ReportJapanese", 7)
        canvas.setFillColor(colors.HexColor("#68766F"))
        canvas.drawRightString(landscape(A4)[0] - 12 * mm, 6 * mm,
                               f"{document.page}ページ")
        canvas.restoreState()

    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
    return path


def _table_style(header=True, accent="#EDF2EF"):
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), "ReportJapanese"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#CBD5CF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(accent)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#334B40")),
        ])
    else:
        commands.append(("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(accent)))
    return TableStyle(commands)
