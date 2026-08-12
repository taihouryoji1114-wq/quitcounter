from nicegui import ui

from core.annual_reports import annual_reports
from core.auth import require_login
from core.clock import today_jst
from core.theme import Theme


BS_SECTIONS = (
    ("流動資産", (
        ("cash_on_hand", "現金"), ("checking_deposit", "当座預金"),
        ("ordinary_deposit", "普通預金"), ("receivables", "売掛金"),
        ("merchandise", "商品・棚卸資産"), ("temporary_payment", "仮払金"),
        ("prepaid", "前払費用"), ("substitute_payment", "立替金"),
        ("other_current_assets", "その他流動資産"),
    )),
    ("固定資産", (
        ("building_equipment", "建物附属設備"), ("vehicles", "車両運搬具"),
        ("fixtures", "什器備品"), ("lump_sum_depreciable_assets", "一括償却資産"),
        ("telephone_rights", "電話加入権"), ("investments", "出資金"),
        ("security_deposit", "保証金"), ("lease_deposit", "敷金"),
        ("membership_deposit", "加盟金"),
        ("other_fixed_assets", "その他固定資産"),
    )),
    ("流動負債", (
        ("payables", "買掛金"), ("short_term_loans", "短期借入金"),
        ("unpaid_accounts", "未払金"), ("accrued_expenses", "未払費用"),
        ("deposits_received", "預り金"), ("unpaid_consumption_tax", "未払消費税"),
        ("other_current_liabilities", "その他流動負債"),
    )),
    ("固定負債", (
        ("long_term_loans", "長期借入金"),
        ("other_fixed_liabilities", "その他固定負債"),
    )),
    ("純資産", (
        ("capital", "資本金"), ("profit_reserve", "利益準備金"),
        ("special_reserve", "別途積立金"), ("retained_earnings", "繰越利益剰余金"),
        ("other_equity", "その他純資産"),
    )),
)

PL_SECTIONS = (
    ("売上・原価", (
        ("sales", "売上高"), ("opening_inventory", "期首棚卸高"),
        ("purchases", "仕入高"), ("closing_inventory", "期末棚卸高"),
    )),
    ("人件費", (
        ("executive_compensation", "役員報酬"), ("salaries", "給料手当"),
        ("retirement_allowance", "退職金"), ("statutory_welfare", "法定福利費"),
        ("welfare", "福利厚生費"), ("temporary_wages", "雑給"),
        ("recruitment_fees", "人材採用費"),
    )),
    ("販売費・一般管理費", (
        ("advertising", "広告宣伝費"), ("freight", "運賃"),
        ("utilities", "水道光熱費"), ("fuel", "燃料費"),
        ("office_supplies", "事務用消耗品費"), ("consumables", "消耗品費"),
        ("rent", "家賃"), ("insurance", "支払保険料"),
        ("repairs", "修繕費"), ("taxes_and_dues", "租税公課"),
        ("entertainment", "接待交際費"), ("travel", "旅費交通費"),
        ("communication", "通信費"), ("fees", "支払手数料"),
        ("membership_fees", "諸会費"), ("card_fees", "カード手数料"),
        ("lease", "リース料"), ("depreciation", "減価償却費"),
        ("miscellaneous_expenses", "雑費"), ("other_sga", "その他販売管理費"),
    )),
    ("営業外・税金", (
        ("interest_income", "受取利息"), ("dividend_income", "受取配当金"),
        ("miscellaneous_income", "雑収入"), ("interest_expense", "支払利息・割引料"),
        ("guarantee_amortization", "保証料償却"), ("miscellaneous_loss", "雑損失"),
        ("extraordinary_income", "特別利益"),
        ("fixed_asset_disposal_loss", "固定資産除却損"),
        ("extraordinary_loss", "その他特別損失"),
        ("corporate_taxes", "法人税等"),
    )),
)


def _money(value):
    return f"¥{int(value):,}"


def _ratio(value):
    return "—" if value is None else f"{value * 100:.1f}%"


def _render_analysis(period=None):
    if not require_login():
        return
    Theme.page("決算分析", app_name="mirai-kessan")
    content = Theme.shell(
        "決算分析",
        "決算書の最新数字を入力して、会社の状態と改善点を診断",
        back_to="/mirai-kessan",
        brand="未来決算",
    )
    periods = annual_reports.list_periods()
    selected_period = period if period in periods else (periods[0] if periods else today_jst().strftime("%Y-%m"))
    report = annual_reports.get_report(selected_period)
    current_result = annual_reports.calculate(report["current"])
    previous_result = annual_reports.calculate(report["previous"])
    has_values = any(report["current"].values())
    inputs = {}

    with content:
        with ui.card().classes("surface-card w-full q-pa-md q-mb-md"):
            ui.label("決算期").classes("text-xs font-bold")
            period_input = ui.input(value=selected_period).props("type=month outlined").classes("w-full q-mt-xs")
            if periods:
                ui.label("保存済みの決算期").classes("text-[10px] text-grey-6 q-mt-md")
                with ui.row().classes("w-full gap-1 q-mt-xs"):
                    for saved_period in periods:
                        ui.button(
                            saved_period.replace("-", "年") + "月",
                            on_click=lambda _, value=saved_period: ui.navigate.to(
                                f"/mirai-kessan/financial-analysis/{value}"
                            ),
                        ).props("outline dense no-caps")

        ui.label("決算書入力").classes("text-xl font-black q-mb-xs")
        ui.label("日々の入力とは連動しません。この決算期の数字だけ入力してください。").classes(
            "text-[10px] text-grey-6 q-mb-md"
        )
        if report.get("previous_period"):
            ui.label(
                f"前期比較には、保存済みの{report['previous_period'].replace('-', '年')}月期を自動使用します。"
            ).classes("text-[10px] text-primary font-bold q-mb-md")
        else:
            ui.label("前期比較をする場合は、古い決算期から先に登録してください。").classes(
                "text-[10px] q-mb-md"
            ).style("color:#A66A17")

        def statement_section(statement_title, sections):
            with ui.expansion(statement_title, icon="description", value=True).classes(
                "surface-card w-full q-mb-md"
            ):
                with ui.element("div").classes("statement-grid statement-head"):
                    ui.label("科目")
                    ui.label("当期")
                for section_title, fields in sections:
                    ui.label(section_title).classes("text-xs font-black text-primary q-mt-md q-mb-xs")
                    for key, label in fields:
                        with ui.element("div").classes("statement-grid items-center"):
                            ui.label(label).classes("text-[10px] text-grey-8")
                            inputs[key] = ui.input(
                                value=str(report["current"][key]) if report["current"][key] else None,
                                placeholder="0 または △59,960",
                            ).props("outlined dense prefix=¥ inputmode=decimal")

        statement_section("貸借対照表", BS_SECTIONS)
        statement_section("損益計算書", PL_SECTIONS)

        def save_report():
            try:
                saved = annual_reports.save_report(
                    str(period_input.value),
                    {key: field.value for key, field in inputs.items()},
                )
            except ValueError as error:
                ui.notify(str(error), type="negative")
                return
            ui.notify("決算書を保存して分析しました", type="positive")
            ui.navigate.to(f"/mirai-kessan/financial-analysis/{saved['period']}")

        ui.button("保存して分析する", icon="analytics", on_click=save_report).classes(
            "w-full q-mb-lg"
        )

        if has_values:
            with ui.row().classes("w-full items-center justify-between q-mb-sm"):
                ui.label("会社の健康診断").classes("text-xl font-black")
                ui.button(
                    "報告モード", icon="present_to_all",
                    on_click=lambda: ui.navigate.to(
                        f"/mirai-kessan/financial-analysis/{selected_period}/report"
                    ),
                ).props("outline dense no-caps")
            with ui.element("div").classes("grid grid-cols-2 gap-2 w-full q-mb-md"):
                metrics = (
                    ("流動比率", _ratio(current_result["current_ratio"]), "短期の支払余力"),
                    ("当座比率", _ratio(current_result["quick_ratio"]), "現預金・売掛金での支払余力"),
                    ("自己資本比率", _ratio(current_result["equity_ratio"]), "会社の財務的な安定性"),
                    ("営業利益率", _ratio(current_result["operating_margin"]), "本業で残る利益"),
                    ("現預金月商倍率", f"{current_result['cash_months']:.1f}か月" if current_result["cash_months"] is not None else "—", "手元資金の厚み"),
                    ("借入金月商倍率", f"{current_result['debt_to_sales'] * 12:.1f}か月" if current_result["debt_to_sales"] is not None else "—", "売上何か月分の借入か"),
                )
                for title, value, note in metrics:
                    with ui.element("div").classes("diagnostic-metric"):
                        ui.label(title).classes("text-[10px] text-grey-7")
                        ui.label(value).classes("text-xl font-black q-mt-xs")
                        ui.label(note).classes("text-[8px] text-grey-6 q-mt-xs")

            with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
                ui.label("貸借対照表の全体像").classes("text-lg font-black")
                with ui.element("div").classes("grid grid-cols-2 gap-2 w-full q-mt-md"):
                    for title, value, color in (
                        ("総資産", current_result["assets"], "#E9F4EE"),
                        ("負債", current_result["liabilities"], "#FFF1E6"),
                        ("純資産", current_result["equity"], "#EEF1FF" if current_result["equity"] >= 0 else "#FDECEA"),
                        ("貸借差額", current_result["balance_gap"], "#F3F5F3" if not current_result["balance_gap"] else "#FFF6DC"),
                    ):
                        with ui.element("div").classes("rounded-xl q-pa-md").style(f"background:{color}"):
                            ui.label(title).classes("text-[9px] text-grey-7")
                            ui.label(_money(value)).classes(
                                "text-lg font-black text-negative" if value < 0 else "text-lg font-black"
                            )

            alerts = []
            if current_result["balance_gap"]:
                alerts.append(("入力確認", f"資産と負債・純資産に {_money(abs(current_result['balance_gap']))} の差があります。決算書の入力漏れを確認してください。", "warning"))
            if current_result["equity"] < 0:
                alerts.append(("最優先：債務超過", f"純資産が {_money(current_result['equity'])} です。利益改善と返済計画を合わせた解消計画が必要です。", "negative"))
            if current_result["current_ratio"] is not None and current_result["current_ratio"] < 1:
                alerts.append(("最優先：短期の支払余力", f"流動比率は {_ratio(current_result['current_ratio'])} です。未払金・税金・短期借入の支払時期と現預金予定を確認してください。", "negative"))
            if current_result["cash_months"] is not None and current_result["cash_months"] < 1:
                alerts.append(("重要：手元資金", f"現預金は月商の約 {current_result['cash_months']:.1f}か月分です。資金繰り予定表を優先して作る状態です。", "warning"))
            if current_result["operating_profit"] < 0:
                alerts.append(("重要：本業の赤字", f"営業損失は {_money(abs(current_result['operating_profit']))} です。原価・人件費・固定費の改善が必要です。", "negative"))
            if not alerts:
                alerts.append(("大きな緊急警告なし", "入力された主要指標では、直ちに表示すべき重大警告はありません。前年差と資金計画を確認してください。", "positive"))

            ui.label("改善の優先順位").classes("text-xl font-black q-mb-sm")
            for title, message, kind in alerts:
                colors = {"negative": ("#FDECEA", "#9D342F"), "warning": ("#FFF5DE", "#8A5D12"), "positive": ("#EAF5EE", "#286647")}
                background, color = colors[kind]
                with ui.card().classes("w-full q-pa-md q-mb-sm").style(
                    f"border-radius:18px;background:{background};color:{color};box-shadow:none"
                ):
                    ui.label(title).classes("text-sm font-black")
                    ui.label(message).classes("text-[10px] leading-relaxed q-mt-xs")

            ui.label("前期からの変化").classes("text-xl font-black q-mt-md q-mb-sm")
            with ui.card().classes("surface-card w-full q-pa-md"):
                comparisons = (
                    ("売上高", report["current"]["sales"], report["previous"]["sales"]),
                    ("営業利益", current_result["operating_profit"], previous_result["operating_profit"]),
                    ("当期純利益", current_result["net_income"], previous_result["net_income"]),
                    ("現金・預金", report["current"]["cash_on_hand"] + report["current"]["checking_deposit"] + report["current"]["ordinary_deposit"], report["previous"]["cash_on_hand"] + report["previous"]["checking_deposit"] + report["previous"]["ordinary_deposit"]),
                    ("純資産", current_result["equity"], previous_result["equity"]),
                )
                for title, current, previous in comparisons:
                    difference = current - previous
                    with ui.row().classes("w-full items-center justify-between q-py-sm no-wrap").style(
                        "border-bottom:1px solid #EEF0EE"
                    ):
                        with ui.column().classes("gap-0"):
                            ui.label(title).classes("text-xs font-bold")
                            ui.label(f"前期 {_money(previous)} → 当期 {_money(current)}").classes("text-[8px] text-grey-6")
                        ui.label(("+" if difference > 0 else "") + _money(difference)).classes(
                            "text-sm font-black text-positive" if difference >= 0 else "text-sm font-black text-negative"
                        )
        else:
            with ui.card().classes("surface-card w-full q-pa-lg"):
                ui.label("決算書を入力すると診断結果が表示されます").classes(
                    "text-sm text-grey-6 text-center"
                )

        ui.add_css("""
        .statement-grid{width:100%;display:grid;grid-template-columns:minmax(120px,1.15fr) minmax(120px,1fr);gap:8px}
        .statement-head{color:#6D7972;font-size:9px;font-weight:800;margin-bottom:5px}
        .statement-grid .q-field__control{min-height:38px;height:38px}.statement-grid .q-field__native{font-size:11px;padding:0}
        .diagnostic-metric{border-radius:16px;padding:14px;background:#F4F7F5;min-width:0}
        @media(max-width:520px){.statement-grid{grid-template-columns:minmax(105px,1fr) minmax(120px,1.15fr);gap:6px}}
        """)


@ui.page("/mirai-kessan/financial-analysis")
def financial_analysis_page():
    _render_analysis()


@ui.page("/mirai-kessan/financial-analysis/{period}")
def financial_analysis_period_page(period: str):
    _render_analysis(period)


@ui.page("/mirai-kessan/financial-analysis/{period}/report")
def financial_analysis_report_page(period: str):
    if not require_login():
        return
    Theme.page("決算報告", app_name="mirai-kessan")
    report = annual_reports.get_report(period)
    current = annual_reports.calculate(report["current"])
    previous = annual_reports.calculate(report["previous"])
    content = Theme.shell(
        "決算報告",
        period.replace("-", "年") + "月期｜会社の現在地と次の一手",
        back_to=f"/mirai-kessan/financial-analysis/{period}",
        brand="未来決算",
    )
    equity_negative = current["equity"] < 0
    liquidity_low = current["current_ratio"] is not None and current["current_ratio"] < 1
    operating_negative = current["operating_profit"] < 0
    urgent_count = sum((equity_negative, liquidity_low, operating_negative))
    with content:
        with ui.card().classes("report-hero w-full q-pa-lg q-mb-md text-white"):
            ui.label("総合診断").classes("text-xs opacity-70")
            ui.label(
                "財務改善を最優先" if urgent_count >= 2 else
                "注意項目を確認" if urgent_count else "大きな緊急警告なし"
            ).classes("text-3xl font-black q-mt-xs")
            ui.label(
                f"重要な確認項目が {urgent_count} 件あります" if urgent_count
                else "主要指標は安定しています。成長と利益改善を確認しましょう。"
            ).classes("text-sm opacity-80 q-mt-sm")

        with ui.element("div").classes("grid grid-cols-2 gap-2 w-full q-mb-md"):
            for title, value, note, danger in (
                ("売上高", report["current"]["sales"], "前期比 " + (_ratio(report["current"]["sales"] / report["previous"]["sales"]) if report["previous"]["sales"] else "—"), False),
                ("営業利益", current["operating_profit"], "営業利益率 " + _ratio(current["operating_margin"]), operating_negative),
                ("当期純利益", current["net_income"], "前期 " + _money(previous["net_income"]), current["net_income"] < 0),
                ("純資産", current["equity"], "自己資本比率 " + _ratio(current["equity_ratio"]), equity_negative),
            ):
                with ui.element("div").classes("report-kpi").style(
                    "background:#FDECEA" if danger else "background:#F3F7F4"
                ):
                    ui.label(title).classes("text-[10px] text-grey-7")
                    ui.label(_money(value)).classes(
                        "text-xl font-black text-negative" if danger else "text-xl font-black"
                    )
                    ui.label(note).classes("text-[8px] text-grey-6")

        with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
            ui.label("財務の全体像").classes("text-lg font-black")
            scale = max(current["assets"], current["liabilities"], abs(current["equity"]), 1)
            for title, value, color in (
                ("資産", current["assets"], "#3F7C62"),
                ("負債", current["liabilities"], "#D18A3B"),
                ("純資産", current["equity"], "#C85450" if equity_negative else "#557CC0"),
            ):
                ui.label(f"{title}　{_money(value)}").classes("text-xs font-bold q-mt-md")
                with ui.element("div").classes("report-bar-track"):
                    ui.element("div").classes("report-bar").style(
                        f"width:{max(abs(value) / scale * 100, 1):.2f}%;background:{color}"
                    )
            if current["balance_gap"]:
                ui.label(
                    f"貸借に {_money(abs(current['balance_gap']))} の差があります。入力内容を確認してください。"
                ).classes("text-xs text-negative font-bold q-mt-md")

        ui.label("最優先で確認").classes("text-xl font-black q-mb-sm")
        priorities = []
        if equity_negative:
            priorities.append(("債務超過", f"純資産 {_money(current['equity'])}。利益を積み上げる中期解消計画が必要です。"))
        if liquidity_low:
            priorities.append(("短期の支払余力", f"流動比率 {_ratio(current['current_ratio'])}。支払時期と現預金予定を月別に確認してください。"))
        if current["cash_months"] is not None and current["cash_months"] < 1:
            priorities.append(("手元資金", f"現預金は月商の約 {current['cash_months']:.1f}か月分です。資金繰り管理を優先してください。"))
        if operating_negative:
            priorities.append(("本業の収益", f"営業損失 {_money(abs(current['operating_profit']))}。原価・人件費・固定費を分けて改善します。"))
        if not priorities:
            priorities.append(("成長と利益改善", "重大警告はありません。前年差と来期計画から次の成長投資を判断できます。"))
        for index, (title, message) in enumerate(priorities, 1):
            with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                with ui.row().classes("items-start no-wrap"):
                    ui.label(str(index)).classes("priority-number")
                    with ui.column().classes("gap-0"):
                        ui.label(title).classes("text-sm font-black")
                        ui.label(message).classes("text-[10px] text-grey-7 leading-relaxed q-mt-xs")

        ui.label("前期との比較").classes("text-xl font-black q-mt-md q-mb-sm")
        with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
            for title, now, before in (
                ("売上高", report["current"]["sales"], report["previous"]["sales"]),
                ("営業利益", current["operating_profit"], previous["operating_profit"]),
                ("現金・預金", report["current"]["cash_on_hand"] + report["current"]["checking_deposit"] + report["current"]["ordinary_deposit"], report["previous"]["cash_on_hand"] + report["previous"]["checking_deposit"] + report["previous"]["ordinary_deposit"]),
                ("純資産", current["equity"], previous["equity"]),
            ):
                difference = now - before
                with ui.element("div").classes("report-kpi"):
                    ui.label(title).classes("text-[10px] text-grey-7")
                    ui.label(("+" if difference > 0 else "") + _money(difference)).classes(
                        "text-lg font-black text-positive" if difference >= 0 else "text-lg font-black text-negative"
                    )
                    ui.label(f"前期 {_money(before)} → 当期 {_money(now)}").classes("text-[8px] text-grey-6")

        ui.label("※診断は経営判断の補助です。最終的な会計・税務判断は顧問税理士と確認してください。").classes(
            "text-[9px] text-grey-6 q-mt-lg"
        )
        ui.add_css("""
        .report-hero{border-radius:26px;border:0;background:linear-gradient(145deg,#173F32,#315F4C 65%,#9B7040);box-shadow:0 18px 38px rgba(24,62,49,.2)}
        .report-kpi{border-radius:17px;padding:15px;background:#F3F7F4;min-width:0}
        .report-bar-track{width:100%;height:22px;border-radius:7px;background:#EDF0EE;overflow:hidden;margin-top:5px}.report-bar{height:100%;border-radius:7px}
        .priority-number{display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:50%;background:#FFF0E4;color:#9A5C24;font-weight:900;flex:none}
        """)
