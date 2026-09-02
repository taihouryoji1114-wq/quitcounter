from nicegui import app, ui

from core.auth import require_app_access, selected_user_id
from core.chankocchi import (FOODS, apply_life_tick, can_depart, care,
                             claim_store_reward, current_wish, feed,
                             has_store_activity, initial_profile, life_routine,
                             next_stage_progress, normalize_profile, stage_info,
                             start_next_generation)
from core.clock import today_jst_string
from core.data import data
from core.theme import Theme


@ui.page('/chankocchi')
def chankocchi_page():
    if not require_app_access('chankocchi'):
        return
    Theme.page('ちゃんこっち', app_name='chankocchi')
    user_id = selected_user_id()
    profiles = data.data.setdefault('chankocchi', {}).setdefault('profiles', {})
    profile = profiles.setdefault(user_id, initial_profile())
    normalize_profile(profile); apply_life_tick(profile)
    state = {'speech': current_wish(profile), 'mode': 'living', 'mini_score': 0}

    def save():
        profiles[user_id] = profile; data.save()

    def finish_animation():
        state['mode'] = 'living'; render.refresh()

    def do_bath():
        result = care(profile, 'bath', today_jst_string())
        state.update(speech=result['speech'], mode='bath'); save(); render.refresh()
        ui.timer(2.6, finish_animation, once=True)

    with ui.dialog() as food_dialog, ui.card().classes('choice-dialog'):
        ui.label('なに食べる？').classes('text-xl font-black')
        ui.label('ちゃんこっちが食べたいごはんを選んでね').classes('text-xs text-grey-6')
        with ui.element('div').classes('food-grid w-full'):
            for key, item in FOODS.items():
                def choose_food(food=key):
                    result = feed(profile, food, today_jst_string())
                    state.update(speech=result['speech'], mode='eating')
                    save(); food_dialog.close(); render.refresh()
                    ui.timer(2.6, finish_animation, once=True)
                ui.button(f"{item['icon']}  {item['label']}", on_click=choose_food).props('flat no-caps').classes('food-choice')

    with ui.dialog() as play_dialog, ui.card().classes('choice-dialog'):
        ui.label('ちゃんこキャッチ').classes('text-xl font-black')
        ui.label('動くおやつを5回つかまえて！').classes('text-xs text-grey-6')
        mini_area = ui.element('div').classes('mini-area w-full')
        score_label = ui.label('0 / 5').classes('mini-score')
        def hit_target():
            state['mini_score'] += 1; score_label.set_text(f"{state['mini_score']} / 5")
            ui.run_javascript("const b=document.querySelector('.mini-target');if(b){b.style.left=(8+Math.random()*72)+'%';b.style.top=(8+Math.random()*64)+'%'}")
            if state['mini_score'] >= 5:
                care(profile, 'play', today_jst_string())
                state.update(speech='もう一回やろ！', mode='playing')
                save(); play_dialog.close(); render.refresh(); ui.timer(2.2, finish_animation, once=True)
        with mini_area:
            ui.button('🍡', on_click=hit_target).props('round flat').classes('mini-target')

    def open_game():
        state['mini_score'] = 0; score_label.set_text('0 / 5'); play_dialog.open()

    def store_reward():
        if not has_store_activity(data.data, today_jst_string()):
            ui.notify('厨房ライブボードの仕事を終えると受け取れます', type='info'); return
        try:
            claim_store_reward(profile, today_jst_string()); save(); render.refresh()
        except ValueError as error:
            ui.notify(str(error), type='warning')

    def open_store():
        app.storage.user['return_to_chankocchi'] = True
        ui.navigate.to('/store-ops')

    def next_generation():
        try:
            start_next_generation(profile); save(); render.refresh()
        except ValueError as error:
            ui.notify(str(error), type='warning')

    def toggle_life_menu():
        ui.run_javascript("document.querySelector('.chanko-app')?.classList.toggle('menu-open')")

    @ui.refreshable
    def render():
        stage = stage_info(profile); progress, progress_label = next_stage_progress(profile)
        today_claimed = today_jst_string() in profile.get('store_reward_dates', [])
        store_done = has_store_activity(data.data, today_jst_string()); mode = state['mode']
        routine = life_routine(profile)
        with ui.element('main').classes('chanko-app'):
            with ui.row().classes('chanko-top w-full items-center no-wrap'):
                with ui.column().classes('gap-0 grow'):
                    ui.label('ちゃんこっち').classes('chanko-logo')
                    ui.label(f"{profile['generation']}代目・{stage['name']}").classes('chanko-sub')
                ui.label(f"🪙 {profile['coins']}").classes('coin-pill')
            with ui.element('div').classes('life-viewport'):
                with ui.element('section').classes(f"life-room mode-{mode} time-{routine['period']}").props(
                        f"data-routine=\"{routine['action']}\" data-hunger=\"{profile['meters']['hunger']}\" "
                        f"data-joy=\"{profile['meters']['joy']}\" data-clean=\"{profile['meters']['cleanliness']}\""):
                    with ui.element('div').classes('window'):
                        ui.element('div').classes('cloud cloud-one'); ui.element('div').classes('cloud cloud-two')
                    ui.element('div').classes('shelf'); ui.element('div').classes('table')
                    with ui.element('div').classes('speech-bubble'): ui.label(state['speech'])
                    with ui.element('div').classes('life-status'):
                        ui.element('i').classes('life-status-dot')
                        ui.label(routine['label']).classes('life-status-label')
                    ui.element('div').classes('sunbeam')
                    ui.element('div').classes('living-trace trace-book')
                    ui.element('div').classes('living-trace trace-cup')
                    ui.element('div').classes('chanko-character pose-sit').props(
                        'aria-label="部屋で暮らすちゃんこっち" role="button" tabindex="0"')
                    with ui.element('div').classes('pet-quick-actions'):
                        ui.button(icon='restaurant', on_click=food_dialog.open).props('round unelevated aria-label="ごはん"').classes('pet-action pet-food')
                        ui.button(icon='sports_esports', on_click=open_game).props('round unelevated aria-label="あそぶ"').classes('pet-action pet-play')
                        ui.button(icon='bathtub', on_click=do_bath).props('round unelevated aria-label="お風呂"').classes('pet-action pet-bath')
                    ui.element('div').classes('actor-shadow')
                    if mode == 'eating':
                        with ui.element('div').classes('meal-bowl'):
                            ui.element('i').classes('steam steam-one'); ui.element('i').classes('steam steam-two')
                    if mode == 'bath':
                        ui.element('div').classes('bath-tub')
                        ui.element('div').classes('bath-bubbles')
                    if mode == 'playing': ui.label('✨').classes('action-prop play-prop')
                with ui.element('nav').classes('room-map').props('aria-label="家の中を移動"'):
                    for room_key, room_label, room_icon in (
                            ('living', 'リビング', 'weekend'), ('kitchen', 'キッチン', 'soup_kitchen'),
                            ('bedroom', '寝室', 'bedtime'), ('garden', '庭', 'local_florist')):
                        ui.button(room_label, icon=room_icon).props(
                            f'flat no-caps data-room="{room_key}"').classes('room-jump')
            ui.button(icon='menu', on_click=toggle_life_menu).props('round unelevated aria-label="暮らしメニュー"').classes('life-menu-fab')
            ui.element('button').classes('life-sheet-shade').on('click', toggle_life_menu).props('aria-label="メニューを閉じる"')
            with ui.element('aside').classes('life-sheet'):
                with ui.row().classes('w-full items-center no-wrap life-sheet-head'):
                    with ui.column().classes('gap-0 grow'):
                        ui.label('ちゃんこっちのお世話').classes('text-lg font-black')
                        ui.label(f"{profile['generation']}代目・{stage['name']}").classes('text-xs text-grey-6')
                    ui.button(icon='close', on_click=toggle_life_menu).props('round flat aria-label="閉じる"')
                with ui.element('div').classes('life-control-panel'):
                    with ui.element('div').classes('meter-grid'):
                        for key, label in {'hunger':'おなか','cleanliness':'お風呂','joy':'ごきげん'}.items():
                            with ui.element('div').classes('meter-card'):
                                ui.label(label); ui.linear_progress(profile['meters'][key] / 100).props('rounded color=amber-7')
                    with ui.element('div').classes('care-grid'):
                        ui.button('ごはん', icon='restaurant', on_click=food_dialog.open).props('flat no-caps').classes('care-button')
                        ui.button('あそぶ', icon='sports_esports', on_click=open_game).props('flat no-caps').classes('care-button')
                        ui.button('お風呂', icon='bathtub', on_click=do_bath).props('flat no-caps').classes('care-button')
                with ui.element('div').classes('life-menu-grid'):
                    with ui.card().classes('growth-card w-full'):
                        with ui.row().classes('w-full items-center no-wrap'):
                            with ui.column().classes('gap-0 grow'):
                                ui.label('成長のきろく').classes('font-black'); ui.label(progress_label).classes('text-xs text-grey-6')
                            ui.label('ちゃんタマあり' if profile.get('egg_ready') else '成長中').classes('growing-chip')
                        ui.linear_progress(progress).props('rounded color=deep-orange-5').classes('q-mt-sm')
                    with ui.card().classes('store-link w-full'):
                        ui.label('今日のお仕事').classes('font-black')
                        ui.label('厨房ライブボードとタスクの実績を確認します').classes('text-[10px] opacity-80')
                        with ui.row().classes('w-full gap-2 q-mt-sm'):
                            ui.button('店舗運営へ', icon='storefront', on_click=open_store).props('flat no-caps').classes('grow store-open')
                            reward_label = '受取済' if today_claimed else '+10枚' if store_done else '未達成'
                            ui.button(reward_label, on_click=store_reward).props('unelevated no-caps').classes('store-reward').set_enabled(not today_claimed)
                if can_depart(profile): ui.button('次の世代を迎える', on_click=next_generation).props('unelevated no-caps color=deep-orange-7').classes('w-full q-mt-md')
        ui.add_css(CHANKO_CSS)
        if mode == 'living':
            ui.run_javascript(CHANKO_LIFE_SCRIPT)
        else:
            action_ratio = {'eating': .31, 'bath': .61, 'playing': .79}.get(mode, 0)
            ui.run_javascript(
                "requestAnimationFrame(()=>{const v=document.querySelector('.life-viewport');"
                "const r=document.querySelector('.life-room');"
                f"if(v&&r)v.scrollTo({{left:Math.max(0,r.clientWidth*{action_ratio}-v.clientWidth/2),behavior:'smooth'}})}})"
            )
    save(); render()


CHANKO_CSS = '''
.chanko-app{position:relative;min-height:100dvh;width:100%;margin:0;padding:0 0 58px;background:linear-gradient(180deg,#D5BA91 0,#F7E9D2 54%,#F3E2C7 100%);box-sizing:border-box;overflow-x:hidden}
.chanko-logo{font-size:25px;font-weight:950;color:#3C2D24}.chanko-sub{font-size:10px;font-weight:800;color:#795D48}.coin-pill{padding:8px 13px;border-radius:999px;background:#3C2D24;color:#FFD980;font-weight:900}.chanko-top{position:absolute;z-index:30;top:max(12px,env(safe-area-inset-top));left:14px;right:14px;width:auto!important;padding:10px 12px;border:1px solid rgba(255,255,255,.62);border-radius:20px;background:rgba(255,249,235,.78);box-shadow:0 8px 24px rgba(66,40,22,.13);backdrop-filter:blur(14px)}
.life-viewport{position:relative;width:100vw;height:min(72dvh,680px);min-height:530px;overflow-x:auto;overflow-y:hidden;border-radius:0 0 38px 38px;box-shadow:0 20px 44px rgba(72,42,24,.22);scrollbar-width:none;scroll-snap-type:x proximity;overscroll-behavior-x:contain;-webkit-overflow-scrolling:touch;background:#4A2F1D}.life-viewport::-webkit-scrollbar{display:none}
.life-room{position:relative;width:max(184vw,1500px);height:100%;min-height:530px;max-width:none;overflow:hidden;background-image:linear-gradient(180deg,rgba(255,244,214,.01),rgba(61,34,18,.07)),url('/static/chankocchi_home_panorama_v2.png');background-size:100% 100%;background-position:center;border:0;isolation:isolate;scroll-snap-align:start}
.life-room.time-evening{filter:saturate(.94) brightness(.9)}.life-room.time-night{filter:saturate(.78) brightness(.7)}.life-room.time-morning{filter:saturate(1.04) brightness(1.04)}
.life-room:after{content:'';position:absolute;z-index:2;left:4%;right:4%;bottom:4%;height:10%;border-radius:50%;background:radial-gradient(ellipse,rgba(49,27,13,.20),transparent 68%);pointer-events:none}.window,.cloud,.shelf,.table{display:none}
.speech-bubble{position:absolute;z-index:10;top:88px;left:18px;max-width:58%;padding:11px 14px;border-radius:17px 17px 17px 5px;background:rgba(255,255,255,.9);box-shadow:0 5px 18px rgba(61,37,18,.12);font-size:12px;font-weight:900;color:#46352A;backdrop-filter:blur(7px)}
.life-status{position:absolute;z-index:10;right:18px;top:91px;display:flex;align-items:center;gap:6px;padding:7px 10px;border-radius:999px;background:rgba(49,39,30,.66);color:white;backdrop-filter:blur(7px);font-size:9px;font-weight:850}.life-status-dot{width:7px;height:7px;border-radius:50%;background:#91E4A7;box-shadow:0 0 0 4px rgba(145,228,167,.14);animation:alive-pulse 2.2s ease-in-out infinite}.sunbeam{position:absolute;z-index:1;left:39%;top:14%;width:30%;height:67%;background:linear-gradient(115deg,rgba(255,239,177,.18),transparent 70%);transform:skewX(-13deg);pointer-events:none;animation:sun-shift 12s ease-in-out infinite alternate}.living-trace{display:none}
.chanko-character{position:absolute!important;z-index:6;width:88px!important;height:88px!important;left:18%;bottom:18%;background-image:url('/static/chankocchi_egg_sprites_v1.png');background-repeat:no-repeat;background-size:400% 100%;filter:sepia(.05) saturate(.93) drop-shadow(0 7px 4px rgba(49,29,16,.25));transition:left 4.8s cubic-bezier(.42,0,.58,1),bottom 4.8s ease,scale 1.2s ease;transform-origin:50% 94%;will-change:left,bottom,transform}
.pet-quick-actions{position:absolute;z-index:18;left:18%;bottom:calc(18% + 88px);display:flex;gap:7px;opacity:0;pointer-events:none;transform:translate(-18px,12px) scale(.82);transition:left 4.8s cubic-bezier(.42,0,.58,1),bottom 4.8s ease,opacity .18s ease,transform .22s ease}.quick-open .pet-quick-actions{opacity:1;pointer-events:auto;transform:translate(-18px,0) scale(1)}.pet-action{width:42px!important;height:42px!important;min-width:42px!important;color:#49372A!important;background:rgba(255,249,232,.96)!important;border:2px solid rgba(255,255,255,.78)!important;box-shadow:0 7px 18px rgba(45,25,12,.24)!important}.pet-food{color:#D47636!important}.pet-play{color:#4B87A4!important}.pet-bath{color:#4D9D9B!important}
.actor-shadow{position:absolute;z-index:5;left:39%;bottom:17%;width:76px;height:17px;border-radius:50%;background:rgba(45,25,13,.2);filter:blur(3px);transition:left 3.8s cubic-bezier(.42,0,.58,1),bottom 3.8s ease,width 1s;pointer-events:none}
.pose-walk-a{background-position:0 0}.pose-walk-b{background-position:33.333% 0}.pose-sit{background-position:66.666% 0;animation:living-breath 3.8s ease-in-out infinite}.pose-sleep{background-position:100% 0;animation:sleep-breath 4.8s ease-in-out infinite}.is-walking{animation:step-bob .42s ease-in-out infinite}.facing-left{transform:scaleX(-1)}
.is-looking{animation:curious-look 1.8s ease-in-out}.is-excited{animation:happy-hop .48s ease-in-out 3}.is-grooming{animation:groom 1.1s ease-in-out 2}.is-listening{animation:ear-listen .8s ease-in-out 2}
.mode-eating .chanko-character{left:39%;bottom:18%;background-position:66.666% 0;animation:nibble .65s ease-in-out infinite}.mode-bath .chanko-character{left:69%;bottom:24%;width:76px!important;height:76px!important;background-position:66.666% 0;animation:bob 1s ease-in-out infinite}.mode-playing .chanko-character{left:84%;bottom:18%;background-position:0 0;animation:hop .72s ease-in-out infinite}
.action-prop{position:absolute;z-index:8}.play-prop{font-size:32px;left:50%;bottom:39%}.meal-bowl{position:absolute;z-index:8;left:64%;bottom:25%;width:54px;height:20px;border-radius:5px 5px 24px 24px;background:linear-gradient(#F8F1DF 0 28%,#31536B 29% 45%,#E8DED0 46%);box-shadow:0 5px 8px rgba(54,30,14,.25)}.meal-bowl:after{content:'';position:absolute;left:7px;right:7px;top:-5px;height:9px;border-radius:50%;background:#A96539;box-shadow:inset 0 2px #F4C06A}.steam{position:absolute;top:-23px;width:7px;height:20px;border-left:2px solid rgba(255,255,255,.84);border-radius:50%;animation:steam-rise 1.6s ease-in-out infinite}.steam-one{left:16px}.steam-two{left:32px;animation-delay:-.7s}.bath-tub{position:absolute;z-index:7;right:2.2%;bottom:15%;width:113px;height:57px;border-radius:15px 15px 34px 34px;background:linear-gradient(180deg,#EAF4F4,#99BEC2);border:4px solid #F6FFFF;box-shadow:0 7px 12px rgba(25,45,49,.24)}.bath-tub:before{content:'';position:absolute;left:5px;right:5px;top:-9px;height:18px;border-radius:50%;background:#CDE8E8;border:3px solid white}.bath-bubbles{position:absolute;z-index:9;right:6%;bottom:26%;width:65px;height:34px;background:radial-gradient(circle at 14% 65%,#fff 0 6px,transparent 7px),radial-gradient(circle at 37% 38%,#fff 0 8px,transparent 9px),radial-gradient(circle at 62% 62%,#fff 0 7px,transparent 8px),radial-gradient(circle at 85% 31%,#fff 0 6px,transparent 7px);animation:bubble-float 1.8s ease-in-out infinite}
.room-map{position:sticky;z-index:24;left:50%;bottom:80px;display:flex;width:max-content;gap:3px;padding:5px;border-radius:18px;background:rgba(50,36,27,.68);backdrop-filter:blur(12px);transform:translateX(-50%);box-shadow:0 8px 24px rgba(30,18,10,.2)}.room-jump{min-height:34px!important;padding:0 7px!important;border-radius:13px!important;color:#fff!important;font-size:9px!important}.room-jump.is-current{background:rgba(255,224,154,.94)!important;color:#563D28!important}
.life-control-panel{position:relative;z-index:20;width:min(calc(100% - 24px),680px);margin:-66px auto 0;padding:13px;border-radius:25px;background:rgba(255,250,239,.88);border:1px solid rgba(255,255,255,.72);box-shadow:0 15px 38px rgba(78,48,28,.16);backdrop-filter:blur(16px)}.meter-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:0 0 9px}.meter-card{padding:9px 8px;border-radius:14px;background:rgba(255,255,255,.72);font-size:9px;font-weight:900;color:#725945}.care-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.care-button{background:#fff!important;color:#543E30!important;min-height:53px!important;border-radius:16px!important}.life-menu-title{display:block;width:min(calc(100% - 32px),680px);margin:24px auto 8px;font-size:17px;font-weight:950;color:#49382D}.life-menu-grid{display:grid;grid-template-columns:1fr;gap:11px;width:min(calc(100% - 32px),680px);margin:0 auto}.growth-card,.store-link{margin-top:0;padding:15px!important;border-radius:21px!important;border:1px solid rgba(120,81,51,.12)!important;box-shadow:0 8px 22px rgba(93,61,39,.07)!important}.growing-chip{font-size:9px;font-weight:900;padding:6px 9px;border-radius:999px;background:#E8EFEA;color:#52685A}.store-link{background:linear-gradient(135deg,#284E3E,#4E8064)!important;color:#fff!important}.store-open{color:white!important}.store-reward{background:#FFE09A!important;color:#5C421B!important}.choice-dialog{width:min(92vw,440px)!important;padding:22px!important;border-radius:25px!important}.food-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;margin-top:12px}.food-choice{min-height:58px!important;border-radius:16px!important;background:#FFF7E5!important;color:#49382D!important}.mini-area{position:relative;height:260px;margin-top:12px;border-radius:20px;background:linear-gradient(#BDE4EC,#F7E0A7 65%,#8FC574 65%);overflow:hidden}.mini-target{position:absolute!important;left:42%;top:38%;font-size:27px!important;transition:left .15s,top .15s}.mini-score{text-align:center;font-size:19px;font-weight:950;color:#5C421B}
.chanko-app{position:fixed;z-index:1;inset:0;height:100dvh;width:100%;margin:0;padding:0;background:#4A2F1D;overflow:hidden}.life-viewport{position:absolute;inset:0;width:100vw;height:100dvh;min-height:100dvh;overflow-x:auto;overflow-y:hidden;border-radius:0;box-shadow:none}.life-room{width:max(205vw,1500px);height:100dvh;min-height:100dvh}.room-map{bottom:max(18px,env(safe-area-inset-bottom))}
.life-menu-fab{position:fixed!important;z-index:35;right:18px;bottom:max(76px,calc(env(safe-area-inset-bottom) + 70px));width:52px!important;height:52px!important;background:rgba(57,42,31,.86)!important;color:#fff!important;box-shadow:0 9px 26px rgba(25,14,8,.3)!important;backdrop-filter:blur(12px)}.life-sheet-shade{position:fixed;z-index:39;inset:0;border:0;background:rgba(35,22,14,.34);opacity:0;pointer-events:none;transition:opacity .25s ease}.life-sheet{position:fixed;z-index:40;left:0;right:0;bottom:0;max-height:min(78dvh,720px);padding:15px 16px max(20px,env(safe-area-inset-bottom));border-radius:29px 29px 0 0;background:rgba(255,250,240,.97);box-shadow:0 -20px 55px rgba(31,19,11,.28);backdrop-filter:blur(20px);overflow-y:auto;transform:translateY(105%);transition:transform .32s cubic-bezier(.22,.8,.2,1)}.menu-open .life-sheet{transform:translateY(0)}.menu-open .life-sheet-shade{opacity:1;pointer-events:auto}.life-sheet-head{position:sticky;top:-15px;z-index:2;margin:-15px 0 8px;padding:16px 0 8px;background:linear-gradient(rgba(255,250,240,.99) 75%,transparent)}.life-control-panel{position:relative;width:100%;margin:0 auto 12px;padding:13px;border-radius:22px;background:#FFF8E9;border:1px solid rgba(132,89,55,.12);box-shadow:none}.life-menu-grid{width:100%;margin:0 auto}
@keyframes living-breath{0%,100%{transform:translateY(0) rotate(-.5deg)}35%{transform:translateY(-2px) rotate(.4deg)}65%{transform:translateY(-3px) rotate(.8deg)}}@keyframes sleep-breath{50%{transform:scale(.965) translateY(2px)}}@keyframes step-bob{0%,100%{margin-bottom:0}50%{margin-bottom:5px}}@keyframes curious-look{0%,100%{transform:rotate(0)}28%{transform:rotate(-6deg)}70%{transform:rotate(5deg)}}@keyframes happy-hop{50%{transform:translateY(-12px) scale(1.04)}}@keyframes groom{35%{transform:rotate(-7deg) scale(.98)}70%{transform:rotate(5deg)}}@keyframes ear-listen{50%{transform:translateY(-2px) scaleY(1.025)}}@keyframes nibble{50%{transform:translateY(3px) rotate(1.5deg)}}@keyframes bob{50%{transform:translateY(-4px)}}@keyframes hop{50%{transform:translateY(-15px) rotate(3deg)}}@keyframes steam-rise{0%{transform:translateY(5px) scale(.8);opacity:0}45%{opacity:.9}100%{transform:translateY(-12px) translateX(4px);opacity:0}}@keyframes bubble-float{50%{transform:translateY(-5px) rotate(2deg)}}@keyframes alive-pulse{50%{opacity:.48;transform:scale(.82)}}@keyframes sun-shift{to{transform:translateX(12px) skewX(-13deg);opacity:.68}}
@media(min-width:760px){.life-menu-grid{grid-template-columns:1fr 1fr}.life-room{width:max(175vw,1700px)}.life-sheet{left:50%;right:auto;width:min(720px,92vw);transform:translate(-50%,105%)}.menu-open .life-sheet{transform:translate(-50%,0)}}@media(max-width:390px){.care-button{font-size:11px!important}.life-viewport{height:100dvh;min-height:100dvh}.room-jump{font-size:8px!important;padding:0 5px!important}.chanko-top{top:max(8px,env(safe-area-inset-top));left:9px;right:9px}.speech-bubble{top:82px}}
'''


CHANKO_LIFE_SCRIPT = r'''
(() => {
  if (window.__chankoLifeTimer) clearTimeout(window.__chankoLifeTimer);
  if (window.__chankoStepTimer) clearInterval(window.__chankoStepTimer);
  const actor = document.querySelector('.life-room.mode-living .chanko-character');
  if (!actor) return;
  const room = actor.closest('.life-room');
  const viewport = actor.closest('.life-viewport');
  const shadow = room.querySelector('.actor-shadow');
  const quickActions = room.querySelector('.pet-quick-actions');
  const bubble = room.querySelector('.speech-bubble .q-label');
  const status = room.querySelector('.life-status-label');
  const routine = room.dataset.routine || 'wander';
  const places = {
    sofa:    {left:  '9%', bottom:'18%', stay:[6500,11000], pose:'sit',   scale:.92, room:'living',  label:'リビングでくつろいでる'},
    window:  {left: '18%', bottom:'18%', stay:[5800,10000], pose:'sit',   scale:.88, room:'living',  label:'窓の外を眺めてる'},
    kitchen: {left: '35%', bottom:'18%', stay:[4200, 7600], pose:'sit',   scale:.91, room:'kitchen', label:'台所の匂いを気にしてる'},
    table:   {left: '46%', bottom:'17%', stay:[5000, 9000], pose:'sit',   scale:.94, room:'kitchen', label:'テーブルのそばでのんびり'},
    bed:     {left: '61%', bottom:'18%', stay:[9000,15000], pose:'sleep', scale:.84, room:'bedroom', label:'お布団でうとうとしてる'},
    dresser: {left: '70%', bottom:'18%', stay:[3800, 6500], pose:'sit',   scale:.84, room:'bedroom', label:'寝室で身づくろいしてる'},
    garden:  {left: '87%', bottom:'17%', stay:[6200,11000], pose:'sit',   scale:.90, room:'garden',  label:'庭のお花を見てる'},
  };
  const keys = Object.keys(places);
  const preferred = {
    wait_food:['kitchen','table'], want_bath:['dresser','bed'], seek_play:['garden','sofa'],
    sleepy:['bed','sofa'], window:['window','garden'], wander:keys,
  };
  let current = sessionStorage.getItem('chankocchi-place');
  if (!places[current]) current = routine === 'sleepy' ? 'bed' : 'table';
  let busy = false;
  let foot = false;
  const randomBetween = ([min,max]) => min + Math.random() * (max-min);
  const setPose = pose => {
    actor.classList.remove('pose-walk-a','pose-walk-b','pose-sit','pose-sleep','is-walking','is-looking','is-grooming','is-listening');
    actor.classList.add(`pose-${pose}`);
  };
  const say = (text, duration=3200) => {
    if (!bubble || !text) return;
    const old = bubble.textContent;
    bubble.textContent = text;
    setTimeout(() => { if (bubble.textContent === text) bubble.textContent = old; }, duration);
  };
  const settle = key => {
    current = key; sessionStorage.setItem('chankocchi-place', key);
    actor.classList.remove('facing-left'); setPose(places[key].pose);
    if (status) status.textContent = places[key].label;
    document.querySelectorAll('.room-jump').forEach(button =>
      button.classList.toggle('is-current', button.dataset.room === places[key].room));
  };
  const moveTo = (next, after) => {
    if (busy || next === current) return after?.();
    busy = true;
    const destination = places[next];
    const goingLeft = keys.indexOf(next) < keys.indexOf(current);
    actor.classList.toggle('facing-left', goingLeft);
    room.classList.remove('quick-open');
    actor.classList.add('is-walking');
    actor.style.scale = destination.scale;
    if (status) status.textContent = 'とことこ移動中';
    window.__chankoStepTimer = setInterval(() => {
      foot = !foot;
      actor.classList.toggle('pose-walk-a', foot);
      actor.classList.toggle('pose-walk-b', !foot);
      actor.classList.remove('pose-sit','pose-sleep');
    }, 320);
    requestAnimationFrame(() => {
      actor.style.left = destination.left;
      actor.style.bottom = destination.bottom;
      if (shadow) { shadow.style.left = `calc(${destination.left} + 12px)`; shadow.style.bottom = destination.bottom; }
      if (quickActions) { quickActions.style.left = destination.left; quickActions.style.bottom = `calc(${destination.bottom} + 88px)`; }
    });
    window.__chankoLifeTimer = setTimeout(() => {
      clearInterval(window.__chankoStepTimer);
      busy = false; settle(next); after?.();
    }, 4900);
  };
  const idleMoment = () => {
    if (busy || actor.classList.contains('pose-sleep')) return;
    const behavior = ['is-looking','is-grooming','is-listening'][Math.floor(Math.random()*3)];
    actor.classList.add(behavior);
    setTimeout(()=>actor.classList.remove(behavior), 2300);
  };
  const chooseNext = () => {
    const pool = preferred[routine] || keys;
    const weighted = Math.random() < .68 ? pool : keys;
    const choices = weighted.filter(key => key !== current);
    return choices[Math.floor(Math.random()*choices.length)] || current;
  };
  const live = () => {
    const destination = chooseNext();
    moveTo(destination, () => {
      const place = places[destination];
      const dwell = randomBetween(place.stay);
      window.__chankoLifeTimer = setTimeout(() => {
        if (Math.random() < .58) idleMoment();
        window.__chankoLifeTimer = setTimeout(live, 2600 + Math.random()*3200);
      }, dwell);
    });
  };
  const start = places[current];
  actor.style.left=start.left; actor.style.bottom=start.bottom; actor.style.scale=start.scale;
  if (shadow) { shadow.style.left=`calc(${start.left} + 12px)`; shadow.style.bottom=start.bottom; }
  if (quickActions) { quickActions.style.left=start.left; quickActions.style.bottom=`calc(${start.bottom} + 88px)`; }
  settle(current);
  actor.onclick = () => {
    if (busy) return;
    room.classList.toggle('quick-open');
    actor.classList.remove('is-looking','is-grooming','is-listening');
    actor.classList.add('is-excited');
    say(routine==='wait_food' ? 'お腹すいた！' : routine==='seek_play' ? 'あそぼ！' : '呼んだ？');
    setTimeout(()=>actor.classList.remove('is-excited'),1700);
  };
  actor.onkeydown = event => { if(event.key==='Enter'||event.key===' '){event.preventDefault();actor.click();} };
  document.querySelectorAll('.room-jump').forEach(button => {
    button.onclick = () => {
      const candidates = keys.filter(key => places[key].room === button.dataset.room);
      const destination = candidates[Math.floor(Math.random() * candidates.length)];
      if (!destination) return;
      const x = parseFloat(places[destination].left) / 100 * room.clientWidth;
      viewport.scrollTo({left: Math.max(0, x - viewport.clientWidth / 2), behavior:'smooth'});
      room.classList.remove('quick-open');
    };
  });
  room.addEventListener('click', event => {
    if (event.target === room) room.classList.remove('quick-open');
  });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && !busy) { idleMoment(); say('おかえり！'); }
  }, {once:true});
  window.__chankoLifeTimer = setTimeout(live, 4500 + Math.random()*2600);
})();
'''
