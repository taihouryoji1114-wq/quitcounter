from calendar import monthrange
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
    login_screen('couple', '夫婦円満', '/couple', 'ふたりで育てる、なかよしガーデン')


@ui.page('/couple')
def couple_page():
    try:
        person = person_id()
    except ValueError:
        ui.navigate.to('/couple/login')
        return
    today = today_jst()
    month = {'year': today.year, 'month': today.month}
    ui.add_css('''
    body {background:#f8f5ee!important;color:#43564c;font-family:system-ui,sans-serif}
    .garden-shell{max-width:820px;margin:auto;padding:28px 18px 70px;width:100%;gap:22px}
    .garden-card{background:#fffdf9;border:1px solid #e8e6dc;border-radius:26px;padding:24px;width:100%;box-shadow:0 8px 30px #43564c08}
    .garden-hero{background:linear-gradient(130deg,#e5eee1,#f7ebdf);border-radius:32px;padding:30px;width:100%}
    .garden-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:7px;width:100%}
    .garden-day{border:0;border-radius:18px;min-height:76px;background:#edf2e7;color:#54654c;cursor:pointer;padding:4px;display:flex;flex-direction:column;align-items:center;justify-content:center}
    .garden-day.today{outline:2px solid #73967b}.garden-day.future{background:#f4f2ec;color:#aaa}
    .garden-day:hover{background:#e5ecdd}.garden-flower{font-size:26px}.garden-kicker{font-size:11px;letter-spacing:.2em;color:#738975}
    .q-btn{border-radius:14px;text-transform:none}.q-tab{border-radius:14px}
    @media(max-width:450px){.garden-shell{padding:18px 12px}.garden-card{padding:17px}.garden-grid{gap:4px}.garden-day{min-height:66px;border-radius:13px}}
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
                ui.label('夫婦円満').classes('text-3xl font-bold')
                ui.label('今日も、あなたと。').classes('text-xl')
                ui.label('穏やかな日も、仲直りした日も。ふたりの歩みを少しずつ。').classes('text-sm')
                ui.label(f'🌸 ふたりで咲かせた花　{count}日').classes('text-lg font-bold')
                ui.label(f'{today:%m月%d日} · あなたのありがとうは' + ('記録済み' if person in current.get('thanks', []) else 'これから'))
                button = ui.button('今日もありがとう ♡', on_click=lambda: action(lambda p: garden.check(p))).props('unelevated color=green-8')
                if person in current.get('thanks', []):
                    button.disable()
                ui.label('それぞれのアカウントで押すと、ひとつの花が咲きます。').classes('text-xs')
                ui.button('🌈 今日は仲直りできた', on_click=lambda: action(lambda p: garden.check(p, True))).props('flat color=green-9')
                ui.label('お休みの日があっても、咲いた花はなくなりません。').classes('text-xs')
            with ui.card().classes('garden-card'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.button(icon='chevron_left', on_click=lambda: change_month(-1)).props('flat round aria-label=前月')
                    ui.label(f"{month['year']}年 {month['month']}月の庭").classes('text-lg font-bold')
                    ui.button(icon='chevron_right', on_click=lambda: change_month(1)).props('flat round aria-label=翌月')
                ui.label('🌸 ふたりで確認　🌱 ひとりで確認　🌈 仲直り　☕ 話し合い').classes('text-xs')
                with ui.element('div').classes('garden-grid'):
                    for w in '月火水木金土日':
                        ui.label(w).classes('text-center text-xs')
                    first, length = monthrange(month['year'], month['month'])
                    for _ in range(first):
                        ui.element('div')
                    for d in range(1, length+1):
                        dt = date(month['year'], month['month'], d)
                        key = dt.isoformat()
                        value = days.get(key, {})
                        flower = '🌸' if len(value.get('thanks', [])) == 2 else '🌱' if value.get('thanks') else '·'
                        with ui.element('button').classes('garden-day' + (' today' if dt == today else '') + (' future' if dt > today else '')).props(f'aria-label="{key}の記録"').on('click', lambda _, k=key: show_day(k)):
                            ui.label(str(d)).classes('text-xs')
                            ui.label(flower).classes('garden-flower')
                            ui.label(('🌈' if value.get('rainbow') else '') + ('☕' if key in state['meetings'] else '')).classes('text-xs')
            with ui.card().classes('garden-card'):
                ui.label('ふたりの宝もの').classes('text-lg font-bold')
                with ui.row().classes('gap-4'):
                    for target, icon, title in [(7,'🏅','はじまりの花束'),(30,'🪑','庭のベンチ'),(100,'🐦','小鳥のお客さま')]:
                        ui.label(f'{icon if count >= target else "🔒"} {title} · {target}日').classes('text-green-9' if count >= target else 'text-grey-6')
                ui.label('連続日数ではなく、ふたりで押した累計日数で育ちます。').classes('text-xs')
            with ui.card().classes('garden-card'):
                ui.label('気持ちのポケット').classes('text-lg font-bold')
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
            with ui.card().classes('garden-card'):
                ui.label('☕ 週に一度の、ふたり会議').classes('text-lg font-bold')
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
