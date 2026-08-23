from nicegui import ui

from core.auth import require_app_access, selected_user_id
from core.daiou import POLICIES, apply_policy, initial_game, nation, normalize_game, strength
from core.data import data
from core.theme import Theme


@ui.page('/daiou')
def daiou_page():
    if not require_app_access('daiou'):
        return
    Theme.page('大王', app_name='daiou')
    user_id = selected_user_id()
    games = data.data.setdefault('daiou', {}).setdefault('profiles', {})
    game = games.setdefault(user_id, initial_game())
    normalize_game(game)
    data.save()

    def choose(key):
        apply_policy(game, key)
        games[user_id] = game
        data.save()
        ui.notify(f'{POLICIES[key][0]}を実行しました', type='positive')
        render.refresh()

    @ui.refreshable
    def render():
        player = nation(game, game['player'])
        with ui.element('main').classes('daiou-app'):
            with ui.element('section').classes('daiou-hero'):
                ui.label('大 王').classes('daiou-title')
                ui.label('十国、それぞれの野心。急がず国を治めよ。').classes('daiou-copy')
                ui.label(f"第{game['turn']}季・{game['season']}").classes('turn-chip')
            with ui.element('div').classes('realm-grid'):
                for label, value in (("国力", strength(player)), ("領土", player['territory']),
                                     ("軍資金", player['wealth']), ("兵力", player['army'])):
                    with ui.element('div').classes('realm-stat'):
                        ui.label(label)
                        ui.label(str(value)).classes('realm-value')
            ui.label('今季の国策').classes('daiou-heading')
            with ui.element('div').classes('policy-grid'):
                for key, (label, description, *_rest) in POLICIES.items():
                    with ui.card().classes('policy-card').on('click', lambda _, value=key: choose(value)):
                        ui.label(label).classes('policy-title')
                        ui.label(description).classes('policy-copy')
            ui.label('大陸勢力').classes('daiou-heading')
            with ui.element('div').classes('nation-list'):
                for item in sorted(game['nations'], key=strength, reverse=True):
                    with ui.element('div').classes('nation-row' + (' player' if item['id'] == game['player'] else '')):
                        with ui.column().classes('gap-0 grow'):
                            ui.label(('あなた・' if item['id'] == game['player'] else '') + item['name']).classes('font-black')
                            ui.label(f"目的：{item['purpose']}　領土 {item['territory']}").classes('text-[10px] opacity-70')
                        ui.label(f"国力 {strength(item)}").classes('nation-power')
            with ui.expansion('国史', icon='history').classes('history-box w-full'):
                for line in game.get('log', []):
                    ui.label(line).classes('history-line')
        ui.add_css('''
        body{background:#071015!important}.daiou-app{width:min(100%,720px);min-height:100vh;margin:auto;padding:18px 16px 56px;color:#F5EBD2;background:radial-gradient(circle at 90% 0,#334B3C 0,transparent 27%),linear-gradient(180deg,#0B1820,#10130F)}.daiou-hero{position:relative;min-height:230px;padding:34px 24px;border-radius:30px;display:flex;flex-direction:column;justify-content:flex-end;overflow:hidden;background:linear-gradient(155deg,rgba(3,10,14,.1),rgba(3,8,7,.86)),radial-gradient(circle at 50% 20%,#B8863A,#26372D 48%,#0A1012 76%);border:1px solid rgba(226,184,96,.35);box-shadow:0 20px 48px rgba(0,0,0,.4)}.daiou-hero:before{content:'王';position:absolute;right:18px;top:-32px;font-size:190px;font-family:serif;font-weight:900;color:rgba(255,224,153,.11)}.daiou-title{font-family:serif;font-size:48px;font-weight:950;letter-spacing:.22em;color:#FFE5A0;text-shadow:0 5px 20px #000}.daiou-copy{font-size:11px;font-weight:800;opacity:.78}.turn-chip{position:absolute;top:17px;left:18px;padding:7px 11px;border-radius:999px;background:rgba(4,12,12,.58);font-size:10px;font-weight:900}.realm-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:12px 0 22px}.realm-stat{padding:11px 8px;border-radius:15px;background:rgba(255,255,255,.07);font-size:8px;color:#B8C3B8}.realm-value{font-size:18px;font-weight:950;color:#FFF1C7}.daiou-heading{margin:15px 2px 9px;font-size:18px;font-weight:950}.policy-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}.policy-card{min-height:100px;padding:16px!important;border-radius:19px!important;background:linear-gradient(145deg,#21362D,#16231E)!important;color:#F8EAC8!important;border:1px solid rgba(220,176,88,.22)!important;box-shadow:none!important;cursor:pointer}.policy-title{font-family:serif;font-size:20px;font-weight:950;color:#F0C96F}.policy-copy{font-size:10px;line-height:1.5;opacity:.7}.nation-list{display:flex;flex-direction:column;gap:6px}.nation-row{display:flex;align-items:center;padding:12px 14px;border-radius:15px;background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.06)}.nation-row.player{background:linear-gradient(90deg,rgba(188,139,53,.32),rgba(255,255,255,.06));border-color:rgba(240,201,111,.38)}.nation-power{padding:6px 9px;border-radius:999px;background:#08100D;font-size:9px;font-weight:900}.history-box{margin-top:13px;border-radius:17px!important;background:rgba(255,255,255,.06)!important}.history-line{padding:8px;border-bottom:1px solid rgba(255,255,255,.06);font-size:10px}@media(max-width:390px){.realm-grid{grid-template-columns:repeat(2,1fr)}}
        ''')
    render()
