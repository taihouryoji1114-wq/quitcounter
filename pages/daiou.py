from nicegui import ui

from core.auth import require_app_access, selected_user_id
from core.daiou import (derived_identity, initial_game, map_cell, nation,
                         normalize_game, perform_map_action, strength)
from core.data import data
from core.theme import Theme

TERRAIN_ICON={"plain":"·","forest":"♣","hill":"▲","river":"≈"}
STRUCTURE_ICON={"capital":"城","town":"町","fort":"砦",None:""}

@ui.page('/daiou')
def daiou_page():
    if not require_app_access('daiou'): return
    Theme.page('大王',app_name='daiou')
    user_id=selected_user_id(); games=data.data.setdefault('daiou',{}).setdefault('profiles',{})
    game=games.setdefault(user_id,initial_game()); normalize_game(game); state={"selected":None}; data.save()

    def save(): games[user_id]=game; data.save()

    def act(action,target=None):
        if not state["selected"]: ui.notify('先に金色の自国領を選んでください',type='warning'); return
        try:
            message=perform_map_action(game,action,state["selected"],target); save(); ui.notify(message,type='positive')
            if map_cell(game,state["selected"])["owner"]!=game["player"]: state["selected"]=None
            render.refresh()
        except ValueError as error: ui.notify(str(error),type='warning')

    def select_cell(cell_id):
        cell=map_cell(game,cell_id)
        if cell["owner"]==game["player"]:
            state["selected"]=cell_id; render.refresh()
        elif state["selected"]: act('advance',cell_id)
        else: ui.notify('金色の自国領から選びます',type='info')

    @ui.refreshable
    def render():
        player=nation(game,game['player']); selected=map_cell(game,state["selected"]) if state["selected"] else None
        with ui.element('main').classes('daiou-app'):
            with ui.element('section').classes('daiou-hero'):
                ui.label('大 王').classes('daiou-title'); ui.label('選んだ方針ではなく、積み重ねた行動が国を作る。').classes('daiou-copy')
                ui.label(f"第{game['turn']}季・{game['season']}").classes('turn-chip')
                ui.label(f"国の姿：{derived_identity(player)}").classes('identity-chip')
            with ui.element('div').classes('realm-grid'):
                for label,value in (("国力",strength(player)),("領土",player['territory']),("軍資金",player['wealth']),("兵力",sum(x['troops'] for x in game['map'] if x['owner']==game['player']))):
                    with ui.element('div').classes('realm-stat'): ui.label(label); ui.label(str(value)).classes('realm-value')
            ui.label('天下盤').classes('daiou-heading'); ui.label('金色の自国領を選び、隣の土地をタップして進みます').classes('map-guide')
            with ui.element('div').classes('world-scroll'):
                with ui.element('div').classes('world-map'):
                    for cell in game['map']:
                        classes=f"map-cell terrain-{cell['terrain']} "
                        classes+=f"owner-{cell['owner']}" if cell['owner'] else 'neutral'
                        if cell['id']==state['selected']: classes+=' selected'
                        with ui.element('button').classes(classes).on('click',lambda _,cid=cell['id']:select_cell(cid)):
                            ui.label(TERRAIN_ICON[cell['terrain']]).classes('terrain-mark')
                            if cell.get('structure'): ui.label(STRUCTURE_ICON[cell['structure']]).classes('structure-mark')
                            if cell['owner']: ui.label(str(cell['troops'])).classes('troop-mark')
            with ui.element('section').classes('command-panel'):
                if selected:
                    owner=nation(game,selected['owner'])
                    ui.label(f"選択中：{owner['name']} {selected['id']}　兵 {selected['troops']}").classes('selected-title')
                    ui.label('隣のマスをタップすると、進出・兵の移動・侵攻を実行します').classes('selected-help')
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
                        ui.label(f"領土 {item['territory']}　{derived_identity(item)}").classes('nation-detail')
            with ui.expansion('国史',icon='history').classes('nation-box w-full'):
                for line in game.get('log',[]): ui.label(line).classes('history-line')
        ui.add_css(DAIOU_CSS)
    render()

DAIOU_CSS='''
body{background:#071015!important}.daiou-app{width:min(100%,760px);min-height:100vh;margin:auto;padding:14px 14px 56px;color:#F5EBD2;background:radial-gradient(circle at 90% 0,#334B3C 0,transparent 27%),linear-gradient(180deg,#0B1820,#10130F)}.daiou-hero{position:relative;min-height:190px;padding:30px 22px;border-radius:28px;display:flex;flex-direction:column;justify-content:flex-end;overflow:hidden;background:linear-gradient(155deg,rgba(3,10,14,.1),rgba(3,8,7,.86)),radial-gradient(circle at 50% 20%,#B8863A,#26372D 48%,#0A1012 76%);border:1px solid rgba(226,184,96,.35)}.daiou-hero:before{content:'王';position:absolute;right:16px;top:-35px;font-size:175px;font-family:serif;font-weight:900;color:rgba(255,224,153,.11)}.daiou-title{font-family:serif;font-size:44px;font-weight:950;letter-spacing:.2em;color:#FFE5A0}.daiou-copy{font-size:10px;font-weight:800;opacity:.78}.turn-chip,.identity-chip{position:absolute;top:15px;padding:7px 10px;border-radius:999px;background:rgba(4,12,12,.64);font-size:9px;font-weight:900}.turn-chip{left:15px}.identity-chip{right:15px;color:#F0C96F}.realm-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:11px 0 16px}.realm-stat{padding:10px 8px;border-radius:14px;background:rgba(255,255,255,.07);font-size:8px;color:#B8C3B8}.realm-value{font-size:18px;font-weight:950;color:#FFF1C7}.daiou-heading{margin:9px 2px 2px;font-size:18px;font-weight:950}.map-guide{font-size:9px;opacity:.68;margin:0 2px 8px}.world-scroll{width:100%;overflow-x:auto;padding:5px 0 10px;scrollbar-width:thin}.world-map{display:grid;grid-template-columns:repeat(8,62px);grid-template-rows:repeat(6,62px);gap:4px;width:max-content;padding:8px;border-radius:18px;background:#06100E;border:1px solid rgba(240,201,111,.22)}.map-cell{position:relative;width:62px;height:62px;border:0;border-radius:12px;color:#EDE4CE;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(255,255,255,.08);transition:.16s transform,.16s box-shadow}.map-cell:active{transform:scale(.94)}.terrain-plain{background:#405C3D}.terrain-forest{background:#173D2B}.terrain-hill{background:#69563B}.terrain-river{background:linear-gradient(135deg,#315D70,#4B7B88)}.neutral{filter:saturate(.55) brightness(.72)}.owner-n0{box-shadow:inset 0 0 0 3px #F5CA69,0 0 13px rgba(245,202,105,.18)}.owner-n1{box-shadow:inset 0 0 0 3px #A8C7E8}.owner-n2{box-shadow:inset 0 0 0 3px #6DB8B2}.owner-n3{box-shadow:inset 0 0 0 3px #D86661}.owner-n4{box-shadow:inset 0 0 0 3px #E9E5D1}.owner-n5{box-shadow:inset 0 0 0 3px #82B66F}.owner-n6{box-shadow:inset 0 0 0 3px #A889C4}.owner-n7{box-shadow:inset 0 0 0 3px #CF9D5C}.owner-n8{box-shadow:inset 0 0 0 3px #62676C}.owner-n9{box-shadow:inset 0 0 0 3px #B1A9D8}.map-cell.selected{box-shadow:inset 0 0 0 4px #FFF,0 0 18px #FFD36E;transform:translateY(-3px)}.terrain-mark{position:absolute;left:7px;top:5px;font-size:15px;opacity:.55}.structure-mark{position:absolute;right:6px;top:5px;font-size:10px;font-weight:950;color:#FFF1B9}.troop-mark{position:absolute;left:7px;bottom:5px;padding:2px 6px;border-radius:999px;background:rgba(2,7,7,.72);font-size:10px;font-weight:950}.command-panel{min-height:96px;margin-top:2px;padding:13px;border-radius:18px;background:linear-gradient(145deg,#21362D,#16231E);border:1px solid rgba(220,176,88,.22)}.selected-title{font-size:13px;font-weight:950;color:#F0C96F}.selected-help{font-size:8px;opacity:.65}.command-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:5px;margin-top:8px}.command-grid .q-btn{background:rgba(255,255,255,.07)!important;color:#F7E8C5!important;font-size:10px!important}.empty-command{text-align:center;padding:24px;font-weight:900;opacity:.6}.nation-box{margin-top:10px;border-radius:16px!important;background:rgba(255,255,255,.06)!important}.nation-row{display:flex;align-items:center;padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.06)}.nation-row.player{color:#F0C96F}.nation-detail{font-size:9px;opacity:.72}.history-line{padding:8px;border-bottom:1px solid rgba(255,255,255,.06);font-size:10px}@media(max-width:390px){.realm-grid{grid-template-columns:repeat(2,1fr)}.world-map{grid-template-columns:repeat(8,58px);grid-template-rows:repeat(6,58px)}.map-cell{width:58px;height:58px}}
'''
