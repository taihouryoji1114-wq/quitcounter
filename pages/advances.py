from nicegui import ui
from uuid import uuid4
from core.auth import require_app_access, require_permission, has_permission
from core.advances import advances
from core.clock import today_jst
from core.theme import Theme


@ui.page("/mirai-kessan/advances")
def advances_page():
    if not require_app_access("future_financials") or not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("立替管理｜未来決算", app_name="mirai-kessan")
    content = Theme.shell("立替管理", "誰がいくら立て替えたか、返ってきたか。仕入れ・損益とは独立しています。",
                          back_to="/mirai-kessan/dashboard", brand="未来決算")

    def save(action):
        if not has_permission("future_dashboard"):
            return
        try:
            action()
        except (ValueError, TypeError) as error:
            ui.notify(str(error), type="negative")
            return
        ui.navigate.to("/mirai-kessan/advances")

    with content:
        names = advances.names()
        paid, returned, remaining = advances.totals()
        with ui.card().classes("w-full q-pa-lg").style("background:#173D30;color:white;border-radius:22px"):
            ui.label("未返金 合計").classes("text-sm")
            ui.label(f"¥{sum(remaining):,}").classes("text-3xl font-bold")
            for i, name in enumerate(names):
                with ui.row().classes("w-full justify-between"):
                    ui.label(name)
                    ui.label(f"¥{remaining[i]:,}").classes("font-bold")
        with ui.expansion("月ごとの立替額を入力・修正", icon="edit", value=True).classes("w-full q-mt-md"):
            month = ui.input("対象月", value=today_jst().strftime("%Y-%m"),
                             on_change=lambda: fields.refresh()).props("type=month outlined")
            @ui.refreshable
            def fields():
                values = advances.state().get("months", {}).get(month.value, [0, 0, 0])
                inputs = [ui.number(name, value=values[i], min=0, precision=0).props("outlined dense prefix=¥ inputmode=numeric").classes("w-full") for i, name in enumerate(names)]
                ui.label("同じ月は追加ではなく上書きです。月の合計額を入力してください。").classes("text-xs text-grey-7")
                ui.button("この月の金額を保存", on_click=lambda: save(lambda: advances.save_month(month.value, [f.value for f in inputs]))).classes("w-full")
            fields()
        with ui.expansion("会社からの返金を記録", icon="payments").classes("w-full q-mt-sm"):
            refund_request_id = uuid4().hex
            day = ui.input("返金日", value=today_jst().isoformat()).props("type=date outlined")
            refunds = [ui.number(f"{name}へ返金", value=0, min=0, precision=0).props("outlined dense prefix=¥ inputmode=numeric").classes("w-full") for name in names]
            ui.button("返金を記録", on_click=lambda: save(lambda: advances.refund(day.value, [f.value for f in refunds], refund_request_id))).classes("w-full")
        with ui.expansion("履歴・修正・累計", icon="history", value=True).classes("w-full q-mt-sm"):
            for i, name in enumerate(names):
                ui.label(f"{name}：立替 ¥{paid[i]:,} ／ 返金 ¥{returned[i]:,}").classes("text-sm")
            with ui.column().classes("w-full").style("max-height:420px;overflow-y:auto"):
                for saved_month, amounts in sorted(advances.state().get("months", {}).items(), reverse=True):
                    ui.label(f"{saved_month} 立替　合計 ¥{sum(amounts):,}").classes("font-bold q-mt-sm")
                    ui.label(" ／ ".join(f"{names[i]} ¥{amounts[i]:,}" for i in range(3))).classes("text-xs")
                    def edit_month(_, target=saved_month):
                        with ui.dialog() as dialog, ui.card().classes("w-full max-w-sm"):
                            ui.label(f"{target}の立替額を修正").classes("text-lg font-bold")
                            current = advances.state().get("months", {}).get(target, [0, 0, 0])
                            edit_inputs = [ui.number(name, value=current[i], min=0, precision=0).props("outlined dense prefix=¥ inputmode=numeric").classes("w-full") for i, name in enumerate(names)]
                            ui.button("修正を保存", on_click=lambda: save(lambda: advances.save_month(target, [f.value for f in edit_inputs]))).classes("w-full")
                            ui.button("やめる", on_click=dialog.close).props("flat")
                        dialog.open()
                    ui.button("この立替額を修正", icon="edit", on_click=edit_month).props("outline dense")
                for record in reversed(advances.state().get("refunds", [])):
                    if record.get("voided"):
                        continue
                    ui.label(f"{record['day']} 返金　合計 ¥{sum(record['amounts']):,}").classes("font-bold q-mt-sm")
                    ui.label(" ／ ".join(f"{names[i]} ¥{record['amounts'][i]:,}" for i in range(3))).classes("text-xs")
                    def edit_refund(_, selected=record):
                        with ui.dialog() as dialog, ui.card().classes("w-full max-w-sm"):
                            ui.label("返金日・割り振り額を修正").classes("text-lg font-bold")
                            edit_day = ui.input("返金日", value=selected["day"]).props("outlined type=date")
                            edit_inputs = [ui.number(name, value=selected["amounts"][i], min=0, precision=0).props("outlined dense prefix=¥ inputmode=numeric").classes("w-full") for i, name in enumerate(names)]
                            ui.button("修正を保存", on_click=lambda: save(lambda: advances.update_refund(selected["id"], edit_day.value, [f.value for f in edit_inputs]))).classes("w-full")
                            ui.button("やめる", on_click=dialog.close).props("flat")
                        dialog.open()
                    ui.button("この返金を修正", icon="edit", on_click=edit_refund).props("outline dense")
                    def cancel(_, selected=record):
                        with ui.dialog() as dialog, ui.card():
                            ui.label("この返金記録を取り消しますか？未返金額に戻ります。")
                            ui.button("取り消す", on_click=lambda: save(lambda: advances.void_refund(selected["id"]))).props("color=negative")
                            ui.button("やめる", on_click=dialog.close).props("flat")
                        dialog.open()
                    ui.button("誤った返金を取り消す", on_click=cancel).props("flat dense color=negative")
        with ui.expansion("3人の名前を設定", icon="group").classes("w-full q-mt-sm"):
            labels = [ui.input(f"{i+1}人目", value=name).props("outlined dense").classes("w-full") for i, name in enumerate(names)]
            ui.label("名前を変更しても金額と履歴は引き継ぎます。").classes("text-xs")
            ui.button("名前を保存", on_click=lambda: save(lambda: advances.save_names([f.value for f in labels])))
