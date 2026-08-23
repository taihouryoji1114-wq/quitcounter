from nicegui import app, ui

from core.auth import require_app_access, selected_user_id
from core.chankocchi import (FOODS, apply_life_tick, can_depart, care,
                             claim_store_reward, current_wish, feed,
                             has_store_activity, initial_profile,
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
            ui.notify('今日のチェック表を終えると受け取れます', type='info'); return
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

    @ui.refreshable
    def render():
        stage = stage_info(profile); progress, progress_label = next_stage_progress(profile)
        today_claimed = today_jst_string() in profile.get('store_reward_dates', [])
        store_done = has_store_activity(data.data, today_jst_string()); mode = state['mode']
        with ui.element('main').classes('chanko-app'):
            with ui.row().classes('chanko-top w-full items-center no-wrap'):
                with ui.column().classes('gap-0 grow'):
                    ui.label('ちゃんこっち').classes('chanko-logo')
                    ui.label(f"{profile['generation']}代目・{stage['name']}").classes('chanko-sub')
                ui.label(f"🪙 {profile['coins']}").classes('coin-pill')
            with ui.element('section').classes(f'life-room mode-{mode}'):
                with ui.element('div').classes('window'):
                    ui.element('div').classes('cloud cloud-one'); ui.element('div').classes('cloud cloud-two')
                ui.element('div').classes('shelf'); ui.element('div').classes('table')
                with ui.element('div').classes('speech-bubble'): ui.label(state['speech'])
                ui.element('div').classes('chanko-character pose-sit').props('aria-label="部屋で暮らすちゃんこっち"')
                if mode == 'eating': ui.label(FOODS.get(profile.get('last_food'), FOODS['chanko'])['icon']).classes('action-prop food-prop')
                if mode == 'bath':
                    ui.label('🛁').classes('action-prop bath-prop'); ui.label('○ ｡ ○').classes('bubble-prop')
                if mode == 'playing': ui.label('✨').classes('action-prop play-prop')
            with ui.element('div').classes('meter-grid'):
                for key, label in {'hunger':'おなか','cleanliness':'お風呂','joy':'ごきげん'}.items():
                    with ui.element('div').classes('meter-card'):
                        ui.label(label); ui.linear_progress(profile['meters'][key] / 100).props('rounded color=amber-7')
            with ui.element('div').classes('care-grid'):
                ui.button('ごはん', icon='restaurant', on_click=food_dialog.open).props('flat no-caps').classes('care-button')
                ui.button('あそぶ', icon='sports_esports', on_click=open_game).props('flat no-caps').classes('care-button')
                ui.button('お風呂', icon='bathtub', on_click=do_bath).props('flat no-caps').classes('care-button')
            with ui.card().classes('growth-card w-full'):
                with ui.row().classes('w-full items-center no-wrap'):
                    with ui.column().classes('gap-0 grow'):
                        ui.label('成長のきろく').classes('font-black'); ui.label(progress_label).classes('text-xs text-grey-6')
                    ui.label('ちゃんタマあり' if profile.get('egg_ready') else '成長中').classes('growing-chip')
                ui.linear_progress(progress).props('rounded color=deep-orange-5').classes('q-mt-sm')
            with ui.card().classes('store-link w-full'):
                ui.label('今日のお仕事').classes('font-black')
                ui.label('チェック表と、今後追加するタスクの実績をサーバーで確認します').classes('text-[10px] opacity-80')
                with ui.row().classes('w-full gap-2 q-mt-sm'):
                    ui.button('店舗運営へ', icon='storefront', on_click=open_store).props('flat no-caps').classes('grow store-open')
                    reward_label = '受取済' if today_claimed else '+10枚' if store_done else '未達成'
                    ui.button(reward_label, on_click=store_reward).props('unelevated no-caps').classes('store-reward').set_enabled(not today_claimed)
            if can_depart(profile): ui.button('次の世代を迎える', on_click=next_generation).props('unelevated no-caps color=deep-orange-7').classes('w-full q-mt-md')
        ui.add_css(CHANKO_CSS)
        if mode == 'living':
            ui.run_javascript(CHANKO_LIFE_SCRIPT)
    save(); render()


CHANKO_CSS = '''
.chanko-app{min-height:100vh;width:min(100%,680px);margin:0 auto;padding:18px 16px 54px;background:linear-gradient(180deg,#FFF8E8,#F3E2C7);box-sizing:border-box}
.chanko-logo{font-size:27px;font-weight:950;color:#3C2D24}.chanko-sub{font-size:10px;font-weight:800;color:#8A6F59}.coin-pill{padding:8px 13px;border-radius:999px;background:#3C2D24;color:#FFD980;font-weight:900}.chanko-top{padding:2px 3px 12px}
.life-room{position:relative;aspect-ratio:16/9;min-height:280px;border-radius:31px;overflow:hidden;background-image:linear-gradient(rgba(255,246,224,.03),rgba(68,38,20,.04)),url('/static/chankocchi_room_2d.png');background-size:cover;background-position:center;border:1px solid rgba(115,72,43,.15);box-shadow:0 18px 44px rgba(95,61,37,.16);isolation:isolate}
.life-room:after{content:'';position:absolute;z-index:2;left:4%;right:4%;bottom:4%;height:10%;border-radius:50%;background:radial-gradient(ellipse,rgba(49,27,13,.20),transparent 68%);pointer-events:none}.window,.cloud,.shelf,.table{display:none}
.speech-bubble{position:absolute;z-index:10;top:14px;left:14px;max-width:64%;padding:10px 13px;border-radius:17px 17px 17px 5px;background:rgba(255,255,255,.93);box-shadow:0 5px 18px rgba(61,37,18,.12);font-size:12px;font-weight:900;color:#46352A;backdrop-filter:blur(5px)}
.chanko-character{position:absolute!important;z-index:6;width:91px!important;height:91px!important;left:38%;bottom:8%;background-image:url('/static/chankocchi_life_sprites.png');background-repeat:no-repeat;background-size:400% 100%;filter:drop-shadow(0 7px 4px rgba(49,29,16,.28));transition:left 3.8s cubic-bezier(.42,0,.58,1),bottom 3.8s ease;transform-origin:50% 94%;will-change:left,bottom,transform}
.pose-walk-a{background-position:0 0}.pose-walk-b{background-position:33.333% 0}.pose-sit{background-position:66.666% 0;animation:living-breath 3.8s ease-in-out infinite}.pose-sleep{background-position:100% 0;animation:sleep-breath 4.8s ease-in-out infinite}.is-walking{animation:step-bob .42s ease-in-out infinite}.facing-left{transform:scaleX(-1)}
.mode-eating .chanko-character{left:61%;bottom:8%;background-position:66.666% 0;animation:nibble .65s ease-in-out infinite}.mode-bath .chanko-character{left:83%;bottom:11%;width:72px!important;height:72px!important;background-position:66.666% 0;animation:bob 1s ease-in-out infinite}.mode-playing .chanko-character{left:42%;bottom:8%;background-position:0 0;animation:hop .72s ease-in-out infinite}
.action-prop{position:absolute;z-index:8}.food-prop{font-size:29px;left:68%;bottom:16%}.bath-prop{font-size:63px;left:82%;bottom:5%;z-index:7}.bubble-prop{position:absolute;z-index:9;left:87%;bottom:32%;font-size:18px;color:white;animation:bubbles 1.7s ease-out infinite}.play-prop{font-size:32px;left:51%;bottom:31%}
.meter-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:11px 0}.meter-card{padding:9px 8px;border-radius:14px;background:rgba(255,255,255,.74);font-size:9px;font-weight:900;color:#725945}.care-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.care-button{background:#fff!important;color:#543E30!important;min-height:53px!important;border-radius:16px!important}.growth-card,.store-link{margin-top:11px;padding:15px!important;border-radius:21px!important;border:1px solid rgba(120,81,51,.12)!important;box-shadow:0 8px 22px rgba(93,61,39,.07)!important}.growing-chip{font-size:9px;font-weight:900;padding:6px 9px;border-radius:999px;background:#E8EFEA;color:#52685A}.store-link{background:linear-gradient(135deg,#284E3E,#4E8064)!important;color:#fff!important}.store-open{color:white!important}.store-reward{background:#FFE09A!important;color:#5C421B!important}.choice-dialog{width:min(92vw,440px)!important;padding:22px!important;border-radius:25px!important}.food-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;margin-top:12px}.food-choice{min-height:58px!important;border-radius:16px!important;background:#FFF7E5!important;color:#49382D!important}.mini-area{position:relative;height:260px;margin-top:12px;border-radius:20px;background:linear-gradient(#BDE4EC,#F7E0A7 65%,#8FC574 65%);overflow:hidden}.mini-target{position:absolute!important;left:42%;top:38%;font-size:27px!important;transition:left .15s,top .15s}.mini-score{text-align:center;font-size:19px;font-weight:950;color:#5C421B}
@keyframes living-breath{0%,100%{transform:translateY(0) rotate(-.5deg)}50%{transform:translateY(-3px) rotate(.8deg)}}@keyframes sleep-breath{50%{transform:scale(.975) translateY(1px)}}@keyframes step-bob{0%,100%{margin-bottom:0}50%{margin-bottom:4px}}@keyframes nibble{50%{transform:translateY(3px) rotate(1.5deg)}}@keyframes bob{50%{transform:translateY(-4px)}}@keyframes hop{50%{transform:translateY(-15px) rotate(3deg)}}@keyframes bubbles{to{transform:translateY(-30px);opacity:0}}
@media(max-width:390px){.life-room{min-height:250px}.chanko-character{width:78px!important;height:78px!important}.care-button{font-size:11px!important}}
'''


CHANKO_LIFE_SCRIPT = r'''
(() => {
  if (window.__chankoLifeTimer) clearTimeout(window.__chankoLifeTimer);
  if (window.__chankoStepTimer) clearInterval(window.__chankoStepTimer);
  const actor = document.querySelector('.life-room.mode-living .chanko-character');
  if (!actor) return;
  const places = [
    {left: '8%', bottom: '8%', stay: 7600, pose: 'sleep'},
    {left: '31%', bottom: '8%', stay: 4300, pose: 'sit'},
    {left: '53%', bottom: '8%', stay: 5200, pose: 'sit'},
    {left: '70%', bottom: '8%', stay: 4600, pose: 'sit'},
  ];
  let current = 1;
  const setPose = pose => {
    actor.classList.remove('pose-walk-a','pose-walk-b','pose-sit','pose-sleep','is-walking');
    actor.classList.add(`pose-${pose}`);
  };
  const live = () => {
    const choices = places.map((_, i) => i).filter(i => i !== current);
    const next = choices[Math.floor(Math.random() * choices.length)];
    const destination = places[next];
    const goingLeft = next < current;
    actor.classList.toggle('facing-left', goingLeft);
    actor.classList.add('is-walking');
    let foot = false;
    window.__chankoStepTimer = setInterval(() => {
      foot = !foot;
      actor.classList.toggle('pose-walk-a', foot);
      actor.classList.toggle('pose-walk-b', !foot);
      actor.classList.remove('pose-sit','pose-sleep');
    }, 320);
    requestAnimationFrame(() => { actor.style.left = destination.left; actor.style.bottom = destination.bottom; });
    window.__chankoLifeTimer = setTimeout(() => {
      clearInterval(window.__chankoStepTimer);
      current = next;
      actor.classList.remove('facing-left');
      setPose(destination.pose);
      window.__chankoLifeTimer = setTimeout(live, destination.stay + Math.random() * 3500);
    }, 3850);
  };
  setPose('sit');
  window.__chankoLifeTimer = setTimeout(live, 3800);
})();
'''
