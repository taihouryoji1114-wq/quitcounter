from nicegui import ui

from core.auth import require_app_access, selected_user_id
from core.daiou import (adjacent_cells, border_strain, command_capacity, commander_for_legion, commander_rank,
                         derived_identity, diplomatic_label, end_alliance,
                         end_turn, form_legion, initial_game, legion_at, map_cell, map_viewbox, nation, normalize_game,
                         perform_map_action, propose_alliance, relation,
                         region_income, region_shape, request_reinforcements, respond_to_diplomatic_offer, strength,
                         trade_with_nation,
                         terrain_effect)
from core.data import data
from core.theme import Theme

TERRAIN_ICON={"plain":"·","forest":"♣","hill":"▲","river":"≈"}
STRUCTURE_ICON={"capital":"城","town":"町","fort":"砦",None:""}
LEGION_STATUS={"marching":"行軍中","garrisoned":"駐屯中","waiting":"待機中"}

@ui.page('/daiou')
def daiou_page():
    if not require_app_access('daiou'): return
    Theme.page('大王',app_name='daiou')
    user_id=selected_user_id(); games=data.data.setdefault('daiou',{}).setdefault('profiles',{})
    game=games.setdefault(user_id,initial_game()); normalize_game(game); state={"selected":None,"inspect":None,"view":"home","event":None,"tactic":"direct","march":50,"last_move":None,"map_action":None,"map_zoom":100}; data.save()

    def save(): games[user_id]=game; data.save()

    def act(action,target=None):
        if not state["selected"]: ui.notify('先に金色の自国領を選んでください',type='warning'); return
        try:
            source=map_cell(game,state['selected'])
            march=max(2,min(source['troops']-1,round(source['troops']*state['march']/100))) if target else None
            message=perform_map_action(game,action,state["selected"],target,tactic=state['tactic'],march_troops=march); save(); ui.notify(message,type='positive')
            state['last_move']=(state['selected'],target) if target else None
            state['map_action']=None
            state['event']={'kind':'battle','message':message} if '戦力' in message else None
            current=map_cell(game,state["selected"])
            if current["owner"]!=game["player"] and (current.get('claim') or {}).get('owner')!=game['player']: state["selected"]=None
            render.refresh()
        except ValueError as error: ui.notify(str(error),type='warning')

    def create_legion():
        try:
            message=form_legion(game,state['selected']); save(); ui.notify(message,type='positive'); render.refresh()
        except ValueError as error: ui.notify(str(error),type='warning')

    def focus_legion(legion):
        state.update(selected=legion['location'],inspect=legion['location'])
        render.refresh()

    def select_cell(cell_id):
        cell=map_cell(game,cell_id)
        if state.get('map_action')=='transfer' and state.get('selected') and cell_id!=state['selected']:
            if cell.get('owner')==game['player']:
                act('transfer',cell_id); return
            ui.notify('兵の移動先は自国領から選んでください',type='warning'); return
        if cell["owner"]==game["player"] or (cell.get('claim') or {}).get('owner')==game['player']:
            state.update(selected=cell_id,inspect=cell_id); render.refresh()
        elif state["selected"]: act('advance',cell_id)
        else:
            state['inspect']=cell_id; render.refresh()

    def select_map_event(event):
        payload=event.args
        region=(payload.get('region') or payload.get('detail.region') or (payload.get('detail') or {}).get('region')) if isinstance(payload,dict) else payload
        if region: select_cell(str(region))

    def continue_game():
        state['view']='game'; render.refresh()

    def return_home():
        state.update(view='home',selected=None,event=None); save(); render.refresh()

    def dismiss_event():
        state['event']=None; render.refresh()

    def choose_tactic(tactic):
        state['tactic']=tactic; render.refresh()

    def choose_march(percent):
        state['march']=percent; render.refresh()

    def change_map_zoom(delta):
        state['map_zoom']=max(70,min(280,state['map_zoom']+delta)); render.refresh()

    def begin_transfer():
        if not state.get('selected'): ui.notify('兵を出す自国領を先に選んでください',type='warning'); return
        state['map_action']='transfer'; ui.notify('移動先の自国領を地図から選んでください'); render.refresh()

    def finish_turn():
        message=end_turn(game); state.update(selected=None,inspect=None,last_move=None)
        reports=game.get('turn_events',[])
        state['event']={'kind':'enemy_attack','message':message,'reports':reports} if reports else {'kind':'order','message':message}
        save(); render.refresh()

    def negotiate(target_id,kind='propose'):
        try:
            if kind=='support': message=request_reinforcements(game,target_id)
            elif kind=='propose': message=propose_alliance(game,target_id)
            elif kind=='trade': message=trade_with_nation(game,target_id)
            else: message=end_alliance(game,target_id)
            state['event']={'kind':'order','message':message}; save(); render.refresh()
        except ValueError as error: ui.notify(str(error),type='warning')

    def answer_offer(accept):
        try:
            message=respond_to_diplomatic_offer(game,accept); state['event']={'kind':'order','message':message}
            save(); render.refresh()
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
        inspected=map_cell(game,state['inspect']) if state.get('inspect') else None
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
                ui.add_css(DAIOU_CSS+DAIOU_BATTLE_CSS+DAIOU_UNITS_CSS)
                return
            with ui.element('section').classes('daiou-hero'):
                ui.button(icon='home',on_click=return_home).props('flat round aria-label="大王ホームへ戻る"').classes('battle-home-button')
                ui.label('大 王').classes('daiou-title'); ui.label('選んだ方針ではなく、積み重ねた行動が国を作る。').classes('daiou-copy')
                ui.label(f"第{game['turn']}季・{game['season']}").classes('turn-chip')
                ui.label(f"国の姿：{derived_identity(player)}").classes('identity-chip')
            with ui.element('div').classes('realm-grid'):
                for label,value in (("国力",strength(player)),("領土",player['territory']),("軍資金",player['wealth']),("兵力",sum(x['troops'] for x in game['map'] if x['owner']==game['player']))):
                    with ui.element('div').classes('realm-stat'): ui.label(label); ui.label(str(value)).classes('realm-value')
            with ui.element('section').classes('command-turn-bar'):
                ui.label('今季の軍令').classes('command-turn-title')
                with ui.element('div').classes('command-seals'):
                    for index in range(3): ui.element('span').classes('command-seal'+(' ready' if index<game.get('commands_left',3) else ' used'))
                ui.button('季節を進める',icon='hourglass_bottom',on_click=finish_turn).props('unelevated no-caps').classes('end-turn-button')
            fronts=[]
            for cell in game['map']:
                if not cell['owner']: continue
                if any(x['owner'] not in {None,cell['owner']} for x in adjacent_cells(game,cell)): fronts.append(cell)
            camps=[x for x in game['map'] if x.get('claim')]
            with ui.element('section').classes('war-status'):
                ui.label('戦況').classes('war-status-title')
                ui.label(f"国境の緊張 {len(fronts)}か所").classes('war-status-item danger' if fronts else 'war-status-item')
                ui.label(f"領土化中 {len(camps)}陣").classes('war-status-item')
                strain=border_strain(game,game['player'])
                ui.label(f"国境負担 {strain}").classes('war-status-item danger' if strain else 'war-status-item')
            if game.get('coalition'):
                members='・'.join(nation(game,x)['name'] for x in game['coalition']['members'])
                with ui.element('section').classes('coalition-alert'):
                    ui.label('合従軍').classes('coalition-title'); ui.label(f"{members}があなたの国を包囲しています").classes('coalition-copy')
            if game.get('diplomatic_offer'):
                offer=game['diplomatic_offer']; sender=nation(game,offer['from'])
                proposal='同盟を結び、互いの国を守りたい' if offer['kind']=='alliance' else '6季の交易協定を結びたい'
                with ui.element('section').classes('envoy-card'):
                    with ui.column().classes('gap-0 grow'):
                        ui.label(f"{sender['name']}から使者が来訪").classes('envoy-title')
                        ui.label(proposal).classes('envoy-copy')
                    ui.button('受ける',on_click=lambda:answer_offer(True)).props('unelevated dense no-caps').classes('envoy-accept')
                    ui.button('断る',on_click=lambda:answer_offer(False)).props('flat dense no-caps').classes('envoy-decline')
            player_legions=[item for item in game.get('legions',[]) if item.get('owner')==game['player']]
            with ui.element('section').classes('army-headquarters'):
                with ui.row().classes('items-center justify-between w-full no-wrap'):
                    with ui.column().classes('gap-0'):
                        ui.label('軍 団 司 令 部').classes('army-hq-title')
                        ui.label('軍団＝国境を越えて進軍する移動部隊・戦闘力+2').classes('army-hq-copy')
                    ui.label(f'{len(player_legions)}軍').classes('army-hq-count')
                with ui.element('div').classes('army-hq-grid'):
                    for legion in player_legions:
                        location=map_cell(game,legion['location'])
                        commander=commander_for_legion(game,legion)
                        with ui.element('button').props('type="button"').classes('army-hq-card').on('click',lambda _,item=legion:focus_legion(item)):
                            with ui.element('div').classes('army-miniature'):
                                ui.element('span').classes('army-soldier rear')
                                ui.element('span').classes('army-soldier lead')
                                ui.element('span').classes('army-banner')
                            with ui.column().classes('gap-0 grow items-start'):
                                ui.label(f"{legion['name']}　{LEGION_STATUS.get(legion.get('status'),'待機中')}").classes('army-card-name')
                                ui.label(f"{location['name']}｜{commander['name'] if commander else '武将未配置'}").classes('army-card-place')
                                if commander: ui.label(f"{commander_rank(commander)} Lv.{commander['level']}｜統率 {command_capacity(commander)*500:,}").classes('army-card-rank')
                            ui.label(f"兵力 {location['troops']*500:,}").classes('army-card-troops')
                with ui.element('div').classes('army-role-guide'):
                    ui.label('⚑ 軍団　侵攻・遠征・同盟国への援軍を担当')
                    ui.label('⬟ 守備隊　土地を守り、徴兵・建設・兵の補給を担当')
            with ui.row().classes('w-full items-center no-wrap map-heading-row'):
                with ui.column().classes('gap-0 grow'):
                    ui.label('葛飾戦図').classes('daiou-heading'); ui.label('まず葛飾区内の戦略と見た目を完成させます').classes('map-guide')
                ui.button(icon='remove',on_click=lambda:change_map_zoom(-10)).props('flat round dense aria-label="地図を縮小"').classes('map-zoom-button')
                ui.label(f"{state['map_zoom']}%").classes('map-zoom-value')
                ui.button(icon='add',on_click=lambda:change_map_zoom(10)).props('flat round dense aria-label="地図を拡大"').classes('map-zoom-button')
            with ui.element('div').classes('nation-legend'):
                for item in game['nations']:
                    if item['alive']:
                        with ui.element('span').classes(f"nation-legend-chip owner-{item['id']}"+(" player" if item['id']==game['player'] else '')):
                            ui.element('i').classes('nation-color-dot')
                            ui.label(('自国・' if item['id']==game['player'] else '')+item['name'])
            with ui.element('div').classes('world-scroll tokyo-scroll'):
                svg=['<defs><marker id="march-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" class="march-arrow"/></marker></defs>']
                for legion in game.get('legions',[]):
                    route=legion.get('route') or {}
                    if legion.get('status')!='marching' or route.get('from') not in {x['id'] for x in game['map']} or route.get('to') not in {x['id'] for x in game['map']}: continue
                    start=region_shape(route['from']); finish=region_shape(route['to'])
                    svg.append(f'<path d="M {start["cx"]} {start["cy"]} L {finish["cx"]} {finish["cy"]}" class="march-route owner-{legion["owner"]}" marker-end="url(#march-arrow)"/>')
                    svg.append(f'<circle r="5" class="marching-unit"><animateMotion dur="2.4s" repeatCount="indefinite" path="M {start["cx"]} {start["cy"]} L {finish["cx"]} {finish["cy"]}"/></circle>')
                for cell in game['map']:
                    classes=f"region-shape terrain-{cell['terrain']} "
                    classes+=f"owner-{cell['owner']}" if cell['owner'] else 'neutral'
                    neighbors=adjacent_cells(game,cell)
                    if cell['owner'] and any(x['owner'] not in {None,cell['owner']} for x in neighbors): classes+=' frontline'
                    if cell['id']==state['selected']: classes+=' selected'
                    shape=region_shape(cell['id'])
                    svg.append(f'<path d="{shape["path"]}" vector-effect="non-scaling-stroke" class="{classes}" data-region="{cell["id"]}" aria-label="{cell["name"]}"><title>{cell["name"]}</title></path>')
                    svg.append(f'<text x="{shape["cx"]}" y="{shape["cy"]-36}" text-anchor="middle" class="region-label">{cell["name"]}</text>')
                    if cell.get('structure'):
                        structure={'capital':'城','town':'町','fort':'砦'}[cell['structure']]
                        svg.append(f'<g class="structure-marker structure-{cell["structure"]}" transform="translate({shape["cx"]-11} {shape["cy"]-29})"><path d="M1 19h20V8l-4 3V5l-4 3V2L9 8V5L5 11 1 8z"/><text x="11" y="17" text-anchor="middle">{structure}</text></g>')
                    if cell['owner'] or cell.get('claim'):
                        marker_owner=cell['owner'] or cell['claim']['owner']
                        legion=legion_at(game,cell['id'])
                        if legion:
                            svg.append(f'<g class="field-army owner-{marker_owner}" transform="translate({shape["cx"]-15} {shape["cy"]-8})"><path class="army-shadow" d="M0 17h30l-4 5H4z"/><circle cx="8" cy="8" r="5"/><circle cx="16" cy="5" r="6"/><circle cx="24" cy="8" r="5"/><path class="army-flag" d="M16 1V-12h13l-4 5 4 5H18"/></g>')
                        else:
                            svg.append(f'<path d="M -10 -8 H 10 V 4 C 10 12 0 17 0 17 S -10 12 -10 4 Z" transform="translate({shape["cx"]} {shape["cy"]})" class="garrison-shield owner-{marker_owner}"/>')
                        svg.append(f'<text x="{shape["cx"]}" y="{shape["cy"]+4}" text-anchor="middle" class="region-troops">{cell["troops"]}</text>')
                        owner_name=nation(game,marker_owner)['name']
                        marker_name=f"{owner_name}・{legion['name']}・{LEGION_STATUS.get(legion.get('status'),'待機中')}" if legion else (owner_name if cell.get('structure')=='capital' else '')
                        if marker_name: svg.append(f'<text x="{shape["cx"]}" y="{shape["cy"]+20}" text-anchor="middle" class="region-owner-name">{marker_name}</text>')
                markup=(f'<div class="tokyo-map-wrap" data-daiou-map><svg viewBox="{map_viewbox()}" role="img" '
                        f'aria-label="葛飾区内の戦略地図" class="tokyo-map" style="width:{round(650*state["map_zoom"]/100)}px">{"".join(svg)}</svg></div>')
                map_html=ui.html(markup,sanitize=False)
                map_html.on('regionclick',select_map_event,
                            js_handler="(event) => emit(event.detail.region)")
                ui.run_javascript('''requestAnimationFrame(() => {
                  const map = document.querySelector('[data-daiou-map]');
                  if (!map || map.dataset.bound === '1') return;
                  map.dataset.bound = '1';
                  map.addEventListener('click', event => {
                    const region = event.target.closest('[data-region]');
                    if (region) map.parentElement.dispatchEvent(new CustomEvent('regionclick', {detail: {region: region.dataset.region}}));
                  });
                });''')
            ui.label('葛飾区の町名を基にしたゲーム用戦場・今後拡張予定').classes('map-source')
            if inspected:
                inspect_owner=nation(game,inspected['owner'])['name'] if inspected.get('owner') else '未領有地'
                inspect_legion=legion_at(game,inspected['id'])
                with ui.element('section').classes('region-intel'):
                    ui.label(f"{inspected['name']}　｜　{inspect_owner}").classes('region-intel-title')
                    unit_name=inspect_legion['name'] if inspect_legion else ('先遣隊' if inspected.get('claim') else '守備隊')
                    strain=border_strain(game,inspected['owner']) if inspected.get('owner') else 0
                    strain_text=f"　｜　国境負担 -{strain}" if strain else ''
                    ui.label(f"{unit_name}・兵 {inspected['troops']}　｜　季節収入 +{region_income(inspected)}　｜　{terrain_effect(inspected)}{strain_text}").classes('region-intel-copy')
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
                        selected_legion=legion_at(game,selected['id'])
                        selected_commander=commander_for_legion(game,selected_legion)
                        unit_name=selected_legion['name'] if selected_legion else '守備隊'
                        ui.label(f"{unit_name}｜{selected['name']}（{owner['name']}）　兵力 {selected['troops']*500:,}").classes('selected-title')
                        if selected_commander:
                            with ui.element('div').classes('commander-strip'):
                                with ui.column().classes('gap-0 grow'):
                                    ui.label(selected_commander['name']).classes('commander-name')
                                    ui.label(f"{commander_rank(selected_commander)}　Lv.{selected_commander['level']}　経験 {selected_commander['xp']}/{selected_commander['level']*8}").classes('commander-rank')
                                ui.label(f"統率上限\n{command_capacity(selected_commander)*500:,}").classes('commander-capacity')
                        role_help='国境を越えて進軍可能・戦闘力+2' if selected_legion else '土地を守る固定部隊。侵攻するには軍団編成が必要'
                        ui.label(role_help+'。自国領へは必要な兵だけ移動できます').classes('selected-help')
                        with ui.element('div').classes('march-picker'):
                            ui.label('派遣兵力').classes('march-label')
                            for percent in (25,50,75,100):
                                label='100%※' if percent==100 else f'{percent}%'
                                ui.button(label,on_click=lambda _,value=percent:choose_march(value)).props('flat dense no-caps').classes('march-choice'+(' active' if state['march']==percent else ''))
                        if state['march']==100:
                            ui.label('※領土を守る兵1を残し、移動可能な全兵を送ります').classes('march-note')
                        with ui.element('div').classes('tactic-picker'):
                            for key,label,icon in (('direct','正面','⚔'),('pincer','挟撃','⇉')):
                                ui.button(f'{icon} {label}',on_click=lambda _,value=key:choose_tactic(value)).props('flat dense no-caps').classes('tactic-choice'+(' active' if state['tactic']==key else ''))
                        with ui.element('div').classes('command-grid'):
                            ui.button('徴兵 +4／資金5',icon='person_add',on_click=lambda:act('recruit')).props('flat no-caps')
                            ui.button('選んだ兵を別の自国領へ移動',icon='multiple_stop',on_click=begin_transfer).props('flat no-caps').classes('transfer-button'+(' active' if state.get('map_action')=='transfer' else ''))
                            if selected_legion: ui.button('この地に駐屯する',icon='shield',on_click=lambda:act('station')).props('flat no-caps')
                            if not selected_legion: ui.button('軍団を編成',icon='flag',on_click=create_legion).props('flat no-caps')
                            ui.button('町を築く 10',icon='holiday_village',on_click=lambda:act('town')).props('flat no-caps')
                            ui.button('砦を築く 8',icon='fort',on_click=lambda:act('fort')).props('flat no-caps')
                else: ui.label('まず金色の自国領をタップ').classes('empty-command')
            with ui.expansion(f"軍団一覧　{len(player_legions)}軍",icon='flag').classes('nation-box w-full'):
                for legion in player_legions:
                    location=map_cell(game,legion['location'])
                    commander=commander_for_legion(game,legion)
                    with ui.element('div').classes('nation-row player'):
                        ui.label(legion['name']).classes('font-black grow')
                        detail=f"{location['name']}・{LEGION_STATUS.get(legion.get('status'),'待機中')}・兵力 {location['troops']*500:,}"
                        if commander: detail+=f"・{commander_rank(commander)} {commander['name']} Lv.{commander['level']}"
                        ui.label(detail).classes('nation-detail')
            with ui.expansion('十国の現在',icon='public').classes('nation-box w-full'):
                for item in sorted((x for x in game['nations'] if x['alive']),key=strength,reverse=True):
                    with ui.element('div').classes('nation-row'+(' player' if item['id']==game['player'] else '')):
                        ui.label(('あなた・' if item['id']==game['player'] else '')+item['name']).classes('font-black grow')
                        action=max(item.get('actions',{}),key=item.get('actions',{}).get)
                        intent={'expand':'↗ 拡大','trade':'⇄ 交易','build':'▣ 建設','defend':'⬟ 防衛','battle':'⚔ 交戦'}[action]
                        strain=border_strain(game,item['id'])
                        ui.label(f"{intent}　領土 {item['territory']}・兵力 {item['army']}"+(f"・国境負担 {strain}" if strain else '')).classes('nation-detail')
                        if item['id']!=game['player']:
                            status=diplomatic_label(game,game['player'],item['id'])
                            ui.label(status).classes('relation-chip '+relation(game,game['player'],item['id'])['status'])
                            if status!='交戦':
                                agreement=game.get('trade_agreements',{}).get(item['id'],0)>=game['turn']
                                ui.button('協定交易' if agreement else '交易',on_click=lambda _,nid=item['id']:negotiate(nid,'trade')).props('flat dense no-caps').classes('diplomacy-button trade')
                            if status in {'同盟','不可侵'}:
                                if status=='同盟': ui.button('援軍',on_click=lambda _,nid=item['id']:negotiate(nid,'support')).props('flat dense no-caps').classes('diplomacy-button support')
                                ui.button('破棄',on_click=lambda _,nid=item['id']:negotiate(nid,'end')).props('flat dense no-caps').classes('diplomacy-button danger')
                            else:
                                ui.button('同盟提案',on_click=lambda _,nid=item['id']:negotiate(nid)).props('flat dense no-caps').classes('diplomacy-button')
            if state.get('event'):
                event=state['event']
                with ui.element('div').classes(f"battle-event {event['kind']}").on('click',lambda _:dismiss_event()):
                    if event['kind']=='enemy_attack':
                        ui.label('急').classes('battle-event-mark')
                        ui.label('敵 襲 報').classes('battle-event-title')
                        with ui.element('div').classes('enemy-report-list'):
                            for report in event.get('reports',[]):
                                with ui.element('div').classes(f"enemy-report-row {report['result']}"):
                                    ui.label('領土陥落' if report['result']=='lost' else '防衛成功').classes('enemy-report-result')
                                    ui.label(report['message']).classes('enemy-report-message')
                    else:
                        ui.label('⚔' if event['kind']=='battle' else ('旗' if event['kind']=='occupy' else '令')).classes('battle-event-mark')
                        ui.label('合戦報' if event['kind']=='battle' else ('領土報' if event['kind']=='occupy' else '軍令')).classes('battle-event-title')
                        ui.label(event['message']).classes('battle-event-message')
                    ui.label('タップして閉じる').classes('battle-event-close')
        ui.add_css(DAIOU_CSS+DAIOU_BATTLE_CSS+DAIOU_UNITS_CSS)
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

DAIOU_UNITS_CSS='''
.army-headquarters{margin:0 0 12px;padding:13px;border-radius:18px;background:linear-gradient(135deg,rgba(68,49,27,.95),rgba(19,31,28,.96));border:1px solid rgba(240,201,111,.35)}.army-hq-title{font-family:serif;font-size:14px;font-weight:950;letter-spacing:.16em;color:#FFE09A}.army-hq-copy{font-size:8px;color:#C9C4B4}.army-hq-count{padding:5px 9px;border-radius:99px;background:#D5AD55;color:#142019;font-size:9px;font-weight:950}.army-hq-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:10px}.army-hq-card{display:flex;align-items:center;gap:8px;min-width:0;padding:9px;border:1px solid rgba(255,224,154,.18);border-radius:13px;color:#F7E8C5;background:rgba(255,255,255,.055);text-align:left}.army-role-guide{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:9px}.army-role-guide .q-label{padding:7px;border-radius:9px;background:rgba(0,0,0,.18);font-size:8px;color:#E5D6B7}.army-miniature{position:relative;width:36px;height:32px;flex:0 0 36px}.army-soldier{position:absolute;bottom:2px;width:12px;height:15px;border-radius:6px 6px 3px 3px;background:linear-gradient(#E7C56E,#7E5A25);box-shadow:0 2px 4px #000}.army-soldier:before{content:'';position:absolute;left:2px;top:-7px;width:8px;height:8px;border-radius:50%;background:#F0D084}.army-soldier.lead{left:13px;height:18px;z-index:2}.army-soldier.rear{left:3px;transform:scale(.8);opacity:.8}.army-banner{position:absolute;right:2px;top:1px;width:12px;height:15px;border-left:2px solid #E8CB81;background:#9D3028;clip-path:polygon(0 0,100% 0,72% 50%,100% 100%,0 100%)}.army-card-name{font-size:10px;font-weight:950;color:#F6D689}.army-card-place{font-size:8px;color:#BFC7BD}.army-card-rank{font-size:7px;color:#E8C979}.army-card-troops{font-size:10px;font-weight:950;white-space:nowrap}.commander-strip{display:flex;align-items:center;gap:10px;margin:7px 0;padding:10px 12px;border-radius:13px;background:linear-gradient(115deg,#162520,#3c2d19);border:1px solid rgba(242,205,117,.42)}.commander-name{font-family:serif;font-size:13px;font-weight:950;color:#FFE09A}.commander-rank{font-size:8px;color:#D8CCB2}.commander-capacity{white-space:pre-line;text-align:center;padding:6px 9px;border-radius:9px;background:#A77A2E;color:#FFF4D5;font-size:8px;font-weight:950}.nation-legend{display:flex;gap:5px;overflow-x:auto;margin:6px 0 8px;padding-bottom:3px}.nation-legend-chip{display:flex;align-items:center;gap:5px;flex:0 0 auto;padding:5px 8px;border-radius:99px;background:rgba(255,255,255,.06);font-size:8px;font-weight:850}.nation-legend-chip.player{box-shadow:inset 0 0 0 1px #F5CA69;color:#FFE3A0}.nation-color-dot{width:8px;height:8px;border-radius:50%;background:#777}.owner-n0 .nation-color-dot{background:#a88032}.owner-n1 .nation-color-dot{background:#527ca7}.owner-n2 .nation-color-dot{background:#337f79}.owner-n3 .nation-color-dot{background:#a84944}.owner-n4 .nation-color-dot{background:#aaa68f}.owner-n5 .nation-color-dot{background:#568947}.owner-n6 .nation-color-dot{background:#765b94}.owner-n7 .nation-color-dot{background:#9a693b}.owner-n8 .nation-color-dot{background:#4c555d}.owner-n9 .nation-color-dot{background:#7770a2}.field-army,.garrison-shield{pointer-events:none;fill:#22312B;stroke:#FFE5A0;stroke-width:1.5;filter:drop-shadow(0 3px 2px rgba(0,0,0,.65))}.field-army.owner-n0,.garrison-shield.owner-n0{fill:#a88032}.field-army.owner-n1,.garrison-shield.owner-n1{fill:#527ca7}.field-army.owner-n2,.garrison-shield.owner-n2{fill:#337f79}.field-army.owner-n3,.garrison-shield.owner-n3{fill:#a84944}.field-army.owner-n4,.garrison-shield.owner-n4{fill:#aaa68f}.field-army.owner-n5,.garrison-shield.owner-n5{fill:#568947}.field-army.owner-n6,.garrison-shield.owner-n6{fill:#765b94}.field-army.owner-n7,.garrison-shield.owner-n7{fill:#9a693b}.field-army.owner-n8,.garrison-shield.owner-n8{fill:#4c555d}.field-army.owner-n9,.garrison-shield.owner-n9{fill:#7770a2}.field-army .army-shadow{fill:#0A1110;stroke:none;opacity:.75}.field-army .army-flag{stroke:#F7D986;stroke-width:1.5}.structure-marker{pointer-events:none;fill:#171B18;stroke:#F5D688;stroke-width:1}.structure-marker text{fill:#FFF0C2;stroke:none;font-size:7px;font-weight:950}.structure-capital{fill:#7B301E}.structure-town{fill:#5E4A25}.structure-fort{fill:#34484A}.envoy-card{display:flex;align-items:center;gap:7px;margin-bottom:10px;padding:12px;border-radius:15px;background:linear-gradient(110deg,#24483d,#172720);border:1px solid rgba(118,222,182,.35)}.envoy-title{font-size:11px;font-weight:950;color:#9CE8CC}.envoy-copy{font-size:8px;color:#DDE8DF}.envoy-accept{background:#4A9B7A!important}.envoy-decline{color:#D8CDB6!important}.map-heading-row{margin-top:5px}.map-zoom-button{color:#F2D481!important;background:rgba(255,255,255,.07)!important}.map-zoom-value{min-width:38px;text-align:center;font-size:9px;font-weight:950}.diplomacy-button.trade{color:#9FE1C4!important}.local-road{pointer-events:none;fill:none;stroke:rgba(255,235,173,.62);stroke-width:1.2;stroke-dasharray:3 2}.local-base{pointer-events:none;fill:#FFE19A;stroke:#5A3A13;stroke-width:1}.local-name{pointer-events:none;fill:#FFF5D8;font-size:6px;font-weight:950;paint-order:stroke;stroke:#172019;stroke-width:1.4px}@media(max-width:480px){.army-hq-grid,.army-role-guide{grid-template-columns:1fr}}

.region-label{pointer-events:none;fill:#FFF3D0;font-size:12px;font-weight:950;paint-order:stroke;stroke:#101815;stroke-width:3px}.march-route{pointer-events:none;fill:none;stroke:#FFE17C;stroke-width:4;stroke-dasharray:9 7;filter:drop-shadow(0 0 4px rgba(255,209,89,.85));animation:marchFlow 1.1s linear infinite}.march-arrow{fill:#FFE17C}@keyframes marchFlow{to{stroke-dashoffset:-32}}
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
.diplomacy-button.support{color:#9DE7D0!important;background:rgba(36,137,107,.18)!important}
.tactic-picker{display:grid;grid-template-columns:repeat(2,1fr);gap:5px;margin-top:9px}.tactic-choice{min-height:34px!important;border-radius:10px!important;color:#D8CFBB!important;background:rgba(255,255,255,.055)!important;font-size:9px!important;font-weight:900!important}.tactic-choice.active{color:#152018!important;background:linear-gradient(135deg,#B9893A,#F0D07B)!important;box-shadow:0 5px 13px rgba(0,0,0,.18)}
@media(min-width:430px){.world-map{grid-template-columns:repeat(var(--map-cols),76px)!important;grid-template-rows:repeat(var(--map-rows),76px)!important}.map-cell{width:76px!important;height:76px!important}.army-flag{font-size:21px}.army-rank{font-size:9px;top:34px}}
@media(max-width:520px){.nation-row{flex-wrap:wrap;gap:4px}.nation-row>.grow{min-width:42%}.nation-detail{margin-left:auto}.diplomacy-button{margin-left:auto!important}}
.map-source{display:block;margin:4px 4px 10px;color:#A9B5AA!important;font-size:8px;text-decoration:none!important;opacity:.7}
.command-turn-bar{display:flex;align-items:center;gap:10px;margin:-5px 0 12px;padding:10px 12px;border-radius:16px;background:rgba(6,17,17,.78);border:1px solid rgba(239,203,120,.25)}.command-turn-title{font-size:10px;font-weight:950;color:#EBCB81}.command-seals{display:flex;gap:5px;margin-right:auto}.command-seal{width:14px;height:14px;border-radius:50%;border:1px solid rgba(255,224,145,.45)}.command-seal.ready{background:#E9BD58;box-shadow:0 0 9px rgba(233,189,88,.5)}.command-seal.used{background:#29322F}.end-turn-button{min-height:34px!important;padding:0 11px!important;border-radius:10px!important;background:linear-gradient(135deg,#8C682E,#E3B956)!important;color:#101A17!important;font-size:9px!important;font-weight:950!important}.region-intel{margin:0 0 8px;padding:11px 13px;border-radius:14px;background:linear-gradient(110deg,rgba(39,61,51,.95),rgba(25,34,31,.95));border-left:4px solid #D8B25D}.region-intel-title{font-size:12px;font-weight:950;color:#F6D98F}.region-intel-copy{margin-top:3px;font-size:9px;color:#D1D8CF}.march-picker{display:flex;align-items:center;gap:5px;margin-top:8px}.march-label{margin-right:auto;font-size:9px;font-weight:900;color:#D9C9A4}.march-choice{min-height:29px!important;padding:0 9px!important;border-radius:9px!important;background:rgba(255,255,255,.06)!important;color:#D8CFBB!important;font-size:9px!important}.march-choice.active{background:#D7AE54!important;color:#142019!important;font-weight:950!important}.region-structure{pointer-events:none;fill:#FFE6A0;font-size:9px;font-weight:950;paint-order:stroke;stroke:#1A1710;stroke-width:2px}.region-piece{pointer-events:none;fill:#FFF0C4;font-size:12px;font-weight:950;paint-order:stroke;stroke:#111;stroke-width:1.3px}.region-owner-name{pointer-events:none;fill:#FFF0C4;font-size:6px;font-weight:950;paint-order:stroke;stroke:#111;stroke-width:1.3px}.marching-unit{pointer-events:none;fill:#FFE57C;stroke:#FFF5CE;stroke-width:2;filter:drop-shadow(0 0 8px #FFD159)}
.march-note{margin-top:5px;font-size:8px;color:#E8CB89}.transfer-button.active{color:#142019!important;background:linear-gradient(135deg,#B9893A,#F0D07B)!important}.battle-event.enemy_attack{background:radial-gradient(circle at 50% 32%,rgba(145,30,22,.96),rgba(3,7,8,.98) 66%)}.enemy-report-list{width:min(100%,390px);max-height:52vh;overflow:auto;margin-top:17px;display:grid;gap:8px}.enemy-report-row{padding:13px 14px;border-radius:15px;text-align:left;border:1px solid rgba(255,220,155,.26);background:rgba(8,13,13,.62)}.enemy-report-row.lost{border-left:5px solid #F05B45}.enemy-report-row.defended{border-left:5px solid #69C99E}.enemy-report-result{font-size:11px;font-weight:950;color:#FFE1A0}.enemy-report-row.lost .enemy-report-result{color:#FF9B86}.enemy-report-row.defended .enemy-report-result{color:#8DE0B9}.enemy-report-message{margin-top:4px;font-size:10px;font-weight:800;line-height:1.65;color:#F8ECD4}
'''

DAIOU_CSS='''
body{background:#071015!important}.daiou-home{min-height:calc(100vh - 84px);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:34px 20px;border-radius:30px;background:radial-gradient(circle at 50% 28%,rgba(212,166,75,.20),transparent 28%),linear-gradient(160deg,#152A24,#080F13 68%);border:1px solid rgba(226,184,96,.30);overflow:hidden}.daiou-home-icon{width:132px!important;height:132px!important;border-radius:29px;box-shadow:0 22px 60px rgba(0,0,0,.48),0 0 0 1px rgba(242,203,112,.38)}.daiou-home-title{margin-top:25px;font-family:serif;font-size:49px;font-weight:950;letter-spacing:.22em;color:#FFE5A0}.daiou-home-copy{margin-top:4px;font-size:11px;font-weight:800;color:#CFC5AC}.home-status{width:min(100%,360px);margin:32px 0 17px;padding:17px;border-radius:18px;background:rgba(255,255,255,.065);border:1px solid rgba(255,255,255,.08)}.home-turn{margin-top:5px;font-size:12px;font-weight:950;color:#EFCB78}.home-realm{margin-top:5px;font-size:10px;color:#D8D9D0}.continue-button{width:min(100%,360px);min-height:57px!important;border-radius:17px!important;background:linear-gradient(135deg,#C49340,#F0CE78)!important;color:#182019!important;font-size:16px!important;font-weight:950!important}.new-button{margin-top:8px;color:#B9B5A9!important}.new-game-dialog{width:min(92vw,430px)!important;padding:22px!important;border-radius:24px!important}.battle-home-button{position:absolute!important;z-index:5;left:14px;top:14px;color:#FFF0C5!important;background:rgba(3,10,12,.48)!important}
body{background:#071015!important}.daiou-app{width:min(100%,760px);min-height:100vh;margin:auto;padding:14px 14px 56px;color:#F5EBD2;background:radial-gradient(circle at 90% 0,#334B3C 0,transparent 27%),linear-gradient(180deg,#0B1820,#10130F)}.daiou-hero{position:relative;min-height:190px;padding:30px 22px;border-radius:28px;display:flex;flex-direction:column;justify-content:flex-end;overflow:hidden;background:linear-gradient(155deg,rgba(3,10,14,.1),rgba(3,8,7,.86)),radial-gradient(circle at 50% 20%,#B8863A,#26372D 48%,#0A1012 76%);border:1px solid rgba(226,184,96,.35)}.daiou-hero:before{content:'王';position:absolute;right:16px;top:-35px;font-size:175px;font-family:serif;font-weight:900;color:rgba(255,224,153,.11)}.daiou-title{font-family:serif;font-size:44px;font-weight:950;letter-spacing:.2em;color:#FFE5A0}.daiou-copy{font-size:10px;font-weight:800;opacity:.78}.turn-chip,.identity-chip{position:absolute;top:15px;padding:7px 10px;border-radius:999px;background:rgba(4,12,12,.64);font-size:9px;font-weight:900}.turn-chip{left:15px}.identity-chip{right:15px;color:#F0C96F}.realm-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:11px 0 16px}.realm-stat{padding:10px 8px;border-radius:14px;background:rgba(255,255,255,.07);font-size:8px;color:#B8C3B8}.realm-value{font-size:18px;font-weight:950;color:#FFF1C7}.daiou-heading{margin:9px 2px 2px;font-size:18px;font-weight:950}.map-guide{font-size:9px;opacity:.68;margin:0 2px 8px}.world-scroll{width:100%;max-height:68vh;overflow:auto;padding:5px 0 10px;scrollbar-width:thin;overscroll-behavior:contain}.world-map{display:grid;grid-template-columns:repeat(var(--map-cols),62px);grid-template-rows:repeat(var(--map-rows),62px);gap:4px;width:max-content;padding:8px;border-radius:18px;background:#06100E;border:1px solid rgba(240,201,111,.22)}.map-cell{position:relative;width:62px;height:62px;border:0;border-radius:12px;color:#EDE4CE;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(255,255,255,.08);transition:.16s transform,.16s box-shadow}.map-cell:active{transform:scale(.94)}.terrain-plain{background:#405C3D}.terrain-forest{background:#173D2B}.terrain-hill{background:#69563B}.terrain-river{background:linear-gradient(135deg,#315D70,#4B7B88)}.neutral{filter:saturate(.55) brightness(.72)}.owner-n0{box-shadow:inset 0 0 0 3px #F5CA69,0 0 13px rgba(245,202,105,.18)}.owner-n1{box-shadow:inset 0 0 0 3px #A8C7E8}.owner-n2{box-shadow:inset 0 0 0 3px #6DB8B2}.owner-n3{box-shadow:inset 0 0 0 3px #D86661}.owner-n4{box-shadow:inset 0 0 0 3px #E9E5D1}.owner-n5{box-shadow:inset 0 0 0 3px #82B66F}.owner-n6{box-shadow:inset 0 0 0 3px #A889C4}.owner-n7{box-shadow:inset 0 0 0 3px #CF9D5C}.owner-n8{box-shadow:inset 0 0 0 3px #62676C}.owner-n9{box-shadow:inset 0 0 0 3px #B1A9D8}.map-cell.selected{box-shadow:inset 0 0 0 4px #FFF,0 0 18px #FFD36E;transform:translateY(-3px)}.terrain-mark{position:absolute;left:7px;top:5px;font-size:15px;opacity:.42}.structure-mark{position:absolute;right:6px;top:5px;font-size:10px;font-weight:950;color:#FFF1B9}.owner-mark{position:absolute;right:6px;bottom:5px;font-size:8px;font-weight:950;opacity:.82}.claim-mark{position:absolute;left:24px;top:20px;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#F2D28A;color:#182018;font-size:9px;font-weight:950;box-shadow:0 0 0 2px rgba(0,0,0,.3)}.troop-mark{position:absolute;left:7px;bottom:5px;padding:2px 6px;border-radius:999px;background:rgba(2,7,7,.72);font-size:10px;font-weight:950}.command-panel{min-height:96px;margin-top:2px;padding:13px;border-radius:18px;background:linear-gradient(145deg,#21362D,#16231E);border:1px solid rgba(220,176,88,.22)}.selected-title{font-size:13px;font-weight:950;color:#F0C96F}.selected-help{font-size:8px;opacity:.65}.command-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:5px;margin-top:8px}.command-grid .q-btn{background:rgba(255,255,255,.07)!important;color:#F7E8C5!important;font-size:10px!important}.empty-command{text-align:center;padding:24px;font-weight:900;opacity:.6}.nation-box{margin-top:10px;border-radius:16px!important;background:rgba(255,255,255,.06)!important}.nation-row{display:flex;align-items:center;padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.06)}.nation-row.player{color:#F0C96F}.nation-detail{font-size:9px;opacity:.72}.history-line{padding:8px;border-bottom:1px solid rgba(255,255,255,.06);font-size:10px}.tokyo-scroll{max-height:none!important;overflow:auto!important;border-radius:20px;background:radial-gradient(circle at 62% 55%,rgba(57,88,67,.72),rgba(4,13,14,.96));border:1px solid rgba(240,201,111,.22);touch-action:pan-x pan-y pinch-zoom}.tokyo-map{display:block;width:max(850px,100%);height:auto;min-height:420px;padding:12px;filter:drop-shadow(0 12px 18px rgba(0,0,0,.36))}.region-shape{cursor:pointer;stroke:rgba(241,226,190,.52);stroke-width:1.4;fill:#405c3d;transition:fill .16s,filter .16s,stroke-width .16s}.region-shape.terrain-forest{fill:#183f2b}.region-shape.terrain-hill{fill:#69563b}.region-shape.neutral{filter:saturate(.55) brightness(.74)}.region-shape.owner-n0{fill:#a88032;stroke:#ffe29a;stroke-width:3}.region-shape.owner-n1{fill:#527ca7}.region-shape.owner-n2{fill:#337f79}.region-shape.owner-n3{fill:#a84944}.region-shape.owner-n4{fill:#aaa68f}.region-shape.owner-n5{fill:#568947}.region-shape.owner-n6{fill:#765b94}.region-shape.owner-n7{fill:#9a693b}.region-shape.owner-n8{fill:#4c555d}.region-shape.owner-n9{fill:#7770a2}.region-shape.selected{stroke:#fff7d5;stroke-width:6;filter:brightness(1.32) drop-shadow(0 0 8px #ffd36e)}.region-shape.frontline{animation:frontGlow 1.7s ease-in-out infinite}.region-army{pointer-events:none;fill:#111b18;stroke:#ffe5a0;stroke-width:2}.region-army.owner-n0{fill:#a88032}.region-army.owner-n1{fill:#527ca7}.region-army.owner-n2{fill:#337f79}.region-army.owner-n3{fill:#a84944}.region-army.owner-n4{fill:#aaa68f}.region-army.owner-n5{fill:#568947}.region-army.owner-n6{fill:#765b94}.region-army.owner-n7{fill:#9a693b}.region-army.owner-n8{fill:#4c555d}.region-army.owner-n9{fill:#7770a2}.region-troops{pointer-events:none;fill:#fff7dd;font-size:9px;font-weight:950;paint-order:stroke;stroke:#111;stroke-width:1.8px}@media(max-width:390px){.realm-grid{grid-template-columns:repeat(2,1fr)}.tokyo-map{width:760px}}
'''
