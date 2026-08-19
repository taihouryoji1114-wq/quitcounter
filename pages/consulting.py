from nicegui import ui

from core.auth import require_app_access
from core.clock import today_jst
from core.consulting import consulting
from core.theme import Theme


@ui.page("/mirai-kessan/consulting")
def consulting_page():
    if not require_app_access("future_financials"):
        return
    Theme.page("経営コンサル｜未来決算", app_name="mirai-kessan")
    month = today_jst().strftime("%Y-%m")
    overview = consulting.executive_overview(month)
    diagnosis = consulting.diagnose(month)
    snapshot = consulting.annual_snapshot(month)
    content = Theme.shell(
        "経営コンサル", "会社の状態を、社長の言葉で判断する",
        back_to="/mirai-kessan/dashboard", brand="未来決算",
    )
    colors = {
        "danger": ("#9E2F38", "#FFF1F1", "error"),
        "warning": ("#A46B16", "#FFF7E8", "warning"),
        "good": ("#23704A", "#ECF7F0", "check_circle"),
        "unknown": ("#5D6670", "#F1F3F4", "help"),
    }
    groups = {
        "今を知る": [
            ("priority", "まず何から直すべき？"),
            ("loss", "本業は大丈夫？"),
            ("compare", "去年より良くなった？"),
        ],
        "未来を知る": [
            ("cash", "お金が足りなくなる可能性は？"),
            ("stress", "売上が下がってもどこまで耐えられる？"),
            ("debt", "借入はどう減らしていく？"),
            ("investment", "いつから攻めてよい？"),
        ],
        "方法を比べる": [
            ("cost", "食材を見直すべき？"),
            ("personnel", "人件費を見直すべき？"),
            ("sales", "売上をどれだけ増やすべき？"),
        ],
        "計画を作る": [
            ("year_plan", "この1年間、何をすればいい？"),
        ],
    }

    with content:
        with ui.row().classes("w-full items-center justify-between q-mb-sm no-wrap"):
            ui.label("会社は今、大丈夫？").classes("text-xl font-black")
            ui.label(snapshot["period"] if snapshot else "決算書未入力").classes("period-chip")

        main_color, main_bg, main_icon = colors[overview["level"]]
        with ui.card().classes("owner-status w-full q-pa-lg text-white").style(
            f"background:linear-gradient(145deg,{main_color},#243B31)"):
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                ui.icon(main_icon).classes("text-2xl")
                ui.label(overview["label"]).classes("text-2xl font-black")
            ui.label(overview["headline"]).classes("text-xs leading-relaxed opacity-90 q-mt-sm")

        if overview["items"]:
            with ui.element("div").classes("status-grid w-full q-mt-sm"):
                for item in overview["items"]:
                    color, bg, icon = colors[item["level"]]
                    with ui.element("div").classes("status-item").style(f"background:{bg}"):
                        with ui.row().classes("items-center no-wrap gap-1"):
                            ui.icon(icon).style(f"color:{color}").classes("text-base")
                            ui.label(item["title"]).classes("text-[10px] font-black")
                        ui.label(item["detail"]).classes("text-[9px] leading-snug text-grey-7 q-mt-xs")

        with ui.expansion("今わかること・まだわからないこと", icon="fact_check", value=False).classes(
            "consult-fold w-full q-mt-sm"):
            with ui.element("div").classes("knowledge-grid w-full"):
                with ui.element("div").classes("knowledge-card known"):
                    ui.label("今わかる").classes("text-[9px] font-black text-positive")
                    for text in overview["known"]:
                        ui.label(f"✓ {text}").classes("text-[9px] q-mt-xs")
                with ui.element("div").classes("knowledge-card unknown"):
                    ui.label("まだわからない").classes("text-[9px] font-black text-grey-7")
                    for text in overview["unknown"]:
                        ui.label(f"・{text}").classes("text-[9px] q-mt-xs")
            with ui.element("div").classes("unlock-card q-mt-sm"):
                ui.label("次に入力すると分かること").classes("text-[9px] font-black")
                ui.label(overview["next_input"]).classes("text-[10px] leading-relaxed q-mt-xs")

        ui.label("詳しく相談する").classes("text-lg font-black q-mt-lg q-mb-xs")
        ui.label("知りたい目的を1つ選んでください").classes("text-[10px] text-grey-6 q-mb-sm")
        menu_area = ui.column().classes("w-full gap-0")
        answer_area = ui.column().classes("w-full gap-0")

        def render_answer(answer):
            answer_area.clear()
            with answer_area:
                with ui.card().classes("consult-answer w-full q-pa-lg q-mt-sm"):
                    ui.label("まず答え").classes("answer-kicker")
                    ui.label(answer["conclusion"]).classes("text-lg font-black q-mt-xs")
                    with ui.expansion("なぜ？", icon="help_outline", value=False).classes("answer-fold w-full q-mt-sm"):
                        ui.label(answer["reason"]).classes("text-[10px] leading-relaxed text-grey-7")
                    with ui.expansion("選択肢・確認すること", icon="rule", value=False).classes("answer-fold w-full"):
                        for action in answer["actions"]:
                            ui.label(f"・{action}").classes("text-[10px] leading-relaxed q-mt-xs")
                    ui.label("できたと判断する基準").classes("answer-kicker q-mt-sm")
                    ui.label(answer["target"]).classes("answer-target")

        def show_answer(key):
            render_answer(consulting.answer(month, key))

        def show_priority(index=0):
            recommendations = diagnosis["recommendations"]
            item = recommendations[min(index, len(recommendations) - 1)]
            answer_area.clear()
            with answer_area:
                with ui.card().classes("consult-answer w-full q-pa-lg q-mt-sm"):
                    ui.label(f"優先順位 {index + 1}/{len(recommendations)}").classes("answer-kicker")
                    ui.label(item["title"]).classes("text-xl font-black q-mt-xs")
                    with ui.expansion("なぜ？", icon="help_outline", value=False).classes("answer-fold w-full q-mt-sm"):
                        ui.label(item["why"]).classes("text-[10px] leading-relaxed")
                    ui.label("考える選択肢").classes("answer-kicker q-mt-sm")
                    ui.label(item["action"]).classes("text-xs leading-relaxed")
                    if index + 1 < len(recommendations):
                        ui.button("次に直すべきものを見る", icon="arrow_forward",
                                  on_click=lambda: show_priority(index + 1)).props("flat no-caps").classes("w-full q-mt-md")

        def show_group(group_name):
            menu_area.clear()
            answer_area.clear()
            with menu_area:
                with ui.row().classes("w-full items-center justify-between no-wrap q-mb-xs"):
                    ui.label(group_name).classes("text-base font-black")
                    ui.button("戻る", icon="arrow_back", on_click=render_groups).props("flat dense no-caps")
                for key, label in groups[group_name]:
                    handler = (lambda: show_priority()) if key == "priority" else (
                        lambda _, selected=key: show_answer(selected))
                    ui.button(label, on_click=handler).props("flat no-caps icon-right=chevron_right").classes(
                        "consult-topic w-full")

        def render_groups():
            menu_area.clear()
            answer_area.clear()
            icons = {"今を知る": "monitor_heart", "未来を知る": "timeline",
                     "方法を比べる": "balance", "計画を作る": "event_note"}
            with menu_area:
                with ui.element("div").classes("consult-group-grid w-full"):
                    for name in groups:
                        with ui.button(on_click=lambda _, selected=name: show_group(selected)).props(
                            "flat no-caps").classes("consult-group"):
                            ui.icon(icons[name]).classes("text-2xl")
                            ui.label(name).classes("text-sm font-black")

        render_groups()
        with ui.expansion("この診断について", icon="info", value=False).classes(
            "consult-fold w-full q-mt-md"):
            ui.label("決算書と入力済みの数字だけで判断します。未入力の税金・返済・特別な支払いは安全判定に含めず、まだ分からないこととして表示します。").classes(
                "text-[10px] leading-relaxed")

        ui.add_css("""
        .period-chip{padding:5px 9px;border-radius:999px;background:#E8F1EC;color:#315F49;font-size:9px;font-weight:900}
        .owner-status{border:0!important;border-radius:25px!important;box-shadow:0 14px 34px rgba(45,55,48,.18)!important}
        .status-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.status-item{min-width:0;padding:11px;border-radius:15px}.status-item .q-label{overflow-wrap:anywhere}
        .consult-fold,.answer-fold{border-radius:16px!important;background:#fff!important;border:1px solid #E2E9E5!important}.consult-fold .q-item,.answer-fold .q-item{min-height:44px!important}
        .knowledge-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.knowledge-card{padding:11px;border-radius:14px}.knowledge-card.known{background:#EDF7F1}.knowledge-card.unknown{background:#F3F4F4}.unlock-card{padding:12px;border-radius:14px;background:#FFF5DC;border:1px solid #F1DFB0}
        .consult-group-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.consult-group{min-height:92px!important;border-radius:19px!important;background:#fff!important;border:1px solid #DDE7E1!important;color:#20382D!important;display:flex!important;flex-direction:column!important;gap:5px!important}
        .consult-topic{min-height:52px!important;border-radius:15px!important;background:#fff!important;border:1px solid #E1E8E4!important;color:#263C32!important;justify-content:space-between!important;margin-bottom:7px!important;padding:8px 12px!important}
        .consult-answer{border-radius:23px!important;border:1px solid #DCE8E1!important;background:linear-gradient(155deg,#fff,#F4F8F5)!important;box-shadow:0 14px 32px rgba(32,61,46,.09)!important}.answer-kicker{font-size:9px;font-weight:900;letter-spacing:.08em;color:#56806B}.answer-target{padding:10px 12px;border-radius:13px;background:#E4F2E9;color:#285941;font-size:11px;font-weight:900;margin-top:4px}
        """)
