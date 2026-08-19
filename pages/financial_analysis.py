from nicegui import ui

from core.annual_reports import annual_reports
from core.auth import require_app_access
from core.clock import today_jst
from core.theme import Theme


BS_SECTIONS = (
    ("流動資産", (
        ("cash_on_hand", "現金"), ("checking_deposit", "当座預金"),
        ("ordinary_deposit", "普通預金"), ("receivables", "売掛金"),
        ("merchandise", "商品・棚卸資産"), ("temporary_payment", "仮払金"),
        ("prepaid", "前払費用"), ("substitute_payment", "立替金"),
    )),
    ("固定資産", (
        ("building_equipment", "建物附属設備"), ("vehicles", "車両運搬具"),
        ("fixtures", "什器備品"), ("lump_sum_depreciable_assets", "一括償却資産"),
        ("telephone_rights", "電話加入権"), ("investments", "出資金"),
        ("security_deposit", "保証金"), ("lease_deposit", "敷金"),
        ("membership_deposit", "加盟金"),
    )),
    ("流動負債", (
        ("payables", "買掛金"), ("short_term_loans", "短期借入金"),
        ("unpaid_accounts", "未払金"), ("accrued_expenses", "未払費用"),
        ("deposits_received", "預り金"), ("unpaid_consumption_tax", "未払消費税"),
    )),
    ("固定負債", (
        ("long_term_loans", "長期借入金"),
        ("other_fixed_liabilities", "その他固定負債"),
    )),
    ("純資産", (
        ("capital", "資本金"), ("profit_reserve", "利益準備金"),
        ("special_reserve", "別途積立金"), ("retained_earnings", "繰越利益剰余金"),
    )),
)

PL_SECTIONS = (
    ("売上・売上原価", (
        ("sales", "売上高"), ("opening_inventory", "期首棚卸高"),
        ("purchases", "仕入高"), ("closing_inventory", "期末棚卸高"),
    )),
    ("人件費", (
        ("executive_compensation", "役員報酬"), ("salaries", "給料手当"),
        ("retirement_allowance", "退職金"), ("statutory_welfare", "法定福利費"),
        ("welfare", "福利厚生費"), ("temporary_wages", "雑給"),
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
        ("lease", "リース料"), ("miscellaneous_expenses", "雑費"),
    )),
    ("営業外・特別損益", (
        ("interest_income", "受取利息"), ("dividend_income", "受取配当金"),
        ("miscellaneous_income", "雑収入"), ("interest_expense", "支払利息・割引料"),
        ("guarantee_amortization", "保証料償却"), ("miscellaneous_loss", "雑損失"),
        ("extraordinary_income", "特別利益"),
        ("fixed_asset_disposal_loss", "固定資産除却損"),
    )),
)


def _money(value):
    return f"¥{int(value):,}"


def _ratio(value):
    return "—" if value is None else f"{value * 100:.1f}%"


def _render_analysis(period=None):
    if not require_app_access("future_financials"):
        return
    Theme.page("決算分析", app_name="mirai-kessan")
    content = Theme.shell(
        "決算分析",
        "決算書の最新数字を入力して、会社の状態と改善点を診断",
        back_to="/mirai-kessan/dashboard",
        brand="未来決算",
    )
    periods = annual_reports.list_periods()
    default_year = today_jst().year if today_jst().month >= 9 else today_jst().year - 1
    selected_period = period if period in periods else (periods[0] if periods else f"{default_year:04d}-09")
    report = annual_reports.get_report(selected_period)
    current_result = annual_reports.calculate(report["current"])
    previous_result = annual_reports.calculate(report["previous"])
    has_values = any(report["current"].values())
    inputs = {}
    subtotal_labels = {}

    def input_number(value):
        try:
            normalized = str(value or 0).strip().replace(",", "")
            if normalized.startswith("△"):
                normalized = "-" + normalized[1:]
            return int(float(normalized))
        except (TypeError, ValueError):
            return 0

    def amount_input(value):
        with ui.element("div").classes("amount-entry"):
            field = ui.input(
                value=f"{value:,}" if value else None,
            ).props("outlined dense prefix=¥ inputmode=decimal").classes("amount-field")

            def toggle_negative():
                text = str(field.value or "").strip()
                if not text:
                    field.value = "△"
                elif text.startswith(("-", "△")):
                    field.value = text[1:]
                else:
                    field.value = "△" + text

            ui.button("△", on_click=toggle_negative).props(
                "flat dense aria-label='プラス・マイナスを切り替え'"
            ).classes("negative-toggle").tooltip("プラス・マイナスを切り替え")
            field.on("focus", js_handler="""(event) => {
                event.target.value = event.target.value.replace(/,/g, '');
            }""")
            field.on("blur", js_handler="""(event) => {
                const raw = event.target.value.trim();
                if (!raw || raw === '△' || raw === '-') return;
                const negative = raw.startsWith('△') || raw.startsWith('-');
                const number = Number(raw.replace(/[△,\-]/g, ''));
                if (!Number.isFinite(number)) return;
                event.target.value = (negative ? '△' : '') + Math.round(number).toLocaleString('ja-JP');
                event.target.dispatchEvent(new Event('input', {bubbles: true}));
            }""")
        return field

    with content:
        with ui.card().classes("period-card surface-card w-full q-pa-sm q-mb-md"):
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                ui.label("決算期").classes("text-xs font-bold q-pl-sm")
                period_year = ui.number(
                    value=int(selected_period[:4]), min=1900, max=2200, step=1
                ).props("outlined dense suffix=年 inputmode=numeric aria-label='決算年'").classes(
                    "period-year"
                )
                ui.label("9月末締め").classes("text-[9px] text-grey-6")
            if periods:
                with ui.expansion("保存済みの決算期", value=False).classes("saved-periods w-full"):
                    with ui.row().classes("w-full gap-1"):
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
            with ui.expansion(statement_title, icon="description", value=False).classes(
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
                            inputs[key] = amount_input(report["current"][key])
                    with ui.element("div").classes("statement-grid subtotal-row items-center"):
                        subtotal_title = (
                            "売上総利益（自動計算）"
                            if section_title == "売上・売上原価"
                            else section_title + " 小計"
                        )
                        ui.label(subtotal_title).classes("text-[10px] font-black")
                        subtotal_labels[section_title] = ui.label("¥0").classes(
                            "text-sm font-black text-primary text-right"
                        )

        statement_section("貸借対照表", BS_SECTIONS)
        statement_section("損益計算書", PL_SECTIONS)

        section_fields = {
            title: tuple(key for key, _ in fields)
            for title, fields in (*BS_SECTIONS, *PL_SECTIONS)
        }

        def refresh_subtotals():
            for title, keys in section_fields.items():
                if title == "売上・売上原価":
                    sales = input_number(inputs["sales"].value)
                    cost = (
                        input_number(inputs["opening_inventory"].value)
                        + input_number(inputs["purchases"].value)
                        - input_number(inputs["closing_inventory"].value)
                    )
                    subtotal = sales - cost
                elif title == "営業外・特別損益":
                    subtotal = (
                        input_number(inputs["interest_income"].value)
                        + input_number(inputs["dividend_income"].value)
                        + input_number(inputs["miscellaneous_income"].value)
                        + input_number(inputs["extraordinary_income"].value)
                        - input_number(inputs["interest_expense"].value)
                        - input_number(inputs["guarantee_amortization"].value)
                        - input_number(inputs["miscellaneous_loss"].value)
                        - input_number(inputs["fixed_asset_disposal_loss"].value)
                    )
                else:
                    subtotal = sum(input_number(inputs[key].value) for key in keys)
                subtotal_labels[title].text = _money(subtotal)

        for field in inputs.values():
            field.on_value_change(lambda _: refresh_subtotals())
        refresh_subtotals()

        def save_report():
            try:
                year = int(period_year.value)
                saved = annual_reports.save_report(
                    f"{year:04d}-09",
                    {key: field.value for key, field in inputs.items()},
                )
            except (TypeError, ValueError) as error:
                ui.notify(str(error), type="negative")
                return
            ui.notify("決算書を保存して分析しました", type="positive")
            ui.navigate.to(f"/mirai-kessan/financial-analysis/{saved['period']}")

        ui.button("保存して分析する", icon="analytics", on_click=save_report).classes(
            "w-full q-mb-lg"
        )

        if has_values:
            with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
                ui.label("バランスシート").classes("text-xl font-black")
                ui.label("左の資産と、右の負債・純資産が同額なら入力完了です").classes(
                    "text-[9px] text-grey-6 q-mb-md"
                )
                with ui.element("div").classes("balance-sheet"):
                    with ui.element("div").classes("balance-side asset-side"):
                        ui.label("資産").classes("balance-heading")
                        for label, value in (
                            ("流動資産", current_result["current_assets"]),
                            ("固定資産", current_result["fixed_assets"]),
                        ):
                            with ui.row().classes("w-full justify-between no-wrap"):
                                ui.label(label)
                                ui.label(_money(value)).classes("font-bold")
                        ui.separator().classes("q-my-sm")
                        with ui.row().classes("w-full justify-between no-wrap"):
                            ui.label("資産合計").classes("font-black")
                            ui.label(_money(current_result["assets"])).classes("font-black")
                    with ui.element("div").classes("balance-side funding-side"):
                        ui.label("負債・純資産").classes("balance-heading")
                        for label, value in (
                            ("流動負債", current_result["current_liabilities"]),
                            ("固定負債", current_result["fixed_liabilities"]),
                            ("純資産", current_result["equity"]),
                        ):
                            with ui.row().classes("w-full justify-between no-wrap"):
                                ui.label(label)
                                ui.label(_money(value)).classes("font-bold")
                        ui.separator().classes("q-my-sm")
                        with ui.row().classes("w-full justify-between no-wrap"):
                            ui.label("合計").classes("font-black")
                            ui.label(_money(current_result["liabilities"] + current_result["equity"])).classes("font-black")
                if current_result["balance_gap"]:
                    larger = "資産側" if current_result["balance_gap"] > 0 else "負債・純資産側"
                    ui.label(
                        f"{larger}が {_money(abs(current_result['balance_gap']))} 多い状態です"
                    ).classes("balance-warning")
                else:
                    ui.label("左右が一致しています").classes("balance-ok")

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
                                "overview-number text-negative" if value < 0 else "overview-number"
                            )

            alerts = []
            if current_result["balance_gap"]:
                larger = "資産側が多い" if current_result["balance_gap"] > 0 else "負債・純資産側が多い"
                alerts.append((
                    "入力確認：貸借が一致していません",
                    f"資産 {_money(current_result['assets'])} に対し、負債＋純資産は {_money(current_result['liabilities'] + current_result['equity'])}。差額 {_money(abs(current_result['balance_gap']))}（{larger}）です。下の内訳と決算書の各合計を照合してください。",
                    "warning",
                ))
                with ui.card().classes("w-full q-pa-md q-mb-sm").style(
                    "border-radius:18px;background:#FFF9EB;box-shadow:none"
                ):
                    ui.label("貸借チェックの内訳").classes("text-sm font-black").style("color:#805817")
                    for label, value in (
                        ("流動資産", current_result["current_assets"]),
                        ("固定資産", current_result["fixed_assets"]),
                        ("資産合計", current_result["assets"]),
                        ("流動負債", current_result["current_liabilities"]),
                        ("固定負債", current_result["fixed_liabilities"]),
                        ("純資産", current_result["equity"]),
                        ("負債・純資産合計", current_result["liabilities"] + current_result["equity"]),
                    ):
                        with ui.row().classes("w-full items-center justify-between q-py-xs"):
                            ui.label(label).classes("text-[10px] text-grey-7")
                            ui.label(_money(value)).classes("text-xs font-bold")
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
        .period-card{border-radius:18px!important}.period-year{width:120px;max-width:42%}.saved-periods .q-item{min-height:34px!important;padding:4px 8px!important;font-size:10px}.statement-grid{width:100%;display:grid;grid-template-columns:minmax(120px,1.15fr) minmax(120px,1fr);gap:8px}
        .statement-head{color:#6D7972;font-size:9px;font-weight:800;margin-bottom:5px}
        .statement-grid .q-field__control{min-height:38px;height:38px}.statement-grid .q-field__native{font-size:11px;padding:0}
        .amount-entry{display:grid;grid-template-columns:minmax(0,1fr) 34px;gap:3px;align-items:center;min-width:0}.amount-field{min-width:0;width:100%}.negative-toggle{min-width:34px!important;width:34px;height:38px;min-height:38px!important;padding:0!important;border-radius:9px!important;background:#FFF0EE!important;color:#B54E48!important;font-size:15px;font-weight:900}
        .subtotal-row{margin:6px 0 12px;padding:9px 10px;border-radius:10px;background:#EDF5F0;border:1px solid #DCE9E1}.balance-sheet{display:grid;grid-template-columns:1fr 1fr;border:2px solid #DDE4DF;border-radius:14px;overflow:hidden}.balance-side{padding:14px;font-size:10px;min-width:0;overflow:hidden}.balance-side .q-row>div,.balance-side .font-bold,.balance-side .font-black{min-width:0;max-width:62%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.balance-side+ .balance-side{border-left:2px solid #DDE4DF}.asset-side{background:#EFF7F2}.funding-side{background:#FFF7EA}.balance-heading{font-size:13px;font-weight:900;margin-bottom:12px}.balance-warning{margin-top:10px;padding:10px;border-radius:10px;background:#FDECEA;color:#A13C36;font-size:11px;font-weight:900;text-align:center}.balance-ok{margin-top:10px;padding:10px;border-radius:10px;background:#EAF5EE;color:#286647;font-size:11px;font-weight:900;text-align:center}
        .diagnostic-metric{border-radius:16px;padding:12px;background:#F4F7F5;min-width:0;overflow:hidden}.diagnostic-metric .text-xl{font-size:clamp(15px,5vw,20px)!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.overview-number{font-size:clamp(12px,4vw,18px);font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
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
    if not require_app_access("future_financials"):
        return
    Theme.page("決算報告", app_name="mirai-kessan")
    report = annual_reports.get_report(period)
    current = annual_reports.calculate(report["current"])
    previous = annual_reports.calculate(report["previous"])
    decision = annual_reports.management_decision(report["current"], report["previous"])
    health = annual_reports.restaurant_health(report["current"])
    content = Theme.shell(
        "決算報告",
        period.replace("-", "年") + "月期｜会社の現在地と次の一手",
        back_to=f"/mirai-kessan/financial-analysis/{period}",
        brand="未来決算",
    )
    equity_negative = current["equity"] < 0
    liquidity_low = current["current_ratio"] is not None and current["current_ratio"] < 1
    operating_negative = current["operating_profit"] < 0
    sales = report["current"]["sales"]
    previous_sales = report["previous"]["sales"]
    personnel = sum(report["current"][key] for key in (
        "executive_compensation", "salaries", "retirement_allowance",
        "statutory_welfare", "welfare", "temporary_wages",
    ))
    total_debt = report["current"]["short_term_loans"] + report["current"]["long_term_loans"]
    working_capital = current["current_assets"] - current["current_liabilities"]
    cogs_rate = current["cogs"] / sales if sales else None
    personnel_rate = personnel / current["gross_profit"] if current["gross_profit"] else None
    sales_change = (sales / previous_sales - 1) if previous_sales else None
    debt_payback_years = total_debt / current["ordinary_profit"] if current["ordinary_profit"] > 0 else None
    with content:
        with ui.card().classes(f"report-hero {decision['mode']} w-full q-pa-lg q-mb-md text-white"):
            ui.label("今の経営方針").classes("text-xs opacity-70")
            ui.label(decision["label"]).classes("text-3xl font-black q-mt-xs")
            ui.label(decision["summary"]).classes("text-sm opacity-85 q-mt-sm leading-relaxed")

        if decision["mode"] == "verify":
            with ui.card().classes("decision-verification w-full q-pa-lg q-mb-md"):
                ui.label("この分析はまだ確定していません").classes("text-lg font-black")
                ui.label(decision["reasons"][0]).classes("text-sm q-mt-sm")
                ui.label("先に貸借を一致させると、守り・改善・攻めを判定できます。").classes(
                    "text-[10px] q-mt-sm opacity-70"
                )
        else:
            with ui.card().classes("decision-card w-full q-pa-lg q-mb-md"):
                ui.label("この方針になった理由").classes("text-base font-black q-mb-sm")
                for reason in decision["reasons"]:
                    with ui.row().classes("items-start no-wrap q-mb-sm"):
                        ui.icon("check_circle").classes("text-primary text-lg")
                        ui.label(reason).classes("text-xs leading-relaxed")

        ui.label("経営サマリー").classes("report-section-title")
        with ui.element("div").classes("grid grid-cols-2 gap-2 w-full q-mb-md"):
            for title, value, note, danger in (
                ("売上高", _money(sales), "前年差 " + (("+" if sales - previous_sales > 0 else "") + _money(sales - previous_sales)) if previous_sales else "前期データなし", False),
                ("営業利益", _money(current["operating_profit"]), "利益率 " + _ratio(current["operating_margin"]), operating_negative),
                ("運転資金", _money(working_capital), "流動資産 − 流動負債", working_capital < 0),
                ("純資産", _money(current["equity"]), "自己資本比率 " + _ratio(current["equity_ratio"]), equity_negative),
            ):
                with ui.element("div").classes("report-kpi danger" if danger else "report-kpi"):
                    ui.label(title).classes("text-[10px] opacity-70")
                    ui.label(value).classes("text-xl font-black q-mt-xs")
                    ui.label(note).classes("text-[8px] opacity-70 q-mt-xs")

        ui.label("次に打つ手").classes("report-section-title")
        for index, action in enumerate(decision["actions"], 1):
            with ui.card().classes("action-card w-full q-pa-md q-mb-sm"):
                with ui.row().classes("items-start no-wrap"):
                    ui.label(str(index)).classes("priority-number")
                    ui.label(action).classes("text-xs font-bold leading-relaxed q-pt-xs")

        ui.label("飲食店の健康診断").classes("report-section-title")
        ui.label("飲食店の参考値と比較。色は合否ではなく、確認の優先度です。").classes(
            "text-[9px] text-grey-6 q-mb-sm"
        )
        with ui.element("div").classes("health-grid w-full q-mb-md"):
            for item in health:
                with ui.element("div").classes(f"health-card {item['status']}"):
                    with ui.row().classes("w-full items-center justify-between no-wrap"):
                        ui.label(item["title"]).classes("health-title")
                        ui.element("span").classes("health-dot")
                    ui.label(item["display"]).classes("health-value")
                    ui.label(item["guide"]).classes("health-guide")
                    with ui.expansion("意味と使い方", value=False).classes("health-help"):
                        ui.label(item["meaning"]).classes("text-[9px] leading-relaxed")
                        ui.label("次の行動：" + item["action"]).classes(
                            "text-[9px] font-bold leading-relaxed q-mt-xs"
                        )

        with ui.expansion("財務の詳しい数字", icon="account_balance", value=False).classes(
            "detail-drawer w-full q-mb-sm"
        ):
            for title, value, meaning in (
                ("流動比率", _ratio(current["current_ratio"]), "短期の支払いに対する流動資産の厚み"),
                ("運転資金", _money(working_capital), "流動資産から流動負債を引いた金額"),
                ("借入残高", _money(total_debt), "短期借入金と長期借入金の合計"),
                ("債務償還年数", f"{debt_payback_years:.1f}年" if debt_payback_years is not None else "算定不可", "現在の経常利益で返す場合の目安"),
            ):
                with ui.row().classes("w-full items-center justify-between no-wrap q-py-sm"):
                    with ui.column().classes("gap-0 min-w-0"):
                        ui.label(title).classes("text-xs font-bold")
                        ui.label(meaning).classes("text-[8px] text-grey-6")
                    ui.label(value).classes("compact-number")

        if decision["mode"] != "attack" and decision["attack_conditions"]:
            with ui.expansion("攻めに転じる条件", icon="rocket_launch", value=False).classes(
                "attack-conditions w-full q-mb-md"
            ):
                for condition in decision["attack_conditions"]:
                    with ui.row().classes("items-start no-wrap q-mb-sm"):
                        ui.icon("radio_button_unchecked").classes("text-amber-8 text-sm")
                        ui.label(condition).classes("text-[10px] leading-relaxed")

        with ui.expansion("前期との比較", icon="compare_arrows", value=False).classes(
            "detail-drawer w-full q-mb-sm"
        ):
            for title, now, before in (
                ("売上高", report["current"]["sales"], report["previous"]["sales"]),
                ("営業利益", current["operating_profit"], previous["operating_profit"]),
                ("当期純利益", current["net_income"], previous["net_income"]),
                ("現金・預金", report["current"]["cash_on_hand"] + report["current"]["checking_deposit"] + report["current"]["ordinary_deposit"], report["previous"]["cash_on_hand"] + report["previous"]["checking_deposit"] + report["previous"]["ordinary_deposit"]),
                ("純資産", current["equity"], previous["equity"]),
            ):
                difference = now - before
                with ui.row().classes("w-full items-center justify-between no-wrap q-py-sm"):
                    ui.label(title).classes("text-xs font-bold")
                    ui.label(("+" if difference > 0 else "") + _money(difference)).classes("compact-number")

        ui.label("※診断は経営判断の補助です。最終的な会計・税務判断は顧問税理士と確認してください。").classes(
            "text-[9px] text-grey-6 q-mt-lg"
        )
        ui.add_css("""
        .report-hero{border-radius:28px;border:0;background:radial-gradient(circle at 90% 10%,rgba(214,170,92,.38),transparent 34%),linear-gradient(145deg,#102F27,#1D5945 70%,#76532E);box-shadow:0 20px 44px rgba(17,55,42,.25)}.report-hero.defense{background:radial-gradient(circle at 88% 8%,rgba(238,150,109,.35),transparent 35%),linear-gradient(145deg,#3B2020,#8B3832)}.report-hero.improve{background:radial-gradient(circle at 88% 8%,rgba(255,213,127,.35),transparent 35%),linear-gradient(145deg,#493411,#A06C22)}.report-hero.attack{background:radial-gradient(circle at 88% 8%,rgba(145,222,181,.32),transparent 35%),linear-gradient(145deg,#0E3A2B,#287C58)}.report-hero.verify{background:linear-gradient(145deg,#4A4F4C,#777F7A)}
        .report-section-title{font-size:18px;font-weight:900;margin:14px 0 8px}.report-kpi{border-radius:18px;padding:14px;background:linear-gradient(145deg,#F1F7F3,#E8F1EC);min-width:0;max-width:100%;overflow:hidden;color:#1B382C;border:1px solid #E0EAE4}.report-kpi .text-xl,.report-kpi .text-lg{font-size:clamp(14px,4.5vw,20px)!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.report-kpi.danger{background:linear-gradient(145deg,#FFF2EF,#FBE4E1);color:#873934;border-color:#F2D1CD}
        .health-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.health-card{border-radius:18px;padding:13px;min-width:0;overflow:hidden;border:1px solid #E2E9E5;background:#F3F7F4}.health-card.good{background:#EAF5EE;color:#245F43}.health-card.caution{background:#FFF5E2;color:#805817}.health-card.danger{background:#FDECEA;color:#923D37}.health-card.unknown{background:#F1F3F2;color:#68716C}.health-title{font-size:10px;font-weight:900;min-width:0}.health-dot{width:8px;height:8px;flex:none;border-radius:50%;background:currentColor}.health-value{font-size:clamp(18px,6vw,27px);font-weight:900;letter-spacing:-.04em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:5px}.health-guide{font-size:8px;opacity:.72;min-height:22px;line-height:1.35}.health-help .q-item{min-height:30px!important;padding:3px 0!important;font-size:9px}.health-help .q-expansion-item__content{padding-top:5px}.detail-drawer{border-radius:18px!important;background:#fff!important;border:1px solid #E4E9E6!important}.compact-number{font-size:clamp(11px,3.8vw,16px);font-weight:900;max-width:44%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:right}
        .decision-card{border-radius:22px!important;background:#F3F8F5!important;border:1px solid #DDEAE2!important;box-shadow:none!important}.decision-verification{border-radius:22px!important;background:#FFF3DF!important;color:#83581B!important;border:1px solid #F0D8AC!important;box-shadow:none!important}.action-card{border-radius:18px!important;background:#fff!important;border:1px solid #E4E9E6!important;box-shadow:0 7px 20px rgba(35,57,45,.05)!important}.attack-conditions{border-radius:18px!important;background:#FFF8EA!important;border:1px solid #F1E0BA!important}.priority-number{display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:50%;background:#FFF0E4;color:#9A5C24;font-weight:900;flex:none}
        """)
