from nicegui import ui

from core.auth import require_app_access, selected_user_id
from core.daiou import (derived_identity, diplomatic_label, end_alliance,
                         initial_game, map_cell, nation, normalize_game,
                         perform_map_action, propose_alliance, relation, strength)
from core.data import data
from core.theme import Theme

TERRAIN_ICON={"plain":"·","forest":"♣","hill":"▲","river":"≈"}
STRUCTURE_ICON={"capital":"城","town":"町","fort":"砦",None:""}

@ui.page('/daiou')
def daiou_page():
    if not require_app_access('daiou'): return
    Theme.page('大王',app_name='daiou')
    user_id=selected_user_id(); games=data.data.setdefault('daiou',{}).setdefault('profiles',{})
    game=games.setdefault(user_id,initial_game()); normalize_game(game); state={"selected":None,"view":"home","event":None}; data.save()

    def save(): games[user_id]=game; data.save()

    def act(action,target=None):
        if not state["selected"]: ui.notify('先に金色の自国領を選んでください',type='warning'); return
        try:
            message=perform_map_action(game,action,state["selected"],target); save(); ui.notify(message,type='positive')
            state['event']={'kind':'battle' if '戦力' in message else ('occupy' if '領土' in message or '野営' in message else 'order'),'message':message}
            current=map_cell(game,state["selected"])
            if current["owner"]!=game["player"] and (current.get('claim') or {}).get('owner')!=game['player']: state["selected"]=None
            render.refresh()
        except ValueError as error: ui.notify(str(error),type='warning')

    def select_cell(cell_id):
        cell=map_cell(game,cell_id)
        if cell["owner"]==game["player"] or (cell.get('claim') or {}).get('owner')==game['player']:
            state["selected"]=cell_id; render.refresh()
        elif state["selected"]: act('advance',cell_id)
        else: ui.notify('金色の自国領から選びます',type='info')

    def continue_game():
        state['view']='game'; render.refresh()

    def return_home():
        state.update(view='home',selected=None,event=None); save(); render.refresh()

    def dismiss_event():
        state['event']=None; render.refresh()

    def negotiate(target_id,kind='propose'):
        try:
            message=propose_alliance(game,target_id) if kind=='propose' else end_alliance(game,target_id)
            state['event']={'kind':'order','message':message}; save(); render.refresh()
        except ValueError as error: ui.notify(str(error),type='warning')

    def new_game():
        replacement=initial_game(); game.clear(); game.update(replacement)
        state.update(view='game',selected=None); save(); new_game_dialog.close(); render.refresh()

    with ui.dialog() as new_game_dialog, ui.card().classes('new-game-dialog'):
        ui.label('新しく国を興しますか？').classes('text-xl font-black')
        ui.label('現在の続きは消えて、最初の状態に戻ります。').classes('text-sm text-grey-7')
        with ui.row().classes('w-full justify-end q-mt-md'):
            ui.button('やめる',on_click=new_game_dialog.close).props('flat no-caps')
            ui.button('新しく始める',on_click=new_game).props('unelevated no-caps color=negative')

    @ui.refreshable
    def render():
        player=nation(game,game['player']); selected=map_cell(game,state["selected"]) if state["selected"] else None
        with ui.element('main').classes('daiou-app'):
            if state['view']=='home':
                with ui.element('section').classes('daiou-home'):
                    ui.image('/static/daiou_icon.png').classes('daiou-home-icon')
                    ui.label('大 王').classes('daiou-home-title')
                    ui.label('十国の思惑を読み、己の国を治めよ').classes('daiou-home-copy')
                    with ui.element('div').classes('home-status'):
                        ui.label(f"第{game['turn']}季・{game['season']}").classes('home-turn')
                        ui.label(f"{player['name']}　領土 {player['territory']}　兵力 {sum(x['troops'] for x in game['map'] if x['owner']==game['player'])}").classes('home-realm')
                    ui.button('続きから',icon='play_arrow',on_click=continue_game).props('unelevated no-caps').classes('continue-button')
                    ui.button('新しく始める',on_click=new_game_dialog.open).props('flat no-caps').classes('new-button')
                ui.add_css(DAIOU_CSS+DAIOU_BATTLE_CSS)
                return
            with ui.element('section').classes('daiou-hero'):
                ui.button(icon='home',on_click=return_home).props('flat round aria-label="大王ホームへ戻る"').classes('battle-home-button')
                ui.label('大 王').classes('daiou-title'); ui.label('選んだ方針ではなく、積み重ねた行動が国を作る。').classes('daiou-copy')
                ui.label(f"第{game['turn']}季・{game['season']}").classes('turn-chip')
                ui.label(f"国の姿：{derived_identity(player)}").classes('identity-chip')
            with ui.element('div').classes('realm-grid'):
                for label,value in (("国力",strength(player)),("領土",player['territory']),("軍資金",player['wealth']),("兵力",sum(x['troops'] for x in game['map'] if x['owner']==game['player']))):
                    with ui.element('div').classes('realm-stat'): ui.label(label); ui.label(str(value)).classes('realm-value')
            fronts=[]
            for cell in game['map']:
                if not cell['owner']: continue
                if any(x['owner'] not in {None,cell['owner']} for x in game['map'] if abs(x['row']-cell['row'])+abs(x['col']-cell['col'])==1): fronts.append(cell)
            camps=[x for x in game['map'] if x.get('claim')]
            with ui.element('section').classes('war-status'):
                ui.label('戦況').classes('war-status-title')
                ui.label(f"国境の緊張 {len(fronts)}か所").classes('war-status-item danger' if fronts else 'war-status-item')
                ui.label(f"領土化中 {len(camps)}陣").classes('war-status-item')
            if game.get('coalition'):
                members='・'.join(nation(game,x)['name'] for x in game['coalition']['members'])
                with ui.element('section').classes('coalition-alert'):
                    ui.label('合従軍').classes('coalition-title'); ui.label(f"{members}があなたの国を包囲しています").classes('coalition-copy')
            ui.label('天下盤').classes('daiou-heading'); ui.label('金色の自国領を選び、隣の土地をタップして進みます').classes('map-guide')
            with ui.element('div').classes('world-scroll'):
                with ui.element('div').classes('world-map'):
                    for cell in game['map']:
                        classes=f"map-cell terrain-{cell['terrain']} "
                        classes+=f"owner-{cell['owner']}" if cell['owner'] else 'neutral'
                        neighbors=[x for x in game['map'] if abs(x['row']-cell['row'])+abs(x['col']-cell['col'])==1]
                        if cell['owner'] and any(x['owner'] not in {None,cell['owner']} for x in neighbors): classes+=' frontline'
                        if cell['id']==state['selected']: classes+=' selected'
                        with ui.element('button').classes(classes).on('click',lambda _,cid=cell['id']:select_cell(cid)):
                            ui.label(TERRAIN_ICON[cell['terrain']]).classes('terrain-mark')
                            if cell.get('structure'): ui.label(STRUCTURE_ICON[cell['structure']]).classes('structure-mark')
                            if cell.get('claim'):
                                claim_nation=nation(game,cell['claim']['owner'])
                                progress=cell['claim'].get('progress',0)
                                ui.label(f"陣 {progress}/2").classes(f"claim-mark claim-{claim_nation['id']}").tooltip(f"{claim_nation['name']}の野営地・領土化 {progress}/2")
                            if cell['owner']:
                                ui.label(nation(game,cell['owner'])['name'][:1]).classes('owner-mark')
                            if cell['owner'] or cell.get('claim'): ui.label(f"⚔ {cell['troops']}").classes('troop-mark')
                            if cell['owner'] or cell.get('claim'):
                                flag_owner=cell['owner'] or cell['claim']['owner']
                                ui.label('⚑').classes(f"army-flag flag-{flag_owner}")
                                ui.label('♟♟♟').classes('army-rank')
            with ui.element('section').classes('command-panel'):
                if selected:
                    claim=selected.get('claim') or {}
                    if claim.get('owner')==game['player'] and selected['owner'] is None:
                        progress=claim.get('progress',0)
                        ui.label(f"先遣隊の野営地　兵 {selected['troops']}").classes('selected-title')
                        ui.label(f"領土化 {progress}/2　ここを守りながら2ターン統治を進めます").classes('selected-help')
                        with ui.element('div').classes('occupation-progress'):
                            for step in range(2): ui.element('span').classes('occupation-seal'+(' done' if step<progress else ''))
                        ui.button('領土化を進める',icon='flag',on_click=lambda:act('occupy')).props('unelevated no-caps').classes('occupy-button')
                    else:
                        owner=nation(game,selected['owner'])
                        ui.label(f"選択中：{owner['name']} {selected['id']}　兵 {selected['troops']}").classes('selected-title')
                        ui.label('隣の地域を押すと、軍が進みます').classes('selected-help')
                        with ui.element('div').classes('command-grid'):
                            ui.button('兵を集める 5',icon='groups',on_click=lambda:act('recruit')).props('flat no-caps')
                            ui.button('町を築く 10',icon='holiday_village',on_click=lambda:act('town')).props('flat no-caps')
                            ui.button('砦を築く 8',icon='fort',on_click=lambda:act('fort')).props('flat no-caps')
                            ui.button('隣国と交易',icon='handshake',on_click=lambda:act('trade')).props('flat no-caps')
                else: ui.label('まず金色の自国領をタップ').classes('empty-command')
            with ui.expansion('十国の現在',icon='public').classes('nation-box w-full'):
                for item in sorted(game['nations'],key=strength,reverse=True):
                    with ui.element('div').classes('nation-row'+(' player' if item['id']==game['player'] else '')):
                        ui.label(('あなた・' if item['id']==game['player'] else '')+item['name']).classes('font-black grow')
                        action=max(item.get('actions',{}),key=item.get('actions',{}).get)
                        intent={'expand':'↗ 拡大','trade':'⇄ 交易','build':'▣ 建設','defend':'⬟ 防衛','battle':'⚔ 交戦'}[action]
                        ui.label(f"{intent}　領土 {item['territory']}").classes('nation-detail')
                        if item['id']!=game['player']:
                            status=diplomatic_label(game,game['player'],item['id'])
                            ui.label(status).classes('relation-chip '+relation(game,game['player'],item['id'])['status'])
                            if status in {'同盟','不可侵'}:
                                ui.button('破棄',on_click=lambda _,nid=item['id']:negotiate(nid,'end')).props('flat dense no-caps').classes('diplomacy-button danger')
                            else:
                                ui.button('同盟提案',on_click=lambda _,nid=item['id']:negotiate(nid)).props('flat dense no-caps').classes('diplomacy-button')
            with ui.expansion('国史',icon='history').classes('nation-box w-full'):
                for line in game.get('log',[]): ui.label(line).classes('history-line')
            if state.get('event'):
                event=state['event']
                with ui.element('div').classes(f"battle-event {event['kind']}").on('click',lambda _:dismiss_event()):
                    ui.label('⚔' if event['kind']=='battle' else ('旗' if event['kind']=='occupy' else '令')).classes('battle-event-mark')
                    ui.label('合戦報' if event['kind']=='battle' else ('領土報' if event['kind']=='occupy' else '軍令')).classes('battle-event-title')
                    ui.label(event['message']).classes('battle-event-message')
                    ui.label('タップして閉じる').classes('battle-event-close')
        ui.add_css(DAIOU_CSS+DAIOU_BATTLE_CSS)
        ui.run_javascript(DAIOU_MAP_MEMORY_SCRIPT)
    render()

DAIOU_MAP_MEMORY_SCRIPT = r'''
(() => {
  requestAnimationFrame(() => {
    const scroller = document.querySelector('.world-scroll');
    if (!scroller) return;
    scroller.scrollLeft = Number(sessionStorage.getItem('daiou-map-x') || 0);
    scroller.scrollTop = Number(sessionStorage.getItem('daiou-map-y') || 0);
    scroller.addEventListener('scroll', () => {
      sessionStorage.setItem('daiou-map-x', scroller.scrollLeft);
      sessionStorage.setItem('daiou-map-y', scroller.scrollTop);
    }, {passive: true});
  });
})();
'''

DAIOU_BATTLE_CSS='''
.map-cell.frontline:after{content:'⚔';position:absolute;right:4px;top:23px;font-size:11px;color:#FFD36E;filter:drop-shadow(0 0 5px #D83A2E);animation:battlePulse 1.25s ease-in-out infinite}
.claim-mark{left:18px!important;top:18px!important;width:auto!important;height:24px!important;padding:0 6px!important;border-radius:8px!important;background:linear-gradient(135deg,#F3D68B,#B88635)!important}
.occupation-progress{display:flex;gap:8px;margin:10px 0}.occupation-seal{display:block;width:26px;height:8px;border-radius:99px;background:rgba(255,255,255,.14);border:1px solid rgba(240,201,111,.35)}
.occupation-seal.done{background:#EFCB78;box-shadow:0 0 10px rgba(239,203,120,.5)}.occupy-button{width:100%;min-height:44px!important;background:linear-gradient(135deg,#B98332,#F0CE78)!important;color:#152018!important;font-weight:950!important;border-radius:13px!important}
@keyframes battlePulse{50%{transform:scale(1.24);filter:drop-shadow(0 0 10px #FF4D35)}}
.war-status{display:flex;align-items:center;gap:7px;margin:0 0 9px;padding:9px 11px;border-radius:13px;background:linear-gradient(90deg,rgba(118,30,24,.72),rgba(25,39,31,.85));border:1px solid rgba(238,187,92,.24)}.war-status-title{font-family:serif;font-size:12px;font-weight:950;color:#FFD98A;margin-right:auto}.war-status-item{padding:4px 7px;border-radius:99px;background:rgba(255,255,255,.08);font-size:8px;font-weight:900}.war-status-item.danger{color:#FFD2A0;box-shadow:inset 0 0 0 1px rgba(255,102,70,.35)}
.army-flag{position:absolute;left:7px;top:17px;font-size:17px;z-index:2;color:#F8D77E;text-shadow:0 2px 3px #000}.army-rank{position:absolute;left:20px;top:29px;font-size:7px;letter-spacing:-2px;color:#F3E4C5;text-shadow:0 1px 2px #000;opacity:.88}.frontline{animation:frontGlow 1.7s ease-in-out infinite}.frontline .army-rank{color:#FFD7A0}.battle-event{position:fixed;z-index:9999;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:34px;text-align:center;background:radial-gradient(circle,rgba(104,25,18,.94),rgba(3,7,8,.96) 62%);animation:eventEnter .34s ease-out}.battle-event.occupy{background:radial-gradient(circle,rgba(82,66,20,.94),rgba(3,9,8,.96) 62%)}.battle-event.order{background:radial-gradient(circle,rgba(24,68,52,.94),rgba(3,9,8,.96) 62%)}.battle-event-mark{font-family:serif;font-size:84px;line-height:1;color:#FFD071;filter:drop-shadow(0 0 20px rgba(255,86,45,.75));animation:markStrike .55s ease-out}.battle-event-title{margin-top:14px;font-family:serif;font-size:27px;font-weight:950;letter-spacing:.28em;color:#FFE6A9}.battle-event-message{max-width:340px;margin-top:16px;font-size:13px;font-weight:900;line-height:1.8;color:#FFF5DC}.battle-event-close{margin-top:24px;font-size:9px;opacity:.55}@keyframes frontGlow{50%{filter:brightness(1.16)}}@keyframes eventEnter{from{opacity:0;transform:scale(1.08)}}@keyframes markStrike{0%{transform:scale(2) rotate(-10deg);opacity:0}65%{transform:scale(.88) rotate(3deg)}100%{transform:scale(1)}}
.coalition-alert{margin:0 0 10px;padding:12px 14px;border-radius:15px;background:linear-gradient(115deg,rgba(128,24,20,.9),rgba(62,25,24,.78));border:1px solid rgba(255,194,96,.42);box-shadow:0 8px 24px rgba(0,0,0,.22)}.coalition-title{font-family:serif;font-size:15px;font-weight:950;color:#FFD985}.coalition-copy{margin-top:3px;font-size:9px;font-weight:800;color:#F8E4C7}.relation-chip{margin-left:7px;padding:3px 7px;border-radius:999px;font-size:8px;font-weight:950;white-space:nowrap;background:rgba(255,255,255,.08)}.relation-chip.alliance{color:#91E8CA;background:rgba(33,130,104,.25)}.relation-chip.war{color:#FFB09F;background:rgba(176,43,34,.28)}.relation-chip.pact{color:#A9D7F3;background:rgba(48,111,154,.28)}.relation-chip.neutral{color:#C8C6BD}.diplomacy-button{margin-left:4px!important;min-height:28px!important;padding:0 7px!important;border-radius:9px!important;color:#EFD492!important;background:rgba(239,212,146,.09)!important;font-size:8px!important;font-weight:900!important}.diplomacy-button.danger{color:#FFAAA0!important;background:rgba(175,48,40,.16)!important}
@media(min-width:430px){.world-map{grid-template-columns:repeat(8,76px)!important;grid-template-rows:repeat(6,76px)!important}.map-cell{width:76px!important;height:76px!important}.army-flag{font-size:21px}.army-rank{font-size:9px;top:34px}}
@media(max-width:520px){.nation-row{flex-wrap:wrap;gap:4px}.nation-row>.grow{min-width:42%}.nation-detail{margin-left:auto}.diplomacy-button{margin-left:auto!important}}
'''

DAIOU_CSS='''
body{background:#071015!important}.daiou-home{min-height:calc(100vh - 84px);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:34px 20px;border-radius:30px;background:radial-gradient(circle at 50% 28%,rgba(212,166,75,.20),transparent 28%),linear-gradient(160deg,#152A24,#080F13 68%);border:1px solid rgba(226,184,96,.30);overflow:hidden}.daiou-home-icon{width:132px!important;height:132px!important;border-radius:29px;box-shadow:0 22px 60px rgba(0,0,0,.48),0 0 0 1px rgba(242,203,112,.38)}.daiou-home-title{margin-top:25px;font-family:serif;font-size:49px;font-weight:950;letter-spacing:.22em;color:#FFE5A0}.daiou-home-copy{margin-top:4px;font-size:11px;font-weight:800;color:#CFC5AC}.home-status{width:min(100%,360px);margin:32px 0 17px;padding:17px;border-radius:18px;background:rgba(255,255,255,.065);border:1px solid rgba(255,255,255,.08)}.home-turn{font-size:12px;font-weight:950;color:#EFCB78}.home-realm{margin-top:5px;font-size:10px;color:#D8D9D0}.continue-button{width:min(100%,360px);min-height:57px!important;border-radius:17px!important;background:linear-gradient(135deg,#C49340,#F0CE78)!important;color:#182019!important;font-size:16px!important;font-weight:950!important}.new-button{margin-top:8px;color:#B9B5A9!important}.new-game-dialog{width:min(92vw,430px)!important;padding:22px!important;border-radius:24px!important}.battle-home-button{position:absolute!important;z-index:5;left:14px;top:14px;color:#FFF0C5!important;background:rgba(3,10,12,.48)!important}
body{background:#071015!important}.daiou-app{width:min(100%,760px);min-height:100vh;margin:auto;padding:14px 14px 56px;color:#F5EBD2;background:radial-gradient(circle at 90% 0,#334B3C 0,transparent 27%),linear-gradient(180deg,#0B1820,#10130F)}.daiou-hero{position:relative;min-height:190px;padding:30px 22px;border-radius:28px;display:flex;flex-direction:column;justify-content:flex-end;overflow:hidden;background:linear-gradient(155deg,rgba(3,10,14,.1),rgba(3,8,7,.86)),radial-gradient(circle at 50% 20%,#B8863A,#26372D 48%,#0A1012 76%);border:1px solid rgba(226,184,96,.35)}.daiou-hero:before{content:'王';position:absolute;right:16px;top:-35px;font-size:175px;font-family:serif;font-weight:900;color:rgba(255,224,153,.11)}.daiou-title{font-family:serif;font-size:44px;font-weight:950;letter-spacing:.2em;color:#FFE5A0}.daiou-copy{font-size:10px;font-weight:800;opacity:.78}.turn-chip,.identity-chip{position:absolute;top:15px;padding:7px 10px;border-radius:999px;background:rgba(4,12,12,.64);font-size:9px;font-weight:900}.turn-chip{left:15px}.identity-chip{right:15px;color:#F0C96F}.realm-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:11px 0 16px}.realm-stat{padding:10px 8px;border-radius:14px;background:rgba(255,255,255,.07);font-size:8px;color:#B8C3B8}.realm-value{font-size:18px;font-weight:950;color:#FFF1C7}.daiou-heading{margin:9px 2px 2px;font-size:18px;font-weight:950}.map-guide{font-size:9px;opacity:.68;margin:0 2px 8px}.world-scroll{width:100%;overflow:auto;padding:5px 0 10px;scrollbar-width:thin;overscroll-behavior:contain}.world-map{display:grid;grid-template-columns:repeat(8,62px);grid-template-rows:repeat(6,62px);gap:4px;width:max-content;padding:8px;border-radius:18px;background:#06100E;border:1px solid rgba(240,201,111,.22)}.map-cell{position:relative;width:62px;height:62px;border:0;border-radius:12px;color:#EDE4CE;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(255,255,255,.08);transition:.16s transform,.16s box-shadow}.map-cell:active{transform:scale(.94)}.terrain-plain{background:#405C3D}.terrain-forest{background:#173D2B}.terrain-hill{background:#69563B}.terrain-river{background:linear-gradient(135deg,#315D70,#4B7B88)}.neutral{filter:saturate(.55) brightness(.72)}.owner-n0{box-shadow:inset 0 0 0 3px #F5CA69,0 0 13px rgba(245,202,105,.18)}.owner-n1{box-shadow:inset 0 0 0 3px #A8C7E8}.owner-n2{box-shadow:inset 0 0 0 3px #6DB8B2}.owner-n3{box-shadow:inset 0 0 0 3px #D86661}.owner-n4{box-shadow:inset 0 0 0 3px #E9E5D1}.owner-n5{box-shadow:inset 0 0 0 3px #82B66F}.owner-n6{box-shadow:inset 0 0 0 3px #A889C4}.owner-n7{box-shadow:inset 0 0 0 3px #CF9D5C}.owner-n8{box-shadow:inset 0 0 0 3px #62676C}.owner-n9{box-shadow:inset 0 0 0 3px #B1A9D8}.map-cell.selected{box-shadow:inset 0 0 0 4px #FFF,0 0 18px #FFD36E;transform:translateY(-3px)}.terrain-mark{position:absolute;left:7px;top:5px;font-size:15px;opacity:.42}.structure-mark{position:absolute;right:6px;top:5px;font-size:10px;font-weight:950;color:#FFF1B9}.owner-mark{position:absolute;right:6px;bottom:5px;font-size:8px;font-weight:950;opacity:.82}.claim-mark{position:absolute;left:24px;top:20px;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#F2D28A;color:#182018;font-size:9px;font-weight:950;box-shadow:0 0 0 2px rgba(0,0,0,.3)}.troop-mark{position:absolute;left:7px;bottom:5px;padding:2px 6px;border-radius:999px;background:rgba(2,7,7,.72);font-size:10px;font-weight:950}.command-panel{min-height:96px;margin-top:2px;padding:13px;border-radius:18px;background:linear-gradient(145deg,#21362D,#16231E);border:1px solid rgba(220,176,88,.22)}.selected-title{font-size:13px;font-weight:950;color:#F0C96F}.selected-help{font-size:8px;opacity:.65}.command-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:5px;margin-top:8px}.command-grid .q-btn{background:rgba(255,255,255,.07)!important;color:#F7E8C5!important;font-size:10px!important}.empty-command{text-align:center;padding:24px;font-weight:900;opacity:.6}.nation-box{margin-top:10px;border-radius:16px!important;background:rgba(255,255,255,.06)!important}.nation-row{display:flex;align-items:center;padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.06)}.nation-row.player{color:#F0C96F}.nation-detail{font-size:9px;opacity:.72}.history-line{padding:8px;border-bottom:1px solid rgba(255,255,255,.06);font-size:10px}@media(max-width:390px){.realm-grid{grid-template-columns:repeat(2,1fr)}.world-map{grid-template-columns:repeat(8,58px);grid-template-rows:repeat(6,58px)}.map-cell{width:58px;height:58px}}
'''
