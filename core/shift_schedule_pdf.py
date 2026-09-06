"""Printable PDF for an automatically generated half-month shift draft."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def create_shift_schedule_pdf(path, result, staff_names):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    font_path = Path(__file__).resolve().parent.parent / "static" / "NotoSansJP-Variable.ttf"
    if "ShiftJapanese" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ShiftJapanese", str(font_path)))

    period = result["period"]
    normal = ParagraphStyle("shift-normal", fontName="ShiftJapanese", fontSize=6.5,
                            leading=8, alignment=1, textColor=colors.HexColor("#17231E"))
    title = ParagraphStyle("shift-title", parent=normal, fontSize=15, leading=19,
                           textColor=colors.HexColor("#173D30"))
    subtitle = ParagraphStyle("shift-subtitle", parent=normal, fontSize=8, leading=10)
    rows = [[Paragraph("日付", normal), *[Paragraph(name, normal) for name in staff_names],
             Paragraph("不足", normal), Paragraph("実人数", normal)]]
    cut_cells = []
    fixed_cells = []
    lunch_totals = {name: 0 for name in staff_names}
    dinner_totals = {name: 0 for name in staff_names}
    manual = result.get("settings", {}).get("manual_overrides", {})

    for row_index, day in enumerate(range(period["start"], period["end"] + 1), start=1):
        value = result["days"][str(day)]
        row = [Paragraph(str(day), normal)]
        for column_index, name in enumerate(staff_names, start=1):
            plan = value["staff"][name]
            lunch_totals[name] += int(bool(plan["lunch"]))
            dinner_totals[name] += int(bool(plan["dinner"]))
            if plan["lunch"] and plan["dinner"]:
                label = "通し"
            elif plan["lunch"]:
                label = "L"
            elif plan["dinner"]:
                label = "D"
            else:
                label = "休"
            if plan.get("cut_meals"):
                label += "<br/>" + "/".join(plan["cut_meals"]) + "希望削減"
                cut_cells.append((column_index, row_index))
            if name in manual.get(str(day), {}):
                label = "● " + label
                fixed_cells.append((column_index, row_index))
            row.append(Paragraph(label, normal))
        shortage = value["shortages"]
        row.append(Paragraph(f'L {shortage["lunch"]} / D {shortage["dinner"]}', normal))
        lunch_count = sum(int(plan["lunch"]) for plan in value["staff"].values())
        dinner_count = sum(int(plan["dinner"]) for plan in value["staff"].values())
        row.append(Paragraph(f"L {lunch_count} / D {dinner_count}", normal))
        rows.append(row)

    rows.append([Paragraph("出勤数", normal),
                 *[Paragraph(f'L {lunch_totals[name]}<br/>D {dinner_totals[name]}', normal)
                   for name in staff_names],
                 Paragraph("—", normal), Paragraph("—", normal)])
    page_width, _ = landscape(A4)
    usable_width = page_width - 14 * mm
    first_width = 12 * mm
    summary_width = 19 * mm
    staff_width = (usable_width - first_width - summary_width * 2) / len(staff_names)
    table = Table(rows, colWidths=[first_width] + [staff_width] * len(staff_names)
                  + [summary_width, summary_width], repeatRows=1)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "ShiftJapanese"),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#C9D4CE")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243E34")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8F2EC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])
    for column, row in cut_cells:
        style.add("BACKGROUND", (column, row), (column, row), colors.HexColor("#FFE2E2"))
        style.add("TEXTCOLOR", (column, row), (column, row), colors.HexColor("#9D3535"))
    for column, row in fixed_cells:
        style.add("BOX", (column, row), (column, row), 1.2, colors.HexColor("#D79B16"))
    table.setStyle(style)

    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4),
                            leftMargin=7 * mm, rightMargin=7 * mm,
                            topMargin=7 * mm, bottomMargin=7 * mm,
                            title="自動作成シフト案")
    label = f'{period["year"]}年{period["month"]}月 {period["start"]}〜{period["end"]}日'
    doc.build([Paragraph("自動作成シフト案", title), Paragraph(label, subtitle),
               Spacer(1, 3 * mm), table])
    return path
