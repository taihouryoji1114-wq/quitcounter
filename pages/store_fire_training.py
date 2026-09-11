from datetime import datetime
from nicegui import ui
from core.auth import has_permission, require_app_access
from core.fire_training import CHECK_ITEMS, COURSE_URL, STORE_FIELDS, fire_training
from core.staffing import staffing
from core.theme import Theme
from pages.store_common import store_header_actions

STORE_ID = "default"
STEPS = [
    ("local_fire_department", "火災を発見", "danger"), ("campaign", "周囲に知らせる", "warn"),
    ("phone_in_talk", "119番通報", "info"), ("fire_extinguisher", "安全なら初期消火", "warn"),
    ("directions_run", "お客様を避難誘導", "safe"), ("door_front", "火・煙の拡大を防ぐ", "warn"),
    ("fire_truck", "消防隊へ状況を伝える", "info"),
]
DETAILS = [
    ("1", "火災を発見したら", "local_fire_department", [
        "火や煙を発見したら『火事です！』と大きな声で周囲に知らせる",
        "自動火災報知設備が作動したら、誤報と決めつけず火災か確認する",
        "火災を確認したら、責任者の許可を待たず速やかに119番通報する",
        "発信機や放送設備がある場合は、建物内にも火災を知らせる",
    ], "『店長の確認を待ってから119番』ではない"),
    ("2", "119番通報", "phone_in_talk", [
        "消防から聞かれたことに、落ち着いて答える",
        "火災であること／店舗名／店舗住所",
        "出火場所／燃えている物／火や煙の状況",
        "けが人・逃げ遅れた人の有無",
        "携帯電話からも119番通報できる",
    ], "分からない項目は推測せず、分かる範囲を正確に伝える"),
    ("3", "初期消火", "fire_extinguisher", [
        "① 安全栓を抜く　② ホースを火元に向ける　③ レバーを握る",
        "炎ではなく、燃えている物・火元を狙う",
        "必ず避難経路を背にして、逃げ道を確保する",
        "炎が天井まで達した、室内全体へ広がった、煙が強い場合は中止する",
    ], "消火より命を優先する"),
    ("4", "お客様の避難誘導", "directions_run", [
        "『火災です。こちらから避難してください』と大きな声で方向を示す",
        "安全な避難経路を使い、エレベーターは使用しない",
        "曲がり角や分かれ道で、避難方向を明確にする",
        "逃げ遅れた人がいないか確認し、可能なら最後に扉・防火戸を閉める",
    ], "煙を避け、安全な出口へ迷わせず誘導する"),
    ("5", "火と煙を広げない", "door_front", [
        "避難時、安全を確認したうえで扉を閉める",
        "普通の扉でも炎や煙の拡大を遅らせる効果がある",
        "防火戸・防火シャッターがある場合は活用する",
        "避難中の人を閉じ込めないよう、スタッフ同士で連絡する",
    ], "区画を作る前に、人が残っていないか連携して確認"),
    ("6", "消防隊が到着したら", "fire_truck", [
        "火災情報：出火場所、燃えている物、延焼・煙の広がり",
        "人の情報：けが人、逃げ遅れ、避難状況、可能性のある場所",
        "消火活動：初期消火の結果、使用設備、防火戸等の状況",
    ], "入口で待ち、消防隊を安全に案内して情報をまとめて伝える"),
]
PROFILE_LABELS = {
    "store_name": "店舗名", "address": "店舗住所", "phone": "店舗電話番号",
    "extinguisher": "消火器の場所", "emergency_exit": "非常口の場所",
    "evacuation_route": "避難経路", "fire_door": "防火戸の場所",
    "fire_equipment": "消防設備の場所", "assembly_point": "集合場所",
}

@ui.page("/store-ops/fire-training")
def store_fire_training_page():
    if not require_app_access("store_ops"): return
    Theme.page("消防訓練｜店舗運営", app_name="store-ops")
    can_manage = has_permission("store_manage")
    settings = fire_training.store_settings(STORE_ID)
    profile, records = settings["profile"], fire_training.completions()
    content = Theme.shell("消防訓練", "火災時に迷わず動くために", back_to="/store-ops",
                          action=store_header_actions, brand="店舗運営")
    def reload(message=None):
        if message: ui.notify(message, type="positive")
        ui.navigate.to("/store-ops/fire-training")

    with content:
        with ui.card().classes("fire-flow w-full q-pa-lg"):
            with ui.row().classes("w-full items-center gap-2 no-wrap"):
                ui.icon("emergency").classes("text-2xl text-red-7")
                with ui.column().classes("gap-0"):
                    ui.label("火災発生時の基本行動").classes("text-xl font-black")
                    ui.label("最初に、この順番を思い出す").classes("text-[10px] text-grey-6")
            with ui.column().classes("fire-step-list w-full gap-0 q-mt-md"):
                for index, (icon, label, tone) in enumerate(STEPS):
                    with ui.row().classes(f"fire-step {tone} w-full items-center no-wrap"):
                        ui.label(str(index + 1)).classes("fire-step-number")
                        ui.icon(icon).classes("fire-step-icon")
                        ui.label(label).classes("fire-step-label")
                    if index < len(STEPS) - 1: ui.icon("south").classes("fire-arrow")

        configured = [(PROFILE_LABELS[key], value) for key, value in profile.items() if value]
        with ui.card().classes("store-fire-info w-full q-pa-lg q-mt-md"):
            with ui.row().classes("w-full items-center gap-2"):
                ui.icon("storefront").classes("text-2xl text-blue-8")
                ui.label("この店舗の緊急情報").classes("text-lg font-black")
            if configured:
                for label, value in configured:
                    with ui.row().classes("store-info-row w-full items-start no-wrap"):
                        ui.label(label).classes("store-info-label")
                        ui.label(value).classes("store-info-value")
            else:
                ui.label("店舗情報はまだ設定されていません").classes("text-sm text-grey-6 q-mt-sm")
                if can_manage: ui.label("下の管理者設定から住所・非常口・避難経路などを登録してください。").classes("text-[10px] text-grey-6")

        ui.label("行動を詳しく確認").classes("section-label w-full")
        for number, title, icon, bullets, key_message in DETAILS:
            with ui.expansion(f"{number}. {title}", icon=icon, value=False).props("duration=140").classes("fire-detail w-full q-mb-sm"):
                with ui.column().classes("w-full gap-2 q-px-md q-pb-md"):
                    if number == "6":
                        for bullet in bullets:
                            group, copy = bullet.split("：", 1)
                            with ui.card().classes("report-group w-full q-pa-md"):
                                ui.label(group).classes("report-group-title")
                                ui.label(copy).classes("detail-copy")
                    else:
                        for bullet in bullets:
                            with ui.row().classes("detail-line w-full items-start no-wrap"):
                                ui.icon("circle").classes("detail-dot")
                                ui.label(bullet).classes("detail-copy")
                    ui.label(key_message).classes("life-first" if number == "3" else "key-message")

        with ui.card().classes("role-card w-full q-pa-lg q-mt-md"):
            ui.label("火災時の役割分担").classes("text-lg font-black")
            ui.label("営業人数を選ぶと、設定された役割を確認できます").classes("text-[10px] text-grey-6")
            with ui.tabs().classes("role-tabs w-full q-mt-sm") as tabs:
                for count in (3, 4, 5): ui.tab(str(count), label=f"{count}人営業")
            with ui.tab_panels(tabs, value="3").classes("role-panels w-full"):
                for count in (3, 4, 5):
                    with ui.tab_panel(str(count)):
                        for index, row in enumerate(settings["role_plans"][str(count)], 1):
                            with ui.row().classes("role-row w-full items-start no-wrap"):
                                ui.label(chr(64 + index)).classes("role-person")
                                with ui.column().classes("gap-0 grow"):
                                    ui.label(row["role"]).classes("text-sm font-black")
                                    ui.label(row["detail"]).classes("text-[10px] text-grey-6")

        with ui.card().classes("check-card w-full q-pa-lg q-mt-md"):
            ui.label("自分の店舗で確認する").classes("text-lg font-black")
            checked_count = sum(settings["checklist"].values())
            check_state = dict(settings["checklist"])
            check_progress = ui.label(f"店舗確認　{checked_count} / {len(CHECK_ITEMS)}").classes("check-progress")
            def update_check(item_id, checked):
                fire_training.set_check(item_id, checked, STORE_ID)
                check_state[item_id] = bool(checked)
                check_progress.set_text(f"店舗確認　{sum(check_state.values())} / {len(CHECK_ITEMS)}")
            for item_id, label in CHECK_ITEMS:
                box = ui.checkbox(label, value=settings["checklist"][item_id]).classes("store-check w-full")
                if can_manage: box.on_value_change(lambda event, key=item_id: update_check(key, event.value))
                else: box.disable()
            ui.label("チェック状態はスタッフ別ではなく、店舗全体で共有されます。").classes("text-[9px] text-grey-6 q-mt-xs")

        with ui.expansion("東京消防庁の公式教材・受講記録", icon="verified_user", value=False).classes("official-training w-full q-mt-md"):
            with ui.column().classes("w-full q-pa-md gap-2"):
                ui.label("参考：東京消防庁 自衛消防活動要領").classes("text-sm font-black")
                ui.button("公式教材を開く", icon="open_in_new", on_click=lambda: ui.run_javascript(f"window.open('{COURSE_URL}','_blank','noopener')")).props("outline no-caps").classes("w-full")
                staff = ui.select(list(staffing.STAFF), label="受講したスタッフ名").props("outlined options-dense").classes("w-full")
                confirmed = ui.checkbox("公式教材を最後まで確認しました")
                def complete():
                    if not confirmed.value:
                        ui.notify("教材を確認後、チェックを入れてください", type="warning"); return
                    try: fire_training.complete(staff.value)
                    except ValueError as error: ui.notify(str(error), type="warning"); return
                    reload("受講完了を記録しました")
                ui.button("受講完了を記録", icon="verified", on_click=complete).props("unelevated no-caps").classes("w-full")
                ui.label(f"受講状況　{len(records)} / {len(staffing.STAFF)}人").classes("text-sm font-black q-mt-sm")
                for name in staffing.STAFF:
                    record = records.get(name)
                    with ui.row().classes("training-row w-full items-center no-wrap"):
                        ui.icon("check_circle" if record else "radio_button_unchecked").classes("text-positive" if record else "text-grey-4")
                        ui.label(name).classes("text-xs font-bold grow")
                        if record:
                            ui.label(datetime.fromisoformat(record["completed_at"]).strftime("%Y/%m/%d %H:%M")).classes("text-[9px] text-grey-6")
                            if can_manage: ui.button(icon="delete_outline", on_click=lambda _, n=name: (fire_training.remove(n), reload("受講記録を取り消しました"))).props("flat round dense color=grey")

        if can_manage:
            with ui.expansion("管理者設定", icon="settings", value=False).classes("fire-admin w-full q-mt-md"):
                with ui.column().classes("w-full q-pa-md gap-2"):
                    ui.label("店舗専用情報").classes("text-base font-black")
                    fields = {key: ui.input(PROFILE_LABELS[key], value=profile[key]).props("outlined dense maxlength=300").classes("w-full") for key in STORE_FIELDS}
                    def save_profile():
                        fire_training.save_profile({key: field.value for key, field in fields.items()}, STORE_ID)
                        reload("店舗の消防情報を保存しました")
                    ui.button("店舗情報を保存", icon="save", on_click=save_profile).props("unelevated no-caps").classes("w-full")
                    ui.separator().classes("q-my-md")
                    ui.label("人数別の役割設定").classes("text-base font-black")
                    ui.label("役割名と行動内容を店舗に合わせて変更できます。").classes("text-[10px] text-grey-6")
                    for count in (3, 4, 5):
                        rows = settings["role_plans"][str(count)]
                        with ui.expansion(f"{count}人営業の役割", value=False).classes("w-full"):
                            role_fields = []
                            for index, row in enumerate(rows, 1):
                                with ui.row().classes("w-full gap-2 no-wrap"):
                                    role = ui.input(f"{chr(64+index)} 役割", value=row["role"]).props("outlined dense").classes("w-2/5")
                                    detail = ui.input("行動内容", value=row["detail"]).props("outlined dense").classes("grow")
                                    role_fields.append((role, detail))
                            def save_roles(current=count, inputs=role_fields):
                                try: fire_training.save_role_plan(current, [{"role": r.value, "detail": d.value} for r, d in inputs], STORE_ID)
                                except ValueError as error:
                                    ui.notify(str(error), type="warning"); return
                                reload(f"{current}人営業の役割を保存しました")
                            ui.button("役割を保存", icon="save", on_click=save_roles).props("unelevated no-caps dense").classes("w-full")

        ui.label("このマニュアルは日常教育と緊急時確認の補助です。店舗の消防計画、建物設備、所轄消防署の指導を優先してください。必要な実地訓練・届出の代わりにはなりません。").classes("training-caution w-full")
        ui.add_css("""
        body{background:#f3f2ed!important}.fire-flow,.store-fire-info,.role-card,.check-card{border-radius:24px!important;border:1px solid #e5e5df!important;box-shadow:0 10px 25px rgba(38,49,43,.07)!important}.fire-flow{background:linear-gradient(145deg,#fff,#fffaf6)!important}.fire-step-list{align-items:stretch}.fire-step{min-height:51px;padding:7px 12px;border-radius:14px;border:1px solid #ecebe6;background:#fff}.fire-step-number{display:grid;place-items:center;width:25px;height:25px;border-radius:50%;background:#f0f1ef;color:#59635d;font-size:10px;font-weight:950}.fire-step-icon{font-size:21px;margin:0 11px}.fire-step-label{font-size:14px;font-weight:950}.fire-step.danger .fire-step-icon{color:#c73e38}.fire-step.warn .fire-step-icon{color:#d6862b}.fire-step.info .fire-step-icon{color:#2978a7}.fire-step.safe .fire-step-icon{color:#278354}.fire-arrow{align-self:center;color:#a9aea9;font-size:16px;margin:1px 0}.section-label{margin:22px 4px 9px;color:#385245;font-size:12px;font-weight:950}.fire-detail{border-radius:17px!important;border:1px solid #e1e5e1!important;background:#fff!important}.fire-detail>.q-expansion-item__container>.q-item{min-height:57px!important;font-size:14px;font-weight:950}.detail-line{gap:9px}.detail-dot{font-size:6px!important;color:#d16942;margin-top:7px}.detail-copy{font-size:12px;line-height:1.65;color:#35433c;overflow-wrap:anywhere}.report-group{border-radius:12px!important;border:1px solid #dce7ec!important;box-shadow:none!important;background:#f6fafc!important}.report-group-title{margin-bottom:4px;color:#28749d;font-size:10px;font-weight:950}.key-message,.life-first{width:100%;padding:11px 13px;border-radius:11px;font-size:11px;font-weight:950}.key-message{color:#824a0b;background:#fff3db;border-left:4px solid #e6a33e}.life-first{color:#9f2926;background:#fff0ef;border:1px solid #f1c0bd;text-align:center;font-size:14px}.store-fire-info{background:linear-gradient(145deg,#f5fbff,#fff)!important}.store-info-row{padding:8px 0;border-top:1px solid #e7edf0}.store-info-label{width:34%;font-size:9px;font-weight:850;color:#63757e}.store-info-value{font-size:12px;font-weight:850;white-space:pre-wrap;overflow-wrap:anywhere}.role-tabs{color:#426153}.role-panels{padding:0!important;background:transparent!important}.role-row{padding:9px 0;border-bottom:1px solid #eceeea}.role-person{display:grid;place-items:center;flex:0 0 28px;height:28px;border-radius:8px;background:#264d3b;color:#fff;font-weight:950}.check-progress{color:#277753;font-size:11px;font-weight:900;margin:4px 0 8px}.store-check{padding:6px 0;border-top:1px solid #eceeea;font-size:12px}.official-training,.fire-admin{border:1px solid #dfe4e0!important;border-radius:17px!important;background:#fff!important}.training-row{padding:5px 0;border-top:1px solid #eee}.training-caution{margin:17px 4px;color:#746f68;font-size:9px;line-height:1.7}@media(max-width:420px){.fire-step{min-height:48px}.fire-step-label{font-size:13px}.detail-copy{font-size:11px}.store-info-label{width:38%}}
        """)
