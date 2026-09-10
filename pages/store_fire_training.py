from datetime import datetime
from nicegui import ui
from core.auth import has_permission, require_app_access
from core.fire_training import COURSE_TITLE, COURSE_URL, fire_training
from core.staffing import staffing
from core.theme import Theme
from pages.store_common import store_header_actions

@ui.page("/store-ops/fire-training")
def store_fire_training_page():
    if not require_app_access("store_ops"): return
    Theme.page("消防訓練｜店舗運営",app_name="store-ops")
    content=Theme.shell("消防訓練","東京消防庁の公式教材で確認",back_to="/store-ops",action=store_header_actions,brand="店舗運営")
    records=fire_training.completions();can_manage=has_permission("store_manage")
    def reload(message=None):
        if message: ui.notify(message,type="positive")
        ui.navigate.to("/store-ops/fire-training")
    with content:
        with ui.card().classes("fire-hero w-full q-pa-lg"):
            with ui.row().classes("w-full items-center gap-3 no-wrap"):
                ui.icon("local_fire_department").classes("text-4xl text-red-7")
                with ui.column().classes("gap-0"):
                    ui.label("自衛消防活動要領").classes("text-xl font-black")
                    ui.label("出典：東京消防庁【電子学習室】").classes("text-xs text-grey-7")
            ui.label("火災発生時の通報・初期消火・避難誘導などを、公式教材で学びます。").classes("text-sm text-grey-8 leading-relaxed q-mt-md")
            ui.button("東京消防庁の教材を開く",icon="open_in_new",on_click=lambda:ui.run_javascript(f"window.open('{COURSE_URL}','_blank','noopener')")).props("unelevated no-caps").classes("training-open w-full q-mt-md")
            ui.label("公式ページが別画面で開きます。動画や内容は店舗アプリへ転載していません。").classes("text-[9px] text-grey-6 q-mt-xs")
        with ui.card().classes("w-full q-pa-lg q-mt-md"):
            ui.label("視聴後の受講記録").classes("text-lg font-black")
            ui.label("教材を最後まで確認した本人が記録してください。").classes("text-xs text-grey-6")
            staff=ui.select(list(staffing.STAFF),label="スタッフ名").props("outlined options-dense").classes("w-full q-mt-md")
            confirmed=ui.checkbox("東京消防庁の教材を確認しました").classes("text-sm q-mt-sm")
            def complete():
                if not confirmed.value:
                    ui.notify("教材を確認後、チェックを入れてください",type="warning");return
                try: fire_training.complete(staff.value)
                except ValueError as e: ui.notify(str(e),type="warning");return
                reload("受講完了を記録しました")
            ui.button("受講完了を記録",icon="verified",on_click=complete).props("unelevated no-caps").classes("w-full q-mt-sm")
        with ui.card().classes("w-full q-pa-lg q-mt-md"):
            ui.label(f"受講状況　{len(records)} / {len(staffing.STAFF)}人").classes("text-lg font-black")
            for name in staffing.STAFF:
                record=records.get(name)
                with ui.row().classes("w-full items-center no-wrap q-py-sm border-t border-grey-3"):
                    ui.icon("check_circle" if record else "radio_button_unchecked").classes("text-positive" if record else "text-grey-4")
                    ui.label(name).classes("text-sm font-bold grow")
                    if record:
                        value=datetime.fromisoformat(record["completed_at"])
                        ui.label(value.strftime("%Y/%m/%d %H:%M")).classes("text-[10px] text-grey-6")
                        if can_manage: ui.button(icon="delete_outline",on_click=lambda _,n=name:(fire_training.remove(n),reload("受講記録を取り消しました"))).props("flat round dense color=grey")
            if can_manage: ui.label("管理者・店長は誤登録を取り消せます。").classes("text-[9px] text-grey-6 q-mt-xs")
        ui.label("この教材視聴は日常教育の補助です。法令・消防計画上必要な実地訓練、届出、記録等の代わりになるとは限りません。").classes("training-caution w-full")
        ui.add_css("""body{background:#f3f1eb!important}.fire-hero{border-radius:25px!important;border:1px solid #ead8c2!important;background:linear-gradient(145deg,#fffaf2,#fff)!important;box-shadow:0 12px 30px rgba(77,51,29,.08)!important}.training-open{min-height:52px!important;border-radius:15px!important;background:#a9302d!important;font-weight:900!important}.training-caution{margin:15px 4px;color:#7a7167;font-size:9px;line-height:1.65}""")
