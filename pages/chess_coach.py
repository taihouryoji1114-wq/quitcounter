from nicegui import ui

from core.auth import require_app_access, selected_user_id
from core.chess_coach import board_from, explore_plans, legal_targets, new_game, play_user_move, undo_full_turn
from core.data import data
from core.theme import Theme


# 白黒とも同じシルエットを使い、色だけを変える。輪郭駒と塗り駒の混在を防ぐ。
PIECES={"P":"♟","N":"♞","B":"♝","R":"♜","Q":"♛","K":"♚",
        "p":"♟","n":"♞","b":"♝","r":"♜","q":"♛","k":"♚"}


@ui.page('/chess-coach')
def chess_coach_page():
    if not require_app_access('chess_coach'): return
    Theme.page('CHESS MENTOR',app_name='chess_coach')
    uid=selected_user_id(); profiles=data.data.setdefault('chess_coach',{}).setdefault('profiles',{})
    game=profiles.setdefault(uid,new_game()); state={'selected':None,'targets':[],'home':not bool(game.get('history'))}

    def save(): data.save()
    def choose(square):
        board=board_from(game); piece=board.piece_at(__import__('chess').parse_square(square))
        if state['selected'] and square in state['targets']:
            try:
                play_user_move(game,state['selected'],square)
                state.update(selected=None,targets=[]); save(); ui.notify('先生が応手を返しました',type='positive')
            except ValueError as error: ui.notify(str(error),type='warning')
            render.refresh(); return
        if piece and piece.color==board.turn:
            state['selected']=square; state['targets']=legal_targets(game,square)
        else: state.update(selected=None,targets=[])
        render.refresh()

    def reset():
        game.clear(); game.update(new_game()); state.update(selected=None,targets=[],home=False); save(); render.refresh()

    def undo():
        try:
            undo_full_turn(game); state.update(selected=None,targets=[]); save(); ui.notify('あなたと先生の手を戻しました')
        except ValueError as error: ui.notify(str(error),type='warning')
        render.refresh()

    def open_plan(plan):
        with ui.dialog() as dialog, ui.card().classes('plan-dialog'):
            with ui.row().classes('items-center justify-between w-full no-wrap'):
                with ui.column().classes('gap-0'):
                    ui.label('PLAN LAB').classes('coach-kicker')
                    ui.label(f"{plan['move']} を試す").classes('plan-title')
                ui.button(icon='close',on_click=dialog.close).props('flat round').classes('header-reset')
            ui.label(plan['verdict']).classes('plan-verdict')
            with ui.element('div').classes('insight-block'):
                ui.label('この手から考えられる狙い').classes('insight-label')
                ui.label(plan['idea']).classes('insight-text')
            with ui.element('div').classes('variation-line'):
                ui.label('代表的な進み方').classes('insight-label')
                ui.label(plan['line']).classes('variation-text')
            with ui.element('div').classes('insight-block danger'):
                ui.label('成立条件・弱点').classes('insight-label')
                ui.label(plan['risk']).classes('insight-text')
            ui.label(plan['note']).classes('plan-note')
            ui.button('別の計画と比べる',icon='account_tree',on_click=dialog.close).props('outline no-caps').classes('compare-button')
        dialog.open()

    @ui.refreshable
    def render():
        if state['home']:
            with ui.element('main').classes('mentor-splash'):
                ui.icon('school').classes('mentor-seal')
                ui.label('CHESS').classes('splash-chess'); ui.label('MENTOR').classes('splash-mentor')
                ui.label('一手には、理由がある。').classes('splash-copy')
                ui.button('指導対局を始める',icon='play_arrow',on_click=lambda:(state.update(home=False),render.refresh())).props('unelevated no-caps color=amber-7 text-color=dark').classes('start-lesson')
                ui.label('ルール判定・相手の意図・候補手を毎手解説').classes('splash-note')
            return
        board=board_from(game); coach=game.get('coach',{})
        with ui.element('main').classes('mentor-app'):
            with ui.element('header').classes('mentor-header'):
                ui.button(icon='arrow_back',on_click=lambda:(state.update(home=True),render.refresh())).props('flat round').classes('header-back')
                with ui.column().classes('gap-0'):
                    ui.label('CHESS MENTOR').classes('mentor-title'); ui.label('指導対局・あなたは白').classes('mentor-subtitle')
                with ui.row().classes('gap-0'):
                    ui.button(icon='undo',on_click=undo).props('flat round').classes('header-reset').tooltip('一手戻す')
                    ui.button(icon='restart_alt',on_click=reset).props('flat round').classes('header-reset').tooltip('最初から')
            with ui.element('section').classes('lesson-status'):
                ui.label(f"LESSON {len(game.get('history',[]))//2+1:02d}").classes('lesson-number')
                ui.label('あなたの手番').classes('turn-title')
                ui.label('動かす駒を選び、光ったマスをタップ').classes('turn-copy')
            with ui.element('div').classes('board-frame'):
                with ui.element('div').classes('chess-board'):
                    for rank in range(7,-1,-1):
                        for file in range(8):
                            import chess
                            sq=chess.square(file,rank); name=chess.square_name(sq); piece=board.piece_at(sq)
                            classes='chess-square '+('light' if (file+rank)%2 else 'dark')
                            if name==state['selected']: classes+=' selected'
                            if name in state['targets']: classes+=' target'
                            if game.get('history') and name in {game['history'][-1].get('from'),game['history'][-1].get('to')}: classes+=' last-move'
                            with ui.button(on_click=lambda _,value=name:choose(value)).props('flat dense').classes(classes):
                                if piece: ui.label(PIECES[piece.symbol()]).classes(
                                    'chess-piece '+('white-piece' if piece.color else 'black-piece')
                                    +f' piece-{piece.symbol().lower()}')
                                if file==0: ui.label(str(rank+1)).classes('rank-label')
                                if rank==0: ui.label(chr(97+file)).classes('file-label')
            with ui.element('section').classes('coach-card '+coach.get('verdict','GUIDE').lower()):
                with ui.row().classes('items-center no-wrap w-full'):
                    ui.icon('psychology_alt').classes('coach-icon')
                    with ui.column().classes('gap-0 grow'):
                        ui.label('COACH ANALYSIS').classes('coach-kicker'); ui.label(coach.get('title','考えてみよう')).classes('coach-title')
                ui.label(coach.get('summary','')).classes('coach-summary')
                with ui.element('div').classes('insight-block'):
                    ui.label('この手の意味').classes('insight-label'); ui.label(coach.get('why','')).classes('insight-text')
                with ui.element('div').classes('insight-block danger'):
                    ui.label('相手の狙い・注意点').classes('insight-label'); ui.label(coach.get('danger','')).classes('insight-text')
                if coach.get('candidates'):
                    ui.label('次に考えたい候補・タップして計画を研究').classes('candidate-label')
                    plans=explore_plans(board,count=len(coach['candidates']))
                    with ui.column().classes('candidate-row w-full'):
                        for i,plan in enumerate(plans):
                            ui.button(f"{i+1}　{plan['move']}　｜　{plan['verdict']}",icon='route',on_click=lambda _,p=plan:open_plan(p)).props('flat no-caps').classes('candidate-chip plan-button')
            if game.get('history'):
                with ui.expansion('これまでの棋譜',icon='history',value=False).classes('history-panel'):
                    for i,item in enumerate(reversed(game['history'])):
                        ui.label(f"{len(game['history'])-i}. {item['side']}　{item['move']}").classes('history-move')
    render()
    ui.add_css(CHESS_CSS)


CHESS_CSS='''
body{background:#080B10!important;color:#F4EFE5}.mentor-splash{width:min(100%,700px);min-height:100vh;margin:auto;padding:54px 24px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;background:radial-gradient(circle at 50% 34%,rgba(210,164,83,.23),transparent 29%),linear-gradient(145deg,#161B23,#07090D 72%)}.mentor-seal{display:flex!important;align-items:center;justify-content:center;width:90px;height:90px;border:1px solid #CFA75E;border-radius:50%;font-size:45px;color:#E3C178;background:linear-gradient(145deg,#272E38,#0A0E14);box-shadow:0 18px 55px #000,0 0 0 7px rgba(209,169,94,.06)}.splash-chess{margin-top:28px;font-family:Georgia,serif;font-size:53px;line-height:.9;letter-spacing:.16em;font-weight:900;color:#F8F2E7}.splash-mentor{font-family:Georgia,serif;font-size:20px;letter-spacing:.55em;color:#D4AF68}.splash-copy{margin-top:23px;font-size:14px;font-weight:800;letter-spacing:.15em;color:#D9D1C2}.start-lesson{width:min(100%,340px);min-height:58px!important;margin-top:39px;border-radius:8px!important;background:linear-gradient(135deg,#C6933E,#F0D18A)!important;color:#121820!important;font-size:14px!important;font-weight:950!important;box-shadow:0 15px 34px rgba(0,0,0,.38)!important}.splash-note{margin-top:14px;font-size:9px;color:#827D74}.mentor-app{width:min(100%,700px);min-height:100vh;margin:auto;padding:18px 14px 60px;background:radial-gradient(circle at 100% 0,rgba(180,131,57,.15),transparent 25%),linear-gradient(180deg,#111720,#080B10)}.mentor-header{display:flex;align-items:center;gap:10px;padding:6px 0 15px}.header-back,.header-reset{color:#CFC7B8!important}.mentor-title{font-family:Georgia,serif;font-size:17px;font-weight:950;letter-spacing:.12em}.mentor-subtitle{font-size:8px;color:#8E918F}.lesson-status{display:grid;grid-template-columns:auto 1fr;column-gap:12px;align-items:center;margin-bottom:12px;padding:12px 15px;border:1px solid rgba(215,177,101,.2);border-radius:14px;background:rgba(255,255,255,.035)}.lesson-number{grid-row:1/3;padding-right:12px;border-right:1px solid rgba(255,255,255,.1);font-family:Georgia,serif;font-size:11px;color:#D9B76F}.turn-title{font-size:13px;font-weight:950}.turn-copy{font-size:8px;color:#8F958F}.board-frame{padding:9px;border:1px solid #B88D4D;border-radius:8px;background:linear-gradient(145deg,#342C23,#11151B);box-shadow:0 18px 45px #000}.chess-board{display:grid;grid-template-columns:repeat(8,1fr);aspect-ratio:1;overflow:hidden;border:2px solid #080A0D}.chess-square{position:relative!important;min-width:0!important;min-height:0!important;padding:0!important;border-radius:0!important}.chess-square.light{background:linear-gradient(145deg,#E5DFD2,#BDB4A3)!important}.chess-square.dark{background:linear-gradient(145deg,#5F6872,#303944)!important}.chess-square.last-move{box-shadow:inset 0 0 0 999px rgba(218,172,69,.29)}.chess-square.selected{box-shadow:inset 0 0 0 4px #F3C665,0 0 17px #F3C665;z-index:2}.chess-square.target:after{content:'';position:absolute;z-index:5;left:40%;top:40%;width:20%;height:20%;border-radius:50%;background:#E4B854;box-shadow:0 0 10px #FFD982}.chess-piece{position:absolute;z-index:4;inset:0;display:flex;align-items:center;justify-content:center;font-family:'Times New Roman',serif;font-size:clamp(31px,10vw,65px);line-height:1;filter:drop-shadow(0 4px 2px rgba(0,0,0,.5));pointer-events:none}.white-piece{color:#FFF8E8;text-shadow:0 1px 0 #fff,0 2px 0 #b6a88e,0 3px 3px #161616,-1px 0 #423A31,1px 0 #423A31}.black-piece{color:#14181D;text-shadow:0 1px 0 #65717c,0 3px 3px #000,-1px 0 #000,1px 0 #000}.rank-label,.file-label{position:absolute;z-index:6;font-size:6px;font-weight:900;opacity:.58;pointer-events:none}.rank-label{left:2px;top:1px}.file-label{right:2px;bottom:1px}.coach-card{margin-top:14px;padding:18px;border-radius:20px;background:linear-gradient(145deg,#19232D,#10151C);border:1px solid rgba(213,174,96,.25);box-shadow:0 12px 30px rgba(0,0,0,.25)}.coach-card.good{border-color:rgba(76,187,139,.5)}.coach-card.careful{border-color:rgba(224,170,71,.55)}.coach-card.rethink{border-color:rgba(214,87,73,.58)}.coach-icon{font-size:35px;color:#D9B76F}.coach-kicker{font-family:Georgia,serif;font-size:8px;letter-spacing:.2em;color:#9D895D}.coach-title{font-size:20px;font-weight:950}.coach-summary{margin:13px 0 10px;font-size:11px;font-weight:850;color:#EDE6D8}.insight-block{margin-top:8px;padding:11px 12px;border-radius:12px;background:rgba(255,255,255,.045);border-left:3px solid #5FA88A}.insight-block.danger{border-left-color:#C98367}.insight-label{font-size:8px;font-weight:950;color:#AEB3AE}.insight-text{margin-top:3px;font-size:10px;line-height:1.65;color:#E6E1D7}.candidate-label{margin-top:14px;font-size:8px;font-weight:900;color:#999D99}.candidate-row{gap:6px!important;margin-top:5px}.candidate-chip{padding:6px 9px;border:1px solid rgba(222,185,109,.22);border-radius:8px;background:rgba(208,166,84,.08);font-size:9px;font-weight:900;color:#E7C980}.history-panel{margin-top:12px;border-radius:15px!important;background:rgba(255,255,255,.04)!important;color:#D8D4CC!important}.history-move{padding:7px 12px;border-bottom:1px solid rgba(255,255,255,.05);font-size:10px}@media(min-width:600px){.mentor-app{padding:28px 38px 70px}.chess-piece{font-size:64px}}
.plan-button{width:100%;min-height:39px!important;justify-content:flex-start!important;text-align:left}.plan-dialog{width:min(92vw,560px)!important;padding:22px!important;border:1px solid rgba(218,178,96,.35)!important;border-radius:22px!important;background:linear-gradient(145deg,#19232D,#0C1118)!important;color:#F4EFE5!important}.plan-title{font-family:Georgia,serif;font-size:21px;font-weight:950}.plan-verdict{margin-top:10px;padding:6px 10px;border-radius:8px;background:rgba(213,169,79,.12);font-size:10px;font-weight:950;color:#EBCB86}.variation-line{margin-top:10px;padding:14px;border:1px solid rgba(214,176,99,.22);border-radius:13px;background:#090D13}.variation-text{margin-top:5px;font-family:Georgia,serif;font-size:13px;line-height:1.7;color:#F0D697}.plan-note{margin-top:12px;font-size:8px;line-height:1.6;color:#8F958F}.compare-button{width:100%;margin-top:14px;color:#E4C47E!important}
/* 碁盤のような灰色をやめ、駒が一目で分かるクラシック配色へ統一 */
.chess-square.light{background:linear-gradient(145deg,#F1E5C8,#D8C59F)!important}.chess-square.dark{background:linear-gradient(145deg,#57705A,#344A3B)!important}.white-piece{color:#FFF7DC;text-shadow:0 1px 0 #fff,0 2px 0 #D7BD87,-1px 0 #31291F,1px 0 #31291F,0 3px 4px rgba(0,0,0,.75)}.black-piece{color:#24211E;text-shadow:0 1px 0 #8C7653,-1px 0 #060606,1px 0 #060606,0 3px 4px rgba(0,0,0,.72)}.chess-piece.piece-p{transform:scale(.86);transform-origin:center}.chess-piece.piece-n,.chess-piece.piece-b{transform:scale(.94)}
'''
