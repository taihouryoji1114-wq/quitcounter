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
        primary = diagnosis["primary"]
        with ui.card().classes("consult-hero w-full q-pa-lg q-mb-md text-white"):
            ui.label("今月の最優先").classes("text-[10px] opacity-70")
            ui.label(primary["title"]).classes("text-2xl font-black q-mt-xs")
            ui.label(primary["why"]).classes("text-xs leading-relaxed opacity-85 q-mt-sm")
            with ui.row().classes("w-full items-center justify-between q-mt-md no-wrap"):
                ui.label(primary["target"]).classes("text-xs font-bold")
                ui.label(primary["deadline"]).classes("deadline-badge")

        ui.label("今月の実行プラン").classes("text-lg font-black q-mb-sm")
        for index, item in enumerate(diagnosis["recommendations"][:5], 1):
            with ui.card().classes("consult-action w-full q-pa-md q-mb-sm"):
                with ui.row().classes("w-full items-start no-wrap"):
                    ui.label(str(index)).classes("consult-number")
                    with ui.column().classes("gap-0 min-w-0 grow"):
                        ui.label(item["title"]).classes("text-sm font-black")
                        ui.label(item["action"]).classes("text-[10px] leading-relaxed q-mt-xs")
                        with ui.row().classes("w-full items-center gap-2 q-mt-sm"):
                            ui.label(item["target"]).classes("target-chip")
                            ui.label(item["deadline"]).classes("deadline-chip")
                        status = ui.select(
                            status_options, value=item["status"], label="進捗"
                        ).props("outlined dense options-dense").classes("w-full q-mt-sm")
                        note = ui.input(
                            "実行メモ", value=item["note"]
                        ).props("outlined dense").classes("w-full q-mt-xs")

                        def save(_, action=item, status_field=status, note_field=note):
                            consulting.save_item(
                                month, action["key"], status_field.value, note_field.value
                            )
                            ui.notify("行動記録を保存しました", type="positive")

                        ui.button("記録する", icon="check", on_click=save).props(
                            "flat dense no-caps"
                        ).classes("self-end q-mt-xs")

        with ui.expansion("判断の前提", icon="info", value=False).classes(
            "consult-info w-full q-mt-sm"
        ):
            ui.label(
                "決算書の財務安全性を優先し、次に今月の営業利益・原価率・人件費率を確認しています。"
                "参考値は絶対的な合否ではなく、行動の優先順位を決める目安です。"
            ).classes("text-[10px] leading-relaxed")
        ui.add_css("""
        .consult-hero{border-radius:28px!important;border:0!important;background:radial-gradient(circle at 90% 10%,rgba(226,176,91,.4),transparent 34%),linear-gradient(145deg,#173D30,#765225)!important;box-shadow:0 18px 40px rgba(30,60,45,.2)!important}.deadline-badge{padding:6px 10px;border-radius:999px;background:rgba(255,255,255,.15);font-size:9px}.consult-action{border-radius:20px!important;border:1px solid #E2E9E5!important;box-shadow:0 7px 20px rgba(35,57,45,.05)!important}.consult-number{width:30px;height:30px;display:flex;align-items:center;justify-content:center;flex:none;border-radius:50%;background:#EAF3EE;color:#376B53;font-weight:900}.target-chip,.deadline-chip{font-size:8px;padding:5px 8px;border-radius:999px;background:#EDF5F0;color:#34664F;max-width:65%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.deadline-chip{background:#FFF3DF;color:#885B1C}.consult-info{border-radius:18px!important;background:#fff!important;border:1px solid #E4E9E6!important}
        """)
