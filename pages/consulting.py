from nicegui import ui

from core.auth import require_login
from core.clock import today_jst
from core.consulting import consulting
from core.theme import Theme


@ui.page("/mirai-kessan/consulting")
def consulting_page():
    if not require_login():
        return
    Theme.page("経営コンサル｜未来決算", app_name="mirai-kessan")
    month = today_jst().strftime("%Y-%m")
    diagnosis = consulting.diagnose(month)
    content = Theme.shell(
        "経営コンサル", "数字を、今月の具体的な行動へ変える",
        back_to="/mirai-kessan/dashboard", brand="未来決算",
    )
    status_options = {
        "not_started": "未着手", "in_progress": "実行中", "completed": "完了",
    }
    with content:
        ui.label("今、一番知りたいことは？").classes("text-xl font-black q-mb-xs")
        ui.label("質問を選ぶと、今の数字から次の行動を出します").classes("text-[10px] text-grey-6 q-mb-sm")
        answer_area = ui.column().classes("w-full gap-0")

        def show_answer(key):
            answer = consulting.answer(month, key)
            answer_area.clear()
            with answer_area:
                with ui.card().classes("consult-answer w-full q-pa-lg q-mt-md"):
                    ui.label("結論").classes("answer-kicker")
                    ui.label(answer["conclusion"]).classes("text-xl font-black q-mb-sm")
                    ui.label(answer["reason"]).classes("text-xs leading-relaxed text-grey-7")
                    ui.separator().classes("q-my-md")
                    ui.label("次にやること").classes("answer-kicker")
                    for index, action in enumerate(answer["actions"], 1):
                        with ui.row().classes("w-full items-start no-wrap gap-2 q-mt-xs"):
                            ui.label(str(index)).classes("mini-number")
                            ui.label(action).classes("text-xs leading-relaxed")
                    ui.label("改善目標").classes("answer-kicker q-mt-md")
                    ui.label(answer["target"]).classes("answer-target")

        with ui.element("div").classes("consult-question-grid w-full"):
            for key, label in consulting.QUESTIONS:
                ui.button(label, on_click=lambda _, selected=key: show_answer(selected)).props(
                    "flat no-caps"
                ).classes("consult-question")

        with ui.expansion("自動診断と行動管理", icon="assignment", value=False).classes(
            "consult-info w-full q-mt-md"
        ):
            primary = diagnosis["primary"]
            with ui.card().classes("consult-hero w-full q-pa-lg q-mb-md text-white"):
                ui.label("今月の最優先").classes("text-[10px] opacity-70")
                ui.label(primary["title"]).classes("text-xl font-black q-mt-xs")
                ui.label(primary["why"]).classes("text-xs leading-relaxed opacity-85 q-mt-sm")
            for index, item in enumerate(diagnosis["recommendations"][:5], 1):
                with ui.card().classes("consult-action w-full q-pa-md q-mb-sm"):
                    ui.label(f"{index}. {item['title']}").classes("text-sm font-black")
                    ui.label(item["action"]).classes("text-[10px] leading-relaxed q-mt-xs")
                    status = ui.select(status_options, value=item["status"], label="進捗").props(
                        "outlined dense options-dense").classes("w-full q-mt-sm")
                    note = ui.input("実行メモ", value=item["note"]).props("outlined dense").classes("w-full q-mt-xs")

                    def save(_, action=item, status_field=status, note_field=note):
                        consulting.save_item(month, action["key"], status_field.value, note_field.value)
                        ui.notify("行動記録を保存しました", type="positive")
                    ui.button("記録する", icon="check", on_click=save).props("flat dense no-caps").classes("self-end")

        with ui.expansion("判断の前提", icon="info", value=False).classes(
            "consult-info w-full q-mt-sm"
        ):
            ui.label(
                "決算書の財務安全性を優先し、次に今月の営業利益・原価率・人件費率を確認しています。"
                "参考値は絶対的な合否ではなく、行動の優先順位を決める目安です。"
            ).classes("text-[10px] leading-relaxed")
        ui.add_css("""
        .consult-question-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.consult-question{min-height:58px!important;border-radius:17px!important;background:#fff!important;border:1px solid #DDE7E1!important;color:#20382D!important;font-size:12px!important;font-weight:800!important;line-height:1.25!important;padding:8px!important}.consult-answer{border-radius:25px!important;border:1px solid #DCE8E1!important;background:linear-gradient(155deg,#fff,#F4F8F5)!important;box-shadow:0 16px 38px rgba(32,61,46,.1)!important}.answer-kicker{font-size:9px;font-weight:900;letter-spacing:.12em;color:#56806B}.answer-target{padding:10px 12px;border-radius:13px;background:#E4F2E9;color:#285941;font-size:12px;font-weight:900}.mini-number{width:22px;height:22px;display:flex;align-items:center;justify-content:center;flex:none;border-radius:50%;background:#315F49;color:#fff;font-size:9px;font-weight:900}.consult-hero{border-radius:22px!important;border:0!important;background:linear-gradient(145deg,#173D30,#765225)!important}.consult-action{border-radius:18px!important;border:1px solid #E2E9E5!important;box-shadow:none!important}.consult-info{border-radius:18px!important;background:#fff!important;border:1px solid #E4E9E6!important}
        """)
