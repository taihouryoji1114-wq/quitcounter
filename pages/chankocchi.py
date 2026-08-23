from nicegui import ui

from core.auth import require_app_access, selected_user_id
from core.chankocchi import (ACTIONS, affection_label, can_depart, care,
                             claim_store_reward, has_store_activity, initial_profile,
                             next_stage_progress, normalize_profile,
                             stage_info, start_next_generation)
from core.clock import today_jst_string
from core.data import data
from core.theme import Theme


@ui.page("/chankocchi")
def chankocchi_page():
    if not require_app_access("chankocchi"):
        return
    Theme.page("ちゃんこっち", app_name="chankocchi")
    user_id = selected_user_id()
    profiles = data.data.setdefault("chankocchi", {}).setdefault("profiles", {})
    profile = profiles.setdefault(user_id, initial_profile())
    normalize_profile(profile)
    data.save()
    state = {"speech": profile.get("last_speech", "おかえり！")}

    def save():
        profiles[user_id] = profile
        data.save()

    def do_care(action):
        result = care(profile, action, today_jst_string())
        state["speech"] = result["speech"]
        save()
        if not result["gained"]:
            ui.notify("今日はもう仲良しポイントを受け取ったお世話です", type="info")
        render.refresh()

    def store_reward():
        if not has_store_activity(data.data, today_jst_string()):
            ui.notify("店舗の今日のチェックを1つ終えると受け取れます", type="info")
            return
        try:
            claim_store_reward(profile, today_jst_string())
            state["speech"] = profile["last_speech"]
            save()
            ui.notify("店舗コインを10枚受け取りました", type="positive")
            render.refresh()
        except ValueError as error:
            ui.notify(str(error), type="warning")

    def next_generation():
        try:
            start_next_generation(profile)
            state["speech"] = profile["last_speech"]
            save()
            render.refresh()
        except ValueError as error:
            ui.notify(str(error), type="warning")

    @ui.refreshable
    def render():
        stage = stage_info(profile)
        progress, progress_label = next_stage_progress(profile)
        today_claimed = today_jst_string() in profile.get("store_reward_dates", [])
        store_done = has_store_activity(data.data, today_jst_string())
        with ui.element("main").classes("chanko-app"):
            with ui.row().classes("chanko-top w-full items-center no-wrap"):
                with ui.column().classes("gap-0 grow"):
                    ui.label("ちゃんこっち").classes("chanko-logo")
                    ui.label(f"{profile['generation']}代目・{stage['name']}").classes("chanko-sub")
                ui.label(f"🪙 {profile['coins']}").classes("coin-pill")

            with ui.element("section").classes("life-room"):
                with ui.element("div").classes("speech-bubble"):
                    ui.label(state["speech"])
                ui.image("/static/chankocchi_stage1.png").classes("chanko-character")
                ui.label(affection_label(profile["affection"])).classes("affection-tag")

            with ui.element("div").classes("meter-grid"):
                meter_labels = {"hunger": "おなか", "cleanliness": "きれい", "energy": "元気", "joy": "ごきげん"}
                for key, label in meter_labels.items():
                    with ui.element("div").classes("meter-card"):
                        ui.label(label)
                        ui.linear_progress(profile["meters"][key] / 100).props("rounded color=amber-7")

            ui.label("お世話する").classes("section-title")
            with ui.element("div").classes("care-grid"):
                icons = {"meal": "restaurant", "play": "sports_esports", "bath": "water_drop", "rest": "bedtime"}
                for action, rule in ACTIONS.items():
                    ui.button(rule["label"], icon=icons[action],
                              on_click=lambda _, value=action: do_care(value)).props(
                                  "flat no-caps").classes("care-button")

            with ui.card().classes("growth-card w-full"):
                with ui.row().classes("w-full items-center no-wrap"):
                    with ui.column().classes("gap-0 grow"):
                        ui.label("成長のきろく").classes("font-black")
                        ui.label(f"なつき度 {profile['affection']}・{progress_label}").classes("text-xs text-grey-6")
                    ui.label("ちゃんタマあり" if profile.get("egg_ready") else "成長中").classes(
                        "egg-chip" if profile.get("egg_ready") else "growing-chip")
                ui.linear_progress(progress).props("rounded color=deep-orange-5").classes("q-mt-sm")

            with ui.card().classes("store-link w-full"):
                with ui.row().classes("w-full items-center no-wrap"):
                    ui.icon("storefront").classes("text-2xl")
                    with ui.column().classes("gap-0 grow"):
                        ui.label("今日のお仕事").classes("font-black")
                        ui.label("店舗で頑張ったごほうび").classes("text-xs opacity-80")
                    reward_label = "受取済" if today_claimed else "+10枚" if store_done else "チェック後"
                    ui.button(reward_label, on_click=store_reward).props(
                        "unelevated no-caps").classes("store-reward").set_enabled(not today_claimed)
                ui.button("店舗運営を開く", icon="arrow_forward", on_click=lambda: ui.navigate.to("/store-ops")).props(
                    "flat no-caps").classes("w-full q-mt-sm")

            if can_depart(profile):
                with ui.card().classes("farewell-card w-full"):
                    ui.label("次の命へ").classes("text-lg font-black")
                    ui.label("大切に育てた記録を家系に残して、ちゃんタマを迎えられます。")
                    ui.button("次の世代を迎える", on_click=next_generation).props(
                        "unelevated no-caps color=deep-orange-7").classes("w-full q-mt-sm")

            history = profile.get("history", [])
            with ui.expansion(f"家系のきろく　{len(history)}代", icon="family_restroom",
                              value=False).classes("history-panel w-full"):
                if not history:
                    ui.label("最初の一代を、一緒に育てています。 ").classes("text-grey-6")
                for item in reversed(history):
                    ui.label(f"{item['generation']}代目　{item['stage']}　なつき度{item['affection']}").classes(
                        "history-row")

        ui.add_css("""
        .chanko-app{min-height:100vh;width:min(100%,680px);margin:0 auto;padding:20px 18px 54px;background:linear-gradient(180deg,#FFF8E8,#F6E7CD 45%,#E7D1AE);box-sizing:border-box}.chanko-top{padding:2px 3px 14px}.chanko-logo{font-size:28px;font-weight:950;color:#3C2D24}.chanko-sub{font-size:11px;font-weight:800;color:#8A6F59}.coin-pill{padding:8px 13px;border-radius:999px;background:#3C2D24;color:#FFD980;font-weight:900}.life-room{position:relative;min-height:390px;border-radius:34px;overflow:hidden;background:radial-gradient(circle at 50% 32%,rgba(255,250,223,.95),rgba(232,193,137,.82) 58%,#A96F45 130%);border:1px solid rgba(115,72,43,.16);box-shadow:0 18px 44px rgba(95,61,37,.18);display:flex;align-items:flex-end;justify-content:center}.life-room:before{content:'';position:absolute;inset:auto 0 0;height:29%;background:linear-gradient(180deg,#C79662,#95613E);border-top:4px solid rgba(255,255,255,.28)}.chanko-character{position:relative;width:min(88%,370px);z-index:2;filter:drop-shadow(0 18px 14px rgba(67,42,25,.25));animation:chanko-breathe 3.4s ease-in-out infinite}.speech-bubble{position:absolute;z-index:3;top:18px;left:18px;right:18px;padding:13px 16px;border-radius:20px 20px 20px 5px;background:rgba(255,255,255,.92);font-size:13px;font-weight:850;color:#46352A;box-shadow:0 7px 20px rgba(65,42,26,.12)}.affection-tag{position:absolute;z-index:3;right:16px;bottom:15px;padding:7px 11px;border-radius:999px;background:rgba(76,48,36,.86);color:#FFF4DC;font-size:10px;font-weight:900}.meter-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:12px 0 18px}.meter-card{padding:9px 8px;border-radius:14px;background:rgba(255,255,255,.72);font-size:9px;font-weight:900;color:#725945}.section-title{font-size:17px;font-weight:950;color:#46352A;margin:2px 2px 9px}.care-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}.care-button{background:rgba(255,255,255,.9)!important;color:#543E30!important;border:1px solid rgba(121,86,59,.15)!important;min-height:54px!important;border-radius:17px!important}.growth-card,.store-link,.farewell-card{margin-top:12px;padding:16px!important;border-radius:22px!important;border:1px solid rgba(120,81,51,.13)!important;box-shadow:0 9px 24px rgba(93,61,39,.08)!important}.egg-chip,.growing-chip{font-size:9px;font-weight:900;padding:6px 9px;border-radius:999px}.egg-chip{background:#FFE1A1;color:#80510B}.growing-chip{background:#E8EFEA;color:#52685A}.store-link{background:linear-gradient(135deg,#284E3E,#4E8064)!important;color:white!important}.store-reward{background:#FFE09A!important;color:#5C421B!important}.farewell-card{background:linear-gradient(145deg,#FFF2E2,#FFE0D3)!important}.history-panel{margin-top:12px;border-radius:20px!important;background:rgba(255,255,255,.72)}.history-row{padding:8px 0;border-bottom:1px solid rgba(100,70,50,.12);font-weight:800}@keyframes chanko-breathe{0%,100%{transform:translateY(0) rotate(-.4deg)}50%{transform:translateY(-7px) rotate(.5deg)}}@media(max-width:380px){.life-room{min-height:350px}.meter-grid{grid-template-columns:repeat(2,1fr)}}
        """)

    render()
