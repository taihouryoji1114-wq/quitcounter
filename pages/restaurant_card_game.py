from nicegui import ui

from core.auth import require_app_access, selected_user_id
from core.data import data
from core.restaurant_card_game import (POSITIONS, STAFF_POOL, card, draw_gacha,
                                       effective_ability, initial_profile, level_up,
                                       open_branch, open_office, promote_manager,
                                       run_business)
from core.theme import Theme


@ui.page("/restaurant-card-game")
def restaurant_card_game_page():
    if not require_app_access("restaurant_card_game"):
        return
    Theme.page("一生懸命！飲食店経営", app_name="restaurant-card-game")
    user_id = selected_user_id()
    profiles = data.data.setdefault("restaurant_card_game", {}).setdefault("profiles", {})
    profile = profiles.setdefault(user_id, initial_profile())
    for key, value in initial_profile().items():
        profile.setdefault(key, value)
    state = {"screen": "home", "last_draw": None}

    def save():
        profiles[user_id] = profile
        data.save()

    def money(value):
        return f"¥{int(value):,}"

    def go(screen):
        state["screen"] = screen
        render.refresh()

    def assign(position, value):
        profile["assignments"][position] = value or ""
        save()
        render.refresh()

    def business():
        run_business(profile)
        save()
        render.refresh()

    def gacha():
        try:
            state["last_draw"] = draw_gacha(profile)
            save()
            render.refresh()
        except ValueError as error:
            ui.notify(str(error), type="warning")

    def upgrade(card_id):
        try:
            level_up(profile, card_id)
            save()
            ui.notify("レベルアップ！", type="positive")
            render.refresh()
        except ValueError as error:
            ui.notify(str(error), type="warning")

    def make_manager(card_id):
        try:
            promote_manager(profile, card_id)
            save()
            ui.notify(f"{card(card_id)['name']}を店長に昇格しました", type="positive")
            render.refresh()
        except ValueError as error:
            ui.notify(str(error), type="warning")

    def build_office():
        try:
            open_office(profile)
            save()
            ui.notify("事務所を開設しました", type="positive")
            render.refresh()
        except ValueError as error:
            ui.notify(str(error), type="warning")

    def build_branch(branch_id):
        try:
            open_branch(profile, branch_id)
            save()
            ui.notify("新しい支店が開業しました", type="positive")
            render.refresh()
        except ValueError as error:
            ui.notify(str(error), type="warning")

    def staff_tile(card_id, compact=False):
        info = card(card_id)
        owned = profile["owned"].get(card_id, {})
        classes = "rg-staff-card compact" if compact else "rg-staff-card"
        with ui.card().classes(classes):
            if card_id == "yamada":
                ui.image("/static/restaurant_card_yamada.jpg").classes("rg-card-art")
            else:
                with ui.element("div").classes(f"rg-card-art rg-art-{info['rarity'].lower()}"):
                    ui.icon("person").classes("text-5xl")
                    ui.label(info["skill"]).classes("rg-art-skill")
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                ui.label(info["rarity"]).classes(f"rarity {info['rarity'].lower()}")
                ui.label(info["name"]).classes("font-black grow")
                ui.label(f"Lv.{owned.get('level', 1)}").classes("text-xs font-black")
            if profile.get("manager_id") == card_id:
                ui.badge("店長", color="deep-orange-9").classes("q-mb-xs")
            with ui.row().classes("w-full justify-between rg-stats"):
                for key in POSITIONS:
                    ui.label(f"{key} {effective_ability(profile, card_id, key)}")
            ui.label(info["effect"]).classes("text-[10px] text-grey-7")
            if not compact:
                xp = int(owned.get("xp", 0))
                need = int(owned.get("level", 1)) * 40
                ui.linear_progress(min(1, xp / need), show_value=False).props("rounded color=amber-7")
                with ui.row().classes("w-full items-center"):
                    ui.label(f"EXP {xp}/{need}").classes("text-[9px] text-grey-6 grow")
                    ui.button("育成", on_click=lambda _, value=card_id: upgrade(value)).props(
                        "flat dense no-caps color=amber-9")
                    ui.button("店長へ", on_click=lambda _, value=card_id: make_manager(value)).props(
                        "flat dense no-caps color=deep-orange-9")

    @ui.refreshable
    def render():
        with ui.element("main").classes("rg-app"):
            with ui.row().classes("rg-topbar w-full items-center no-wrap"):
                if state["screen"] != "home":
                    ui.button(icon="arrow_back", on_click=lambda: go("home")).props("flat round")
                with ui.column().classes("gap-0 grow"):
                    ui.label("一生懸命！").classes("rg-logo")
                    ui.label("飲食店経営カードゲーム").classes("rg-sublogo")
                ui.label(f"💎 {profile['gems']:,}").classes("rg-currency")
            if state["screen"] == "home":
                with ui.card().classes("rg-hero w-full"):
                    ui.label(f"創業 {profile['year']}年目").classes("rg-kicker")
                    ui.label("人を育て、店を伸ばす。").classes("rg-title")
                    ui.label("最高のチームで、最強の飲食店をつくろう").classes("rg-copy")
                    with ui.row().classes("w-full gap-2 q-mt-md"):
                        ui.button("営業を始める", icon="restaurant", on_click=lambda: go("business")).props(
                            "unelevated no-caps").classes("rg-primary grow")
                        ui.button("採用ガチャ", icon="style", on_click=lambda: go("gacha")).props(
                            "outline no-caps color=amber-7").classes("grow")
                with ui.element("div").classes("rg-metrics"):
                    for label, value in (("現金", money(profile["cash"])),
                                         ("累計利益", money(profile["total_profit"])),
                                         ("支店", f"{profile['branches']}店舗"),
                                         ("経営Pt", f"{profile['management_points']}P")):
                        with ui.card().classes("rg-metric"):
                            ui.label(label)
                            ui.label(value)
                with ui.element("div").classes("rg-menu"):
                    for title, subtitle, icon, screen in (
                        ("営業", "配置して売上を作る", "storefront", "business"),
                        ("スタッフ", "能力と育成を確認", "groups", "staff"),
                        ("採用", "新しい仲間と出会う", "style", "gacha"),
                        ("会社", "支店と成長の記録", "domain", "company")):
                        with ui.card().classes("rg-menu-card cursor-pointer").on(
                                "click", lambda _, value=screen: go(value)):
                            ui.icon(icon).classes("text-2xl text-amber-8")
                            ui.label(title).classes("font-black")
                            ui.label(subtitle).classes("text-[9px] text-grey-6")
            elif state["screen"] == "business":
                ui.label("スタッフ配置").classes("rg-page-title")
                ui.label("各部門に1人ずつ配置。適材適所が利益を生みます").classes("rg-page-copy")
                choices = {
                    item_id: (f"{card(item_id)['name']}　"
                              + " ".join(f"{key}{effective_ability(profile, item_id, key)}"
                                         for key in POSITIONS))
                    for item_id in profile["owned"]
                }
                choices[""] = "未配置"
                with ui.element("div").classes("rg-positions"):
                    for key, label in POSITIONS.items():
                        with ui.card().classes(f"rg-position pos-{key.lower()}"):
                            ui.label(key).classes("rg-position-mark")
                            ui.label(label).classes("font-black")
                            ui.select(choices, value=profile["assignments"].get(key, ""),
                                      on_change=lambda event, position=key: assign(
                                          position, event.value)).props("outlined dense").classes("w-full")
                            current = profile["assignments"].get(key, "")
                            ui.label(f"能力 {effective_ability(profile, current, key)}").classes(
                                "rg-power")
                ui.button("この布陣で営業する", icon="play_arrow", on_click=business).props(
                    "unelevated no-caps").classes("rg-primary w-full q-mt-md")
                result = profile.get("last_result")
                if result and result.get("customer"):
                    with ui.card().classes("rg-result w-full q-mt-md"):
                        with ui.row().classes("w-full items-center no-wrap q-mb-sm"):
                            ui.icon("whatshot").classes("text-2xl text-red-8")
                            with ui.column().classes("gap-0 grow"):
                                ui.label("襲撃カード公開").classes("text-[9px] text-red-8 font-black")
                                ui.label(result["customer"]["name"]).classes("text-lg font-black")
                            ui.label(f"売上候補 {money(result['customer']['sales'])}").classes(
                                "text-xs font-black")
                        ui.image(result["customer"]["image"]).classes("rg-customer-card")
                        ui.label(f"前年の営業結果　{result['completed']}/4部門達成").classes("font-black")
                        with ui.element("div").classes("rg-result-grid"):
                            for key, label in POSITIONS.items():
                                ok = result["achieved"][key]
                                ui.label(f"{'✓' if ok else '×'} {label}  {result['abilities'][key]} / 必要{result['requirements'][key]}").classes(
                                    "success" if ok else "failure")
                        ui.separator()
                        ui.label(f"売上 {money(result['sales'])} − 人件費 {money(result['labor'])} − 家賃 {money(result['rent'])}")
                        ui.label(f"利益 {money(result['profit'])}").classes(
                            "rg-profit positive" if result["profit"] >= 0 else "rg-profit negative")
                        ui.label(f"サボりポイント +{result['support']}").classes("text-amber-9 font-black")
            elif state["screen"] == "staff":
                ui.label("スタッフ一覧").classes("rg-page-title")
                ui.label(f"獲得済み {len(profile['owned'])}/{len(STAFF_POOL)}人").classes("rg-page-copy")
                with ui.element("div").classes("rg-staff-grid"):
                    for card_id in profile["owned"]:
                        staff_tile(card_id)
            elif state["screen"] == "gacha":
                with ui.card().classes("rg-gacha w-full text-center"):
                    ui.label("採用ガチャ").classes("rg-page-title")
                    ui.label("SSR 8%　SR 20%　R 37%　N 35%").classes("rg-page-copy")
                    if state["last_draw"]:
                        drawn, duplicate = state["last_draw"]
                        ui.label("採用成功！" if not duplicate else "再会！限界突破素材を獲得").classes("text-amber-8 font-black")
                        staff_tile(drawn["id"], compact=True)
                    ui.button("1回採用　💎100", icon="auto_awesome", on_click=gacha).props(
                        "unelevated no-caps").classes("rg-primary w-full q-mt-md")
            else:
                ui.label("会社の成長").classes("rg-page-title")
                with ui.element("div").classes("rg-company-grid"):
                    with ui.card().classes("rg-company-card"):
                        ui.image("/static/rg_ceo.jpg").classes("rg-company-art")
                        ui.label("社長（あなた）").classes("text-lg font-black")
                        ui.label(f"経営レベル {profile['ceo_level']}").classes("text-amber-9 font-black")
                        ui.label("会社全体を率いるプレイヤー。事務所を持つと毎年、経営ポイントを獲得します。")
                    with ui.card().classes("rg-company-card"):
                        ui.image("/static/rg_manager.jpg").classes("rg-company-art")
                        ui.label("店長").classes("text-lg font-black")
                        manager = card(profile.get("manager_id", ""))
                        ui.label(manager["name"] if manager else "まだ任命されていません").classes(
                            "text-amber-9 font-black")
                        ui.label("全能力5以上のスタッフを昇格できます。店長がいると全部門能力+1。")
                    with ui.card().classes("rg-company-card"):
                        ui.image("/static/rg_office.jpg").classes("rg-company-art")
                        ui.label("事務所").classes("text-lg font-black")
                        ui.label("開設済み" if profile["office_level"] else "未開設　50万円").classes(
                            "text-amber-9 font-black")
                        ui.label("社長が現場を離れ、毎年経営ポイント+1。")
                        if not profile["office_level"]:
                            ui.button("事務所を開く", on_click=build_office).props(
                                "unelevated no-caps").classes("rg-primary w-full")
                    for branch_id, name, image, price in (
                        ("nagoya", "名古屋店", "/static/rg_branch_nagoya.jpg", 700_000),
                        ("ginza", "銀座旗艦店", "/static/rg_branch_ginza.jpg", 1_500_000)):
                        with ui.card().classes("rg-company-card"):
                            ui.image(image).classes("rg-company-art")
                            ui.label(name).classes("text-lg font-black")
                            opened = branch_id in profile["branch_assets"]
                            ui.label("営業中" if opened else f"開業資金 {money(price)}").classes(
                                "text-amber-9 font-black")
                            ui.label("支店が増えると営業売上も増えます。")
                            if not opened:
                                ui.button("この支店を開く", on_click=lambda _, value=branch_id: build_branch(value)).props(
                                    "unelevated no-caps").classes("rg-primary w-full")
    render()
    ui.add_css("""
    body{background:radial-gradient(circle at 50% -10%,#49320f,#120e0a 42%,#080706)!important;color:#f7ead0!important}.rg-app{width:min(100%,720px);margin:auto;min-height:100vh;padding:18px 16px 60px}.rg-topbar{padding:4px 2px 18px}.rg-logo{font-family:serif;font-size:24px;font-weight:900;color:#f4cc73;text-shadow:0 2px 14px #b56a18}.rg-sublogo{font-size:9px;letter-spacing:.18em;color:#c3aa7b}.rg-currency{padding:8px 12px;border:1px solid #8e682c;border-radius:999px;background:#17110a;font-weight:900}.rg-hero{padding:28px!important;border-radius:28px!important;border:1px solid #9d7431!important;background:linear-gradient(145deg,rgba(10,13,20,.94),rgba(68,32,10,.92)),url('/static/restaurant_card_yamada.jpg') 88% 20%/44% auto no-repeat!important;box-shadow:0 22px 55px rgba(0,0,0,.42)!important;overflow:hidden}.rg-kicker{font-size:10px;font-weight:900;color:#efc66e;letter-spacing:.12em}.rg-title{font-family:serif;font-size:30px;font-weight:900;margin-top:12px}.rg-copy{font-size:11px;color:#d8cdb8}.rg-primary{background:linear-gradient(135deg,#d99d32,#8f5116)!important;color:white!important;box-shadow:0 8px 20px rgba(198,126,28,.3)!important}.rg-metrics{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;margin-top:12px}.rg-metric{padding:14px!important;border-radius:18px!important;background:rgba(27,22,17,.94)!important;border:1px solid #46371f!important}.rg-metric>div:first-child{font-size:9px;color:#ae9c7c}.rg-metric>div:last-child{font-size:17px;font-weight:900;color:#fff}.rg-menu{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:16px}.rg-menu-card{padding:18px!important;border-radius:21px!important;background:linear-gradient(145deg,#fffaf0,#ead9b9)!important;color:#22170d!important;border:1px solid #c4994d!important}.rg-page-title{font-family:serif;font-size:27px;font-weight:900;color:#f6d584}.rg-page-copy{font-size:10px;color:#bcae98;margin-bottom:14px}.rg-positions{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}.rg-position{padding:13px!important;border-radius:19px!important;background:#f7efdf!important;color:#1f160d!important;border:2px solid #875b27!important}.rg-position-mark{width:34px;height:34px;display:flex;align-items:center;justify-content:center;border-radius:10px;background:#6e1616;color:#fff;font-weight:900}.pos-d .rg-position-mark{background:#173c68}.pos-c .rg-position-mark{background:#195b31}.pos-s .rg-position-mark{background:#563067}.rg-power{font-size:11px;font-weight:900;color:#9a641b}.rg-result,.rg-gacha{padding:20px!important;border-radius:23px!important;background:#fff8e9!important;color:#24180d!important;border:1px solid #b7863e!important}.rg-customer-card{width:min(100%,330px);margin:8px auto 16px;border-radius:16px;box-shadow:0 12px 28px rgba(29,13,3,.28)}.rg-result-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:6px;margin:10px 0}.success{color:#17683c;font-weight:900}.failure{color:#ae2525;font-weight:900}.rg-profit{font-size:24px;font-weight:900}.rg-profit.positive{color:#137044}.rg-profit.negative{color:#b32424}.rg-staff-grid,.rg-company-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.rg-staff-card{padding:10px!important;border-radius:19px!important;background:#fff7e8!important;color:#21160d!important;border:2px solid #9c712e!important}.rg-staff-card.compact{width:min(100%,300px);margin:12px auto}.rg-card-art{width:100%;aspect-ratio:2/2.7;object-fit:cover;border-radius:12px;margin-bottom:8px}.rg-card-art[class*='rg-art-']{display:flex;flex-direction:column;align-items:center;justify-content:center;background:radial-gradient(circle,#d6ac53,#30200e);color:#fff}.rg-art-ssr{background:radial-gradient(circle,#a56cdb,#130e1e)!important}.rg-art-sr{background:radial-gradient(circle,#4a91cb,#101b29)!important}.rg-art-r{background:radial-gradient(circle,#5fa56b,#132018)!important}.rg-art-skill{font-size:12px;font-weight:900;margin-top:10px}.rarity{padding:3px 7px;border-radius:7px;background:#333;color:white;font-size:9px;font-weight:900}.rarity.ssr{background:#7540a8}.rarity.sr{background:#226aa0}.rarity.r{background:#28753d}.rg-stats{font-size:10px;font-weight:900;padding:6px 0}.rg-company-card{padding:11px!important;border-radius:20px!important;background:#fff7e8!important;color:#21160d!important;border:1px solid #b98b46!important}.rg-company-art{width:100%;aspect-ratio:1/1.15;object-fit:cover;border-radius:13px}.q-field--outlined .q-field__control{border-radius:11px!important;background:white}@media(max-width:390px){.rg-staff-grid,.rg-company-grid{grid-template-columns:1fr}.rg-title{font-size:25px}.rg-hero{background-size:55% auto!important}}
    """)
