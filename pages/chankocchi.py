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
                    ui.element('div').classes('actor-shadow')
                    if mode == 'eating':
                        with ui.element('div').classes('meal-bowl'):
                            ui.element('i').classes('steam steam-one'); ui.element('i').classes('steam steam-two')
                    if mode == 'bath':
                        ui.element('div').classes('bath-tub')
                        ui.element('div').classes('bath-bubbles')
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
                ui.label('厨房ライブボードと、今後追加するタスクの実績を確認します').classes('text-[10px] opacity-80')
                with ui.row().classes('w-full gap-2 q-mt-sm'):
                    ui.button('店舗運営へ', icon='storefront', on_click=open_store).props('flat no-caps').classes('grow store-open')
                    reward_label = '受取済' if today_claimed else '+10枚' if store_done else '未達成'
                    ui.button(reward_label, on_click=store_reward).props('unelevated no-caps').classes('store-reward').set_enabled(not today_claimed)
            if can_depart(profile): ui.button('次の世代を迎える', on_click=next_generation).props('unelevated no-caps color=deep-orange-7').classes('w-full q-mt-md')
        ui.add_css(CHANKO_CSS)
        if mode == 'living':
            ui.run_javascript(CHANKO_LIFE_SCRIPT)
        else:
            action_x = {'eating': 360, 'bath': 560, 'playing': 220}.get(mode, 0)
            ui.run_javascript(
                f"requestAnimationFrame(()=>document.querySelector('.life-viewport')?.scrollTo({{left:{action_x},behavior:'smooth'}}))"
            )
    save(); render()


CHANKO_CSS = '''
.chanko-app{min-height:100vh;width:min(100%,680px);margin:0 auto;padding:18px 16px 54px;background:linear-gradient(180deg,#FFF8E8,#F3E2C7);box-sizing:border-box}
.chanko-logo{font-size:27px;font-weight:950;color:#3C2D24}.chanko-sub{font-size:10px;font-weight:800;color:#8A6F59}.coin-pill{padding:8px 13px;border-radius:999px;background:#3C2D24;color:#FFD980;font-weight:900}.chanko-top{padding:2px 3px 12px}
.life-viewport{width:100%;overflow-x:auto;overflow-y:hidden;border-radius:31px;box-shadow:0 18px 44px rgba(95,61,37,.16);scrollbar-width:thin;scroll-snap-type:x proximity;overscroll-behavior-x:contain;-webkit-overflow-scrolling:touch}
.life-room{position:relative;width:820px;height:461px;max-width:none;overflow:hidden;background-image:linear-gradient(rgba(255,246,224,.03),rgba(68,38,20,.04)),url('/static/chankocchi_room_2d.png');background-size:100% 100%;background-position:center;border:1px solid rgba(115,72,43,.15);isolation:isolate;scroll-snap-align:start}
.life-room.time-evening{filter:saturate(.94) brightness(.9)}.life-room.time-night{filter:saturate(.78) brightness(.7)}.life-room.time-morning{filter:saturate(1.04) brightness(1.04)}
.life-room:after{content:'';position:absolute;z-index:2;left:4%;right:4%;bottom:4%;height:10%;border-radius:50%;background:radial-gradient(ellipse,rgba(49,27,13,.20),transparent 68%);pointer-events:none}.window,.cloud,.shelf,.table{display:none}
.speech-bubble{position:absolute;z-index:10;top:14px;left:14px;max-width:64%;padding:10px 13px;border-radius:17px 17px 17px 5px;background:rgba(255,255,255,.93);box-shadow:0 5px 18px rgba(61,37,18,.12);font-size:12px;font-weight:900;color:#46352A;backdrop-filter:blur(5px)}
.life-status{position:absolute;z-index:10;right:13px;top:13px;display:flex;align-items:center;gap:6px;padding:7px 10px;border-radius:999px;background:rgba(49,39,30,.66);color:white;backdrop-filter:blur(7px);font-size:9px;font-weight:850}.life-status-dot{width:7px;height:7px;border-radius:50%;background:#91E4A7;box-shadow:0 0 0 4px rgba(145,228,167,.14);animation:alive-pulse 2.2s ease-in-out infinite}.sunbeam{position:absolute;z-index:1;left:39%;top:14%;width:30%;height:67%;background:linear-gradient(115deg,rgba(255,239,177,.18),transparent 70%);transform:skewX(-13deg);pointer-events:none;animation:sun-shift 12s ease-in-out infinite alternate}.living-trace{position:absolute;z-index:4;pointer-events:none;opacity:.78}.trace-book{left:72%;bottom:18%;width:29px;height:20px;border-radius:3px;background:#34576D;transform:rotate(-7deg);box-shadow:3px 3px 0 #EEE0BD}.trace-cup{left:59%;bottom:27%;width:14px;height:15px;border-radius:2px 2px 6px 6px;background:#F1E8D4;border:2px solid #48768B}.trace-cup:after{content:'';position:absolute;right:-7px;top:2px;width:7px;height:7px;border:2px solid #48768B;border-left:0;border-radius:0 6px 6px 0}
.chanko-character{position:absolute!important;z-index:6;width:103px!important;height:103px!important;left:38%;bottom:18%;background-image:url('/static/chankocchi_life_sprites.png');background-repeat:no-repeat;background-size:400% 100%;filter:drop-shadow(0 7px 4px rgba(49,29,16,.28));transition:left 3.8s cubic-bezier(.42,0,.58,1),bottom 3.8s ease,scale 1.2s ease;transform-origin:50% 94%;will-change:left,bottom,transform}
.actor-shadow{position:absolute;z-index:5;left:39%;bottom:17%;width:76px;height:17px;border-radius:50%;background:rgba(45,25,13,.2);filter:blur(3px);transition:left 3.8s cubic-bezier(.42,0,.58,1),bottom 3.8s ease,width 1s;pointer-events:none}
.pose-walk-a{background-position:0 0}.pose-walk-b{background-position:33.333% 0}.pose-sit{background-position:66.666% 0;animation:living-breath 3.8s ease-in-out infinite}.pose-sleep{background-position:100% 0;animation:sleep-breath 4.8s ease-in-out infinite}.is-walking{animation:step-bob .42s ease-in-out infinite}.facing-left{transform:scaleX(-1)}
.is-looking{animation:curious-look 1.8s ease-in-out}.is-excited{animation:happy-hop .48s ease-in-out 3}.is-grooming{animation:groom 1.1s ease-in-out 2}.is-listening{animation:ear-listen .8s ease-in-out 2}
.mode-eating .chanko-character{left:58%;bottom:18%;background-position:66.666% 0;animation:nibble .65s ease-in-out infinite}.mode-bath .chanko-character{left:87%;bottom:24%;width:76px!important;height:76px!important;background-position:66.666% 0;animation:bob 1s ease-in-out infinite}.mode-playing .chanko-character{left:42%;bottom:18%;background-position:0 0;animation:hop .72s ease-in-out infinite}
.action-prop{position:absolute;z-index:8}.play-prop{font-size:32px;left:50%;bottom:39%}.meal-bowl{position:absolute;z-index:8;left:64%;bottom:25%;width:54px;height:20px;border-radius:5px 5px 24px 24px;background:linear-gradient(#F8F1DF 0 28%,#31536B 29% 45%,#E8DED0 46%);box-shadow:0 5px 8px rgba(54,30,14,.25)}.meal-bowl:after{content:'';position:absolute;left:7px;right:7px;top:-5px;height:9px;border-radius:50%;background:#A96539;box-shadow:inset 0 2px #F4C06A}.steam{position:absolute;top:-23px;width:7px;height:20px;border-left:2px solid rgba(255,255,255,.84);border-radius:50%;animation:steam-rise 1.6s ease-in-out infinite}.steam-one{left:16px}.steam-two{left:32px;animation-delay:-.7s}.bath-tub{position:absolute;z-index:7;right:2.2%;bottom:15%;width:113px;height:57px;border-radius:15px 15px 34px 34px;background:linear-gradient(180deg,#EAF4F4,#99BEC2);border:4px solid #F6FFFF;box-shadow:0 7px 12px rgba(25,45,49,.24)}.bath-tub:before{content:'';position:absolute;left:5px;right:5px;top:-9px;height:18px;border-radius:50%;background:#CDE8E8;border:3px solid white}.bath-bubbles{position:absolute;z-index:9;right:6%;bottom:26%;width:65px;height:34px;background:radial-gradient(circle at 14% 65%,#fff 0 6px,transparent 7px),radial-gradient(circle at 37% 38%,#fff 0 8px,transparent 9px),radial-gradient(circle at 62% 62%,#fff 0 7px,transparent 8px),radial-gradient(circle at 85% 31%,#fff 0 6px,transparent 7px);animation:bubble-float 1.8s ease-in-out infinite}
.meter-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:11px 0}.meter-card{padding:9px 8px;border-radius:14px;background:rgba(255,255,255,.74);font-size:9px;font-weight:900;color:#725945}.care-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.care-button{background:#fff!important;color:#543E30!important;min-height:53px!important;border-radius:16px!important}.growth-card,.store-link{margin-top:11px;padding:15px!important;border-radius:21px!important;border:1px solid rgba(120,81,51,.12)!important;box-shadow:0 8px 22px rgba(93,61,39,.07)!important}.growing-chip{font-size:9px;font-weight:900;padding:6px 9px;border-radius:999px;background:#E8EFEA;color:#52685A}.store-link{background:linear-gradient(135deg,#284E3E,#4E8064)!important;color:#fff!important}.store-open{color:white!important}.store-reward{background:#FFE09A!important;color:#5C421B!important}.choice-dialog{width:min(92vw,440px)!important;padding:22px!important;border-radius:25px!important}.food-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;margin-top:12px}.food-choice{min-height:58px!important;border-radius:16px!important;background:#FFF7E5!important;color:#49382D!important}.mini-area{position:relative;height:260px;margin-top:12px;border-radius:20px;background:linear-gradient(#BDE4EC,#F7E0A7 65%,#8FC574 65%);overflow:hidden}.mini-target{position:absolute!important;left:42%;top:38%;font-size:27px!important;transition:left .15s,top .15s}.mini-score{text-align:center;font-size:19px;font-weight:950;color:#5C421B}
@keyframes living-breath{0%,100%{transform:translateY(0) rotate(-.5deg)}35%{transform:translateY(-2px) rotate(.4deg)}65%{transform:translateY(-3px) rotate(.8deg)}}@keyframes sleep-breath{50%{transform:scale(.965) translateY(2px)}}@keyframes step-bob{0%,100%{margin-bottom:0}50%{margin-bottom:5px}}@keyframes curious-look{0%,100%{transform:rotate(0)}28%{transform:rotate(-6deg)}70%{transform:rotate(5deg)}}@keyframes happy-hop{50%{transform:translateY(-12px) scale(1.04)}}@keyframes groom{35%{transform:rotate(-7deg) scale(.98)}70%{transform:rotate(5deg)}}@keyframes ear-listen{50%{transform:translateY(-2px) scaleY(1.025)}}@keyframes nibble{50%{transform:translateY(3px) rotate(1.5deg)}}@keyframes bob{50%{transform:translateY(-4px)}}@keyframes hop{50%{transform:translateY(-15px) rotate(3deg)}}@keyframes steam-rise{0%{transform:translateY(5px) scale(.8);opacity:0}45%{opacity:.9}100%{transform:translateY(-12px) translateX(4px);opacity:0}}@keyframes bubble-float{50%{transform:translateY(-5px) rotate(2deg)}}@keyframes alive-pulse{50%{opacity:.48;transform:scale(.82)}}@keyframes sun-shift{to{transform:translateX(12px) skewX(-13deg);opacity:.68}}
@media(min-width:900px){.life-room{width:900px;height:506px}}@media(max-width:390px){.care-button{font-size:11px!important}}
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
  const bubble = room.querySelector('.speech-bubble .q-label');
  const status = room.querySelector('.life-status-label');
  const routine = room.dataset.routine || 'wander';
  const places = {
    bed:     {left:  '5%', bottom:'18%', stay:[9000,15000], pose:'sleep', scale:.84, label:'お気に入りの場所で休んでる'},
    kitchen: {left: '27%', bottom:'18%', stay:[4200, 7600], pose:'sit',   scale:.92, label:'台所の匂いを気にしてる'},
    window:  {left: '45%', bottom:'19%', stay:[6500,11000], pose:'sit',   scale:.94, label:'窓の外を眺めてる'},
    table:   {left: '62%', bottom:'17%', stay:[5000, 9000], pose:'sit',   scale:1.0, label:'テーブルのそばでのんびり'},
    book:    {left: '70%', bottom:'18%', stay:[5200, 9200], pose:'sit',   scale:.94, label:'本が気になってる'},
    bath:    {left: '88%', bottom:'18%', stay:[3800, 6500], pose:'sit',   scale:.86, label:'お風呂をのぞいてる'},
  };
  const keys = Object.keys(places);
  const preferred = {
    wait_food:['kitchen','table'], want_bath:['bath','book'], seek_play:['table','window'],
    sleepy:['bed','window'], window:['window','kitchen'], wander:keys,
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
  };
  const moveTo = (next, after) => {
    if (busy || next === current) return after?.();
    busy = true;
    const destination = places[next];
    const goingLeft = keys.indexOf(next) < keys.indexOf(current);
    actor.classList.toggle('facing-left', goingLeft);
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
      if (room && viewport) {
        const targetX = parseFloat(destination.left) / 100 * room.clientWidth;
        viewport.scrollTo({left: Math.max(0, targetX - viewport.clientWidth / 2), behavior: 'smooth'});
      }
    });
    window.__chankoLifeTimer = setTimeout(() => {
      clearInterval(window.__chankoStepTimer);
      busy = false; settle(next); after?.();
    }, 3900);
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
  settle(current);
  actor.onclick = () => {
    if (busy) return;
    actor.classList.remove('is-looking','is-grooming','is-listening');
    actor.classList.add('is-excited');
    say(routine==='wait_food' ? 'お腹すいた！' : routine==='seek_play' ? 'あそぼ！' : '呼んだ？');
    setTimeout(()=>actor.classList.remove('is-excited'),1700);
  };
  actor.onkeydown = event => { if(event.key==='Enter'||event.key===' '){event.preventDefault();actor.click();} };
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && !busy) { idleMoment(); say('おかえり！'); }
  }, {once:true});
  window.__chankoLifeTimer = setTimeout(live, 4500 + Math.random()*2600);
})();
'''
