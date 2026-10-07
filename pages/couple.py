from datetime import date
from nicegui import ui
from core.auth import current_role, is_authenticated, log_out
from core.clock import today_jst
from core.couple import garden


def person_id():
    if not is_authenticated() or current_role() not in ('owner', 'partner'):
        raise ValueError('ふたりのアカウントでログインしてください')
    return 'user1' if current_role() == 'owner' else 'user2'


@ui.page('/couple/login')
def couple_login():
    from pages.login import login_screen
    login_screen('couple', '夫婦円満', '/couple', 'ふたりで育てる、なかよしガーデン', app_name='couple')


@ui.page('/couple')
def couple_page():
    try:
        person = person_id()
    except ValueError:
        ui.navigate.to('/couple/login')
        return
    from core.theme import Theme
    Theme.page('夫婦円満', app_name='couple')
    ui.add_head_html('<script src="/static/couple-hold.js"></script>')
    today = today_jst()
    month = {'year': today.year, 'month': today.month}
    ui.add_css('''
    body {background:#f8f5ee!important;color:#43564c;font-family:system-ui,sans-serif}
    .garden-shell{max-width:820px;margin:auto;padding:28px 18px 70px;width:100%;gap:22px}
    .garden-card{background:#fffdf9;border:1px solid #e8e6dc;border-radius:26px;padding:24px;width:100%;box-shadow:0 8px 30px #43564c08}
    .garden-hero{background:linear-gradient(130deg,#e5eee1,#f7ebdf);border-radius:32px;padding:30px;width:100%}
    .together-pad{touch-action:none;user-select:none;-webkit-user-select:none;padding:22px 0}.together-heart{touch-action:none;-webkit-touch-callout:none;border:none;width:42%;height:145px;border-radius:36px;font-size:70px;background:#ead3d3;color:#b66d7b;transition:transform .15s,background .15s}.together-heart.holding{background:#a9c6af;color:white;transform:scale(.94)}.together-heart:disabled{opacity:.65}
    .garden-kicker{font-size:11px;letter-spacing:.2em;color:#738975}
    .garden-hero{align-items:center;text-align:center;background:transparent;padding:12px 0 20px}
    .thanks-button{width:100%;min-height:150px;border-radius:40px!important;font-size:clamp(24px,6vw,38px)!important;background:linear-gradient(135deg,#557c60,#355b48)!important;box-shadow:0 14px 30px #355b4828!important;color:#fff!important}
    .garden-scene{position:relative;isolation:isolate;width:100%;min-height:410px;overflow:hidden;border-radius:36px;background:linear-gradient(#e5f0ed 0%,#f5f5df 43%,#d6e4bb 44%,#b9ce9f 100%);padding:120px 18px 58px}
    .garden-scene:before{content:'';position:absolute;z-index:-1;inset:95px -30% -140px;border-radius:50%;background:#cadbaa;transform:rotate(-10deg);box-shadow:80px 70px 0 20px #adc896}
    .garden-scene:after{content:'';position:absolute;z-index:-1;width:80px;height:600px;background:#eadbc1;top:100px;left:48%;transform:rotate(28deg);border-radius:50%}
    .garden-sun{position:absolute;top:28px;right:42px;width:54px;height:54px;background:#f8d98e;border-radius:50%;box-shadow:0 0 0 12px #f8d98e22}
    .garden-tree{position:absolute;top:35px;left:22px;font-size:90px;filter:saturate(.65)}
    .garden-fence{position:absolute;bottom:16px;left:20px;right:20px;height:30px;background:repeating-linear-gradient(90deg,#f7f0df 0 8px,transparent 8px 25px);border-top:5px solid #f7f0df;border-bottom:5px solid #f7f0df;opacity:.75}
    .garden-memories{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:24px 18px;position:relative;padding:15px 0}
    .memory-card{border:1px solid #ffffffbb;background:#fffdf2ed;color:#52634b;border-radius:22px 22px 22px 6px;padding:12px 15px;min-width:100px;box-shadow:0 12px 18px #43564c18;cursor:pointer;animation:bloom-in .7s ease both;transition:transform .2s}
    .memory-card:nth-child(3n+2){margin-top:32px;transform:rotate(5deg)}.memory-card:nth-child(3n){transform:rotate(-5deg)}.memory-card:hover{transform:translateY(-5px)}
    .garden-empty{position:relative;background:#ffffffe0;border-radius:22px;padding:20px;text-align:center;max-width:310px;margin:30px auto;color:#637458}
    .garden-drawer{width:100%;background:#fffdf9;border:1px solid #e8e6dc;border-radius:22px;padding:10px}.garden-drawer .q-expansion-item__content{padding:12px}
    .q-btn{border-radius:14px;text-transform:none}
    @keyframes bloom-in{from{opacity:0;translate:0 25px;scale:.8}to{opacity:1;translate:0 0;scale:1}}
    @media(prefers-reduced-motion:reduce){.memory-card{animation:none;transition:none}}
    @media(max-width:450px){.garden-shell{padding:18px 12px;gap:16px}.garden-card{padding:17px}.garden-scene{padding-left:10px;padding-right:10px}.memory-card{min-width:85px;padding:10px}.garden-memories{gap:16px 10px}}
    ''')

    def action(fn):
        try:
            fn(person_id())
        except ValueError as error:
            ui.notify(str(error), type='warning')
            return
        body.refresh()

    def show_day(day):
        state = garden.state(person_id())
        value = state['days'].get(day, {})
        with ui.dialog() as dialog, ui.card().classes('garden-card').style('max-width:450px'):
            ui.label(day.replace('-', ' / ')).classes('text-xl font-bold')
            count = len(value.get('thanks', []))
            ui.label('🌸 ふたりのありがとうが揃いました' if count == 2 else '🌱 ひとりのありがとう' if count else 'まだ記録はありません')
            if value.get('rainbow'):
                ui.label('🌈 仲直りの記録')
            if day in state['meetings']:
                ui.label('☕ ふたり会議').classes('font-bold')
                ui.label(state['meetings'][day]['promise']).classes('whitespace-pre-wrap')
            for note in state['notes']:
                if note['created_at'][:10] == day:
                    ui.label(('💌 ' if note['shared'] else '🔒 ') + note['category'])
                    ui.label(note['text']).classes('whitespace-pre-wrap')
            ui.button('閉じる', on_click=dialog.close).props('flat')
        dialog.open()

    @ui.refreshable
    def body():
        state = garden.state(person_id())
        days = state['days']
        count = sum(len(v.get('thanks', [])) == 2 for v in days.values())
        current = days.get(today.isoformat(), {})
        with ui.column().classes('garden-shell'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('OUR LITTLE GARDEN').classes('garden-kicker')
                ui.button('ログアウト', on_click=lambda: log_out('/couple/login')).props('flat dense color=grey-7')
            with ui.column().classes('garden-hero gap-3'):
                ui.label('夫婦円満').classes('text-sm')
                ui.label(f'🌸 ふたりで咲かせた花　{count}輪').classes('text-xl font-bold q-mb-md')
                ui.label('今日もありがとう').classes('text-3xl font-bold')
                completed = len(current.get('thanks', [])) == 2
                with ui.element('div').classes('together-pad w-full').props('data-done=' + ('true' if completed else 'false')) as pad:
                    with ui.row().classes('w-full no-wrap justify-center gap-5'):
                        for side in ('left', 'right'):
                            with ui.element('button').props(f'data-heart={side} aria-label="{"左" if side == "left" else "右"}のハート"' + (' disabled' if completed else '')).classes('together-heart'):
                                ui.label('♥').classes('pointer-events-none')
                    ui.label('今日の花が咲きました 🌸' if completed else '左右のハートを、ふたりで3秒長押し').props('data-status').classes('text-sm text-center q-mt-md')
                pad.on('pointerdown', lambda: action(lambda p: garden.together(p)), js_handler='(e) => window.coupleHold(e, emit)')
            with ui.column().classes('w-full gap-2'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.button(icon='chevron_left', on_click=lambda: change_month(-1)).props('flat round aria-label=前月')
                    ui.label(f"{month['year']}年 {month['month']}月の庭").classes('text-lg font-bold')
                    ui.button(icon='chevron_right', on_click=lambda: change_month(1)).props('flat round aria-label=翌月')
                with ui.element('div').classes('garden-scene'):
                    ui.element('div').classes('garden-sun').props('aria-hidden=true')
                    ui.label('🌳').classes('garden-tree').props('aria-hidden=true')
                    ui.element('div').classes('garden-fence').props('aria-hidden=true')
                    flowers = [(key, value) for key, value in sorted(days.items())
                               if key.startswith(f"{month['year']:04d}-{month['month']:02d}-")
                               and len(value.get('thanks', [])) == 2]
                    if not flowers:
                        with ui.column().classes('garden-empty'):
                            ui.label('🌱').classes('text-4xl self-center')
                            ui.label('最初の花を、ふたりで。').classes('font-bold')
                            ui.label('ふたりで3秒。今日の花が、ここに浮かびます。').classes('text-xs')
                    with ui.element('div').classes('garden-memories'):
                        for key, value in flowers:
                            with ui.element('button').classes('memory-card').props(f'aria-label="{key}の花を開く"').on('click', lambda _, k=key: show_day(k)):
                                ui.label('🌸').classes('text-4xl')
                                ui.label(f'{int(key[5:7])}月{int(key[8:10])}日').classes('font-bold')
                                ui.label(('🌈' if value.get('rainbow') else '♡') + (' ☕' if key in state['meetings'] else '')).classes('text-xs')
            with ui.expansion('ふたりの宝もの', icon='redeem', value=False).classes('garden-drawer'):
                with ui.row().classes('gap-4'):
                    for target, icon, title in [(7,'🏅','はじまりの花束'),(30,'🪑','庭のベンチ'),(100,'🐦','小鳥のお客さま')]:
                        ui.label(f'{icon if count >= target else "🔒"} {title} · {target}日').classes('text-green-9' if count >= target else 'text-grey-6')
                ui.label('連続日数ではなく、ふたりで押した累計日数で育ちます。').classes('text-xs')
            with ui.expansion('気持ちのポケット', icon='mail_outline', value=False).classes('garden-drawer'):
                ui.button('🌈 今日は仲直りできた', on_click=lambda: action(lambda p: garden.check(p, True))).props('flat color=green-9')
                category = ui.select(['ありがとう','気になったこと','次に話したいこと'], value='ありがとう', label='メモの種類').classes('w-full')
                memo = ui.textarea('今の気持ちをひとこと').props('outlined maxlength=2000').classes('w-full')
                shared = ui.switch('相手にも共有する', value=False)
                ui.label('オフのメモは、自分のアカウントだけに表示します。').classes('text-xs')
                ui.button('メモをしまう', on_click=lambda: action(lambda p: garden.note(p, category.value, memo.value, shared.value))).props('color=green-8')
                for note in reversed(state['notes']):
                    with ui.column().classes('w-full p-3 rounded-xl bg-orange-1'):
                        ui.label(('💌 共有' if note['shared'] else '🔒 自分だけ') + ' · ' + note['category'] + ' · ' + note['created_at'][:10]).classes('text-xs')
                        ui.label(('自分' if note['owner'] == person else '相手') + 'のメモ').classes('text-xs')
                        ui.label(note['text']).classes('whitespace-pre-wrap')
                        if note['owner'] == person:
                            ui.button('削除', on_click=lambda _, nid=note['id']: action(lambda p: garden.delete_note(p, nid))).props('flat dense color=grey-7')
            with ui.expansion('☕ 週に一度の、ふたり会議', icon='local_cafe', value=False).classes('garden-drawer'):
                last = max(state['meetings'], default=None)
                ui.label('前回：' + last if last else 'まだ話し合いの記録はありません')
                if not last or (today - date.fromisoformat(last)).days >= 7:
                    ui.label('今週、ゆっくりお茶を飲む時間をつくりませんか。').classes('text-green-8')
                ui.label('① うれしかったこと → ② 気になったこと → ③ 来週の小さな約束').classes('text-sm')
                when = ui.input('話し合った日', value=today.isoformat()).props('type=date').classes('w-full')
                promise = ui.textarea('ふたりで決めた、来週の小さな約束').props('outlined maxlength=1000').classes('w-full')
                ui.label('ふたりに共有されます。同じ日を保存すると、その日の約束を更新します。').classes('text-xs')
                ui.button('話し合いを記録する', on_click=lambda: action(lambda p: garden.meeting(p, when.value, promise.value))).props('color=green-8')
                for day, meeting in sorted(state['meetings'].items(), reverse=True):
                    ui.label('☕ ' + day).classes('font-bold')
                    ui.label(meeting['promise']).classes('whitespace-pre-wrap')

    def change_month(delta):
        index = month['year']*12 + month['month']-1 + delta
        month['year'], m = divmod(index, 12)
        month['month'] = m+1
        body.refresh()
    body()
